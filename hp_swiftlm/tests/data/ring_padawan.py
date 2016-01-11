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


#
# This file was built using:
#       hlm-input-model/2.0/hp-ci/padawan/ dated 13 July 2015
# ...with one change: the ring-specifications were changed to
# use the MGMT network
#
# How to modify this file:
#
# 1/ Run the (v2) configuration processor with the padawan input model
# 2/ Copy the resulting group_vars/all file into the padawan_input_model
#    variable below.
# 3/ Edit the padawan_net_hosts variable below to contain the hosts
#    listed in net/host.hf
# 4/ Copy the drive_configurations data from osconfig-probe/  and put into
#   the padawan_drive_configurations variable below
# 5/ If the input model has few changes, the expected_cmds variable should
#    be ok. However, any of the followingg changes will require you to update
#    expected_cmds:
#    - changes in ip addresses
#    - changes in device names causes by a change to the input model
#    - changes in weights if the padawan-vagrant is changed
#    The order of the expected_cmds does not matter
#
padawan_input_model = '''

global:
    all_ring_specifications:
    -   region_name: regionone
        swift_zones:
        -   id: 1
            rack_ids:
            -   one
        -   id: 2
            rack_ids:
            -   two
        swift_regions:
        -   id: 9
            rack_ids:
            -   one
            -   two
        rings:
        -   display_name: Account Ring
            min_part_time: 24
            name: account
            partition_power: 17
            replication_policy:
                replica_count: 3
        -   display_name: Container Ring
            min_part_time: 24
            name: container
            partition_power: 17
            replication_policy:
                replica_count: 3
        -   default: true
            display_name: General
            min_part_time: 24
            name: object-0
            partition_power: 17
            replication_policy:
                replica_count: 3
        -   name: object-1
            weight_step: 3.3
            display_name: Extra
            min_part_time: 12
            partition_power: 17
            replication_policy:
                replica_count: 1
    all_servers:
    -   disk_model:
            name: DISK_SET_COMPUTE
            volume_groups:
            -   logical_volumes:
                -   fstype: ext4
                    mount: /
                    name: root
                    size: 35%
                -   fstype: ext4
                    mkfs_opts: -O large_file
                    mount: /var/log
                    name: LV_LOG
                    size: 70%
                -   fstype: ext4
                    mkfs_opts: -O large_file
                    mount: /var/crash
                    name: LV_CRASH
                    size: 30%
                name: vg0
                physical_volumes:
                - /dev/sda1
            -   logical_volumes:
                -   fstype: ext4
                    mkfs_opts: -O large_file
                    mount: /var/lib
                    name: LV_COMPUTE
                    size: 100%
                name: vg-comp
                physical_volumes:
                - /dev/sdb
        name: padawan-ccp-compute0001
        rack: null
        region: regionone
    -   disk_model:
            name: DISK_SET_COMPUTE
            volume_groups:
            -   logical_volumes:
                -   fstype: ext4
                    mount: /
                    name: root
                    size: 35%
                -   fstype: ext4
                    mkfs_opts: -O large_file
                    mount: /var/log
                    name: LV_LOG
                    size: 70%
                -   fstype: ext4
                    mkfs_opts: -O large_file
                    mount: /var/crash
                    name: LV_CRASH
                    size: 30%
                name: vg0
                physical_volumes:
                - /dev/sda1
            -   logical_volumes:
                -   fstype: ext4
                    mkfs_opts: -O large_file
                    mount: /var/lib
                    name: LV_COMPUTE
                    size: 100%
                name: vg-comp
                physical_volumes:
                - /dev/sdb
            # This is put here to test that a compute node (that does not have
            # SWF-ACC, SWF-CON or SWF-OBJ configured, is allowed to have a
            # disk consumed by Swift. See SWIF-2585 for motivation
            # These drives will NOT appear in the rings
            device_groups:
            -   consumer:
                    attrs:
                        rings:
                        - account
                        - container
                        - object-0
                    name: swift
                devices:
                -   name: /dev/sdc
                -   name: /dev/sdd
                name: dummy
        name: padawan-ccp-compute0002
        rack: null
        region: regionone
    -   disk_model:
            name: DISK_SET_COMPUTE
            volume_groups:
            -   logical_volumes:
                -   fstype: ext4
                    mount: /
                    name: root
                    size: 35%
                -   fstype: ext4
                    mkfs_opts: -O large_file
                    mount: /var/log
                    name: LV_LOG
                    size: 70%
                -   fstype: ext4
                    mkfs_opts: -O large_file
                    mount: /var/crash
                    name: LV_CRASH
                    size: 30%
                name: vg0
                physical_volumes:
                - /dev/sda1
            -   logical_volumes:
                -   fstype: ext4
                    mkfs_opts: -O large_file
                    mount: /var/lib
                    name: LV_COMPUTE
                    size: 100%
                name: vg-comp
                physical_volumes:
                - /dev/sdb
        name: padawan-ccp-compute0003
        rack: null
        region: regionone
    -   disk_model:
            device_groups:
            -   consumer:
                    attrs:
                        rings:
                        - account
                        - container
                        - object-0
                    name: swift
                devices:
                -   name: /dev/sdc
                -   name: /dev/sdd
                name: swiftobj
            -   consumer:
                    name: cinder
                devices:
                -   name: /dev/sde
                name: cinder-volume
                # This checks that nothing bad happens when no rings are
                # specified -- it just means that /dev/sdf is not added
                # to any ring
            -   consumer:
                    name: swift
                    attrs:
                       rings: []
                devices:
                -  name: /dev/sdf
                name: notinrings
            name: DISK_SET_CONTROLLER
            volume_groups:
            -   consumer:
                    name: os
                logical_volumes:
                -   fstype: ext4
                    mount: /
                    name: root
                    size: 30%
                -   fstype: ext4
                    mkfs_opts: -O large_file
                    mount: /var/log
                    name: LV_LOG
                    size: 50%
                -   fstype: ext4
                    mkfs_opts: -O large_file
                    mount: /var/crash
                    name: LV_CRASH
                    size: 20%
                name: hlm-vg
                physical_volumes:
                - /dev/sda1
                - /dev/sdb
        name: padawan-ccp-c1-m1-mgmt
        rack: one
        region: regionone
    -   disk_model:
            device_groups:
            -   consumer:
                    attrs:
                        rings:
                        - account
                        - container
                        - object-0
                        - object-1
                    name: swift
                devices:
                -   name: /dev/sdc
                -   name: /dev/sdd
                name: swiftobj
            -   consumer:
                    name: cinder
                devices:
                -   name: /dev/sde
                name: cinder-volume
            name: DISK_SET_CONTROLLER
            volume_groups:
            -   consumer:
                    name: os
                logical_volumes:
                -   fstype: ext4
                    mount: /
                    name: root
                    size: 30%
                -   fstype: ext4
                    mkfs_opts: -O large_file
                    mount: /var/log
                    name: LV_LOG
                    size: 30%
                -   fstype: ext4
                    name: LV_SWFAC
                    size: 20%
                    consumer:
                        name: swift
                        attrs:
                            rings:
                            - name: account
                            - name: container
                -   fstype: ext4
                    mkfs_opts: -O large_file
                    mount: /var/crash
                    name: LV_CRASH
                    size: 20%
                name: hlm-vg
                physical_volumes:
                - /dev/sda_root
                - /dev/sdb
        name: padawan-ccp-c1-m2-mgmt
        rack: one
        region: regionone
    -   disk_model:
            device_groups:
            -   consumer:
                    attrs:
                        rings:
                        - account
                        - container
                        - object-0
                    name: swift
                devices:
                -   name: /dev/sdc
                -   name: /dev/sdd
                name: swiftobj
            -   consumer:
                    name: cinder
                devices:
                -   name: /dev/sde
                name: cinder-volume
            name: DISK_SET_CONTROLLER
            volume_groups:
            -   consumer:
                    name: os
                logical_volumes:
                -   fstype: ext4
                    mount: /
                    name: root
                    size: 30%
                -   fstype: ext4
                    mkfs_opts: -O large_file
                    mount: /var/log
                    name: LV_LOG
                    size: 50%
                -   fstype: ext4
                    name: LV_SWFOBJ
                    size: 10%
                    consumer:
                        name: swift
                        attrs:
                            rings:
                            - name: object-0
                -   fstype: ext4
                    mkfs_opts: -O large_file
                    mount: /var/crash
                    name: LV_CRASH
                    size: 20%
                name: hlm-vg
                physical_volumes:
                - /dev/sda1
                - /dev/sdb
        name: padawan-ccp-c1-m3-mgmt
        rack: two
        region: regionone
    ansible_vars: []
    ntp_servers:
    - ntp.hp.net
    - ntp1aus1.hp.net
    - ntp1aus2.hp.net
    vips:
    - padawan-ccp-vip-LOG-SVR-mgmt
    - padawan-ccp-vip-GLA-REG-mgmt
    - padawan-ccp-vip-HEA-ACW-mgmt
    - padawan-ccp-vip-FND-MDB-mgmt
    - padawan-ccp-vip-HEA-ACF-mgmt
    - padawan-ccp-vip-CND-API-mgmt
    - padawan-ccp-vip-admin-CND-API-mgmt
    - padawan-ccp-vip-GLA-API-mgmt
    - padawan-ccp-vip-MON-API-mgmt
    - padawan-ccp-vip-KEY-API-mgmt
    - padawan-ccp-vip-admin-KEY-API-mgmt
    - padawan-ccp-vip-CEI-API-mgmt
    - padawan-ccp-vip-admin-CEI-API-mgmt
    - padawan-ccp-vip-SWF-PRX-mgmt
    - padawan-ccp-vip-admin-SWF-PRX-mgmt
    - padawan-ccp-vip-FND-IDB-mgmt
    - padawan-ccp-vip-admin-FND-IDB-mgmt
    - padawan-ccp-vip-NEU-SVR-mgmt
    - padawan-ccp-vip-NOV-API-mgmt
    - padawan-ccp-vip-admin-NOV-API-mgmt
    - padawan-ccp-vip-HEA-API-mgmt
    - padawan-ccp-vip-HZN-WEB-mgmt
topology:
    control_planes:
    -   name: ccp
        services:
        -   components:
            -   hosts:
                - padawan-ccp-c1-m3
                - padawan-ccp-c1-m2
                - padawan-ccp-c1-m1
                name: ip-cluster
            -   hosts:
                - padawan-ccp-c1-m3
                - padawan-ccp-c1-m2
                - padawan-ccp-c1-m1
                name: zookeeper
            -   hosts:
                - padawan-ccp-compute0001
                - padawan-ccp-compute0002
                - padawan-ccp-compute0003
                name: nova-kvm
            -   hosts:
                - padawan-ccp-c1-m3
                - padawan-ccp-c1-m2
                - padawan-ccp-c1-m1
                name: cinder-client
            -   hosts:
                - padawan-ccp-c1-m3
                - padawan-ccp-c1-m2
                - padawan-ccp-c1-m1
                name: heat-client
            -   hosts:
                - padawan-ccp-c1-m3
                - padawan-ccp-c1-m2
                - padawan-ccp-c1-m1
                - padawan-ccp-compute0001
                - padawan-ccp-compute0002
                - padawan-ccp-compute0003
                name: stunnel
            -   hosts:
                - padawan-ccp-c1-m3
                - padawan-ccp-c1-m2
                - padawan-ccp-c1-m1
                name: swift-client
            -   hosts:
                - padawan-ccp-c1-m3
                - padawan-ccp-c1-m2
                - padawan-ccp-c1-m1
                name: rabbitmq
            -   hosts:
                - padawan-ccp-c1-m3
                - padawan-ccp-c1-m2
                - padawan-ccp-c1-m1
                name: apache2
            -   hosts:
                - padawan-ccp-c1-m3
                - padawan-ccp-c1-m2
                - padawan-ccp-c1-m1
                name: influxdb
            -   hosts:
                - padawan-ccp-c1-m3
                - padawan-ccp-c1-m2
                - padawan-ccp-c1-m1
                name: openstack-client
            -   hosts:
                - padawan-ccp-c1-m3
                - padawan-ccp-c1-m2
                - padawan-ccp-c1-m1
                name: neutron-client
            -   hosts:
                - padawan-ccp-c1-m3
                - padawan-ccp-c1-m2
                - padawan-ccp-c1-m1
                name: storm
            -   hosts:
                - padawan-ccp-c1-m3
                - padawan-ccp-c1-m2
                - padawan-ccp-c1-m1
                name: mysql
            -   hosts:
                - padawan-ccp-c1-m3
                - padawan-ccp-c1-m2
                - padawan-ccp-c1-m1
                name: kafka
            -   hosts:
                - padawan-ccp-c1-m3
                - padawan-ccp-c1-m2
                - padawan-ccp-c1-m1
                name: glance-client
            -   hosts:
                - padawan-ccp-c1-m3
                - padawan-ccp-c1-m2
                - padawan-ccp-c1-m1
                name: ceilometer-client
            -   hosts:
                - padawan-ccp-c1-m3
                - padawan-ccp-c1-m2
                - padawan-ccp-c1-m1
                name: keystone-client
            -   hosts:
                - padawan-ccp-c1-m3
                - padawan-ccp-c1-m2
                - padawan-ccp-c1-m1
                name: nova-client
            -   hosts:
                - padawan-ccp-compute0001
                - padawan-ccp-compute0002
                - padawan-ccp-compute0003
                name: neutron-lbaas-agent
            name: foundation
        -   components:
            -   hosts:
                - padawan-ccp-c1-m3
                - padawan-ccp-c1-m2
                - padawan-ccp-c1-m1
                name: ceilometer-collector
            -   hosts:
                - padawan-ccp-c1-m3
                - padawan-ccp-c1-m2
                - padawan-ccp-c1-m1
                name: ceilometer-api
            -   hosts:
                - padawan-ccp-c1-m3
                - padawan-ccp-c1-m2
                - padawan-ccp-c1-m1
                name: ceilometer-expirer
            -   hosts:
                - padawan-ccp-c1-m3
                - padawan-ccp-c1-m2
                - padawan-ccp-c1-m1
                name: ceilometer-common
            -   hosts:
                - padawan-ccp-c1-m3
                - padawan-ccp-c1-m2
                - padawan-ccp-c1-m1
                name: ceilometer-agent-notification
            -   hosts:
                - padawan-ccp-c1-m3
                - padawan-ccp-c1-m2
                - padawan-ccp-c1-m1
                name: ceilometer-agent-central
            name: ceilometer
        -   components:
            -   hosts:
                - padawan-ccp-c1-m3
                - padawan-ccp-c1-m2
                - padawan-ccp-c1-m1
                - padawan-ccp-compute0001
                - padawan-ccp-compute0002
                - padawan-ccp-compute0003
                name: logging-producer
            -   hosts:
                - padawan-ccp-c1-m3
                - padawan-ccp-c1-m2
                - padawan-ccp-c1-m1
                name: logging-server
            name: logging
        -   components:
            -   hosts:
                - padawan-ccp-c1-m3
                - padawan-ccp-c1-m2
                - padawan-ccp-c1-m1
                name: monasca-persister
            -   hosts:
                - padawan-ccp-c1-m3
                - padawan-ccp-c1-m2
                - padawan-ccp-c1-m1
                - padawan-ccp-compute0001
                - padawan-ccp-compute0002
                - padawan-ccp-compute0003
                name: monasca-agent
            -   hosts:
                - padawan-ccp-c1-m3
                - padawan-ccp-c1-m2
                - padawan-ccp-c1-m1
                name: monasca-threshold
            -   hosts:
                - padawan-ccp-c1-m3
                - padawan-ccp-c1-m2
                - padawan-ccp-c1-m1
                name: monasca-api
            -   hosts:
                - padawan-ccp-c1-m3
                - padawan-ccp-c1-m2
                - padawan-ccp-c1-m1
                name: monasca-notifier
            name: monasca
        -   components:
            -   hosts:
                - padawan-ccp-c1-m3
                - padawan-ccp-c1-m2
                - padawan-ccp-c1-m1
                name: nova-console-auth
            -   hosts:
                - padawan-ccp-c1-m3
                - padawan-ccp-c1-m2
                - padawan-ccp-c1-m1
                name: nova-novncproxy
            -   hosts:
                - padawan-ccp-compute0001
                - padawan-ccp-compute0002
                - padawan-ccp-compute0003
                name: nova-compute
            -   hosts:
                - padawan-ccp-c1-m3
                - padawan-ccp-c1-m2
                - padawan-ccp-c1-m1
                name: nova-conductor
            -   hosts:
                - padawan-ccp-c1-m3
                - padawan-ccp-c1-m2
                - padawan-ccp-c1-m1
                name: nova-api
            -   hosts:
                - padawan-ccp-c1-m3
                - padawan-ccp-c1-m2
                - padawan-ccp-c1-m1
                name: nova-scheduler
            name: nova
        -   components:
            -   hosts:
                - padawan-ccp-c1-m3
                - padawan-ccp-c1-m2
                - padawan-ccp-c1-m1
                name: heat-api-cfn
            -   hosts:
                - padawan-ccp-c1-m3
                - padawan-ccp-c1-m2
                - padawan-ccp-c1-m1
                name: heat-engine
            -   hosts:
                - padawan-ccp-c1-m3
                - padawan-ccp-c1-m2
                - padawan-ccp-c1-m1
                name: heat-api
            -   hosts:
                - padawan-ccp-c1-m3
                - padawan-ccp-c1-m2
                - padawan-ccp-c1-m1
                name: heat-api-cloudwatch
            name: heat
        -   components:
            -   hosts:
                - padawan-ccp-c1-m3
                - padawan-ccp-c1-m2
                - padawan-ccp-c1-m1
                name: keystone-api
            name: keystone
        -   components:
            -   hosts:
                - padawan-ccp-c1-m3
                - padawan-ccp-c1-m2
                - padawan-ccp-c1-m1
                name: horizon
            name: horizon
        -   components:
            -   hosts:
                - padawan-ccp-c1-m3
                - padawan-ccp-c1-m2
                - padawan-ccp-c1-m1
                name: cinder-backup
            -   hosts:
                - padawan-ccp-c1-m3
                - padawan-ccp-c1-m2
                - padawan-ccp-c1-m1
                name: cinder-api
            -   hosts:
                - padawan-ccp-c1-m3
                - padawan-ccp-c1-m2
                - padawan-ccp-c1-m1
                name: cinder-volume
            -   hosts:
                - padawan-ccp-c1-m3
                - padawan-ccp-c1-m2
                - padawan-ccp-c1-m1
                name: cinder-scheduler
            name: cinder
        -   components:
            -   hosts:
                - padawan-ccp-c1-m3
                - padawan-ccp-c1-m2
                - padawan-ccp-c1-m1
                name: glance-api
            -   hosts:
                - padawan-ccp-c1-m3
                - padawan-ccp-c1-m2
                - padawan-ccp-c1-m1
                name: glance-registry
            name: glance
        -   components:
            -   hosts:
                - padawan-ccp-c1-m3
                - padawan-ccp-c1-m2
                - padawan-ccp-c1-m1
                name: swift-proxy
            -   hosts:
                - padawan-ccp-c1-m3
                - padawan-ccp-c1-m2
                - padawan-ccp-c1-m1
                name: swift-account
            -   hosts:
                - padawan-ccp-c1-m3
                - padawan-ccp-c1-m2
                - padawan-ccp-c1-m1
                name: swift-container
            -   hosts:
                - padawan-ccp-c1-m3
                - padawan-ccp-c1-m2
                - padawan-ccp-c1-m1
                name: swift-object
            name: swift
        -   components:
            -   hosts:
                - padawan-ccp-c1-m3
                - padawan-ccp-c1-m2
                - padawan-ccp-c1-m1
                name: neutron-ml2-plugin
            -   hosts:
                - padawan-ccp-c1-m3
                - padawan-ccp-c1-m2
                - padawan-ccp-c1-m1
                name: neutron-server
            -   hosts:
                - padawan-ccp-c1-m3
                - padawan-ccp-c1-m2
                - padawan-ccp-c1-m1
                - padawan-ccp-compute0001
                - padawan-ccp-compute0002
                - padawan-ccp-compute0003
                name: neutron-openvswitch-agent
            -   hosts:
                - padawan-ccp-c1-m3
                - padawan-ccp-c1-m2
                - padawan-ccp-c1-m1
                - padawan-ccp-compute0001
                - padawan-ccp-compute0002
                - padawan-ccp-compute0003
                name: neutron-metadata-agent
            -   hosts:
                - padawan-ccp-c1-m3
                - padawan-ccp-c1-m2
                - padawan-ccp-c1-m1
                name: neutron-dhcp-agent
            -   hosts:
                - padawan-ccp-c1-m3
                - padawan-ccp-c1-m2
                - padawan-ccp-c1-m1
                - padawan-ccp-compute0001
                - padawan-ccp-compute0002
                - padawan-ccp-compute0003
                name: neutron-l3-agent
            name: neutron
    name: padawan
'''

padawan_net_hosts = [
    '192.168.245.2           padawan-ccp-c1-m3-mgmt',
    '192.168.222.2           padawan-ccp-c1-m3-obj',
    '192.168.245.3           padawan-ccp-c1-m2-mgmt',
    '192.168.222.3           padawan-ccp-c1-m2-obj',
    '192.168.245.4           padawan-ccp-c1-m1-mgmt',
    '192.168.222.4           padawan-ccp-c1-m1-obj',
    '192.168.245.5           padawan-ccp-compute0001',
    '192.168.245.5           padawan-ccp-compute0001-mgmt',
    '192.168.245.6           padawan-ccp-compute0002',
    '192.168.245.6           padawan-ccp-compute0002-mgmt',
    '192.168.245.7           padawan-ccp-compute0003',
    '192.168.245.7           padawan-ccp-compute0003-mgmt',
    '192.168.245.8           padawan-ccp-vip-LOG-SVR-mgmt',
    '192.168.245.8           padawan-ccp-vip-admin-SWF-PRX-mgmt']


host_list_acc = [
    {'host': 'padawan-ccp-c1-m3-mgmt', 'port': '6002', 'use_tls': False},
    {'host': 'padawan-ccp-c1-m2-mgmt', 'port': '6002', 'use_tls': False},
    {'host': 'padawan-ccp-c1-m1-mgmt', 'port': '6002', 'use_tls': False}
]

host_list_con = [
    {'host': 'padawan-ccp-c1-m3-mgmt', 'port': '6001', 'use_tls': False},
    {'host': 'padawan-ccp-c1-m2-mgmt', 'port': '6001', 'use_tls': False},
    {'host': 'padawan-ccp-c1-m1-mgmt', 'port': '6001', 'use_tls': False}
]

# Note: put objects on -obj network (to exercise ip address resolution
host_list_obj = [
    {'host': 'padawan-ccp-c1-m3-obj', 'port': '6000', 'use_tls': False},
    {'host': 'padawan-ccp-c1-m2-obj', 'port': '6000', 'use_tls': False},
    {'host': 'padawan-ccp-c1-m1-obj', 'port': '6000', 'use_tls': False}
]

padawan_swf_rng_consumes = {
    'consumes_SWF_ACC': {'members': {'private': host_list_acc}},
    'consumes_SWF_CON': {'members': {'private': host_list_con}},
    'consumes_SWF_OBJ': {'members': {'private': host_list_obj}}
}

padawan_drive_configurations = '''
hlm_drive_configuration:

-   drives:
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
        -   bytes: 20000000000
            partition: sdb1
    -   bytes: 20000000000
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
    hostname: padawan-ccp-c1-m1
    ipaddr: 192.168.245.4


-   drives:
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
        -   bytes: 20000000000
            partition: sdb1
    -   bytes: 20000000000
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
    hostname: padawan-ccp-c1-m2
    ipaddr: 192.168.245.3

-   drives:
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
        -   bytes: 20000000000
            partition: sdb1
    -   bytes: 20000000000
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
    hostname: padawan-ccp-c1-m3
    ipaddr: 192.168.245.2
'''

expected_cmds = [
    'swift-ring-builder /tmp/newrings/region-regionone/container.builder'
    ' create 17 3.0 24',
    'swift-ring-builder /tmp/newrings/region-regionone/object-0.builder '
    ' create 17 3.0 24',
    'swift-ring-builder /tmp/newrings/region-regionone/account.builder'
    ' create 17 3.0 24',
    'swift-ring-builder /tmp/newrings/region-regionone/object-1.builder'
    ' create 17 1.0 12',
    'swift-ring-builder /tmp/newrings/region-regionone/account.builder add'
    ' --region 9 --zone 2 --ip 192.168.245.2 --port 6002'
    ' --replication-port 6002 --replication-ip 192.168.245.2 --device disk0'
    ' --meta padawan-ccp-c1-m3:disk0:/dev/sdc --weight 18.63',
    'swift-ring-builder /tmp/newrings/region-regionone/account.builder add'
    ' --region 9 --zone 2 --ip 192.168.245.2 --port 6002'
    ' --replication-port 6002 --replication-ip 192.168.245.2 --device disk1'
    ' --meta padawan-ccp-c1-m3:disk1:/dev/sdd --weight 18.63',
    'swift-ring-builder /tmp/newrings/region-regionone/account.builder add'
    ' --region 9 --zone 1 --ip 192.168.245.3 --port 6002'
    ' --replication-port 6002 --replication-ip 192.168.245.3 --device disk0'
    ' --meta padawan-ccp-c1-m2:disk0:/dev/sdc --weight 18.63',
    'swift-ring-builder /tmp/newrings/region-regionone/account.builder add'
    ' --region 9 --zone 1 --ip 192.168.245.3 --port 6002'
    ' --replication-port 6002 --replication-ip 192.168.245.3 --device disk1'
    ' --meta padawan-ccp-c1-m2:disk1:/dev/sdd --weight 18.63',
    'swift-ring-builder /tmp/newrings/region-regionone/account.builder add'
    ' --region 9 --zone 1 --ip 192.168.245.4 --port 6002'
    ' --replication-port 6002 --replication-ip 192.168.245.4 --device disk0'
    ' --meta padawan-ccp-c1-m1:disk0:/dev/sdc --weight 18.63',
    'swift-ring-builder /tmp/newrings/region-regionone/account.builder add'
    ' --region 9 --zone 1 --ip 192.168.245.4 --port 6002'
    ' --replication-port 6002 --replication-ip 192.168.245.4 --device disk1'
    ' --meta padawan-ccp-c1-m1:disk1:/dev/sdd --weight 18.63',
    'swift-ring-builder /tmp/newrings/region-regionone/container.builder add'
    ' --region 9 --zone 2 --ip 192.168.245.2 --port 6001'
    ' --replication-port 6001 --replication-ip 192.168.245.2 --device disk0'
    ' --meta padawan-ccp-c1-m3:disk0:/dev/sdc --weight 18.63',
    'swift-ring-builder /tmp/newrings/region-regionone/container.builder add'
    ' --region 9 --zone 2 --ip 192.168.245.2 --port 6001'
    ' --replication-port 6001 --replication-ip 192.168.245.2 --device disk1'
    ' --meta padawan-ccp-c1-m3:disk1:/dev/sdd --weight 18.63',
    'swift-ring-builder /tmp/newrings/region-regionone/container.builder add'
    ' --region 9 --zone 1 --ip 192.168.245.3 --port 6001'
    ' --replication-port 6001 --replication-ip 192.168.245.3 --device disk0'
    ' --meta padawan-ccp-c1-m2:disk0:/dev/sdc --weight 18.63',
    'swift-ring-builder /tmp/newrings/region-regionone/container.builder add'
    ' --region 9 --zone 1 --ip 192.168.245.3 --port 6001'
    ' --replication-port 6001 --replication-ip 192.168.245.3 --device disk1'
    ' --meta padawan-ccp-c1-m2:disk1:/dev/sdd --weight 18.63',
    'swift-ring-builder /tmp/newrings/region-regionone/container.builder add'
    ' --region 9 --zone 1 --ip 192.168.245.4 --port 6001'
    ' --replication-port 6001 --replication-ip 192.168.245.4 --device disk0'
    ' --meta padawan-ccp-c1-m1:disk0:/dev/sdc --weight 18.63',
    'swift-ring-builder /tmp/newrings/region-regionone/container.builder add'
    ' --region 9 --zone 1 --ip 192.168.245.4 --port 6001'
    ' --replication-port 6001 --replication-ip 192.168.245.4 --device disk1'
    ' --meta padawan-ccp-c1-m1:disk1:/dev/sdd --weight 18.63',
    'swift-ring-builder /tmp/newrings/region-regionone/object-0.builder add'
    ' --region 9 --zone 2 --ip 192.168.222.2 --port 6000'
    ' --replication-port 6000 --replication-ip 192.168.222.2 --device disk0'
    ' --meta padawan-ccp-c1-m3:disk0:/dev/sdc --weight 18.63',
    'swift-ring-builder /tmp/newrings/region-regionone/object-0.builder add'
    ' --region 9 --zone 2 --ip 192.168.222.2 --port 6000'
    ' --replication-port 6000 --replication-ip 192.168.222.2 --device disk1'
    ' --meta padawan-ccp-c1-m3:disk1:/dev/sdd --weight 18.63',
    'swift-ring-builder /tmp/newrings/region-regionone/object-0.builder add'
    ' --region 9 --zone 1 --ip 192.168.222.3 --port 6000'
    ' --replication-port 6000 --replication-ip 192.168.222.3 --device disk0'
    ' --meta padawan-ccp-c1-m2:disk0:/dev/sdc --weight 18.63',
    'swift-ring-builder /tmp/newrings/region-regionone/object-0.builder add'
    ' --region 9 --zone 1 --ip 192.168.222.3 --port 6000'
    ' --replication-port 6000 --replication-ip 192.168.222.3 --device disk1'
    ' --meta padawan-ccp-c1-m2:disk1:/dev/sdd --weight 18.63',
    'swift-ring-builder /tmp/newrings/region-regionone/object-0.builder add'
    ' --region 9 --zone 1 --ip 192.168.222.4 --port 6000'
    ' --replication-port 6000 --replication-ip 192.168.222.4 --device disk0'
    ' --meta padawan-ccp-c1-m1:disk0:/dev/sdc --weight 18.63',
    'swift-ring-builder /tmp/newrings/region-regionone/object-0.builder add'
    ' --region 9 --zone 1 --ip 192.168.222.4 --port 6000'
    ' --replication-port 6000 --replication-ip 192.168.222.4 --device disk1'
    ' --meta padawan-ccp-c1-m1:disk1:/dev/sdd --weight 18.63',
    'swift-ring-builder /tmp/newrings/region-regionone/object-1.builder add'
    ' --region 9 --zone 1 --ip 192.168.222.3 --port 6000'
    ' --replication-port 6000 --replication-ip 192.168.222.3 --device disk0'
    ' --meta padawan-ccp-c1-m2:disk0:/dev/sdc --weight 3.30',
    'swift-ring-builder /tmp/newrings/region-regionone/object-1.builder add'
    ' --region 9 --zone 1 --ip 192.168.222.3 --port 6000'
    ' --replication-port 6000 --replication-ip 192.168.222.3 --device disk1'
    ' --meta padawan-ccp-c1-m2:disk1:/dev/sdd --weight 3.30',
    'swift-ring-builder /tmp/newrings/account.builder add'
    ' --region 9 --zone 1 --ip 192.168.245.3 --port 6002'
    ' --replication-port 6002 --replication-ip 192.168.245.3 --device lvm0'
    ' --meta padawan-ccp-c1-m2:lvm0:/dev/hlm-vg/LV_SWFAC --weight 11.73',
    'swift-ring-builder /tmp/newrings/container.builder add'
    ' --region 9 --zone 1 --ip 192.168.245.3 --port 6001'
    ' --replication-port 6001 --replication-ip 192.168.245.3 --device lvm0'
    ' --meta padawan-ccp-c1-m2:lvm0:/dev/hlm-vg/LV_SWFAC --weight 11.73',
    'swift-ring-builder /tmp/newrings/object-0.builder add'
    ' --region 9 --zone 2 --ip 192.168.222.2 --port 6000'
    ' --replication-port 6000 --replication-ip 192.168.222.2 --device lvm0'
    ' --meta padawan-ccp-c1-m3:lvm0:/dev/hlm-vg/LV_SWFOBJ --weight 1.87',
    'swift-ring-builder /tmp/newrings/region-regionone/object-0.builder'
    ' rebalance 999',
    'swift-ring-builder /tmp/newrings/region-regionone/container.builder'
    ' rebalance 999',
    'swift-ring-builder /tmp/newrings/region-regionone/account.builder'
    ' rebalance 999',
    'swift-ring-builder /tmp/newrings/region-regionone/object-1.builder'
    ' rebalance 999'
]

# NOTE: region and zone set to 1, rack id should match input model
expected_lv_devices = [
    {'region_name': 'regionone', 'rack_id': 'one', 'region_id': 1,
     'zone_id': 1,
     'server_name': 'padawan-ccp-c1-m2', 'server_ip': '192.168.245.3',
     'server_bind_port': '6002', 'replication_ip': '192.168.245.3',
     'replication_bind_port': '6002',
     'swift_drive_name': 'lvm0', 'device_name': '/dev/hlm-vg/LV_SWFAC',
     'meta': 'padawan-ccp-c1-m2:lvm0:/dev/hlm-vg/LV_SWFAC',
     'ring_name': 'account', 'group_type': 'lvm', 'presence': 'present',
     'block_devices': {'percent': '20%',
                       'physicals': ['/dev/sda_root', '/dev/sdb']}},
    {'region_name': 'regionone', 'rack_id': 'one', 'region_id': 1,
     'zone_id': 1,
     'server_name': 'padawan-ccp-c1-m2', 'server_ip': '192.168.245.3',
     'server_bind_port': '6001', 'replication_ip': '192.168.245.3',
     'replication_bind_port': '6001',
     'swift_drive_name': 'lvm0', 'device_name': '/dev/hlm-vg/LV_SWFAC',
     'meta': 'padawan-ccp-c1-m2:lvm0:/dev/hlm-vg/LV_SWFAC',
     'ring_name': 'container', 'group_type': 'lvm', 'presence': 'present',
     'block_devices': {'percent': '20%',
                       'physicals': ['/dev/sda_root', '/dev/sdb']}},
    {'region_name': 'regionone', 'rack_id': 'two', 'region_id': 1,
     'zone_id': 1,
     'server_name': 'padawan-ccp-c1-m3', 'server_ip': '192.168.222.2',
     'server_bind_port': '6000', 'replication_ip': '192.168.222.2',
     'replication_bind_port': '6000',
     'swift_drive_name': 'lvm0', 'device_name': '/dev/hlm-vg/LV_SWFOBJ',
     'meta': 'padawan-ccp-c1-m3:lvm0:/dev/hlm-vg/LV_SWFOBJ',
     'ring_name': 'object-0', 'group_type': 'lvm', 'presence': 'present',
     'block_devices': {'percent': '10%',
                       'physicals': ['/dev/sda1', '/dev/sdb']}}
]
