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


import re

from swiftlm.utils.metricdata import MetricData, CheckFailure
from swiftlm.utils.values import Severity
from swiftlm.utils.utility import run_cmd

BASE_RESULT = MetricData(
    name=__name__,
    messages={
        'ok': 'OK',
        'fail': 'ntpd not running: {error}',
    }
)


def check_status():
    cmd_result = run_cmd('systemctl status ntp')
    r = BASE_RESULT.child()

    if cmd_result.exitcode != 0:
        r['error'] = cmd_result.output
        r.value = Severity.fail
    else:
        r.value = Severity.ok

    return [r]


def check_details():
    """
    Parses ntp data in the form:

        remote           refid   st t when poll reach   delay   offset  jitter
    ===========================================================================
    bindcat.fhsu.ed .INIT.       16 u    - 1024    0    0.000    0.000   0.000
    origin.towfowi. .INIT.       16 u    - 1024    0    0.000    0.000   0.000
    time-b.nist.gov .INIT.       16 u    - 1024    0    0.000    0.000   0.000
    services.quadra .INIT.       16 u    - 1024    0    0.000    0.000   0.000
    associd=0 status=c011 leap_alarm, sync_unspec, 1 event, freq_not_set,
    version="ntpd 4.2.6p5@1.2349-o Fri Apr 10 19:04:04 UTC 2015 (1)",
    processor="x86_64", system="Linux/3.14.44-1-amd64-hlinux", leap=11,
    stratum=16, precision=-23, rootdelay=0.000, rootdisp=26.340, refid=INIT,
    reftime=00000000.00000000  Mon, Jan  1 1900  0:00:00.000,
    clock=d94f932a.13f33874  Tue, Jul 14 2015 13:54:50.077, peer=0, tc=3,
    mintc=3, offset=0.000, frequency=0.000, sys_jitter=0.000,
    clk_jitter=0.000, clk_wander=0.000
    """
    results = []
    cmd_result = run_cmd('ntpq -pcrv')

    if cmd_result.exitcode != 0:
        failed = CheckFailure.child(
            dimensions={
                'check': BASE_RESULT.name,
                'error': cmd_result.output,
            }
        )
        failed.value = Severity.fail
        return [failed]

    results.append(check_ntpq_fact(cmd_result, 'stratum'))
    results.append(check_ntpq_fact(cmd_result, 'offset'))

    return results


def check_ntpq_fact(cmd_result, fact_name):
    fact_result = BASE_RESULT.child(fact_name)

    # This regex will pick out the value after a fact. e.g
    #   stratum=16,
    # will match and the value '16' will be stored in 'match.groups()[0]'.
    # If output does not match the regex 'match' will be None.
    fact_regex = re.compile(fact_name+'=(.*?),')

    match = fact_regex.search(cmd_result.output)
    if match is None:
        failed = CheckFailure.child(
            dimensions={
                'check': fact_result.name,
                'error': 'Output does not contain "%s"' % fact_name,
            }
        )
        failed.value = Severity.fail
        return failed
    else:
        fact_level = match.groups()[0]
        fact_result.value = fact_level

    return fact_result


def main():
    """Checks that ntp is running on the server."""
    results = []
    results.extend(check_status())
    results.extend(check_details())

    return results
