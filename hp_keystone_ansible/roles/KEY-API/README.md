
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


80README
======

There are different configurable entries for keystone
1. Configuration entries that go into keystone.conf
2. Deployment specific configuration which are not part of keystone.conf like log_level, process count etc
3. Additional configuration like the per-domain specific LDAP backend configuration


The following section describes the mechansim used for overriding or changing those configuration entries:

For 1: keystone.conf
   - Edit the files keystone.conf.j2  to add or change any config settings
   - You can get default/available configuration for kilo from
     http://docs.openstack.org/kilo/config-reference/content/section_keystone.conf.html
   - Make sure you don't change any values under {{ }}

For 2: keystone deployment such as log level
    - Edit the files  keystone_deploy_config.yml to change any config settings
    - Here you can only change values, can't add any new settings

For 1 and 2, to deploy the new settings:
    - ansible-playbook -i hosts/verb_hosts keystone-reconfigure.yml

For 3:
Configuring LDAP
    - Look at the file keystone_configure_ldap_sample.yml
    - copy that file to, for example, /tmp/myldap.yml
    - Edit that file and populate it with your ldap settings
    - ansible-playbook  -i hosts/verb_hosts keystone-reconfigure.yml  -e@/tmp/myldap.yml
    - You can follow the same procedure and add as many ldaps as you want. Make sure each ldap is configured under its
      own domain

Enabling features in Keystone
   HLM doesn't enable all the features by default.  Some of these features are tested/supported and some of them are
experimental. Tested features can be enabled and used in production. Experimental featuers can be enabled for POC  or
to get customer feedback. Experimental features may require few manual configuration and may have defects. We will
move an experimental feature to supported featureset once we have resolved all the issues with it


Tested/Supported Features

Enable Auditing
 - Edit the files  keystone_deploy_config.yml
 - Change the value keystone_enable_auditing to True
 - ansible-playbook -i hosts/verb_hosts keystone-reconfigure.yml


Experimental Features

Changing for UUID token to FernetToken
 - Edit the files  keystone_deploy_config.yml and change the value of "keystone_configure_fernet" to True
 - ansible-playbook -i hosts/verb_hosts keystone-reconfigure.yml

