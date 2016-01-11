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


from os import listdir
import os.path
import subprocess
import sys
import yaml
import json

from swiftlm.rings.ring_model import DeviceInfo, RingSpecification


class RingDelta(object):
    """
    The ring delta describes rings in actionable terms

    The ring delta contains the following:

    delta_rings
        Is all known ring specifications. Most ring specifications originate
        in the input model. However, we might find a builder file for a ring
        that has been since deleted from the input model.

    delta_ring_actions
        Describes the actions we will take against delta_rings (such as
        create or change replica-count).

    delta_devices
        Is all known devices. Most devices originate in the input model.
        However, we may find a device in a builder file (because the
        device or server has since been removed from the input model).

        In addition to listing the device attributes, we also record the
        action (add, remove, change weight) that should happen to the
        device.
    """

    def __init__(self):
        self.delta_rings = {}
        self.delta_ring_actions = {}
        self.delta_devices = []

    def read_from_file(self, fd, fmt):
        if fmt == 'yaml':
            model = yaml.safe_load(fd)
        else:
            model = json.loads(fd)
        self.load_model(model)
        fd.close()

    def write_to_file(self, fd, fmt):
        data = self.dump_model()
        if fmt == 'yaml':
            output = yaml.safe_dump(data, default_flow_style=False)
        else:
            output = yaml.dumps(data, indent=2)
        fd.write(output)
        if not fd == sys.stdout:
            fd.close()

    def __repr__(self):
        output = ''
        for region_name, ring_name in self.delta_rings.keys():
            output += '-----------------------------\n'
            output += 'region_name: %s ring_name: %s\n ring_spec: %s' % (
                region_name,  ring_name, self.delta_rings[(region_name,
                                                           ring_name)])
        for region_name, ring_name in self.delta_ring_actions:
            output += '-----------------------------\n'
            output += 'region_name: %s ring_name: %s\n action: %s' % (
                region_name,  ring_name, self.delta_ring_actions[(region_name,
                                                                  ring_name)])
        for device in self.delta_devices:
            output += '-----------------------------\n'
            output += 'DEVICE\n'
            output += '%s\n' % device
        return output

    def dump_model(self):
        staged_rings = []
        for region_name, ring_name in self.delta_rings.keys():
            ring_specification = self.delta_rings[(region_name, ring_name)]
            staged_rings.append({'region_name': region_name,
                                 'ring_name': ring_name,
                                 'ring_specification':
                                 ring_specification.dump_model()})
        stage_ring_actions = []
        for region_name, ring_name in self.delta_ring_actions.keys():
            action = self.delta_ring_actions[(region_name, ring_name)]
            stage_ring_actions.append({'region_name': region_name,
                                       'ring_name': ring_name,
                                       'action': action})
        staged_devices = []
        for device in self.delta_devices:
            staged_devices.append(device.dump_model())
        return {'delta_rings': staged_rings,
                'delta_ring_actions': stage_ring_actions,
                'delta_devices': staged_devices}

    def load_model(self, data):
        staged_rings = data.get('delta_rings')
        for staged_ring in staged_rings:
            region_name = staged_ring.get('region_name')
            ring_name = staged_ring.get('ring_name')
            ring_specification = RingSpecification(None)
            ring_specification.load_model(staged_ring.get(
                'ring_specification'))
            self.delta_rings[(region_name, ring_name)] = ring_specification
        stage_ring_actions = data.get('delta_ring_actions')
        for stage_ring_action in stage_ring_actions:
            region_name = stage_ring_action.get('region_name')
            ring_name = stage_ring_action.get('ring_name')
            action = stage_ring_action.get('action')
            self.delta_ring_actions[(region_name, ring_name)] = action
        for staged_device in data.get('delta_devices'):
            device = DeviceInfo()
            device.load_from_model(staged_device)
            self.delta_devices.append(device)

    def append_device(self, device_info):
        self.delta_devices.append(device_info)

    def register_ring(self, region_name, ring_name, ring_specification):
        self.delta_rings[(region_name, ring_name)] = ring_specification
        self.delta_ring_actions[(region_name, ring_name)] = ['undetermined']

    def sort(self):
        self.delta_devices = sorted(self.delta_devices, None,
                                    DeviceInfo.sortkey)

    def get_report(self, detail='summary'):
        output = ''
        for region_name, ring_name in self.delta_rings.keys():
            if self.delta_ring_actions.get((region_name,
                                            ring_name)) == ['add']:
                output += 'Need to create ring %s for region %s\n' % (
                    ring_name, region_name)
        num_devices_to_add = 0
        num_devices_to_remove = 0
        num_devices_to_set_weight = 0
        for device_info in self.delta_devices:
            if device_info.presence == 'add':
                if detail == 'full':
                    output += 'Need to add device: %s\n' % device_info
                num_devices_to_add += 1
            elif device_info.presence == 'remove':
                if detail == 'full':
                    output += 'Need to remove device: %s\n' % device_info
                num_devices_to_remove += 1
            elif device_info.presence == 'set-weight':
                if detail == 'full':
                    output += 'Need to change weight on'
                    output += ' device: %s\n' % device_info
                num_devices_to_set_weight += 1
        output += 'Need to add %s devices\n' % num_devices_to_add
        output += 'Need to remove %s devices\n' % num_devices_to_remove
        output += 'Need to set weight on %s devices\n' % (
            num_devices_to_set_weight)
        return output


class RingBuilder(object):

    def __init__(self, builder_dir, read_write):
        self.builder_dir = builder_dir
        self.flat_device_list = []
        self.builder_rings = {}
        if not os.path.isdir(builder_dir):
                raise IOError('%s is not a directory' % builder_dir)
        if read_write:
            for region_dir in [f for f in listdir(builder_dir) if
                               (os.path.isdir(os.path.join(builder_dir, f)) and
                                f.startswith('region-'))]:
                region_name = region_dir[len('region-'):]
                region_dir = os.path.join(builder_dir, region_dir)
                for filename in [f for f in listdir(region_dir) if
                                 (os.path.isfile(os.path.join(region_dir,
                                                              f)) and
                                  f.endswith('.builder'))]:
                    ring_name = filename[0:filename.find('.builder')]
                    self.replica_count = 0.0
                    self.balance = 0.0
                    for device_info in self._parse_builder_output(os.path.join(
                            region_dir, filename)):
                        device_info.region_name = region_name
                        device_info.ring_name = ring_name
                        self.flat_device_list.append(device_info)
                    self.register_ring(region_name, ring_name,
                                       self.replica_count, self.balance)

    def __repr__(self):
        output = '  RING FILES\n'
        for region_name, ring_name in self.builder_rings.keys():
            output += '    KS REGION: %s ring: %s' % (region_name, ring_name)
            output += ' ringspec: %s\n' % self.builder_rings[(region_name,
                                                              ring_name)]

        output += '  FLAT DEVICES\n'
        for drive_detail in self.flat_device_list:
            output += '    %s\n' % drive_detail
        return output

    def register_ring(self, region_name, ring_name, replica_count, balance):
        if not self.builder_rings.get((region_name, ring_name)):
            model = {'name': ring_name,
                     'partition_power': 0,
                     'replication_policy': {'replica_count': replica_count},
                     'min_part_time': 0,
                     'display_name': 'unknown',
                     'server_network_group': 'unknown',
                     'balance': balance}
            ringspec = RingSpecification(None)
            ringspec.load_model(model)
            self.builder_rings[(region_name, ring_name)] = ringspec

    def get_ringspec(self, region_name, ring_name):
        return self.builder_rings[(region_name, ring_name)]

    def _parse_builder_output(self, builder_filename):
        ring_name = builder_filename[0:builder_filename.find('.builder')]
        try:
            output = subprocess.check_output(['swift-ring-builder',
                                              '%s' % builder_filename])
        except subprocess.CalledProcessError as err:
            print('ERROR: swift-ring-builder %s: %s' % (builder_filename, err))
            sys.exit(1)
        done_with_headers = False
        for line in output.split('\n'):
            items = line.split()
            if not items:
                break
            if items[1] == 'partitions,':
                self.partitions = int(items[0])
                self.replica_count = float(items[2])
                self.balance = float(items[10])
            if items[0] == 'Devices:':
                done_with_headers = True
                continue
            if done_with_headers:
                (deviceid, region_id, zone_id, server, port, replicationip,
                 replicationport, drive, weight, partitions, balance,
                 meta) = items
                device_info = DeviceInfo({'ring_name': ring_name,
                                          'zone_id': zone_id,
                                          'region_id': region_id,
                                          'server_ip': server,
                                          'server_bind_port': port,
                                          'replication_ip': replicationip,
                                          'replication_bind_port':
                                          replicationport,
                                          'swift_drive_name': drive,
                                          'weight': weight,
                                          'balance': balance,
                                          'meta': meta,
                                          'presence': 'present'})
                yield device_info

    def device_count(self, region_name, ring_name):
        count = 0
        for device_info in self.flat_device_list:
            if (region_name == device_info.region_name and
                    ring_name == device_info.ring_name):
                count += 1
        return count

    def command_ring_create(self, region_name, ringspec):
        ring_name = ringspec.name
        builder_path = os.path.join(self.builder_dir,
                                    'region-%s' % region_name,
                                    '%s.builder' % ring_name)
        return 'swift-ring-builder %s create %s %s %s' % (
            builder_path,
            ringspec.partition_power,
            ringspec.replica_count,
            ringspec.min_part_time)

    def command_set_replica_count(self, region_name, ringspec):
        ring_name = ringspec.name
        builder_path = os.path.join(self.builder_dir,
                                    'region-%s' % region_name,
                                    '%s.builder' % ring_name)
        return 'swift-ring-builder %s set_replicas %s' % (
            builder_path,
            ringspec.replica_count)

    def command_device_add(self, device_info):
        ring_name = device_info.ring_name
        region_name = device_info.region_name
        builder_path = os.path.join(self.builder_dir,
                                    'region-%s' % region_name,
                                    '%s.builder' % ring_name)
        if not device_info.replication_bind_port:
            device_info.replication_bind_port = device_info.server_bind_port
        if not device_info.replication_ip:
            device_info.replication_ip = device_info.server_ip
        return ('swift-ring-builder %s add'
                ' --region %s --zone %s'
                ' --ip %s --port %s'
                ' --replication-port %s --replication-ip %s'
                ' --device %s --meta %s'
                ' --weight %s' % (builder_path,
                                  device_info.region_id,
                                  device_info.zone_id,
                                  device_info.server_ip,
                                  device_info.server_bind_port,
                                  device_info.replication_bind_port,
                                  device_info.replication_ip,
                                  device_info.swift_drive_name,
                                  device_info.meta,
                                  device_info.weight))

    def command_rebalance(self, region_name, ringspec):
        ring_name = ringspec.name
        builder_path = os.path.join(self.builder_dir,
                                    'region-%s' % region_name,
                                    '%s.builder' % ring_name)
        return ('swift-ring-builder %s rebalance 999' % builder_path)

    def command_device_set_weight(self, device_info):
        ring_name = device_info.ring_name
        region_name = device_info.region_name
        builder_path = os.path.join(self.builder_dir,
                                    'region-%s' % region_name,
                                    '%s.builder' % ring_name)
        ipaddr = device_info.server_ip
        swift_drive_name = device_info.swift_drive_name
        search = '%s/%s' % (ipaddr, swift_drive_name)
        return('swift-ring-builder %s  set_weight %s %s' % (builder_path,
               search, device_info.weight))

    def command_device_remove(self, device_info):
        ring_name = device_info.ring_name
        region_name = device_info.region_name
        builder_path = os.path.join(self.builder_dir,
                                    'region-%s' % region_name,
                                    '%s.builder' % ring_name)
        ipaddr = device_info.server_ip
        swift_drive_name = device_info.swift_drive_name
        search = '%s/%s' % (ipaddr, swift_drive_name)
        return('swift-ring-builder %s  remove %s' % (builder_path, search))

    @staticmethod
    def run_cmd(cmd):
        status = 0
        try:
            output = subprocess.check_output(cmd.split())
        except subprocess.CalledProcessError as err:
            status = err.returncode
            output = err.output
        if int(status) <= 1:
            # Exited with EXIT_WARNING
            status = -1
        return (int(status), output)
