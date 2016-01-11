#!/usr/bin/env python
#
# An Ansible module to query apt for the list of packages
# available for update.
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

DOCUMENTATION = '''
---
module: apt-upgrade-list
author: Tom Howley
short_description: Queries apt for list of packages available for upgrade.
description:
    - Updates the local apt cache.
    - Queries the apt cache to get the list of packages avalailable for upgrade.
      That list of packages is written to the fact: list_pkg_upgrades
options:
    Currently no options.
'''

EXAMPLES = '''
- apt-upgrade-list:
'''

import datetime
import json


def get_list_pkg_upgrades():

    cmd = "sudo apt-get upgrade -u --assume-no"
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
    output, err = p.communicate()
    output = output.splitlines()
    list_pkg_upgrades = []

    UPGRADE_STR="The following packages will be upgraded:"
    idx_start_match = next((i for i, v in enumerate(output) if v == UPGRADE_STR), -1)
    if idx_start_match == -1:
      return list_pkg_upgrades

    idx_end_match = next((i for i, v in enumerate(output) if re.match('^\d*\s*upgraded.*not upgraded.$',v)), -1)
    if idx_end_match == -1:
      return list_pkg_upgrades

    for line in output[idx_start_match+1:idx_end_match]:
        list_pkg_upgrades.extend(line.split())

    for pkg in list_pkg_upgrades:
        print "Pkg: %s" % pkg

    return list_pkg_upgrades

def main():

    module = AnsibleModule(argument_spec = dict())
    list_pkg_upgrades = get_list_pkg_upgrades()
    changed = (len(list_pkg_upgrades) > 0)
    ansible_facts_dict = dict(list_pkg_upgrades=list_pkg_upgrades)
    result = dict(changed=changed, ansible_facts=ansible_facts_dict)
    module.exit_json(**result)

from ansible.module_utils.basic import *
main()
