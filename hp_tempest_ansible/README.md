
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

This repo holds ansible playbooks to deploy, configure and run tempest
within Helion OpenStack, version 2.0 and further.

Tempest is deployed within its own virtualenv in the deployer VM, and it
can be run from there at any time, by standing up the deployer.

The tempest tests embedded in HOS serve multiple purposes:

- running tempest as part of our CI
- running targeted tests as part of the developer workflow
- professional services and customers to run tests to validate their cloud,
  after install or update
  
There are several tasks associated with tests:
  
- install: deploy tempest and run-time dependencies on the target
- test-environment: read cloud status before tests. This can be used to:
    - discover resources that can be used for testing
    - mark resources that should not be clean-ed up after the test run
    - collect details about the system under test, such as the version number,
      the number of nodes, important configuration flags, etc
- test-resources: provision any test resource which is required prior to the
  execution of the tests. This may include test accounts, images, flavours,
  networks, etc. 
- configure: 
    - create folders for test data and results
    - setup OS users to run the tests
    - create test configuration files
    - prepare tests so that all relevant logs and results will end up on a
      dedicated folder - which is useful for CI to archive logs and results
    - verify the configuration
- run: run the tests, generate test results
- cleanup: restore - as much as possible - the status of the cloud before the
  test run. This step can probably be skipped in CI, but it's useful when
  running the tests against a longer-life test system or a production deployment

Much of the structure of these repos is imposed by Ansible.  For further
information on Ansible see <http://www.ansible.com/home> and in particular
the documentation at <http://docs.ansible.com/>.  At a high-level, the
structure is as follows:


```
└── tempest-ansible
    ├── filter_plugins
    ├── library
    ├── tempest-run.yml
    ├── tempest-deploy.yml
    └── roles
        ├── TPS-TST
        │   ├── defaults
        │   ├── files
        │   ├── handlers
        │   ├── meta
        │   ├── tasks
        │   │   ├── configure.yml
        │   │   ├── install.yml
        │   │   ├── test-resources.yml
        │   │   ├── run.yml
        │   │   └── cleanup.yml
        │   ├── templates
        │   └── vars
        │       └── main.yml
