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
# Generated by Django 1.10 on 2016-08-23 12:20
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('WorkflowEngine', '0036_auto_20160819_1354'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='event',
            name='archiveObject',
        ),
        migrations.RemoveField(
            model_name='event',
            name='type',
        ),
        migrations.RemoveField(
            model_name='profile',
            name='nationality',
        ),
        migrations.RemoveField(
            model_name='profile',
            name='submissionAgreement',
        ),
        migrations.AlterField(
            model_name='processstep',
            name='archiveobject',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='steps', to='ip.InformationPackage'),
        ),
        migrations.DeleteModel(
            name='ArchiveObject',
        ),
        migrations.DeleteModel(
            name='Event',
        ),
        migrations.DeleteModel(
            name='EventType',
        ),
        migrations.DeleteModel(
            name='Nationality',
        ),
        migrations.DeleteModel(
            name='Profile',
        ),
        migrations.DeleteModel(
            name='SubmissionAgreement',
        ),
    ]