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
DOCUMENTATION = '''
---
module: monasca_agent_plugin
short_description: Configure the Monasca agent by running the given monasca-setup detection plugin.
description:
    This module uses the --detection_plugins option of monasca-setup and it is assumed that the full primary configuration of monasca-setup has already
    been done. This primary configuration is done when running the monasca-agent ansible role this module is found in.
    - Monasca project homepage - https://wiki.openstack.org/wiki/Monasca
author: Tim Kuhlman <tim@backgroundprocess.com>
requirements: [ ]
options:
    args:
        required: false
        description:
            - A string containing arguments passed to the detection plugin
    name:
        required: false
        description:
            - The name of the detection plugin to run, this or names is required.
    names:
        required: false
        description:
            - A list of detection plugins to run, this or name is required.
    state:
        required: false
        default: "configured"
        choices: [ configured, absent ]
        description:
            - If the state is configured the detection plugin will be run causing updates if needed. If absent the configuration created by the
              detection_plugins will be removed.
    monasca_setup_path:
        required: false
        default: "/opt/monasca/bin/monasca-setup"
        description:
            - The path to the monasca-setup command.
'''

EXAMPLES = '''
tasks:
    - name: Monasca agent ntp plugin configuration
      monasca_agent_plugin: name="ntp"
    - name: Monasca agent plugin configuration
      monasca_agent_plugin:
        names:
            - ntp
            - mysql
'''

from ansible.module_utils.basic import *


def main():
    module = AnsibleModule(
        argument_spec=dict(
            args=dict(required=False, type='str'),
            name=dict(required=False, type='str'),
            names=dict(required=False, type='list'),
            state=dict(default='configured', choices=['configured', 'absent'], type='str'),
            monasca_setup_path=dict(default='/opt/monasca/bin/monasca-setup', type='str')
        ),
        supports_check_mode=True
    )

    if module.params['names'] is None and module.params['name'] is None:
        module.fail_json(msg='Either name or names paramater must be specified')

    if module.params['names'] is not None:
        names = module.params['names']
    else:
        names = [module.params['name']]

    args = [module.params['monasca_setup_path']]
    if module.check_mode:
        args.append('--dry_run')
    if module.params['state'] == 'absent':
        args.append('-r')
    args.append('-d')
    args.extend(names)
    if module.params['args'] is not None:
        args.extend(['-a', module.params['args']])

    rc, out, err = module.run_command(args, check_rc=True)
    if err.find('Not all plugins found') != -1:
        module.fail_json(msg='Some specified plugins were not found.', stdout=out.rstrip("\r\n"), stderr=err.rstrip("\r\n"))

    if err.find('No changes found') == -1:
        changed = True
    else:
        changed = False

    module.exit_json(changed=changed, cmd=args, stdout=out.rstrip("\r\n"), stderr=err.rstrip("\r\n"), rc=rc)

if __name__ == "__main__":
    main()
