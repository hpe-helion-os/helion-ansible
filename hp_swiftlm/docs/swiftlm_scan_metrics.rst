
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


Metrics Produced By swiftlm-scan
================================

Introduction
------------

The swiftlm-scan program is comprised a number of "checks". Each check
produces one or more metrics. This document describes the metrics.

The following information is organised as follows:

* Metric name

  This is the name of the metric being described. This is the name that
  Monasca receives.

* Check name

  This is the name of the check producing the metric.

* Value Class

  This is one the following. This is not a Monasca concept. We use it so that
  the table is less verbose.

  - Measurement -- this is used when the value of the metric reports a
    value. For example, the voltage of a 12V battery might be 11.98.

  - Status -- this is used when the value represents a state or status
    something in the system. The following values are used:

    0. Status is normal or ok
    1. Status is in a warning state
    2. Status is in a failed state
    3. The state is unknown (cannot be determined or not applicable at the
       current time

    Generally, a metric of this value class will also have a value_meta

* Dimensions. This is the dimensions as sent to Monasca

* Value_meta. This is optional. When present, it contains additional data
  in addition to the value of the metric.

* Description. This provides a longer description of the values and
  meaning of the metric.

* Troubleshooting/Resolution. This provides some suggestions for using and
  interpreting the metric values to troubleshoot and resolve problems on
  your system.


Metrics
-------

* swiftlm.systems.check_mounts

  - Reports the status of mounted Swift filesystems
  - Check: --check-mounts
  - Dimensions:

    * hostname: name of host being reported
    * service: object-storage

    Value Class: Status
    Value Meta:

    * msg: see list

  - Description

    This metric reports the mount state of each drive that should be mounted
    on this node. On errors, the following value_meta.msg are used:

    * `could not find any devices to check`

      There are no drives on this server. Currently this is because the
      --check-mounts check is still being developed.

* swiftlm.systems.connectivity.memcache_check

  - Reports if a proxy server can connect to memcached on other servers
  - Check: --connectivity
  - Dimensions:

      * observer_host: the host reporting the metric.
      * hostname: the host being connected to
      * target_port: the port memcached listens on (normally 11211)
      *  service: object-storage

  - Value Class: Status
  - Value Meta:

      * msg

  - Description

    This metric reports if memcached on the host as specified by the
    hostname dimension is accepting connections from the host running the
    check. The following value_meta.msg are used:

    * `<hostname>:<target_port> ok`

      We successfully connected to <hostname> on port <target_port>

    * TBS

      TBS

* swiftlm.systems.connectivity.connect_check

  - Reports if a Swift server can connect to a host or VIP
  - Check: --connectivity
  - Dimensions:

    * observer_host: the host that is able/unable to connect to the hostname
    * hostname: the host being connected to
    * target_port: the port being connected to (example 35357)
    * service: object-storage

    Value Class: Status
    Value Meta:

    * msg

  - Description

    This metric reports if a server can connect to other hosts or VIPs. The
    check attempts to connect to all other hosts in the ring (i.e., to other
    Swift servers and also to the VIP of the following services:

    * The Keystone VIP used to validate tokens (normally port 35357)
    * The VIP of Swift itself

    The check simply connects to the <hostname>:<target_port>. It does
    not attempt to send data.

    The following value_meta.msg are used:

    * `<hostname>:<target_port> ok`

      We successfully connected to <hostname> on port <target_port>

    * `Could not connect to http:<hostname>:<target_port>`

      We could not connect to <hostname> on port <target_port>

  - Troubleshooting/Resolution

    When a Swift server is down, all *other* servers will report that they
    cannot connect.

    If a single server or groups of servers cannot connect to other servers,
    you should look for a pattern that explains why. For example, has a
    network switch failed? Are servers on the correct VLANs?

    If the Keystone service stops working, all Swift proxy servers will report
    a connection failure. Restoring the Keystone service will resume normal
    operations.

    If a single Swift proxy server is reporting a problem you should
    investigate the connectivity of that server. Since this server can no longer
    validate tokens, your users will get (apparently random) 401 responses.
    Consider stopping swift-proxy-server on that node until you determine why
    it cannot connect to the Keystone service.

* swiftlm.systems.ntp NOT IMPLEMENTED

  - Reports if NTP is running on the server.
  - Check: --ntp
  - Dimensions:

    * hostname: the host being checked
    * service: object-storage
    * error: Text of any error messages that occur

  - Description

    This metrics reports if NTP is running on the host. The host uses
    `systemctl status` to determine this.

    The following value_meta.msg are used:

    * `OK`

      NTP is running.

    * `ntpd not running: <error>`

      NTP was not running. Error is the text returned by systemctl which may
      help diagnose the issue.

  - Troubleshooting/Resolution

    When NTP is not running XXX


* swiftlm.systems.ntp.stratum  NOT IMPLEMENTED

  - Reports the statum level of NTP
  - Check: --ntp
  - Dimensions:

    * hostname: the host being checked
    * service: object-storage

  - Description

    This metric's value will be the stratum level of the current server.
    This is determined using the output of `ntpq -pcrv`.


  - Troubleshooting/Resolution

    When the stratum level increases this indicates that time is being
    recieved from less accurate sources.
    Ensure that the configured master NTP servers are up and that no other
    servers have been added to the time reference list. All servers should be
    within +/-1 stratum level of each other at most.


* swiftlm.systems.ntp.offset  NOT IMPLEMENTED

  - Reports the offset from the system clock and the reported NTP time.
  - Check: --ntp
  - Dimensions:

    * hostname: the host being checked
    * service: object-storage

  - Description

    This metric's value will be the offset of the system clock and the NTP
    time.
    This is determined using the output of `ntpq -pcrv`.


  - Troubleshooting/Resolution

    A high offset means that the server isnt adjusting its time correctly or
    that its hardware clock is malfunctioning. If the clock is battery backed
    it could be at a low power level.


* swiftlm.swift.file_ownership

  - Reports if Swift configuration and data files have the appropriate owner
  - Check: --file-ownership
  - Dimensions:

    * hostname: the host where the file is stored
    * path: the pathname of the file or directory
    * service: object-storage

    Value Class: Status
    Value Meta:

    * msg

  - Description

    This metric reports if a directory or file has the appropriate owner.
    The check looks at Swift configuration directories and files. It also
    looks at the top-level directories of mounted file systems (example,
    /srv/node/disk0 and /srv/node/disk0/objects.

    The following value_meta.msg are used:

    * `Path: <path> is not owned by swift`

      The file or directory at <path> is not owned by Swift. Specifically,
      the directory/file should be owned by swift.swift.

    * `Path: /etc/swift/empty should not be empty` or `Path: /etc/swift/empty is not owned by swift`

      The file in /etc/swift is empty. Generally, configuration files should
      have content.

    * `Path: /srv/node/disk1 is not owned by swift`

      This is a special case: the directory /srv/node/disk1 is owned by
      the root user. This happens when a filesystem fails to mount -- and
      so we see the ownership of the mount point -- not the mounted filesystem
      root directory.

  - Troubleshooting/Resolution

    Improper ownership of configuration files may be due to manual editing
    or copy of files. Returning the configuration process may resolve the
    problem. If not, check that the file is a configuration file that is
    actually used by Swift. If not, consider deleting or moving it.

    Improper ownership of top-level directories on mounted filesystems may
    be due to insertion of a disk drive that belongs to a different system.
    The Swift processes will be unable to write accounts, containers or objects
    to the filesystems. You should stop all Swift processes and perform
    a rename of all files on the filesystem to correct the problem.


* swiftlm.swift.replication.object.last_replication, swiftlm.swift.replication.container.last_replication, swiftlm.swift.replication.account.last_replication

  - Reports how long it has been since the replicator last finished a replication
    run. The replicator in question is indicated in the metric name.
  - Check: --replication
  - Dimensions:

    * hostname: the host where replicator is running
    * service: object-storage

    Value Class: Measurement
    Value Meta:

    * None

  - Description

    This reports how long (in seconds) since the replicator process last
    finished a replication run. If the replicator is stuck, the time
    will keep increasing forever. The time a replicator normally takes
    depends on disk sizes and how much data needs to be replicated. However,
    a value over 24 hours is generally bad.

  - Troubleshooting/Resolution

    The replicator might be stuck (XFS filesystem hang or other issue).
    Restart the process in question. For example, to restart the object-replicator::

        sudo systemctl restart swift-object-replicator


* swiftlm.swift.drive_audit
  - Reports the status from the swift-drive-audit program
  - Check: --drive-audit
  - Dimensions:

    * hostname: the host where swift-drive-audit is running
    * service: object-storage
    * mount_point: the mountpoint of the filesystem
    * kernel_device: the device on which the filesystem is mounted

    Value Class: Status
    Value Meta:

    * `No errors found on device mounted at: /srv/node/disk0`

      No errors were found

    * `Errors found on device mounted at: /srv/node/disk0`

      Errors were found in the kernel log


  - Description

    If an unrecoverable read error (URE) occurs on a filesystem, the error is
    logged in the kernel log. The swift-drive-audit program scans the kernel log
    looking for patterns indicating possible UREs.

    To get more information, log onto the node in question and run::

        sudo swift-drive-audit  /etc/swift/drive-audit.conf

    UREs are common on large disk drives. They do not necessarily indicate that
    the drive is failed. You can use the xfs_repair command to attempt to repair
    the filesystem. Failing this, you may need to wipe the filesystem.

    If UREs occur very often on a specific drive, this may indicate that
    the drive is about to fail and should be replaced.

* swiftlm.swift.swift_services

  - Reports if a Swift process (daemon/server) is running or not
  - Check: --swift-services
  - Dimensions:

    * hostname: name of host being reported
    * service: object-storage
    * component: the process (daemon/server) being reported

    Value Class: Status
    Value Meta:

    * `<name> is running`

      The named process is running.

    * `<name> is not running`

       The named process has stopped.

  - Description

    This metric reports of the process as named in the component dimension
    and the msg value_meta is running or not.

    Use the swift-start.yml playbook to attempt to restart the stopped
    process (it will start any process that has stopped -- you don't need
    to specifically name the process).

* swiftlm.generic_hardware.network_interface

  - Reports the speed of a network interface
  - Check: --network-interface
  - Dimensions:

    * hostname: name of host being reported
    * service: object-storage
    * interface: the NIC being reported

    Value Class: Measurement
    Value Meta:

    * None

  - Description

    The value is the speed of the interface. A value of 0 indicates that
    the speed has not been reported by ethtool.

    Only NICs used by Swift are reported.

* swiftlm.generic_hardware.network_interface.<metric>

  - Reports the value of a NICs metric
  - Check: --network-interface
  - Dimensions:

    * hostname: name of host being reported
    * service: object-storage
    * interface: the NIC being reported

    Value Class: Measurement
    Value Meta:

    * None

  - Description

    The value is the value of the metric. For example, for
    swiftlm.generic_hardware.network_interface.rx.errs, the value of the
    receive error count.

    Only NICs used by Swift are reported.

* swiftlm.systems.check_mounts

  - Reports if Swift filesystem are correctly mounted
  - Check: --check-mounts
  - Dimensions:

    * hostname: name of host being reported
    * service: object-storage
    * mount: the mountpoint of the filesystem
    * device: the device where the filesystem is mounted
    * label: always "---NA---"

    Value Class: Status
    Value Meta:

    * `/dev/sdc1 mounted at /srv/node/disk0 ok`

      Normal, ok, state

    * `/dev/sdd1 not mounted at /srv/node/disk1`


  - Description

    Checks the status of Swift device filesystems.

    You can attempt to remount by logging into the node and running the
    following command::

        sudo swiftlm-drive-provision --mount
