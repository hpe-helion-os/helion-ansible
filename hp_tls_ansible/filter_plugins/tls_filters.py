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
# Set of filters for TLS playbooks

# Get a list of certificate names and return a unique list

def get_cert_files(d):
    ret = list()
    for service in d.keys():
        if 'networks' in d[service].keys():
            for network in d[service]['networks']:
                if 'cert_file' in network.keys():
                    ret.append(network['cert_file'])
    return list(set(ret))

class FilterModule(object):

    def filters(self):
        return {'get_cert_files': get_cert_files}

