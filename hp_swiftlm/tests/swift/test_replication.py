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
import pprint
from mock import patch, Mock, PropertyMock

import six

from swiftlm.swift import replication
from swiftlm.utils.metricdata import CheckFailure
from swiftlm.utils.values import Severity, ServerType

if six.PY2:
    BUILTIN_OPEN = '__builtin__.open'
else:
    BUILTIN_OPEN = 'builtins.open'


class TestHealthCheck(unittest.TestCase):
    def p(self, name, mock):
        p = patch(name, mock)
        p.start()
        self.addCleanup(p.stop)

    def setUp(self):
        self.module = 'swiftlm.swift.replication.'

        self.p('swiftlm.utils.metricdata.get_base_dimensions', lambda: {})
        self.p('swiftlm.utils.metricdata.timestamp', lambda: 123456)
        self.p('swiftlm.swift.replication.timestamp', lambda: 123456)
        self.p('swiftlm.swift.replication.BASE_RESULT.dimensions', {})

    def test_recon_ok(self):
        mock_json = Mock()
        mock_json.return_value = {
            'replication_last': '1222'
        }
        mock_server_type = Mock(spec=ServerType)
        mock_server_type.name = 'servertype'
        mock_server_type.is_instance = True

        with patch(BUILTIN_OPEN):
            with patch('json.load', mock_json):
                actual = replication._recon_check(mock_server_type)

        self.assertIsInstance(actual, list)
        self.assertEqual(len(actual), 1)
        r = actual[0]
        expected = replication.BASE_RESULT.child('servertype.last_replication')
        # mocked timestamp - object_last_replication
        expected.value = 123456 - 1222

        self.assertDictEqual(expected.metric(), r.metric())

    def test_recon_fail(self):
        mock_json = Mock()
        mock_json.side_effect = ValueError('error')
        mock_server_type = Mock(spec=ServerType)
        mock_server_type.name = 'servertype'
        mock_server_type.is_instance = True

        with patch(BUILTIN_OPEN):
            with patch('json.load', mock_json):
                actual = replication._recon_check(mock_server_type)

        self.assertIsInstance(actual, list)
        self.assertEqual(len(actual), 2)
        actual = [m.metric() for m in actual]

        expected1 = replication.BASE_RESULT.child(
            'servertype.last_replication')
        expected1.value = 0

        self.assertIn(expected1.metric(), actual)
        actual.remove(expected1.metric())

        expected2 = CheckFailure.child(dimensions={
            'check': expected1.name,
            'error': 'error',
        })
        expected2.value = Severity.fail

        pprint.pprint(expected2.metric())
        pprint.pprint(actual)
        self.assertIn(expected2.metric(), actual)
        actual.remove(expected2.metric())

    def test_recon_server_type(self):
        mock_server_type = Mock(spec=ServerType)
        mock_server_type.name = 'servertype'
        mock_server_type.is_instance = False

        actual = replication._recon_check(mock_server_type)

        self.assertIsInstance(actual, list)
        self.assertEqual(len(actual), 0)

    def test_main(self):
        mock_recon_check = Mock()
        mock_recon_check.side_effect = [['a'], ['b'], ['c']]

        with patch(self.module + '_recon_check', mock_recon_check):
            actual = replication.main()

        self.assertIsInstance(actual, list)
        self.assertListEqual(['a', 'b', 'c'], actual)

        # Tests account_recon_check in isolation
        mock_recon_check = Mock()
        mock_recon_check.side_effect = [['a']]
        with patch(self.module + '_recon_check', mock_recon_check):
            with patch(self.module + 'object_recon_check') as rc1:
                with patch(self.module + 'container_recon_check') as rc2:
                    actual = replication.main()

        self.assertIsInstance(actual, list)
        self.assertListEqual(['a'], actual)
        self.assertTrue(rc1.called)
        self.assertTrue(rc2.called)

        # Tests container_recon_check in isolation
        mock_recon_check = Mock()
        mock_recon_check.side_effect = [['a']]
        with patch(self.module + '_recon_check', mock_recon_check):
            with patch(self.module + 'object_recon_check') as rc1:
                with patch(self.module + 'account_recon_check') as rc2:
                    actual = replication.main()

        self.assertIsInstance(actual, list)
        self.assertListEqual(['a'], actual)
        self.assertTrue(rc1.called)
        self.assertTrue(rc2.called)

        # Tests object_recon_check in isolation
        mock_recon_check = Mock()
        mock_recon_check.side_effect = [['a']]
        with patch(self.module + '_recon_check', mock_recon_check):
            with patch(self.module + 'container_recon_check') as rc1:
                with patch(self.module + 'account_recon_check') as rc2:
                    actual = replication.main()

        self.assertIsInstance(actual, list)
        self.assertListEqual(['a'], actual)
        self.assertTrue(rc1.called)
        self.assertTrue(rc2.called)
