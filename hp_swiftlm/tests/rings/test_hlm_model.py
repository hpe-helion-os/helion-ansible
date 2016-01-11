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


import unittest
from yaml import safe_load

from swiftlm.rings.hlm_model import InputModel
from swiftlm.rings.ring_model import DeviceInfo

from tests.data.ring_padawan import padawan_input_model, padawan_net_hosts, \
    padawan_swf_rng_consumes, expected_lv_devices


lvm_disk_model = '''
global:
    all_servers:
    -   disk_model:
            name: WHATEVER
            volume_groups:
            -   logical_volumes:
                -   name: SW0
                    consumer:
                        name: swift
                        attrs:
                            rings:
                            - object-0
                            - object-1
                -   name: SW1
                    consumer:
                        name: swift
                        attrs:
                            rings:
                            - object-2
                            - object-3
                name: vg-one
                physical_volumes:
                - /dev/sda1
            -   logical_volumes:
                -   name: SW2
                    consumer:
                        name: swift
                        attrs:
                            rings:
                            - object-4
                            - object-5
                            - object-6
                name: vg=two
                physical_volumes:
                - /dev/sdb
        name: padawan-ccp-c1-m1-mgmt
        rack: null
        region: regionone
    -   disk_model:
            name: WHATEVER
            volume_groups:
            -   logical_volumes:
                -   name: SW0
                    consumer:
                        name: swift
                        attrs:
                            rings:
                            - object-7
                -   name: SW1
                    consumer:
                        name: swift
                        attrs:
                            rings:
                            - object-8
                name: vg-one
                physical_volumes:
                - /dev/sda1
            -   logical_volumes:
                -   name: SW2
                    consumer:
                        name: swift
                        attrs:
                            rings: []
                -   name: SW3
                    consumer:
                        name: swift
                        attrs:
                            rings:
                            - object-9
                            - object-10
                name: vg=two
                physical_volumes:
                - /dev/sdb
        name: padawan-ccp-c1-m2-mgmt
        rack: null
        region: regionone
'''

device_groups_disk_model = '''
global:
    all_servers:
    -   disk_model:
            name: WHATEVER
            device_groups:
              - name: swiftac
                devices:
                    # should be 0
                  - name: /dev/sdb
                    # should be 1
                  - name: /dev/sdc
                consumer:
                  name: swift
                  attrs:
                    rings:
                      - account
                      - container
              - name: swiftobj
                devices:
                    # should be 2
                  - name: /dev/sdd
                    # should be 3
                  - name: /dev/sde
                    # should be 4
                  - name: /dev/sdf
                consumer:
                  name: swift
                  attrs:
                    rings:
                      - object-0
              - name: swiftobj
                devices:
                    # should be 5
                  - name: /dev/sdg
                    # should be 6
                  - name: /dev/sdh
                    # should be 7
                  - name: /dev/sdi
                consumer:
                  name: swift
                  attrs:
                    rings:
                      - object-1

              - name: swiftobj
                devices:
                    # should be 8
                  - name: /dev/sdj
                    # should be 9
                  - name: /dev/sdk
                    # should be 10
                  - name: /dev/sdl
                consumer:
                  name: swift
                  attrs:
                    rings: []
              - name: swiftobj
                devices:
                    # should be 11
                  - name: /dev/sdm
                    # should be 12
                  - name: /dev/sdn
                    # should be 13
                  - name: /dev/sdo
                consumer:
                  name: swift
                  attrs:
                    rings:
                      - object-1
                      - object-0

        name: padawan-ccp-c1-m1-mgmt
        rack: null
        region: regionone
    -   disk_model:
            name: WHATEVER
            device_groups:
              - name: a
                devices:
                  - name: /dev/sda
                consumer:
                  name: swift
                  attrs:
                    rings:
                      - account
              - name: b
                devices:
                  - name: /dev/sdb
                consumer:
                  name: swift
                  attrs:
                    rings:
                      - container
              - name: c
                devices:
                  - name: /dev/sdc
                consumer:
                  name: swift
                  attrs:
                    rings:
                      - object-0
              - name: d
                devices:
                  - name: /dev/sdd
                consumer:
                  name: swift
                  attrs:
                    rings:
                      - object-1
              - name: e
                devices:
                  - name: /dev/sde
                consumer:
                  name: swift
                  attrs:
                    rings:
                      - object-2
        name: padawan-ccp-c1-m2-mgmt
        rack: null
        region: regionone
'''


class TestHlmModel(unittest.TestCase):

    def test_iter_volume_groups(self):
        input_model = InputModel(config=safe_load(padawan_input_model),
                                 hosts_fd=padawan_net_hosts,
                                 consumes=padawan_swf_rng_consumes)
        lv_devices = []
        lv_expected = []
        for lv_device in input_model._iter_volume_groups():
            lv_devices.append(DeviceInfo(lv_device))
        self.assertEqual(len(lv_devices), 3)

        # This could be done with a simple assertEquals(), but this allowed
        # me to pin-point differences between actual and expected results
        for lv_device in expected_lv_devices:
            lv_expected.append(DeviceInfo(lv_device))
        lv_expected = sorted(lv_expected, None,  DeviceInfo.sortkey)
        lv_devices = sorted(lv_devices, None, DeviceInfo.sortkey)
        for i in range(0, len(lv_expected)):
            self.assertEqual(sorted(lv_expected[i].keys()),
                             sorted(lv_devices[i].keys()))
            for key in lv_expected[i].keys():
                self.assertEqual(lv_expected[i].get(key),
                                 lv_devices[i].get(key))


class TestLvm(unittest.TestCase):

    def test_lvm_numbering(self):
        input_model = InputModel(config=safe_load(lvm_disk_model),
                                 hosts_fd=padawan_net_hosts,
                                 consumes=padawan_swf_rng_consumes)
        lv_devices = []
        lv_info = set()
        for lv_device in input_model._iter_volume_groups():
            lv_devices.append(DeviceInfo(lv_device))
            lv_info.add((lv_device.server_name, lv_device.ring_name,
                         lv_device.swift_drive_name))
        self.assertEqual(len(lv_devices), 11)

        # Do not change this without also examining test_drivedata.py
        lv_expected = [
            ('padawan-ccp-c1-m1', 'object-0', 'lvm0'),
            ('padawan-ccp-c1-m1', 'object-1', 'lvm0'),

            ('padawan-ccp-c1-m1', 'object-2', 'lvm1'),
            ('padawan-ccp-c1-m1', 'object-3', 'lvm1'),

            ('padawan-ccp-c1-m1', 'object-4', 'lvm2'),
            ('padawan-ccp-c1-m1', 'object-5', 'lvm2'),
            ('padawan-ccp-c1-m1', 'object-6', 'lvm2'),

            ('padawan-ccp-c1-m2', 'object-7', 'lvm0'),

            ('padawan-ccp-c1-m2', 'object-8', 'lvm1'),

            ('padawan-ccp-c1-m2', 'object-9', 'lvm3'),
            ('padawan-ccp-c1-m2', 'object-10', 'lvm3')
        ]
        for lv in set(lv_expected):
            self.assertTrue(lv in lv_info, '%s missing from %s' % (
                lv, lv_info))
            lv_expected.remove(lv)
        self.assertEqual(0, len(lv_expected), 'still have %s' % lv_expected)


class TestDev(unittest.TestCase):

    def test_dev_numbering(self):
        input_model = InputModel(config=safe_load(device_groups_disk_model),
                                 hosts_fd=padawan_net_hosts,
                                 consumes=padawan_swf_rng_consumes)
        dev_devices = []
        dev_info = set()
        for dev_device in input_model._iter_device_groups():
            dev_devices.append(DeviceInfo(dev_device))
            dev_info.add((dev_device.server_name, dev_device.ring_name,
                         dev_device.swift_drive_name, dev_device.device_name))
        self.assertEqual(len(dev_devices), 21)

        # Do not change this without also examining test_drivedata.py
        dev_expected = [
            ('padawan-ccp-c1-m1', 'account', 'disk0', '/dev/sdb'),
            ('padawan-ccp-c1-m1', 'container', 'disk0', '/dev/sdb'),
            ('padawan-ccp-c1-m1', 'account', 'disk1', '/dev/sdc'),
            ('padawan-ccp-c1-m1', 'container', 'disk1', '/dev/sdc'),

            ('padawan-ccp-c1-m1', 'object-0', 'disk2', '/dev/sdd'),
            ('padawan-ccp-c1-m1', 'object-0', 'disk3', '/dev/sde'),
            ('padawan-ccp-c1-m1', 'object-0', 'disk4', '/dev/sdf'),

            ('padawan-ccp-c1-m1', 'object-1', 'disk5', '/dev/sdg'),
            ('padawan-ccp-c1-m1', 'object-1', 'disk6', '/dev/sdh'),
            ('padawan-ccp-c1-m1', 'object-1', 'disk7', '/dev/sdi'),

            ('padawan-ccp-c1-m1', 'object-1', 'disk11', '/dev/sdm'),
            ('padawan-ccp-c1-m1', 'object-0', 'disk11', '/dev/sdm'),
            ('padawan-ccp-c1-m1', 'object-1', 'disk12', '/dev/sdn'),
            ('padawan-ccp-c1-m1', 'object-0', 'disk12', '/dev/sdn'),
            ('padawan-ccp-c1-m1', 'object-1', 'disk13', '/dev/sdo'),
            ('padawan-ccp-c1-m1', 'object-0', 'disk13', '/dev/sdo'),

            ('padawan-ccp-c1-m2', 'account', 'disk0', '/dev/sda'),
            ('padawan-ccp-c1-m2', 'container', 'disk1', '/dev/sdb'),
            ('padawan-ccp-c1-m2', 'object-0', 'disk2', '/dev/sdc'),
            ('padawan-ccp-c1-m2', 'object-1', 'disk3', '/dev/sdd'),
            ('padawan-ccp-c1-m2', 'object-2', 'disk4', '/dev/sde')
        ]
        for dev in set(dev_expected):
            self.assertTrue(dev in dev_info, '%s missing from %s' % (
                dev, dev_info))
            dev_info.remove(dev)
        self.assertEqual(0, len(dev_info), 'still have %s' % dev_info)
