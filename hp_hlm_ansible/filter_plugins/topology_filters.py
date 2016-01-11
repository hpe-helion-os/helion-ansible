#!/usr/bin/python
#
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
"""
The topology is expressed via a group variable that looks like this:

  topology:
    control_planes:
      - name: ccp
        services:
          - name: keystone
            components:
              - name: keystone-api
                hosts:
                  - host1
                  - host2
                  - host3
          - name: foundation
            components:
              - name: mysql
                hosts:
                  - host1
                  - host2
                  - host3
      - name: rcp01
        services:
          - name: nova
            components:
              - name: nova-api
                hosts:
                  - host4
                  - host5
                  - host6
              - name: nova-scheduler
                hosts:
                  - host4
                  - host5
                  - host6


The following filters are provided for correct navigation of that structure:

topology_filter_control_planes: yields a set of (control-plane) named tuples
topology_filter_services: yields a set of (control-plane, service) named tuples
topology_filter_components: yields a set of (control-plane, service, service-element) named tuples
topology_filter_hosts: yields a set of (control-plane, service, service-element, host) named tuples
"""

import collections

control_plane = ['control_plane']
service = control_plane + ['service']
component = service + ['component']
host = component + ['host']


def make_dict(layout):
    def f(*path):
        return dict(zip(layout, path))
    return f


def descend(dictionary, path, remaining, tuple):
    """ Descend one level into a dictionary. """

    if not remaining:
        return [tuple(*path)]

    accessor, collect = remaining[0]
    if callable(collect):
        function = collect
    else:
        function = lambda item: item[collect]
    results = []
    for item in dictionary[accessor]:
        results.extend(descend(item, path + [function(item)], remaining[1:], tuple))
    return results


def topology_filter_control_planes(topology):
    return descend(topology, [], [('control_planes', 'name')], make_dict(control_plane))


def topology_filter_services(topology):
    return descend(topology, [], [('control_planes', 'name'),
                                  ('services', 'name')], make_dict(service))


def topology_filter_components(topology):
    return descend(topology, [], [('control_planes', 'name'),
                                  ('services', 'name'),
                                  ('components', 'name')], make_dict(component))


def topology_filter_hosts(topology):
    return descend(topology, [], [('control_planes', 'name'),
                                  ('services', 'name'),
                                  ('components', 'name'),
                                  ('hosts', str)], make_dict(host))


class FilterModule(object):

    def filters(self):
        return {
            'dict_zip_maker': make_dict,
            'descend': descend,
            'topology_filter_control_planes': topology_filter_control_planes,
            'topology_filter_services': topology_filter_services,
            'topology_filter_components': topology_filter_components,
            'topology_filter_hosts': topology_filter_hosts,
            }


if __name__ == '__main__':
    import yaml

    test = """
---
  topology:
    control_planes:
      - name: ccp
        services:
          - name: keystone
            components:
              - name: keystone-api
                hosts:
                  - host1
                  - host2
                  - host3
          - name: foundation
            components:
              - name: mysql
                hosts:
                  - host1
                  - host2
                  - host3
      - name: rcp01
        services:
          - name: nova
            components:
              - name: nova-api
                hosts:
                  - host4
                  - host5
                  - host6
              - name: nova-scheduler
                hosts:
                  - host4
                  - host5
                  - host6
"""
    topology = yaml.safe_load(test)['topology']

    assert topology_filter_control_planes(topology) == [
        {'control_plane':'ccp'},
        {'control_plane': 'rcp01'}]
    assert topology_filter_services(topology) == [
        {'control_plane': 'ccp', 'service': 'keystone'},
        {'control_plane': 'ccp', 'service': 'foundation'},
        {'control_plane': 'rcp01', 'service': 'nova'}]
    assert topology_filter_components(topology) == [
        {'control_plane': 'ccp', 'service': 'keystone', 'component': 'keystone-api'},
        {'control_plane': 'ccp', 'service': 'foundation', 'component': 'mysql'},
        {'control_plane': 'rcp01', 'service': 'nova', 'component': 'nova-api'},
        {'control_plane': 'rcp01', 'service': 'nova', 'component': 'nova-scheduler'}]
    assert topology_filter_hosts(topology) == [
        {'control_plane': 'ccp', 'service': 'keystone', 'component': 'keystone-api', 'host': 'host1'},
        {'control_plane': 'ccp', 'service': 'keystone', 'component': 'keystone-api', 'host': 'host2'},
        {'control_plane': 'ccp', 'service': 'keystone', 'component': 'keystone-api', 'host': 'host3'},
        {'control_plane': 'ccp', 'service': 'foundation', 'component': 'mysql', 'host': 'host1'},
        {'control_plane': 'ccp', 'service': 'foundation', 'component': 'mysql', 'host': 'host2'},
        {'control_plane': 'ccp', 'service': 'foundation', 'component': 'mysql', 'host': 'host3'},
        {'control_plane': 'rcp01', 'service': 'nova', 'component': 'nova-api', 'host': 'host4'},
        {'control_plane': 'rcp01', 'service': 'nova', 'component': 'nova-api', 'host': 'host5'},
        {'control_plane': 'rcp01', 'service': 'nova', 'component': 'nova-api', 'host': 'host6'},
        {'control_plane': 'rcp01', 'service': 'nova', 'component': 'nova-scheduler', 'host': 'host4'},
        {'control_plane': 'rcp01', 'service': 'nova', 'component': 'nova-scheduler', 'host': 'host5'},
        {'control_plane': 'rcp01', 'service': 'nova', 'component': 'nova-scheduler', 'host': 'host6'}]
