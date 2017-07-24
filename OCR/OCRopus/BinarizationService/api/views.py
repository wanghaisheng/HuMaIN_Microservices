# -*- coding: utf-8 -*-
##########################################################################################
# Developer: Luan,Jingchao        Project: HuMaIN (http://humain.acis.ula.ve)
# Description: 
#     Receive OCRopus binarization service requests from user, call binarization function 
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
from rest_framework.decorators import api_view, parser_classes
from rest_framework.response import Response
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.conf import settings
from django.shortcuts import render
from wsgiref.util import FileWrapper
from .models import Parameters
from .binarization import binarization_exec
from .extrafunc import resize_image, del_service_files
from .serializers import ParameterSerializer
import sys, os, os.path, zipfile, StringIO


# Set encoding
reload(sys)
sys.setdefaultencoding('utf8')

# Get the directory which stores all input and output files
projectDir = settings.BASE_DIR
dataDir = settings.MEDIA_ROOT

def index(request):
    return render(request, 'index.html')

@csrf_exempt
@api_view(['GET', 'POST'])
def binarizationView(request, format=None):
    if request.data.get('image') is None:
        #return HttpResponse(content='Please upload an image', status=400)
        return Response("ERROR: Please upload an image", status=status.HTTP_400_BAD_REQUEST)

    ### Receive image and parameters with model serializer
    paras_serializer = ParameterSerializer(data=request.data)
    if paras_serializer.is_valid():
        paras_serializer.save()
    else:
        return Response(paras_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    ### Resize the image if its size smaller than 600*600
    imagepath = projectDir + paras_serializer.data['image']
    try:
        resize_image(imagepath)
    except:
        Parameters.objects.filter(id=paras_serializer.data['id']).delete()
        del_service_files(dataDir)
        return Response("ERROR: Re-size image error", status=status.HTTP_500_INTERNAL_SERVER_ERROR)
 
    ### Call OCR binarization function
    output_file = binarization_exec(imagepath, paras_serializer.data)
    if output_file is None:
        Parameters.objects.filter(id=paras_serializer.data['id']).delete()
        del_service_files(dataDir)
        return Response("ERROR: sth wrong with binarization", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    ### Return output file
    fdir, fname = os.path.split(output_file)
    response = HttpResponse(FileWrapper(open(output_file, 'rb')), content_type='application/force-download')
    response['Content-Disposition'] = 'attachment; filename=%s' % fname
    
    ### Delete all datas generated during this service
    # Delete data in database
    Parameters.objects.filter(id=paras_serializer.data['id']).delete()
    # Delete files in local storage
    del_service_files(dataDir)

    return response