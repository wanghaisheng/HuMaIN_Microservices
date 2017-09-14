#!/usr/bin/env python
##########################################################################################
# Developer: Luan,Jingchao        Project: HuMaIN (http://humain.acis.ufl.edu)
# Description: 
#     Extract the individual line images from a binarized image, based on the default 
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

# TODO:
# ! add option for padding
# - fix occasionally missing page numbers
# - treat large h-whitespace as separator
# - handle overlapping candidates
# - use cc distance statistics instead of character scale
# - page frame detection
# - read and use text image segmentation mask
# - pick up stragglers
# ? laplacian as well

from __future__ import print_function

from pylab import *
import glob,os,os.path
import traceback
from scipy.ndimage import measurements
from scipy.misc import imsave
from scipy.ndimage.filters import gaussian_filter,uniform_filter,maximum_filter
from multiprocessing import Pool
import ocrolib
from ocrolib import psegutils,morph,sl
from ocrolib.exceptions import OcropusException
from ocrolib.toplevel import *
from numpy import amax, amin
from django.conf import settings
import logging

dataDir = settings.MEDIA_ROOT
# 'args_default' only contains the parameters that cannot be set by users
args_default = {
    # output parameters
    'pad':3,         # adding for extracted lines
    'expand':3,      # expand mask for grayscale extraction
    # other parameters
    'nocheck':True,  # disable error checking on inputs
    'quiet':False,   # be less verbose
    'debug':False
}

# The global variable
args = {}
logger = logging.getLogger('django')

# The entry of segmentation service
# Return the directories, each directory related to a input image and stored the segmented line images  
def segmentation_exec(image, parameters):
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

    # Segment the image
    output_list = []
    try:
        output_list = process(image)
    except OcropusException as e:
        if e.trace:
            traceback.print_exc()
        else:
            logger.info(image+":"+e)
    except Exception as e:
        traceback.print_exc()
    
    return output_list


def norm_max(v):
    return v/amax(v)


def check_page(image):
    if len(image.shape)==3: return "input image is color image %s"%(image.shape,)
    if mean(image)<median(image): return "image may be inverted"
    h,w = image.shape
    if h<600: return "image not tall enough for a page image %s"%(image.shape,)
    if h>10000: return "image too tall for a page image %s"%(image.shape,)
    if w<600: return "image too narrow for a page image %s"%(image.shape,)
    if w>10000: return "line too wide for a page image %s"%(image.shape,)
    slots = int(w*h*1.0/(30*30))
    _,ncomps = measurements.label(image>mean(image))
    if ncomps<10: return "too few connected components for a page image (got %d)"%(ncomps,)
    if ncomps>slots: return "too many connnected components for a page image (%d > %d)"%(ncomps,slots)
    return None


def print_info(*objs):
    print("INFO: ", *objs, file=sys.stdout)

def print_error(*objs):
    print("ERROR: ", *objs, file=sys.stderr)

def B(a):
    if a.dtype==dtype('B'): return a
    return array(a,'B')

def DSAVE(title,image):
    if not args['debug']: return
    if type(image)==list:
        assert len(image)==3
        image = transpose(array(image),[1,2,0])
    fname = "_"+title+".png"
    logger.info("debug " + fname)
    imsave(fname,image)



################################################################
### Column finding.
###
### This attempts to find column separators, either as extended
### vertical black lines or extended vertical whitespace.
### It will work fairly well in simple cases, but for unusual
### documents, you need to tune the parameters.
################################################################

def compute_separators_morph(binary,scale):
    """Finds vertical black lines corresponding to column separators."""
    d0 = int(max(5,scale/4))
    d1 = int(max(5,scale))+args['sepwiden']
    thick = morph.r_dilation(binary,(d0,d1))
    vert = morph.rb_opening(thick,(10*scale,1))
    vert = morph.r_erosion(vert,(d0//2,args['sepwiden']))
    vert = morph.select_regions(vert,sl.dim1,min=3,nbest=2*args['maxseps'])
    vert = morph.select_regions(vert,sl.dim0,min=20*scale,nbest=args['maxseps'])
    return vert

def compute_colseps_mconv(binary,scale=1.0):
    """Find column separators using a combination of morphological
    operations and convolution."""
    h,w = binary.shape
    smoothed = gaussian_filter(1.0*binary,(scale,scale*0.5))
    smoothed = uniform_filter(smoothed,(5.0*scale,1))
    thresh = (smoothed<amax(smoothed)*0.1)
    DSAVE("1thresh",thresh)
    blocks = morph.rb_closing(binary,(int(4*scale),int(4*scale)))
    DSAVE("2blocks",blocks)
    seps = minimum(blocks,thresh)
    seps = morph.select_regions(seps,sl.dim0,min=args['csminheight']*scale,nbest=args['maxcolseps'])
    DSAVE("3seps",seps)
    blocks = morph.r_dilation(blocks,(5,5))
    DSAVE("4blocks",blocks)
    seps = maximum(seps,1-blocks)
    DSAVE("5combo",seps)
    return seps

def compute_colseps_conv(binary,scale=1.0):
    """Find column separators by convoluation and
    thresholding."""
    h,w = binary.shape
    # find vertical whitespace by thresholding
    smoothed = gaussian_filter(1.0*binary,(scale,scale*0.5))
    smoothed = uniform_filter(smoothed,(5.0*scale,1))
    thresh = (smoothed<amax(smoothed)*0.1)
    DSAVE("1thresh",thresh)
    # find column edges by filtering
    grad = gaussian_filter(1.0*binary,(scale,scale*0.5),order=(0,1))
    grad = uniform_filter(grad,(10.0*scale,1))
    # grad = abs(grad) # use this for finding both edges
    grad = (grad>0.5*amax(grad))
    DSAVE("2grad",grad)
    # combine edges and whitespace
    seps = minimum(thresh,maximum_filter(grad,(int(scale),int(5*scale))))
    seps = maximum_filter(seps,(int(2*scale),1))
    DSAVE("3seps",seps)
    # select only the biggest column separators
    seps = morph.select_regions(seps,sl.dim0,min=args['csminheight']*scale,nbest=args['maxcolseps'])
    DSAVE("4seps",seps)
    return seps

def compute_colseps(binary,scale):
    """Computes column separators either from vertical black lines or whitespace."""
    logger.info("considering at most %g whitespace column separators" % args['maxcolseps'])
    colseps = compute_colseps_conv(binary,scale)
    DSAVE("colwsseps",0.7*colseps+0.3*binary)
    
    logger.info("considering at most %g black column separators" % args['maxseps'])
    seps = compute_separators_morph(binary,scale)
    DSAVE("colseps",0.7*seps+0.3*binary)
    colseps = maximum(colseps,seps)
    binary = minimum(binary,1-seps)
    return colseps,binary



################################################################
### Text Line Finding.
###
### This identifies the tops and bottoms of text lines by
### computing gradients and performing some adaptive thresholding.
### Those components are then used as seeds for the text lines.
################################################################

def compute_gradmaps(binary,scale):
    # use gradient filtering to find baselines
    boxmap = psegutils.compute_boxmap(binary,scale)
    cleaned = boxmap*binary
    DSAVE("cleaned",cleaned)
    if args['usegause']:
        # this uses Gaussians
        grad = gaussian_filter(1.0*cleaned,(args['vscale']*0.3*scale,
                                            args['hscale']*6*scale),order=(1,0))
    else:
        # this uses non-Gaussian oriented filters
        grad = gaussian_filter(1.0*cleaned,(max(4,args['vscale']*0.3*scale),
                                            args['hscale']*scale),order=(1,0))
        grad = uniform_filter(grad,(args['vscale'],args['hscale']*6*scale))
    bottom = ocrolib.norm_max((grad<0)*(-grad))
    top = ocrolib.norm_max((grad>0)*grad)
    return bottom,top,boxmap

def compute_line_seeds(binary,bottom,top,colseps,scale):
    """Base on gradient maps, computes candidates for baselines
    and xheights.  Then, it marks the regions between the two
    as a line seed."""
    t = args['threshold']
    vrange = int(args['vscale']*scale)
    bmarked = maximum_filter(bottom==maximum_filter(bottom,(vrange,0)),(2,2))
    bmarked = bmarked*(bottom>t*amax(bottom)*t)*(1-colseps)
    tmarked = maximum_filter(top==maximum_filter(top,(vrange,0)),(2,2))
    tmarked = tmarked*(top>t*amax(top)*t/2)*(1-colseps)
    tmarked = maximum_filter(tmarked,(1,20))
    seeds = zeros(binary.shape,'i')
    delta = max(3,int(scale/2))
    for x in range(bmarked.shape[1]):
        transitions = sorted([(y,1) for y in find(bmarked[:,x])]+[(y,0) for y in find(tmarked[:,x])])[::-1]
        transitions += [(0,0)]
        for l in range(len(transitions)-1):
            y0,s0 = transitions[l]
            if s0==0: continue
            seeds[y0-delta:y0,x] = 1
            y1,s1 = transitions[l+1]
            if s1==0 and (y0-y1)<5*scale: seeds[y1:y0,x] = 1
    seeds = maximum_filter(seeds,(1,int(1+scale)))
    seeds = seeds*(1-colseps)
    DSAVE("lineseeds",[seeds,0.3*tmarked+0.7*bmarked,binary])
    seeds,_ = morph.label(seeds)
    return seeds



################################################################
### The complete line segmentation process.
################################################################

def remove_hlines(binary,scale,maxsize=10):
    labels,_ = morph.label(binary)
    objects = morph.find_objects(labels)
    for i,b in enumerate(objects):
        if sl.width(b)>maxsize*scale:
            labels[b][labels[b]==i+1] = 0
    return array(labels!=0,'B')

def compute_segmentation(binary,scale):
    """Given a binary image, compute a complete segmentation into
    lines, computing both columns and text lines."""
    binary = array(binary,'B')

    # start by removing horizontal black lines, which only
    # interfere with the rest of the page segmentation
    binary = remove_hlines(binary,scale)

    # do the column finding
    if not args['quiet']: logger.info("computing column separators")
    colseps,binary = compute_colseps(binary,scale)

    # now compute the text line seeds
    if not args['quiet']: logger.info("computing lines")
    bottom,top,boxmap = compute_gradmaps(binary,scale)
    seeds = compute_line_seeds(binary,bottom,top,colseps,scale)
    DSAVE("seeds",[bottom,top,boxmap])

    # spread the text line seeds to all the remaining
    # components
    if not args['quiet']: logger.info("propagating labels")
    llabels = morph.propagate_labels(boxmap,seeds,conflict=0)
    if not args['quiet']: logger.info("spreading labels")
    spread = morph.spread_labels(seeds,maxdist=scale)
    llabels = where(llabels>0,llabels,spread*binary)
    segmentation = llabels*binary
    return segmentation



################################################################
### Processing each file.
################################################################

def process(image):
    imagename_base, ext = os.path.splitext(str(image))
    outputdir = os.path.join(dataDir, imagename_base)

    try:
        binary = ocrolib.read_image_binary(image)
    except IOError:
        if ocrolib.trace: traceback.print_exc()
        logger.error("cannot open %s" % (image))
        return

    checktype(binary,ABINARY2)

    if not args['nocheck']:
        check = check_page(amax(binary)-binary)
        if check is not None:
            logger.error("%s SKIPPED %s (use -n to disable this check)" % (image, check))
            return

    binary = 1-binary # invert

    if args['scale']==0:
        scale = psegutils.estimate_scale(binary)
    else:
        scale = args['scale']
    logger.info("scale %f" % (scale))
    if isnan(scale) or scale>1000.0:
        logger.error("%s: bad scale (%g); skipping\n" % (image, scale))
        return
    if scale<args['minscale']:
        logger.error("%s: scale (%g) less than --minscale; skipping\n" % (image, scale))
        return

    # find columns and text lines
    if not args['quiet']: logger.info("computing segmentation")
    segmentation = compute_segmentation(binary,scale)
    if amax(segmentation)>args['maxlines']:
        logger.error("%s: too many lines %g" % (image, amax(segmentation)))
        return
    if not args['quiet']: logger.info("number of lines %g" % amax(segmentation))

    # compute the reading order
    if not args['quiet']: logger.info("finding reading order")
    lines = psegutils.compute_lines(segmentation,scale)
    order = psegutils.reading_order([l.bounds for l in lines])
    lsort = psegutils.topsort(order)

    # renumber the labels so that they conform to the specs
    nlabels = amax(segmentation)+1
    renumber = zeros(nlabels,'i')
    for i,v in enumerate(lsort): renumber[lines[v].label] = 0x010000+(i+1)
    segmentation = renumber[segmentation]

    # finally, output everything
    if not args['quiet']: logger.info("writing lines")
    if not os.path.exists(outputdir):
        os.mkdir(outputdir)
    lines = [lines[i] for i in lsort]
    #ocrolib.write_page_segmentation("%s.pseg.png"%outputdir,segmentation)
    cleaned = ocrolib.remove_noise(binary,args['noise'])

    ### Return image files list (in disk)
    # write into output list
    output_list = []
    outputpath_base = os.path.join(outputdir,imagename_base)
    for i,l in enumerate(lines):
        binline = psegutils.extract_masked(1-cleaned,l,pad=args['pad'],expand=args['expand'])
        output_line = outputpath_base + "_%d.png" % (i+1)
        ocrolib.write_image_binary(output_line, binline)
        output_list.append(output_line)
    logger.info("%6d  %s %4.1f %d" % (i, image,  scale,  len(lines)))
    return output_list
    """

    ### Return image objects dictionary (in memory)
    output_dic = {}  # key: line NO. value: single-line image object
    for index, line in enumerate(lines):
        binline = psegutils.extract_masked(1-cleaned,line,pad=args['pad'],expand=args['expand'])
        assert binline.ndim==2
        midrange = 0.5*(amin(binline)+amax(binline))
        image_array = array(255*(binline>midrange),'B')
        image_pil = ocrolib.array2pil(image_array)
        output_dic[index] = image_pil
    logger.info("%6d  %s %4.1f %d" % (i, image,  scale,  len(lines)))
    print("=== dic ===")
    print(output_dic)
    return output_dic
    """
