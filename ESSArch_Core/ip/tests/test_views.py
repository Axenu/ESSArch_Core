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

from rest_framework.test import APITestCase

from ESSArch_Core.ip.models import (
    ArchivalInstitution,
    ArchivistOrganization,
    ArchivalType,
    ArchivalLocation,
    InformationPackage,
)


class ArchivalInstitutionTests(APITestCase):
    def setUp(self):
        self.url = '/api/archival-institutions/'

    def test_list(self):
        a1 = ArchivalInstitution.objects.create(name='a1')

        response = self.client.get(self.url)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], str(a1.pk))
        self.assertEqual(response.data[0]['name'], a1.name)

    def test_detail(self):
        a1 = ArchivalInstitution.objects.create(name='a1')
        a2 = ArchivalInstitution.objects.create(name='a2')

        response = self.client.get('%s%s/' % (self.url, a1.pk))
        self.assertEqual(response.data['id'], str(a1.pk))
        self.assertEqual(response.data['name'], a1.name)

        response = self.client.get('%s%s/' % (self.url, a2.pk))
        self.assertEqual(response.data['id'], str(a2.pk))
        self.assertEqual(response.data['name'], a2.name)

    def test_filter_ip_state(self):
        a1 = ArchivalInstitution.objects.create(name='a1')
        a2 = ArchivalInstitution.objects.create(name='a2')

        ip1 = InformationPackage.objects.create(
            State='state1', ArchivalInstitution=a1
        )
        ip2 = InformationPackage.objects.create(
            State='state2', ArchivalInstitution=a2
        )

        response = self.client.get(self.url, {'ip_state': ip1.State})
        self.assertEqual(response.data[0]['id'], str(a1.pk))
        self.assertEqual(response.data[0]['name'], a1.name)

        response = self.client.get(self.url, {'ip_state': ip2.State})
        self.assertEqual(response.data[0]['id'], str(a2.pk))
        self.assertEqual(response.data[0]['name'], a2.name)

        response = self.client.get(self.url, {'ip_state': 'new_state'})
        self.assertEqual(response.data, [])


class ArchivistOrganizationTests(APITestCase):
    def setUp(self):
        self.url = '/api/archivist-organizations/'

    def test_list(self):
        a1 = ArchivistOrganization.objects.create(name='a1')

        response = self.client.get(self.url)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], str(a1.pk))
        self.assertEqual(response.data[0]['name'], a1.name)

    def test_detail(self):
        a1 = ArchivistOrganization.objects.create(name='a1')
        a2 = ArchivistOrganization.objects.create(name='a2')

        response = self.client.get('%s%s/' % (self.url, a1.pk))
        self.assertEqual(response.data['id'], str(a1.pk))
        self.assertEqual(response.data['name'], a1.name)

        response = self.client.get('%s%s/' % (self.url, a2.pk))
        self.assertEqual(response.data['id'], str(a2.pk))
        self.assertEqual(response.data['name'], a2.name)

    def test_filter_ip_state(self):
        a1 = ArchivistOrganization.objects.create(name='a1')
        a2 = ArchivistOrganization.objects.create(name='a2')

        ip1 = InformationPackage.objects.create(
            State='state1', ArchivistOrganization=a1
        )
        ip2 = InformationPackage.objects.create(
            State='state2', ArchivistOrganization=a2
        )

        response = self.client.get(self.url, {'ip_state': ip1.State})
        self.assertEqual(response.data[0]['id'], str(a1.pk))
        self.assertEqual(response.data[0]['name'], a1.name)

        response = self.client.get(self.url, {'ip_state': ip2.State})
        self.assertEqual(response.data[0]['id'], str(a2.pk))
        self.assertEqual(response.data[0]['name'], a2.name)

        response = self.client.get(self.url, {'ip_state': 'new_state'})
        self.assertEqual(response.data, [])


class ArchivalTypeTests(APITestCase):
    def setUp(self):
        self.url = '/api/archival-types/'

    def test_list(self):
        a1 = ArchivalType.objects.create(name='a1')

        response = self.client.get(self.url)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], str(a1.pk))
        self.assertEqual(response.data[0]['name'], a1.name)

    def test_detail(self):
        a1 = ArchivalType.objects.create(name='a1')
        a2 = ArchivalType.objects.create(name='a2')

        response = self.client.get('%s%s/' % (self.url, a1.pk))
        self.assertEqual(response.data['id'], str(a1.pk))
        self.assertEqual(response.data['name'], a1.name)

        response = self.client.get('%s%s/' % (self.url, a2.pk))
        self.assertEqual(response.data['id'], str(a2.pk))
        self.assertEqual(response.data['name'], a2.name)

    def test_filter_ip_state(self):
        a1 = ArchivalType.objects.create(name='a1')
        a2 = ArchivalType.objects.create(name='a2')

        ip1 = InformationPackage.objects.create(
            State='state1', ArchivalType=a1
        )
        ip2 = InformationPackage.objects.create(
            State='state2', ArchivalType=a2
        )

        response = self.client.get(self.url, {'ip_state': ip1.State})
        self.assertEqual(response.data[0]['id'], str(a1.pk))
        self.assertEqual(response.data[0]['name'], a1.name)

        response = self.client.get(self.url, {'ip_state': ip2.State})
        self.assertEqual(response.data[0]['id'], str(a2.pk))
        self.assertEqual(response.data[0]['name'], a2.name)

        response = self.client.get(self.url, {'ip_state': 'new_state'})
        self.assertEqual(response.data, [])


class ArchivalLocationTests(APITestCase):
    def setUp(self):
        self.url = '/api/archival-locations/'

    def test_list(self):
        a1 = ArchivalLocation.objects.create(name='a1')

        response = self.client.get(self.url)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], str(a1.pk))
        self.assertEqual(response.data[0]['name'], a1.name)

    def test_detail(self):
        a1 = ArchivalLocation.objects.create(name='a1')
        a2 = ArchivalLocation.objects.create(name='a2')

        response = self.client.get('%s%s/' % (self.url, a1.pk))
        self.assertEqual(response.data['id'], str(a1.pk))
        self.assertEqual(response.data['name'], a1.name)

        response = self.client.get('%s%s/' % (self.url, a2.pk))
        self.assertEqual(response.data['id'], str(a2.pk))
        self.assertEqual(response.data['name'], a2.name)

    def test_filter_ip_state(self):
        a1 = ArchivalLocation.objects.create(name='a1')
        a2 = ArchivalLocation.objects.create(name='a2')

        ip1 = InformationPackage.objects.create(
            State='state1', ArchivalLocation=a1
        )
        ip2 = InformationPackage.objects.create(
            State='state2', ArchivalLocation=a2
        )

        response = self.client.get(self.url, {'ip_state': ip1.State})
        self.assertEqual(response.data[0]['id'], str(a1.pk))
        self.assertEqual(response.data[0]['name'], a1.name)

        response = self.client.get(self.url, {'ip_state': ip2.State})
        self.assertEqual(response.data[0]['id'], str(a2.pk))
        self.assertEqual(response.data[0]['name'], a2.name)

        response = self.client.get(self.url, {'ip_state': 'new_state'})
        self.assertEqual(response.data, [])
