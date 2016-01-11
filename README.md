
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


# hpe-helion-os project

This project contains the Ansible playbooks, cloud topology and service definition
models, and configuration processing engine that comprise HPE's HOS v2.0 product.
We are making this source available for the community to examine and share.  It is also
possible to run the configuration processing engine against the various input
models.  We will update this project as new releases of HOS become available.  We
will also post tooling to allow the community to build a virtual cloud and
exercise the Ansible playbooks at a later date.

We welcome feedback and comments, which can be addressed to <helion-os@groups.ext.hpe.com>.

The basic architecture of the HOS v2.0 product is as follows:

1. A cloud topology and service definition contained in helion-input-model is
2. Processed by the configuration processing engine in helion-configuration-processor
to produce
3. Ansible inputs that are consumed by the playbooks in helion-ansible to deploy a
working cloud.

## helion-input-model

This repository contains cloud topology and service definitions that are processed by
helion-configuration-processor.  The basic structure of the repo is as follows:

```
└── 2.0
    ├── examples
    │   ├── entry-scale-esx
    │   │   └── data
    │   │       └── swift
    │   ├── entry-scale-kvm-ceph
    │   │   └── data
    │   │       └── swift
    │   ├── entry-scale-kvm-vsa
    │   │   └── data
    │   │       └── swift
    │   └── entry-scale-swift
    │       └── data
    │           └── swift
    ├── services
    │   ├── ceilometer
    │   ├── ceph
    │   ├── cinder
    │   ├── freezer
    │   ├── glance
    │   ├── heat
    │   ├── icinga
    │   ├── ironic
    │   ├── keystone
    │   ├── logging
    │   ├── magnum
    │   ├── monasca
    │   ├── neutron
    │   ├── nova
    │   ├── ntp
    │   ├── operations
    │   └── swift
    └── tech-preview
        └── mid-scale
            └── data
                └── swift
```


The "2.0" refers to the version of input model.  The model inputs are of two basic kinds:

- Cloud topology inputs (logical and physical cloud architecture) contained in "examples"
and "tech-preview"
- Service inputs (Swift, Nova, etc.) contained in "services"

The Service inputs are relatively static and describe such things as the name of the service
or service component, inter-service variables such as passwords, service interdependencies,
and VIP endpoints if needed along with their properties.  On the other hand the cloud topology
inputs which describe the logical and physical structure of the cloud can vary considerably.
They describe the size and shape of the cloud onto which you deploy the various services -
for example what region(s) the cloud has, which services run in which region, which services
are co-located, what servers and networks are to be used.

For more information on the input model please see [here](http://docs.hpcloud.com/#helion/input_model.html)

## helion-configuration-processor

This repository contains the source of the configuration processing engine that takes the
cloud topology and service definitions in helion-input-model and produces Ansible variables
that are consumed by the playbooks in helion-ansible.  The aim of the configuration processing
engine is to remove the need for built-in knowledge of the cloud toplogy from the service
definitions (provided in its inputs) and the Ansible playbooks. The configuration processor
generates a set of Ansible artefacts - hosts files, group\_vars files and host\_vars files:

- The hosts files contain hostgroups for each service-component (e.g.
nova-api, nova-scheduler, etc.) - this allows each service to determine the
list of hosts where the service-component is to be installed.

- The vars files contain the server specific configuration values for each
service. The vars generated in host\_vars and group\_vars are derived from the
service-component names defined in the inputs to CP, so these must match the
relevant variable references used in the helion-ansible repo.

### Configuration processor stages

The processing progresses through a number of distinct phases.  These are:

- **Input Process:**  The topology and service definition inputs are read
- **Validation Process:**  The topology inputs are validated, i.e. checked for errors. As part
of this process the inputs are checked against defined Schema.
- **Model Creation Process:**  Internal data structures are created
- **Controller Processor:**  Internal helper functions are initialised
- **CleanUpStage Process:**  The "staging" area that contains the Ansible outputs and other
outputs is cleared
- **Migration Process:**  Some legacy keywords in the inputs are migrated to their current
values
- **Generate Process:**  The various inputs are processed to produce an internal representation
of the cloud that has been specified
- **Build Process:** Various outputs are generated based on the internal cloud representation.
These outputs include:
    - An Ansible hosts file (verb\_hosts) that describes the various server groups assigned to services
    - An Ansible group\_vars/ directory that contains service definitions for server groups
    - An Ansible host\_vars/ directory that contains per-server definitions
    - Various networking and server information files
    - An ascii pictorial representation of the cloud "CloudDiagram.txt"
    - The "persistent state", namely generated "private\_data" (mostly passwords), ip addresses and
server allocations.  This state ensures continuity between successive runs of the configuration
processor.
- **Explainer Process:**  Produces a file "explain.txt" that provides some detail on the server
allocation and network configuration decisions that the configuration processor has made.
- **Finalizer Process:**  Produces some additional output - information files including dumps of
internal data structures which can be useful when developing and debugging.

A list of the information files produced by the configuration processor along with descriptions
of their contents can be found [here](http://docs.hpcloud.com/#helion/input_model.html#input_model__cpinfofiles).


### Configuration processor repo structure

The basic structure of the repo is as follows:

```
├── ConfigurationProcessor
│   ├── helion_configurationprocessor
│   │   ├── cp
│   │   │   ├── controller
│   │   │   ├── lib
│   │   │   ├── model
│   │   │   │   └── v2_0
│   │   │   └── processor
│   │   │       └── models
│   │   └── plugins
│   │       ├── builders
│   │       │   ├── 2_0
│   │       │   ├── Ansible
│   │       │   └── Diagram
│   │       ├── checkpointers
│   │       ├── explainers
│   │       │   └── 2_0
│   │       ├── finalizers
│   │       │   └── 2_0
│   │       ├── generators
│   │       │   └── 2_0
│   │       ├── migrators
│   │       │   └── 2_0
│   │       ├── validators
│   │       │   └── 2_0
│   │       └── variables
│   │           └── 2_0
│   └── tools
│       └── regress
│           └── regress
├── Data
│   ├── Config
│   └── Site
│       └── Schema
│           └── 2.0
├── Driver
└── Scripts
```
The python Stevedore module is used to manage various "plugins" that complete distinct components
of such phases as Generation, Validation, Building and so on.  This code is in the "plugins"
directory.  The cp directory contains the code that marshalls the various phases, reads the input,
provides internal helper functions, and declares the plugin base classes.

### Configuration processor output

The basic structure of the output from a run is as follows:
```
└── entry-scale-kvm-vsa
    └── 2.0
        ├── persistent_state
        └── stage
            ├── ansible
            │   ├── group_vars
            │   ├── hosts
            │   └── host_vars
            ├── info
            ├── internal
            └── net
                └── intf
```

The name of the cloud is at the head of the tree, the "2.0" refers to the version of the input model.
The "persistent state" is held in "persistent_state", and the other output including the Ansible
output is in "stage".

We've included a script that you can use to set the various command-line options to the main script
that is used to run the code (Driver/hlm-cp).  This script is Driver/run_cp.sh.  You will need to
update the DEFINITION and SERVICE_DIR variables with the path to helion-input-model, as
indicated in the script.

A successful run will produce console output like the following:

```
@@@ Processing cloud model version 2.0

################################################## Input Processing Started ##################################################

Input Processing Succeeded in 1.612s

################################################## Validate Process Started ##################################################
Validator encryption-key Started
Validator encryption-key Completed in 0.000s
Validator disk-model-2.0 Started
Validator disk-model-2.0 Completed in 0.078s
Validator interface-models-2.0 Started
Validator interface-models-2.0 Completed in 0.036s
Validator network-groups-2.0 Started
Validator network-groups-2.0 Completed in 0.044s
Validator networks-2.0 Started
Validator networks-2.0 Completed in 0.040s
Validator server-roles-2.0 Started
Validator server-roles-2.0 Completed in 0.014s
Validator server-groups-2.0 Started
Validator server-groups-2.0 Completed in 0.016s
Validator control-planes-2.0 Started
Validator control-planes-2.0 Completed in 0.034s
Validator nic-mappings-2.0 Started
Validator nic-mappings-2.0 Completed in 0.019s
Validator servers-2.0 Started
Validator servers-2.0 Completed in 0.030s
Validator pass-through-2.0 Started
Validator pass-through-2.0 Completed in 0.004s
Validator ring-specifications-2.0 Started
Validator ring-specifications-2.0 Completed in 0.094s
Validator firewall-rules-2.0 Started
Validator firewall-rules-2.0 Completed in 0.023s
Validator cross-reference-2.0 Started
Validator cross-reference-2.0 Completed in 0.004s
Validator deployer-network-lifecycle-mgr-2.0 Started
Validator deployer-network-lifecycle-mgr-2.0 Completed in 0.004s

Validate Process Succeeded in 0.680s

################################################## Model Creation Process Started ##################################################
about to load CloudDescription cloudConfig.yml
loading CloudDescription

Model Creation Process Succeeded in 0.010s

################################################## Controller Creation Process Started ##################################################

Controller Creation Process Succeeded in 0.002s

################################################## CleanUpStage Process Started ##################################################

CleanUpStage Process Succeeded in 0.002s

################################################## Migration Process Started ##################################################
Migrating the "CloudModel" model with the "resource-nodes-to-resources-2.0" migrator...

Migration Process Succeeded in 0.008s

################################################## Generate Process Started ##################################################
Generator encryption-key Started
Generator encryption-key Completed in 0.012s
Generator cloud-cplite-2.0 Started
Generator cloud-cplite-2.0 Completed in 0.307s
Generator ring-specifications-2.0 Started
Generator ring-specifications-2.0 Completed in 0.000s
Generator firewall-generator-2.0 Started
Generator firewall-generator-2.0 Completed in 0.000s
Generator consumes-generator-2.0 Started
Generator consumes-generator-2.0 Completed in 0.440s
Generator route-generator-2.0 Started
Generator route-generator-2.0 Completed in 0.008s

Generate Process Succeeded in 0.981s

################################################## Build Process Started ##################################################
Builder hosts-file-2.0 Started
Builder hosts-file-2.0 Generated the following artifacts:
	(+) ./clouds/entry-scale-kvm-vsa/2.0/stage/net/hosts.hf
Builder hosts-file-2.0 Completed in 0.000s
Builder ansible-hosts-2.0 Started
Builder ansible-hosts-2.0 Generated the following artifacts:
	(+) ./clouds/entry-scale-kvm-vsa/2.0/stage/ansible/hosts/localhost
	(+) ./clouds/entry-scale-kvm-vsa/2.0/stage/ansible/hosts/verb_hosts
Builder ansible-hosts-2.0 Completed in 0.001s
Builder ansible-all-vars-2.0 Started
Builder ansible-all-vars-2.0 Generated the following artifacts:
	(+) ./clouds/entry-scale-kvm-vsa/2.0/stage/ansible/group_vars/all
Builder ansible-all-vars-2.0 Completed in 0.080s
Builder ans-host-vars-2.0 Started
Builder ans-host-vars-2.0 Generated the following artifacts:
	(+) ./clouds/entry-scale-kvm-vsa/2.0/stage/ansible/host_vars/helion-cp1-c1-m1-mgmt
	(+) ./clouds/entry-scale-kvm-vsa/2.0/stage/ansible/host_vars/helion-cp1-c1-m2-mgmt
	(+) ./clouds/entry-scale-kvm-vsa/2.0/stage/ansible/host_vars/helion-cp1-c1-m3-mgmt
	(+) ./clouds/entry-scale-kvm-vsa/2.0/stage/ansible/host_vars/helion-cp1-vsa0001-mgmt
	(+) ./clouds/entry-scale-kvm-vsa/2.0/stage/ansible/host_vars/helion-cp1-vsa0002-mgmt
	(+) ./clouds/entry-scale-kvm-vsa/2.0/stage/ansible/host_vars/helion-cp1-vsa0003-mgmt
	(+) ./clouds/entry-scale-kvm-vsa/2.0/stage/ansible/host_vars/helion-cp1-comp0001-mgmt
Builder ans-host-vars-2.0 Completed in 0.409s
Builder ans-group-vars-2.0 Started
Builder ans-group-vars-2.0 Generated the following artifacts:
	(+) ./clouds/entry-scale-kvm-vsa/2.0/stage/ansible/group_vars/entry-scale-kvm-vsa-control-plane-1-cluster1
	(+) ./clouds/entry-scale-kvm-vsa/2.0/stage/ansible/group_vars/entry-scale-kvm-vsa-control-plane-1
	(+) ./clouds/entry-scale-kvm-vsa/2.0/stage/ansible/group_vars/entry-scale-kvm-vsa-control-plane-1-vsa
	(+) ./clouds/entry-scale-kvm-vsa/2.0/stage/ansible/group_vars/entry-scale-kvm-vsa-control-plane-1-compute
Builder ans-group-vars-2.0 Completed in 0.815s
Builder ans-encr-artifacts Started
Builder ans-encr-artifacts Generated no artifacts
Builder ans-encr-artifacts Completed in 0.000s
Builder net-info-2.0 Started
Builder net-info-2.0 Generated the following artifacts:
	(+) ./clouds/entry-scale-kvm-vsa/2.0/stage/info/net_info.yml
Builder net-info-2.0 Completed in 0.002s
Builder route-info-2.0 Started
Builder route-info-2.0 Generated the following artifacts:
	(+) ./clouds/entry-scale-kvm-vsa/2.0/stage/info/route_info.yml
Builder route-info-2.0 Completed in 0.000s
Builder server-info-2.0 Started
Builder server-info-2.0 Generated the following artifacts:
	(+) ./clouds/entry-scale-kvm-vsa/2.0/stage/info/server_info.yml
Builder server-info-2.0 Completed in 0.008s
Builder firewall-info-2.0 Started
{'enable': True, 'logging': True}
Builder firewall-info-2.0 Generated the following artifacts:
	(+) ./clouds/entry-scale-kvm-vsa/2.0/stage/info/firewall_info.yml
Builder firewall-info-2.0 Completed in 0.041s
Builder diagram-2.0 Started
Builder diagram-2.0 Generated the following artifacts:
	(+) ./clouds/entry-scale-kvm-vsa/2.0/stage/info/CloudDiagram.txt
Builder diagram-2.0 Completed in 0.040s

Build Process Succeeded in 1.634s

################################################## Explanation Process Started ##################################################
Explainer file ./clouds/entry-scale-kvm-vsa/2.0/stage/CloudExplanation.txt Created
Explainer servers-2.0 Started
Explainer servers-2.0 Completed in 0.000s

Explanation Process Succeeded in 0.023s

################################################## Finalize Process Started ##################################################
Finalizer cloud-model-2.0 Started
Finalizer cloud-model-2.0 Generated the following artifacts:
	(+) ./clouds/entry-scale-kvm-vsa/2.0/stage/internal/CloudModel.json
	(+) ./clouds/entry-scale-kvm-vsa/2.0/stage/internal/ConfigFiles.json
Finalizer cloud-model-2.0 Completed in 0.431s
Finalizer service-view-2.0 Started
Finalizer service-view-2.0 Generated the following artifacts:
	(+) ./clouds/entry-scale-kvm-vsa/2.0/stage/info/service_info.yml
Finalizer service-view-2.0 Completed in 0.018s
Finalizer address-allocation-2.0 Started
Finalizer address-allocation-2.0 Generated the following artifacts:
	(+) ./clouds/entry-scale-kvm-vsa/2.0/stage/info/address_info.yml
Finalizer address-allocation-2.0 Completed in 0.006s

Finalize Process Succeeded in 0.479s

################################################################################
# The configuration processor completed successfully.
################################################################################
```
## helion-ansible

This directory contains the Ansible scripts that are run against the output produced by
the configuration processing engine to deploy the working cloud that has been specified
by the helion inputs.

### Brief overview of helion-ansible structure

HOS v2.0 and the concept of Lifecycle management aim to ensure ease of
cloud operation.  To this end, we have identified
high-level lifecycle phases or "operations" that are required for the cloud
as a whole and for each service, e.g. deploy, reconfigure and upgrade, where
a service refers to nova, cinder, glance, etc. Each service lifecycle
operation in turn uses lower-level "verbs", which are defined per
service-component, where examples of a service-component are nova-api,
nova-scheduler, etc. and example verbs are install, configure, start and stop.

Hence there is a hierarchy of invoked operations that may look something like:

    cloud deploy
      ─> nova deploy
        ─> nova-api
          ─> install
          ─> configure
        ─> nova-conductor
          ─> install
          ─> configure
        ─> nova-post-configure
          ─> db_create
          ─> keystone_setup
        ─> nova-api
          ─> start
        ─> nova-conductor
          ─> start
      ...
      ─> glance deploy
        ─> glance-api
          ─> install
          ─> configure
        ─> glance-post-configure
          ─> db_create
          ─> keystone_setup
        ─> glance-api
          ─> start
      ...

The general layout of a &lt;service&gt;-ansible directory reflects this structure and
is as follows:

- An Ansible role is defined per service-component, e.g. nova-api,
 nova-scheduler, etc.; additional \_private\_ roles may also be defined, see
detailed overview below.
- Each role comprises a set of standard verb playbooks, e.g. install.yml,
configure.yml and start.yml, in addition to service-specific or private verbs.
- A top-level playbook is defined for each operation, e.g. nova-deploy.yml,
nova-reconfigure.yml and nova-upgrade.yml; there may be additional
\_private\_ operations
- The top-level operation playbooks combine and orchestrate the lower-level
service-component verb playbooks in a series of plays.

The helion-ansible repo contains Ansible directories including playbooks
for a variety of Openstack services - e.g. Swift, Cinder, Nova, Keystone,
Tempest, Ironic, Neutron, Glance, Freezer, Ceilometer, Heat etc.
In addition there are the following Ansible directories:

- mq-ansible:  RabbitMQ
- db-ansible:  MySQL
- ceph-ansible:  Ceph
- cluster-ansible:  HAProxy, Apache, keepalived
- cobbler-ansible:  Cobbler
- osconfig-ansible:  OS configuration
- logging-ansible:  Logging
- swiftlm:  Utility library used by swift-ansible (ring management etc)
- cinderlm:  Utility library used by cinder-ansible
- hlm-ansible:  Contains overarching helion orchestration playbooks and
playbooks for the following operations including:
    - configuration processor operations
    - python venv packaging and distribution (python applications are installed
and managed as versioned venvs)
    - git operations (configuration processor state is managed using git)
    - variable pass-through operations
    - sos reports


### Detailed overview of &lt;service&gt;-ansible directory layout

The structure of a helion-ansible directory is a combination of the structure imposed
by Ansible itself and the particular operation and verb playbook layout of helion.
For further information on Ansible see <http://www.ansible.com/home> and in
particular the documentation at <http://docs.ansible.com/>.  At a high-level, the
structure is as follows:

    └── <service>-ansible
        ├── filter_plugins
        ├── library
        ├── <service>-<operation-1>.yml
        ├── <service>-<operation-2>.yml
        ├── <service>-<operation-3>.yml
        ├── _<service>-<private operation-1>.yml
        ├── _<service>-<private operation-2>.yml
        └── roles
            ├── <service-component-role-1>
            │   ├── defaults
            │   ├── files
            │   ├── handlers
            │   ├── meta
            │   ├── tasks
            │   │   ├── <verb 1>.yml
            │   │   ├── <verb 2>.yml
            │   │   ├── <verb 3>.yml
            │   │   ├── _<private verb 1>.yml
            │   │   ├── _<private verb 2>.yml
            │   │   └── .....
            │   ├── templates
            │   └── vars
            ├── <service-component-role-2>
            ├── <service-component-role-3>
            ├── ....
            ├── _<private-service-role-1>
            │   ├── defaults
            │   ├── files
            │   ├── handlers
            │   ├── meta
            │   ├── tasks
            │   │   └── .....
            │   ├── templates
            │   └── vars
            │       └── main.yml
            ├── _<private-service-role-2>
            └── ....


#### Operation Playbooks

Each &lt;service&gt;-ansible directory contains service operation playbook files
at the top level. These yaml files coordinate the service-component verbs into
plays to carry out major lifecycle operations, such as deploy, reconfigure or
upgrade.  The operation playbooks describe how the service-component
role "verbs" are orchestrated, and handle any inter-role dependencies.
The overarching helion orchestration layer (e.g. hlm-deploy.yml from hlm-ansible)
invokes the service operation playbooks. In exceptional circumstances it is
possible that this overarching orchestration layer will invoke individual
verbs directly.

helion provides playbooks that combine all service playbooks for a single
operation, e.g. hlm-deploy invokes &lt;service&gt;-deploy for services in order
to deploy a complete cloud. Each &lt;service&gt;-operation playbook, e.g.
nova-deploy is also runnable on its own. The set of operation playbooks
represent the API that is available for the operator of the cloud, both
at the cloud level and the per-service level. For example, the API for
managing the lifecycle of the nova service could comprise the following
set of playbooks:

- nova-deploy.yml
- nova-cloud-configure.yml
- nova-reconfgure.yml
- nova-stop.yml
- nova-start.yml
- nova-upgrade.yml

#### Private Operation Playbooks

The above set of example playbooks for nova can be used standalone or as part
of another operation playbook. For example, the nova-deploy playbook will end
by including the nova-start playbook to start all nova services. It is
generally useful to group repeated sets of plays into high-level playbooks for
re-use between these operation playbooks. For example, nova uses a configure
playbook that has a series of plays that each invoke the configure verb for
each of the nova service components:

    ---
    - hosts: "{{ target_hosts | default('all') }}:&NOV-CND"
      sudo: yes
      roles:
      - NOV-CND
      tasks:
      - include: roles/NOV-CND/tasks/configure.yml

    - hosts: "{{ target_hosts | default('all') }}:&NOV-API"
      sudo: yes
      roles:
      - NOV-API
      tasks:
      - include: roles/NOV-API/tasks/configure.yml

    - hosts: "{{ target_hosts | default('all') }}:&NOV-SCH"
      sudo: yes
      roles:
      - NOV-SCH
      tasks:
      - include: roles/NOV-SCH/tasks/configure.yml

    .... remaining nova components.

The above playbook is termed in HOS v2.0 as an \_private\_ operation playbook as it
is not part of the API for managing the lifecycle of nova. Private operation
playbooks are indicated by preceding the playbook name with a "\_"
character, e.g. \_nova-configure.yml. This playbook can be invoked from
multiple operation playbooks (e.g. nova-deploy, nova-reconfigure and
nova-upgrade), but is not executed on its own.

#### Roles

Roles are located as sub-directories of the "roles" directory at the top
level of the repo. A majority of the Ansible roles in helion will map to
service components, e.g. nova-api, nova-scheduler, cinder-api and the
convention is to give the Ansible role the same name as given to that
service component in the service/\*.yml inputs to the configuration processor.
These roles are directly referenced in the top-level playbooks (public or private).

#### Private Roles

It is also common for a service to group a set of tasks in a role that is only
directly referenced by other roles within the service; a typical example is a
common role that contains tasks shared between multiple roles within the
service. Such a role is termed an \_private\_ role and HOS v2.0 uses the convention
of preceding an private role name with a "\_" character, e.g. \_SWF-CMN.
Private roles are not referenced in high-level operation playbooks, such as
deploy or upgrade; instead, their constituent verbs are directly included by
verbs in other roles, e.g. the swift object install verb:

        ---
        - include: ../../_SWF-CMN/tasks/install.yml

        - name: SWF-OBJ | install | Install Swift Object services
          install_package: name=swift service={{ item.key }} state=present
          with_dict: object_services

which uses the install verb from an interal swift common role, and the swift
object configure verb:

        ---
        - include: ../../_SWF-CMN/tasks/configure.yml
        - include: ../../_SWF-RSY/tasks/configure.yml

        .... additional tasks for configuring swift object component.

which uses two private swift roles. In addition, the swift object role
needs to specify a dependency on the swift common role by including the
following in SWF-OBJ/meta/main.yml:

        ---
        dependencies:
          - role: _SWF-CMN

   The above ensures that all variables required for the included \_SWF-CMN
or \_SWF-RSY verbs are present when invoked from SWF-OBJ verbs.

#### Verbs

Each of the above-mentioned roles contain a set of "verbs", which exist as
individual yaml files under the "tasks" subdirectory of each role.
The helion development team have identified a set of standard verbs that are
believed to be applicable to a majority of service-components across an
Openstack deployment. In turn the service-component roles include implementations
of these verbs as separate yaml task files. Ideally each verb will also include
a validate step at the end, to confirm that the verb has completed successfully,
or raise an error otherwise. Note, however, that some of the identified verbs
may not be relevant to all service-components.

"Verbs" include:

- start
- stop
- install
- configure

The verbs described above are invoked from a higher-level service operation
playbook, such as nova-deploy.yml. Service teams can also define \_private\_
verbs or task files within a role that are not intended for use outside
the role, i.e. they are only invoked by other verbs within that role. The
convention in HOS v2.0 is to prefix the name of these task files with a "\_"
character, e.g. "\_join\_cluster.yml" in the rabbitmq Ansible codebase
(mq-ansible repo).
