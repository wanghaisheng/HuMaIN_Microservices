# -*- coding: utf-8 -*-
##########################################################################################
# Developer: Luan,Jingchao        Project: HuMaIN (http://humain.acis.ula.ve)
# Description: 
#	Given the segmented (single-line) images' directory to variable 'imageDir', the script 
# will call OCR recognition microservice for each image file in the directory
#	It will return a folder containing the outputs of recognition service.
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
	parser = argparse.ArgumentParser("Call OCRopy Recognition Service")

	parser.add_argument('image')
	parser.add_argument('-o','--output',default=None,help="output directory, without the last slash")
	parser.add_argument('-m','--model',default=None, help="line recognition model")
	parser.add_argument("-l","--height",default=-1,type=int, help="target line height (overrides recognizer)")
	parser.add_argument("-p","--pad",default=16,type=int, help="extra blank padding to the left and right of text line")
	parser.add_argument('-N',"--nonormalize",action="store_true", help="don't normalize the textual output from the recognizer")
	parser.add_argument('--llocs',action="store_true", help="output LSTM locations for characters")
	parser.add_argument('--probabilities',action="store_true",help="output probabilities for each letter")

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


### Call recognition service
def call_recog(imagepath, dstDir, parameters):
	url_recog = 'http://10.5.146.92:8003/recognitionapi'

	# Uploaded iamges
	multiple_files = [('image', (imagepath, open(imagepath, 'rb')))]
	if parameters['model'] is not None:
		multiple_files.append(('model', (parameters['model'], open(parameters['model'], 'rb'))))
	del parameters['model']
	# Call recognition service and get response
	resp = requests.get(url_recog, files=multiple_files, data=parameters)

	# If user didn't provide dst folder, save output to current directory
	if dstDir is None:
		dstDir = os.getcwd()

	# Unpress the zip file responsed from recognition service
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

	### Call recognition service
	call_recog(imagepath, dstDir, args)

	print("\n--- %s seconds ---" % (time.time() - start_time))
