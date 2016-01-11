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

# Given two dictionaries of packages with versions, return a new dict
# containing the set of packages where there is a version difference
# in the two provided sets. Packages not in common between the two sets
# are ignored.


def upgraded_pkgs(before_pkgs, after_pkgs):
  return {k:after_pkgs[k] for k in after_pkgs if\
  (k in before_pkgs and before_pkgs[k]["Version"]!=after_pkgs[k]["Version"])}

class FilterModule(object):

    def filters(self):
        return {'upgraded_pkgs': upgraded_pkgs}
