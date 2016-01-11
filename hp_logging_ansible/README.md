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
README
======

This repo contains the following roles:
- logging-server: Management for logging server stack
- logging-monitor: Management for monitoring of logging
- logging-producer: Management for logging producer stack

The verbs:
- configure
- install
- status
- start
- stop

The operations:
- deploy
- reconfigure

top-level playbooks
- logging-deploy.yml - deploys centralized logging
- logging-reconfigure.yml - reconfigure centralized logging with new configuration values
- logging-status.yml - check centralized logging services status
- logging-start.yml - start centralized logging services
- logging-stop.yml - stop centralized logging services

