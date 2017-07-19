# -*- coding: utf-8 -*-
from rest_framework import serializers
from api.models import Parameters

class ParameterSerializer(serializers.ModelSerializer):
	class Meta:
		model = Parameters
		fields = ('id', 'height', 'pad', 'nonormalize', 'llocs', 'probabilities', 'parallel')