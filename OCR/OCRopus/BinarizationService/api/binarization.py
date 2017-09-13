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

from __future__ import print_function
from pylab import *
from numpy.ctypeslib import ndpointer
import os, os.path
from scipy.ndimage import filters, interpolation, morphology, measurements
from scipy import stats
import ocrolib
import StringIO, PIL, numpy
from numpy import amax, amin
import logging


# 'args_default' only contains the parameters that cannot be set by users
args_default = {
'nocheck':True  # disable error checking on inputs
}

# The global variable
args = {}
logger = logging.getLogger('django')

# The entry of binarization service
def binarization_exec(image, parameters):
    # Update parameters values customed by user
    # Each time update the args with the default args dictionary, avoid the effect of the previous update
    global args
    args = args_default.copy()
    args.update(parameters)
    print("=====Parameters Values =====")
    print(args)
    print("============================")
    
    if len(image) < 1:
        print("ERROR: Please upload an image")
        return None

    # Unicode to str
    #image = str(image)

    # Binarize the image
    try:
        output_file = process(image)
    except:
        output_file = None

    return output_file
    

def print_info(*objs):
    print("INFO: ", *objs, file=sys.stdout)

def print_error(*objs):
    print("ERROR: ", *objs, file=sys.stderr)

def check_page(image):
    if len(image.shape)==3: return "input image is color image %s"%(image.shape,)
    if mean(image)<median(image): return "image may be inverted"
    h,w = image.shape
    if h<600: return "image not tall enough for a page image %s"%(image.shape,)
    if h>10000: return "image too tall for a page image %s"%(image.shape,)
    if w<600: return "image too narrow for a page image %s"%(image.shape,)
    if w>10000: return "line too wide for a page image %s"%(image.shape,)
    return None

def estimate_skew_angle(image,angles):
    estimates = []
    for a in angles:
        v = mean(interpolation.rotate(image,a,order=0,mode='constant'),axis=1)
        v = var(v)
        estimates.append((v,a))
    _,a = max(estimates)
    return a

def H(s): return s[0].stop-s[0].start
def W(s): return s[1].stop-s[1].start
def A(s): return W(s)*H(s)


def array2pil(a):
    if a.dtype==dtype("B"):
        if a.ndim==2:
            return PIL.Image.frombytes("L",(a.shape[1],a.shape[0]),a.tostring())
        elif a.ndim==3:
            return PIL.Image.frombytes("RGB",(a.shape[1],a.shape[0]),a.tostring())
        else:
            raise OcropusException("bad image rank")
    elif a.dtype==dtype('float32'):
        return PIL.Image.fromstring("F",(a.shape[1],a.shape[0]),a.tostring())
    else:
        raise Exception("unknown image type")


def process(imagepath):
    logger.info("# %s" % (imagepath))
    raw = ocrolib.read_image_gray(imagepath) 

    # perform image normalization
    image = raw-amin(raw)
    if amax(image)==amin(image):
        logger.info("# image is empty: %s" % (imagepath))
        return
    image /= amax(image)

    if not args['nocheck']:
        check = check_page(amax(image)-image)
        if check is not None:
            logger.error(imagepath+"SKIPPED"+check+"(use -n to disable this check)")
            return

    # flatten the image by estimating the local whitelevel
    comment = ""
    # if not, we need to flatten it by estimating the local whitelevel
    logger.info("flattening")
    m = interpolation.zoom(image,args['zoom'])
    m = filters.percentile_filter(m,args['perc'],size=(args['range'],2))
    m = filters.percentile_filter(m,args['perc'],size=(2,args['range']))
    m = interpolation.zoom(m,1.0/args['zoom'])
    w,h = minimum(array(image.shape),array(m.shape))
    flat = clip(image[:w,:h]-m[:w,:h]+1,0,1)

    # estimate skew angle and rotate
    if args['maxskew']>0:
        logger.info("estimating skew angle")
        d0,d1 = flat.shape
        o0,o1 = int(args['bignore']*d0),int(args['bignore']*d1)
        flat = amax(flat)-flat
        flat -= amin(flat)
        est = flat[o0:d0-o0,o1:d1-o1]
        ma = args['maxskew']
        ms = int(2*args['maxskew']*args['skewsteps'])
        angle = estimate_skew_angle(est,linspace(-ma,ma,ms+1))
        flat = interpolation.rotate(flat,angle,mode='constant',reshape=0)
        flat = amax(flat)-flat
    else:
        angle = 0

    # estimate low and high thresholds
    logger.info("estimating thresholds")
    d0,d1 = flat.shape
    o0,o1 = int(args['bignore']*d0),int(args['bignore']*d1)
    est = flat[o0:d0-o0,o1:d1-o1]
    if args['escale']>0:
        # by default, we use only regions that contain
        # significant variance; this makes the percentile
        # based low and high estimates more reliable
        e = args['escale']
        v = est-filters.gaussian_filter(est,e*20.0)
        v = filters.gaussian_filter(v**2,e*20.0)**0.5
        v = (v>0.3*amax(v))
        v = morphology.binary_dilation(v,structure=ones((int(e*50),1)))
        v = morphology.binary_dilation(v,structure=ones((1,int(e*50))))
        est = est[v]
    lo = stats.scoreatpercentile(est.ravel(),args['lo'])
    hi = stats.scoreatpercentile(est.ravel(),args['hi'])
    # rescale the image to get the gray scale image
    logger.info("rescaling")
    flat -= lo
    flat /= (hi-lo)
    flat = clip(flat,0,1)
    bin = 1*(flat>args['threshold'])

    
    # output the normalized grayscale and the thresholded image
    logger.info("%s lo-hi (%.2f %.2f) angle %4.1f %s" % (imagepath, lo, hi, angle, comment))
    logger.info("writing")

    """
    ### Return image file path in disk (write to disk firstly)
    base,_ = ocrolib.allsplitext(imagepath)
    outputfile_bin = base+".bin.png"
    ocrolib.write_image_binary(outputfile_bin, bin)
    return outputfile_bin
    """
    
    ### Return image object directly (in memory)
    assert bin.ndim==2
    midrange = 0.5*(amin(bin)+amax(bin))
    image_array = array(255*(bin>midrange),'B') # wrong if call "ocrlib.midrange()"
    image_pil = array2pil(image_array)  # wrong if call "ocrlib.array2pil()"
    return image_pil
    
