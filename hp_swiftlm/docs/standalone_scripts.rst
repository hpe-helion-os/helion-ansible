
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


Standalone Script Setup
=======================

Standalone scripts are placed in the `swiftlm/cli` directory.

To install the script it must be added to the `console_scripts`
section in `setup.py`::

    console_scripts=[
        'swiftlm-new-script = swiftlm.cli.new_script:main'
    ]

Scripts must have the prefix `swiftlm` to be installed correctly.
They should also have no file extension and use hyphens to separate words.

After the install the ansible playbooks will symlink anything in the created
anything with the correct prefix to `/usr/local/bin`.  This means that all
the swift scripts will be in `$PATH` and can be quickly called from the
command line.

Scripts should be run as standalone programs::

    $ swift-drive-provision
      # Or if /usr/local/bin is not in $PATH
    $ /usr/local/bin/swift-drive-provision

Attempting to run the script with python will cause errors and should
not be done::

    $ python /usr/local/bin/swift-drive-provision
      # This would cause the script to fail.
