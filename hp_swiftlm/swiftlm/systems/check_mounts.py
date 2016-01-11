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

from __future__ import print_function

import grp
import os
import pwd
import json
import subprocess
from collections import namedtuple

from swiftlm.utils.values import Severity
from swiftlm.utils.metricdata import MetricData
from swiftlm.utils.utility import run_cmd

DEVICES = '/etc/ansible/facts.d/swift_drive_info.fact'
MOUNT_PATH = '/srv/node/'
LABEL_CHECK_DISABLED = '---NA---'

Device = namedtuple('Device', ['device', 'mount', 'label'])


def get_devices():
    """
    Parses ansible facts file in JSON format to discover drives.
    Required facts in the format are shown below.
    {
        ...
        "devices": [{
            "name": "/dev/sd#",
            "swift_drive_name": "disk0",
            "label": "0000000d001",
            ...
            }
        ]
        ...
    }

    label is not currently in the file so we stub it out with NO_LABEL.
    """
    try:
        with open(DEVICES, 'r') as f:
            data = json.load(f)['devices']
    except (IOError, ValueError):
        data = []

    devices = []
    for d in data:
        l = d.get('label', LABEL_CHECK_DISABLED)
        devices.append(Device(
            device=d['name'],
            mount=MOUNT_PATH+d['swift_drive_name'],
            label=l
        ))

    return devices


def is_mounted(d, r):
    return os.path.ismount(d.mount)


def is_mounted_775(d, r):
    # Take the last three digits of the octal repr of the permissions.
    perms = oct(os.stat(d.mount).st_mode)[-3:]
    if perms == '755':
        return True
    else:
        r['permissions'] = perms
        return False


def is_ug_swift(d, r):
    """Checks mount point is owned by swift"""
    stats = os.stat(d.mount)
    uid = stats.st_uid
    gid = stats.st_gid

    user = pwd.getpwuid(uid).pw_name
    group = grp.getgrgid(gid).gr_name
    if user == group == 'swift':
        return True
    else:
        r['user'] = user
        r['group'] = group
        return False


def is_valid_label(d, r):
    if d.label == LABEL_CHECK_DISABLED:
        return True

    rc = run_cmd('xfs_admin -l %s | grep -q %s' % (d.mount, d.label))
    if rc.exitcode == 0:
        return True
    else:
        return False


def is_xfs(d, r):
    rc = run_cmd('mount | grep -qE "%s.*xfs"' % d.mount)
    if rc.exitcode == 0:
        return True
    else:
        return False


def is_valid_xfs(d, r):
    rc = run_cmd('xfs_info %s' % d.mount)
    if rc.exitcode == 0:
        return True
    else:
        return False


BASE_RESULT = MetricData(
    name=__name__,
    messages={
        is_mounted.__name__: '{device} not mounted at {mount}',
        is_mounted_775.__name__: ('{device} mounted at {mount} has permissions'
                                  ' {permissions} not 755'),
        is_ug_swift.__name__: ('{device} mounted at {mount} is not owned by'
                               ' swift, has user: {user}, group: {group}'),
        is_valid_label.__name__: ('{device} mounted at {mount} has invalid '
                                  'label {label}'),
        is_xfs.__name__: '{device} mounted at {mount} is not XFS',
        is_valid_xfs.__name__: '{device} mounted at {mount} is corrupt',
        'ok': '{device} mounted at {mount} ok',
        'no_devices': 'No devices found'
    }
)


def check_mounts():
    results = []
    checks = (
        is_mounted,
        is_mounted_775,
        is_ug_swift,
        is_valid_label,
        is_xfs,
        is_valid_xfs)

    devices = get_devices()
    if not devices:
        result = BASE_RESULT.child()
        result.value = Severity.warn
        result.message = 'no_devices'

        return result

    for d in devices:
        result = BASE_RESULT.child(dimensions=d.__dict__)
        for check in checks:
            if not check(d, result):
                result.message = check.__name__
                result.value = Severity.fail
                break
        else:
            result.value = Severity.ok

        results.append(result)

    return results


def main():
    """Checks the relevant swift mount points."""
    return check_mounts()


if __name__ == "__main__":
    print(main())
