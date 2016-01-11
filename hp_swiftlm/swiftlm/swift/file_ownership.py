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


import os
import os.path
import pwd

from swiftlm.utils.utility import server_type
from swiftlm.utils.metricdata import MetricData
from swiftlm.utils.values import Severity, ServerType

SWIFT_DIR = '/etc/swift'
CONF_DIR = '/etc'
NODE_DIR = '/srv/node'

ZERO_BYTE_EXCLUDE = frozenset(['reload-trigger', 'swauth_to_tenant_map.gz'])
SWIFT_OWNED_EXCLUDE = frozenset(['lost+found'])

BASE_RESULT = MetricData(
    name=__name__,
    messages={
        'empty': 'Path: {path} should not be empty',
        'ownership': 'Path: {path} is not owned by swift',
        'missing': 'Path: {path} is missing',
    }
)


def add_result(results, path, reason):
    c = BASE_RESULT.child(dimensions={'path': path})
    c.value = Severity.fail
    c.message = reason
    results.add(c)


def _is_swift_owned(results, p):
    # True = good, False = bad
    owner = pwd.getpwuid(os.stat(p).st_uid).pw_name
    if owner == 'swift':
        return True
    else:
        if os.path.basename(p) not in SWIFT_OWNED_EXCLUDE:
            add_result(results, p, 'ownership')
            return False


def not_swift_owned():
    results = set()
    # Check /etc/swift and its children
    p = SWIFT_DIR
    if os.path.isdir(p):
        for root, dirs, files in os.walk(p, followlinks=True):
            for d in dirs:
                x = os.path.join(root, d)
                _is_swift_owned(results, x)
            for f in files:
                x = os.path.join(root, f)
                _is_swift_owned(results, x)
    else:
        add_result(results, p, 'missing')

    # Check all disk directories in /srv/node/
    p = NODE_DIR
    if os.path.isdir(p):
        # We need to use topdown otherwise the directory tree is generated
        # first, This would be unacceptably slow with large numbers or objects
        for root, dirs, _ in os.walk(p, topdown=True):
            for d in dirs:
                x = os.path.join(root, d)
                _is_swift_owned(results, x)

            break   # We only want to check immediate child directories
    else:
        if server_type(ServerType.object):
            # We only care that this directory is missing on object servers.
            add_result(results, p, 'missing')
    return results


def _is_empty_file(results, p):
    # True = bad, False = good
    # Should think of a way to make false = bad here to match _is_swift_owned
    if not os.path.isfile(p):
        add_result(results, p, 'missing')
        return True

    if (os.stat(p).st_size == 0 and
            os.path.basename(p) not in ZERO_BYTE_EXCLUDE):
        add_result(results, p, 'empty')
        return True

    return False


def empty_files():
    results = set()
    # Check individual files
    if not server_type(ServerType.proxy):
        _is_empty_file(results, CONF_DIR + '/rsyncd.conf')

    _is_empty_file(results, CONF_DIR + '/rsyslog.conf')

    # Check all children in /etc/swift
    p = SWIFT_DIR
    if os.path.isdir(p):
        for root, _, files in os.walk(p, followlinks=True):
            for f in files:
                x = os.path.join(root, f)
                _is_empty_file(results, x)
    else:
        add_result(results, p, 'missing')
    return results


def main():
    """Check that swift owns its relevant files and directories."""
    results = not_swift_owned()
    results.update(empty_files())
    return list(results)


if __name__ == "__main__":
    main()
