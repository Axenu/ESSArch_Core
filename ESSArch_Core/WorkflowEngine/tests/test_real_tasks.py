# -*- coding: utf-8 -*-

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

import filecmp
import mock
import os
import shutil
import string
import subprocess
import tarfile
import tempfile
import traceback
import unicodedata
import uuid

import requests

from celery import states as celery_states

from lxml import etree

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core import mail
from django.test import TransactionTestCase, override_settings

from ESSArch_Core.configuration.models import (
    ArchivePolicy,
    EventType,
    Path
)

from ESSArch_Core.exceptions import FileFormatNotAllowed

from ESSArch_Core.ip.models import (
    EventIP,
    InformationPackage,
)

from ESSArch_Core.storage.exceptions import (
    MTFailedOperationException,
    RobotMountException,
    RobotUnmountException
)

from ESSArch_Core.storage.models import (
    TAPE,

    Robot,

    StorageMedium,
    StorageMethod,
    StorageMethodTargetRelation,
    StorageTarget,
    TapeDrive,
    TapeSlot,
)

from ESSArch_Core.storage.tape import (
    DEFAULT_TAPE_BLOCK_SIZE,

    get_tape_file_number,
    mount_tape,
    rewind_tape,
    set_tape_file_number,
    unmount_tape,
    write_to_tape,
)

from ESSArch_Core.util import find_and_replace_in_file, parse_content_range_header

from ESSArch_Core.WorkflowEngine.models import (
    ProcessStep,
    ProcessTask,
)


def setUpModule():
    settings.CELERY_ALWAYS_EAGER = True
    settings.CELERY_EAGER_PROPAGATES_EXCEPTIONS = True


class CalculateChecksumTestCase(TransactionTestCase):
    def setUp(self):
        self.taskname = "ESSArch_Core.tasks.CalculateChecksum"
        self.root = os.path.dirname(os.path.realpath(__file__))
        self.datadir = os.path.join(self.root, "datadir")

        try:
            os.mkdir(self.datadir)
        except OSError as e:
            if e.errno != 17:
                raise

        self.fname = os.path.join(self.datadir, "file1.txt")

    def tearDown(self):
        shutil.rmtree(self.datadir)

    def test_file_with_content(self):
        with open(self.fname, "w") as f:
            f.write('foo')

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'filename': self.fname
            }
        )

        expected = "2c26b46b68ffc68ff99b453c1d30413413422d706483bfa0f98a5e886266e7ae"
        actual = task.run().get()

        self.assertEqual(expected, actual)

    def test_empty_file(self):
        open(self.fname, "a").close()

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'filename': self.fname
            }
        )

        expected = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        actual = task.run().get()

        self.assertEqual(expected, actual)

    def test_small_block_size(self):
        with open(self.fname, "w") as f:
            f.write('foo')

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'filename': self.fname,
                'block_size': 1
            }
        )

        expected = "2c26b46b68ffc68ff99b453c1d30413413422d706483bfa0f98a5e886266e7ae"
        actual = task.run().get()

        self.assertEqual(expected, actual)

    def test_md5(self):
        with open(self.fname, "w") as f:
            f.write('foo')

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'filename': self.fname,
                'algorithm': 'MD5'
            }
        )

        expected = "acbd18db4cc2f85cedef654fccc4a4d8"
        actual = task.run().get()

        self.assertEqual(expected, actual)

    def test_sha1(self):
        with open(self.fname, "w") as f:
            f.write('foo')

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'filename': self.fname,
                'algorithm': 'SHA-1'
            }
        )

        expected = "0beec7b5ea3f0fdbc95d0dd47f3c5bc275da8a33"
        actual = task.run().get()

        self.assertEqual(expected, actual)

    def test_sha224(self):
        with open(self.fname, "w") as f:
            f.write('foo')

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'filename': self.fname,
                'algorithm': 'SHA-224'
            }
        )

        expected = "0808f64e60d58979fcb676c96ec938270dea42445aeefcd3a4e6f8db"
        actual = task.run().get()

        self.assertEqual(expected, actual)

    def test_sha384(self):
        with open(self.fname, "w") as f:
            f.write('foo')

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'filename': self.fname,
                'algorithm': 'SHA-384'
            }
        )

        expected = "98c11ffdfdd540676b1a137cb1a22b2a70350c9a44171d6b1180c6be5cbb2ee3f79d532c8a1dd9ef2e8e08e752a3babb"
        actual = task.run().get()

        self.assertEqual(expected, actual)

    def test_sha512(self):
        with open(self.fname, "w") as f:
            f.write('foo')

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'filename': self.fname,
                'algorithm': 'SHA-512'
            }
        )

        expected = "f7fbba6e0636f890e56fbbf3283e524c6fa3204ae298382d624741d0dc6638326e282c41be5e4254d8820772c5518a2c5a8c0c7f7eda19594a7eb539453e1ed7"
        actual = task.run().get()

        self.assertEqual(expected, actual)

class IdentifyFileFormatTestCase(TransactionTestCase):
    def setUp(self):
        self.taskname = "ESSArch_Core.tasks.IdentifyFileFormat"
        self.root = os.path.dirname(os.path.realpath(__file__))
        self.datadir = os.path.join(self.root, "datadir")

        try:
            os.mkdir(self.datadir)
        except OSError as e:
            if e.errno != 17:
                raise

        self.fname = os.path.join(self.datadir, "file1.txt")

    def tearDown(self):
        shutil.rmtree(self.datadir)

    def test_file_with_content(self):
        with open(self.fname, "w") as f:
            f.write('foo')

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'filename': self.fname
            }
        )

        expected = ("Plain Text File", None, "x-fmt/111")
        actual = task.run().get()

        self.assertEqual(expected, actual)

    def test_filename_with_non_english_characters(self):
        fname = os.path.join(self.datadir, u'åäö.txt')

        with open(fname, "w") as f:
            f.write('foo')

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'filename': fname
            }
        )

        expected = ("Plain Text File", None, "x-fmt/111")
        actual = task.run().get()

        self.assertEqual(expected, actual)

    def test_empty_file_with_filename_with_non_english_characters(self):
        fname = os.path.join(self.datadir, u'åäö.txt')

        open(fname, "a").close()

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'filename': fname
            }
        )

        expected = ("Plain Text File", None, "x-fmt/111")
        actual = task.run().get()

        self.assertEqual(expected, actual)

    def test_non_existent_file_extension(self):
        fname = os.path.join(self.datadir, 'foo.zxczxc')

        with open(fname, "w") as f:
            f.write('foo')

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'filename': fname
            }
        )

        with self.assertRaises(ValueError):
            task.run().get()

    def test_non_existent_file_extension_with_filename_with_non_english_characters(self):
        fname = os.path.join(self.datadir, 'åäö.zxczxc')

        with open(fname, "w") as f:
            f.write('foo')

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'filename': fname
            }
        )

        with self.assertRaises(ValueError):
            task.run().get()


class GenerateXMLTestCase(TransactionTestCase):
    def setUp(self):
        self.taskname = "ESSArch_Core.tasks.GenerateXML"
        self.root = os.path.dirname(os.path.realpath(__file__))
        self.datadir = os.path.join(self.root, "datadir")
        self.fname = os.path.join(self.datadir, 'test1.xml')
        self.spec = {
            '-name': 'foo',
            '-attr': [
                {
                    '-name': 'fooAttr',
                    '#content': [{'var': 'foo'}]
                }
            ],
            '-children': [
                {
                    '-name': 'bar',
                    '#content': [{'var': 'bar'}]
                },
                {
                    '-name': 'baz',
                    '-containsFiles': True,
                    '#content': [{'var': 'FName'}]
                }
            ]
        }

        self.specData = {
            'foo': 'foodata',
            'bar': 'bardata'
        }

        Path.objects.create(
            entity="path_mimetypes_definitionfile",
            value=os.path.join(self.root, "mime.types")
        )

        try:
            os.mkdir(self.datadir)
        except OSError as e:
            if e.errno != 17:
                raise

    def tearDown(self):
        shutil.rmtree(self.datadir)

    def test_without_file(self):
        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'info': self.specData,
                'filesToCreate': {
                    self.fname: self.spec
                }
            }
        )

        task.run()

        tree = etree.parse(self.fname)
        root = tree.getroot()

        self.assertEqual(root.get('fooAttr'), 'foodata')
        self.assertEqual(root.find('bar').text, 'bardata')
        self.assertNotIn('baz', root.attrib)

    def test_with_file(self):
        open(os.path.join(self.datadir, 'example.txt'), 'a').close()

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'info': self.specData,
                'filesToCreate': {
                    self.fname: self.spec
                },
                'folderToParse': self.datadir
            }
        )

        task.run()

        tree = etree.parse(self.fname)
        root = tree.getroot()

        self.assertEqual(root.get('fooAttr'), 'foodata')
        self.assertEqual(root.find('bar').text, 'bardata')
        self.assertEqual(root.find('baz').text, 'example.txt')

    def test_with_non_ascii_file(self):
        open(os.path.join(self.datadir, u'åäö.txt'), 'a').close()

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'info': self.specData,
                'filesToCreate': {
                    self.fname: self.spec
                },
                'folderToParse': self.datadir
            }
        )

        task.run()

        tree = etree.parse(self.fname)
        root = tree.getroot()


        self.assertEqual(root.get('fooAttr'), 'foodata')
        self.assertEqual(root.find('bar').text, 'bardata')

        a = root.find('baz').text
        b = u'åäö.txt'

        self.assertEqual(unicodedata.normalize('NFC', a), unicodedata.normalize('NFC', b))

    def test_with_multiple_files(self):
        extra_file = os.path.join(self.datadir, 'test2.xml')

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'info': self.specData,
                'filesToCreate': {
                    self.fname: self.spec,
                    extra_file: self.spec
                }
            }
        )

        task.run()

        self.assertTrue(os.path.isfile(self.fname))
        self.assertTrue(os.path.isfile(extra_file))

    def test_with_disallowed_file(self):
        open(os.path.join(self.datadir, 'example.docx'), 'a').close()

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'info': self.specData,
                'filesToCreate': {
                    self.fname: self.spec
                },
                'folderToParse': self.datadir
            }
        )

        with self.assertRaises(FileFormatNotAllowed):
            task.run().get()

        self.assertFalse(os.path.exists(self.fname))

    def test_undo_with_disallowed_file(self):
        open(os.path.join(self.datadir, 'example.docx'), 'a').close()

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'info': self.specData,
                'filesToCreate': {
                    self.fname: self.spec
                },
                'folderToParse': self.datadir
            }
        )

        with self.assertRaises(FileFormatNotAllowed):
            task.run().get()

        task.undo().get()

    def test_with_external(self):
        self.spec = {
            '-name': 'root',
            '-children': [
                {
                    '-name': 'file',
                    '-containsFiles': True,
                    '-attr': [
                        {
                            '-name': 'href',
                            '#content': [{'var': 'href'}]
                        },
                    ],
                },
            ],
            '-external': {
                '-dir': 'external',
                '-file': 'external.xml',
                '-pointer': {
                    '-name': 'ptr',
                    '-attr': [
                        {
                            '-name': 'href',
                            '#content': [{'var': '_EXT_HREF'}]
                        },
                    ],
                },
                '-specification': {
                    '-name': 'mets',
                    '-attr': [
                        {
                            '-name': 'LABEL',
                            '#content': [{'var': '_EXT'}]
                        },
                    ],
                    '-children': [
                        {
                            '-name': 'file',
                            '-containsFiles': True,
                            '-attr': [
                                {
                                    '-name': 'href',
                                    '#content': [{'var': 'href'}]
                                },
                            ],
                        },
                    ]
                }
            },
        }

        os.mkdir(os.path.join(self.datadir, 'external'))
        os.mkdir(os.path.join(self.datadir, 'external', 'ext1'))
        os.mkdir(os.path.join(self.datadir, 'external', 'ext2'))

        open(os.path.join(self.datadir, 'file0.txt'), 'a').close()

        open(os.path.join(self.datadir, 'external', 'ext1', 'file1.txt'), 'a').close()
        open(os.path.join(self.datadir, 'external', 'ext2', 'file1.pdf'), 'a').close()

        step = ProcessStep.objects.create(name="root step")
        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'filesToCreate': {
                    self.fname: self.spec,
                },
                'folderToParse': self.datadir
            },
            processstep=step,
        )

        task.run()

        all_parse_file_tasks = ProcessTask.objects.filter(
            name="ESSArch_Core.tasks.ParseFile"
        )
        parse_file_tasks_with_step = ProcessTask.objects.filter(
            name="ESSArch_Core.tasks.ParseFile",
            processstep__parent_step=step
        )

        self.assertEqual(parse_file_tasks_with_step.count(), all_parse_file_tasks.count())

    def test_undo(self):
        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'info': self.specData,
                'filesToCreate': {
                    self.fname: self.spec
                }
            }
        )

        task.run()

        self.assertTrue(os.path.isfile(self.fname))

        task.undo()

        self.assertFalse(os.path.isfile(self.fname))

    def test_undo_multiple_created_files(self):
        extra_file = os.path.join(self.datadir, 'test2.xml')

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'info': self.specData,
                'filesToCreate': {
                    self.fname: self.spec,
                    extra_file: self.spec
                }
            }
        )

        task.run()

        self.assertTrue(os.path.isfile(self.fname))
        self.assertTrue(os.path.isfile(extra_file))

        task.undo()

        self.assertFalse(os.path.isfile(self.fname))
        self.assertFalse(os.path.isfile(extra_file))

class InsertXMLTestCase(TransactionTestCase):
    def setUp(self):
        self.taskname = "ESSArch_Core.tasks.InsertXML"
        self.root = os.path.dirname(os.path.realpath(__file__))
        self.datadir = os.path.join(self.root, "datadir")
        self.fname = os.path.join(self.datadir, 'test1.xml')

        self.spec = {
            '-name': 'inserted',
            '#content': [{'var': 'inserted_var'}]
        }

        Path.objects.create(
            entity="path_mimetypes_definitionfile",
            value=os.path.join(self.root, "mime.types")
        )

        try:
            os.mkdir(self.datadir)
        except OSError as e:
            if e.errno != 17:
                raise

        root = etree.fromstring("""
            <root>
                <foo><nested><duplicate></duplicate></nested></foo>
                <bar><duplicate></duplicate></bar>
            </root>
        """)

        with open(self.fname, 'w') as f:
            f.write(etree.tostring(root, pretty_print=True, xml_declaration=True, encoding='UTF-8'))

    def tearDown(self):
        shutil.rmtree(self.datadir)

    def test_insert_empty_to_root(self):
        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'filename': self.fname,
                'elementToAppendTo': 'root',
                'spec': self.spec,
            }
        )

        with self.assertRaises(TypeError):
            task.run()

    def test_insert_non_empty_to_root(self):
        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'filename': self.fname,
                'elementToAppendTo': 'root',
                'spec': self.spec,
                'info': {'inserted_var': 'inserted data'}
            }
        )

        task.run()

        tree = etree.parse(self.fname)
        inserted = tree.find('.//inserted')

        self.assertIsNotNone(inserted)
        self.assertEqual(inserted.text, 'inserted data')

    def test_insert_to_element_with_children(self):
        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'filename': self.fname,
                'elementToAppendTo': 'foo',
                'spec': self.spec,
                'info': {'inserted_var': 'inserted data'}
            }
        )

        task.run()

        tree = etree.parse(self.fname)

        foo = tree.find('.//foo')
        nested = tree.find('.//nested')
        inserted = tree.find('.//inserted')

        self.assertLess(foo.index(nested), foo.index(inserted))

    def test_insert_at_index(self):
        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'filename': self.fname,
                'elementToAppendTo': 'foo',
                'spec': self.spec,
                'info': {'inserted_var': 'inserted data'},
                'index': 0
            }
        )

        task.run()

        tree = etree.parse(self.fname)

        foo = tree.find('.//foo')
        nested = tree.find('.//nested')
        inserted = tree.find('.//inserted')

        self.assertLess(foo.index(inserted), foo.index(nested))

    def test_insert_to_duplicate_element(self):
        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'filename': self.fname,
                'elementToAppendTo': 'duplicate',
                'spec': self.spec,
                'info': {'inserted_var': 'inserted data'},
            }
        )

        task.run()

        tree = etree.parse(self.fname)
        duplicates = tree.findall('.//duplicate')

        self.assertIsNotNone(duplicates[0].find('.//inserted'))
        self.assertIsNone(duplicates[1].find('.//inserted'))

    def test_undo(self):
        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'filename': self.fname,
                'elementToAppendTo': 'foo',
                'spec': self.spec,
                'info': {'inserted_var': 'inserted data'},
            }
        )

        task.run()

        tree = etree.parse(self.fname)
        self.assertIsNotNone(tree.find('.//inserted'))

        task.undo()

        tree = etree.parse(self.fname)
        self.assertIsNone(tree.find('.//inserted'))

    def test_undo_index(self):
        task1 = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'filename': self.fname,
                'elementToAppendTo': 'foo',
                'spec': self.spec,
                'info': {'inserted_var': 'inserted 1'},
            }
        )

        task2 = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'filename': self.fname,
                'elementToAppendTo': 'foo',
                'spec': self.spec,
                'info': {'inserted_var': 'inserted 2'},
                'index': 0
            }
        )

        task3 = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'filename': self.fname,
                'elementToAppendTo': 'foo',
                'spec': self.spec,
                'info': {'inserted_var': 'inserted 3'},
                'index': 2
            }
        )

        task1.run()
        task2.run()
        task3.run()

        tree = etree.parse(self.fname)
        found = tree.findall('.//inserted')
        self.assertEqual(len(found), 3)
        self.assertEqual(found[0].text, 'inserted 2')
        self.assertEqual(found[1].text, 'inserted 3')
        self.assertEqual(found[2].text, 'inserted 1')

        task3.undo()

        tree = etree.parse(self.fname)
        found = tree.findall('.//inserted')
        self.assertEqual(len(found), 2)
        self.assertEqual(found[0].text, 'inserted 2')
        self.assertEqual(found[1].text, 'inserted 1')

        task2.undo()

        tree = etree.parse(self.fname)
        found = tree.findall('.//inserted')
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].text, 'inserted 1')

        task1.undo()

        tree = etree.parse(self.fname)
        self.assertIsNone(tree.find('.//inserted'))


class AppendEventsTestCase(TransactionTestCase):
    def setUp(self):
        self.taskname = "ESSArch_Core.tasks.AppendEvents"
        self.root = os.path.dirname(os.path.realpath(__file__))
        self.datadir = os.path.join(self.root, "datadir")
        self.fname = os.path.join(self.datadir, 'test1.xml')
        self.ip = InformationPackage.objects.create(label="testip")
        self.user = User.objects.create(username="testuser")

        try:
            os.mkdir(self.datadir)
        except OSError as e:
            if e.errno != 17:
                raise

        root = etree.fromstring("""
            <premis:premis xmlns:premis='http://xml.ra.se/PREMIS'
            xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance'
            xmlns:xlink='http://www.w3.org/1999/xlink'
            xsi:schemaLocation='http://xml.ra.se/PREMIS http://xml.ra.se/PREMIS/ESS/RA_PREMIS_PreVersion.xsd'
            version='2.0'>
            </premis:premis>
        """)

        with open(self.fname, 'w') as f:
            f.write(etree.tostring(root, pretty_print=True, xml_declaration=True, encoding='UTF-8'))

    def tearDown(self):
        shutil.rmtree(self.datadir)

    def test_undo(self):
        event_type = EventType.objects.create()

        for i in range(10):
            EventIP.objects.create(
                eventType=event_type, linkingAgentIdentifierValue=self.user,
                linkingObjectIdentifierValue=self.ip
            ),

        task1 = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'filename': self.fname,
                'events': EventIP.objects.all()
            },
            information_package=self.ip
        )

        task1.run()

        EventIP.objects.all().delete()

        for i in range(10):
            EventIP.objects.create(
                eventType=event_type, linkingAgentIdentifierValue=self.user,
                linkingObjectIdentifierValue=self.ip
            ),

        tree = etree.parse(self.fname)
        found = tree.findall('.//{*}event')
        self.assertEqual(len(found), 10)

        task2 = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'filename': self.fname,
                'events': EventIP.objects.all()
            },
            information_package=self.ip
        )

        task2.run()

        tree = etree.parse(self.fname)
        found = tree.findall('.//{*}event')
        self.assertEqual(len(found), 20)

        task2.undo()

        tree = etree.parse(self.fname)
        found = tree.findall('.//{*}event')
        self.assertEqual(len(found), 10)

        task1.undo()

        tree = etree.parse(self.fname)
        found = tree.findall('.//{*}event')
        self.assertEqual(len(found), 0)


class CreateTARTestCase(TransactionTestCase):
    def setUp(self):
        self.datadir = tempfile.mkdtemp()

    def tearDown(self):
        try:
            shutil.rmtree(self.datadir)
        except:
            pass

    def test_run(self):
        filename = os.path.join(self.datadir, "file.txt")
        open(filename, "a").close()

        tarname = self.datadir + ".tar"

        task = ProcessTask.objects.create(
            name="ESSArch_Core.tasks.CreateTAR",
            params={
                "dirname": self.datadir,
                "tarname": tarname
            },
        )
        task.run()

        self.assertTrue(os.path.isdir(self.datadir))
        self.assertTrue(os.path.isfile(filename))
        self.assertTrue(os.path.isfile(tarname))

    def test_undo(self):
        filename = os.path.join(self.datadir, "file.txt")
        open(filename, "a").close()

        tarname = self.datadir + ".tar"

        task = ProcessTask.objects.create(
            name="ESSArch_Core.tasks.CreateTAR",
            params={
                "dirname": self.datadir,
                "tarname": tarname
            },
        )
        task.run()

        self.assertTrue(os.path.isdir(self.datadir))
        self.assertTrue(os.path.isfile(filename))
        self.assertTrue(os.path.isfile(tarname))

        shutil.rmtree(self.datadir)
        task.undo()

        self.assertTrue(os.path.isdir(self.datadir))
        self.assertTrue(os.path.isfile(filename))
        self.assertFalse(os.path.isfile(tarname))

class CreateZIPTestCase(TransactionTestCase):
    def setUp(self):
        self.datadir = tempfile.mkdtemp()

    def tearDown(self):
        try:
            shutil.rmtree(self.datadir)
        except:
            pass

    def test_run(self):
        filename = os.path.join(self.datadir, "file.txt")
        open(filename, "a").close()

        zipname = self.datadir + ".zip"

        task = ProcessTask.objects.create(
            name="ESSArch_Core.tasks.CreateZIP",
            params={
                "dirname": self.datadir,
                "zipname": zipname
            },
        )
        task.run()

        self.assertTrue(os.path.isdir(self.datadir))
        self.assertTrue(os.path.isfile(filename))
        self.assertTrue(os.path.isfile(zipname))

    def test_undo(self):
        filename = os.path.join(self.datadir, "file.txt")
        open(filename, "a").close()

        zipname = self.datadir + ".zip"

        task = ProcessTask.objects.create(
            name="ESSArch_Core.tasks.CreateZIP",
            params={
                "dirname": self.datadir,
                "zipname": zipname
            },
        )
        task.run()

        self.assertTrue(os.path.isdir(self.datadir))
        self.assertTrue(os.path.isfile(filename))
        self.assertTrue(os.path.isfile(zipname))

        shutil.rmtree(self.datadir)
        task.undo()

        self.assertTrue(os.path.isdir(self.datadir))
        self.assertTrue(os.path.isfile(filename))
        self.assertFalse(os.path.isfile(zipname))

class ValidateFilesTestCase(TransactionTestCase):
    def setUp(self):
        self.taskname = "ESSArch_Core.tasks.ValidateFiles"
        self.root = os.path.dirname(os.path.realpath(__file__))
        self.datadir = os.path.join(self.root, "datadir")
        self.fname = os.path.join(self.datadir, 'test1.xml')
        self.ip = InformationPackage.objects.create(label="testip")
        self.user = User.objects.create(username="testuser")

        Path.objects.create(
            entity="path_mimetypes_definitionfile",
            value=os.path.join(self.root, "mime.types")
        )

        self.filesToCreate = {
            self.fname: {
                '-name': 'root',
                '-children': [{
                    '-name': 'object',
                    '-containsFiles': True,
                    '-filters': {'FName': '^((?!' + os.path.basename(self.fname) + ').)*$'},
                    '-children': [
                        {
                            '-name': 'storage',
                            '-children': [{
                                '-name': 'contentLocation',
                                '-children': [{
                                    '-name': 'contentLocationValue',
                                    '#content': [
                                        {
                                            'text': 'file:///',
                                        },
                                        {
                                            'var': 'href'
                                        }
                                    ]
                                }]
                            }]
                        },
                        {
                            '-name': 'objectCharacteristics',
                            '-children': [
                                {
                                    '-name': 'fixity',
                                    '-children': [
                                        {
                                            '-name': 'messageDigest',
                                            '#content': [{
                                                'var': 'FChecksum'
                                            }]
                                        },
                                        {
                                            '-name': 'messageDigestAlgorithm',
                                            '#content': [{
                                                'var': 'FChecksumType'
                                            }]
                                        }
                                    ]
                                },
                                {
                                    '-name': 'format',
                                    '-children': [
                                        {
                                            '-name': 'formatDesignation',
                                            '-children': [
                                                {
                                                    '-name': 'formatName',
                                                    '#content': [
                                                        {
                                                            'var': 'FFormatName'
                                                        }
                                                    ]
                                                }
                                            ]
                                        },
                                        {
                                            '-name': 'messageDigestAlgorithm',
                                            '#content': [{
                                                'var': 'FChecksumType'
                                            }]
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                }]
            }
        }

        try:
            os.mkdir(self.datadir)
        except OSError as e:
            if e.errno != 17:
                raise

        root = etree.fromstring('<root></root>')

        with open(self.fname, 'w') as f:
            f.write(etree.tostring(root, pretty_print=True, xml_declaration=True, encoding='UTF-8'))

    def tearDown(self):
        shutil.rmtree(self.datadir)

    def test_no_validation(self):
        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'validate_fileformat': False,
                'validate_integrity': False,
            }
        )

        res = task.run().get()

        self.assertEqual(len(res), 0)

    def test_validation_without_files(self):
        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'ip': self.ip.pk,
                'xmlfile': self.fname
            }
        )

        res = task.run().get()

        self.assertEqual(len(res), 0)

    def test_validation_with_files(self):
        num_of_files = 3

        for i in range(num_of_files):
            with open(os.path.join(self.datadir, '%s.txt' % i), 'w') as f:
                f.write('%s' % i)

        ProcessTask.objects.create(
            name='ESSArch_Core.tasks.GenerateXML',
            params={
                'filesToCreate': self.filesToCreate,
                'folderToParse': self.datadir
            }
        ).run()

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'ip': self.ip.pk,
                'xmlfile': self.fname,
                'rootdir': self.datadir
            }
        )

        res = task.run().get()

        self.assertTrue(len(res) >= num_of_files)

    def test_external_xml_files(self):
        num_of_files = 2

        os.mkdir(os.path.join(self.datadir, 'ext'))
        os.mkdir(os.path.join(self.datadir, 'ext', 'ext1'))
        os.mkdir(os.path.join(self.datadir, 'ext', 'ext2'))

        for i in range(num_of_files):
            with open(os.path.join(self.datadir, 'ext', 'ext1', '%s.txt' % i), 'w') as f:
                f.write('%s' % i)

            with open(os.path.join(self.datadir, 'ext', 'ext2', '%s.rtf' % i), 'w') as f:
                f.write('%s' % i)

        ext1 = os.path.join(self.datadir, "ext", "ext1", "ext1.xml")
        ext2 = os.path.join(self.datadir, "ext", "ext2", "ext2.xml")

        with open(self.fname, 'w') as xml:
            xml.write('''<?xml version="1.0" encoding="UTF-8" ?>
            <root xmlns:xlink="http://www.w3.org/1999/xlink">
                <mptr xlink:href="ext/ext1/ext1.xml"/>
                <mptr xlink:href="ext/ext2/ext2.xml"/>
            </root>
            ''')

        with open(ext1, 'w') as xml:
            xml.write('''<?xml version="1.0" encoding="UTF-8" ?>
            <root xmlns:xlink="http://www.w3.org/1999/xlink">
                <file CHECKSUM="cfcd208495d565ef66e7dff9f98764da" CHECKSUMTYPE="MD5" FILEFORMATNAME="Plain Text File"><FLocat href="0.txt"/></file>
                <file CHECKSUM="c4ca4238a0b923820dcc509a6f75849b" CHECKSUMTYPE="MD5" FILEFORMATNAME="Plain Text File"><FLocat href="1.txt"/></file>
            </root>
            ''')

        with open(ext2, 'w') as xml:
            xml.write('''<?xml version="1.0" encoding="UTF-8" ?>
            <root xmlns:xlink="http://www.w3.org/1999/xlink">
                <file CHECKSUM="cfcd208495d565ef66e7dff9f98764da" CHECKSUMTYPE="MD5" FILEFORMATNAME="Rich Text Format"><FLocat href="0.rtf"/></file>
                <file CHECKSUM="c4ca4238a0b923820dcc509a6f75849b" CHECKSUMTYPE="MD5" FILEFORMATNAME="Rich Text Format"><FLocat href="1.rtf"/></file>
            </root>
            ''')

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'ip': self.ip.pk,
                'xmlfile': self.fname,
                'rootdir': self.datadir
            }
        )

        task.run().get()

        with open(os.path.join(self.datadir, 'ext', 'ext1', '%s.txt' % i), 'a') as f:
            f.write('added')

        with self.assertRaises(AssertionError):
            task.run().get()

    def test_change_checksum(self):
        num_of_files = 3

        for i in range(num_of_files):
            with open(os.path.join(self.datadir, '%s.txt' % i), 'w') as f:
                f.write('%s' % i)

        ProcessTask.objects.create(
            name='ESSArch_Core.tasks.GenerateXML',
            params={
                'filesToCreate': self.filesToCreate,
                'folderToParse': self.datadir
            }
        ).run()

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'ip': self.ip.pk,
                'xmlfile': self.fname,
                'rootdir': self.datadir
            }
        )

        task.run()

        for i in range(num_of_files):
            with open(os.path.join(self.datadir, '%s.txt' % i), 'w') as f:
                f.write('%s updated' % i)

        with self.assertRaisesRegexp(AssertionError, 'checksum'):
            task.run()

    def test_change_file_format(self):
        num_of_files = 3

        for i in range(num_of_files):
            with open(os.path.join(self.datadir, '%s.txt' % i), 'w') as f:
                f.write('%s' % i)

        ProcessTask.objects.create(
            name='ESSArch_Core.tasks.GenerateXML',
            params={
                'filesToCreate': self.filesToCreate,
                'folderToParse': self.datadir
            }
        ).run()

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'ip': self.ip.pk,
                'xmlfile': self.fname,
                'rootdir': self.datadir
            }
        )

        task.run()

        for i in range(num_of_files):
            src = os.path.join(self.datadir, '%s.txt' % i)
            dst = os.path.join(self.datadir, '%s.pdf' % i)

            shutil.move(src, dst)

        find_and_replace_in_file(self.fname, '.txt', '.pdf')

        with self.assertRaisesRegexp(AssertionError, 'format name'):
            task.run()

    def test_fail_and_stop_step_when_inner_task_fails(self):
        fname = os.path.join(self.datadir, 'test1.txt')
        open(fname, 'a').close()

        ProcessTask.objects.create(
            name='ESSArch_Core.tasks.GenerateXML',
            params={
                'filesToCreate': self.filesToCreate,
                'folderToParse': self.datadir
            }
        ).run()

        with open(fname, 'w') as f:
            f.write('added')

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'ip': self.ip.pk,
                'xmlfile': self.fname,
                'rootdir': self.datadir
            }
        )

        with self.assertRaises(AssertionError):
            task.run()

        task.refresh_from_db()

        step = ProcessStep.objects.get(name="Validate Files")

        self.assertEqual(task.status, celery_states.FAILURE)
        self.assertEqual(step.status, celery_states.FAILURE)


class ValidateIntegrityTestCase(TransactionTestCase):
    def setUp(self):
        self.taskname = "ESSArch_Core.tasks.ValidateIntegrity"
        self.root = os.path.dirname(os.path.realpath(__file__))
        self.datadir = os.path.join(self.root, "datadir")
        self.fname = os.path.join(self.datadir, 'test1.txt')

        try:
            os.mkdir(self.datadir)
        except OSError as e:
            if e.errno != 17:
                raise

    def tearDown(self):
        shutil.rmtree(self.datadir)

    def test_correct(self):
        open(self.fname, 'a').close()

        t = ProcessTask.objects.create(
            name='ESSArch_Core.tasks.CalculateChecksum',
            params={
                'filename': self.fname
            }
        )

        checksum = t.run().get()

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'filename': self.fname,
                'checksum': checksum,
            }
        )

        task.run()

    def test_incorrect(self):
        open(self.fname, 'a').close()

        t = ProcessTask.objects.create(
            name='ESSArch_Core.tasks.CalculateChecksum',
            params={
                'filename': self.fname
            }
        )

        checksum = t.run().get()

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'filename': self.fname,
                'checksum': checksum,
            }
        )

        with open(self.fname, 'w') as f:
            f.write('foo')

        with self.assertRaisesRegexp(AssertionError, 'checksum'):
            task.run()


class ValidateFileFormatTestCase(TransactionTestCase):
    def setUp(self):
        self.taskname = "ESSArch_Core.tasks.ValidateFileFormat"
        self.root = os.path.dirname(os.path.realpath(__file__))
        self.datadir = os.path.join(self.root, "datadir")
        self.fname = os.path.join(self.datadir, 'test1.txt')

        try:
            os.mkdir(self.datadir)
        except OSError as e:
            if e.errno != 17:
                raise

    def tearDown(self):
        shutil.rmtree(self.datadir)

    def test_correct(self):
        open(self.fname, 'a').close()

        t = ProcessTask.objects.create(
            name='ESSArch_Core.tasks.IdentifyFileFormat',
            params={
                'filename': self.fname
            }
        )

        fformat = t.run().get()

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'filename': self.fname,
                'format_name': fformat[0],
            }
        )

        task.run()

    def test_incorrect(self):
        open(self.fname, 'a').close()

        t = ProcessTask.objects.create(
            name='ESSArch_Core.tasks.IdentifyFileFormat',
            params={
                'filename': self.fname
            }
        )

        fformat = t.run().get()

        newfile = string.replace(self.fname, '.txt', '.pdf')
        shutil.move(self.fname, newfile)

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'filename': newfile,
                'format_name': fformat[0],
            }
        )

        with self.assertRaisesRegexp(AssertionError, 'format'):
            task.run()


class ValidateXMLFileTestCase(TransactionTestCase):
    def setUp(self):
        self.taskname = "ESSArch_Core.tasks.ValidateXMLFile"
        self.root = os.path.dirname(os.path.realpath(__file__))
        self.datadir = os.path.join(self.root, "datadir")
        self.fname = os.path.join(self.datadir, 'test1.xml')
        self.schema = os.path.join(self.datadir, 'test1.xsd')

        try:
            os.mkdir(self.datadir)
        except OSError as e:
            if e.errno != 17:
                raise

        schema_root = etree.fromstring("""
            <xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
                <xsd:element name="foo" type="xsd:integer"/>

                <xsd:attribute name="href" type="xsd:string"/>

                <xsd:element name="mptr">
                    <xsd:complexType>
                        <xsd:attribute ref="href" use="required"/>
                    </xsd:complexType>
                </xsd:element>

                <xsd:element name="root">
                    <xsd:complexType>
                        <xsd:sequence>
                            <xsd:element minOccurs="0" ref="foo"/>
                            <xsd:element minOccurs="0" maxOccurs="unbounded" ref="mptr"/>
                        </xsd:sequence>
                    </xsd:complexType>
                </xsd:element>
            </xsd:schema>
        """)

        with open(self.schema, 'w') as f:
            f.write(etree.tostring(schema_root, pretty_print=True, xml_declaration=True, encoding='UTF-8'))

    def tearDown(self):
        shutil.rmtree(self.datadir)

    def test_correct(self):
        root = etree.fromstring('<foo>5</foo>')

        with open(self.fname, 'w') as f:
            f.write(etree.tostring(root, pretty_print=True, xml_declaration=True, encoding='UTF-8'))

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'xml_filename': self.fname,
                'schema_filename': self.schema
            }
        )

        task.run()

    def test_incorrect(self):
        root = etree.fromstring('<foo>bar</foo>')

        with open(self.fname, 'w') as f:
            f.write(etree.tostring(root, pretty_print=True, xml_declaration=True, encoding='UTF-8'))

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'xml_filename': self.fname,
                'schema_filename': self.schema
            }
        )

        with self.assertRaisesRegexp(etree.DocumentInvalid, 'not a valid value of the atomic type'):
            task.run()

    def test_correct_with_correct_external(self):
        ext1 = os.path.join(self.datadir, 'ext1.xml')
        ext2 = os.path.join(self.datadir, 'ext2.xml')

        with open(self.fname, 'w') as xml:
            xml.write('''<?xml version="1.0" encoding="UTF-8" ?>
            <root>
                <foo>3</foo>
                <mptr href="ext1.xml"/>
                <mptr href="ext2.xml"/>
            </root>
            ''')

        with open(ext1, 'w') as xml:
            xml.write('''<?xml version="1.0" encoding="UTF-8" ?>
            <foo>5</foo>
            ''')

        with open(ext2, 'w') as xml:
            xml.write('''<?xml version="1.0" encoding="UTF-8" ?>
            <foo>10</foo>
            ''')

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'xml_filename': self.fname,
                'schema_filename': self.schema
            }
        )

        task.run()

    def test_correct_with_incorrect_external(self):
        ext1 = os.path.join(self.datadir, 'ext1.xml')
        ext2 = os.path.join(self.datadir, 'ext2.xml')

        with open(self.fname, 'w') as xml:
            xml.write('''<?xml version="1.0" encoding="UTF-8" ?>
            <root>
                <foo>3</foo>
                <mptr href="ext1.xml"/>
                <mptr href="ext2.xml"/>
            </root>
            ''')

        with open(ext1, 'w') as xml:
            xml.write('''<?xml version="1.0" encoding="UTF-8" ?>
            <foo>'5'</foo>
            ''')

        with open(ext2, 'w') as xml:
            xml.write('''<?xml version="1.0" encoding="UTF-8" ?>
            <foo>10</foo>
            ''')

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'xml_filename': self.fname,
                'schema_filename': self.schema
            }
        )

        with self.assertRaisesRegexp(etree.DocumentInvalid, 'not a valid value of the atomic type'):
            task.run()

    def test_incorrect_with_correct_external(self):
        ext1 = os.path.join(self.datadir, 'ext1.xml')
        ext2 = os.path.join(self.datadir, 'ext2.xml')

        with open(self.fname, 'w') as xml:
            xml.write('''<?xml version="1.0" encoding="UTF-8" ?>
            <root>
                <foo>'3'</foo>
                <mptr href="ext1.xml"/>
                <mptr href="ext2.xml"/>
            </root>
            ''')

        with open(ext1, 'w') as xml:
            xml.write('''<?xml version="1.0" encoding="UTF-8" ?>
            <foo>5</foo>
            ''')

        with open(ext2, 'w') as xml:
            xml.write('''<?xml version="1.0" encoding="UTF-8" ?>
            <foo>10</foo>
            ''')

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'xml_filename': self.fname,
                'schema_filename': self.schema
            }
        )

        with self.assertRaisesRegexp(etree.DocumentInvalid, 'not a valid value of the atomic type'):
            task.run()

    def test_incorrect_with_incorrect_external(self):
        ext1 = os.path.join(self.datadir, 'ext1.xml')
        ext2 = os.path.join(self.datadir, 'ext2.xml')

        with open(self.fname, 'w') as xml:
            xml.write('''<?xml version="1.0" encoding="UTF-8" ?>
            <root>
                <foo>'3'</foo>
                <mptr href="ext1.xml"/>
                <mptr href="ext2.xml"/>
            </root>
            ''')

        with open(ext1, 'w') as xml:
            xml.write('''<?xml version="1.0" encoding="UTF-8" ?>
            <foo>'5'</foo>
            ''')

        with open(ext2, 'w') as xml:
            xml.write('''<?xml version="1.0" encoding="UTF-8" ?>
            <foo>10</foo>
            ''')

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'xml_filename': self.fname,
                'schema_filename': self.schema
            }
        )

        with self.assertRaisesRegexp(etree.DocumentInvalid, 'not a valid value of the atomic type'):
            task.run()

    def test_external_with_specified_rootdir(self):
        ext1 = os.path.join(self.datadir, 'ext1.xml')
        ext2 = os.path.join(self.datadir, 'ext2.xml')

        with open(self.fname, 'w') as xml:
            xml.write('''<?xml version="1.0" encoding="UTF-8" ?>
            <root>
                <foo>3</foo>
                <mptr href="ext1.xml"/>
                <mptr href="ext2.xml"/>
            </root>
            ''')

        with open(ext1, 'w') as xml:
            xml.write('''<?xml version="1.0" encoding="UTF-8" ?>
            <foo>5</foo>
            ''')

        with open(ext2, 'w') as xml:
            xml.write('''<?xml version="1.0" encoding="UTF-8" ?>
            <foo>10</foo>
            ''')

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'xml_filename': self.fname,
                'schema_filename': self.schema,
                'rootdir': self.datadir,
            }
        )

        task.run()


class ValidateLogicalPhysicalRepresentationTestCase(TransactionTestCase):
    def setUp(self):
        self.taskname = "ESSArch_Core.tasks.ValidateLogicalPhysicalRepresentation"
        self.root = os.path.dirname(os.path.realpath(__file__))
        self.datadir = os.path.join(self.root, "datadir")
        self.fname = os.path.join(self.datadir, 'test1.xml')
        self.ip = InformationPackage.objects.create(label="testip")
        self.user = User.objects.create(username="testuser")

        Path.objects.create(
            entity="path_mimetypes_definitionfile",
            value=os.path.join(self.root, "mime.types")
        )

        self.filesToCreate = {
            self.fname: {
                '-name': 'root',
                '-children': [{
                    '-name': 'object',
                    '-containsFiles': True,
                    '-filters': {'FName': '^((?!' + os.path.basename(self.fname) + ').)*$'},
                    '-children': [
                        {
                            '-name': 'storage',
                            '-children': [{
                                '-name': 'contentLocation',
                                '-children': [{
                                    '-name': 'contentLocationValue',
                                    '#content': [
                                        {
                                            'text': 'file:///',
                                        },
                                        {
                                            'var': 'href'
                                        }
                                    ]
                                }]
                            }]
                        }
                    ]
                }]
            }
        }

        try:
            os.mkdir(self.datadir)
        except OSError as e:
            if e.errno != 17:
                raise

        root = etree.fromstring('<root></root>')

        with open(self.fname, 'w') as f:
            f.write(etree.tostring(root, pretty_print=True, xml_declaration=True, encoding='UTF-8'))

    def tearDown(self):
        shutil.rmtree(self.datadir)

    def test_validation_without_files(self):
        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'xmlfile': self.fname
            }
        )

        task.run()

    def test_validation_with_files(self):
        num_of_files = 3
        files = []

        for i in range(num_of_files):
            fname = os.path.join(self.datadir, '%s.txt' % i)
            with open(fname, 'w') as f:
                f.write('%s' % i)
            files.append(fname)

        ProcessTask.objects.create(
            name='ESSArch_Core.tasks.GenerateXML',
            params={
                'filesToCreate': self.filesToCreate,
                'folderToParse': self.datadir
            }
        ).run()

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'files': files,
                'files_reldir': self.datadir,
                'xmlfile': self.fname,
            }
        )

        task.run()

    def test_validation_with_incorrect_file_name(self):
        num_of_files = 3
        files = []

        for i in range(num_of_files):
            fname = os.path.join(self.datadir, '%s.txt' % i)
            with open(fname, 'w') as f:
                f.write('%s' % i)
            files.append(fname)

        ProcessTask.objects.create(
            name='ESSArch_Core.tasks.GenerateXML',
            params={
                'filesToCreate': self.filesToCreate,
                'folderToParse': self.datadir
            }
        ).run()

        files[0] = string.replace(files[0], 'txt', 'txtx')

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'files': files,
                'files_reldir': self.datadir,
                'xmlfile': self.fname,
            }
        )

        with self.assertRaisesRegexp(AssertionError, "the logical representation differs from the physical"):
            task.run()

    def test_validation_with_too_many_files(self):
        num_of_files = 3
        files = []

        for i in range(num_of_files):
            fname = os.path.join(self.datadir, '%s.txt' % i)
            with open(fname, 'w') as f:
                f.write('%s' % i)
            files.append(fname)

        ProcessTask.objects.create(
            name='ESSArch_Core.tasks.GenerateXML',
            params={
                'filesToCreate': self.filesToCreate,
                'folderToParse': self.datadir
            }
        ).run()

        fname = os.path.join(self.datadir, '%s.txt' % (num_of_files+1))
        files.append(fname)

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'files': files,
                'files_reldir': self.datadir,
                'xmlfile': self.fname,
            }
        )

        with self.assertRaisesRegexp(AssertionError, "the logical representation differs from the physical"):
            task.run()

    def test_validation_with_too_few_files(self):
        num_of_files = 3
        files = []

        for i in range(num_of_files):
            fname = os.path.join(self.datadir, '%s.txt' % i)
            with open(fname, 'w') as f:
                f.write('%s' % i)
            files.append(fname)

        ProcessTask.objects.create(
            name='ESSArch_Core.tasks.GenerateXML',
            params={
                'filesToCreate': self.filesToCreate,
                'folderToParse': self.datadir
            }
        ).run()

        fname = os.path.join(self.datadir, '%s.txt' % (num_of_files+1))
        files.pop()

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'files': files,
                'files_reldir': self.datadir,
                'xmlfile': self.fname,
            }
        )

        with self.assertRaisesRegexp(AssertionError, "the logical representation differs from the physical"):
            task.run()

    def test_validation_with_file_in_wrong_folder(self):
        num_of_files = 3
        files = []

        for i in range(num_of_files):
            fname = os.path.join(self.datadir, '%s.txt' % i)
            with open(fname, 'w') as f:
                f.write('%s' % i)
            files.append(fname)

        ProcessTask.objects.create(
            name='ESSArch_Core.tasks.GenerateXML',
            params={
                'filesToCreate': self.filesToCreate,
                'folderToParse': self.datadir
            }
        ).run()

        moved_file = files[0]
        new_dir = os.path.join(self.datadir, 'new_dir')
        new_file = os.path.join(new_dir, os.path.basename(moved_file))

        os.mkdir(new_dir)
        shutil.move(moved_file, new_file)

        files[0] = new_file

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'files': files,
                'files_reldir': self.datadir,
                'xmlfile': self.fname,
            }
        )

        with self.assertRaisesRegexp(AssertionError, "the logical representation differs from the physical"):
            task.run()


class UpdateIPStatusTestCase(TransactionTestCase):
    def setUp(self):
        self.taskname = "ESSArch_Core.tasks.UpdateIPStatus"
        self.ip = InformationPackage.objects.create(label="testip", state='initial')

    def test_update(self):
        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'ip': self.ip.pk,
                'status': 'new',
                'prev': self.ip.state
            }
        )

        task.run()

        self.ip.refresh_from_db()
        self.assertEqual(self.ip.state, 'new')

    def test_undo(self):
        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'ip': self.ip.pk,
                'status': 'new',
                'prev': self.ip.state
            }
        )

        task.run()

        self.ip.refresh_from_db()
        self.assertEqual(self.ip.state, 'new')

        task.undo()

        self.ip.refresh_from_db()
        self.assertEqual(self.ip.state, 'initial')


class UpdateIPPathTestCase(TransactionTestCase):
    def setUp(self):
        self.taskname = "ESSArch_Core.tasks.UpdateIPPath"
        self.ip = InformationPackage.objects.create(label="testip", object_path='initial')

    def test_update(self):
        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'ip': self.ip.pk,
                'path': 'new',
                'prev': self.ip.object_path
            }
        )

        task.run()

        self.ip.refresh_from_db()
        self.assertEqual(self.ip.object_path, 'new')

    def test_undo(self):
        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'ip': self.ip.pk,
                'path': 'new',
                'prev': self.ip.object_path
            }
        )

        task.run()

        self.ip.refresh_from_db()
        self.assertEqual(self.ip.object_path, 'new')

        task.undo()

        self.ip.refresh_from_db()
        self.assertEqual(self.ip.object_path, 'initial')


class UpdateIPSizeAndCountTestCase(TransactionTestCase):
    def setUp(self):
        self.taskname = "ESSArch_Core.tasks.UpdateIPSizeAndCount"
        self.root = os.path.dirname(os.path.realpath(__file__))
        self.datadir = os.path.join(self.root, "datadir")
        self.ip = InformationPackage.objects.create(object_path=self.datadir)

        try:
            os.mkdir(self.datadir)
        except OSError as e:
            if e.errno != 17:
                raise

    def tearDown(self):
        shutil.rmtree(self.datadir)

    def test_init(self):
        self.assertEqual(self.ip.object_size, 0)
        self.assertEqual(self.ip.object_num_items, 0)

    def test_run_empty(self):
        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'ip': self.ip.pk,
            }
        )

        task.run()

        self.ip.refresh_from_db()
        self.assertEqual(self.ip.object_size, 0)
        self.assertEqual(self.ip.object_num_items, 0)

    def test_add_empty_file_and_run(self):
        open(os.path.join(self.datadir, 'foo.txt'), 'a').close()

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'ip': self.ip.pk,
            }
        )

        task.run()

        self.ip.refresh_from_db()
        self.assertEqual(self.ip.object_size, 0)
        self.assertEqual(self.ip.object_num_items, 1)

    def test_add_file_with_content_and_run(self):
        with open(os.path.join(self.datadir, 'foo.txt'), 'w') as f:
            f.write('foo')

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'ip': self.ip.pk,
            }
        )

        task.run()

        self.ip.refresh_from_db()
        self.assertEqual(self.ip.object_size, 3)
        self.assertEqual(self.ip.object_num_items, 1)

    def test_add_empty_dir_and_run(self):
        os.mkdir(os.path.join(self.datadir, 'foo'))

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'ip': self.ip.pk,
            }
        )

        task.run()

        self.ip.refresh_from_db()
        self.assertEqual(self.ip.object_size, 0)
        self.assertEqual(self.ip.object_num_items, 0)

    def test_add_dir_with_file_with_content_and_run(self):
        os.mkdir(os.path.join(self.datadir, 'foo'))
        with open(os.path.join(self.datadir, 'foo', 'foo.txt'), 'w') as f:
            f.write('foo')

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'ip': self.ip.pk,
            }
        )

        task.run()

        self.ip.refresh_from_db()
        self.assertEqual(self.ip.object_size, 3)
        self.assertEqual(self.ip.object_num_items, 1)

    def test_add_multiple_dirs_with_files_and_run(self):
        os.mkdir(os.path.join(self.datadir, 'foo'))
        os.mkdir(os.path.join(self.datadir, 'bar'))
        with open(os.path.join(self.datadir, 'foo', 'foo.txt'), 'w') as f:
            f.write('foo')

        with open(os.path.join(self.datadir, 'bar', 'bar.txt'), 'w') as f:
            f.write('bar')

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'ip': self.ip.pk,
            }
        )

        task.run()

        self.ip.refresh_from_db()
        self.assertEqual(self.ip.object_size, 6)
        self.assertEqual(self.ip.object_num_items, 2)

    def test_add_multiple_dirs_with_files_with_same_name_and_run(self):
        os.mkdir(os.path.join(self.datadir, 'foo'))
        os.mkdir(os.path.join(self.datadir, 'bar'))
        with open(os.path.join(self.datadir, 'foo', 'foo.txt'), 'w') as f:
            f.write('foo')

        with open(os.path.join(self.datadir, 'bar', 'foo.txt'), 'w') as f:
            f.write('foo')

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'ip': self.ip.pk,
            }
        )

        task.run()

        self.ip.refresh_from_db()
        self.assertEqual(self.ip.object_size, 6)
        self.assertEqual(self.ip.object_num_items, 2)

    def test_object_path_set_to_file_and_run(self):
        with open(os.path.join(self.datadir, 'foo.txt'), 'w') as f:
            f.write('foo')

        self.ip.object_path = os.path.join(self.datadir, 'foo.txt')
        self.ip.save()

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'ip': self.ip.pk,
            }
        )

        task.run()

        self.ip.refresh_from_db()
        self.assertEqual(self.ip.object_size, 3)
        self.assertEqual(self.ip.object_num_items, 1)


class DeleteFilesTestCase(TransactionTestCase):
    def setUp(self):
        self.taskname = "ESSArch_Core.tasks.DeleteFiles"
        self.root = os.path.dirname(os.path.realpath(__file__))
        self.datadir = os.path.join(self.root, "datadir")

        try:
            os.mkdir(self.datadir)
        except OSError as e:
            if e.errno != 17:
                raise

    def tearDown(self):
        shutil.rmtree(self.datadir)

    def test_delete_empty_dir(self):
        dirname = os.path.join(self.datadir, 'newdir')
        os.mkdir(dirname)

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'path': dirname
            }
        )

        task.run()

        self.assertFalse(os.path.isdir(dirname))

    def test_delete_dir_with_files(self):
        dirname = os.path.join(self.datadir, 'newdir')
        os.mkdir(dirname)

        for i in range(3):
            open(os.path.join(dirname, str(i)), 'a').close()

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'path': dirname
            }
        )

        task.run()

        self.assertFalse(os.path.isdir(dirname))

    def test_delete_file(self):
        fname = os.path.join(self.datadir, 'test.txt')
        open(fname, 'a').close()

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'path': fname
            }
        )

        task.run()

        self.assertFalse(os.path.isfile(fname))


class CopyFileTestCase(TransactionTestCase):
    def setUp(self):
        self.taskname = "ESSArch_Core.tasks.CopyFile"
        self.root = os.path.dirname(os.path.realpath(__file__))
        self.datadir = os.path.join(self.root, "datadir")
        self.src = os.path.join(self.datadir, "src.txt")

        try:
            os.mkdir(self.datadir)
        except OSError as e:
            if e.errno != 17:
                raise

    def tearDown(self):
        shutil.rmtree(self.datadir)

    def test_local_empty(self):
        dst = os.path.join(self.datadir, "dst.txt")

        open(self.src, 'a').close()

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'src': self.src,
                'dst': dst
            }
        )

        task.run()

        self.assertTrue(os.path.isfile(self.src))
        self.assertTrue(os.path.isfile(dst))
        self.assertTrue(filecmp.cmp(self.src, dst))

    def test_local_non_empty(self):
        dst = os.path.join(self.datadir, "dst.txt")
        content = 'foo'

        with open(self.src, 'w') as f:
            f.write(content)

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'src': self.src,
                'dst': dst
            }
        )

        task.run()

        self.assertTrue(os.path.isfile(self.src))
        self.assertTrue(os.path.isfile(dst))
        self.assertTrue(filecmp.cmp(self.src, dst))
        self.assertEqual(open(dst).read(), content)

    def test_local_non_ascii_file_name(self):
        src = os.path.join(self.datadir, u'åäö.txt')
        dst = os.path.join(self.datadir, u'öäå.txt')
        content = 'foo'

        with open(src, 'w') as f:
            f.write(content)

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'src': src,
                'dst': dst
            }
        )

        task.run()

        self.assertTrue(os.path.isfile(src))
        self.assertTrue(os.path.isfile(dst))
        self.assertTrue(filecmp.cmp(src, dst))
        self.assertEqual(open(dst).read(), content)

    def test_local_small_block_size(self):
        dst = os.path.join(self.datadir, "dst.txt")
        content = 'foo'

        with open(self.src, 'w') as f:
            f.write(content)

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'src': self.src,
                'dst': dst,
                'block_size': 1
            }
        )

        task.run()

        self.assertTrue(os.path.isfile(self.src))
        self.assertTrue(os.path.isfile(dst))
        self.assertTrue(filecmp.cmp(self.src, dst))
        self.assertEqual(open(dst).read(), content)

    def test_local_dst_existing(self):
        dst = os.path.join(self.datadir, "dst.txt")
        content = 'foo'
        dstcontent = 'bar'

        with open(self.src, 'w') as f:
            f.write(content)

        with open(dst, 'w') as f:
            f.write(dstcontent)

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'src': self.src,
                'dst': dst,
            }
        )

        task.run()

        self.assertTrue(os.path.isfile(self.src))
        self.assertTrue(os.path.isfile(dst))
        self.assertTrue(filecmp.cmp(self.src, dst))
        self.assertEqual(open(dst).read(), content)

    @mock.patch('ESSArch_Core.tasks.requests.Session.post')
    @mock.patch('ESSArch_Core.tasks.CopyChunk.run', side_effect=lambda *args, **kwargs: None)
    def test_remote(self, mock_copy_chunk, mock_post):
        fname = "src.txt"
        src = os.path.join(self.datadir, fname)
        dst = "http://remote.destination/upload"
        session = requests.Session()

        with open(src, 'w') as f:
            f.write('foo')

        task = ProcessTask.objects.create(
            name=self.taskname,
            args=[src, dst],
            params={
                'requests_session': session,
                'block_size': 1
            }
        )
        task.run().get()

        calls = [
            mock.call(src, dst, 0, file_size=3, block_size=1, requests_session=mock.ANY),
            mock.call(src, dst, 1, file_size=3, block_size=1, requests_session=mock.ANY, upload_id=None,),
            mock.call(src, dst, 2, file_size=3, block_size=1, requests_session=mock.ANY, upload_id=None,),
            mock.call(src, dst, 3, file_size=3, block_size=1, requests_session=mock.ANY, upload_id=None,),
        ]
        mock_copy_chunk.assert_has_calls(calls)

        mock_post.assert_called_once_with(
            dst + '_complete/',
            data=mock.ANY, headers={'Content-Type': mock.ANY},
        )


class CopyChunkTestCase(TransactionTestCase):
    def setUp(self):
        self.taskname = "ESSArch_Core.tasks.CopyChunk"
        self.root = os.path.dirname(os.path.realpath(__file__))
        self.datadir = os.path.join(self.root, "datadir")

        try:
            os.mkdir(self.datadir)
        except OSError as e:
            if e.errno != 17:
                raise

    def tearDown(self):
        shutil.rmtree(self.datadir)

    @mock.patch('ESSArch_Core.tasks.requests.Session.post')
    def test_remote(self, mock_post):
        fname = "src.txt"
        src = os.path.join(self.datadir, fname)
        dst = "http://remote.destination/upload"
        session = requests.Session()

        attrs = {'json.return_value': {'upload_id': uuid.uuid4().hex}}
        mock_response = mock.Mock()
        mock_response.configure_mock(**attrs)

        mock_post.return_value = mock_response

        with open(src, 'w') as f:
            f.write('foo')

        upload_id = uuid.uuid4().hex

        ProcessTask.objects.create(
            name=self.taskname,
            args=[src, dst, 1, upload_id],
            params={
                'requests_session': session,
                'block_size': 1,
                'file_size': 3,
            }
        ).run().get()

        mock_post.assert_called_once_with(
            dst, files={'the_file': ('src.txt', 'o')},
            data={'upload_id': upload_id},
            headers={'Content-Range': 'bytes 1-1/3'},
        )

    @mock.patch('ESSArch_Core.tasks.requests.Session.post')
    def test_remote_server_error(self, mock_post):
        attrs = {'raise_for_status.side_effect': requests.exceptions.HTTPError}
        mock_response = mock.Mock()
        mock_response.configure_mock(**attrs)

        mock_post.return_value = mock_response

        fname = "src.txt"
        src = os.path.join(self.datadir, fname)
        dst = "http://remote.destination/upload"
        session = requests.Session()

        with open(src, 'w') as f:
            f.write('foo')

        upload_id = uuid.uuid4().hex

        with self.assertRaises(requests.exceptions.HTTPError):
            ProcessTask.objects.create(
                name=self.taskname,
                args=[src, dst, 1, upload_id],
                params={
                    'requests_session': session,
                    'block_size': 1,
                    'file_size': 3,
                }
            ).run().get()

        mock_post.assert_called_once_with(
            dst, files={'the_file': ('src.txt', 'o')},
            data={'upload_id': upload_id},
            headers={'Content-Range': 'bytes 1-1/3'},
        )

class SendEmailTestCase(TransactionTestCase):
    def setUp(self):
        self.taskname = 'ESSArch_Core.tasks.SendEmail'

        self.sender = 'from@example.com'
        self.recipients = ['to1@example.com', 'to2@example2.com']
        self.subject = 'this is the subject'
        self.body = 'this is the body'

        self.root = os.path.dirname(os.path.realpath(__file__))
        self.datadir = os.path.join(self.root, "datadir")

        try:
            os.mkdir(self.datadir)
        except OSError as e:
            if e.errno != 17:
                raise

        self.fname = os.path.join(self.datadir, "file1.txt")

    def tearDown(self):
        shutil.rmtree(self.datadir)

    def test_send(self):
        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'sender': self.sender,
                'recipients': self.recipients,
                'subject': self.subject,
                'body': self.body
            }
        )

        task.run()

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, self.subject)

    def test_send_attachments(self):
        with open(self.fname, 'w') as f:
            f.write('foo')

        attachments = [self.fname]

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'sender': self.sender,
                'recipients': self.recipients,
                'subject': self.subject,
                'body': self.body,
                'attachments': attachments
            }
        )

        task.run()

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, self.subject)
        self.assertEqual(len(mail.outbox[0].attachments), 1)
        self.assertEqual(mail.outbox[0].attachments[0][0], os.path.basename(attachments[0]))


class ConvertFileTestCase(TransactionTestCase):
    def setUp(self):
        self.taskname = 'ESSArch_Core.tasks.ConvertFile'

        self.root = os.path.dirname(os.path.realpath(__file__))
        self.datadir = os.path.join(self.root, "datadir")

        try:
            os.mkdir(self.datadir)
        except OSError as e:
            if e.errno != 17:
                raise

    def tearDown(self):
        try:
            shutil.rmtree(self.datadir)
        except:
            pass

    def test_doc_to_pdf(self):
        fpath = os.path.join(self.datadir, "file1.docx")
        open(fpath, 'a').close()

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'filepath': fpath,
                'new_format': 'pdf'
            }
        )

        task.run().get()

        self.assertTrue(os.path.isfile(os.path.join(self.datadir, 'file1.pdf')))

    def test_docx_to_pdf(self):
        fpath = os.path.join(self.datadir, "file1.docx")
        open(fpath, 'a').close()

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'filepath': fpath,
                'new_format': 'pdf'
            }
        )

        task.run().get()

        self.assertTrue(os.path.isfile(os.path.join(self.datadir, 'file1.pdf')))


@override_settings(CELERY_ALWAYS_EAGER=True, CELERY_EAGER_PROPAGATES_EXCEPTIONS=True)
class MountTapeTestCase(TransactionTestCase):
    def setUp(self):
        self.taskname = 'ESSArch_Core.tasks.MountTape'

        self.datadir = tempfile.mkdtemp()
        self.label_dir = Path.objects.create(entity='label', value=os.path.join(self.datadir, 'label'))
        self.tape_drive_device = tempfile.NamedTemporaryFile(dir=self.datadir, delete=False)

        user = User.objects.create()

        self.robot = Robot.objects.create(device='/dev/sg6')
        self.tape_drive = TapeDrive.objects.create(pk=0, device=self.tape_drive_device.name, robot=self.robot)
        self.tape_slot = TapeSlot.objects.create(slot_id=0, robot=self.robot)

        self.target = StorageTarget.objects.create()
        self.medium = StorageMedium.objects.create(
            storage_target=self.target, status=20, location_status=20,
            block_size=self.target.default_block_size,
            format=self.target.default_format, agent=user,
            tape_slot=self.tape_slot
        )

        try:
            os.mkdir(self.label_dir.value)
        except OSError as e:
            if e.errno != 17:
                raise

    def tearDown(self):
        shutil.rmtree(self.datadir)

    @mock.patch('ESSArch_Core.tasks.create_tape_label')
    @mock.patch('ESSArch_Core.tasks.verify_tape_label')
    @mock.patch('ESSArch_Core.tasks.tarfile')
    @mock.patch('ESSArch_Core.storage.tape.is_tape_drive_online')
    @mock.patch('ESSArch_Core.tasks.mount_tape')
    def test_mount_tape_without_label_file(self, mock_mount, mock_online, mock_tarfile, mock_verify_label, mock_create_label):
        self.medium.format = 100
        self.medium.save(update_fields=['format'])

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'medium': self.medium.pk,
                'drive': self.tape_drive.pk,
            },
        )

        task.run().get()

        mock_tarfile.open.assert_not_called()

        mock_mount.assert_called_once_with(self.robot.device, self.tape_slot.slot_id, self.tape_drive.pk)
        mock_online.assert_called_once_with(self.tape_drive.device)

        mock_create_label.assert_not_called()
        mock_verify_label.assert_not_called()

        self.medium.refresh_from_db()
        self.tape_drive.refresh_from_db()

        self.assertEqual(self.medium.num_of_mounts, 1)
        self.assertEqual(self.tape_drive.num_of_mounts, 1)
        self.assertTrue(self.medium.tape_drive == self.tape_drive)

    @mock.patch('ESSArch_Core.tasks.verify_tape_label')
    @mock.patch('ESSArch_Core.tasks.tarfile')
    @mock.patch('ESSArch_Core.tasks.tape_empty')
    @mock.patch('ESSArch_Core.storage.tape.is_tape_drive_online')
    @mock.patch('ESSArch_Core.tasks.mount_tape')
    def test_mount_tape_with_valid_label_file(self, mock_mount, mock_online, mock_empty, mock_tarfile, mock_verify_label):
        mock_empty.return_value = False
        mock_verify_label.return_value = True

        mocked_tarmember = mock.Mock()
        mocked_tarmember.configure_mock(name='file_label.xml')

        mocked_tar = mock.Mock()
        mocked_tar.configure_mock(**{
            'getmembers.return_value': [mocked_tarmember],
            'extractfile.return_value.read.return_value': 'xmldata',
        })

        mock_tarfile.open.return_value = mocked_tar

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'medium': self.medium.pk,
                'drive': self.tape_drive.pk,
            },
        )

        task.run().get()

        mock_mount.assert_called_once_with(self.robot.device, self.tape_slot.slot_id, self.tape_drive.pk)
        mock_online.assert_called_once_with(self.tape_drive.device)
        mock_verify_label.assert_called_once_with(self.medium, 'xmldata')

        self.medium.refresh_from_db()
        self.tape_drive.refresh_from_db()

        self.assertEqual(self.medium.num_of_mounts, 1)
        self.assertEqual(self.tape_drive.num_of_mounts, 1)
        self.assertTrue(self.medium.tape_drive == self.tape_drive)

    @mock.patch('ESSArch_Core.tasks.verify_tape_label')
    @mock.patch('ESSArch_Core.tasks.tarfile')
    @mock.patch('ESSArch_Core.tasks.tape_empty')
    @mock.patch('ESSArch_Core.storage.tape.is_tape_drive_online')
    @mock.patch('ESSArch_Core.tasks.mount_tape')
    def test_mount_tape_with_invalid_label_file(self, mock_mount, mock_online, mock_empty, mock_tarfile, mock_verify_label):
        mock_empty.return_value = False
        mock_verify_label.return_value = False

        mocked_tarmember = mock.Mock()
        mocked_tarmember.configure_mock(name='file_label.xml')

        mocked_tar = mock.Mock()
        mocked_tar.configure_mock(**{
            'getmembers.return_value': [mocked_tarmember],
            'extractfile.return_value.read.return_value': 'xmldata',
        })

        mock_tarfile.open.return_value = mocked_tar

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'medium': self.medium.pk,
                'drive': self.tape_drive.pk,
            },
        )

        with self.assertRaisesRegexp(ValueError, 'labelfile with wrong'):
            task.run().get()

        self.medium.refresh_from_db()
        self.tape_drive.refresh_from_db()

        self.assertEqual(self.medium.num_of_mounts, 0)
        self.assertEqual(self.tape_drive.num_of_mounts, 0)
        self.assertFalse(self.medium.tape_drive == self.tape_drive)

    @mock.patch('ESSArch_Core.tasks.write_to_tape')
    @mock.patch('ESSArch_Core.tasks.create_tape_label')
    @mock.patch('ESSArch_Core.tasks.rewind_tape')
    @mock.patch('ESSArch_Core.tasks.tarfile')
    @mock.patch('ESSArch_Core.tasks.tape_empty')
    @mock.patch('ESSArch_Core.storage.tape.is_tape_drive_online')
    @mock.patch('ESSArch_Core.tasks.mount_tape')
    def test_mount_tape_with_reuse_file(self, mock_mount, mock_online, mock_empty, mock_tarfile, mock_rewind, mock_create_label, mock_write_tape):
        mock_empty.return_value = False

        mocked_tarmember = mock.Mock()
        mocked_tarmember.configure_mock(name='reuse')

        mocked_tar = mock.Mock()
        mocked_tar.configure_mock(**{'getmembers.return_value': [mocked_tarmember]})

        mock_tarfile.open.return_value = mocked_tar

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'medium': self.medium.pk,
                'drive': self.tape_drive.pk,
            },
        )

        task.run().get()

        mock_mount.assert_called_once_with(self.robot.device, self.tape_slot.slot_id, self.tape_drive.pk)
        mock_online.assert_called_once_with(self.tape_drive.device)
        mock_rewind.assert_called_once_with(self.tape_drive.device)
        mock_create_label.assert_called_once()
        mock_write_tape.called_once_with(self.tape_drive.device, mock.ANY)

        self.medium.refresh_from_db()
        self.tape_drive.refresh_from_db()

        self.assertEqual(self.medium.num_of_mounts, 1)
        self.assertEqual(self.tape_drive.num_of_mounts, 1)
        self.assertTrue(self.medium.tape_drive == self.tape_drive)

    @mock.patch('ESSArch_Core.tasks.tarfile')
    @mock.patch('ESSArch_Core.tasks.tape_empty')
    @mock.patch('ESSArch_Core.storage.tape.is_tape_drive_online')
    @mock.patch('ESSArch_Core.tasks.mount_tape')
    def test_mount_tape_with_unknown_information(self, mock_mount, mock_online, mock_empty, mock_tarfile):
        mock_empty.return_value = False

        mocked_tarmember = mock.Mock()
        mocked_tarmember.configure_mock(name='foo')

        mocked_tar = mock.Mock()
        mocked_tar.configure_mock(**{'getmembers.return_value': [mocked_tarmember]})

        mock_tarfile.open.return_value = mocked_tar

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'medium': self.medium.pk,
                'drive': self.tape_drive.pk,
            },
        )

        with self.assertRaisesRegexp(ValueError, 'unknown information'):
            task.run().get()

        mock_mount.assert_called_once_with(self.robot.device, self.tape_slot.slot_id, self.tape_drive.pk)
        mock_online.assert_called_once_with(self.tape_drive.device)

        self.medium.refresh_from_db()
        self.tape_drive.refresh_from_db()

        self.assertEqual(self.medium.num_of_mounts, 0)
        self.assertEqual(self.tape_drive.num_of_mounts, 0)
        self.assertFalse(self.medium.tape_drive == self.tape_drive)

    @mock.patch('ESSArch_Core.tasks.write_to_tape')
    @mock.patch('ESSArch_Core.tasks.rewind_tape')
    @mock.patch('ESSArch_Core.tasks.create_tape_label')
    @mock.patch('ESSArch_Core.tasks.tape_empty')
    @mock.patch('ESSArch_Core.storage.tape.is_tape_drive_online')
    @mock.patch('ESSArch_Core.tasks.mount_tape')
    def test_mount_empty_tape(self, mock_mount, mock_check_online, mock_tape_empty, mock_create_label, mock_rewind, mock_write_tape):
        mock_tape_empty.return_value = True

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'medium': self.medium.pk,
                'drive': self.tape_drive.pk,
            },
        )

        task.run().get()

        mock_create_label.called_once()
        mock_rewind.assert_called_once_with(self.tape_drive.device)
        mock_write_tape.called_once_with(self.tape_drive.device, mock.ANY)

        self.medium.refresh_from_db()
        self.tape_drive.refresh_from_db()

        self.assertEqual(self.medium.num_of_mounts, 1)
        self.assertEqual(self.tape_drive.num_of_mounts, 1)
        self.assertTrue(self.medium.tape_drive == self.tape_drive)


@override_settings(CELERY_ALWAYS_EAGER=True, CELERY_EAGER_PROPAGATES_EXCEPTIONS=True)
class UnmountTapeTestCase(TransactionTestCase):
    def setUp(self):
        self.taskname = 'ESSArch_Core.tasks.UnmountTape'

        user = User.objects.create()

        self.robot = Robot.objects.create(device='/dev/sg6')
        self.tape_drive = TapeDrive.objects.create(pk=0, device='/dev/nst0', robot=self.robot)
        self.tape_slot = TapeSlot.objects.create(slot_id=0, robot=self.robot)

        self.target = StorageTarget.objects.create()
        self.medium = StorageMedium.objects.create(
            storage_target=self.target, status=20, location_status=20,
            block_size=self.target.default_block_size,
            format=self.target.default_format, agent=user,
            tape_slot=self.tape_slot
        )

    @mock.patch('ESSArch_Core.tasks.unmount_tape')
    def test_unmount_drive_without_tape(self, mock_unmount):
        mock_unmount.return_value = None

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'drive': self.tape_drive.pk,
            },
        )

        with self.assertRaises(ValueError):
            task.run().get()

        mock_unmount.assert_not_called()

    @mock.patch('ESSArch_Core.tasks.unmount_tape')
    def test_unmount_drive_with_tape(self, mock_unmount):
        mock_unmount.return_value = None

        self.medium.tape_drive = self.tape_drive
        self.medium.save(update_fields=['tape_drive'])

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'drive': self.tape_drive.pk,
            },
        )

        task.run().get()

        mock_unmount.assert_called_once_with(self.robot.device, self.tape_slot.slot_id, self.tape_drive.pk)

        self.medium.refresh_from_db()

        self.assertIsNone(self.medium.tape_drive)


@override_settings(CELERY_ALWAYS_EAGER=True, CELERY_EAGER_PROPAGATES_EXCEPTIONS=True)
class RewindTapeTestCase(TransactionTestCase):
    def setUp(self):
        self.taskname = 'ESSArch_Core.tasks.RewindTape'

        user = User.objects.create()

        self.robot = Robot.objects.create(device='/dev/sg6')
        self.tape_drive = TapeDrive.objects.create(pk=0, device='/dev/nst0', robot=self.robot)
        self.tape_slot = TapeSlot.objects.create(slot_id=0, robot=self.robot)

        self.target = StorageTarget.objects.create()
        self.medium = StorageMedium.objects.create(
            storage_target=self.target, status=20, location_status=20,
            block_size=self.target.default_block_size,
            format=self.target.default_format, agent=user,
            tape_slot=self.tape_slot
        )

    @mock.patch('ESSArch_Core.tasks.rewind_tape')
    def test_rewind_unmounted_tape(self, mock_rewind):
        mock_rewind.return_value = None

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'medium': self.medium.pk,
            },
        )

        with self.assertRaises(ValueError):
            task.run().get()

        mock_rewind.assert_not_called()

    @mock.patch('ESSArch_Core.tasks.rewind_tape')
    def test_rewind_mounted_tape(self, mock_rewind):
        mock_rewind.return_value = None

        self.medium.tape_drive = self.tape_drive
        self.medium.save(update_fields=['tape_drive'])

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'medium': self.medium.pk,
            },
        )

        task.run().get()

        mock_rewind.assert_called_once_with(self.tape_drive.device)


@override_settings(CELERY_ALWAYS_EAGER=True, CELERY_EAGER_PROPAGATES_EXCEPTIONS=True)
class WriteToTapeTestCase(TransactionTestCase):
    def setUp(self):
        self.taskname = 'ESSArch_Core.tasks.WriteToTape'

        user = User.objects.create()

        self.robot = Robot.objects.create(device='/dev/sg6')
        self.tape_drive = TapeDrive.objects.create(pk=0, device='/dev/nst0', robot=self.robot)
        self.tape_slot = TapeSlot.objects.create(slot_id=0, robot=self.robot)

        self.target = StorageTarget.objects.create()
        self.medium = StorageMedium.objects.create(
            storage_target=self.target, status=20, location_status=20,
            block_size=self.target.default_block_size,
            format=self.target.default_format, agent=user,
            tape_slot=self.tape_slot
        )

        self.temp = tempfile.NamedTemporaryFile()

    @mock.patch('ESSArch_Core.tasks.write_to_tape')
    def test_write_unmounted_tape(self, mock_write):
        mock_write.return_value = None

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'medium': self.medium.pk,
                'path': self.temp.name,
            },
        )

        with self.assertRaises(ValueError):
            task.run().get()

        mock_write.assert_not_called()

    @mock.patch('ESSArch_Core.tasks.write_to_tape')
    def test_write_mounted_tape(self, mock_write):
        mock_write.return_value = None

        self.medium.tape_drive = self.tape_drive
        self.medium.save(update_fields=['tape_drive'])

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'medium': self.medium.pk,
                'path': self.temp.name,
            },
        )

        task.run().get()

        mock_write.assert_called_once_with(self.tape_drive.device, path=self.temp.name, block_size=DEFAULT_TAPE_BLOCK_SIZE)


@override_settings(CELERY_ALWAYS_EAGER=True, CELERY_EAGER_PROPAGATES_EXCEPTIONS=True)
class ReadTapeTestCase(TransactionTestCase):
    def setUp(self):
        self.taskname = 'ESSArch_Core.tasks.ReadTape'

        user = User.objects.create()

        self.robot = Robot.objects.create(device='/dev/sg6')
        self.tape_drive = TapeDrive.objects.create(pk=0, device='/dev/nst0', robot=self.robot)
        self.tape_slot = TapeSlot.objects.create(slot_id=0, robot=self.robot)

        self.target = StorageTarget.objects.create()
        self.medium = StorageMedium.objects.create(
            storage_target=self.target, status=20, location_status=20,
            block_size=self.target.default_block_size,
            format=self.target.default_format, agent=user,
            tape_slot=self.tape_slot
        )

        self.temp = tempfile.NamedTemporaryFile()

    @mock.patch('ESSArch_Core.tasks.read_tape')
    def test_read_unmounted_tape(self, mock_read):
        mock_read.return_value = None

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'medium': self.medium.pk,
                'path': self.temp.name,
            },
        )

        with self.assertRaises(ValueError):
            task.run().get()

        mock_read.assert_not_called()

    @mock.patch('ESSArch_Core.tasks.read_tape')
    def test_read_mounted_tape(self, mock_read):
        mock_read.return_value = None

        self.medium.tape_drive = self.tape_drive
        self.medium.save(update_fields=['tape_drive'])

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'medium': self.medium.pk,
                'path': self.temp.name,
            },
        )

        task.run().get()

        mock_read.assert_called_once_with(self.tape_drive.device, path=self.temp.name, block_size=DEFAULT_TAPE_BLOCK_SIZE)


@override_settings(CELERY_ALWAYS_EAGER=True, CELERY_EAGER_PROPAGATES_EXCEPTIONS=True)
class GetTapeFileNumberTestCase(TransactionTestCase):
    def setUp(self):
        self.taskname = 'ESSArch_Core.tasks.GetTapeFileNumber'

        user = User.objects.create()

        self.robot = Robot.objects.create(device='/dev/sg6')
        self.tape_drive = TapeDrive.objects.create(pk=0, device='/dev/nst0', robot=self.robot)
        self.tape_slot = TapeSlot.objects.create(slot_id=0, robot=self.robot)

        self.target = StorageTarget.objects.create()
        self.medium = StorageMedium.objects.create(
            storage_target=self.target, status=20, location_status=20,
            block_size=self.target.default_block_size,
            format=self.target.default_format, agent=user,
            tape_slot=self.tape_slot
        )

    @mock.patch('ESSArch_Core.tasks.get_tape_file_number')
    def test_get_file_number_unmounted_tape(self, mock_get_file_number):
        num = 5
        mock_get_file_number.return_value = 5

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'medium': self.medium.pk,
            },
        )

        with self.assertRaises(ValueError):
            task.run().get()

        mock_get_file_number.assert_not_called()

    @mock.patch('ESSArch_Core.tasks.get_tape_file_number')
    def test_get_file_number_mounted_tape(self, mock_get_file_number):
        num = 5
        mock_get_file_number.return_value = num

        self.medium.tape_drive = self.tape_drive
        self.medium.save(update_fields=['tape_drive'])

        temp = tempfile.NamedTemporaryFile()

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'medium': self.medium.pk,
            },
        )

        task.run().get()

        task.refresh_from_db()

        mock_get_file_number.assert_called_once_with(self.tape_drive.device)
        self.assertEqual(task.result, num)


@override_settings(CELERY_ALWAYS_EAGER=True, CELERY_EAGER_PROPAGATES_EXCEPTIONS=True)
class SetTapeFileNumberTestCase(TransactionTestCase):
    def setUp(self):
        self.taskname = 'ESSArch_Core.tasks.SetTapeFileNumber'

        user = User.objects.create()

        self.robot = Robot.objects.create(device='/dev/sg6')
        self.tape_drive = TapeDrive.objects.create(pk=0, device='/dev/nst0', robot=self.robot)
        self.tape_slot = TapeSlot.objects.create(slot_id=0, robot=self.robot)

        self.target = StorageTarget.objects.create()
        self.medium = StorageMedium.objects.create(
            storage_target=self.target, status=20, location_status=20,
            block_size=self.target.default_block_size,
            format=self.target.default_format, agent=user,
            tape_slot=self.tape_slot
        )

    @mock.patch('ESSArch_Core.tasks.set_tape_file_number')
    def test_set_file_number_unmounted_tape(self, mock_set_file_number):
        mock_set_file_number.return_value = None

        num = 5

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'medium': self.medium.pk,
                'num': num,
            },
        )

        with self.assertRaises(ValueError):
            task.run().get()

        mock_set_file_number.assert_not_called()

    @mock.patch('ESSArch_Core.tasks.set_tape_file_number')
    def test_set_file_number_mounted_tape(self, mock_set_file_number):
        mock_set_file_number.return_value = None

        self.medium.tape_drive = self.tape_drive
        self.medium.save(update_fields=['tape_drive'])

        num = 5

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'medium': self.medium.pk,
                'num': num,
            },
        )

        task.run().get()

        mock_set_file_number.assert_called_once_with(self.tape_drive.device, num)
