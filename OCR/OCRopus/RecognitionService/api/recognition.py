#!/usr/bin/env python
##########################################################################################
# Developer: Luan,Jingchao        Project: HuMaIN (http://humain.acis.ula.ve)
# Description: 
#     Recognize and extract line text from a singal-line image, based on the default
# parameters or parameters set by user.
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

from __future__ import print_function

import traceback
import codecs
from pylab import *
import os.path
import ocrolib
import matplotlib
from multiprocessing import Pool
from ocrolib import edist
from ocrolib.exceptions import FileNotFound, OcropusException
from collections import Counter
from ocrolib import lstm
from scipy.ndimage import measurements
from django.conf import settings


# Get the directory which stores all input and output files
dataDir = settings.MEDIA_ROOT
# The directory of the default model
default_model = settings.BASE_DIR + "/models/en-default.pyrnn.gz"

# 'args_default' only contains the parameters that cannot be set by users
args_default = {
    'model':default_model, # line recognition model
    'nocheck':False,       # disable error checking on images
    'quiet':False          # turn off most output

}

# The global variable
args = {}

# The entry of segmentation service
# Return the directories, each directory related to a input image and stored the segmented line images  
def recognition_exec(image, parameters, *model):
    # Update parameters values customed by user
    # Each time update the args with the default args dictionary, avoid the effect of the previous update
    global args
    args = args_default.copy()
    args.update(parameters)
    # if model set by user, update model using the model set by user
    for m in model:
        if m is not None:
            args.update({'model': m})
    print("=====Parameters Values =====")
    print(args)
    print("============================")

    if len(image) < 1:
        print("ERROR: Please upload an image")
        return None

    # Unicode to str
    image = str(image)

    # Get the line normalizer
    get_linenormalizer()

    # Recognize the single-line image
    output_list = []
    try:
        output_list = process(image)
    except OcropusException as e:
        if e.trace:
            traceback.print_exc()
        else:
            print_info(image+":"+e)
    except Exception as e:
        traceback.print_exc()
    
    return output_list


def print_info(*objs):
    print("INFO: ", *objs, file=sys.stdout)

def print_error(*objs):
    print("ERROR: ", *objs, file=sys.stderr)

def check_line(image):
    if len(image.shape)==3: return "input image is color image %s"%(image.shape,)
    if mean(image)<median(image): return "image may be inverted"
    h,w = image.shape
    if h<20: return "image not tall enough for a text line %s"%(image.shape,)
    if h>200: return "image too tall for a text line %s"%(image.shape,)
    if w<1.5*h: return "line too short %s"%(image.shape,)
    if w>4000: return "line too long %s"%(image.shape,)
    ratio = w*1.0/h
    _,ncomps = measurements.label(image>mean(image))
    lo = int(0.5*ratio+0.5)
    hi = int(4*ratio)+1
    if ncomps<lo: return "too few connected components (got %d, wanted >=%d)"%(ncomps,lo)
    if ncomps>hi*ratio: return "too many connected components (got %d, wanted <=%d)"%(ncomps,hi)
    return None


# Get the line normalizer 
def get_linenormalizer():
    global network
    global lnorm
    # load the network used for classification
    try:
        network = ocrolib.load_object(args['model'],verbose=1)
        for x in network.walk(): x.postLoad()
        for x in network.walk():
            if isinstance(x,lstm.LSTM):
                x.allocate(5000)
    except FileNotFound:
        print_error("")
        print_error("Cannot find OCR model file:" + args['model'])
        print_error("Download a model and put it into:" + ocrolib.default.modeldir)
        print_error("(Or override the location with OCROPUS_DATA.)")
        print_error("")
        sys.exit(1)

    # get the line normalizer from the loaded network, or optionally
    # let the user override it (this is not very useful)
    lnorm = getattr(network,"lnorm",None)

    if args['height']>0:
        lnorm.setHeight(args['height'])  



# process one image
def process(imagepath):
    output_list = []
    base,_ = ocrolib.allsplitext(imagepath)
    line = ocrolib.read_image_gray(imagepath)
    raw_line = line.copy()
    if prod(line.shape)==0: return None
    if amax(line)==amin(line): return None

    if not args['nocheck']:
        check = check_line(amax(line)-line)
        if check is not None:
            print_error("%s SKIPPED %s (use -n to disable this check)" % (imagepath, check))
            return (0,[],0,imagepath)

    temp = amax(line)-line
    temp = temp*1.0/amax(temp)
    lnorm.measure(temp)
    line = lnorm.normalize(line,cval=amax(line))

    line = lstm.prepare_line(line,args['pad'])
    pred = network.predictString(line)

    if args['llocs']:
        # output recognized LSTM locations of characters
        result = lstm.translate_back(network.outputs,pos=1)
        scale = len(raw_line.T)*1.0/(len(network.outputs)-2*args['pad'])
        output_llocs = base+".llocs"
        with codecs.open(output_llocs,"w","utf-8") as locs:
            for r,c in result:
                c = network.l2s([c])
                r = (r-args['pad'])*scale
                locs.write("%s\t%.1f\n"%(c,r))
            output_list.append(output_llocs)
                #plot([r,r],[0,20],'r' if c==" " else 'b')
        #ginput(1,1000)

    if args['probabilities']:
        # output character probabilities
        result = lstm.translate_back(network.outputs,pos=2)
        output_prob = base+".prob"
        with codecs.open(output_prob,"w","utf-8") as file:
            for c,p in result:
                c = network.l2s([c])
                file.write("%s\t%s\n"%(c,p))
            output_list.append(output_prob)

    if not args['nonormalize']:
        pred = ocrolib.normalize_text(pred)

    if not args['quiet']:
        print_info(imagepath+":"+pred)
    output_text = base+".txt"
    ocrolib.write_text(output_text,pred)
    output_list.append(output_text)

    return output_list