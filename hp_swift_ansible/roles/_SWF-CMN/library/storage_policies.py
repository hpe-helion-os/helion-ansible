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
import json
import shlex
import sys


def get_storage_policies(ringspecs, region_name):
    storage_policies = []
    for region_rings in ringspecs:
        if region_name == region_rings.get('region_name'):
            for ring in region_rings.get('rings'):
                if ring.get('name').startswith('object-'):
                    index = ring.get('name')[7:]
                    name = ring.get('display_name')
                    policy = {'policy': {'index': index, 'name': name}}
                    if ring.get('default', False):
                        policy = {'policy': {'index': index, 'name': name,
                                             'default': 'yes'}}
                    else:
                        policy = {'policy': {'index': index, 'name': name}}
                    storage_policies.append(policy)
    return storage_policies


def main():
    ringspecs = ''
    region_name = ''
    try:
        args_file = sys.argv[1]
        args_data = file(args_file).read()
        arguments = shlex.split(args_data)
    except (IndexError, IOError):
        arguments = sys.argv  # Running interactively
    for arg in arguments:
        if "=" in arg:
            (key, value) = arg.split('=')
            if key == 'ring-specifications':
                ringspecs = value
            elif key == 'region-name':
                region_name = value

    ringspecs = ringspecs.replace("'", '"')          # fix single quotes
    ringspecs = ringspecs.replace('True', 'true')    # fix boolean
    ringspecs = ringspecs.replace('False', 'false')  # fix boolean
    storage_policies = get_storage_policies(json.loads(ringspecs),
                                            region_name)
    ret = {}
    ret['failed'] = False
    ret['rc'] = 0
    ret['ansible_facts'] = {'storage_policies': storage_policies}
    print(json.dumps(ret))


if __name__ == '__main__':
    main()
