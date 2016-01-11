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


output1 = (
    "drive-audit: Devices found: ["
    "{'block_device': '/dev/sdc1', "
    "'major': '8', "
    "'mount_point': '/srv/node/sdc1', "
    "'kernel_device': 'sdc1', "
    "'minor': '50'},"
    "{'block_device': '/dev/sdd1', "
    "'major': '8', "
    "'mount_point': '/srv/node/sdd1', "
    "'kernel_device': 'sdd1', "
    "'minor': '49'}]\n"
    "drive-audit: Errors found: {}\n"
    "drive-audit: No drives were unmounted\n"
)

output2 = """drive-audit: Devices found: []
drive-audit: Error: No devices found!
drive-audit: Errors found: {'sdd': 6, 'sdb': 1032}
drive-audit: No drives were unmounted"""

# errors found on 2 out of 3 devices
output3 = (
    "drive-audit: Devices found: ["
    "{'block_device': '/dev/sdb1', "
    "'major': '8', "
    "'mount_point': '/srv/node/sdb1', "
    "'kernel_device': 'sdb1', "
    "'minor': '49'},"
    "{'block_device': '/dev/sdc1', "
    "'major': '8', "
    "'mount_point': '/srv/node/sdc1', "
    "'kernel_device': 'sdc1', "
    "'minor': '50'},"
    "{'block_device': '/dev/sdd1', "
    "'major': '8', "
    "'mount_point': '/srv/node/sdd1', "
    "'kernel_device': 'sdd1', "
    "'minor': '51'}]\n"
    "drive-audit: Errors found: {'sdd': 3, 'sdb1':"
    "20, 'sdd1': 2, 'sdb': 516}\n"
    "drive-audit: No drives were unmounted\n"
)
