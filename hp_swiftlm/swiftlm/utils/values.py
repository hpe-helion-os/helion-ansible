#!/usr/bin/python

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


import enum
import os


class ServerType(enum.Enum):
    # Using bit shifted values since the value doesnt matter and it could
    # help in the future to show servers that satisfy multiple types.
    object = 1 << 0
    account = 1 << 1
    container = 1 << 2
    proxy = 1 << 3

    @property
    def is_instance(self):
        swift_path = '/opt/stack/service/swift-' + self.name + '-server/etc/'
        return os.path.isfile(swift_path + self.name + '-server.conf')


class Severity(enum.IntEnum):
    # We need to use an IntEnum to dump to JSON/YAML
    ok = 0
    warn = 1
    fail = 2
    unknown = 3

    def __str__(self):
        return str(int(self))

    @staticmethod
    def yaml_repr(dumper, data):
        return dumper.represent_scalar('tag:yaml.org,2002:str', str(data))
