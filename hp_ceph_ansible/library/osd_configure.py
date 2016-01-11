#!/usr/bin/env python
#
# An Ansible module to configure OSD.
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

import os
import re
import time
import uuid


DOCUMENTATION = '''
---
module: osd_configure
version_added: "1.0"
short_description: Configures an OSD on the node based on the input parameters
hostname=osd-host-name
data_disk=osd-data-disk
journal_disk=osd-journal-disk-or-none
fstype=xfs/ext4/btree
cluster_name=ceph
cluster_uuid=uuid
persist_mountpoint=fstab to persist to /etc/fstab
zap_data_disk=True or False
data_disk_poll_attempts=max attempts to verify data disk existence
data_disk_poll_interval=data disk polling interval in seconds
'''


EXAMPLES = '''
- osd_configure:
    hostname: osd-1
    data_disk: /dev/sde
    journal_disk: /dev/sdf
    fstype: xfs
    cluster_name: ceph
    cluster_uuid: 019e66db-b7ab-41c5-94f3-26490805dc90
    persist_mountpoint: fstab
    zap_data_disk: True
    data_disk_poll_attempts: 5
    data_disk_poll_interval: 12
'''


def _run_command(module, command, strip_output=True, ignore_error=False):
    '''
    Run a module command raising an exception if the command failed.
    :param command: the command to execute
    :param strip_output: strip spaces at the beginning and end of output
    :param ignore_error: if True, does not raise exception on error
    :return: command output on success, raise exception on failure
    '''
    rc, out, err = module.run_command(command)
    if not ignore_error and rc != 0:
        raise Exception("'%s' failed with error %s!" % (command, err))
    return (out.strip() if strip_output else out, err)


def create_and_configure_osd(module, hostname, fstype, data_disk, journal_disk,
                             cluster_name, cluster_uuid, persist_mountpoint,
                             zap_data_disk, data_disk_poll_attempts=5,
                             data_disk_poll_interval=12):
    '''
    Execute the steps to create an OSD and configure it.
    :param module: current module instance
    :param hostname: host on which module is being run on
    :param fstype: storage file system type
    :param data_disk: device to be used for object storage
    :param journal_disk: journal device
    :param cluster_name: name of the Ceph cluster
    :param cluster_uuid: uuid of the cluster
    :param persist_mountpoint: persist osd data disk mount
    :param zap_data_disk: zap the data disk if True
    :param data_disk_poll_attempts: no. of attempts to verify data disk is
                                    available
    :param data_disk_poll_interval: data disk polling interval in seconds
    :return: True on success, raises exception on failure.
    '''
    osd_uuid = str(uuid.uuid4())
    zap_disk = '--zap-disk' if zap_data_disk else ''
    journal_disk = journal_disk if journal_disk else ''
    prepare_cmd = ('ceph-disk -v prepare --cluster-uuid %s --cluster %s '
                   '--osd-uuid %s --fs-type %s %s %s %s' % (cluster_uuid,
                                                            cluster_name,
                                                            osd_uuid,
                                                            fstype,
                                                            zap_disk,
                                                            data_disk,
                                                            journal_disk))
    out, err = _run_command(module, prepare_cmd)

    data_disk = re.search('Creating %s fs on (\S+)' % fstype, err)
    if not data_disk:
        raise Exception("Failed to fetch data disk information!")
    else:
        data_disk = data_disk.group(1)

    # This loop is an attempt to reduce the occurrence of STOR-1186, where the
    # disk prepare successfully returns, however disk activate is not able to
    # see the data disk.
    attempt = 0
    while attempt < int(data_disk_poll_attempts):
        if os.path.exists(data_disk):
            break
        else:
            time.sleep(float(data_disk_poll_interval))
            attempt += 1

    # run activate in verbose mode to capture the osd number
    bootstrap_keyring = (" --activate-key /var/lib/ceph/bootstrap-osd/"
                         "%s.keyring" % cluster_name)
    activate_cmd = 'ceph-disk -v activate %s --mark-init=none %s' % (
        bootstrap_keyring, data_disk)
    out, err = _run_command(module, activate_cmd)
    # strange that the verbose logs end up in the error and not output stream!
    osd_number = re.search('ceph-disk:OSD id is (\d+)', err).group(1)

    cmd_regex = '([a-zA-Z0-9\/]+)mount -o (\S+) -- (\S+) (\S+)'
    mount_args = re.search('Running command: %s' % cmd_regex, err)
    if not mount_args:
        raise Exception("Failed to fetch mount options!")
    else:
        mount_args = mount_args.groups()

    # make the mount persistent, so that service comes up after system reboot.
    if persist_mountpoint == 'fstab':
        fstab_mount = "\n%s %s %s defaults,%s 0 2\n" % (mount_args[2],
                                                        mount_args[3],
                                                        fstype,
                                                        mount_args[1])
        with open("/etc/fstab", "a") as fstab_fp:
            fstab_fp.write(fstab_mount)

    crushadd_cmd = 'ceph --cluster %s osd crush add osd.%s 1.0 host=%s' % (
        cluster_name, osd_number, hostname)
    _ = _run_command(module, crushadd_cmd)

    return {'osd_number': osd_number}


def check_osd_disk_status(data_disk):
    '''
    Check whether data disk is being used by OSD or not.
    :param data_disk: device to be used for object storage
    :return: 0 if the disk is being used by osd else 1.
    '''
    command = "ceph-disk list | grep 'ceph data' | grep %s" % data_disk
    rc = os.system(command)
    return rc


def main():
    module = AnsibleModule(
        argument_spec=dict(
            hostname=dict(required=True),
            data_disk=dict(required=True),
            journal_disk=dict(required=True),
            fstype=dict(required=True),
            cluster_name=dict(required=True),
            cluster_uuid=dict(required=True),
            persist_mountpoint=dict(required=True),
            zap_data_disk=dict(required=True),
            data_disk_poll_attempts=dict(required=True),
            data_disk_poll_interval=dict(required=True)
        ),
        supports_check_mode=False
    )

    try:
        params = module.params
        retval = check_osd_disk_status(params['data_disk'])
        if retval == 0:
            module.exit_json(**dict(changed=False, result=retval))
        else:
            retval = create_and_configure_osd(
                module, params['hostname'], params['fstype'],
                params['data_disk'], params['journal_disk'],
                params['cluster_name'], params['cluster_uuid'],
                params['persist_mountpoint'], params['zap_data_disk'],
                params['data_disk_poll_attempts'],
                params['data_disk_poll_interval'])
    except Exception, e:
        module.fail_json(msg='Exception: %s' % e)
    else:
        module.exit_json(**dict(changed=True, result=retval))


# import module snippets
from ansible.module_utils.basic import *
if __name__ == '__main__':
    main()
