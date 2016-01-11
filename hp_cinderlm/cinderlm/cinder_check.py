#!/usr/bin/env python
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

from __future__ import print_function

import argparse
import cinderclient
from cinderclient.client import Client as CinderClient
from datetime import datetime
from novaclient.client import Client as NovaClient
import os
import sys
import time

argparser = argparse.ArgumentParser(usage="Cinder Check Utility")


def create_arguments(parser):
    """Sets up the CLI and config-file options"""
    client_args = parser.add_argument_group('client test arguments')

    client_args.add_argument('-t', '--tenantname',
                             default='admin',
                             help='Tenant Name')
    client_args.add_argument('-u', '--username',
                             default='admin',
                             help='Username')
    client_args.add_argument('-p', '--password',
                             default='admin',
                             help='Password')
    client_args.add_argument(
        '--auth_url',
        default='http://PADAWANBASE-CCP-T01-VIP-KEY-API-NETCLM:5000/v2.0',
        help='auth_url')
    client_args.add_argument('-V', '--api-version', dest="api_version",
                             default="1", type=str,
                             help="Run check using version specified")
    client_args.add_argument('-N', '--nova-api-version',
                             dest="nova_api_version",
                             default="2", type=str,
                             help="Run check using version specified")
    client_args.add_argument('-v', '--verbose', dest="verbose",
                             default=False, action="store_true",
                             help="Run check in verbose mode")
    client_args.add_argument('-a', '--check-api', dest="check_api",
                             default=False, action="store_true",
                             help="Run Cinder API monitoring check")
    client_args.add_argument('-f', '--full', dest="full",
                             default=False, action="store_true",
                             help="Run a more detailed check")
    client_args.add_argument('-i', '--image',
                             default=None,
                             help="Specify the image to boot an instance.")
    client_args.add_argument('-l', '--flavor',
                             default=None,
                             help="Specify the flavor to boot an instance.")


class CinderCheckClient(object):
    def __init__(self, options):
        self.options = options
        self.creds = {'username': options.username,
                      'tenant_name': options.tenantname,
                      'password': options.password,
                      'auth_url': options.auth_url}

    def get_nova_client(self):
        return NovaClient(self.options.nova_api_version,
                          username=self.creds['username'],
                          api_key=self.creds['password'],
                          project_id=self.creds['tenant_name'],
                          auth_url=self.creds['auth_url'],
                          endpoint_type='publicURL')

    def get_api_client(self):
        return CinderClient(self.options.api_version,
                            username=self.creds['username'],
                            api_key=self.creds['password'],
                            project_id=self.creds['tenant_name'],
                            auth_url=self.creds['auth_url'],
                            endpoint_type='publicURL')

    def print(self, msg):
        print("%s: %s" % (datetime.utcnow().isoformat(), msg))

    def run_tests(self):
        """Main part of program. Runs tests specified on command line."""

        if self.options.check_api:
            self.api_tests()

    def api_tests(self):
        """Run Cinder API  tests"""
        self.print("Cinder API tests")
        self.client = self.get_api_client()
        self.novaclient = self.get_nova_client()
        if self.options.api_version == '1':
            self.api_tests_v1()
        elif self.options.api_version == '2':
            self.api_tests_v2()

    def api_tests_v1(self):
        self.print("Test: API V1")
        self.api_tests_common('1')

    def api_tests_v2(self):
        self.print("Test: API V2")
        self.api_tests_common('2')

    def _name_for_vers(self, vol, vers):
        return (vol.display_name if vers == '1' else vol.name)

    def _wait_for_instance_status(self, instance_id, status_list, timeout=60):
        """Loop and wait for instance to reach a specified state."""
        loop_counter = int(timeout) / 2
        while loop_counter > 0:
            loop_counter -= 1
            try:
                instance = self.novaclient.servers.get(instance_id)
                if instance.status not in status_list:
                    time.sleep(2)
                else:
                    break
            except Exception as e:
                raise Exception("api:INSTANCEGET #1 Failed : %s" % (e))
        else:
            raise Exception("api:INSTANCEGET #1 timed out")
        self.print("Instance: %s went to state %s." %
                   (instance_id, instance.status))
        return instance.status

    def _wait_for_status(self, vol_id, status_list, timeout=60):
        """Loop and wait for volume to reach a specified state."""
        loop_counter = int(timeout) / 2
        while loop_counter > 0:
            loop_counter -= 1
            try:
                vol = self.client.volumes.get(vol_id)
                if vol.status not in status_list:
                    time.sleep(2)
                else:
                    break
            except Exception as e:
                raise Exception("api:VOLGET #1 Failed : %s" % (e))
        else:
            raise Exception("api:VOLGET #1 timed out")
        self.print("Volume: %s went to state %s." % (vol_id, vol.status))
        return vol.status

    def _wait_for_backup_status(self, bck_id, status_list, timeout=60):
        """Loop and wait for volume backup to reach a specified state."""
        loop_counter = int(timeout) / 2
        while loop_counter > 0:
            loop_counter -= 1
            try:
                bck = self.client.backups.get(bck_id)
                if bck.status not in status_list:
                    time.sleep(2)
                else:
                    break
            except Exception as e:
                raise Exception("api:BCKGET #1 Failed : %s" % (e))
        else:
            raise Exception("api:BCKGET #1 timed out")
        self.print("Backup: %s went to state %s." % (bck_id, bck.status))
        return bck.status

    def _api_tests_undo(self, vol_id, bck_id=None, instance_id=None):
        """Perform requested tidyup; on best-effort basis"""
        if instance_id is not None:
            try:
                self.novaclient.servers.get(instance_id)
                self.novaclient.servers.delete(instance_id)
            except cinderclient.exceptions.NotFound:
                pass
            except Exception as e:
                self.print("Failed to delete test instance: %s" % e)
        if vol_id is not None:
            try:
                # Give the volume one more chance to get into a deleteable
                # state.
                self._wait_for_status(vol_id, ['available', 'error'])
                vol = self.client.volumes.get(vol_id)
                self.client.volumes.delete(vol)
            except cinderclient.exceptions.NotFound:
                pass
            except Exception as e:
                self.print("Failed to delete test volume: %s" % e)
        if bck_id is not None:
            try:
                bckup = self.client.backups.get(bck_id)
                self.client.backups.delete(bckup)
            except cinderclient.exceptions.NotFound:
                pass
            except Exception as e:
                self.print("Failed to delete test backup: %s" % e)

    def api_tests_attach(self, vol_id):
        self.print("Test: API attach volume")
        #
        # There's nothing much we can do, except use the first image and
        # flavor.
        image = self.novaclient.images.list()[0]
        flavor = self.novaclient.flavors.list()[0]
        # But CLI can override:
        if self.options.image is not None:
            image = self.options.image
            self.print("Booting from the image %s" % image)
        if self.options.flavor is not None:
            flavor = self.options.flavor
            self.print("Booting with the flavor %s" % flavor)
        instance = self.novaclient.servers.create(name="__chkvm__",
                                                  image=image,
                                                  flavor=flavor)
        vm_status = self._wait_for_instance_status(instance.id,
                                                   ['ACTIVE', 'ERROR'])
        if vm_status != 'ACTIVE':
            self._api_tests_undo(None, None, instance.id)
            raise Exception("api:Instance final status not 'ACTIVE'")

        try:
            self.novaclient.volumes.create_server_volume(instance.id,
                                                         vol_id, None)
            self._wait_for_status(vol_id, ['in-use', 'error'])
            self.novaclient.volumes.delete_server_volume(instance.id,
                                                         vol_id)
            self._wait_for_status(vol_id, ['available', 'error'])
        except Exception as e:
            self._api_tests_undo(vol_id, None, instance.id)
            raise Exception("api:Instance exception in attach/detach - %s" % e)

        self.novaclient.servers.delete(instance)

    def api_tests_backup(self, vol_id, do_restore=True):
        """Cinder backup API tests: list, create, restore, delete"""
        self.print("Test: API Backup list")
        try:
            test_vol_backup_list = self.client.backups.list()
        except Exception as e:
            raise Exception("api:BACKUP list Failed : %s" % (e))
        if self.options.verbose:
            for bck in test_vol_backup_list:
                self.print("Backup: %s; volume: %s backup status: %s" %
                           (bck.id, bck.volume_id, bck.status))

        self.print("Test: API Backup create")
        try:
            test_vol_backup = self.client.backups.create(
                vol_id, name='__chkvolbck__')
        except Exception as e:
            raise Exception("api:BACKUP create Failed : %s" % (e))

        # volume status will be 'backing-up' for a while
        # wait for the backup to be done
        vol_status = self._wait_for_status(vol_id,
                                           ['available', 'error'])
        if vol_status != 'available':
            self._api_tests_undo(None, test_vol_backup.id)
            raise Exception("api:BACKUP final status not 'available'")

        # self.print("Test: API Backup in Swift")
        # TODO: for added bonus - check the swift container for files

        if do_restore:
            self.print("Test: API Backup restore")
            try:
                restore = self.client.restores.restore(test_vol_backup.id)
                restore_vol_id = restore.volume_id
            except Exception as e:
                self._api_tests_undo(None, test_vol_backup.id)
                raise Exception("api:BACKUP restore Failed : %s" % (e))

            vol_status = self._wait_for_status(restore_vol_id,
                                               ['available', 'error'])
            if vol_status != 'available':
                self._api_tests_undo(restore_vol_id, test_vol_backup.id)
                raise Exception("api:RESTORE final vol status not 'available'")

            # backup status will be 'restoring' for a while
            bck_status = self._wait_for_backup_status(test_vol_backup.id,
                                                      ['available', 'error'])
            if bck_status != 'available':
                self._api_tests_undo(restore_vol_id, test_vol_backup.id)
                raise Exception("api:RESTORE final bck status not 'available'")

            # Now delete the restored volume
            self._api_tests_undo(restore_vol_id)

        self.print("Test: API Backup delete")
        try:
            self.client.backups.delete(test_vol_backup)
        except Exception as e:
            raise Exception("api:BACKUP delete Failed : %s" % (e))
            # TODO: check the backup is actually gone
            #       the backup status goes to 'deleting'

    def api_tests_common(self, vers):
        """Basic API tests: list, create, delete"""
        self.print("Test: API List")
        try:
            test_vol_list = self.client.volumes.list()
        except cinderclient.exceptions.NotFound as c:
            print("Error: Check your openstack auth url", file=sys.stderr)
            raise Exception("api:VOLLIST Failed : %s" % (c))
        except Exception as e:
            raise Exception("api:VOLLIST Failed : %s" % (e))
        if self.options.verbose:
            for vol in test_vol_list:
                self.print("Volume: %s; name: %s status: %s" %
                           (vol.id,
                            (self._name_for_vers(vol, vers)),
                            vol.status))

        self.print("Test: API Create - 1GiB volume")
        try:
            if vers == '1':
                test_vol_create = self.client.volumes.create(
                    1, display_name='__chkvol__')
            else:
                test_vol_create = self.client.volumes.create(
                    1, name='__chkvol__')
        except Exception as e:
            raise Exception("api:VOLCREATE Failed : %s" % (e))
        if self.options.verbose:
            self.print("Volume: %s; name: %s status: %s" %
                       (test_vol_create.id,
                        self._name_for_vers(test_vol_create, vers),
                        test_vol_create.status))

        # Loop and wait for volume to go active
        vol_status = self._wait_for_status(test_vol_create.id,
                                           ['available', 'error'])
        if vol_status != 'available':
            self._api_tests_undo(test_vol_create.id)
            raise Exception("api:VOLCREATE final status is not 'available'")

        if self.options.full:
            try:
                self.api_tests_backup(test_vol_create.id)
                self.api_tests_attach(test_vol_create.id)
            except Exception:
                self._api_tests_undo(test_vol_create.id)
                raise

        self.print("Test: API Delete")
        try:
            self.client.volumes.delete(test_vol_create)
        except cinderclient.exceptions.NotFound as c:
            raise Exception("api:VOLDELETE Failed : %s" % (c))
        except Exception as e:
            self.print(type(e))
            raise Exception("api:VOLDELETE Failed : %s" % (e))
        # TODO: check the volume is actually gone
        if self.options.verbose:
            try:
                tmpvol = self.client.volumes.get(test_vol_create.id)
                self.print("Volume: %s; name: %s status: %s" %
                           (tmpvol.id,
                            self._name_for_vers(tmpvol, vers),
                            tmpvol.status))
            except cinderclient.exceptions.NotFound as c:
                self.print("Volume: %s; name: %s removed...." %
                           (test_vol_create.id,
                            self._name_for_vers(test_vol_create, vers)))
            except Exception as e:
                raise Exception("api:VOLGET #2 Failed : %s" % (e))


def main():
    if not os.geteuid() == 0:
        print("You must be 'root' user to run this script", file=sys.stderr)
        sys.exit(1)

    create_arguments(argparser)
    args = argparser.parse_args()

    test = CinderCheckClient(args)
    test.run_tests()
    print("Test completed.")

if __name__ == '__main__':
    main()
