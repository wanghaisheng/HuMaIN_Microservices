# -*- coding: utf-8 -*-
##########################################################################################
# Developer: Luan,Jingchao        Project: HuMaIN (http://humain.acis.ufl.edu)
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
import sys, os, os.path
import time
import logging

# Set encoding
reload(sys)
sys.setdefaultencoding('utf8')

# Get the directory which stores all input and output files
projectDir = settings.BASE_DIR
dataDir = settings.MEDIA_ROOT

def index(request):
    return render(request, 'index.html')

### New version: process image in-memory => response output image from memory
@csrf_exempt
@api_view(['GET', 'POST'])
def binarizationView(request, format=None):
    receive_req = time.time()
    logger = logging.getLogger('django')
    if request.data.get('image') is None:
        logger.error("Please upload only one image")
        return Response("ERROR: Please upload only one image", status=status.HTTP_400_BAD_REQUEST)

    ### Receive parameters with model serializer
    paras_serializer = ParameterSerializer(data=request.data)
    if paras_serializer.is_valid():
        paras_serializer.save()
    else:
        logger.error(paras_serializer.errors)
        return Response(paras_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    image_object = request.FILES['image']
    
    ### Resize the image if its size smaller than 600*600
    #try:
    #    resize_image(image_object)
    #except:
    #    Parameters.objects.filter(id=paras_serializer.data['id']).delete()
    #   return Response("ERROR: Re-size image error", status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
 
    ### Call OCR binarization function
    bin_begin = time.time()
    output_file = binarization_exec(image_object, paras_serializer.data)
    bin_end = time.time()
    if output_file is None:
        Parameters.objects.filter(id=paras_serializer.data['id']).delete()
        logger.error("sth wrong with binarization")
        return Response("ERROR: sth wrong with binarization", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    ### Return image object (in memory)
    response = HttpResponse(content_type="image/png")
    output_file.save(response, "PNG")

    ### Delete parameters object in DB
    Parameters.objects.filter(id=paras_serializer.data['id']).delete()

    send_resp = time.time()
    logger.info("===== Image %s =====" % str(image_object))
    logger.info("*** Before bin: %.2fs ***" % (bin_begin-receive_req))
    logger.info("*** Bin: %.2fs ***" % (bin_end-bin_begin))
    logger.info("*** After bin: %.2fs ***" % (send_resp-bin_end))
    logger.info("*** Service time: %.2fs ***" % (send_resp-receive_req))
    return response


"""
### Old version: save image to disk => process image from disk => save output to disk => response output image => delete disk images
@csrf_exempt
@api_view(['GET', 'POST'])
def binarizationView(request, format=None):
    receive_req = time.time()
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
    #try:
    #    resize_image(imagepath)
    #except:
    #    Parameters.objects.filter(id=paras_serializer.data['id']).delete()
    #    del_service_files(dataDir)
    #    return Response("ERROR: Re-size image error", status=status.HTTP_500_INTERNAL_SERVER_ERROR)
 
    ### Call OCR binarization function
    bin_begin = time.time()
    output_file = binarization_exec(imagepath, paras_serializer.data)
    bin_end = time.time()
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


    send_resp = time.time()
    print("*** Before bin: %.4f ***" % (bin_begin-receive_req))
    print("*** Bin: %.4f ***" % (bin_end-bin_begin))
    print("*** After bin: %.4f ***" % (send_resp-bin_end))
    print("*** Service time: %.4f ***" % (send_resp-receive_req))
    return response
"""
