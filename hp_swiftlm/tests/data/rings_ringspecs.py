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


ringspec_simple = '''
global:
    all_ring_specifications:
    -   region_name: region1
        rings:
        -   display_name: Account Ring
            min_part_time: 0
            name: account
            partition_power: 17
            replication_policy:
                replica_count: 1
            server_network_group: OBJECT
        -   display_name: Container Ring
            min_part_time: 0
            name: container
            partition_power: 17
            replication_policy:
                replica_count: 2
            server_network_group: OBJECT
        -   default: true
            display_name: General
            min_part_time: 0
            name: object-0
            partition_power: 17
            replication_policy:
                replica_count: 3
            server_network_group: OBJECT
        -   default: false
            display_name: EC
            min_part_time: 0
            name: object-1
            partition_power: 17
            erasure_coding_policy:
                ec_num_data_fragments: 4
                ec_num_parity_fragments: 10
                ec_type: jerasure_rs_vand
                ec_object_segment_size: 1000000
'''

ringspec_region_zones = '''
global:
    all_ring_specifications:
    -   region_name: region1
        swift_regions:
            - id: 2
              rack_ids:
                - 21
                - twotwo
                - two3
            - id: 3
              rack_ids:
                - 31
                - threetwo
                - three3
        rings:
        -   display_name: Account Ring
            min_part_time: 0
            name: account
            partition_power: 17
            replication_policy:
                replica_count: 3
        -   display_name: Container Ring
            min_part_time: 0
            name: container
            partition_power: 17
            replication_policy:
                replica_count: 3
        -   default: true
            display_name: General
            min_part_time: 0
            name: object-0
            partition_power: 17
            replication_policy:
                replica_count: 3

    -   region_name: region2
        swift_regions:
            - id: 4
              rack_ids:
                - four1
                - four2
                - four3
            - id: 5
              rack_ids:
              rack_ids:
                - 51
                - 52
                - 53
            - id: 9
              rack_ids:
                - 91

        swift_zones:
            - id: 6
              rack_ids:
                - four1
                - four2
                - four3
                - 51
                - 52
                - 53
            - id: 10
              rack_ids:
                - 101
        rings:
        -   display_name: Account Ring
            min_part_time: 0
            name: account
            partition_power: 17
            replication_policy:
                replica_count: 3
            server_network_group: OBJECT
        -   display_name: Container Ring
            min_part_time: 0
            name: container
            partition_power: 17
            replication_policy:
                replica_count: 3
            server_network_group: OBJECT
        -   default: true
            swift_zones:
                - id: 7
                  rack_ids:
                    - four1
                    - four2
                    - four3
                - id: 8
                  rack_ids:
                    - 51
                    - 52
                    - 53
            display_name: General
            min_part_time: 0
            name: object-0
            partition_power: 17
            replication_policy:
                replica_count: 3
            server_network_group: OBJECT
'''
