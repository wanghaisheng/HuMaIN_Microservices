
# -*- coding: utf-8 -*-
#!/usr/bin/env python
##########################################################################################
# Developer: Luan,Jingchao        Project: HuMaIN (http://humain.acis.ufl.edu)
# Description: 
#     Convert a image from grayscale to black and white, based on the default parameters or
# parameters set by user.
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
from PIL import Image
from resizeimage import resizeimage # Used for image resize
from django.core.exceptions import ValidationError
import sys, os, os.path, shutil

'''
This module rpovides extra functions
'''

### Check the validation of the uploaded images
def validate_image_extension(value):
    ext = os.path.splitext(value.name)[1]  # [0] returns path+filename
    valid_extensions = ['.png', '.jpg', '.jpeg']
    if not ext.lower() in valid_extensions:
        raise ValidationError(u'Unsupported file extension.')


### Resize the image size to meet the smallest size requirment of binarization: 600*600 pixels
### Resize by adding a white backgroud border, but not to strech the original image
def resize_image(imagepath):
    fd_img = open(imagepath, 'r')
    img = Image.open(fd_img)
    w, h = img.size
    if w<600 or h<600:
        if w<600: w = 600
        if h<600: h = 600
        new_size = [w, h]
        new_image = resizeimage.resize_contain(img, new_size)
        new_image.save(imagepath, new_image.format) # override the original image
        fd_img.close()
    else:
        pass


### Delete all files related to this service time, including inputs and outputs
def del_service_files(dataDir):
    for the_file in os.listdir(dataDir):
        file_path = os.path.join(dataDir, the_file)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(e)