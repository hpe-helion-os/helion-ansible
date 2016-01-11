
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


Developing swiftlm-scan Checks
==============================

Adding a Check
--------------

If it fits into theme of an existing folder place it there and register it (see below).

If the check does not fit into the current folder structure,
create a new folder and inside that folder place a blank `__init__.py`
file and add your check script.

Registering a Check
-------------------

Checks must have a function named `main` that is the entry point to the
check.

The docstring for the main function will become the console help
text for the check and so should be short but describe what the
check accomplishes.

Registering a check requires you to add it to the `setup.py` file.
See Below for an example::

      # With the directory structure below.
    $ touch swiftlm/swift/new_check.py
    $ cat<<END > swiftlm/swift/new_check.py
    def main():
        """ Command line help text relevant to new check. """
        print('new check ok')
    END

This sets up an example check file.
Real checks should return a list of or an individual `MetricData` instance
which is converted to monasca output (See other checks for an example of how to do this).

You then need to edit the `setup.py` file and enter the check in the `entry_points`
section.

Checks are entered in the `swiftlm.plugins` list.
The example below show how the entry will look. Other sections may be present
but are not relevant to adding a new check::

    entry_points={
        'swiftlm.plugins': [
            'new-check = swiftlm.swift.new_check:main',
        ],
    }

`new-check` is the name of the check at the command line.

Names are not required to name match to their file names but its a good
convention.
Running the new check is then just a matter of updating the swiftlm installation
and running it::

    $ swift-scan --new-check

Will run the check by itself::

    $ swift-scan

If no flags are passed to `swift-scan` all checks including `new-check` are
run. This does not need to be configured beyond adding the check to `setup.py`

Line length limits are not enforced on the `setup.py` file because of the
levels of indentation and long import paths.

At the time of writing there are some reserved names, these are:

* h
* help
* v
* verbose
* format
