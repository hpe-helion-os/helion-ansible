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
# Takes list of ansible stat results and returns item(hostname) if file exists
# in that host


def one_from_list(results, return_nested_item=False):
    for result in results:
        if 'stat' in result and result['stat']['exists']:
            return result['item']['item'] if return_nested_item \
                else result['item']


class FilterModule(object):
    def filters(self):
        return {'one_from_list': one_from_list}
