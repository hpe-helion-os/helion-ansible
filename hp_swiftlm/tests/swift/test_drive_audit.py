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


import socket
import subprocess
import unittest

from mock import patch, MagicMock
import time

from swiftlm.swift import drive_audit
from swiftlm.utils.metricdata import MetricData
from swiftlm.utils.values import Severity
from tests.data.drive_audit_data import output1, output2, output3


class TestDriveAudit(unittest.TestCase):

    def test_get_devices(self):
        devices = drive_audit.get_devices(output1)
        self.assertEquals(devices, [{'kernel_device': 'sdc',
                                     'mount_point': '/srv/node/sdc1'},
                                    {'kernel_device': 'sdd',
                                     'mount_point': '/srv/node/sdd1'}])

    def test_get_devices_no_devs(self):
        devices = drive_audit.get_devices(output2)
        self.assertEquals(devices, [])

    def test_get_devices_err_devs(self):
        devices = drive_audit.get_devices(output3)
        self.assertEquals(devices, [{'kernel_device': 'sdb',
                                     'mount_point': '/srv/node/sdb1'},
                                    {'kernel_device': 'sdc',
                                     'mount_point': '/srv/node/sdc1'},
                                    {'kernel_device': 'sdd',
                                     'mount_point': '/srv/node/sdd1'}])

    def test_get_error_devices_when_errors(self):
        devices = drive_audit.get_error_devices(output3)
        self.assertEquals(devices, {'sdb': 516,
                                    'sdb1': 20,
                                    'sdd1': 2,
                                    'sdd': 3})

    def test_get_error_devices_when_no_errors(self):
        devices = drive_audit.get_error_devices(output1)
        self.assertEquals(devices, {})


class TestMain(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None
        self.fake_time = int(time.time())
        self.expected_dimensions_base = dict(hostname=socket.gethostname(),
                                             service='object-storage')
        self.expected_metric_base = dict(
            metric='swiftlm.swift.drive_audit',
            timestamp=self.fake_time)

    @patch('subprocess.Popen')
    def test_no_errors_found(self, popen):
        # Expect no MetricData returned when no errors found
        popen.return_value = MagicMock(spec=subprocess.Popen,
                                       communicate=lambda: (None, output1))
        with patch('swiftlm.utils.metricdata.timestamp',
                   lambda *args: self.fake_time):
            results = drive_audit.main()

        scenarios = (({'kernel_device': 'sdc',
                      'mount_point': '/srv/node/sdc1'}, Severity.ok,
                      'No errors found on device mounted at: /srv/node/sdc1'),
                     ({'kernel_device': 'sdd',
                       'mount_point': '/srv/node/sdd1'}, Severity.ok,
                      'No errors found on device mounted at: /srv/node/sdd1'))
        expected = []
        for scenario in scenarios:
            expected_dimensions = dict(self.expected_dimensions_base)
            expected_dimensions.update(scenario[0])
            expected_value_meta = dict(msg=scenario[2])
            expected_metric = dict(self.expected_metric_base)
            expected_metric.update(dict(dimensions=expected_dimensions,
                                        value=scenario[1],
                                        value_meta=expected_value_meta))
            expected.append(expected_metric)
        self.assertEqual(len(expected), len(results), results)
        for result in results:
            self.assertTrue(result.metric() in expected, result.metric())
            # consume expected result once it has been matched
            expected.remove(result.metric())
        self.assertFalse(expected)

    @patch('subprocess.Popen')
    def test_errors_found(self, popen):
        popen.return_value = MagicMock(spec=subprocess.Popen,
                                       communicate=lambda: (None, output3))
        with patch('swiftlm.utils.metricdata.timestamp',
                   lambda *args: self.fake_time):
            results = drive_audit.main()

        scenarios = (({'kernel_device': 'sdc',
                       'mount_point': '/srv/node/sdc1'}, Severity.ok,
                      'No errors found on device mounted at: /srv/node/sdc1'),
                     ({'kernel_device': 'sdb',
                       'mount_point': '/srv/node/sdb1'}, Severity.fail,
                      'Errors found on device mounted at: /srv/node/sdb1'),
                     ({'kernel_device': 'sdd',
                       'mount_point': '/srv/node/sdd1'}, Severity.fail,
                      'Errors found on device mounted at: /srv/node/sdd1'))
        expected = []
        for scenario in scenarios:
            expected_dimensions = dict(self.expected_dimensions_base)
            expected_dimensions.update(scenario[0])
            expected_value_meta = dict(msg=scenario[2])
            expected_metric = dict(self.expected_metric_base)
            expected_metric.update(dict(dimensions=expected_dimensions,
                                        value=scenario[1],
                                        value_meta=expected_value_meta))
            expected.append(expected_metric)
        self.assertEqual(len(expected), len(results), results)
        for result in results:
            self.assertTrue(result.metric() in expected, result.metric())
            # consume expected result once it has been matched
            expected.remove(result.metric())
        self.assertFalse(expected)

    @patch('subprocess.Popen')
    def test_errors_found_but_not_devices(self, popen):
        popen.return_value = MagicMock(spec=subprocess.Popen,
                                       communicate=lambda: (None, output2))
        with patch('swiftlm.utils.metricdata.timestamp',
                   lambda *args: self.fake_time):
            result = drive_audit.main()
        self.assertTrue(isinstance(result, MetricData))
        expected_dimensions = dict(self.expected_dimensions_base)
        expected_value_meta = dict(msg='No devices found')
        expected_metric = dict(self.expected_metric_base)
        expected_metric.update(dict(dimensions=expected_dimensions,
                                    value=Severity.warn,
                                    value_meta=expected_value_meta))
        self.assertEquals(expected_metric, result.metric())
