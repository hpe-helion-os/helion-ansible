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
from mock import Mock, patch

from swiftlm.systems import ntp
from swiftlm.utils.values import Severity
from swiftlm.utils.utility import CommandResult
from swiftlm.utils.metricdata import MetricData, CheckFailure


class TestNtp(unittest.TestCase):
    def p(self, name, mock):
        p = patch(name, mock)
        p.start()
        self.addCleanup(p.stop)

    def setUp(self):
        self.p('swiftlm.systems.ntp.BASE_RESULT.dimensions', {})
        self.p('swiftlm.utils.metricdata.get_base_dimensions', lambda *a: {})
        self.p('swiftlm.utils.metricdata.timestamp', lambda *a: 123456)

    def test_status_ok(self):
        mock_command = Mock()
        mock_command.return_value = CommandResult(0, '')

        with patch('swiftlm.systems.ntp.run_cmd', mock_command):
            with patch('swiftlm.systems.ntp.check_details', lambda: []):
                actual = ntp.main()

        self.assertIsInstance(actual, list)
        self.assertEqual(len(actual), 1)
        r = actual[0]
        self.assertIsInstance(r, MetricData)

        expected = MetricData.single(ntp.__name__, Severity.ok,
                                     ntp.BASE_RESULT.messages['ok'])
        self.assertEqual(r, expected)

    def test_status_fail(self):
        mock_command = Mock()
        mock_command.return_value = CommandResult(1, 'error')

        with patch('swiftlm.systems.ntp.run_cmd', mock_command):
            with patch('swiftlm.systems.ntp.check_details', lambda: []):
                actual = ntp.main()

        self.assertIsInstance(actual, list)
        self.assertEqual(len(actual), 1)
        r = actual[0]
        self.assertIsInstance(r, MetricData)

        expected = MetricData.single(ntp.__name__, Severity.fail,
                                     ntp.BASE_RESULT.messages['fail'],
                                     {'error': 'error'})
        self.assertEqual(r, expected)

    def test_details_ok(self):
        mock_command = Mock()
        mock_command.return_value = CommandResult(0, 'stratum=1,offset=2,')

        with patch('swiftlm.systems.ntp.run_cmd', mock_command):
            with patch('swiftlm.systems.ntp.check_status', lambda: []):
                actual = ntp.main()

        self.assertIsInstance(actual, list)
        self.assertEqual(len(actual), 2)
        actual = [a.metric() for a in actual]

        expected = [
            MetricData.single(ntp.__name__+'.stratum', '1', ''),
            MetricData.single(ntp.__name__+'.offset', '2', '')
        ]

        for e in expected:
            self.assertIn(e.metric(), actual)

    def test_details_fail(self):
        mock_command = Mock()
        mock_command.return_value = CommandResult(0, 'stratum=1,')

        with patch('swiftlm.systems.ntp.run_cmd', mock_command):
            with patch('swiftlm.systems.ntp.check_status', lambda: []):
                actual = ntp.main()

        self.assertIsInstance(actual, list)
        self.assertEqual(len(actual), 2)
        actual = [a.metric() for a in actual]

        failed = CheckFailure.child()
        failed.value = Severity.fail
        failed['check'] = ntp.__name__ + '.offset'
        failed['error'] = 'Output does not contain "offset"'

        expected = [
            failed,
            MetricData.single(ntp.__name__+'.stratum', '1', ''),
        ]

        for e in expected:
            self.assertIn(e.metric(), actual)

    def test_main(self):
        with patch('swiftlm.systems.ntp.check_status', lambda: ['a']):
            with patch('swiftlm.systems.ntp.check_details', lambda: ['b']):
                actual = ntp.main()

        self.assertListEqual(['a', 'b'], actual)
