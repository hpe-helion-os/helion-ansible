
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

The cinder repo will have the following roles:
- CND-VOL
- CND-API
- CND-SCH
- CND-BCK

In time the role names, specified in the configuration processor will change
to: cinder-volume, cinder-api, cinder-scheduler and cinder-backup.

The service verbs are:
- install
- configure
- start
- stop

An example of the cinder-ansible structure:
```
└── cinder-ansible
    ├── filter_plugins
    ├── library
    ├── README.md
    └── roles
        ├── cinder
        │   ├── defaults
        │   ├── files
        │   ├── handlers
        │   ├── meta
        │   ├── tasks
        │   │   └── cinder-deploy.yml
        │   ├── templates
        │   └── vars
        ├── cinder-volume
        │   ├── defaults
        │   ├── files
        │   ├── handlers
        │   ├── meta
        │   ├── tasks
        │   │   ├── configure.yml
        │   │   ├── install.yml
        │   │   └── start.yml
        │   ├── templates
        │   └── vars
        ├── cinder-api
        │   ├── defaults
        │   ├── files
        │   ├── handlers
        │   ├── meta
        │   ├── tasks
        │   │   ├── configure.yml
        │   │   ├── install.yml
        │   │   └── start.yml
        │   ├── templates
        │   └── vars
        ├── cinder-scheduler
        │   ├── defaults
        │   ├── files
        │   ├── handlers
        │   ├── meta
        │   ├── tasks
        │   │   ├── configure.yml
        │   │   ├── install.yml
        │   │   └── start.yml
        │   ├── templates
        │   └── vars
        └── cinder-backup
            ├── defaults
            ├── files
            ├── handlers
            ├── meta
            ├── tasks
            │   ├── configure.yml
            │   ├── install.yml
            │   └── start.yml
            ├── templates
            └── vars
 
```
