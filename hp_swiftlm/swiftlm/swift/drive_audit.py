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


import ast
import subprocess

from swiftlm.utils.metricdata import MetricData
from swiftlm.utils.values import Severity

ERRORS_PATTERN = 'drive-audit: Errors found:'
DEVICES_PATTERN = 'drive-audit: Devices found:'

BASE_RESULT = MetricData(
    name=__name__,
    messages={
        'ok': 'No errors found on device mounted at: {mount_point}',
        'warn': 'No devices found',
        'fail': 'Errors found on device mounted at: {mount_point}',
        'unknown': 'Unrecoverable error: {error}'
    }
)


def get_devices(output):
    """
    Returns a list of devices as a dict of mount_point and device
    """
    # TODO use drive_model.yml to determine drives to check
    lines = [s.strip() for s in output.split('\n') if s]
    for line in lines:
        if DEVICES_PATTERN in line:
            devs = line.split(DEVICES_PATTERN)[1].strip()
            devices = ast.literal_eval(devs)
            return [{'mount_point': d['mount_point'],
                     'kernel_device': d['kernel_device'][:-1]} for
                    d in devices]


def get_error_devices(output):
    """
    Returns a dict of mapping device->error count for each device
    with errors.
    """
    lines = [s.strip() for s in output.split('\n') if s]
    for line in lines:
        if ERRORS_PATTERN in line:
            devices = line.split(ERRORS_PATTERN)[1].strip()
            err_devices = ast.literal_eval(devices)
            return err_devices


def check_errors():
    try:
        # TODO check that '/etc/swift/drive-audit.conf' exists and
        # has log_to_console set
        process = subprocess.Popen(
            ['swift-drive-audit', '/etc/swift/drive-audit.conf'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        _, output = process.communicate()
    except (OSError, IOError) as e:
        result = BASE_RESULT.child(dimensions={'error': str(e)})
        result.value = Severity.unknown
        return result

    found_devs = get_devices(output)
    if not found_devs:
        result = BASE_RESULT.child()
        # TODO maybe bump this up to a fail
        result.value = Severity.warn
        return result

    results = []
    error_devices = get_error_devices(output)
    for dev in found_devs:
        dimensions = dict(dev)
        result = BASE_RESULT.child(dimensions=dimensions)
        if dev.get('kernel_device') in error_devices.keys():
            # TODO might like to include error count in value_meta
            result.value = Severity.fail
        else:
            result.value = Severity.ok
        results.append(result)
    return results


def main():
    """Checks for corrupted sectors on drives."""
    return check_errors()
