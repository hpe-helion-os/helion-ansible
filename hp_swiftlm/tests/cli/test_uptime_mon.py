#!/usr/bin/python

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
import StringIO
import logging
import ConfigParser
from swiftlm.cli import uptime_mon
from swiftlm.cli.uptime_mon import UPtimeMonException
from swiftlm.cli.uptime_mon import TrackConnection
from swiftlm.cli.uptime_mon import component_states, severities


class TestArgumentParser(unittest.TestCase):
    def test_config_file_path(self):
        args = uptime_mon.parse_args(['--config', '/path/to/file'])
        self.assertEqual(vars(args)['configFile'], '/path/to/file')

    def test_default_config_file_path(self):
        args = uptime_mon.parse_args([])
        self.assertEqual(vars(args)['configFile'],
                         '/etc/swift/swiftlm-uptime-monitor.conf')


class TestArgumentValidator(unittest.TestCase):
    def setUp(self):
        self.data = """[logging]
log_level: info
log_facility:  LOG_LOCAL0
log_format: r'%(name)s - %(levelname)s : %(message)s'

[latency_monitor]
interval: 60
checks_per_interval: 40
swiftlm_uptime_monitor_cache_dir: /var/cache/swift/swiftlm_uptime_mon
cache_file_path: /var/cache/swift/swiftlm_uptime_monitor/uptime.stats
keystone_auth_url: http://HOSTNAME:35357/v2.0
object_store_url: http://HOSTNAME:8080/v1/
user_name: swift-monitor
password: changeme
project_id:
project_name: swift-monitor
auth_version: 2
"""

        buf = StringIO.StringIO(self.data)
        self.config = ConfigParser.ConfigParser()
        self.config.readfp(buf)
        self.config.set('logging', 'name', 'uptime_mon')
        self.config.set('logging', 'levelname', 'info')
        self.config.set('logging', 'message', 'Foo message')

    def tearDown(self):
        self.data = None
        self.config = None

    def test_missing_logging_section(self):
        self.config.remove_section('logging')

        self.assertRaises(UPtimeMonException,
                          lambda: uptime_mon.validate_args(self.config))

    def test_missing_latency_monitor_section(self):
        self.config.remove_section('latency_monitor')
        self.assertRaises(UPtimeMonException,
                          lambda: uptime_mon.validate_args(self.config))

    def test_missing_object_store_url_option(self):
        self.config.remove_option('latency_monitor', 'object_store_url')
        self.assertRaises(UPtimeMonException,
                          lambda: uptime_mon.validate_args(self.config))

    def test_missing_cache_file_path_option(self):
        self.config.remove_option('latency_monitor', 'cache_file_path')
        self.assertRaises(UPtimeMonException,
                          lambda: uptime_mon.validate_args(self.config))

    def test_missing_user_name_option(self):
        self.config.remove_option('latency_monitor', 'user_name')
        self.assertRaises(UPtimeMonException,
                          lambda: uptime_mon.validate_args(self.config))

    def test_missing_password_option(self):
        self.config.remove_option('latency_monitor', 'password')
        self.assertRaises(UPtimeMonException,
                          lambda: uptime_mon.validate_args(self.config))

    def test_missing_keystone_auth_url_option(self):
        self.config.remove_option('latency_monitor', 'keystone_auth_url')
        self.assertRaises(UPtimeMonException,
                          lambda: uptime_mon.validate_args(self.config))

    def test_missing_project_details_option(self):
        self.config.remove_option('latency_monitor', 'project_id')
        self.config.remove_option('latency_monitor', 'project_name')
        self.assertRaises(UPtimeMonException,
                          lambda: uptime_mon.validate_args(self.config))


class TestTrackConnection(unittest.TestCase):
    def setUp(self):
        self.connection = TrackConnection('http://H:35357/v2.0',
                                          'swift-monitor',
                                          'changeme',
                                          logging.getLogger(name='test'),
                                          '/path/to/uptime.stats',
                                          object_store_url='http://H:8080/v1/',
                                          auth_version=2,
                                          os_options={})
        self.latency_reset = True
        self.state_reset = True

    def tearDown(self):
        pass

    def test_initialiazation(self):
        # Ensure metric data reset in __init__
        self.assertTrue(not self.connection.metric_data,
                        "Metric data is not empty")
        # Ensure the state dict is reset in __init__
        for state in self.connection.state.values():
            if not state['current_state'] == component_states.unknown \
                    or not state['reason'] == '' or state['metrics']:
                self.state_reset = False

        self.assertTrue(self.state_reset,
                        "State data is not empty")

        # Ensure the latency dict is reset in __init__
        for value in self.connection.latency.values():
            if value > 0:
                self.latency_reset = False
                break

        self.assertTrue(self.latency_reset,
                        "Latency data is not empty")
        # Ensure logger set to valid logger object in __init__
        self.assertIsInstance(self.connection.logger, logging.getLoggerClass(),
                              "Invalid logger object")
        # Ensure cache file path is not empty
        self.assertIsNotNone(self.connection.cache_file_path)

    def test_record_state_info(self):
        # Call record_state method to set INFO state as FAILED
        self.connection.record_state(severities.info,
                                     uptime_mon.COMPONENT_KEYSTONE_GET_TOKEN,
                                     component_states.failed, "Error")

        state_details = self.connection.state[
            uptime_mon.COMPONENT_KEYSTONE_GET_TOKEN + severities.info]

        self.assertEqual(state_details['current_state'],
                         component_states.failed)
        self.assertGreater(state_details['metrics']['timestamp'], 0)
        self.assertEqual(state_details['metrics']['metric'],
                         'swiftlm.info.state')
        self.assertEqual(state_details['metrics']['dimensions']['url'],
                         'http://H:35357/v2.0')
        self.assertEqual(state_details['metrics']['dimensions']['component'],
                         uptime_mon.COMPONENT_KEYSTONE_GET_TOKEN)
        self.assertEqual(state_details['metrics']['value'],
                         uptime_mon.STATE_VALUE_FAILED)
        self.assertEqual(state_details['metrics']['value_meta'],
                         {'msg': 'Error'})

        # Again call record_state method to set INFO state as OK
        self.connection.record_state(severities.info,
                                     uptime_mon.COMPONENT_KEYSTONE_GET_TOKEN,
                                     component_states.ok, "Error")

        self.assertEqual(state_details['current_state'],
                         component_states.ok)
        self.assertGreater(state_details['metrics']['timestamp'], 0)
        self.assertEqual(state_details['metrics']['metric'],
                         'swiftlm.info.state')
        self.assertEqual(state_details['metrics']['dimensions']['url'],
                         'http://H:35357/v2.0')
        self.assertEqual(state_details['metrics']['dimensions']['component'],
                         uptime_mon.COMPONENT_KEYSTONE_GET_TOKEN)
        self.assertEqual(state_details['metrics']['value'],
                         uptime_mon.STATE_VALUE_OK)
        self.assertFalse('value_meta' in state_details['metrics'])

    def test_record_state_hard(self):
        # Call record_state method to set HARD state as FAILED
        self.connection.record_state(severities.hard,
                                     uptime_mon.COMPONENT_REST_API,
                                     component_states.failed, "Error")
        state_details = self.connection.state[
            uptime_mon.COMPONENT_REST_API + severities.hard]

        self.assertEqual(state_details['current_state'],
                         component_states.failed)
        self.assertGreater(state_details['metrics']['timestamp'], 0)
        self.assertEqual(state_details['metrics']['metric'],
                         'swiftlm.hard.state')
        self.assertEqual(state_details['metrics']['dimensions']['url'],
                         'http://H:8080/v1/')
        self.assertEqual(state_details['metrics']['dimensions']['component'],
                         uptime_mon.COMPONENT_REST_API)
        self.assertEqual(state_details['metrics']['value'],
                         uptime_mon.STATE_VALUE_FAILED)
        self.assertEqual(state_details['metrics']['value_meta'],
                         {'msg': 'Error'})

        # Again call record_state method to set HARD state as OK
        self.connection.record_state(severities.hard,
                                     uptime_mon.COMPONENT_REST_API,
                                     component_states.ok, "SUCCESS")

        self.assertEqual(state_details['current_state'],
                         component_states.ok)
        self.assertGreater(state_details['metrics']['timestamp'], 0)
        self.assertEqual(state_details['metrics']['metric'],
                         'swiftlm.hard.state')
        self.assertEqual(state_details['metrics']['dimensions']['url'],
                         'http://H:8080/v1/')
        self.assertEqual(state_details['metrics']['dimensions']['component'],
                         uptime_mon.COMPONENT_REST_API)
        self.assertEqual(state_details['metrics']['value'],
                         uptime_mon.STATE_VALUE_OK)
        self.assertFalse('value_meta' in state_details['metrics'])

    def test_latency_write_log(self):
        # First record two latencies samples for all components
        self.connection.latency_record(uptime_mon.COMPONENT_KEYSTONE_GET_TOKEN,
                                       0.011)
        self.connection.latency_record(uptime_mon.COMPONENT_KEYSTONE_GET_TOKEN,
                                       0.121)

        self.connection.latency_record(uptime_mon.COMPONENT_REST_API, 0.011)
        self.connection.latency_record(uptime_mon.COMPONENT_REST_API, 0.121)
        self.connection.latency_record(uptime_mon.COMPONENT_HEALTHCHECK_API,
                                       0.011)
        self.connection.latency_record(uptime_mon.COMPONENT_HEALTHCHECK_API,
                                       0.121)
        # Then call latency_write_log method
        self.connection.latency_write_log()

        keystone_avg_latency_found = False
        keystone_max_latency_found = False
        rest_api_avg_latency_found = False
        rest_api_max_latency_found = False
        healthcheck_avg_latency_found = False
        healthcheck_max_latency_found = False

        for measurement in self.connection.metric_data:
            if uptime_mon.AVG_LATENCY in measurement.values():
                if uptime_mon.COMPONENT_KEYSTONE_GET_TOKEN in\
                        measurement['dimensions'].values():
                    keystone_avg_latency_found = True
                if uptime_mon.COMPONENT_REST_API in \
                        measurement['dimensions'].values():
                    rest_api_avg_latency_found = True
                if uptime_mon.COMPONENT_HEALTHCHECK_API in \
                        measurement['dimensions'].values():
                    healthcheck_avg_latency_found = True

            if uptime_mon.MAX_LATENCY in measurement.values():
                if uptime_mon.COMPONENT_KEYSTONE_GET_TOKEN in \
                        measurement['dimensions'].values():
                    keystone_max_latency_found = True
                if uptime_mon.COMPONENT_REST_API in \
                        measurement['dimensions'].values():
                    rest_api_max_latency_found = True
                if uptime_mon.COMPONENT_HEALTHCHECK_API in \
                        measurement['dimensions'].values():
                    healthcheck_max_latency_found = True
        # Ensure the latency measurements for all components are stored
        # in metric_data list
        self.assertTrue(keystone_avg_latency_found,
                        "Keystone avg latency metric not found")
        self.assertTrue(keystone_max_latency_found,
                        "Keystone max latency metric not found")
        self.assertTrue(rest_api_avg_latency_found,
                        "REST API avg latency metric not found")
        self.assertTrue(rest_api_max_latency_found,
                        "REST API max latency metric not found")
        self.assertTrue(healthcheck_avg_latency_found,
                        "HEALTH CHECK avg latency metric not found")
        self.assertTrue(healthcheck_max_latency_found,
                        "HEALTH CHECK max latency metric not found")

if __name__ == "__main__":
    all_tests = unittest.TestSuite()
    all_tests.addTest(unittest.makeSuite(TestArgumentParser))
    all_tests.addTest(unittest.makeSuite(TestArgumentValidator))
    all_tests.addTest(unittest.makeSuite(TestTrackConnection))
    unittest.TextTestRunner().run(all_tests)
