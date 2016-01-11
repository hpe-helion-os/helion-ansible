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


import sys
import os.path
from yaml import safe_load, safe_dump

from swiftlm.rings.ring_model import DeviceInfo, Consumes, SwiftModelException
from swiftlm.utils.drivedata import DISK_MOUNT, LVM_MOUNT


class InputModel(object):
    """
    Access the drive data in the input model

    The input model looks like:

        global:
            all_servers:
              -  name: server1
                 disk_model:
                    device_groups:
                      -  consumer:
                            name: swift
                            attrs:
                                rings:
                                - object-0           # Allows raw name or
                                - name: object-0     # name as key (future
                                                     # extension
                            devices:
                              - /dev/sda
                              - /dev/sdb
                              - .etc...
                      -  consumer:
                            name: <something-else>   # We ignore
                            attrs:
                            devices:



    The main output is from iter_devices(). This returns a list of all swift
    drives with following items:

        region_name
            the Keystone region name, i.e., which system the device
            refers to. (e.g., region1)
        region_id
            The swift region id (e.g., 1)
        zone_id
            The swift zone id (e.g., 2)
        server_name
            The name of the server
        server_ip
            The IP address of the server
        server_bind_port:
            The port number to use (e.g., 6000)
        replication_ip
            The IP address of the drive on the replication network.
            Or None if no replication network
        replication_bind_port
            Port to use if a replication network is used
        swift_drive_name
            Name used in ring files (e.g. swdisk1)
        device_name
            Dhe name of the device (e.g., /dev/sdb)
        ring_name
            The ringname (e.g., object-1)
        group_type
            'device' or 'volume'
        presence:
            Currently always 'present' (reserved for future use -- would allow
            controlled removal of drives or server from an input model)
    """

    def __init__(self, fd=None, config=None, hosts_fd=None, consumes=None):
        self.config = {}
        self.servers = []
        self.host_ip_map = {}
        if fd:
            self._read_config(fd)
        if config:
            self.config = config
            self.servers = self.config.get('global').get('all_servers')
        self.devices = []
        if hosts_fd:
            self._load_host_ip_mapping(hosts_fd)
        if consumes:
            self.consumes = Consumes(consumes)

    def iter_devices(self):
        for device_info in self._iter_device_groups():
            yield device_info
        for device_info in self._iter_volume_groups():
            yield device_info

    def _iter_device_groups(self):
        for server in self.config.get('global').get('all_servers'):
            server_name = server.get('name')
            disk_model = server.get('disk_model')
            region_name = server.get('region')
            rack_id = server.get('rack')
            device_index = 0
            for device_group in disk_model.get('device_groups', []):
                consumer = device_group.get('consumer')
                if consumer and consumer.get('name', 'other') == 'swift':
                    attrs = consumer.get('attrs')
                    if not attrs:
                        raise SwiftModelException('The attrs item is'
                                                  ' missing from device-groups'
                                                  ' %s in disk model %s' %
                                                  (device_group.get('name'),
                                                   disk_model.get('name')))
                    devices = device_group.get('devices')
                    if attrs.get('rings', None) is None:
                        raise SwiftModelException('The rings item is'
                                                  ' missing from device-groups'
                                                  ' %s in disk model %s' %
                                                  (device_group.get('name'),
                                                   disk_model.get('name')))
                    for device in devices:
                        for ring in attrs.get('rings'):
                            if isinstance(ring, str):
                                ring_name = ring
                            else:
                                ring_name = ring.get('name')
                            server_ip, bind_port = self._get_server_bind(
                                ring_name, server_name)
                            if not server_ip:
                                # When a swift service (example swift-account)
                                # is configured in the input model to run a
                                # node, we expect the node to be in the
                                # "consumes" variable. e.g., consumes_SWF_ACC
                                # should have this node in its list. Since we
                                # failed to get the network name/port, it means
                                # that it is not.
                                # In model terms, we have a disk model that
                                # calls out that a device hosts a ring (e.g.
                                # account), but the node is not configured
                                # to run SWF-ACC.
                                # TODO: this may be worth warning
                                break

                            swift_drive_name = DISK_MOUNT + str(device_index)
                            device_info = DeviceInfo({
                                'region_name': region_name,
                                'rack_id': rack_id,
                                'region_id': 1,      # later, the rack id may
                                'zone_id': 1,        # change these defaults
                                'server_name': Consumes.basename(server_name),
                                'server_ip': server_ip,
                                'server_bind_port': bind_port,
                                'replication_ip': server_ip,
                                'replication_bind_port': bind_port,
                                'swift_drive_name': swift_drive_name,
                                'device_name': device.get('name'),
                                'ring_name': ring_name,
                                'group_type': 'device',
                                'block_devices': {'percent': '100%',
                                                  'physicals':
                                                      [device.get('name')]},
                                'presence': 'present'})

                            yield device_info
                        device_index += 1

    def _iter_volume_groups(self):
        for server in self.config.get('global').get('all_servers'):
            server_name = server.get('name')
            disk_model = server.get('disk_model')
            region_name = server.get('region')
            rack_id = server.get('rack')
            lv_index = 0
            for volume_group in disk_model.get('volume_groups', []):
                vg_name = volume_group.get('name')
                physical_volumes = volume_group.get('physical_volumes')
                for logical_volume in volume_group.get('logical_volumes', []):
                    lv_name = logical_volume.get('name')
                    percent = logical_volume.get('size')
                    consumer = logical_volume.get('consumer')
                    if consumer and consumer.get('name', 'other') == 'swift':
                        attrs = consumer.get('attrs')
                        if not attrs:
                            raise SwiftModelException('The attrs item is'
                                                      ' missing from '
                                                      ' logical volume'
                                                      ' %s in disk model %s' %
                                                      (logical_volume.get(
                                                          'name'),
                                                       disk_model.get('name')))
                        if attrs.get('rings', None) is None:
                            raise SwiftModelException('The rings item is'
                                                      ' missing from logical'
                                                      ' volume'
                                                      ' %s in disk model %s' %
                                                      (logical_volume.get(
                                                          'name'),
                                                       disk_model.get('name')))
                        for ring in attrs.get('rings'):
                            if isinstance(ring, str):
                                ring_name = ring
                            else:
                                ring_name = ring.get('name')
                            server_ip, bind_port = self._get_server_bind(
                                ring_name, server_name)
                            if not server_ip:
                                # TODO: this may be worth warning
                                break
                            swift_drive_name = LVM_MOUNT + str(lv_index)
                            device_name = '/dev/' + vg_name + '/' + lv_name
                            device_info = DeviceInfo({
                                'region_name': region_name,
                                'rack_id': rack_id,
                                'region_id': 1,    # later, the rack id may
                                'zone_id': 1,      # change these defaults
                                'server_name': Consumes.basename(
                                    server_name),
                                'server_ip': server_ip,
                                'server_bind_port': bind_port,
                                'replication_ip': server_ip,
                                'replication_bind_port': bind_port,
                                'swift_drive_name': swift_drive_name,
                                'device_name': device_name,
                                'ring_name': ring_name,
                                'group_type': 'lvm',
                                'block_devices': {'percent': percent,
                                                  'physicals':
                                                      physical_volumes},
                                'presence': 'present'})
                            yield device_info
                        lv_index += 1

    def _get_server_bind(self, ring_name, server_name):
        network_name, network_port = self.consumes.get_network_name_port(
            ring_name, server_name)
        if not network_name:
            return None, None
        server_ip = self.ip_address(network_name, 'ring: %s host: %s' % (
            ring_name, server_name))
        return (server_ip, network_port)

    def __repr__(self):
        output = '\nInput Model\n'
        output += '-----------\n\n'
        output += '\n  Servers\n'
        output += '    Number: %s' % len(self.config.get('global').get(
            'all_servers'))
        output += '\n    Device Information\n'
        for di in self.iter_devices():
            output += '\n      device info: %s' % di
        return output

    def _read_config(self, fd):
        self.config = safe_load(fd)

    def _load_host_ip_mapping(self, hosts_fd):
        """
        Load host to IP mapping data

        For now, this is simply a hosts file (/etc/hosts or .net/hosts.hf).
        Later, this will load the HLM 2.0 model.
        """
        for line in hosts_fd:
            line = line.strip()
            try:
                if line.startswith('#'):
                    continue
                words = line.split()
                ip_address = words[0]
                hostname = words[1]
                self.host_ip_map[ip_address] = hostname
                self.host_ip_map[hostname] = ip_address
            except Exception:
                continue  # Ignore all parsing errors

    def ip_address(self, hostname, context):
        """
        Returns IP address of host from hosts file
        """
        ip_address = self.host_ip_map.get(hostname)
        if not ip_address:
            raise SwiftModelException('Cannot find ip address of %s for'
                                      ' %s' % (hostname, context))
        return ip_address

    def aliases(self, ip_address):
        """
        Given an ip address, return a list of alternate ip addresses

        :param ip_address: The ip address to lookup.
        :return: list of ip addresses
        """
        aliases = []
        network_name = self.host_ip_map.get(ip_address)
        if not network_name:
            return []
        basename = Consumes.basename(network_name)
        for item in self.host_ip_map.keys():
            item_name = self.host_ip_map.get(item)
            if item_name:
                item_basename = Consumes.basename(item_name)
                if item_basename == basename:
                    aliases.append(item)
        return aliases
