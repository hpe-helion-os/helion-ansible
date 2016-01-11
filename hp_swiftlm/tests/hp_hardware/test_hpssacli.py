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
import mock
import pprint

from swiftlm.hp_hardware import hpssacli
from swiftlm.utils.metricdata import MetricData
from swiftlm.utils.utility import CommandResult
from swiftlm.utils.values import Severity

from tests.data.hpssacli_data import *


class TestHpssacli(unittest.TestCase):

    def setUp(self):
        mock_metricdata_timestamp = mock.Mock()
        mock_metricdata_timestamp.return_value = 123456
        p = mock.patch('swiftlm.utils.metricdata.timestamp',
                       mock_metricdata_timestamp)
        p.start()
        self.addCleanup(p.stop)

        p = mock.patch('swiftlm.hp_hardware.hpssacli.BASE_RESULT.dimensions',
                       {})
        p.start()
        self.addCleanup(p.stop)

    def check_metrics(self, expected, metrics):
        # Checks that the expected metric exists in the metrics
        # list.
        # returns the metrics list with expected removed if it does
        # otherwise fails the test.
        for m in metrics:
            if m == expected:
                metrics.remove(m)
                return metrics

        pprint.pprint('Expected')
        pprint.pprint(expected.metric())

        pprint.pprint('Actual')
        for m in metrics:
            pprint.pprint(m.metric())
        self.fail('did not find %s in metrics %s' %
                  (repr(expected), str(metrics)))

    def test_get_info_hpssacli_error(self):
        # All of the get_*_info functions use the same hpssacli error handling
        # code. Do a generic test here.
        def do_it(func, metric_name, slot_used):
            # Test first failure condition.
            # could be anything from hpssacli is missing to insufficent
            # privileges
            mock_command = mock.Mock()
            mock_command.return_value = CommandResult(1, 'error')
            with mock.patch('swiftlm.hp_hardware.hpssacli.run_cmd',
                            mock_command):
                if slot_used == "N/A":
                    actual = func()
                else:
                    actual = func(slot_used)

            self.assertIsInstance(actual, list)
            self.assertTrue(len(actual), 1)
            r = actual[0]

            if slot_used == "N/A":

                expected = MetricData.single(
                    'check.failure', Severity.fail,
                    '{check} failed with: {error}',
                    {'check': hpssacli.__name__ + '.' + metric_name,
                        'error': 'error', 'component': 'swiftlm-scan'})
            else:

                expected = MetricData.single(
                    'check.failure', Severity.fail,
                    '{check} slot: {slot} failed with: {error}',
                    {'check': hpssacli.__name__ + '.' + metric_name,
                        'error': 'error', 'slot': slot_used,
                        'component': 'swiftlm-scan'})

            self.assertEqual(r, expected)

            # Test hpssacli providing no output.
            mock_command = mock.Mock()
            mock_command.return_value = CommandResult(0, '')
            with mock.patch('swiftlm.hp_hardware.hpssacli.run_cmd',
                            mock_command):
                if slot_used == "N/A":
                    actual = func()
                else:
                    actual = func(slot_used)

            self.assertIsInstance(actual, list)
            self.assertTrue(len(actual), 1)
            r = actual[0]

            if slot_used == "N/A":

                expected = MetricData.single(
                    'check.failure', Severity.fail,
                    '{check} failed with: {error}',
                    {'check': hpssacli.__name__ + '.' + metric_name,
                        'error': 'No usable output from hpssacli',
                        'component': 'swiftlm-scan'})
            else:

                expected = MetricData.single(
                    'check.failure', Severity.fail,
                    '{check} slot: {slot} failed with: {error}',
                    {'check': hpssacli.__name__ + '.' + metric_name,
                        'error': 'No usable output from hpssacli',
                        'slot': slot_used,
                        'component': 'swiftlm-scan'})

            self.assertEqual(r, expected)

        t_slot = "1"

        for test in (
                (hpssacli.get_physical_drive_info, 'physical_drive', t_slot),
                (hpssacli.get_logical_drive_info, 'logical_drive', t_slot),
                (hpssacli.get_smart_array_info, 'smart_array', "N/A")):
            do_it(*test)

    def test_get_physical_drive_info(self):
        # List of tuples.
        # t[0] = Data set that hpssacli should return
        # t[1] = Tuple(Severity, Message, Status)
        tests = [
            (PHYSICAL_DRIVE_DATA, (Severity.ok, 'OK', 'OK')),
            (PHYSICAL_DRIVE_STATUS_FAIL, (
                Severity.fail,
                hpssacli.BASE_RESULT.messages['physical_drive'],
                'FAIL'))
        ]

        test_slot = "1"

        for test_data, expected_metrics in tests:
            mock_command = mock.Mock()
            mock_command.return_value = CommandResult(0, test_data)
            with mock.patch('swiftlm.hp_hardware.hpssacli.run_cmd',
                            mock_command):
                actual = hpssacli.get_physical_drive_info(test_slot)

            self.assertIsInstance(actual, list)
            self.assertTrue(len(actual), 1)
            r = actual[0]

            self.assertIsInstance(r, MetricData)

            expected = MetricData.single(
                hpssacli.__name__ + '.physical_drive',
                expected_metrics[0],  # Severity
                expected_metrics[1],  # Message
                {'status': expected_metrics[2],  # Status
                 'serial': 'YFJMHTZD', 'box': '1', 'bay': '1',
                 'component': 'physical_drive', 'controller_slot': '1'})

            self.assertEqual(r, expected)

    def test_get_logical_drive_info(self):
        # Test that normal output and bugged output give exactly
        # the same results
        mock_command = mock.Mock()
        test_slot = "1"
        mock_command.return_value = CommandResult(0, LOGICAL_DRIVE_DATA)
        with mock.patch('swiftlm.hp_hardware.hpssacli.run_cmd',
                        mock_command):
            data_1 = hpssacli.get_logical_drive_info(test_slot)

        self.assertIsInstance(data_1, list)
        self.assertTrue(len(data_1), 3)

        mock_command = mock.Mock()
        mock_command.return_value = CommandResult(0, LOGICAL_DRIVE_DATA_BUGGED)
        with mock.patch('swiftlm.hp_hardware.hpssacli.run_cmd',
                        mock_command):
            data_2 = hpssacli.get_logical_drive_info(test_slot)

        self.assertIsInstance(data_2, list)
        self.assertTrue(len(data_2), 3)

        # Check the data is the same for both
        for d in data_1:
            data_2 = self.check_metrics(d, data_2)

        # Check data is as expected.
        expected_lun = MetricData.single(
            hpssacli.__name__ + '.logical_drive',
            Severity.ok, 'OK',
            {'component': 'logical_drive', 'sub_component': 'lun_status',
             'status': "OK", 'logical_drive': 'L', 'caching': 'Enabled'})
        data_1 = self.check_metrics(expected_lun, data_1)

        expected_cache = MetricData.single(
            hpssacli.__name__ + '.logical_drive',
            Severity.ok, 'OK',
            {'component': 'logical_drive', 'sub_component': 'cache_status',
             'status': "OK", 'logical_drive': 'L', 'caching': 'Enabled'})
        data_1 = self.check_metrics(expected_cache, data_1)

        self.assertFalse(data_1, 'Got more metrics than expected with'
                         'LOGICAL_DRIVE_DATA')
        self.assertFalse(data_2, 'Got more metrics than expected with'
                         'LOGICAL_DRIVE_DATA_BUGGED')

    def test_get_logical_drive_info_failures(self):
        tests = [
            (LOGICAL_DRIVE_LUN_FAIL, 'lun_status'),
            (LOGICAL_DRIVE_CACHE_FAIL, 'cache_status')
        ]

        test_slot = "1"
        for test_data, failed_component in tests:
            mock_command = mock.Mock()
            mock_command.return_value = CommandResult(0, test_data)
            with mock.patch('swiftlm.hp_hardware.hpssacli.run_cmd',
                            mock_command):
                actual = hpssacli.get_logical_drive_info(test_slot)

            expected_lun = MetricData.single(
                hpssacli.__name__ + '.logical_drive',
                Severity.ok, 'OK',
                {'component': 'logical_drive',
                 'logical_drive': 'L',
                 'sub_component': 'lun_status',
                 'caching': 'Enabled',
                 'status': "OK"})

            expected_cache = MetricData.single(
                hpssacli.__name__ + '.logical_drive',
                Severity.ok, 'OK',
                {'component': 'logical_drive',
                 'logical_drive': 'L',
                 'sub_component': 'cache_status',
                 'caching': 'Enabled',
                 'status': "OK"})

            if expected_lun['sub_component'] == failed_component:
                expected_lun.value = Severity.fail
                expected_lun['status'] = 'Fail'
                expected_lun._message = (hpssacli.BASE_RESULT.messages
                                         ['l_drive'])

            if expected_cache['sub_component'] == failed_component:
                expected_lun['caching'] = 'Disabled'

            actual = self.check_metrics(expected_lun, actual)

            if expected_cache['sub_component'] == failed_component:
                expected_cache.value = Severity.fail
                expected_cache['caching'] = 'Disabled'
                expected_cache._message = (hpssacli.BASE_RESULT.messages
                                           ['l_cache'])

            if expected_lun['sub_component'] == failed_component:
                expected_cache['status'] = 'Fail'

            actual = self.check_metrics(expected_cache, actual)

            self.assertFalse(actual, 'Got more metrics than expected')

    def test_get_controller_info(self):
        expected_base = MetricData(
            name=hpssacli.__name__ + '.smart_array',
            messages=hpssacli.BASE_RESULT.messages,
            dimensions={
                'serial': 'PACCR0M9VZ41S4Q',
                'model': 'Smart Array P410',
                'slot': '1',
                'component': 'controller',
            })

        # List of tuples.
        # t[0] = Data set that hpssacli should return
        # t[1] = The failed component in the test data
        tests = [
            (SMART_ARRAY_DATA, []),
            (SMART_ARRAY_CACHE_FAIL, ['cache']),
            (SMART_ARRAY_BATTERY_FAIL, ['battery/capacitor']),
            (SMART_ARRAY_CONTROLLER_FAIL, ['controller']),
            (SMART_ARRAY_BATTERY_COUNT_FAIL, ['battery/capacitor count']),
        ]

        for test_data, failures in tests:
            mock_command = mock.Mock()
            mock_command.return_value = CommandResult(0, test_data)
            with mock.patch('swiftlm.hp_hardware.hpssacli.run_cmd',
                            mock_command):
                actual, actual_slots = hpssacli.get_smart_array_info()

            self.assertIsInstance(actual, list)
            self.assertEqual(len(actual), 5)

            expected_firmware = expected_base.child('firmware')
            expected_firmware.value = 6.60
            actual = self.check_metrics(expected_firmware, actual)

            bcc = 'battery/capacitor count'
            if bcc in failures:
                expected_battery_count = expected_base.child(dimensions={
                    'sub_component': bcc, 'count': '0'})
                expected_battery_count.value = Severity.fail
                expected_battery_count.message = 'no_battery'
            else:
                expected_battery_count = expected_base.child(dimensions={
                    'sub_component': bcc, 'count': '1'})
                expected_battery_count.value = Severity.ok

            actual = self.check_metrics(expected_battery_count, actual)

            for submetric in ('battery/capacitor', 'controller', 'cache'):
                if submetric in failures:
                    expected_status = expected_base.child(dimensions={
                        'sub_component': submetric, 'status': 'FAIL'})
                    expected_status.value = Severity.fail
                    expected_status.message = 'controller_status'
                else:
                    expected_status = expected_base.child(dimensions={
                        'sub_component': submetric, 'status': 'OK'})
                    expected_status.value = Severity.ok

                actual = self.check_metrics(expected_status, actual)

            self.assertFalse(actual, 'Got more metrics than expected')

    def test_get_controller_slot_count(self):

        # Expect to get 2 slots returned, slot 1 & 3
        expected_slots = ["1", "3"]

        test_data = SMART_ARRAY_DATA_2_CONT

        mock_command = mock.Mock()
        mock_command.return_value = CommandResult(0, test_data)
        with mock.patch('swiftlm.hp_hardware.hpssacli.run_cmd', mock_command):
            actual, actual_slots = hpssacli.get_smart_array_info()

        self.assertEqual(len(actual_slots), 2)
        self.assertEqual(expected_slots, actual_slots)
