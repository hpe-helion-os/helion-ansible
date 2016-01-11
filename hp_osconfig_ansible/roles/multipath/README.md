
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


multipath
=========

This role enables users to configure various multipath on target
machines.

Requirements
------------

This role requires Ansible 1.4 or higher

Role Variables
--------------

The variables that can be passed to this role and a brief description about
them are as follows:


    multipath_defaults: <A dictionary of key-value pairs for defaults section>
    eg:
        multipath_defaults:
          user_friendly_names: no
          max_fds: max
          fast_io_fail_tmo: 5


    multipath_devices: <A list of devices with key-value pairs for devices section>
    eg:
        multipath_devices:
          - vendor:                  "HP"
            product:                 "3PAR"
            path_selector:           "round-robin 0"
            getuid_callout:          "/lib/udev/scsi_id -g -u -d /dev/%n"

          - vendor:                  "NETAPP"
            product:                 "LUN"
            path_selector:           "round-robin 0"
            getuid_callout:          "/lib/udev/scsi_id -g -u -d /dev/%n"

    multipath_blacklist: <A list of regex with key-value pairs for blacklist section>
    eg:
        multipath_blacklist:
          - devnode: "^sd[a-z]"
          - wwid: "2345123469"
          - device:
              vendor: "IBM"
              product: "*"


    multipath_blacklist_exceptions: <A list of regex with key-value pairs for blacklist_exceptions section>
    eg:
        multipath_blacklist_exceptions:
          - devnode: "^sdc"
          - wwid: "23451234698"
          - device:
              vendor: "IBM"
              product: "ST500"

Operational Guide:
------------------
The default settings are to blacklist all devices. To overwrite the default settings
do the following before running the site.yml playbook

 1. In the HOS deployer node, open the multipath/multipath_settings.yml under my_cloud/config
    where the default setting will be to blacklist all devices with the exception of HP 3PAR:
    i.e.,
        multipath_blacklist:
          - device:
              vendor: ".*"
              product: ".*"

        multipath_blacklist_exceptions:
          - device:
              vendor: "3PARdata"
              product: "VV"
    NOTE: Additionally all disk model devices will be blacklisted by default using wwid
 2. Modify the file as per the "Role Variables" section described at the beginning
 3. Follow the below steps to apply the settings:

        cd ~/helion/hos/ansible
        git add -A
        git commit -m "your commit message"
        ansible-playbook -i hosts/localhost config-processor-run.yml
        ansible-playbook -i hosts/localhost ready-deployment.yml

        cd ~/scratch/ansible/next/hos/ansible
        ansible-playbook -i hosts/verb_hosts site.yml


Examples
--------

Input variables:
----------------

    multipath_defaults:
      user_friendly_names: no
      max_fds: max
      flush_on_last_del: yes
      queue_without_daemon: no
      dev_loss_tmo: infinity
      fast_io_fail_tmo: 5

    multipath_devices:
      - vendor:                  "NETAPP"
        product:                 "LUN"
        path_grouping_policy:    group_by_prio
        features:                "3 queue_if_no_path pg_init_retries 50"
        prio:                    "alua"
        path_checker:            tur
        failback:                immediate
        path_selector:           "round-robin 0"
        hardware_handler:        "1 alua"
        rr_weight:               uniform
        rr_min_io:               128
        getuid_callout:          "/lib/udev/scsi_id -g -u -d /dev/%n"

      - vendor:                  "HP"
        product:                 "3PAR"
        path_grouping_policy:    group_by_prio
        failback:                immediate
        path_selector:           "round-robin 0"
        getuid_callout:          "/lib/udev/scsi_id -g -u -d /dev/%n"

    multipath_blacklist:
      - devnode: "^sd[a-z]"
      - wwid: "2345123469"
      - device:
          vendor: "IBM"
          product: "*"

    multipath_blacklist_exceptions:
      - devnode: "^sdc"
      - wwid: "23451234698"
      - device:
          vendor: "IBM"
          product: "ST500"


Resulting multipath.conf:
-------------------------

    defaults {
        fast_io_fail_tmo "5"
        flush_on_last_del "True"
        max_fds "max"
        user_friendly_names "False"
        dev_loss_tmo "infinity"
        queue_without_daemon "False"
    }

    devices {
        device {
            path_checker "tur"
            product "LUN"
            vendor "NETAPP"
            features "3 queue_if_no_path pg_init_retries 50"
            prio "alua"
            rr_min_io "128"
            path_grouping_policy "group_by_prio"
            path_selector "round-robin 0"
            getuid_callout "/lib/udev/scsi_id -g -u -d /dev/%n"
            hardware_handler "1 alua"
            rr_weight "uniform"
            failback "immediate"
            }
        device {
            product "3PAR"
            vendor "HP"
            path_grouping_policy "group_by_prio"
            path_selector "round-robin 0"
            getuid_callout "/lib/udev/scsi_id -g -u -d /dev/%n"
            failback "immediate"
            }
    }

    blacklist {
        devnode "^sd[a-z]"
        wwid "2345123469"
        device {
            product "*"
            vendor "IBM"
            }
    }

    blacklist_exceptions {
        devnode "^sdc"
        wwid "23451234698"
        device {
            product "ST500"
            vendor "IBM"
            }
    }
