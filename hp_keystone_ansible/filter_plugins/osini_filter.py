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
# Creates a list of tuples from the dictionary

def ini_tuple(config_entries):
    config_tuples  = list()
    for section in config_entries:
        for option in sorted(config_entries[section]):
            #config_tuples.append(item0, item1, config_entries[item0][item1])
            config_tuples.append( dict(section=section,
                                option=option,
                                value=config_entries[section][option]
                                )
                           )
    return config_tuples


class FilterModule(object):

    def filters(self):
        return {'osini': ini_tuple}
