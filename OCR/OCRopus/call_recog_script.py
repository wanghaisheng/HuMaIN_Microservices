# -*- coding: utf-8 -*-
##########################################################################################
# Developer: Luan,Jingchao        Project: HuMaIN (http://humain.acis.ufl.edu)
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

start_time = time.time()

### The server IP and PORT in lab ACIS deploying HuMaIN OCRopus microservices (Only accessable for ACIS members)
### Please Replace with your server IP when testing
IP = "10.5.146.92"
PORT = "8003"

### Transfer string to boolean
def str2bool(v):
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')


### Validation and receive parameters
parser = argparse.ArgumentParser("Call OCRopy Recognition Service")

parser.add_argument('image', help="The path of a image file, or a folder containing all pre-process images.")
parser.add_argument('-o','--output',default=None,help="output directory, without the last slash")
parser.add_argument('-m','--model',default=argparse.SUPPRESS, help="line recognition model")
parser.add_argument("-l","--height",default=argparse.SUPPRESS,type=int, help="target line height (overrides recognizer)")
parser.add_argument("-p","--pad",default=argparse.SUPPRESS,type=int, help="extra blank padding to the left and right of text line")
parser.add_argument('-N',"--nonormalize", type=str2bool, help="don't normalize the textual output from the recognizer")
parser.add_argument('--llocs', type=str2bool, help="output LSTM locations for characters")
parser.add_argument('--probabilities', type=str2bool, help="output probabilities for each letter")

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


### Call recognition service
def call_recog(imagepath, dstDir, parameters):
	url_recog = "http://" + IP + ":" + PORT + "/recognitionapi"

	# Uploaded iamges
	multiple_files = [('image', (imagepath, open(imagepath, 'rb')))]
	if 'model' in parameters.keys():
		multiple_files.append(('model', (parameters['model'], open(parameters['model'], 'rb'))))
		del parameters['model']
	# Call recognition service and get response
	iamge_dir, image_name = os.path.split(imagepath)
	call_begin = time.time()
	resp = requests.get(url_recog, files=multiple_files, data=parameters)
	print("*** Recognition service time: %.2f seconds***" % (time.time()-call_begin))

	# Unpress the zip file responsed from recognition service
	if resp.status_code == 200:
		# For python 3+, replace with io.BytesIO(resp.content)
		z = zipfile.ZipFile(StringIO.StringIO(resp.content)) 
		z.extractall(dstDir) 
		unzip_end = time.time()
	else:
		print("Image %s Recognition error!" % imagepath)
		#print(resp.content)
        return

if __name__ == '__main__':
	image = args['image']
	dstDir = args['output']

	### Only keep the setable parameters
	del args['image']
	del args['output']


	### Call recognition service
	if os.path.isfile(image):
		print("\n===== %s ======" % image)
		call_recog(image, dstDir, args)
	elif os.path.isdir(image):
		image_list = os.listdir(image)
		image_list.sort()
		for image_name in image_list:
			image_path = os.path.join(image, image_name)
			# One image failed do not affect the process of other images
			try:
				print("\n===== %s =====" % image_name)
				call_recog(image_path, dstDir, args)
			except:
				pass
	else:
		parser.print_help()
		sys.exit(0)

	print("*** Over all invoke time: %.2f seconds ***\n" % (time.time() - start_time))
