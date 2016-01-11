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


import json

from swiftlm.utils.metricdata import MetricData, timestamp, CheckFailure
from swiftlm.utils.values import Severity, ServerType

RECON_PATH = '/var/cache/swift/'
TIMEOUT = 2
BASE_RESULT = MetricData(
    name=__name__,
    messages={}
)


def _recon_check(st):
    """
    Parses the blah.recon file and returns the last replication.

    :param st: ServerType, Used to determine the metric names and recon
        file name.
    :param replication_field_name: string, name of the field in the json
        file that hold the last replication data.
    """
    results = []
    if not st.is_instance:
        return results
    r = BASE_RESULT.child(name=st.name + '.last_replication')
    recon_file = st.name + '.recon'
    try:
        with open(RECON_PATH + recon_file) as f:
            j = json.load(f)

        last_replication = j.get('replication_last')
        if last_replication is None:
            last_replication = j.get('object_replication_last')

        last_replication = int(last_replication)
        last_replication = timestamp() - last_replication
    except (ValueError, IOError) as e:
        c = CheckFailure.child(dimensions={
            'check': r.name,
            'error': str(e)
        })
        c.value = Severity.fail
        results.append(c)
        last_replication = 0

    r.value = last_replication
    results.append(r)
    return results


def object_recon_check():
    return _recon_check(ServerType.object)


def container_recon_check():
    return _recon_check(ServerType.container)


def account_recon_check():
    return _recon_check(ServerType.account)


def main():
    """Checks replication and health status."""
    results = []
    results.extend(object_recon_check())
    results.extend(container_recon_check())
    results.extend(account_recon_check())

    return results
