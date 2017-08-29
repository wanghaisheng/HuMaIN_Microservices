# -*- coding: utf-8 -*-
##########################################################################################
# Developer: Luan,Jingchao        Project: HuMaIN (http://humain.acis.ufl.edu)
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

start_time = time.time()

### Validation and receive parameters
parser = argparse.ArgumentParser("Call OCRopy Binarization Service")

parser.add_argument('image', help="The path of a image file, or a folder containing all pre-process images.")
parser.add_argument('-o','--output',default=None, help="output directory, without the last slash")
parser.add_argument('-t','--threshold',type=float, default=argparse.SUPPRESS, help='threshold, determines lightness')
parser.add_argument('-z','--zoom',type=float,default=argparse.SUPPRESS, help='zoom for page background estimation, smaller=faster')
parser.add_argument('-e','--escale',type=float,default=argparse.SUPPRESS, help='scale for estimating a mask over the text region')
parser.add_argument('-b','--bignore',type=float,default=argparse.SUPPRESS, help='ignore this much of the border for threshold estimation')
parser.add_argument('-p','--perc',type=float,default=argparse.SUPPRESS, help='percentage for filters')
parser.add_argument('-r','--range',type=int,default=argparse.SUPPRESS, help='range for filters')
parser.add_argument('-m','--maxskew',type=float,default=argparse.SUPPRESS, help='skew angle estimation parameters (degrees)')
parser.add_argument('--lo',type=float,default=argparse.SUPPRESS, help='percentile for black estimation')
parser.add_argument('--hi',type=float,default=argparse.SUPPRESS, help='percentile for white estimation')
parser.add_argument('--skewsteps',type=int,default=argparse.SUPPRESS, help='steps for skew angle estimation (per degree)')

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


def call_bin(imagepath, dstDir, parameters):
	url_bin = 'http://localhost:8001/binarizationapi'

	# Uploaded iamges
	image = {'image': open(imagepath, 'rb')}

	# Call binarization service
	#print("*** Send request: %.4f ***" % time.time())
	call_begin = time.time()
	resp = requests.get(url_bin, files=image, data=parameters, stream=True)
	print("*** Bin service time: %.4f ***" % (time.time()-call_begin))

	# Save the responsed binarized image
	image = os.path.basename(imagepath)
	image_name, image_ext = os.path.splitext(image)
	dstimage = image_name + ".bin.png"
	dstpath = os.path.join(dstDir, dstimage)

	if resp.status_code == 200:
		with open(dstpath, 'wb') as fd:
			for chunk in resp:
				fd.write(chunk)
	else:
		print("Image %s Binarization error!" % imagepath)
		#print(resp.content)


if __name__ == '__main__':
	image = args['image']
	dstDir = args['output']

	### Only keep the setable parameters
	del args['image']
	del args['output']

	### Call binarization service
	if os.path.isfile(image):
		print("\n===== %s ======" % image)
		call_bin(image, dstDir, args)
	elif os.path.isdir(image):
		for image_name in os.listdir(image):
			image_path = os.path.join(image, image_name)
			# One image failed do not affect the process of other images
			try:
				print("\n========== %s ==========" % image_name)
				call_bin(image_path, dstDir, args)
			except:
				pass
	else:
		parser.print_help()
		sys.exit(0)
	
	print("--- Over all invoke time: %.4f seconds ---" % (time.time() - start_time))