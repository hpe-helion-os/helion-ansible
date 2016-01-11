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


import json
import os
import tempfile
import unittest

import mock
import six
from shutil import rmtree

from swiftlm.utils import utility
from swiftlm.utils.utility import RingDeviceEntry
from swiftlm.utils.values import Severity, ServerType


if six.PY2:
    BUILTIN_OPEN = '__builtin__.open'
    COMMANDS_MODULE = 'commands'
else:
    BUILTIN_OPEN = 'builtins.open'
    COMMANDS_MODULE = 'subprocess'


class TestUtility(unittest.TestCase):

    @mock.patch('os.path.isfile')
    def test_server_type(self, mock_isfile):
        mock_isfile.return_value = True
        expected = {
            'object': True,
            'proxy': True,
            'container': True,
            'account': True
        }

        # test dict of all ServerTypes.
        actual = utility.server_type()
        self.assertDictEqual(expected, actual)

        # test a single ServerType
        is_o = utility.server_type(ServerType.object)
        self.assertTrue(is_o)

        # test multiple ServerTypes
        is_o, is_a = utility.server_type(ServerType.object, ServerType.account)
        self.assertTrue(is_o)
        self.assertTrue(is_a)

        with self.assertRaisesRegexp(ValueError, 'ServerType'):
            utility.server_type('test')

    @mock.patch(COMMANDS_MODULE + '.getoutput')
    def test_ip_to_interface(self, mock_command):

        # testing:
        # duplicate interfaces/variable lines and whitespace/no inet addr
        mock_data = 'Kernel Interface table\n'\
            'br-eth1 Link encap:Ethernet HWaddr 46:5f:ab:d2:ed:47\n'\
            '  inet addr:192.168.245.4 Bcast:192.168.245.15 '\
            'Mask:255.255.255.240\n'\
            '  inet6 addr: fe80::445f:abff:fed2:ed47/64 Scope:Link\n'\
            '  UP BROADCAST RUNNING MULTICAST MTU:1500 Metric:1\n'\
            '  RX packets:56610907 errors:0 dropped:0 overruns:0 frame:0\n'\
            '  TX packets:54015961 errors:0 dropped:0 overruns:0 carrier:0\n'\
            '  collisions:0 txqueuelen:0\n'\
            '  RX bytes:29151178698 (27.1 GiB) TX '\
            'bytes:29647366952 (27.6 GiB)\n'\
            '\n'\
            'eth0 Link encap:Ethernet HWaddr 52:54:00:ba:5a:30\n'\
            '  inet addr:192.168.121.67 Bcast:192.168.121.255 '\
            'Mask:255.255.255.0\n'\
            '  inet6 addr: fe80::5054:ff:feba:5a30/64 Scope:Link\n'\
            '  UP BROADCAST RUNNING MULTICAST MTU:1500 Metric:1\n'\
            '  RX packets:338611 errors:0 dropped:0 overruns:0 frame:0\n'\
            '  TX packets:79717 errors:0 dropped:0 overruns:0 carrier:0\n'\
            '  collisions:0 txqueuelen:1000\n'\
            '  RX bytes:19263289 (18.3 MiB) TX bytes:5722887 (5.4 MiB)\n'\
            '\n'\
            'eth0 Link encap:Ethernet HWaddr 52:54:00:ba:5a:30\n'\
            '       inet addr:192.168.120.66 Bcast:192.168.121.255 '\
            'Mask:255.255.255.0\n'\
            '  inet6 addr: fe80::5054:ff:feba:5a30/64 Scope:Link\n'\
            '  UP BROADCAST RUNNING MULTICAST MTU:1500 Metric:1\n'\
            '  RX packets:338611 errors:0 dropped:0 overruns:0 frame:0\n'\
            '  TX packets:79717 errors:0 dropped:0 overruns:0 carrier:0\n'\
            '  collisions:0 txqueuelen:1000\n'\
            '  RX bytes:19263289 (18.3 MiB) TX bytes:5722887 (5.4 MiB)\n'\
            '\n'\
            'eth2 Link encap:Ethernet HWaddr 52:54:00:ba:5a:30\n'\
            '  inet6 addr: fe80::5054:ff:feba:5a30/64 Scope:Link\n'\
            '  UP BROADCAST RUNNING MULTICAST MTU:1500 Metric:1\n'\
            '\n'\
            'eth3 Link encap:Ethernet HWaddr 52:54:00:ba:5a:30\n'\
            '\n'\
            'eth4 Link encap:Ethernet HWaddr 52:54:00:ba:5a:30\n'\
            '  inet6 addr: fe80::5054:ff:feba:5a30/64 Scope:Link\n'\
            '  UP BROADCAST RUNNING MULTICAST MTU:1500 Metric:1\n'\

        mock_command.return_value = mock_data

        d = utility.ip_to_interface()

        self.assertEqual(d, {'192.168.245.4': 'br-eth1',
                             '192.168.121.67': 'eth0',
                             '192.168.120.66': 'eth0'})


class TestDumpUptimeStatsFile(unittest.TestCase):

    def test_file_truncated(self):
        testdir = tempfile.mkdtemp()
        fake_logger = mock.MagicMock()
        data = json.dumps([{'metric': 'foo',
                            'dimensions': {
                                'hostname': 'example.com',
                                'fifth': 'dimension'
                            }}])
        path = os.path.join(testdir, 'junk')
        utility.dump_swiftlm_uptime_data(data, path, logger=fake_logger)
        with open(path) as f:
            self.assertEqual(data, json.load(f))
        # now write a shorter data string to the same file
        data = json.dumps([{'metric': 'foo',
                            'dimensions': {
                                'hostname': 'timy.com',
                            }}])
        utility.dump_swiftlm_uptime_data(data, path, logger=fake_logger)
        with open(path) as f:
            self.assertEqual(data, json.load(f))


class TestGetRingHosts(unittest.TestCase):
    def setUp(self):
        self.testdir = tempfile.mkdtemp()

    def tearDown(self):
        rmtree(self.testdir, ignore_errors=True)

    def test_finds_object_ring_files(self):
        devices = [dict(ip='1.2.3.4', port='6001', device='/sdb',
                        replication_port='6021', replication_ip='1.2.3.4'),
                   dict(ip='1.2.3.5', port='6001', device='/sdb',
                        replication_port='6021', replication_ip='1.2.3.5')]

        for f in ('object.ring.gz', 'object-1.ring.gz',
                  'account.ring.gz', 'container.ring.gz', 'junk'):
            open(os.path.join(self.testdir, f), 'wb')
        with mock.patch('swiftlm.utils.utility.RingData.load') as mock_load:
            with mock.patch('swiftlm.utils.utility.SWIFT_PATH', self.testdir):
                mock_load.return_value = mock.MagicMock(devs=devices)
                results = utility.get_ring_hosts(ServerType.object)
        self.assertEqual(4, len(results))
        # 2 devs per ring file
        expected = [RingDeviceEntry(dev['ip'], dev['port'], dev['device'])
                    for dev in devices] * 2
        self.assertEqual(expected, results, results)

    def test_finds_all_ring_files(self):
        devices = [dict(ip='1.2.3.4', port='6001', device='/sdb',
                        replication_port='6021', replication_ip='1.2.3.4'),
                   dict(ip='1.2.3.5', port='6001', device='/sdb',
                        replication_port='6021', replication_ip='1.2.3.5')]

        for f in ('object.ring.gz', 'object-1.ring.gz',
                  'account.ring.gz', 'container.ring.gz', 'junk'):
            open(os.path.join(self.testdir, f), 'wb')
        with mock.patch('swiftlm.utils.utility.RingData.load') as mock_load:
            with mock.patch('swiftlm.utils.utility.SWIFT_PATH', self.testdir):
                mock_load.return_value = mock.MagicMock(devs=devices)
                results = utility.get_ring_hosts()
        self.assertEqual(8, len(results))
        # 2 devs per ring file
        expected = [RingDeviceEntry(dev['ip'], dev['port'], dev['device'])
                    for dev in devices] * 4
        self.assertEqual(expected, results, results)

    def test_no_ring_files(self):
        for f in ('junk'):
            open(os.path.join(self.testdir, f), 'wb')
        with mock.patch('swiftlm.utils.utility.SWIFT_PATH', self.testdir):
            results = utility.get_ring_hosts()
        self.assertEqual([], results)

    def test_no_swift_dir(self):
        non_existent_dir = os.path.join(self.testdir, 'not_here')
        with mock.patch('swiftlm.utils.utility.SWIFT_PATH', non_existent_dir):
            results = utility.get_ring_hosts()
        self.assertEqual([], results)
