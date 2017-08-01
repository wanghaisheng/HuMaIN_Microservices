# -*- coding: utf-8 -*-
##########################################################################################
# Developer: Luan,Jingchao        Project: HuMaIN (http://humain.acis.ula.ve)
# Description: 
#	Given the original images' directory to variable 'imageDir', the script will call OCR 
# binarization microservice for each image file in the directory. 
#	It will return a folder containing the outputs of binarization service.
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


import requests, zipfile, StringIO
import time, argparse, os, sys, subprocess, shutil


# These two constant values are same with the output folder name of related service 
# Must keep the same values
OUT_FOLDER_SEG = "output_segmentation"
OUT_FOLDER_RECOG = "output_recognition"

### Transfer string to boolean
def str2bool(v):
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')


"""
Receive and validate parameters.
Separate parameters set by user to 3 parameters dictionaries related to the 3 services respectively
Return parameters dictionary set by users, and the 3 separeted parameters dictionaries
"""
### Set settable parameters and receive parameters set by user
parser = argparse.ArgumentParser("Call OCRopy microervices")

parser.add_argument('image', help = "The path of a image file, or a folder containing all pre-process images.")
parser.add_argument('-o','--output', required=True, help="output directory, without the last slash")
		
### Binarization parameters (#10)
group_bin = parser.add_argument_group(title="group_bin", description="Call OCRopy binarization microervices")
group_bin.add_argument('--threshold_bin',type=float,default=argparse.SUPPRESS,help='threshold, determines lightness')
group_bin.add_argument('--zoom',type=float,default=argparse.SUPPRESS,help='zoom for page background estimation, smaller=faster')
group_bin.add_argument('--escale',type=float,default=argparse.SUPPRESS,help='scale for estimating a mask over the text region')
group_bin.add_argument('--bignore',type=float,default=argparse.SUPPRESS,help='ignore this much of the border for threshold estimation')
group_bin.add_argument('--perc',type=float,default=argparse.SUPPRESS,help='percentage for filters')
group_bin.add_argument('--range',type=int,default=argparse.SUPPRESS,help='range for filters')
group_bin.add_argument('--maxskew',type=float,default=argparse.SUPPRESS,help='skew angle estimation parameters (degrees)')
group_bin.add_argument('--lo',type=float,default=argparse.SUPPRESS,help='percentile for black estimation')
group_bin.add_argument('--hi',type=float,default=argparse.SUPPRESS,help='percentile for white estimation')
group_bin.add_argument('--skewsteps',type=int,default=argparse.SUPPRESS,help='steps for skew angle estimation (per degree)')

### Segmentation parameters (#12)
group_seg = parser.add_argument_group(title="group_seg", description='segmentation parameters')
group_seg.add_argument('--minscale',type=float,default=argparse.SUPPRESS, help='minimum scale permitted')
group_seg.add_argument('--maxlines',type=float,default=argparse.SUPPRESS, help='maximum # lines permitted')
group_seg.add_argument('--scale',type=float,default=argparse.SUPPRESS, help='the basic scale of the document (roughly, xheight) 0=automatic')
group_seg.add_argument('--hscale',type=float,default=argparse.SUPPRESS, help='non-standard scaling of horizontal parameters')
group_seg.add_argument('--vscale',type=float,default=argparse.SUPPRESS, help='non-standard scaling of vertical parameters')
group_seg.add_argument('--threshold_seg',type=float,default=argparse.SUPPRESS, help='baseline threshold')
group_seg.add_argument('--noise',type=int,default=argparse.SUPPRESS, help="noise threshold for removing small components from lines")
group_seg.add_argument('--usegauss',action='store_true', default=argparse.SUPPRESS, help='use gaussian instead of uniform')
group_seg.add_argument('--maxseps',type=int,default=argparse.SUPPRESS, help='maximum black column separators')
group_seg.add_argument('--sepwiden',type=int,default=argparse.SUPPRESS, help='widen black separators (to account for warping)')
group_seg.add_argument('--maxcolseps',type=int,default=argparse.SUPPRESS, help='maximum # whitespace column separators')
group_seg.add_argument('--csminheight',type=float,default=argparse.SUPPRESS, help='minimum column height (units=scale)')
	
### Recognition parameters (#6)
group_recog = parser.add_argument_group(title="group_recog", description='recognition parameters')
group_recog.add_argument('--model',default=argparse.SUPPRESS, help="line recognition model")
group_recog.add_argument('--height',default=argparse.SUPPRESS,type=int, help="target line height (overrides recognizer)")
group_recog.add_argument('--pad',default=argparse.SUPPRESS,type=int, help="extra blank padding to the left and right of text line")
group_recog.add_argument('--nonormalize',type=str2bool, default=argparse.SUPPRESS, help="don't normalize the textual output from the recognizer")
group_recog.add_argument('--llocs',type=str2bool, default=argparse.SUPPRESS, help="output LSTM locations for characters")
group_recog.add_argument('--probabilities', type=str2bool, default=argparse.SUPPRESS, help="output probabilities for each letter")

args = parser.parse_args()
args = vars(args)


### Validate or create the destination folder
if not os.path.isdir(args['output']):
	subprocess.call(["mkdir -p " + args['output']], shell=True)
	if not os.path.isdir(args['output']):
		print("Error: Destination folder %s could not be created" % (args['output']))
		sys.exit(0)

### Settable parameters list for each microservice
paras_bin = []
paras_seg = []
paras_recog = []
for para in group_bin._group_actions:
	paras_bin.append(para.dest)
for para in group_seg._group_actions:
	paras_seg.append(para.dest)
for para in group_recog._group_actions:
	paras_recog.append(para.dest)

### Separete arguments set by user for each microservice
args_bin = {}
args_seg = {}
args_recog = {}
for arg in args.keys():
	if arg in paras_recog: args_recog[arg] = args.get(arg)
	elif arg in paras_seg: args_seg[arg] = args.get(arg)
	elif arg in paras_bin: args_bin[arg] = args.get(arg)
	else: pass

print(args)
print("====== set binarization parameters ======")
print(args_bin)
print("====== set segmentation parameters ======")
print(args_seg)
print("====== set recognition parameters  ======")
print(args_recog)
print("=========================================\n")

### Transfer parameter 'threshold_bin' and 'threshold_seg' to 'threshold' which is same with parameter key in service
if 'threshold_bin' in args_bin.keys():
	args_bin['threshold'] = args_bin.get('threshold_bin')
	del args_bin['threshold_bin']
if 'threshold_seg' in args_seg.keys():
	args_seg['threshold'] = args_seg.get('threshold_seg')
	del args_seg['threshold_seg']


"""
Call binarization microservice and return the path of the binarized image
""" 
def call_bin(imagepath, dstDir, parameters):
	url_bin = 'http://10.5.146.92:8001/binarizationapi'

	# Uploaded iamges
	image = {'image': open(imagepath, 'rb')}

	# Call binarization service
	resp = requests.get(url_bin, files=image, data=parameters, stream=True)

	# Save the responsed binarized image
	image = os.path.basename(imagepath)
	image_name, image_ext = os.path.splitext(image)
	output_image = image_name + ".bin.png"
	output_imagepath = ""
	output_imagepath = os.path.join(dstDir, output_image)

	if resp.status_code == 200:
		with open(output_imagepath, 'wb') as fd:
			for chunk in resp:
				fd.write(chunk)
	else:
		print("Image %s Binarization error!" % imagepath)
		#print("ERROR code: %d" % resp.status_code)
		#print(resp.content)

	return output_imagepath


"""
Call segmentation service and return the path of the segmented images
"""
def call_seg(imagepath, dstDir, parameters):
	url_seg = 'http://10.5.146.92:8002/segmentationapi'

	# Uploaded iamges
	image = {'image': open(imagepath, 'rb')}

	# Call segmentation service and get response
	resp = requests.get(url_seg, files=image, data=parameters)

	# Unpress the zip file responsed from segmentation service, and save it
	if resp.status_code == 200:
		# For python 3+, replace with io.BytesIO(resp.content)
		z = zipfile.ZipFile(StringIO.StringIO(resp.content)) 
		z.extractall(dstDir) 
	else:
		print("Image %s Segmentation error!" % imagepath)
		#print("ERROR code: %d" % resp.status_code)
		#print(resp.content)

	output_list = []
	output_dir = os.path.join(dstDir, OUT_FOLDER_SEG)
	for line_image in os.listdir(output_dir):
		image_path = os.path.join(output_dir, line_image)
		output_list.append(image_path)

	return output_list


"""
Call recognition service and return the path of the recognized file and 
maybe return other files according to parameters set by user
"""
def call_recog(imagepath, dstDir, parameters):
	url_recog = 'http://10.5.146.92:8003/recognitionapi'

	# Uploaded iamges
	multiple_files = [('image', (imagepath, open(imagepath, 'rb')))]
	if 'model' in parameters.keys():
		multiple_files.append(('model', (parameters['model'], open(parameters['model'], 'rb'))))
		del parameters['model']
	# Call recognition service and get response
	resp = requests.get(url_recog, files=multiple_files, data=parameters)

	# Unpress the zip file responsed from recognition service
	if resp.status_code == 200:
		# For python 3+, replace with io.BytesIO(resp.content)
		z = zipfile.ZipFile(StringIO.StringIO(resp.content)) 
		z.extractall(dstDir) 
	else:
		print("Image %s Recognition error!" % imagepath)
		#print(resp.content)


"""
Process the image by calling the 3 services and process the output files
"""
def process(image):
	image_origin = image
	dstDir = args['output']

	### Call binarization service
	image_bined = call_bin(image_origin, dstDir, args_bin)

	### Call segmentation service
	images_list_seged= call_seg(image_bined, dstDir, args_seg)

	### Call recognition service
	for image_seged in images_list_seged:
		call_recog(image_seged, dstDir, args_recog)
	files_list_recoged = []
	output_dir = os.path.join(dstDir, OUT_FOLDER_RECOG)
	for file in os.listdir(output_dir):
		file_path = os.path.join(output_dir, file)
		files_list_recoged.append(file_path)

	### For each original image, combine its recognized single-line files into one file
	# Separate the output files of recognition service into different lists according to its extension
	recoged_text_list = []
	recoged_prob_list = []
	recoged_llocs_list = []
	for file_recoged in files_list_recoged:
		if file_recoged.endswith('.txt'): recoged_text_list.append(file_recoged)
		elif file_recoged.endswith('.prob'): recoged_prob_list.append(file_recoged)
		elif file_recoged.endswith('.llocs'): recoged_llocs_list.append(file_recoged)
		else: pass
	
	image_name, ext = os.path.splitext(os.path.basename(image_origin))
	# Combine text files
	output_text_path = os.path.join(dstDir, image_name)+".txt"
	recoged_text_list.sort()
	with open(output_text_path, "wb") as outfile:
		for file in recoged_text_list:
			with open(file, "rb") as infile:
				outfile.write(infile.read())
				infile.close()
	outfile.close()

	# Combine probabilities files
	if recoged_prob_list:
		output_prob_path = os.path.join(dstDir, image_name)+".prob"
		recoged_prob_list.sort()
		with open(output_prob_path, "wb") as outfile:
			for file in recoged_prob_list:
				with open(file, "rb") as infile:
					outfile.write(infile.read())
					infile.close()
		outfile.close()

    # Combine llocs files
	if recoged_llocs_list:
		output_llocs_path = os.path.join(dstDir, image_name)+".llocs"
		recoged_llocs_list.sort()
		with open(output_llocs_path, "wb") as outfile:
			for file in recoged_llocs_list:
				with open(file, "rb") as infile:
					outfile.write(infile.read())
					infile.close()
		outfile.close()

	### Delete all intermediate output
	os.unlink(image_bined)
	shutil.rmtree(os.path.join(dstDir, OUT_FOLDER_SEG))
	shutil.rmtree(os.path.join(dstDir, OUT_FOLDER_RECOG))


if __name__ == '__main__':
	start_time = time.time()

	# Process one image, or process all images inside a folder
	if os.path.isfile(args['image']):
		process(args['image'])
	elif os.path.isdir(args['image']):
		for image in os.listdir(args['image']):
			image_path = os.path.join(args['image'], image)
			# One image fail do not affect the process of other images
			try:
				process(image_path)
			except:
				pass

	print("\n--- %s seconds ---" % (time.time() - start_time))