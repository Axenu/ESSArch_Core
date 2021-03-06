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
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('WorkflowEngine', '0042_auto_20160826_1338'),
    ]

    operations = [
        migrations.AlterField(
            model_name='processtask',
            name='processstep',
            field=models.ForeignKey(related_name='tasks', blank=True, to='WorkflowEngine.ProcessStep', null=True),
        ),
        migrations.AlterField(
            model_name='processtask',
            name='time_done',
            field=models.DateTimeField(null=True, verbose_name='done at', blank=True),
        ),
        migrations.AlterField(
            model_name='processtask',
            name='time_started',
            field=models.DateTimeField(null=True, verbose_name='started at', blank=True),
        ),
    ]
