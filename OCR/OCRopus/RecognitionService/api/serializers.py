# -*- coding: utf-8 -*-
from rest_framework import serializers
from api.models import Parameters

class ParameterSerializer(serializers.ModelSerializer):
	#image = serializers.ImageField(max_length=None, use_url=True,)
	class Meta:
		model = Parameters
		fields = ('id', 'height', 'pad', 'nonormalize', 'llocs', 'probabilities')