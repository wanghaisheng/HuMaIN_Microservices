# -*- coding: utf-8 -*-
import os, os.path, shutil

'''
This module rpovides extra functions
'''

### Check the validation of the uploaded images
def validate_image_extension(value):
    ext = os.path.splitext(value.name)[1]  # [0] returns path+filename
    valid_extensions = ['.png', '.jpg', '.jpeg']
    if not ext.lower() in valid_extensions:
        raise ValidationError(u'Unsupported file extension.')


# Delete all files related to this service time, including inputs and outputs
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