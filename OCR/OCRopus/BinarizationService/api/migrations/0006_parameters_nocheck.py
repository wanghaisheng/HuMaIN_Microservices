# -*- coding: utf-8 -*-
# Generated by Django 1.11.2 on 2017-07-04 19:48
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0005_remove_parameters_image'),
    ]

    operations = [
        migrations.AddField(
            model_name='parameters',
            name='nocheck',
            field=models.BooleanField(default=True),
        ),
    ]