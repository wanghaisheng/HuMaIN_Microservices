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
import time, argparse, os, sys, subprocess


### Validation and receive parameters
def valid_and_receive_args():
	parser = argparse.ArgumentParser("Call OCRopy Binarization Service")

	parser.add_argument('image')
	parser.add_argument('-o','--output',default=None,help="output directory, without the last slash")
	parser.add_argument('-t','--threshold',type=float,default=0.5,help='threshold, determines lightness, default: %(default)s')
	parser.add_argument('-z','--zoom',type=float,default=0.5,help='zoom for page background estimation, smaller=faster, default: %(default)s')
	parser.add_argument('-e','--escale',type=float,default=1.0,help='scale for estimating a mask over the text region, default: %(default)s')
	parser.add_argument('-b','--bignore',type=float,default=0.1,help='ignore this much of the border for threshold estimation, default: %(default)s')
	parser.add_argument('-p','--perc',type=float,default=80,help='percentage for filters, default: %(default)s')
	parser.add_argument('-r','--range',type=int,default=20,help='range for filters, default: %(default)s')
	parser.add_argument('-m','--maxskew',type=float,default=2,help='skew angle estimation parameters (degrees), default: %(default)s')
	parser.add_argument('--lo',type=float,default=5,help='percentile for black estimation, default: %(default)s')
	parser.add_argument('--hi',type=float,default=90,help='percentile for white estimation, default: %(default)s')
	parser.add_argument('--skewsteps',type=int,default=8,help='steps for skew angle estimation (per degree), default: %(default)s')

	args = parser.parse_args()

	### The existence of the source image is verified
	if not os.path.isfile(args.image):
		print("Error: File %s was not found" % (imagepath))
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


def call_bin(imagepath, dstDir, parameters):
	url_bin = 'http://10.5.146.92:8001/binarizationapi'

	# Uploaded iamges
	image = {'image': open(imagepath, 'rb')}

	# Call binarization service
	resp = requests.get(url_bin, files=image, data=parameters, stream=True)

	# Save the responsed binarized image
	image = os.path.basename(imagepath)
	image_name, image_ext = os.path.splitext(image)
	dstimage = image_name + ".bin.png"
	dstpath = ""
	if dstDir is None:
		# If dst folder is none, save output image to current directory
		dstpath = os.path.join(os.getcwd(), dstimage)
	else:
		dstpath = os.path.join(dstDir, dstimage)

	if resp.status_code == 200:
		with open(dstpath, 'wb') as fd:
			for chunk in resp:
				fd.write(chunk)
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

	### Call binarization service
	call_bin(imagepath, dstDir, args)

	print("\n--- %s seconds ---" % (time.time() - start_time))