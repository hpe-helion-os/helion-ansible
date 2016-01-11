#
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

def journal_disk_validate(journal_disks, journal_disk_size):
    disk_dict = {}
    unit_gb = 1024 * 1024 * 1024

    for disk in journal_disks:
        disk_name, disk_size = disk.split(":", 1)
        if disk_name:
            cnt = disk_dict[disk_name]['count']+1 if disk_name in disk_dict else 1
            disk_dict[disk_name] = {'size': round(float(disk_size)/unit_gb, 2), 'count': cnt}

    for disk in disk_dict:
        req_size = disk_dict[disk]['count'] * journal_disk_size/float(1024)
        act_size = disk_dict[disk]['size']
        if req_size > act_size:
            return "Journal disk %s does not have the capacity to support requested OSDs (minimum expected size %s GiB, actual size %s GiB)." %(disk, round(req_size,2), act_size)
    return True

class FilterModule(object):
    def filters(self):
        return {'journal_disk_validate': journal_disk_validate}

