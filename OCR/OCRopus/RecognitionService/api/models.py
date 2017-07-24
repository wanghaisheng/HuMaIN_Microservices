# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from django.conf import settings
from .extrafunc import validate_image_extension


### The parameters that can be set by an service API call
class Parameters(models.Model):
	image = models.ImageField(upload_to='', null=True, help_text="the uploaded image need to be binarized", validators=[validate_image_extension])
	# line dewarping (usually contained in model)
	height = models.IntegerField(default=-1, help_text="target line height (overrides recognizer)")
    # recognition
	pad = models.IntegerField(default=16, help_text="extra blank padding to the left and right of text line")
	nonormalize = models.BooleanField(default=False, help_text="don't normalize the textual output from the recognizer")
	llocs = models.BooleanField(default=False, help_text="output LSTM locations for characters")
	probabilities = models.BooleanField(default=False, help_text="output probabilities for each letter")
	
	#parallel = models.IntegerField(default=1, help_text="number of parallel CPUs to use")