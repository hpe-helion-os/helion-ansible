#!/usr/bin/env python
#
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

import os

import setuptools


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


def requirements():
    here = os.path.abspath(os.path.dirname(__name__))
    with open(here + '/requirements.txt', 'r') as f:
        return [y.strip() for y in f.readlines() if y.strip()]
reqs = requirements()

setuptools.setup(
    name="cinderlm",
    version="0.0.2",
    description="Lifecycle management for cinder",
    long_description=read('README.md'),
    author="Hewlett Packard Enterprise Development Company, L.P.",
    classifiers=[
        "Development Status :: 1 - Alpha",
        "Topic :: Utilities",
        "License :: OSI Approved :: Apache 2.0",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 2.6",
    ],

    packages=setuptools.find_packages(exclude=['docs', 'etc', 'tests']),
    install_requires=reqs,
    entry_points={
        'console_scripts': [
            'cinder_check = cinderlm.cinder_check:main',
            'cinder_diag = cinderlm.cinder_diag:main',
        ],
    },
)
