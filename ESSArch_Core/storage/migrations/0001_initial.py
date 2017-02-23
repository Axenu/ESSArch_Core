# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2017-02-23 10:16
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import picklefield.fields
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('configuration', '0006_archivepolicy'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('ip', '0029_auto_20170223_1116'),
    ]

    operations = [
        migrations.CreateModel(
            name='AccessQueue',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('req_uuid', models.CharField(max_length=36)),
                ('req_type', models.IntegerField(choices=[(3, 'Generate DIP (package)'), (4, 'Generate DIP (package extracted)'), (1, 'Generate DIP (package & package extracted)'), (2, 'Verify StorageMedium'), (5, 'Get AIP to ControlArea')], null=True)),
                ('req_purpose', models.CharField(max_length=255)),
                ('user', models.CharField(max_length=45)),
                ('password', models.CharField(blank=True, max_length=45)),
                ('object_identifier_value', models.CharField(blank=True, max_length=255)),
                ('storage_medium_id', models.CharField(blank=True, max_length=45)),
                ('status', models.IntegerField(blank=True, choices=[(0, 'Pending'), (2, 'Initiate'), (5, 'Progress'), (20, 'Success'), (100, 'FAIL')], default=0, null=True)),
                ('path', models.CharField(max_length=255)),
                ('posted', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'permissions': (('list_accessqueue', 'Can list access queue'),),
            },
        ),
        migrations.CreateModel(
            name='CacheStorage',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255, verbose_name='Cache Name')),
                ('path', models.CharField(max_length=255, verbose_name='Cache Directory')),
            ],
        ),
        migrations.CreateModel(
            name='IngestStorage',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255, verbose_name='Ingest Name')),
                ('path', models.CharField(max_length=255, verbose_name='Ingest Directory')),
            ],
        ),
        migrations.CreateModel(
            name='IOQueue',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('req_type', models.IntegerField(choices=[(10, 'Write to tape'), (15, 'Write to disk'), (20, 'Read from tape'), (25, 'Read from disk'), (41, 'Write to HDFS'), (42, 'Read from HDFS'), (43, 'Write to HDFS-REST'), (44, 'Read from HDFS-REST')])),
                ('req_purpose', models.CharField(blank=True, max_length=255)),
                ('user', models.CharField(max_length=45)),
                ('object_path', models.CharField(blank=True, max_length=256)),
                ('write_size', models.BigIntegerField(blank=True, null=True)),
                ('result', picklefield.fields.PickledObjectField(blank=True, editable=False)),
                ('status', models.IntegerField(blank=True, choices=[(0, 'Pending'), (2, 'Initiate'), (5, 'Progress'), (20, 'Success'), (100, 'FAIL')], default=0)),
                ('task_id', models.CharField(blank=True, max_length=36)),
                ('posted', models.DateTimeField(auto_now_add=True)),
                ('remote_status', models.IntegerField(blank=True, choices=[(0, 'Pending'), (2, 'Initiate'), (5, 'Transfer'), (20, 'Success'), (100, 'FAIL')], default=0)),
                ('transfer_task_id', models.CharField(blank=True, max_length=36)),
                ('access_queue', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='storage.AccessQueue')),
                ('ip', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='ip.InformationPackage')),
            ],
            options={
                'permissions': (('list_IOQueue', 'Can list IOQueue'),),
            },
        ),
        migrations.CreateModel(
            name='StorageMedium',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('medium_id', models.CharField(max_length=255, unique=True, verbose_name='The id for the medium, e.g. barcode')),
                ('status', models.IntegerField(choices=[(0, 'Inactive'), (20, 'Write'), (30, 'Full'), (100, 'FAIL')])),
                ('location', models.CharField(max_length=255)),
                ('location_status', models.IntegerField(choices=[(10, 'Delivered'), (20, 'Received'), (30, 'Placed'), (40, 'Collected'), (50, 'Robot')])),
                ('block_size', models.IntegerField(choices=[(128, '64K'), (250, '125K'), (256, '128K'), (512, '256K'), (1024, '512K'), (2048, '1024K')])),
                ('format', models.IntegerField(choices=[(103, '103 (AIC support)'), (102, '102 (Media label)'), (101, '101 (Old read only)'), (100, '100 (Old read only)')])),
                ('used_capacity', models.BigIntegerField()),
                ('number_of_mounts', models.IntegerField()),
                ('create_date', models.DateTimeField(auto_now_add=True)),
                ('last_changed_local', models.DateTimeField(null=True)),
                ('last_changed_external', models.DateTimeField(null=True)),
                ('agent', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'permissions': (('list_storageMedium', 'Can list storageMedium'),),
            },
        ),
        migrations.CreateModel(
            name='StorageMethod',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(blank=True, max_length=255, verbose_name='Name')),
                ('status', models.BooleanField(default=False, verbose_name='Storage method status')),
                ('type', models.IntegerField(choices=[(200, 'DISK'), (300, 'TAPE'), (400, 'CAS')], default=200, verbose_name='Type')),
                ('archive_policy', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='configuration.ArchivePolicy')),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='StorageMethodTargetRelation',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(blank=True, max_length=255, verbose_name='Name')),
                ('status', models.IntegerField(choices=[(0, 'Disabled'), (1, 'Enabled'), (2, 'ReadOnly'), (3, 'Migrate')], default=0, verbose_name='Storage target status')),
                ('storage_method', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='storage.StorageMethod')),
            ],
            options={
                'ordering': ['name'],
                'verbose_name': 'Storage Target/Method Relation',
            },
        ),
        migrations.CreateModel(
            name='StorageObject',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('content_location_type', models.IntegerField(choices=[(200, 'DISK'), (300, 'TAPE'), (400, 'CAS')])),
                ('content_location_value', models.CharField(max_length=255)),
                ('last_changed_local', models.DateTimeField(null=True)),
                ('last_changed_external', models.DateTimeField(null=True)),
                ('ip', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='storage', to='ip.InformationPackage')),
                ('storage_medium', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='storage', to='storage.StorageMedium')),
            ],
            options={
                'permissions': (('list_storage', 'Can list storage'),),
            },
        ),
        migrations.CreateModel(
            name='StorageTargets',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255, unique=True, verbose_name='Name')),
                ('status', models.BooleanField(default=True, verbose_name='Storage target status')),
                ('type', models.IntegerField(choices=[(200, 'DISK'), (301, 'IBM-LTO1'), (302, 'IBM-LTO2'), (303, 'IBM-LTO3'), (304, 'IBM-LTO4'), (305, 'IBM-LTO5'), (306, 'IBM-LTO6'), (325, 'HP-LTO5'), (326, 'HP-LTO6'), (401, 'HDFS'), (402, 'HDFS-REST')], default=200, verbose_name='Type')),
                ('default_block_size', models.IntegerField(choices=[(128, '64K'), (250, '125K'), (256, '128K'), (512, '256K'), (1024, '512K'), (2048, '1024K')], default=1024, verbose_name='Default block size (tape)')),
                ('default_format', models.IntegerField(choices=[(103, '103 (AIC support)'), (102, '102 (Media label)'), (101, '101 (Old read only)'), (100, '100 (Old read only)')], default=103, verbose_name='Default format')),
                ('min_chunk_size', models.BigIntegerField(choices=[(0, 'Disabled'), (1048576, '1 MByte'), (1073741824, '1 GByte'), (53687091201, '5 GByte'), (10737418240, '10 GByte'), (107374182400, '100 GByte'), (214748364800, '200 GByte'), (322122547200, '300 GByte'), (429496729600, '400 GByte'), (536870912000, '500 GByte')], default=0, verbose_name='Min chunk size')),
                ('min_capacity_warning', models.BigIntegerField(default=0, verbose_name='Min capacity warning (0=Disabled)')),
                ('max_capacity', models.BigIntegerField(default=0, verbose_name='Max capacity (0=Disabled)')),
                ('remote_server', models.CharField(blank=True, max_length=255, verbose_name='Remote server (https://hostname,user,password)')),
                ('master_server', models.CharField(blank=True, max_length=255, verbose_name='Master server (https://hostname,user,password)')),
                ('target', models.CharField(max_length=255, verbose_name='Target (URL, path or barcodeprefix)')),
            ],
            options={
                'ordering': ['name'],
                'verbose_name': 'Storage Target',
            },
        ),
        migrations.AddField(
            model_name='storagemethodtargetrelation',
            name='storage_target',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='storage.StorageTargets'),
        ),
        migrations.AddField(
            model_name='storagemedium',
            name='storage_target',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='storage.StorageTargets'),
        ),
        migrations.AddField(
            model_name='ioqueue',
            name='storage_medium',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='storage.StorageMedium'),
        ),
        migrations.AddField(
            model_name='ioqueue',
            name='storage_method',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='storage.StorageMethod'),
        ),
        migrations.AddField(
            model_name='ioqueue',
            name='storage_method_target',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='storage.StorageMethodTargetRelation'),
        ),
        migrations.AddField(
            model_name='ioqueue',
            name='storage_object',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='storage.StorageObject'),
        ),
        migrations.AddField(
            model_name='ioqueue',
            name='storage_target',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='storage.StorageTargets'),
        ),
    ]
