# -*- coding: utf-8 -*-
##########################################################################################
# Developer: Luan,Jingchao        Project: HuMaIN (http://humain.acis.ufl.edu)
# Description: 
#	Given the binarized images' directory to variable 'imageDir', the script will call OCR 
# segmentation microservice for each image file in the directory
#	It will return a folder containing the outputs of segmentation service.
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
import time, argparse, os, sys, subprocess

start_time = time.time()

### The server IP and PORT in lab ACIS deploying HuMaIN OCRopus microservices (Only accessable for ACIS members)
### Please Replace with your server IP when testing
IP = "10.5.146.92"
PORT = "8002"

### Transfer string to boolean
def str2bool(v):
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')
        

### Validation and receive parameters
parser = argparse.ArgumentParser("Call OCRopy Segmentation Service")

parser.add_argument('image', help="The path of a image file, or a folder containing all pre-process images.")

# output parameters
parser.add_argument('-o','--output', default=None, help="output directory, without the last slash")

# limits
group_limits = parser.add_argument_group('limits')
group_limits.add_argument('--minscale',type=float,default=argparse.SUPPRESS, help='minimum scale permitted')
group_limits.add_argument('--maxlines',type=float,default=argparse.SUPPRESS, help='maximum # lines permitted')

# scale parameters
group_scale = parser.add_argument_group('scale parameters')
group_scale.add_argument('--scale',type=float,default=argparse.SUPPRESS, help='the basic scale of the document (roughly, xheight) 0=automatic')
group_scale.add_argument('--hscale',type=float,default=argparse.SUPPRESS, help='non-standard scaling of horizontal parameters')
group_scale.add_argument('--vscale',type=float,default=argparse.SUPPRESS, help='non-standard scaling of vertical parameters')

# line parameters
group_line = parser.add_argument_group('line parameters')
group_line.add_argument('--threshold',type=float,default=argparse.SUPPRESS, help='baseline threshold')
group_line.add_argument('--noise',type=int,default=argparse.SUPPRESS, help="noise threshold for removing small components from lines")
group_line.add_argument('--usegauss', type=str2bool, help='use gaussian instead of uniform')

# column parameters
group_column = parser.add_argument_group('column parameters')
group_column.add_argument('--maxseps',type=int,default=argparse.SUPPRESS, help='maximum black column separators')
group_column.add_argument('--sepwiden',type=int,default=argparse.SUPPRESS, help='widen black separators (to account for warping)')
group_column.add_argument('--maxcolseps',type=int,default=argparse.SUPPRESS, help='maximum # whitespace column separators')
group_column.add_argument('--csminheight',type=float,default=argparse.SUPPRESS, help='minimum column height (units=scale)')


args = parser.parse_args()

### The existence of the destination folder is verified or created
if args.output is None:
	# If output folder is not set, save output image to current directory
	args.output = os.getcwd()
else:
	if not os.path.isdir(args.output):
		subprocess.call(["mkdir -p " + args.output], shell=True)
		if not os.path.isdir(args.output):
			print("Error: Destination folder %s could not be created" % (args.output))
			sys.exit(0)

args = vars(args)

### Call segmentation service
def call_seg(imagepath, dstDir, parameters):
	url_seg = "http://" + IP + ":" + PORT + "/segmentationapi"

	# Uploaded iamges
	image = {'image': open(imagepath, 'rb')}

	# Call segmentation service and get response
	image_dir, image_name = os.path.split(imagepath)
	call_begin = time.time()
	resp = requests.get(url_seg, files=image, data=parameters)
	print("*** Segmentation service time: %.2f seconds***" % (time.time()-call_begin))

	# Unpress the zip file responsed from segmentation service, and save it
	if resp.status_code == 200:
		# For python 3+, replace with io.BytesIO(resp.content)
		z = zipfile.ZipFile(StringIO.StringIO(resp.content)) 
		z.extractall(dstDir)
		unzip_end = time.time()
	else:
		print("Image %s Segmentation error!" % image_name)
		#print(resp.content)
		return

if __name__ == '__main__':
	image = args['image']
	dstDir = args['output']

	### Only keep the setable parameters
	del args['image']
	del args['output']

	### Call segmentation service
	if os.path.isfile(image):
		print("\n===== %s ======" % image)
		call_seg(image, dstDir, args)
	elif os.path.isdir(image):
		for image_name in os.listdir(image):
			image_path = os.path.join(image, image_name)
			# One image failed do not affect the process of other images
			try:
				print("\n===== %s ======" % image)
				call_seg(image_path, dstDir, args)
			except:
				pass
	else:
		parser.print_help()
		sys.exit(0)

	print("*** Over all invoke time: %.2f seconds ***\n" % (time.time() - start_time))
