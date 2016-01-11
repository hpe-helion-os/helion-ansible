#!/bin/bash
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

# this script runs the logging-test playbook to simulate service log (JSON) growth
set -x

# Get the count from command line. If not provided, use a default
log_times=${1:-10}
for i in `seq $log_times`; do
  ansible-playbook -i hosts/verb_hosts logging-test.yml -e log_message=msg_$i
done
set +x

