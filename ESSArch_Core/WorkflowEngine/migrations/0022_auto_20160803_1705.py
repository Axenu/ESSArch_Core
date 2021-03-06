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
# Generated by Django 1.9.8 on 2016-08-03 17:05
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('WorkflowEngine', '0021_auto_20160803_1628'),
    ]

    operations = [
        migrations.CreateModel(
            name='Nationality',
            fields=[
                ('name', models.CharField(max_length=128, primary_key=True, serialize=False)),
                ('shortname', models.CharField(max_length=2)),
            ],
            options={
                'db_table': 'Nationality',
            },
        ),
        migrations.CreateModel(
            name='Profile',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('state', models.CharField(choices=[(0, 'Unspecified'), (10, 'Complete')], default='Unspecified', max_length=255)),
                ('archivistOrganisation', models.CharField(max_length=255)),
                ('archivistOrganisationIdentity', models.CharField(max_length=255)),
                ('archivistOrganisationSoftware', models.CharField(max_length=255)),
                ('archivistOrganisationSoftwareIdentity', models.CharField(max_length=255)),
                ('creatorOrganisation', models.CharField(max_length=255)),
                ('creatorOrganisationIdentity', models.CharField(max_length=255)),
                ('creatorOrganisationSoftware', models.CharField(max_length=255)),
                ('creatorOrganisationSoftwareIdentity', models.CharField(max_length=255)),
                ('producerOrganisation', models.CharField(max_length=255)),
                ('producerIndividual', models.CharField(max_length=255)),
                ('producerOrganisationSoftware', models.CharField(max_length=255)),
                ('producerOrganisationSoftwareIdentity', models.CharField(max_length=255)),
                ('ipOwnerOrganisation', models.CharField(max_length=255)),
                ('ipOwnerIndividual', models.CharField(max_length=255)),
                ('ipOwnerOrganisationSoftware', models.CharField(max_length=255)),
                ('ipOwnerOrganisationSoftwareIdentity', models.CharField(max_length=255)),
                ('editorOrganisation', models.CharField(max_length=255)),
                ('editorIndividual', models.CharField(max_length=255)),
                ('editorOrganisationSoftware', models.CharField(max_length=255)),
                ('editorOrganisationSoftwareIdentity', models.CharField(max_length=255)),
                ('preservationOrganisation', models.CharField(max_length=255)),
                ('preservationIndividual', models.CharField(max_length=255)),
                ('preservationOrganisationSoftware', models.CharField(max_length=255)),
                ('preservationOrganisationSoftwareIdentity', models.CharField(max_length=255)),
                ('nationality', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='WorkflowEngine.Nationality')),
            ],
            options={
                'db_table': 'Profile',
            },
        ),
        migrations.CreateModel(
            name='SubmissionAgreement',
            fields=[
                ('name', models.CharField(max_length=128, primary_key=True, serialize=False)),
            ],
            options={
                'db_table': 'SubmissionAgreement',
            },
        ),
        migrations.AddField(
            model_name='profile',
            name='submissionAgreement',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='WorkflowEngine.SubmissionAgreement'),
        ),
    ]
