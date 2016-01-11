#!/usr/bin/python

# (c) Copyright 2015 Hewlett Packard Enterprise Development Company LP
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#


from setuptools import setup, find_packages
from codecs import open
from os import path


here = path.abspath(path.dirname(__name__))


def requirements():
    with open(here + '/requirements.txt', 'r') as f:
        return [y.strip() for y in f.readlines() if y.strip()]


setup(
    name='swiftlm',
    version='0.1.0',
    description='Lifecycle management for Openstack Swift systems',
    author='Hewlett-Packard Development Company, L.P',
    license='Apache 2.0',
    classifers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: Apache 2.0',

        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
    ],
    keywords='Openstack Swift',
    packages=find_packages(exclude=['docs', 'etc', 'tests']),
    install_requires=requirements(),
    entry_points={
        'console_scripts': [
            'swiftlm-scan = swiftlm.cli.runner:main',
            'swiftlm-uptime-mon = swiftlm.cli.uptime_mon:main',
            'swiftlm-ring-supervisor = swiftlm.cli.supervisor:main',
            'swiftlm-drive-provision = swiftlm.cli.drive_provision:main',
        ],
        'swiftlm.plugins': [
            'check-mounts = swiftlm.systems.check_mounts:main',
            'connectivity = swiftlm.systems.connectivity:main',
            'drive-audit = swiftlm.swift.drive_audit:main',
            'file-ownership = swiftlm.swift.file_ownership:main',
            'swift-services = swiftlm.swift.swift_services:main',
            'network-interface = swiftlm.generic_hardware.network_interface:main',
            'replication = swiftlm.swift.replication:main',
            'hpssacli = swiftlm.hp_hardware.hpssacli:main',
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
