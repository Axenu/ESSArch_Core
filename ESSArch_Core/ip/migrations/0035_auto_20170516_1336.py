# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2017-05-16 11:36
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ip', '0034_auto_20170509_1546'),
    ]

    operations = [
        migrations.AddField(
            model_name='informationpackage',
            name='archived',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='informationpackage',
            name='cached',
            field=models.BooleanField(default=False),
        ),
    ]
