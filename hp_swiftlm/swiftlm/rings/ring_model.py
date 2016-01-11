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


import copy
import os
from yaml import safe_load


class SwiftModelException(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class RingSpecification(dict):
    """
    Specification of a single ring

    This input has the following structure:

        name: <str>                        # Ring name
        display_name: <str>
        weight-step: <float>               # Optional. (default None)
        partition_power: <int>
        min_part_time: <int>
        default: <bool>                    # Optional (default: False)
        server_network_group: <str>
        server_bind_port: <int>     # Optional (defaults)
        replication_network_group: <str>   # Optional (server_network_group)
        replication_bind_port: <int>       # Optional

        replication_policy:                # Must be present for account/
            replica_count: <int>           # container rings

        erasure_coding_policy;             # Optional for object rings
             ec_num_data_fragments: <int>
             ec_num_parity_fragments: <int>
             ec_type: jerasure_rs_vand     # Optional
             ec_object_segment_size: <int>

        swift_zones:                       # Optional. Not yet implemented
             id: <int>                     # in the input model
             rack_ids:
               -  1
               -  2
        balance: <float>                   # Not in input model, but is in
                                           # rings read from a builder file

        parent: <obj>                      # Not in model. A pointer to
                                           # containing specification
                                           # (to inherit region and zone)
    """
    keynames = ['name', 'display_name', 'partition_power', 'min_part_time',
                'default', 'server_network_group', 'server_bind_port',
                'replication_network_group', 'replication_bind_port',
                'replication_policy', 'erasure_coding_policy',
                'swift_zones', 'balance', 'parent', 'weight_step']

    def __init__(self, parent):
        super(RingSpecification, self).__init__()
        self.update({'parent': parent})

    def __getattr__(self, item):
        # Special case for replica-count
        if item == 'replica_count':
            if self.get('replication_policy'):
                return float(
                    self.get('replication_policy').get('replica_count'))
            elif self.get('erasure_coding_policy'):
                ec = self.get('erasure_coding_policy')
                return float((ec.get('ec_num_data_fragments') +
                              ec.get('ec_num_parity_fragments')))
            return None

        # Return value for valid items
        if item in RingSpecification.keynames:
            return self.get(item, None)
        else:
            raise AttributeError

    def __repr__(self):
        output = '(ring) name: %s,' % self.name
        output += ' display-name: %s,' % self.display_name
        output += ' partition-power: %s,' % self.partition_power
        output += ' replica_count: %s' % self.__getattr__('replica_count')
        return output

    def dump_model(self):
        model = {}
        for key in self.keys():
            if key not in ['parent']:
                model[key] = self.get(key)
        return model

    def load_model(self, model):
        self.update(model)
        if not self.get('server_bind_port', None):
            if self.get('name').startswith('account'):
                port = 6002
            elif self.get('name').startswith('container'):
                port = 6001
            else:
                port = 6000
            self['server_bind_port'] = port
        if not self.get('replication_network_group', None):
            self['replication_network_group'] = self.server_network_group
            self['replication_bind_port'] = self.server_bind_port
        if self.replication_policy and self.erasure_coding_policy:
            raise SwiftModelException('Ring: %s has specified both'
                                      ' replication_policy and'
                                      ' erasure_coding_policy. Only one'
                                      ' may be specified.' % self.name)
        if not (self.replication_policy or self.erasure_coding_policy):
            raise SwiftModelException('Ring: %s is missing a policy'
                                      ' type (replication_policy or'
                                      ' erasure_coding_policy).' % self.name)

    def get_zone(self, rack_id):
        """
        Get zone id for given rack.

        :param rack_id: Rack id to search for
        :returns: -1 zones not specified. None means rack_id not found
        """

        if self.swift_zones:
            for zone in self.swift_zones:
                zone_id = zone.get('id')
                for id in zone.get('rack_ids'):
                    if str(rack_id) == str(id):
                        return zone_id
            return None
        else:
            return -1


class KeystoneRegionRings(object):
    """
    Rings in a given Keystone region"

    The input model looks like:

        region_name: region1
        rings:
          - <RingSpecification>     # see that class for details
          - etc...

    """
    def __init__(self, parent):
        self.parent = parent
        self.region_name = ''
        self.swift_regions = []
        self.swift_zones = []
        self.rings = []

    def __repr__(self):
        output = 'region-name: %s\n' % self.region_name
        output += 'swift-regions: %s\n' % self.swift_regions
        output += 'swift-zones: %s\n' % self.swift_zones
        output += '----rings----\n'
        for ringspec in self.rings:
            output += '\n%s' % ringspec
            output += '----end ring----\n'
        return output

    def load_model(self, model):
        self.region_name = model.get('region_name')
        for ring in model.get('rings'):
            ringspec = RingSpecification(self)
            ringspec.load_model(ring)
            self.rings.append(ringspec)
        if model.get('swift_regions'):
            self.swift_regions = model.get('swift_regions')
        if model.get('swift_zones'):
            self.swift_zones = model.get('swift_zones')

    def get_region(self, rack_id):
        if self.swift_regions:
            for region in self.swift_regions:
                region_id = region.get('id')
                for id in region.get('rack_ids'):
                    if str(rack_id) == str(id):
                        return region_id

        else:
            return -1

    def get_zone(self, rack_id):
        if self.swift_zones:
            for zone in self.swift_zones:
                zone_id = zone.get('id')
                for id in zone.get('rack_ids'):
                    if str(rack_id) == str(id):
                        return zone_id
            return None
        else:
            return -1

    def get_region_zone(self, ring_name, rack_id):
        """ Get region/zone; -1 means not defined """
        swift_region_id = self.get_region(rack_id)

        swift_zone_id = None
        for ringspec in self.rings:
            if ring_name == ringspec.name:
                swift_zone_id = ringspec.get_zone(rack_id)
                if not swift_zone_id:
                    return (swift_region_id, None)
        if swift_zone_id == -1:
            # Not at ring level -- get from region (this) level
            swift_zone_id = self.get_zone(rack_id)

        return swift_region_id, swift_zone_id


class RingSpecifications(object):
    """
    Specification of multiple Keystone regions

    This data is directly loaded from the input model.

    The model looks like:

        global:
            all_ring_specifications:
              -  <KeystoneRegionRings>     # See that class for details
              -  etc...
    """
    def __init__(self, fd=None, model=None):
        self.keystone_ring_specifications = []
        if fd:
            self.load_model(safe_load(fd))
        if model:
            self.load_model(model)

    def __repr__(self):
        output = ''
        for ksregion in self.keystone_ring_specifications:
            output += '\n%s' % ksregion
        return output

    def load_model(self, model):
        ringspecs = model.get('global').get('all_ring_specifications')
        for ksregion in ringspecs:
            keystone_region_rings = KeystoneRegionRings(self)
            keystone_region_rings.load_model(ksregion)
            self.keystone_ring_specifications.append(keystone_region_rings)

    def get_storage_policies(self, region_name):
        sp = {'storage_policies': []}
        for region_rings in self.keystone_ring_specifications:
            if region_rings.region_name == region_name:
                for ringspec in region_rings.rings:
                    if ringspec.name.startswith('object'):
                        index = ringspec.name[7:]
                        is_default = ringspec.default
                        default_value = 'no'
                        if is_default:
                            default_value = 'yes'
                        attributes = {'index': int(index),
                                      'name': ringspec.display_name,
                                      'default': default_value}
                        sp['storage_policies'].append({'policy': attributes})
        return sp

    def get_region_zone(self, region_name, ring_name, rack_id):
        for keystone_region_rings in self.keystone_ring_specifications:
            if region_name == keystone_region_rings.region_name:
                return keystone_region_rings.get_region_zone(ring_name,
                                                             rack_id)
                break
        return (None, None)

    def get_ringspec(self, region_name, ring_name):
        for region_rings in self.keystone_ring_specifications:
            if region_rings.region_name == region_name:
                for ringspec in region_rings.rings:
                    if ringspec.name == ring_name:
                        return ringspec

    def get_weight_step(self, region_name, ring_name):
        ringspec = self.get_ringspec(region_name, ring_name)
        if ringspec:
            weight_step = ringspec.get('weight_step', None)
            if weight_step:
                return float(weight_step)
        return None


class DeviceInfo(dict):
    """
    Represents all the data connected with a device
    """

    keynames = ['region_name', 'rack_id', 'region_id', 'zone_id',
                'server_name', 'server_ip', 'server_bind_port',
                'replication_ip', 'replication_bind_port',
                'swift_drive_name', 'device_name', 'ring_name', 'group_type',
                'presence', 'weight', 'balance', 'meta',
                'block_devices']

    def __init__(self, model=None):
        super(DeviceInfo, self).__init__()
        if model:
            self.load_from_model(model)

    def __getattr__(self, item):
        if item in DeviceInfo.keynames:
            return self.get(item, None)
        else:
            raise AttributeError('No key %s in %s' % (item, self))

    def __setattr__(self, item, value):
        if item in DeviceInfo.keynames:
            self.update({item: value})
        else:
            raise AttributeError('No key %s in %s' % (item, self))

    def is_same_device(self, device_info):
        if (self.region_name == device_info.region_name and
                self.ring_name == device_info.ring_name and
                self.server_ip == device_info.server_ip and
                self.swift_drive_name == device_info.swift_drive_name):
            return True
        return False

    def dump_model(self):
        return self.copy()

    def load_from_model(self, model):
        self.update(model)
        if not self.region_name:
            self['region_name'] = 'unknown'
        if not self.group_type:
            self['group_type'] = 'device'
        if not self.presence:
            self['presence'] = 'present'
        if not self.balance:
            self['balance'] = 0
        if not self.meta and (self.swift_drive_name and self.device_name):
            self['meta'] = '%s:%s:%s' % (self.server_name,
                                         self.swift_drive_name,
                                         self.device_name)

    @staticmethod
    def sortkey(device_info):
        return (device_info.region_name + device_info.ring_name +
                device_info.server_ip + device_info.swift_drive_name)


class DriveConfigurations(object):
    """
    Represents all disk configuration of all known servers

    This contains the drive configuration for all servers. It provides
    a convenient way of getting the size of any given drive (/dev/sda) or
    partition (/dev/sda1).
    """
    def __init__(self):
        self.configurations = {}
        self.drive_data = {}

    def add(self, configuration):
        ipaddr = configuration.get('ipaddr')
        self.configurations[ipaddr] = configuration
        for name, size, fulldrive in configuration.iter_drive_info():
            self.drive_data[(ipaddr, name)] = (size, fulldrive)

    def get_drive_configuration(self, ipaddr):
        return self.configurations.get(ipaddr)

    def iter_drives(self):
        for ipaddr in self.configurations.keys():
            drive_configuration = self.configurations.get(ipaddr)
            for (name, size,
                 fulldrive) in drive_configuration.iter_drive_info():
                yield (ipaddr, name, size, fulldrive)

    def get_drive_data(self, ipaddr, name):
        return self.drive_data.get((ipaddr, name), (None, None))

    def get_hw(self, ipaddr, device_info):
        """
        Get actual size of a swift device. Also whether its a partition or not

        The device_info may refer to a block device or a volume in a LVM. If
        a block device, it may refer to a specific partition.

        LVM is made up up several physical drives and the space is then
        allocated on a % basis to each volume. We need the volume size.

        The fulldrive flag indicates is the swift drive uses all of the
        physical drive or is just one of many partitions on the drive. An
        LVM volume is considered a full drive.

        :param ipaddr: ip address (used to find the drive configuration)
        :param device_info: description of the drive

        :returns: tuple of size, fulldrive
        """
        hw_size = None
        if device_info.group_type == 'device':
            physical = device_info.block_devices.get('physicals')[0]
            hw_size, hw_fulldrive = self.get_drive_data(ipaddr, physical)
        else:
            # LVM -- work out size from physical drives and % size
            physical_volumes_total = 0
            for physical in device_info.block_devices.get('physicals'):
                if physical.endswith('_root'):
                    # Templated device name - convert /dev/sdX_root to /dev/sdX
                    # This makes the LVM appear slightly bigger than it
                    # actually is since the boot partition gets counted in the
                    # size.
                    physical = physical[:-len('_root')]
                block_device_size, hw_fulldrive = self.get_drive_data(
                    ipaddr, physical)
                if block_device_size:
                    physical_volumes_total += block_device_size
            if physical_volumes_total:
                percent_human = device_info.block_devices.get(
                    'percent')
                try:  # should be something such as 20%
                    percent = int(percent_human.split('%')[0])
                    hw_size = physical_volumes_total * percent / 100
                except ValueError:
                    hw_size = None
            hw_fulldrive = True
        return hw_size, hw_fulldrive


class DriveConfiguration(dict):
    """
    Represents the disk drive configuration of a server

    The data originates in osconfig probe_hardware module.

    Normally the input model contains device names (e.g., /dev/sda).
    The swiftlm drive provision process will own the fill drive,
    hence it will create a single partition spanning the drive. Hence
    osconfig probe_hardware will return both the drive (/dev/sda) and the
    partition (/dev/sda1). For our purposes we use /dev/sda whether or
    not it has been partitioned.

    Alternatively (mostly to cope with non-standard layouts), we will
    allow partition names in the model (e.g., /dev/sda1). To cope with this
    we return the drive and all partitions, but mark them as not being a
    full drive.

    The input data looks like (yaml):

        ipaddr: 10.0.0.1
        hostname: example
        drives:
        -   name: /dev/sda
            bytes: 100000000
            partitions:
            -   partition: sda1
                bytes: 100000000
        -   name: /dev/sdb
            bytes: 200000000
            partitions: []
        -   name: /dev/sbc
            bytes: 300000
            partitions:
            -    partition: sdc1
                 bytes: 100000
                 partition: sdc2
                 bytes: 200000

    """
    keynames = ['ipaddr', 'hostname', 'drives']

    def __init__(self):
        super(DriveConfiguration, self).__init__()

    def load_model(self, model):
        self.update(model)

    def iter_drive_info(self):
        """
        Get list of drives

        :return: a list where each item is a tuple containing:
            name of drive (e.g. /dev/sda
            size (in bytes)
            boolean, where True means device is the full drive; False means
                it is a partition on the drive
        """
        for drive in self.get('drives'):
            name = drive.get('name')
            size = drive.get('bytes')
            partitions = drive.get('partitions')
            if len(partitions) == 0:
                yield (name, size, True)
            elif len(partitions) == 1:
                # Single partition (e.g., sda1) using full drive
                # Return drive name (e.g., /dev/sda) covers both
                yield (name, size, True)
            else:
                # Drive is partitioned into smaller chunks
                # Return drive and all partitions, e.g.,
                # /dev/sda, /dev/sda1, /dev/sda2
                yield (name, size, False)
                for partition in partitions:
                    yield (os.path.join('/dev',
                                        partition.get('partition')),
                           partition.get('bytes'), False)


class Consumes(object):
    """
    Manages the SWF_RNG variable produced by the Configuration Processor. The
    idea is that the swift-ring-builder/SWF-RNG is definded to consume
    SWF-ACC, SWF-COn and SWF-OBJ. This means the Configuration Processor
    will create the appropriate consumes relationships for those services. In
    other words, the CP will tell us whether to use blah-mgt or blah-obj as
    the appropriate network to communicate on.

    The input model looks like:

    consumes_SWF_ACC:
        members:
            private:
            -   host: padawan-ccp-c1-m3-mgmt
                port: 6002
                use_tls: false
            -   host: padawan-ccp-c1-m2-mgmt
                port: 6002
                use_tls: false
            -   host: padawan-ccp-c1-m1-mgmt
                port: 6002
                use_tls: false
    consumes_SWF_CON:
        etc...
    consumes_SWF_OBJ:
        etc...

    The main function used is get_network_name_port(). For example,
    given an input model as shown above, a ringname/ringtype of 'account'
    and a hostname of 'padawan-ccp-c1-m2' or 'padawan-ccp-c1-m2-mgmt'
    or 'padawan-ccp-c1-m2-obj', the function returns,,

        (padawan-ccp-c1-m2-mgmt, 6002)

    ...since the appropriate network for the account-server is the '-mgmt'
    network.

    """

    @classmethod
    def get_node_list(cls, item, model):
        node_list = model[item]['members']['private']
        return node_list

    @classmethod
    def basename(cls, hostname):
        """ Remove suffix from host name """
        rindex = hostname.rfind('-')
        if rindex > 0:
            return hostname[:rindex]
        else:
            return hostname  # no suffix or starts with '-'

    def __init__(self, model):
        self.nodes = {}
        self.nodes['account'] = Consumes.get_node_list('consumes_SWF_ACC',
                                                       model)
        self.nodes['container'] = Consumes.get_node_list('consumes_SWF_CON',
                                                         model)
        self.nodes['object'] = Consumes.get_node_list('consumes_SWF_OBJ',
                                                      model)
        self.base_to_network = {}
        for ringtype in ['account', 'container', 'object']:
            for node in self.nodes[ringtype]:
                network_name = node['host']
                network_port = node['port']
                basename = Consumes.basename(network_name)
                self.base_to_network[(ringtype, basename)] = (network_name,
                                                              network_port)

    def get_network_name_port(self, ringtype, hostname):
        """
        :param ringtype: Tupe if ring (account, etc.) Can be ring name
            (e.g., object-0)
        :param hostname: name of host -- the name can be any of the variants
            (e.g., blah-mgmt, blah-obj)
        :return: tuple of ip-address, port
        """
        if ringtype.startswith('object'):
            ringtype = 'object'
        result = self.base_to_network.get((ringtype, hostname))
        if result:
            return result
        basename = Consumes.basename(hostname)
        result = self.base_to_network.get((ringtype, basename), (None, None))

        return result
