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
import re

from swiftlm.utils.utility import server_type
from swiftlm.utils.metricdata import MetricData
from swiftlm.utils.values import Severity

PROC_DIR = '/proc'

BASE_RESULT = MetricData(
    name=__name__,
    messages={
        'fail': '{component} is not running',
        'ok': '{component} is running',
        'unknown': 'no swift services running',
    }
)

SERVICES = [
    "account-auditor",
    "account-reaper",
    "account-replicator",
    "account-server",
    "container-replicator",
    "container-server",
    "container-updater",
    "container-auditor",
    "object-replicator",
    "object-server",
    "object-updater",
    "object-auditor",
    "proxy-server"
]


def services_to_check():
    # Filter SERVICES down to what should be running on the node.
    # server_type returns a dict of {'object': bool, etc}
    prefix_server_type = tuple(k for k, v in server_type().items() if v)
    services = [s for s in SERVICES if s.startswith(prefix_server_type)]

    return services


def check_swift_processes():
    results = []

    services = services_to_check()

    if not services:
        c = BASE_RESULT.child()
        c.value = Severity.unknown
        return c

    for service in services:
        c = BASE_RESULT.child(dimensions={'component': service})

        if not is_service_running(service):
            c.value = Severity.fail
        else:
            c.value = Severity.ok

        results.append(c)

    return results


def is_service_running(service):
    for sub_directory in os.listdir(PROC_DIR):
        if ((os.path.exists(os.path.join(PROC_DIR, sub_directory, "comm"))) and
                (re.match("^[0-9]+", sub_directory))):
            cmdline = os.path.join(PROC_DIR, sub_directory, "cmdline")
            if "swift-" + service in open(cmdline, "r").read():
                return True

    # Reach here if no matching process not found in /proc/cmdline
    return False


def main():
    """Check that the relevant services are running."""
    return check_swift_processes()
