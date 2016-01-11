#!/usr/bin/env python

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


import yaml


DISK_MOUNT = 'disk'
LVM_MOUNT = 'lvm'


class SwiftlmInvalidConfig(Exception):
    pass


class Drive(object):
    def __init__(self, device, consumer, swift_name):
        self.device = device
        self.consumer = consumer
        self.swift_device_name = swift_name

    @classmethod
    def load(cls, file_name):
        try:
            data = yaml.safe_load(open(file_name).read())
        except yaml.YAMLError as err:
            raise SwiftlmInvalidConfig("Unable to read yaml in %s - %s"
                                       % (file_name, err))
        except IOError as io_err:
            raise SwiftlmInvalidConfig("Unable to read %s - %s"
                                       % (file_name, io_err))
        return cls.get_drives(data)

    @classmethod
    def get_drives(cls, data):
        drives = []
        device_num = 0
        if "device_groups" in data:
            for device_group in data['device_groups']:
                for device in device_group['devices']:
                    if device_group.get('consumer'):
                        if device_group['consumer']['name'] == 'swift':
                            drives.append(
                                cls(device=device['name'],
                                    consumer=device_group['consumer'],
                                    swift_name=DISK_MOUNT + str(device_num)))
                            device_num += 1

        return drives

    def __repr__(self):
        return 'Drive("{}", {}, "{}")'.format(
            self.device, self.consumer, self.swift_device_name)


class LogicalVol(object):
    def __init__(self, lvm, consumer, swift_name, lvg):
        self.lvm = lvm
        self.consumer = consumer
        self.swift_lvm_name = swift_name
        self.lvg = lvg

    @classmethod
    def load(cls, file_name):

        try:
            data = yaml.safe_load(open(file_name).read())
        except yaml.YAMLError as err:
            raise SwiftlmInvalidConfig("Unable to read yaml in %s - %s"
                                       % (file_name, err))
        except IOError as io_err:
            raise SwiftlmInvalidConfig("Unable to read %s - %s"
                                       % (file_name, io_err))

        return cls.get_lvms(data)

    @classmethod
    def get_lvms(cls, data):
        lvms = []
        lvm_num = 0
        if "volume_groups" in data:
            for volume_group in data['volume_groups']:
                for lv in volume_group['logical_volumes']:
                    lvm_name = lv.get('name')
                    consumer = lv.get('consumer')
                    if consumer and isinstance(consumer, dict):
                        if consumer.get('name', 'not-swift') == 'swift':
                            lvms.append(
                                cls(consumer=consumer,
                                    swift_name=LVM_MOUNT + str(lvm_num),
                                    lvm=lvm_name,
                                    lvg=volume_group['name']))
                            lvm_num += 1
        return lvms

    def __repr__(self):
        return 'Logical_Vol("{}", {}, "{}", "{}")'.format(
            self.lvm, self.consumer, self.swift_lvm_name, self.lvg)
