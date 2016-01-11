
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


Swiftlm custom plugins for monasca agent
========================================

Introduction
------------

There are two steps to installing a custom plugin: install a detect plugin and
install a check plugin.

The detect plugin
-----------------

A custom detect plugin is installed in
`/usr/lib/monasca/agent/custom_detect.d`. This detect class gets called when
the `monasca-setup` command is run specifying the class name with its `-d`
option. This is done by the ansible task
`monasca_agent_plugin <https://github.com/hpcloud-mon/ansible-monasca-agent/blob/master/library/monasca_agent_plugin.py>`_

The detect plugin can be passed args from the `monasca-setup` cli or from
ansible task. GOTCHA: as far as I can tell the args values cannot contain
whitespace.

The detect plugin implements a method that should generate config for the
actual check plugin. This config is then used to create a yaml file in
`/etc/monasca/agent/conf.d`. The name of this yaml file must match the name of
the check plugin module described next.

The detect plugin generates config for each instance of a check - each instance
may have different config. For the `swiftlm`_check we generate a single
instance of the check that runs all the `swiftlm` tasks, where a task is for
example `connectivity` or `drive-audit`. An alternative design would generate
multiple instances each configured to run one `swiftlm` task.

Note: it is possible to create the yaml file directly but the recommended way
is to use a detect class to avoid learning the yaml schema.

The check plugin
----------------

A custom check plugin is installed in `/usr/lib/monasca/agent/custom_checks.d`.
The class in this module extends a monasca agent class, and implements a check
method that is called each time the agent daemon wakes up.

The check method gathers metrics from all the configured swiftlm tasks:

- entry point (or 'plugin') tasks: entry points are loaded and called
  directly. These tasks are disabled by default because the entry points are
  not installed in the monasca-agent venv.

- command line tasks: the `swiftlm-scan --format json` command is called for
  each command line task. These tasks are currently a hard-coded list but could
  be configured via the ansible task that deploys the detect plugin.

- load file tasks: metrics are read from files(s) configured via the ansible
  task that deploys the detect plugin. The file should contain a json encoded
  list of metric dicts.

Each task is assumed to return a single dict or a list of dicts. Each dict
should have keys that match the keyword args expected by the monasca agent
super-class gauge method(), which the plugin calls for each metric.

Metrics that are reporting a severity level of OK (i.e. 0) may be suppressed
i.e. not reported to the monasca-agent. By default none are suppressed - the
`suppress_ok` arg for the detect plugin may be used to configure suppression
for specific command tasks.

TBD: the OK suppression needs to distinguish between metrics whose value
represents a severity level and metrics whose value represents a raw value.

The plugin itself may generate metrics if a task fails e.g. if a file cannot be
found or a command line task times out.

(An alternative design would be to have individual check classes for each type
of task (command line, load file etc.). However, it is not clear that the
monasca agent supports multiple check classes in the same module since the name
of the check config file in `/etc/monasca/agent/conf.d` must match the name of
the *module* in `/usr/lib/monasca/agent/custom_checks.d`. Consequently, each
check class would need to be in a separate module, those modules would be
unable to import from a common module or each other, and there would be no way
to re-use common code between the check classes.)


Metric uploading to monasca
---------------------------

The monasca-agent collector daemon calls the plugin check method periodically
(every 60 secs by default). It aggregates metrics and de-duplicates them.

The monasca-agent forwarder sends metrics to a monasca service using
monascaclient.

Seeing it work
--------------

Follow process for hlm-dev-tools install. Before running `hlm-deploy.yml` on
the deployer vm:

  - comment out all services after swift, to save time.

  - Follow instructions here https://jira.hpcloud.net/browse/JAH-1871 to
    use vertica db with monasca. That workaround is currently required to
    have `monasca metric-list` return any results (see below).

Then, on the deployer VM::

    $ ansible-playbook -i hosts/verb_hosts monasca-cli-dev.yml \
        --limit PADAWANBASE-CCP-T1-M1-NETCLM
    $ ssh PADAWANBASE-CCP-T1-M1-NETCLM
    $ source ~/monasca-env.sh

Check swiftlm plugins source code modules are installed::

    $ sudo ls -R /usr/lib/monasca/agent/custom_*
    /usr/lib/monasca/agent/custom_checks.d:
    swiftlm_check.py

    /usr/lib/monasca/agent/custom_detect.d:
    swiftlm_detect.py  swiftlm_detect.pyc


Check swiftlm_check is installed in agent conf.d::

    $ sudo less /etc/monasca/agent/conf.d/swiftlm_check.yaml

    init_config: null
    instances:
    - dimensions:
        service: object-storage
      metrics_files: /var/cache/swift/swiftlm_uptime_monitor/uptime.stats
      name: swiftlm_check


To inspect the monasca agent collector log::

    $ sudo tail -f /var/log/monasca/agent/collector.log |grep swiftlm

This relates to the daemon that periodically runs the checks. (NB 60 secs
between updates) Default log level is WARN so you will see nothing if all is
ok, but if one of the custom plugin tasks fails (e.g. uptime.stats file not
found) then this will show up as a WARNING log message.

To check the monasca agent forwarder log (this relates to calls from agent to
monasca service)::

    $ sudo tail -f /var/log/monasca/agent/forwarder.log

To set log level lower for collector.log::

    $ sudo /opt/monasca/bin/monasca-setup -u monasca -p monasca \
        --keystone_url=http://PADAWANBASE-CCP-T01-VIP-KEY-API-NETCLM:35357/v3 \
        --project_name admin --log_level=DEBUG

All reported swiftlm_check metrics are logged at DEBUG level.

NB GOTCHA: running monasca-setup will cause the swiftlmdetect class to be
reloaded, but without any args, so the uptime states file arg will be lost on
any host where it had been configured by the ansible playbook. So to manually
reload the swiftlm_detect class and pass its args::

    $ sudo /opt/monasca/bin/monasca-setup -d swiftlmdetect \
        -a "metrics_files=/var/cache/swift/swiftlm_uptime_monitor/uptime.stats"

NB: the name of the monasca detect plugin passed with the -d arg is the name of
the python class, not the name of the python module file.

The uptime stats file should be here::

    $ sudo ls -l /var/cache/swift/swiftlm_uptime_monitor/uptime.stats

Querying monasca using monasca cli
----------------------------------

    export OS_PROJECT_NAME=admin
    export OS_PASSWORD=monasca
    export OS_AUTH_URL=http://padawan-ccp-vip-admin-KEY-API-mgmt:35357/v2.0
    export OS_USERNAME=monasca
    export OS_ENDPOINT_TYPE=internalURL
    export OS_CACERT=/etc/ssl/certs/ca-certificates.crt

To list metrics (NB: metric listing was broken at time of writing without the
workaround to install vertica described
here: https://jira.hpcloud.net/browse/JAH-1871)::

    $ monasca metric-list

To list the monasca alarm definitions to check swiftlm alarms are installed::

    $ monasca alarm-definition-list
    $ monasca alarm-definition-list |grep swiftlm

To see detail of the swiftlm alarm definition(s), use alarm definition ID from
above, e.g::

    $ monasca alarm-definition-show a3089c39-ce65-402e-a1bf-61775b572c7f

To see alarms::

    $ monasca alarm-list |grep swiftlm

To see measurements, in this case filtered for the swiftlm_check.task metrics
that result from plugin task failures::

    $ monasca measurement-list  swiftlm_check.task 2015-07-08T12:58:48.000Z \
        --merge_metrics --dimensions hostname=PADAWANBASE-CCP-T1-M1-NETCLM

To see results of swift_services check for the last minute (-1 argument)::

    $ monasca measurement-list swiftlm.swift.swift_services -1 --merge_metrics \
        --dimensions hostname=padawan-ccp-c1-m1-mgmt

The last minute might be too limiting, so also try with -2 (last two minutes).

You can add dimensions and remove --merge_metrics as follows::

    $ monasca measurement-list swiftlm.swift.swift_services -3 \
        --dimensions hostname=padawan-ccp-c1-m1-mgmt,component=account-server

It is possible to manually create metrics using the `monasca metric-create`
command.
