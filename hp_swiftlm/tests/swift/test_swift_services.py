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


from shutil import rmtree
import socket
import tempfile
import mock
import unittest

import six
import time

from swiftlm.swift import swift_services
from swiftlm.swift.swift_services import SERVICES
from swiftlm.utils.values import Severity
from tests import create_fake_process_entries

if six.PY2:
    BUILTIN_OPEN = '__builtin__.open'
    COMMANDS_MODULE = 'commands'
else:
    BUILTIN_OPEN = 'builtins.open'
    COMMANDS_MODULE = 'subprocess'


class TestSwiftServices(unittest.TestCase):
    server_type = {
        'account': True,
        'object': True,
        'container': True,
        'proxy': True
    }

    @mock.patch('swiftlm.swift.swift_services.server_type')
    def test_services_to_check(self, mock_type):
        mock_type.return_value = self.server_type
        stc = swift_services.services_to_check()

        self.assertEqual(SERVICES, stc)
        self.assertEqual(len(SERVICES), len(stc))

        st = self.server_type.copy()
        st['proxy'] = False
        mock_type.return_value = st
        stc = swift_services.services_to_check()

        self.assertNotEqual(SERVICES, stc)
        self.assertEqual(len(SERVICES) - 1, len(stc))

    @mock.patch('swiftlm.swift.swift_services.server_type')
    @mock.patch('swiftlm.swift.swift_services.is_service_running')
    def test_check_swift_processes(self, mock_running, mock_type):
        mock_type.return_value = self.server_type
        mock_running.return_value = True

        results = swift_services.check_swift_processes()
        self.assertEqual(len(SERVICES), len(results))
        for r in results:
            self.assertEqual(Severity.ok, r.value)

    @mock.patch('swiftlm.swift.swift_services.server_type')
    @mock.patch('swiftlm.swift.swift_services.is_service_running')
    def test_check_dead_swift_processes(self, mock_running, mock_type):
        mock_type.return_value = self.server_type
        mock_running.return_value = False

        results = swift_services.check_swift_processes()
        self.assertEqual(len(SERVICES), len(results))
        for r in results:
            self.assertEqual(Severity.fail, r.value)


class TestMain(unittest.TestCase):

    def setUp(self):
        self.testdir = tempfile.mkdtemp()
        self.fake_time = int(time.time())
        self.expected_dimensions_base = dict(hostname=socket.gethostname(),
                                             service='object-storage')
        self.expected_metric_base = dict(
            metric='swiftlm.swift.swift_services',
            timestamp=self.fake_time)

    def tearDown(self):
        rmtree(self.testdir, ignore_errors=True)

    def test_all_services_running(self):
        server_types = dict(proxy=True,
                            object=True,
                            container=True,
                            account=True)
        expected_services = list(s for s in swift_services.SERVICES
                                 if s.startswith(tuple(server_types.keys())))
        create_fake_process_entries(self.testdir, expected_services)
        with mock.patch('swiftlm.utils.metricdata.timestamp',
                        lambda *args: self.fake_time):
            with mock.patch('swiftlm.swift.swift_services.server_type',
                            lambda *args: server_types):
                with mock.patch('swiftlm.swift.swift_services.PROC_DIR',
                                self.testdir):
                    results = swift_services.main()

        self.assertEqual(len(expected_services), len(results))
        for r in results:
            metric = r.metric()
            actual_service = metric['dimensions']['component']
            self.assertTrue(actual_service in expected_services)

            expected_services.remove(actual_service)
            expected_dimensions = dict(self.expected_dimensions_base)
            expected_dimensions.update(dict(component=actual_service))
            expected_value_meta = dict(msg=actual_service + ' is running')
            expected_metric = dict(self.expected_metric_base)
            expected_metric.update(dict(dimensions=expected_dimensions,
                                        value=Severity.ok,
                                        value_meta=expected_value_meta))
            self.assertEqual(expected_metric, metric)
        # sanity check - all expected services found in actual metrics
        self.assertFalse(expected_services)

    def test_no_services_running(self):
        server_types = dict(proxy=True,
                            object=True,
                            container=True,
                            account=True)
        expected_services = list(s for s in swift_services.SERVICES
                                 if s.startswith(tuple(server_types.keys())))
        with mock.patch('swiftlm.utils.metricdata.timestamp',
                        lambda *args: self.fake_time):
            with mock.patch('swiftlm.swift.swift_services.server_type',
                            lambda *args: server_types):
                with mock.patch('swiftlm.swift.swift_services.PROC_DIR',
                                self.testdir):
                    results = swift_services.main()

        self.assertEqual(len(expected_services), len(results))
        for r in results:
            metric = r.metric()
            actual_service = metric['dimensions']['component']
            self.assertTrue(actual_service in expected_services)

            expected_services.remove(actual_service)
            expected_dimensions = dict(self.expected_dimensions_base)
            expected_dimensions.update(dict(component=actual_service))
            expected_value_meta = dict(msg=actual_service + ' is not running')
            expected_metric = dict(self.expected_metric_base)
            expected_metric.update(dict(dimensions=expected_dimensions,
                                        value=Severity.fail,
                                        value_meta=expected_value_meta))
            self.assertEqual(expected_metric, metric)
        # sanity check - all expected services found in actual metrics
        self.assertFalse(expected_services)

    def test_only_expected_services_checked(self):
        # no object server conf means no check for object server procs
        server_types = dict(proxy=True,
                            container=True,
                            account=True)
        expected_services = list(s for s in swift_services.SERVICES
                                 if s.startswith(tuple(server_types.keys())))
        create_fake_process_entries(self.testdir, expected_services)
        with mock.patch('swiftlm.utils.metricdata.timestamp',
                        lambda *args: self.fake_time):
            with mock.patch('swiftlm.swift.swift_services.server_type',
                            lambda *args: server_types):
                with mock.patch('swiftlm.swift.swift_services.PROC_DIR',
                                self.testdir):
                    results = swift_services.main()

        self.assertEqual(len(expected_services), len(results))
        for r in results:
            metric = r.metric()
            actual_service = metric['dimensions']['component']
            self.assertTrue(actual_service in expected_services)

            expected_services.remove(actual_service)
            expected_dimensions = dict(self.expected_dimensions_base)
            expected_dimensions.update(dict(component=actual_service))
            expected_value_meta = dict(msg=actual_service + ' is running')
            expected_metric = dict(self.expected_metric_base)
            expected_metric.update(dict(dimensions=expected_dimensions,
                                        value=Severity.ok,
                                        value_meta=expected_value_meta))
            self.assertEqual(expected_metric, metric)
        # sanity check - all expected services found in actual metrics
        self.assertFalse(expected_services)

    def test_no_server_conf_found(self):
        server_types = dict(proxy=False,
                            object=False,
                            container=False,
                            account=False)
        with mock.patch('swiftlm.utils.metricdata.timestamp',
                        lambda *args: self.fake_time):
            with mock.patch('swiftlm.swift.swift_services.server_type',
                            lambda *args: server_types):
                with mock.patch('swiftlm.swift.swift_services.PROC_DIR',
                                self.testdir):
                    results = swift_services.main()

        # results should be a single MetricData instance
        metric = results.metric()
        expected_dimensions = dict(self.expected_dimensions_base)
        expected_metric = dict(self.expected_metric_base)
        expected_value_meta = dict(msg='no swift services running')
        expected_metric.update(dict(dimensions=expected_dimensions,
                                    value=Severity.unknown,
                                    value_meta=expected_value_meta))
        self.assertEqual(expected_metric, metric)
