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


device_info_simple = '''
region_name: region2
region_id: 2
zone_id: 3
server_name: host.example.com
server_ip: 10.0.0.1
swift_drive_name: disk99
device_name: /dev/sdh
ring_name: object-2
group_type: device
presence: present
weight: '12.34'
balance: 99
'''

# Keep the next two items in sync (input and the resulting iter)
drive_configuration_simple = '''
drives:
-   bytes: 42949672960
    name: /dev/sda
    partitions:
    -   bytes: 42941447
        partition: sda1
    -   bytes: 9999
        partition: sda2
-   bytes: 20000000000
    name: /dev/sdb
    partitions:
    -   bytes: 19999999999
        partition: sdb1
-   bytes: 30000000000
    name: /dev/sdc
    partitions: []
-   bytes: 20000000000
    name: /dev/sdd
    partitions: []
-   bytes: 20000000000
    name: /dev/sde
    partitions: []
-   bytes: 20000000000
    name: /dev/sdf
    partitions: []
hostname: four
ipaddr: 192.168.245.4
'''

drive_configuration_simple_iter = [('/dev/sda', 42949672960, False),
                                   ('/dev/sda1', 42941447, False),
                                   ('/dev/sda2', 9999, False),
                                   ('/dev/sdb', 20000000000, True),
                                   ('/dev/sdc', 30000000000, True),
                                   ('/dev/sdd', 20000000000, True),
                                   ('/dev/sde', 20000000000, True),
                                   ('/dev/sdf', 20000000000, True)]
