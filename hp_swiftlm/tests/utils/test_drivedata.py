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
import unittest


from swiftlm.utils.drivedata import Drive, LogicalVol
from tests.rings.test_hlm_model import device_groups_disk_model, lvm_disk_model


class TestUtility(unittest.TestCase):

    def test_valid_disk_model(self):
        disk_model = '''
volume_groups:
-   consumer:
        name: os
    logical_volumes:
    -   fstype: ext4
        mount: /
        name: root
        size: 40%
    -   attrs:
            rings:
            - account
            - container
        consumer:
            name: swift
        name: swf1
        size: 5%
    -   attrs:
            rings:
            - account
            - container
        consumer:
            name: swift
        name: swf2
        size: 5%
    -   fstype: ext4
        mkfs_opts: -O large_file
        mount: /var/log
        name: log
        size: 20%
    -   fstype: ext4
        mkfs_opts: -O large_file
        mount: /var/crash
        name: crash
        size: 10%
    -   fstype: ext4
        mkfs_opts: -O large_file
        mount: /var/lib/elasticsearch
        name: elasticsearch
        size: 10%
    -   fstype: ext4
        mkfs_opts: -O large_file
        mount: /var/lib/zookeeper
        name: zookeeper
        size: 5%
    name: hlm-vg
'''
        swift_lvms = LogicalVol.get_lvms(yaml.safe_load(disk_model))
        expect0 = ('swf1', 'lvm0')
        expect1 = ('swf2', 'lvm1')
        results = []
        for swift_lvm in swift_lvms:
            name = swift_lvm.lvm
            mount = swift_lvm.swift_lvm_name
            results.append((name, mount))
        self.assertEqual(results, [expect0, expect1])

    def test_no_swift_consumers(self):
        disk_model = '''
volume_groups:
-   consumer:
        name: os
    logical_volumes:
    -   fstype: ext4
        mount: /
        name: root
        size: 40%
    -   fstype: ext4
        mkfs_opts: -O large_file
        mount: /var/log
        name: log
        size: 20%
    -   fstype: ext4
        mkfs_opts: -O large_file
        mount: /var/crash
        name: crash
        size: 10%
    -   fstype: ext4
        mkfs_opts: -O large_file
        mount: /var/lib/elasticsearch
        name: elasticsearch
        size: 10%
    -   fstype: ext4
        mkfs_opts: -O large_file
        mount: /var/lib/zookeeper
        name: zookeeper
        size: 5%
    name: hlm-vg
'''
        swift_lvms = LogicalVol.get_lvms(yaml.safe_load(disk_model))
        self.assertEqual(len(swift_lvms), 0)

    def test_bad_consumer_syntax(self):
        disk_model = '''
volume_groups:
-   consumer:
        name: os
    logical_volumes:
    -   fstype: ext4
        mount: /
        name: root
        size: 40%
    -   name: swf1
        consumer: swift   # should be object with name and attrs
        attrs:
            rings:
               - junk
    name: hlm-vg
'''
        swift_lvms = LogicalVol.get_lvms(yaml.safe_load(disk_model))
        self.assertEqual(len(swift_lvms), 0)

    def test_drivedata_same_as_hlm_model_numbering(self):
        hlm_model = yaml.safe_load(device_groups_disk_model)
        server0 = hlm_model.get('global').get('all_servers')[0]
        drive_model = server0.get('disk_model')
        swift_devs = Drive.get_drives(drive_model)
        name_numbers = []
        for dev in swift_devs:
            name_numbers.append((dev.device, dev.swift_device_name))

        # Do not change this without also examining test_hlm_model.py
        dev_expected = [
            ('/dev/sdb', 'disk0'),
            ('/dev/sdc', 'disk1'),
            ('/dev/sdd', 'disk2'),
            ('/dev/sde', 'disk3'),
            ('/dev/sdf', 'disk4'),
            ('/dev/sdg', 'disk5'),
            ('/dev/sdh', 'disk6'),
            ('/dev/sdi', 'disk7'),
            ('/dev/sdj', 'disk8'),
            ('/dev/sdk', 'disk9'),
            ('/dev/sdl', 'disk10'),
            ('/dev/sdm', 'disk11'),
            ('/dev/sdn', 'disk12'),
            ('/dev/sdo', 'disk13')
        ]
        for dev in set(dev_expected):
            self.assertTrue(dev in name_numbers, '%s missing from %s' % (
                dev, name_numbers))
            name_numbers.remove(dev)
        self.assertEqual(0, len(name_numbers), 'still have %s' % name_numbers)

    def test_lvmdata_same_as_hlm_model_numbering(self):
        hlm_model = yaml.safe_load(lvm_disk_model)
        server0 = hlm_model.get('global').get('all_servers')[0]
        drive_model = server0.get('disk_model')
        swift_devs = LogicalVol.get_lvms(drive_model)
        name_numbers = []
        for dev in swift_devs:
            name_numbers.append(dev.swift_lvm_name)

        # Do not change this without also examining test_hlm_model.py
        dev_expected = ['lvm0', 'lvm1', 'lvm2']
        for dev in set(dev_expected):
            self.assertTrue(dev in name_numbers, '%s missing from %s' % (
                dev, name_numbers))
            name_numbers.remove(dev)
        self.assertEqual(0, len(name_numbers), 'still have %s' % name_numbers)

        # Check we handle empty ring list (lvm2 has no rings), but has
        # Swift consumer
        server1 = hlm_model.get('global').get('all_servers')[1]
        drive_model = server1.get('disk_model')
        swift_devs = LogicalVol.get_lvms(drive_model)
        name_numbers = []
        for dev in swift_devs:
            name_numbers.append(dev.swift_lvm_name)

        # Do not change this without also examining test_hlm_model.py
        dev_expected = ['lvm0', 'lvm1', 'lvm2', 'lvm3']
        for dev in set(dev_expected):
            self.assertTrue(dev in name_numbers, '%s missing from %s' % (
                dev, name_numbers))
            name_numbers.remove(dev)
        self.assertEqual(0, len(name_numbers), 'still have %s' % name_numbers)
