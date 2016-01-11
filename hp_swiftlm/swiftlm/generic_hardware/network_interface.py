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

try:
    import commands
except ImportError:
    import subprocess as commands
import string


from swiftlm.utils.utility import get_swift_bind_ips, UtilityExeception
from swiftlm.utils.utility import ip_to_interface
from swiftlm.utils.metricdata import MetricData
from swiftlm.utils.values import Severity

BASE_RESULT = MetricData(
    name=__name__,
    messages={
        'fail': 'Could not discover a valid interface name'
    }
)


def str_to_num(val):
    # if val is a number then convert it to a number literal
    try:
        return int(val)
    except ValueError:
        try:
            return float(val)
        except:
            return val


def get_interface_names(ip_to_interface_map, bind_ip_list):
    """
    Get set of unique interface names.

    :return: list of interface names
    """
    interface_name_list = set()

    for ip_address in bind_ip_list:
        interface_name_list.add(ip_to_interface_map[ip_address])

    return interface_name_list


def get_interface_speed(interface_name):
    """
    Get the NIC speed of the specified interface

    :param interface_name: eth1
    :return: Response
    """
    c = BASE_RESULT.child(dimensions={'interface': interface_name})

    command = "ethtool " + interface_name
    interface_data = commands.getoutput(command)
    speed = ''

    # Filter lines here. We only want the speed.
    lines = interface_data.split('\n')
    for line in lines:
        if 'Speed' in line:
            _, speed = line.split(':')

    # Only leave the digits
    speed = ''.join(c for c in speed if c in string.digits)
    if speed:
        c.value = str_to_num(speed)
    else:
        c.value = 0
    return c


def get_interface_data(interface_name):
    """Turn the raw data line for an interface into a dict of values."""
    command = 'cat /proc/net/dev | grep ' + interface_name + ':'
    interface_data = commands.getoutput(command)

    data = [str_to_num(val) for val in interface_data.split()]

    # Values are the index of the data after splitting command
    # output on whitespace.
    d = {
        'interface': interface_name,
        'rx': {
            'bytes': 1,
            'packets': 2,
            'errs': 3,
            'drop': 4,
            'fifo': 5,
            'frame': 6,
            'compressed': 7,
            'multicast': 8,
        },
        'tx': {
            'bytes': 9,
            'packets': 10,
            'errs': 11,
            'drop': 12,
            'fifo': 13,
            'colls': 14,
            'carrier': 15,
            'compressed': 16,
        },
    }

    for x in ['rx', 'tx']:
        for field_name, field_index in d[x].items():
            d[x][field_name] = data[field_index]

    return d


def run_network_interface_check():
    results = []
    ip_to_interface_map = ip_to_interface()
    bind_ip_list = get_swift_bind_ips()

    try:
        interface_names = get_interface_names(ip_to_interface_map,
                                              bind_ip_list)
    except UtilityExeception:
        c = BASE_RESULT.child()
        c.value = Severity.fail
        return [c]

    for interface_name in interface_names:
        results.append(get_interface_speed(interface_name))
        data = get_interface_data(interface_name)
        for x in ['rx', 'tx']:
            for stat_name, stat_count in data[x].items():
                c = BASE_RESULT.child(
                    name=x+'.'+stat_name,
                    dimensions={
                        'interface': interface_name,
                    }
                )
                c.value = stat_count
                results.append(c)

    return results


def main():
    """Check NIC speed and stats for each interface."""
    return run_network_interface_check()


if __name__ == '__main__':
    main()
