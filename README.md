# HuMaIN_Microservices
Reusable information extraction and data processing microservices. Based on [OCRopus](https://github.com/tmbdev/ocropy) and its library [ocrolib](https://github.com/tmbdev/ocropy/tree/master/ocrolib)

## Setting Up
1. Start and activate environment

	```
	$ virtualenv env
	$ source env/bin/activate
	```

2. Install requirement packages
	
	```
	$ pip install -r requirements.txt
	```
	Note: Install one time under directory '/HuMaIN_Microservices/OCR/OCRopus/' for testing, or install three times under each 	microservice directory like '/HuMaIN_Microservices/OCR/OCRopus/BinarizationService/' for deployment.

3. Run each microservice respectively

	For Binarization microservice: (under directory '/OCR/OCRopus/BinarizationService/')
	```
	$ python manage.py runserver 0.0.0.0:8001
	```
	For Segmentation microservice: (under directory '/OCR/OCRopus/SegmentationService/')
	```
	$ python manage.py runserver 0.0.0.0:8002
	```
	For Recognition microservice:  (under directory '/OCR/OCRopus/RecognitionService/')
	```
	$ python manage.py runserver 0.0.0.0:8003
	```
