
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

The swift repo will have the following roles:
- SWF-PRX
- SWF-CMN
- SWF-ACC
- SWF-CON
- SWF-OBJ

In time the role names, specified in the configuration processor will change
to: swift-proxy, swift-common, swift-account, swift-container and
swift-object.

The service verbs are:
- install
- configure
- start
- stop

An example of the swift-ansible structure:
```
└── swift-ansible
    ├── filter_plugins
    ├── library
    ├── README.md
    └── roles
        ├── swift
        │   ├── defaults
        │   ├── files
        │   ├── handlers
        │   ├── meta
        │   ├── tasks
        │   │   └── swift-deploy.yml
        │   ├── templates
        │   └── vars
        ├── swift-account
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
        ├── swift-common
        │   ├── defaults
        │   ├── files
        │   ├── handlers
        │   ├── meta
        │   ├── tasks
        │   │   ├── configure.yml
        │   │   └── install.yml
        │   ├── templates
        │   └── vars
        ├── swift-container
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
        ├── swift-object
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
        └── swift-proxy
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

Note that the "swift-common" role does not have a "start" verb, since that role
only installs and populates configuration files that are common to the other
Swift roles.

install_package results
-----------------------
The install_package module, used to install the swift and swiftlm venvs and also
create the various swift services, like swift-proxy-server, produces a rather
large result structure that is stored in variables like swift_proxy_install_result.
This result is used to determine  if the package changed, what version is
installed. When called in a loop the result structure also includes the
part of the dictionary used when calling install_package. Here is an example of
the install_package result structure returned for the swift_proxy_server:

{
    "item": {
        "cache": null,
        "changed": false,
        "clean": false,
        "extra_mode_bits": 0,
        "group": "root",
        "invocation": {
            "module_args": "",
            "module_name": "install_package"
        },
        "item": {
            "key": "swift-proxy-server",
            "value": {
                "cmd": "swift-proxy-server",
                "main": true
        },
        "name": "swift",
        "service": "swift-proxy-server",
        "state": "present",
        "version": "20150824T073404Z"
        },
    }
}

