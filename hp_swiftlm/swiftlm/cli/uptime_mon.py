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

import socket
from os import getenv
from os import path
from sys import exit
import sys
import urlparse
import uuid
from swiftclient import Connection
from swiftclient import ClientException
from swiftclient import http_connection
from swiftclient import RequestException
from requests.exceptions import ConnectionError
import time
import argparse
import ConfigParser
from swiftlm.utils.utility import get_logger
from swiftlm.utils.utility import dump_swiftlm_uptime_data, timestamp, Enum

from httplib import HTTPException

SERVICE_NAME = 'object-storage'
AVG_LATENCY = 'swiftlm.avg_latency_sec'
MAX_LATENCY = 'swiftlm.max_latency_sec'
HARD_STATE = 'swiftlm.hard.state'
INFO_STATE = 'swiftlm.info.state'
COMPONENT_KEYSTONE_GET_TOKEN = 'keystone-get-token'
COMPONENT_REST_API = 'rest-api'
COMPONENT_HEALTHCHECK_API = 'healthcheck-api'

common_dimensions = dict()
# 0 = ok, 1 = failed, 3 = unknown
component_states = Enum(['ok', 'failed', 'unknown'])
STATE_VALUE_OK = 0
STATE_VALUE_FAILED = 1
STATE_VALUE_UNKNOWN = 3
severities = Enum(['info', 'hard'])


class UPtimeMonException(Exception):
    pass


def health_check(url, logger):
    scheme = urlparse.urlparse(url).scheme
    netloc = urlparse.urlparse(url).netloc
    url = scheme + '://' + netloc + '/healthcheck'
    parsed, conn = http_connection(url)
    logger.debug('GET %s' % url)
    conn.request('GET', parsed.path, '', {'X-Auth-Token': 'none-needed'})
    resp = conn.getresponse()
    resp.read()
    if resp.status < 200 or resp.status >= 300:
        raise ClientException('GET /healthcheck failed',
                              http_scheme=parsed.scheme,
                              http_host=conn.host, http_port=conn.port,
                              http_path=parsed.path, http_status=resp.status,
                              http_reason=resp.reason)
    resp_headers = {}
    for header, value in resp.getheaders():
        resp_headers[header.lower()] = value
    return resp_headers


def endpoint_trim(url, extension=None):
    s = urlparse.urlparse(url).netloc.split(':')[0]
    if extension is None:
        return s
    else:
        return s + '-' + extension


class TrackConnection(Connection):
    def __init__(self, auth_url, user_name, key, logger, cache_file_path,
                 object_store_url=None, auth_version="2",
                 os_options=None):
        socket.setdefaulttimeout(30.0)  # timeout set at socket level
        Connection.__init__(self, auth_url, user_name, key, retries=0,
                            os_options=os_options,
                            auth_version=auth_version)
        # needed if keystone-get-token does not work
        self.object_store_url = object_store_url
        self.state = dict()
        for sev in severities:
            for component_name in self.component_names():
                self.state[component_name + sev] = \
                    dict(current_state=component_states.unknown,
                         reason='',
                         metrics={})

        self.latency = dict()
        self.metric_data = []
        self.latency_reset()
        self.logger = logger
        self.cache_file_path = cache_file_path

    @staticmethod
    def component_names():
        return (COMPONENT_KEYSTONE_GET_TOKEN,
                COMPONENT_REST_API,
                COMPONENT_HEALTHCHECK_API)

    def metric_data_reset(self):
        self.metric_data = []

    def dump_metric_data(self):
        self.logger.debug("PRINTING CONTENTS OF METRIC DATA")

        # Read the component state metrics and append them to metrics_data dict
        for sev in severities:
            for component_name in self.component_names():
                self.metric_data.append(self.state[component_name +
                                                   sev]['metrics'])

        self.logger.debug(self.metric_data)
        dump_swiftlm_uptime_data(self.metric_data,
                                 self.cache_file_path,
                                 self.logger)

    def latency_reset(self):
        for component_name in self.component_names():
            self.latency[(component_name, 'num-samples')] = 0
            self.latency[(component_name, 'total-time')] = 0
            self.latency[(component_name, 'max-latency')] = 0

    def latency_record(self, component_name, duration):
        if duration > self.latency[(component_name, 'max-latency')]:
            self.latency[(component_name, 'max-latency')] = duration
        self.latency[(component_name, 'num-samples')] += 1
        self.latency[(component_name, 'total-time')] += duration

    def latency_write_log(self):
        # TODO log the latency data every 10 cycle at INFO level
        for component_name in self.component_names():
            if self.latency[(component_name, 'total-time')] == 0:
                self.logger.debug('No latency data for %s'
                                  % component_name)
                continue
            avg_latency = float(self.latency[(component_name, 'total-time')] /
                                self.latency[(component_name, 'num-samples')])
            max_latency = self.latency[(component_name, 'max-latency')]
            self.logger.debug('Metric:%s:avg-latency: %s'
                              % (component_name, avg_latency))
            self.logger.debug('Metric:%s:max-latency: %s'
                              % (component_name, max_latency))
            dimensions = common_dimensions.copy()
            dimensions['component'] = component_name
            if component_name == COMPONENT_KEYSTONE_GET_TOKEN:
                dimensions['url'] = self.authurl
            else:
                dimensions['url'] = self.object_store_url
            self.metric_data.append(
                dict(metric=AVG_LATENCY, value=avg_latency,
                     dimensions=dimensions, timestamp=timestamp()))

            self.metric_data.append(
                dict(metric=MAX_LATENCY, value=max_latency,
                     dimensions=dimensions, timestamp=timestamp()))

    def record_state(self, sev, component_name, new_state, reason):
        self.logger.debug(" ++++++++++++++ record_state called %s %s %s %s" %
                          (sev, component_name, new_state, reason))
        # Pick out the name (drop https://, port and path)
        k = component_name + sev
        if k in self.state.keys():
            old_state = self.state[component_name + sev]
        else:
            old_state = component_states.unknown
            state_details = dict(current_state=old_state,
                                 reason='',
                                 metrics={})
            self.state[component_name + severities.info] = state_details
            self.state[component_name + severities.hard] = state_details

        if old_state != new_state:
            now = time.time()
            state_details = self.state[component_name + sev]

            state_details['current_state'] = new_state
            state_details['reason'] = reason

            dimensions = common_dimensions.copy()
            dimensions['component'] = component_name
            if component_name == COMPONENT_KEYSTONE_GET_TOKEN:
                dimensions['url'] = self.authurl
            else:
                dimensions['url'] = self.object_store_url

            if sev == severities.info:
                metric_name = INFO_STATE
            elif sev == severities.hard:
                metric_name = HARD_STATE
            else:
                raise Exception("Invalid severity %s specified" % sev)
            # Report state as 0 for ok, 1 for failed and 3 for unknown
            # Monasca alarm expressions support only numerical values hence
            # report numbers for state so that we can configure alarms in
            # monasca
            if new_state == component_states.failed:
                state_details['metrics'] = \
                    dict(metric=metric_name,
                         value=STATE_VALUE_FAILED,
                         dimensions=dimensions,
                         timestamp=timestamp(),
                         value_meta={'msg': str(reason)})
            elif new_state == component_states.ok:
                state_details['metrics'] = \
                    dict(metric=metric_name,
                         value=STATE_VALUE_OK,
                         dimensions=dimensions,
                         timestamp=timestamp())
            else:
                # this condition may not exist, still adding it to
                # be complete
                state_details['metrics'] = \
                    dict(metric=metric_name,
                         value=STATE_VALUE_UNKNOWN,
                         dimensions=dimensions,
                         timestamp=timestamp())

            message = '{0} {1} {2}'.format(component_name, new_state, reason)
            # We need to log all state transitions at INFO level
            self.logger.info('%s %s %s %s\n'
                             % (time.strftime('%Y%m%d-%H:%M.%S',
                                              time.gmtime(now)), now, sev,
                                message.replace('\n', ' ')))

    def check_keystone_get_token(self):

        # Ask keystone for a token
        retries = 1  # don't try too hard
        attempts = 0
        component = COMPONENT_KEYSTONE_GET_TOKEN
        component_state = component_states.ok
        reason = 'success'

        while attempts <= retries:
            start_time = time.time()
            try:
                self.logger.debug('Doing GET AUTH')
                start_time = time.time()
                self.url, token = self.get_auth()
                duration = time.time() - start_time
                self.latency_record(component, duration)
                self.logger.debug('SUCCESS; token: %s    in %s'
                                  % (self.token, duration))
                self.token = token
                component_state = component_states.ok
                reason = 'success'
            except (socket.error, HTTPException, ClientException,
                    ConnectionError) as err:
                duration = time.time() - start_time
                self.latency_record(component, duration)
                self.record_state(severities.info, component,
                                  component_states.failed, err)
                component_state = component_states.failed
                reason = err
            if component_state == component_states.failed:
                time.sleep(1)
                attempts += 1
            else:
                attempts = retries + 1  # break out of loop

        self.record_state(severities.hard, component, component_state, reason)
        self.record_state(severities.info, component, component_state, reason)
        return component_state

    def check_object_store(self):
        # If no token then cannot perform request
        if not self.token:
            self.record_state(severities.info, COMPONENT_REST_API,
                              component_states.failed,
                              'Authentication failed')
            self.record_state(severities.hard, COMPONENT_REST_API,
                              component_states.failed,
                              'Authentication failed')
            return

        retries = 3
        attempts = 0
        tinyobj_contents = str(uuid.uuid4())  # Create random contents
        tinyobj_name = 'tinyobj-' + socket.gethostname()
        component_state = component_states.ok
        reason = 'success'

        while attempts <= retries:
            obj_start_time = time.time()
            start_time = obj_start_time
            try:
                self.http_conn = None  # Force new connection
                self.logger.debug('Doing OBJECT PUT/GET/DELETE')
                obj_start_time = time.time()
                start_time = obj_start_time
                self.head_account()
                duration = time.time() - start_time
                self.logger.debug('head-account ok in %s' % duration)
                start_time = time.time()
                self.put_container('swift_monitor_latency_test')
                duration = time.time() - start_time
                self.logger.debug('put-container ok in %s' % duration)
                start_time = time.time()
                self.put_object('swift_monitor_latency_test', tinyobj_name,
                                tinyobj_contents)
                duration = time.time() - start_time
                self.logger.debug('put-object ok in %s' % duration)
                start_time = time.time()
                headers, body = self.get_object('swift_monitor_latency_test',
                                                tinyobj_name,
                                                resp_chunk_size=65536)
                chunks = []
                for chunk in body:
                    self.logger.debug('get-object chunk: %s' % chunk)
                    chunks.append(chunk)
                duration = time.time() - start_time
                self.logger.debug('get-object ok in %s' % duration)
                start_time = time.time()
                self.delete_object('swift_monitor_latency_test', tinyobj_name)
                duration = time.time() - start_time
                self.logger.debug('delete-object ok in %s' % duration)
                duration = time.time() - obj_start_time
                self.latency_record(COMPONENT_REST_API, duration)
                component_state = component_states.ok
                reason = 'success'
            except (socket.error, HTTPException, ClientException,
                    ConnectionError) as err:
                duration = time.time() - start_time
                self.latency_record(COMPONENT_REST_API, duration)
                self.record_state(severities.info, COMPONENT_REST_API,
                                  component_states.failed, err)
                component_state = component_states.failed
                reason = err
            if component_state == component_states.failed:
                time.sleep(1)
                attempts += 1
            else:
                attempts = retries + 1  # break out of loop

        self.record_state(severities.hard, COMPONENT_REST_API, component_state,
                          reason)
        self.record_state(severities.info, COMPONENT_REST_API, component_state,
                          reason)
        return component_state

    def check_object_store_health_check(self, logger):

        component = COMPONENT_HEALTHCHECK_API
        retries = 3
        attempts = 0
        component_state = component_states.ok
        reason = 'success'

        while attempts <= retries:
            start_time = time.time()
            try:
                self.http_conn = None  # Force new connection
                logger.debug('Doing GET /healthcheck')
                start_time = time.time()
                health_check(self.object_store_url, self.logger)
                duration = time.time() - start_time
                self.latency_record(component, duration)
                logger.debug('Ok in %s' % duration)
                component_state = component_states.ok
                reason = 'success'
            except (socket.error, HTTPException, ClientException,
                    RequestException, ConnectionError) as err:
                duration = time.time() - start_time
                self.latency_record(component, duration)
                self.record_state(severities.info, component,
                                  component_states.failed, err)
                component_state = component_states.failed
                reason = err
            if component_state == component_states.failed:
                time.sleep(1)
                attempts += 1
            else:
                attempts = retries + 1  # break out of loop

        self.record_state(severities.hard, component, component_state, reason)
        self.record_state(severities.info, component, component_state, reason)
        return component_state


def main_loop(parsed_arguments, logger):
    args_to_log = [(key, value) for key, value in parsed_arguments.iteritems()
                   if key != 'password']
    logger.info('Starting swiftlm uptime monitor service with following'
                ' parameters:\n'
                '%s' % args_to_log)
    os_options = {}
    if parsed_arguments['region']:
        os_options['region'] = parsed_arguments['region']

    if parsed_arguments['project_id']:
        os_options['project_id'] = parsed_arguments['project_id']
    elif parsed_arguments['project_name']:
        os_options['project_name'] = parsed_arguments['project_name']
    if parsed_arguments['endpoint_type']:
        os_options['endpoint_type'] = parsed_arguments['endpoint_type']

    conn = TrackConnection(parsed_arguments['keystone_auth_url'],
                           parsed_arguments['user_name'],
                           parsed_arguments['password'],
                           logger,
                           parsed_arguments['cache_file_path'],
                           object_store_url=parsed_arguments[
                               'object_store_url'],
                           auth_version=parsed_arguments['auth_version'],
                           os_options=os_options)

    common_dimensions['observer_host'] = socket.gethostname()
    common_dimensions['service'] = SERVICE_NAME

    if parsed_arguments['region']:
        common_dimensions['region'] = parsed_arguments['region']

    while True:
        conn.latency_reset()
        conn.metric_data_reset()
        if conn.user != "None":
            conn.check_keystone_get_token()
        if conn.user != "None":
            for proxy in range(0, parsed_arguments['objectChecksPerInterval']):
                service_state = conn.check_object_store()
                if service_state != component_states.ok:
                    break
        for proxy in range(0, parsed_arguments['objectChecksPerInterval']):
            service_state = conn.check_object_store_health_check(logger)
            if service_state != component_states.ok:
                break

        conn.latency_write_log()
        conn.dump_metric_data()
        time.sleep(parsed_arguments['main_loop_interval'])


usage_message = """

OVERVIEW

This program performs a set of operations as follows
at each cycle:

1/ Gets a token from the Keystone service (keystone-get-token)
2/ Performs a number of HEAD operations against the account using
   this token and the Swift URL/account (rest-api)
   If we cannot get a token from the keystone service, we continue
   to use the existing token. If this becomes invalid, the
   rest-api is marked failed.
3/ Performs a number of healthcheck-api operations against the Swift
   endpoint (healthcheck-api)

For rest-api and healthcheck-api operations, they are repeated
many times each cycle. The idea is to make the load balancers
round robin us through all the proxies. See checks_per_interval
below.

Writes to syslog LOG_LOCAL0 facility as follows:
- A record of each transition from ok to failure and vice vera

  Records look something like:
      20120418-20:00.33 1334779233.48 hard rest-api failed ECONNREFUSED
      20120418-20:00.43 1334779243.50 hard rest-api ok success

  Fields as follows:
      20120418-20:00.33 - human readable date
      1334779233.48 - timestamp in seconds
      hard/failed - means the component failed even after several retries
             info/failed  means that the component failed on first try
             If this is a temporary glitch, you should expect to see
             an info/ok within a few seconds
             If not, then expect to see hard/failed after retries
             are exhausted
      rest-api - The name of the component.
             The names of all components are as follows:
             keystone-get-token -- the AUTH service
             rest-api -- Swift access using a token
             healthcheck-api -- Swift healthcheck-api (no token)
      ECONNREFUSED - on failures, records the immediate cause

- Each access is timed. At each cycle the latency data is written
  to a /var/cache/swift/swiftlm_uptime_monitor/uptime.stats file
  and at every Nth cycle latency data is written to syslog LOG_LOCAL0
  facility. The data includes the average and max latency over all the
  requests made against a service for the cycle. The records look lke:
      2012/04/19 14:58:01 UTC metric:rest-api:avg-latency: 0.0136341639927
      2012/04/19 14:58:01 UTC metric:rest-api:max-latency: 0.0152399539948
  The unit at the end is seconds.
  We measure latency of keystone-get-token, rest-api and healthcheck-api
  components.

FILES

The configuration file is specifed using the -c/--config option. This files
looks something like:
    [logging]
    # You can specify default log routing here if you want:
    log_level = info
    log_facility = LOG_LOCAL0
    log_format = '%(name)s - %(levelname)s : %(message)s'

    [latency_monitor]
    # Time between each cycle
    interval:60

    # Number of operations to make each cycle. Make this larger
    # than number of proxy servers
    checks_per_interval:70

    #The file path where the uptime stats are written
    cache_file_path: /var/cache/swift/swiftlm_uptime_monitor/uptime.stats

    #You must speicfy both keystone_auth_url and object_store_url
    # object_store_url is requried for performing healtchcheck operation
    keystone_auth_url: https://region-1.identity.my.com:35357/v2.0/
    object_store_url: https://region-1.objects.my.com/v1.0/
    endpoint_type: internalURL

    # Credential information -- uses Keystone V2 format
    user_name: my.address@example.com
    password: whatever
    # If both project_name and project_id are specified, project_id is
      considered for authentication
    project-id: 12345678912345
    project_name: myproject
    auth_version:2 # if not specified defaults to 2
"""


def parse_args(args):
    parser = argparse.ArgumentParser(
        description='swift-uptime-mon '
                    '--config CONFIGFILE',
        usage=usage_message)
    parser.add_argument('-c', '--config', dest='configFile',
                        default='/etc/swift/swiftlm-uptime-monitor.conf')
    return parser.parse_args(args)


def validate_args(config):
    if not config.has_section('logging'):
        raise UPtimeMonException(
            "Please specify logging options in config file")

    if not config.has_section('latency_monitor'):
        raise UPtimeMonException(
            "Please specify latency_monitor options in config file")

    logger = get_logger(dict(config.items('logging')), name='uptime-mon')
    parsed_arguments = {}
    try:
        parsed_arguments['object_store_url'] = config.get('latency_monitor',
                                                          'object_store_url')
    except ConfigParser.NoOptionError:
        msg = "Please provide Object Store URL, Quitting swift uptime mon"
        logger.exception(msg)
        raise UPtimeMonException(msg)
    try:
        parsed_arguments['endpoint_type'] = config.get('latency_monitor',
                                                       'endpoint_type')
    except ConfigParser.NoOptionError:
        parsed_arguments['endpoint_type'] = getenv('OS_ENDPOINT_TYPE')
    try:
        parsed_arguments['main_loop_interval'] = int(
            config.get('latency_monitor', 'interval'))
    except ConfigParser.NoOptionError:
        parsed_arguments['main_loop_interval'] = 40
    try:
        parsed_arguments['objectChecksPerInterval'] = int(
            config.get('latency_monitor', 'checks_per_interval'))
    except ConfigParser.NoOptionError:
        parsed_arguments['objectChecksPerInterval'] = 60
    try:
        parsed_arguments['keystone_auth_url'] = config.get('latency_monitor',
                                                           'keystone_auth_url')
    except ConfigParser.NoOptionError:
        parsed_arguments['keystone_auth_url'] = getenv('OS_AUTH_URL')
    try:
        parsed_arguments['user_name'] = config.get('latency_monitor',
                                                   'user_name')
    except ConfigParser.NoOptionError:
        parsed_arguments['user_name'] = getenv('OS_USERNAME')
    try:
        parsed_arguments['password'] = config.get('latency_monitor',
                                                  'password')
    except ConfigParser.NoOptionError:
        parsed_arguments['password'] = getenv('OS_PASSWORD')
    try:
        parsed_arguments['auth_version'] = config.get('latency_monitor',
                                                      'auth_version')
    except ConfigParser.NoOptionError:
        # If auth version is not specified default it to 2.0
        parsed_arguments['auth_version'] = '2.0'

    try:
        parsed_arguments['project_id'] = config.get('latency_monitor',
                                                    'project_id')
    except ConfigParser.NoOptionError:
        parsed_arguments['project_id'] = getenv('OS_PROJECT_ID')
    try:
        parsed_arguments['project_name'] = config.get('latency_monitor',
                                                      'project_name')
    except ConfigParser.NoOptionError:
        parsed_arguments['project_name'] = getenv('OS_PROJECT_NAME')

    try:
        parsed_arguments['region'] = config.get('latency_monitor', 'region')
    except ConfigParser.NoOptionError:
        parsed_arguments['region'] = getenv('OS_REGION')

    try:
        parsed_arguments['cache_file_path'] = config.get('latency_monitor',
                                                         'cache_file_path')
    except ConfigParser.NoOptionError:
        msg = "Please specify cache file path, Quitting swift uptime mon"
        logger.exception(msg)
        raise UPtimeMonException(msg)

    if parsed_arguments['user_name'] is None:
        message = "User name is mandatory, Quitting swift uptime mon"
        logger.exception(message)
        raise UPtimeMonException(message)

    if parsed_arguments['password'] is None:
        message = "Password is mandatory, Quitting swift uptime mon"
        logger.exception(message)
        raise UPtimeMonException(message)

    if parsed_arguments['keystone_auth_url'] is None:
        message = ("Keystone Auth URL is mandatory, "
                   "Unable to get this URL from OS_AUTH_URL "
                   "environment variable, Quitting swift uptime mon")
        logger.exception(message)
        raise UPtimeMonException(message)

    if parsed_arguments['project_id'] is None and \
       parsed_arguments['project_name'] is None:
        message = ("One of project_name or project_id must be specified, "
                   "Quitting swift uptime mon")
        logger.exception(message)
        raise UPtimeMonException(message)

    return parsed_arguments, logger


def main():
    args = parse_args(sys.argv[1:])

    # Ensure configuration file is present
    if not path.isfile(args.configFile):
        message = "Config file not present, Quitting swift uptime mon"
        raise Exception(message)

    config = ConfigParser.RawConfigParser()
    config.read(args.configFile)
    parsed_arguments, logger = validate_args(config)

    # if both project_id and project_name are specified use project_id
    if parsed_arguments['project_id']:
        if parsed_arguments['project_name']:
            del parsed_arguments['project_name']

    main_loop(parsed_arguments, logger)
    exit(0)


if __name__ == "__main__":
    main()
