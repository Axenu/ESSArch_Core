# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-03-06 11:12
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('ip', '0030_auto_20170224_1149'),
    ]

    operations = [
        migrations.AlterField(
            model_name='informationpackage',
            name='policy',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='information_packages', to='configuration.ArchivePolicy'),
        ),
    ]
