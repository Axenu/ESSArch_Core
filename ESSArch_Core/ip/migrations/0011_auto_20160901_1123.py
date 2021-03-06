"""
    ESSArch is an open source archiving and digital preservation system

    ESSArch Core
    Copyright (C) 2005-2017 ES Solutions AB

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program. If not, see <http://www.gnu.org/licenses/>.

    Contact information:
    Web - http://www.essolutions.se
    Email - essarch@essolutions.se
"""

# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2016-09-01 11:23
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
import uuid

def forwards_func(apps, schema_editor):
    InformationPackage = apps.get_model("ip", "InformationPackage")
    db_alias = schema_editor.connection.alias

    for ip in InformationPackage.objects.using(db_alias).all():
        try:
            ip.ArchivalInstitution = uuid.uuid4()
        except:
            pass

        try:
            ip.ArchivistOrganization = uuid.uuid4()
        except:
            pass

        try:
            ip.ArchivalType = uuid.uuid4()
        except:
            pass

        try:
            ip.ArchivalLocation = uuid.uuid4()
        except:
            pass

        ip.save()

def reverse_func(apps, schema_editor):
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('ip', '0010_remove_informationpackage_status'),
    ]

    operations = [
        migrations.RunPython(forwards_func, reverse_func),
        migrations.CreateModel(
            name='ArchivalInstitution',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
            ],
            options={
                'verbose_name': 'ArchivalInstitution',
            },
        ),
        migrations.CreateModel(
            name='ArchivalLocation',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
            ],
            options={
                'verbose_name': 'ArchivalLocation',
            },
        ),
        migrations.CreateModel(
            name='ArchivalType',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
            ],
            options={
                'verbose_name': 'ArchivalType',
            },
        ),
        migrations.CreateModel(
            name='ArchivistOrganization',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
            ],
            options={
                'verbose_name': 'ArchivistOrganization',
            },
        ),
        migrations.AlterField(
            model_name='informationpackage',
            name='ArchivalInstitution',
            field=models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='information_packages', to='ip.ArchivalInstitution'),
        ),
        migrations.AlterField(
            model_name='informationpackage',
            name='ArchivalLocation',
            field=models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='information_packages', to='ip.ArchivalLocation'),
        ),
        migrations.AlterField(
            model_name='informationpackage',
            name='ArchivalType',
            field=models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='information_packages', to='ip.ArchivalType'),
        ),
        migrations.AlterField(
            model_name='informationpackage',
            name='ArchivistOrganization',
            field=models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='information_packages', to='ip.ArchivistOrganization'),
        ),
    ]
