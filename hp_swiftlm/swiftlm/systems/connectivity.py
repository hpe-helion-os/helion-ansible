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


from threading import Thread, BoundedSemaphore
import urlparse

try:
    import configparser
except ImportError:
    import ConfigParser as configparser
import os
import socket
from collections import namedtuple

from swiftlm.utils.utility import (
    get_ring_hosts, server_type, UtilityExeception
)
from swiftlm.utils.metricdata import MetricData, get_base_dimensions
from swiftlm.utils.values import Severity, ServerType
from swiftlm.utils.utility import run_cmd

# Connectivity needs to report out target hostname and observer hostname
# rather than the normal hostname dimension
_base_dimensions = dict(get_base_dimensions())
_base_dimensions['observer_host'] = _base_dimensions['hostname']
del _base_dimensions['hostname']

BASE_RESULT = MetricData(
    name=__name__,
    messages={
        'ok': '{hostname}:{target_port} ok',
        'warn': 'No hosts to check',
        'fail': '{hostname}:{target_port} {fail_message}',
        'unknown': 'Unrecoverable error: {error}',
    },
    dimensions=_base_dimensions
)

MAX_THREAD_LIMIT = 10
SWIFT_PROXY_PATH = '/opt/stack/service/swift-proxy-server/etc'


class HostPort(namedtuple('HostPort', ['host', 'port'])):
    @classmethod
    def from_string(cls, s):
        """ Create a HostPort instance from a string """
        # Supports:
        # http://host.name, http://host.name:port
        # host.name, host.name:port
        # 10.10.10.10, 10.10.10.10:9999
        s = s.strip()
        colon_count = s.count(':')

        if colon_count == 2:
            return cls(*s.rsplit(':', 1))
        elif colon_count == 0:
            return cls(s, '0')
        elif colon_count == 1:
            colon_index = s.find(':')

            if (len(s) >= colon_index+2 and
                    s[colon_index+1] == s[colon_index+2] == '/'):
                # We ignore this, it is a URI scheme not a port.
                # We have to check the length of s first though, if s is
                # host:1 we could cause an indexerror.
                return cls(s, '0')
            else:
                return cls(*s.rsplit(':', 1))


class CheckThread(Thread):
    """ Threaded generic check """
    def __init__(self, hostport, check_func, thread_limit, result):
        """
        :params hostport: HostPort to be passed to check_func.
        :params check_func: function that accepts a HostPort, performs a check
                            and returns a bool indicating success or failure.
                            True is success, False is a failure
        :params thread_limit: BoundedSemaphore for limiting number of active
                              threads.
        :params result: MetricData that will contain the results of the threads
                        check.
        """
        Thread.__init__(self)
        self.thread_limit = thread_limit
        self.check_func = check_func
        self.hostport = hostport

        self.result = result
        self.result.name += '.' + check_func.__name__
        self.result['hostname'] = hostport.host
        self.result['target_port'] = hostport.port

    def run(self):
        self.thread_limit.acquire()
        check_result = self.check_func(self.hostport)

        if check_result[0]:
            self.result.value = Severity.ok
        else:
            self.result['fail_message'] = check_result[1]
            self.result.value = Severity.fail

        self.thread_limit.release()


def connect_check(hp):
    try:
        s = socket.create_connection(hp, 10.0)
        return (True,)
    except (socket.error, socket.timeout) as e:
        return (False, str(e))
    finally:
        try:
            s.shutdown(socket.SHUT_RDWR)
        except Exception:
            pass


def memcache_check(hp):
    try:
        s = socket.create_connection(hp, 10.0)
        s.sendall('stats\n')
        _ = s.recv(1024)
        return (True,)
    except (socket.error, socket.timeout) as e:
        return (False, str(e))
    finally:
        try:
            s.shutdown(socket.SHUT_RDWR)
        except Exception:
            pass


def ping_check(hp):
    try:
        cmd_result = run_cmd('ping -c 1 -A %s' % hp.host)
        if cmd_result.exitcode == 0:
            return (True,)
        else:
            return (False, "ping_check failed")
    except Exception:
        return (False, "ping_check failed")


def check(targets, check_func, results):
    threads = []
    thread_limit = BoundedSemaphore(value=MAX_THREAD_LIMIT)

    if not targets:
        c = BASE_RESULT.child()
        c.name += '.' + check_func.__name__
        c.value = Severity.warn
        results.append(c)
        return

    for target in targets:
        t = CheckThread(target, check_func, thread_limit, BASE_RESULT.child())
        t.start()
        threads.append(t)

    for t in threads:
        t.join(10.0)
        if t.isAlive():
            t.result.value = Severity.fail

        results.append(t.result)


def main():
    """Checks connectivity to memcache and object servers."""
    results = []

    if server_type(ServerType.proxy):
        cp = configparser.ConfigParser()
        cp.read(os.path.join(SWIFT_PROXY_PATH, 'proxy-server.conf'))

        try:
            memcache_servers = [
                HostPort.from_string(s) for s in
                cp.get('filter:cache', 'memcache_servers').split(',')
            ]
        except configparser.NoSectionError:
            memcache_servers = []

        check(memcache_servers, memcache_check, results)

        try:
            # Remove the version api path.
            ise = cp.get('filter:authtoken', 'identity_uri')
            parsed = urlparse.urlparse(ise)
            endpoint_servers = [HostPort(parsed.hostname, str(parsed.port))]
        except configparser.NoSectionError:
            endpoint_servers = []

        check(endpoint_servers, connect_check, results)

    # TODO -- rewrite this as a connect_check
    # try:
    #     ping_targets = []
    #     devices = get_ring_hosts(ring_type=None)
    #     ip_set = set()
    #
    #     for device in devices:
    #         if device.ip not in ip_set:
    #             # Port not relevant for ping_check. (Empty string is an
    #             # invalid dimension value, Hence '_' used for target_port)
    #             ping_targets.append(HostPort(device.ip, '_'))
    #             ip_set.add(device.ip)
    #
    # except Exception:  # noqa
    #   # may be some problem loading ring files, but not concern of this check
    #     # to diagnose any further.
    #     pass
    #
    # check(ping_targets, ping_check, results)

    return results
