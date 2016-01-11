
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


Swiftlm Documentation
=====================


Introduction
------------

The swiftlm project contains a number of features designed to help manage
and monitor Swift.

The main components in swiftlm as as follows:

* swiftlm-scan

  The swiftlm-scan utility comprises a number of checks and metric-measurement
  functions. When run, it scans the system and generates a list of metrics.
  The metrics are encoded in JSON. The format and layout of the metrics
  is designed to be compatible with Monasca. Howerver, since the data
  is encoded as JSON, it is possible to integrate the results with other
  monitoring systems.

* swiftlm_uptime_mon

  The swiftlm_uptime_mon program monitors the VIP if a Swift system and
  determines if the system is responding. It measures the uptime and
  latency of the Swift service.

* Monasca Agent for swiftlm

  This is a Monasca-Agent plug in. It's purpose is to report metrics generated
  by swiftlm-scan and swiftlm_uptime_mon to Monasca.

* swiftlm-ring-supervisor

  This utility is used to build and manage rings. The swiftlm-ring-supervisor
  is tightly integrated with the Helion Openstack Lifecycle Manager (HLM)
  data model. The concept is that you provide a declarative description of
  your cloud (the input model) and the swiftlm-ring-supervisor will
  figure out the appropriate ring changes so that the Swift system uses
  the cloud resources as specified in the input model.


Metric Information
------------------

The metrics produced by swiftlm are described in:

* `Metrics Produced by swiftlm-scan <swiftlm_scan_metrics.html>`_

* `Metrics Produced by swiftlm-uptime-mon <swiftlm_uptime_mon_metrics.html>`_

Developer Information
---------------------

* `Standalone Script Setup <standalone_scripts.html>`_

* `Monasca Plugin <monasca_plugin.html>`_

* `Developing swiftlm-scan Checks <test_runner.html>`_

Testing rst Files
-----------------

To test correctness of an rst file, run rst2html.py as follows::

    rst2html < blah.rst > ../build/blah.rst

Point your browser at something such as::

    file:///home/<path>/swiftlm/build/index.html

The rst2html.py utility is in docutils. Install as follows::

    pip install docutils




