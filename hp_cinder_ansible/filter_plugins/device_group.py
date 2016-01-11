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
# Usage :
#   {device_groups:[{name:N1, consumer:C1, ...},
#                   {name:N2, consumer:C2, ...},
#                   ...]} | device_group(N2, C2)
#     => {name:N2, consumer:C2, ...}


def device_group(data, dg_name, dg_consumer):
    output = None
    for dg in data.get("device_groups", []):
        # skip if doesn't match require name
        name = dg.get("name")
        if not name or name != dg_name:
            continue

        # skip if doesn't have a consumer entry
        consumer = dg.get("consumer")
        if not consumer:
            continue

        # skip if consumer name doesn't match required consumer
        consumer_name = consumer.get("name")
        if not consumer_name or consumer_name != dg_consumer:
            continue

        # found a matching device group, so return it
        output = dg
        break
    return output


class FilterModule(object):
    def filters(self):
        return {'device_group': device_group}
