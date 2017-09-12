# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2017-09-05 17:35
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0005_auto_20170723_2100'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='parameters',
            name='image',
        ),
        migrations.AlterField(
            model_name='parameters',
            name='maxseps',
            field=models.IntegerField(default=0, help_text='maximum # black column separators'),
        ),
    ]