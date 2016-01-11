
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


**Freezer/BURA playbooks for HLM**
===================

## Prerequisite
For now we assume the freezer-api role will always be installed on the same host
as the logging-server role (they share the elasticsearch database without a vip).

## Infra
The playbooks will deploy the freezer infrastructure:

 - freezer-api
 - freezer-agent and freezer-scheduler on nodes where backup should happen

## Roles
We provide four ansible roles:

 - freezer-api
 - freezer-agent
 - freezer-post-configure (keystone and database configuration)
 - freezer-jobs (backup and restore job managment)

## Auto backup
Backup of the following items will be automaticaly configured:
(Datas are backuped to swift every 24h)
Deployer node:

 - /home/
 - /etc/passwd
 - /etc/shadow
 - /etc/ssh/
 - /var/lib/cobbler/

Mysql nodes:

 - mysql database

Swift Proxy node:

- /etc/swiftlm/builder_dir


It is possible to disable the creation of the backup and restore jobs by setting the following variables to false:
freezer_backup_jobs_upload
freezer_restore_jobs_upload

For example:
> ansible-playbook -i hosts/verb_hosts site.yml -e "freezer_backup_jobs_upload=false"

## Serialization
By default we use some serialization in two steps of the deployement:

 - During the start of all freezer-scheduler. As the it is polling the
   freezer-api and keystone every 60 sec, this will avoid a big number of
   scheduler to do query at the same time.
 - During the upload of backup and restore jobs, to avoid DDoS-ing the
   infrastrucure if installing a large number of compute.

The default value of the serialization is 3, which means those steps will
execute on three nodes in parallel (instead of all of them).
You can tune it by setting the freezer_serialization parameter like this:
> ansible-playbook -i hosts/verb_hosts site.yml -e freezer_serialization=10

This serialization can be turned off completly byt setting it to 100%
> ansible-playbook -i hosts/verb_hosts site.yml -e "freezer_serialization=100%"
