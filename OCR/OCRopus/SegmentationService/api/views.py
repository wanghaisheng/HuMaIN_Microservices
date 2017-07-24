# -*- coding: utf-8 -*-
##########################################################################################
# Developer: Luan,Jingchao        Project: HuMaIN (http://humain.acis.ula.ve)
# Description: 
#     Receive OCRopus segmentation service requests from user, call segmentation function
# and get the output, and then return the output or error info to user.
##########################################################################################
# Copyright 2017    Advanced Computing and Information Systems (ACIS) Lab - UF
#                   (https://www.acis.ufl.edu/)
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
# http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
##########################################################################################


from __future__ import unicode_literals
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.conf import settings
from django.shortcuts import render
from .models import Parameters
from .serializers import ParameterSerializer
from .segmentation import segmentation_exec
from .extrafunc import del_service_files
import sys, os, os.path, zipfile, StringIO


# Get the directory which stores all input and output files
projectDir = settings.BASE_DIR
dataDir = settings.MEDIA_ROOT

def index(request):
    return render(request, 'index.html')

@csrf_exempt
@api_view(['GET', 'POST'])
def segmentationView(request, format=None):
    if request.data.get('image') is None:
        #return HttpResponse(content='Please upload an image', status=400)
        return Response("ERROR: Please upload an image", status=status.HTTP_400_BAD_REQUEST)

    ### Receive image and parameters with model serializer
    paras_serializer = ParameterSerializer(data=request.data)
    if paras_serializer.is_valid():
        paras_serializer.save()
    else:
        return Response(paras_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    ### Call segmentation function
    imagepath = projectDir + paras_serializer.data['image']
    output_list = segmentation_exec(imagepath, paras_serializer.data)
    if not output_list: # if output_list is emplty
        Parameters.objects.filter(id=paras_serializer.data['id']).delete()
        del_service_files(dataDir)
        return Response("ERROR: sth wrong with segmentation", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    ### return the multiple files in zip type
    # Folder name in ZIP archive which contains the above files
    zip_dir = "output_segmentation"
    zip_filename = "%s.zip" % zip_dir
    # Open StringIO to grab in-memory ZIP contents
    strio = StringIO.StringIO()
    # The zip compressor
    zf = zipfile.ZipFile(strio, "w")

    for fpath in output_list:
        # Caculate path for file in zip
        fdir, fname = os.path.split(fpath)
        zip_path = os.path.join(zip_dir, fname)
        # Add file, at correct path
        zf.write(fpath, zip_path)

    zf.close()
    # Grab ZIP file from in-memory, make response with correct MIME-type
    response = HttpResponse(strio.getvalue(), content_type="application/x-zip-compressed")
    # And correct content-disposition
    response["Content-Disposition"] = 'attachment; filename=%s' % zip_filename
    
    ### Delete all datas generated during this service
    # Delete data in database
    Parameters.objects.filter(id=paras_serializer.data['id']).delete()
    # Delete files in local storage
    del_service_files(dataDir)

    return response