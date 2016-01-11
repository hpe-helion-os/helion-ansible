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


import threading

try:
    import commands as commands_wrapper
except ImportError:
    import subprocess as commands_wrapper
import glob

import os.path
from collections import namedtuple

from swiftlm.utils.ringdata import RingData
from swiftlm.utils.values import ServerType
from swiftlm.utils import SWIFT_PATH, PROXY_PATH, ACCOUNT_PATH, \
    CONTAINER_PATH, OBJECT_PATH

import logging
import syslog
import signal
import time
import fcntl
from contextlib import contextmanager
import errno
import json

import datetime
import ConfigParser

swiftlm_scan_conf = "/etc/swiftlm/swiftlm-scan.conf"

# namedtuple for use with the results from RingData.devs
RingDeviceEntry = namedtuple('RingDeviceEntry', ['ip', 'port', 'device'])
# More descriptive wrapper around the results of run_command
CommandResult = namedtuple('CommandResult', ['exitcode', 'output'])

LOG_LEVEL_MAP = {'debug': logging.DEBUG,
                 'info': logging.INFO,
                 'warning': logging.WARNING,
                 'error': logging.ERROR,
                 'critical': logging.CRITICAL}

SYSLOG_LEVEL_MAP = {'debug': syslog.LOG_DEBUG,
                    'info': syslog.LOG_INFO,
                    'warning': syslog.LOG_WARNING,
                    'error': syslog.LOG_ERR,
                    'critical': syslog.LOG_CRIT}

LOG_FACILITY_MAP = {"LOG_LOCAL0": syslog.LOG_LOCAL0,
                    "LOG_LOCAL1": syslog.LOG_LOCAL1,
                    "LOG_LOCAL2": syslog.LOG_LOCAL2,
                    "LOG_LOCAL3": syslog.LOG_LOCAL3,
                    "LOG_LOCAL4": syslog.LOG_LOCAL4,
                    "LOG_LOCAL5": syslog.LOG_LOCAL5,
                    "LOG_LOCAL6": syslog.LOG_LOCAL6,
                    "LOG_LOCAL7": syslog.LOG_LOCAL7}


class UtilityExeception(Exception):
    pass


class SwiftlmSysLogHandler(logging.Handler):
    """A logging handler that emits messages to syslog.syslog."""
    def __init__(self, log_facility, log_level_str):
        try:
            syslog.openlog(logoption=syslog.LOG_PID, facility=log_facility)
        except IOError:
            try:
                syslog.openlog(syslog.LOG_PID, log_facility)
            except IOError:
                try:
                    syslog.openlog('swiftlm', syslog.LOG_PID,
                                   log_facility)
                except:
                    raise
        syslog.setlogmask(syslog.LOG_UPTO(SYSLOG_LEVEL_MAP[log_level_str]))
        logging.Handler.__init__(self)

    def emit(self, record):
        syslog.syslog(self.format(record))


class Timeout():
    """Timeout class using ALARM signal."""
    class Timeout(Exception):
        pass

    def __init__(self, seconds):
        self.seconds = seconds

    def __enter__(self):
        signal.signal(signal.SIGALRM, self.raise_timeout)
        signal.alarm(self.seconds)

    def __exit__(self, *args):
        signal.alarm(0)    # disable alarm

    def __str__(self):
        return '%s' % str(self.seconds)

    @staticmethod
    def raise_timeout(*args):
        raise Timeout.Timeout()


class MessageTimeout(Timeout):

    def __init__(self, seconds=None, msg=None):
        # Timeout.__init__(self, seconds=seconds)
        Timeout.__init__(self, seconds)
        self.msg = msg

    def __str__(self):
        return '%s: %s' % (Timeout.__str__(self), self.msg)


class LockTimeout(MessageTimeout):
    pass


class Enum(set):
    def __getattr__(self, name):
        if name in self:
            return name
        raise AttributeError


def run_cmd(cmd):
    # Wrapper around commands and subprocess.
    # we dont want to have to do try..except ImportError
    # all over the code and in the tests.
    return CommandResult(*commands_wrapper.getstatusoutput(cmd))


def get_swift_bind_ips(interface=None):
    """
    Get unique bind ips from swiftlm-scan.conf.

    :returns: set of bind_ips
    """
    bind_ips = set()
    option_name_list = ["proxy_bind_ip", "account_bind_ip",
                        "containter_bind_ip", "object_bind_ip",
                        "account_replication_ip", "container_replication_ip",
                        "object_replication_ip"
                        ]
    if interface is None:
        parser = ConfigParser.RawConfigParser()
        parser.read(swiftlm_scan_conf)
        for option_name in option_name_list:
            try:
                ip = parser.get("network-interface", option_name)
                bind_ips.add(ip)
            except (ConfigParser.NoOptionError, ConfigParser.NoSectionError):
                pass
    return bind_ips


def ip_to_interface():
    """
    Obtain an ip to interface map by parsing netstat -ie output.

    :returns: dictionary of ip to interface mapping
    """
    # netstat -ie produces...
    # Kernel Interface table <not needed>
    # br-eth1 Link encap:Ethernet HWaddr ca:7f:53:3f:26:4e
    #         inet addr:192.168.245.3 Bcast:192.168.245.15 Mask:255.255.255.240
    #         <not needed text>
    #
    # eth0   Link encap:Ethernet HWaddr 52:54:00:e3:c8:56
    #        inet addr:192.168.121.171 Bcast:192.168.121.255 Mask:255.255.255.0
    #        <not needed text>
    netstat_string = commands_wrapper.getoutput("/bin/netstat -ie")
    netstat_lines = (netstat_string.split('\n', 1)[1]).split('\n')
    ip_to_interface_map = dict()
    next_interface = True

    for line in netstat_lines:
        words = line.split()
        if next_interface:
            interface_name = words[0]
            next_interface = False
        if not line:
            # Blank line. Next line (if present) will be the next interface.
            next_interface = True
        elif words[0] == 'inet':
            ip_address = words[1].split(':')[1]
            ip_to_interface_map[ip_address] = interface_name

    return ip_to_interface_map


def get_ring_hosts(ring_type=None):
    """
    Get data about hosts in a ring.

    :param ring_type: If is None data from all rings is returned.
                    If is ServerType only data from the rings of that server
                    type is returned.

    :returns: list of RingDeviceEntry
    """
    ring_data = []
    if not os.path.isdir(SWIFT_PATH):
        return ring_data

    ring_files = [f for f in os.listdir(SWIFT_PATH) if f.endswith('.ring.gz')]

    if ring_type is not None:
        if not isinstance(ring_type, ServerType):
            raise ValueError('ring_type must be a ServerType')
        ring_files = [r for r in ring_files if r.startswith(ring_type.name)]

    for r in ring_files:
        r = os.path.join(SWIFT_PATH, r)
        rd = RingData.load(r)
        for device in rd.devs:
            ring_data.append(
                RingDeviceEntry(
                    device['ip'], device['port'], device['device']))

    return ring_data


def server_type(*args):
    """
    Get information about the type of server checks are running on

    :args: ServerType(s) or None

    :returns: if No args returns a dictionary of ServerType.X.name: bool
                for all ServerTypes
              if 1 arg returns a bool
              if 2+ args returns a tuple of bools

    Does not support SAIO.

    Example:
        am_i_pac = all(server_type(ServerType.proxy, ServerType.account,
                                   ServerType.container)
            or

        st = server_type()
        am_i_pac = st['proxy'] and st['account'] and st['container']
    """

    def conf_file_present(path, conf):
        return os.path.isfile(path + conf)

    active_server_types = {
        ServerType.object: conf_file_present(OBJECT_PATH,
                                             'object-server.conf'),
        ServerType.proxy: conf_file_present(PROXY_PATH,
                                            'proxy-server.conf'),
        ServerType.container: conf_file_present(CONTAINER_PATH,
                                                'container-server.conf'),
        ServerType.account: conf_file_present(ACCOUNT_PATH,
                                              'account-server.conf'),
    }

    try:
        if len(args) == 1:
            return active_server_types[args[0]]
        elif len(args) > 1:
            return (active_server_types[a] for a in args)
        else:
            return {k.name: v for k, v in active_server_types.items()}
    except KeyError:
        raise ValueError('args to server_type must be a ServerType')


def get_logger(conf, name=None):
    if not conf:
        conf = {}
    if not name:
        name = "swiftlm"

    # Some variables we need
    log_level_str = conf.get('log_level', 'info').lower()
    log_level = LOG_LEVEL_MAP[log_level_str]
    log_format = conf.get('log_format', '%(levelname)s : %(message)s')
    log_facility = LOG_FACILITY_MAP[conf.get('log_facility', 'LOG_LOCAL0')]
    # Configuring the logger
    logger = logging.getLogger(name=name)
    logger.setLevel(log_level)

    # Clearing previous logs
    logger.handlers = []

    # Setting formatters and adding handlers.
    formatter = logging.Formatter(log_format)
    handlers = [SwiftlmSysLogHandler(log_facility, log_level_str)]
    for h in handlers:
        h.setFormatter(formatter)
        logger.addHandler(h)
    return logger


@contextmanager
def lock_file(file_name, timeout=10, append=False, unlink=True):
    """
    Context manager that acquires a lock on a file.  This will block until
    the lock can be acquired, or the timeout time has expired (whichever occurs
    first).

    :param file_name: file to be locked
    :param timeout: timeout (in seconds)
    :param append: True if file should be opened in append mode
    :param unlink: True if the file should be unlinked at the end
    """
    flags = os.O_CREAT | os.O_RDWR
    if append:
        flags |= os.O_APPEND
        mode = 'a+'
    else:
        mode = 'r+'
    while True:
        fd = os.open(file_name, flags)
        file_obj = os.fdopen(fd, mode)
        try:
            with LockTimeout(timeout, file_name):
                while True:
                    try:
                        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        break
                    except IOError as err:
                        if err.errno != errno.EAGAIN:
                            raise
                    time.sleep(0.01)
            try:
                if os.stat(file_name).st_ino != os.fstat(fd).st_ino:
                    continue
            except OSError as err:
                if err.errno == errno.ENOENT:
                    continue
                raise
            yield file_obj
            if unlink:
                os.unlink(file_name)
            break
        finally:
            file_obj.close()


def dump_swiftlm_uptime_data(data_list, uptime_stats_file, logger,
                             lock_timeout=2):
    """Update swiftlm uptime data

    :param data_list: Dictionary of cache key/value pairs to write out
    :param uptime_stats_file: cache file to update
    :param logger: the logger to use to log an encountered error
    :param lock_timeout: timeout (in seconds)
    """
    try:
        with lock_file(uptime_stats_file, lock_timeout, unlink=False) as cf:
            cf.truncate()
            cf.write(json.dumps(data_list)+'\n')
    except (Exception, Timeout):
        logger.exception('Exception dumping swiftlm uptime cache')


def get_swiftlm_uptime_mon_data(uptime_stats_file, logger, openr=open):
    """retrieve values from a swiftlm uptime mon cache file

    :params cache_file: cache file to retrieve items from.
    :params openr: open to use [for unittests]
    :return: dict of cache items and their values or none if not found
    """
    try:
        with openr(uptime_stats_file, 'r') as f:
            return json.load(f)
    except IOError:
        logger.exception('Error reading swiftlm uptime mon cache file')
    except ValueError:
        logger.exception('Error parsing swiftlm uptime mon cache file')


def timestamp(dt=None,
              epoch=datetime.datetime(1970, 1, 1),
              allow_microseconds=False):
    """
    Return a timestamp in seconds since epoch.

    We normalize the timestamps to second precision since python2 cant do
    microseconds properly.
    Setting allow_microseconds=True will return them whenever possible
    but will make timestamps from different python versions inconsistent.

    This function assumes that all machines are configured with the same
    timezone.

    Passing in a epoch that has tz_info set will cause the timestamp to be TZ
    aware for python 2-3.2. Example:
        ts = timestamp(datetime.datetime(1970, 1, 1, tzinfo=timezone))
    To get a TZ aware timestamp for python 3.3+ you must pass in a
    datetime that has tz_info set. Example:
        dt = datetime.datetime.now().replace(tz_info=timezone)
        ts = timestamp(dt)

    In both cases timezone must be an implementation of the abstract base class
    datetime.tzinfo
    """
    if dt is None:
        dt = datetime.datetime.now()

    try:
        # Python 3.3+
        ts = dt.timestamp()
    except AttributeError:
        try:
            # Python 3.0-3.2
            # timedelta supports division
            ts = (dt - epoch) / datetime.timedelta(seconds=1)
        except TypeError:
            # Python 2
            ts = (dt - epoch).total_seconds()

    if allow_microseconds:
        return ts
    else:
        return int(ts)
