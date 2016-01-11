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
module: get_wwid
short_description: Retrieves the wwids of specified device or devices for a
 given HLM Host data
description:
     - The module accepts either a device parameter or a HLM Host data JSON
options:
  device:
    description:
      - Full path of the device E.g., '/dev/sda' to retrieve wwid
    required: true (One of the two options)
    default: null
  hlm_host_info:
    description:
      - HLM host info in JSON form. This is usually found in host_vars as host.
      - Use to_json filter to convert to JSON string
    required: true (One of the two options)
    default: null
author:
'''

EXAMPLES = '''
# Example from Ansible Playbooks.
- get_wwid: device='/dev/sda'

# Returns dict with key 'wwid' and wwid of the device as value.

# Using HLM host info
- get_wwid: hlm_host_info='{{ host | to_json }}'

# Returns dict with key 'wwid' and device-wwid key-value pairs dict as value.

# NOTE: Please use single quotes for host info converted to JSON as
# double quotes will cause argument errors
'''


def main():
    module = AnsibleModule(
        argument_spec=dict(
            device=dict(),
            hlm_host_info=dict()
        )
    )
    device = module.params['device']
    hlm_host_info = json.loads(module.params['hlm_host_info'])

    if not device and not hlm_host_info:
        module.fail_json(rc=256, msg="No device or HLM host info specified")

    hlm_disk_models = hlm_host_info['my_disk_models'] \
        if 'my_disk_models' in hlm_host_info else dict()
    hlm_device_groups = hlm_host_info['my_device_groups'] \
        if 'my_device_groups' in hlm_host_info else dict()

    if hlm_host_info:
        rc_cumulative = 0
        err_cumulative = ""
        wwids = dict()

        if hlm_disk_models:
            for volume_group in hlm_disk_models['volume_groups']:
                for physical_volume in volume_group['physical_volumes']:
                    physical_volume = physical_volume.replace('_root', '')
                    wwid_command = '/lib/udev/scsi_id -g %s' % physical_volume
                    rc, out, err = module.run_command(wwid_command)
                    rc_cumulative += rc
                    err_cumulative += err
                    wwids[physical_volume] = '' if out is None \
                        else out.rstrip("\r\n")

        if hlm_device_groups:
            for device_group in hlm_device_groups:
                for entry in hlm_device_groups[device_group]:
                    for dev in entry['devices']:
                        wwid_command = '/lib/udev/scsi_id -g %s' % dev['name']
                        rc, out, err = module.run_command(wwid_command)
                        rc_cumulative += rc
                        err_cumulative += err
                        wwids[dev['name']] = '' if out is None \
                            else out.rstrip("\r\n")

        module.exit_json(
            hostname=hlm_host_info['vars']['my_network_name'],
            wwid=wwids,
            rc=rc_cumulative,
            stderr=err_cumulative,
            changed=True
        )

    if device:
        wwid_command = '/lib/udev/scsi_id -g %s' % device
        rc, out, err = module.run_command(wwid_command)

        module.exit_json(
            disk=wwid_command,
            wwid='' if out is None else out.rstrip("\r\n"),
            stderr='' if err is None else err.rstrip("\r\n"),
            rc=rc,
            changed=True
        )


from ansible.module_utils.basic import *    # NOQA

main()
