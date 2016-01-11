# (c) Copyright 2015 Hewlett Packard Enterprise Development Company LP
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#


import unittest
from yaml import safe_load

from swiftlm.rings.ring_model import RingSpecifications, RingSpecification,\
    DeviceInfo, DriveConfiguration, SwiftModelException
from swiftlm.rings.hlm_model import InputModel

from tests.data.rings_ringspecs import ringspec_simple, ringspec_region_zones
from tests.data.rings_data import device_info_simple, \
    drive_configuration_simple, drive_configuration_simple_iter


class TestRingSpecs(unittest.TestCase):

    def test_ringspec_load(self):
        model = {'name': 'dummy',
                 'partition_power': 1,
                 'replication_policy': {'replica_count': 3},
                 'min_part_time': 2,
                 'display_name': 'dummy_display',
                 'balance': 100.0,
                 'weight_step': 30}
        ringspec = RingSpecification(None)
        ringspec.load_model(model)
        self.assertEquals(ringspec.name, 'dummy')
        self.assertEquals(ringspec.display_name, 'dummy_display')
        self.assertEquals(ringspec.partition_power, 1)
        self.assertEquals(ringspec.min_part_time, 2)
        self.assertEquals(ringspec.balance, 100.0)
        self.assertRaises(AttributeError, ringspec.__getattr__, 'junk')
        self.assertEquals(ringspec.replica_count, 3.0)
        self.assertEquals(ringspec.weight_step, 30.0)

    def test_simple_ringspecs(self):
        ring_model = RingSpecifications(model=safe_load(ringspec_simple))
        self.assertEquals(
            ring_model.keystone_ring_specifications[0].region_name, 'region1')

    def test_storage_policies(self):
        ring_model = RingSpecifications(model=safe_load(ringspec_simple))
        sp = ring_model.get_storage_policies('region1')
        self.assertEquals(sp['storage_policies'][0]['policy']['index'], 0)

    def test_load_region_zones(self):
        ring_model = RingSpecifications(model=safe_load(ringspec_region_zones))
        self.assertEquals(
            ring_model.keystone_ring_specifications[0].region_name, 'region1')
        self.assertEquals(
            ring_model.keystone_ring_specifications[1].region_name, 'region2')

    def test_opaque_rack_ids(self):
        ring_model = RingSpecifications(model=safe_load(ringspec_region_zones))
        r, z = ring_model.get_region_zone('region1', 'account', 21)
        self.assertEquals((r, z), (2, -1))
        r, z = ring_model.get_region_zone('region1', 'account', '21')
        self.assertEquals((r, z), (2, -1))
        r, z = ring_model.get_region_zone('region2', 'account', '51')
        self.assertEquals((r, z), (5, 6))

    def test_rack_ids(self):
        scenarios = [
            ('region1', 'container', 21, 2, -1),
            ('region1', 'object-0', 31, 3, -1),
            ('region2', 'account', 'four3', 4, 6),
            ('region2', 'account', 52, 5, 6),
            ('region2', 'object-0', 'four1', 4, 7),
            ('region2', 'object-0', 53, 5, 8),
            ('region2', 'container', 91, 9, None),
            ('region2', 'container', 101, None, 10),
            ('region2', 'bad-ring', 52, 5, None),
            ('bad-region', 'account', 52, None, None),
            ('region1', 'container', None, None, -1),
            ('region2', 'container', None, None, None),
            ('region2', 'object-0', None, None, None),
        ]
        ring_model = RingSpecifications(model=safe_load(ringspec_region_zones))
        for scenario in scenarios:
            rg, rng, rck, rv, rz = scenario
            r, z = ring_model.get_region_zone(rg, rng, rck)
            self.assertEquals((rg, rng, rck, r, z), (rg, rng, rck, rv, rz))

    def test_replication_replica_count(self):
        ring_model = RingSpecifications(model=safe_load(ringspec_simple))
        self.assertEquals(
            ring_model.get_ringspec('region1', 'account').replica_count, 1.0)
        self.assertEquals(
            ring_model.get_ringspec('region1', 'container').replica_count, 2.0)
        self.assertEquals(
            ring_model.get_ringspec('region1', 'object-0').replica_count, 3.0)
        self.assertEquals(
            ring_model.get_ringspec('region1', 'object-1').replica_count, 14.0)


class TestDeviceInfo(unittest.TestCase):

    def test_simple_device_info(self):
        device_info = DeviceInfo(model=safe_load(device_info_simple))
        self.assertEquals(device_info.region_name, 'region2')
        self.assertEquals(device_info.region_id, 2)
        self.assertEquals(device_info.replication_ip, None)
        self.assertEquals(device_info.presence, 'present')
        self.assertEquals(device_info.meta, 'host.example.com:disk99:/dev/sdh')
        with self.assertRaises(AttributeError):
            _ = device_info.junk
        with self.assertRaises(AttributeError):
            device_info.junk = 'junk'


class TestDriveConfiguration(unittest.TestCase):

    def TestDriveConfigationSimple(self):
        dc = DriveConfiguration()
        dc.load_model(safe_load(drive_configuration_simple))
        self.assertEquals(dc.get('hostname'), 'four')
        result = []
        for item in dc.iter_drive_info():
            result.append(item)
        self.assertEqual(result, drive_configuration_simple_iter)


class TestIpAddress(unittest.TestCase):

    def setUp(self):
        hosts = padawan_net_hosts = [
            '192.168.245.2           padawan-ccp-c1-m3-mgmt',
            '192.168.222.2           padawan-ccp-c1-m3-obj',
            '192.168.245.3           padawan-ccp-c1-m2-mgmt',
            '192.168.222.3           padawan-ccp-c1-m2-obj',
            '192.168.245.4           padawan-ccp-c1-m1-mgmt',
            '192.168.222.4           padawan-ccp-c1-m1-obj',
            '192.168.111.4           padawan-vip']
        self.input_model = InputModel(hosts_fd=hosts)

    def TestMapping(self):
        self.assertEqual(self.input_model.ip_address('192.168.245.2', 'test'),
                         'padawan-ccp-c1-m3-mgmt')

        self.assertEqual(self.input_model.ip_address('padawan-ccp-c1-m3-mgmt',
                                                     'test'),
                         '192.168.245.2')

    def TestNotFound(self):
        self.assertRaises(SwiftModelException, self.input_model.ip_address,
                          'junk', 'test')

    def TestAlias(self):
        expect = sorted(['192.168.245.2', '192.168.222.2'])
        alisas = self.input_model.aliases('192.168.245.2')
        self.assertEqual(sorted(alisas), expect)
        alisas = self.input_model.aliases('192.168.222.2')
        self.assertEqual(sorted(alisas), expect)
        expect = ['192.168.111.4']
        alisas = self.input_model.aliases('192.168.111.4')
        self.assertEqual(sorted(alisas), expect)

    def TestBadAlias(self):
        alisas = self.input_model.aliases('junk')
        self.assertEqual(alisas, [])

    def TestEdgeCase(self):
        # As specified, the aliases only work for ip addresses -- returning
        # a list of ip addresses. However, given a valid name, it returns that
        # name -- not (by design) a list of names. That might be possible,
        # but not needed for now.
        alisas = self.input_model.aliases('padawan-ccp-c1-m3-mgmt')
        self.assertEqual(alisas, ['padawan-ccp-c1-m3-mgmt'])
