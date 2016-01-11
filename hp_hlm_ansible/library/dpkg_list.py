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
module: dpkg_list
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
- dpkg_list:
'''

import datetime
import json


def get_installed_pkgs():

    cmd = "dpkg-query -W -f='${Package} ${Version}\n'"
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
    output, err = p.communicate()
    output = output.splitlines()
    installed_pkgs = {}

    for line in output:
      (pkg, version) = line.split()
      installed_pkgs[pkg] = { "Version": version }

    return installed_pkgs


def main():

    module = AnsibleModule(argument_spec = dict())
    installed_pkgs = get_installed_pkgs()
    changed = False
    ansible_facts_dict = dict(installed_pkgs=installed_pkgs)
    result = dict(changed=changed, ansible_facts=ansible_facts_dict)
    module.exit_json(**result)

from ansible.module_utils.basic import *
main()
