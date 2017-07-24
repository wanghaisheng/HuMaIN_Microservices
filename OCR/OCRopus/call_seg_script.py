# -*- coding: utf-8 -*-
##########################################################################################
# Developer: Luan,Jingchao        Project: HuMaIN (http://humain.acis.ula.ve)
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


### Validation and receive parameters
def valid_and_receive_args():
	parser = argparse.ArgumentParser("Call OCRopy Segmentation Service")

	parser.add_argument('image')

	# output parameters
	parser.add_argument('-o','--output',default=None,help="output directory, without the last slash")
	
	# limits
	group_limits = parser.add_argument_group('limits')
	group_limits.add_argument('--minscale',type=float,default=1.0,
	                    help='minimum scale permitted, default: %(default)s')
	group_limits.add_argument('--maxlines',type=float,default=300,
	                    help='maximum # lines permitted, default: %(default)s')

	# scale parameters
	group_scale = parser.add_argument_group('scale parameters')
	group_scale.add_argument('--scale',type=float,default=0.0,
	                    help='the basic scale of the document (roughly, xheight) 0=automatic, default: %(default)s')
	group_scale.add_argument('--hscale',type=float,default=1.0,
	                    help='non-standard scaling of horizontal parameters, default: %(default)s')
	group_scale.add_argument('--vscale',type=float,default=1.0,
	                    help='non-standard scaling of vertical parameters, default: %(default)s')

	# line parameters
	group_line = parser.add_argument_group('line parameters')
	group_line.add_argument('--threshold',type=float,default=0.2,
	                    help='baseline threshold, default: %(default)s')
	group_line.add_argument('--noise',type=int,default=8,
	                    help="noise threshold for removing small components from lines, default: %(default)s")
	group_line.add_argument('--usegauss',action='store_true',
	                    help='use gaussian instead of uniform, default: %(default)s')

	# column parameters
	group_column = parser.add_argument_group('column parameters')
	group_column.add_argument('--maxseps',type=int,default=0,
	                    help='maximum black column separators, default: %(default)s')
	group_column.add_argument('--sepwiden',type=int,default=10,
	                    help='widen black separators (to account for warping), default: %(default)s')
	group_column.add_argument('--maxcolseps',type=int,default=3,
	                    help='maximum # whitespace column separators, default: %(default)s')
	group_column.add_argument('--csminheight',type=float,default=10,
	                    help='minimum column height (units=scale), default: %(default)s')


	args = parser.parse_args()

	### The existence of the source image is verified
	if not os.path.isfile(args.image):
		parser.print_help()
		sys.exit(0)

	### The existence of the destination folder is verified or created
	if args.output is not None:
		if not os.path.isdir(args.output):
			subprocess.call(["mkdir -p " + args.output], shell=True)
			if not os.path.isdir(args.output):
				print("Error: Destination folder %s could not be created" % (args.output))
				sys.exit(0)

	return vars(args)

### Call segmentation service
def call_seg(imagepath, dstDir, parameters):
	url_seg = 'http://10.5.146.92:8002/segmentationapi'

	# Uploaded iamges
	image = {'image': open(imagepath, 'rb')}

	# Call segmentation service and get response
	resp = requests.get(url_seg, files=image, data=parameters)

	# If user didn't provide dst folder, save output to current directory
	if dstDir is None:
		dstDir = os.getcwd()

	# Unpress the zip file responsed from segmentation service, and save it
	if resp.status_code == 200:
		# For python 3+, replace with io.BytesIO(resp.content)
		z = zipfile.ZipFile(StringIO.StringIO(resp.content)) 
		z.extractall(dstDir) 
	else:
		print("\nERROR code: %d" % resp.status_code)
		#print(resp.content)


if __name__ == '__main__':
	start_time = time.time()
	### validation and receive parameters
	args = valid_and_receive_args()

	imagepath = args['image']
	dstDir = args['output']

	### Only keep the setable parameters
	del args['image']
	del args['output']

	### Call segmentation service
	call_seg(imagepath, dstDir, args)

	print("\n--- %s seconds ---" % (time.time() - start_time))