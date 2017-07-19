# -*- coding: utf-8 -*-
##########################################################################################
# Developer: Luan,Jingchao        Project: HuMaIN (http://humain.acis.ula.ve)
# Description: 
#     Receive OCRopus recognition service requests from user, call recognition function and
# get the output, and then return the output or error info to user.
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
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
from django.http import HttpResponse
from django.conf import settings
from django.shortcuts import render
from wsgiref.util import FileWrapper
from .serializers import ParameterSerializer
from .recognition import recognition_exec
from .extrafunc import del_service_files
import sys, os, os.path, zipfile, StringIO, glob


# Get the directory which stores all input and output files
dataDir = settings.MEDIA_ROOT

def index(request):
    return render(request, 'index.html')

@csrf_exempt
@api_view(['GET', 'POST'])
def recognitionView(request, format=None):
    if request.data.get('image') is None:
        return HttpResponse("Please upload at least one binarized image.")

    ### Receive and store uploaded image(s)
    # One or multiple images/values in one field
    imagepaths = []
    images = request.data.getlist('image')
    for image in images:
        image_str = str(image)
        imagepaths.append(dataDir+"/"+image_str)
        default_storage.save(dataDir+"/"+image_str, image)

    ### Receive and store uploaded recognizor model specified by the user
    if request.data.get('model') is not None:
        model = request.data.get('model')
        modelpath = dataDir+"/"+str(model)
        default_storage.save(modelpath, model)
    
    ### Receive other parameters set by the user
    data_dict = request.data.dict()
    # Image(s) and model will be processed seperately for receiving multiple images and store in local FS
    del data_dict['image']
    # Serialize the specified parameters, only containing the specified parameters
    # If we want to generate the parameters object with all of the default paremeters, call parameters.save()
    paras_serializer = ParameterSerializer(data=data_dict)
    if paras_serializer.is_valid():
        pass # needn't parameters.save(), since we needn't to store these parameters in DB
    parameters = paras_serializer.data
    if request.data.get('model') is not None:
        parameters.update({'model':modelpath})
	
    # Call OCR recognition function
    #alltext_file = recognition_exec(dataDir)
    outputfiles = recognition_exec(imagepaths, parameters)

    # Return the multiple files in zip type
    # Folder name in ZIP archive which contains the above files
    zip_dir = "output_recognition"
    zip_filename = "%s.zip" % zip_dir
    # Open StringIO to grab in-memory ZIP contents
    strio = StringIO.StringIO()
    # The zip compressor
    zf = zipfile.ZipFile(strio, "w")

    for fpath in outputfiles:
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

    # Delete all files related to this service time
    del_service_files(dataDir)

    return response