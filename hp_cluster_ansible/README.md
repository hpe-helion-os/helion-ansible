
(c) Copyright 2015 Hewlett Packard Enterprise Development Company LP

Licensed under the Apache License, Version 2.0 (the "License"); you may
not use this file except in compliance with the License. You may obtain
a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
License for the specific language governing permissions and limitations
under the License.


README
======

This repo contains the following roles:
- FND-CLU: cluster role, which has no tasks but depends on the following two
  roles.
- haproxy: haproxy role
- keepalived: keepalived role
- FND-AP2: Apache role
- cluster-lifecycle: this role is currently empty, save for vars/main.yml

The verbs:
- install
- configure
- start
- stop

The operations:
- deploy

TODO: Separate haproxy, keepalived and FND-AP2 into their own repos
TODO: Rename FND-CLU and FND-AP2 when CP supports non-mnemonic names.

These roles are relatively simple, and are refactored from the kenobi ansible
playbooks.  Two top level playbooks - FND-CLU-deploy.yml and
FND-AP2-deploy.yml - deploy the services.

Repo structure:

```
├── FND-AP2-deploy.yml
├── FND-CLU-deploy.yml
├── README.md
└── roles
    ├── cluster-lifecycle
    │   ├── defaults
    │   │   └── dummy
    │   ├── files
    │   │   └── dummy
    │   ├── handlers
    │   │   └── dummy
    │   ├── meta
    │   │   └── dummy
    │   ├── tasks
    │   ├── templates
    │   │   └── dummy
    │   └── vars
    │       ├── dummy
    │       └── main.yml
    ├── FND-AP2
    │   ├── defaults
    │   │   └── main.yml
    │   └── tasks
    │       ├── configure.yml
    │       ├── install.yml
    │       ├── start.yml
    │       └── stop.yml
    ├── FND-CLU
    │   ├── meta
    │   │   └── main.yml
    │   └── README
    ├── haproxy
    │   ├── files
    │   │   └── enable_nonlocal_binding
    │   ├── README
    │   ├── tasks
    │   │   ├── configure.yml
    │   │   ├── install.yml
    │   │   ├── start.yml
    │   │   └── stop.yml
    │   ├── templates
    │   │   └── haproxy.cfg
    │   └── vars
    │       └── main.yml
    └── keepalived
        ├── tasks
        │   ├── configure.yml
        │   ├── install.yml
        │   ├── start.yml
        │   └── stop.yml
        └── templates
            └── keepalived.conf

```
