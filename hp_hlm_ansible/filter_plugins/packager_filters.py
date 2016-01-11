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
# Load a "packages" manifest from a directory; cache these
# by default.

# Given such a dictionary, locate the latest version of a
# named package.


import os.path
import yaml

# J2 expressions are repeatedly re-evaluated.
# Often, we want to access a fixed file on disk.
# So, we cache results on a per-directory basis.

_packages = {}


def load_packages(dir_name, uncached=False):
    if not uncached and dir_name in _packages:
        return _packages[dir_name]

    with open(os.path.join(dir_name, "packages")) as f:
        manifest = yaml.safe_load(f)

    if not uncached:
        _packages[dir_name] = manifest

    return manifest


def package_max_version(manifest, package):
    packages = manifest['packages']
    if package in packages:
        return max(packages[package])


# Return a predictable path to the configuration directory
# or the binary directory for a service component.

# This relies on the service component being "activated" -
# that is, having an unversioned symlink in /opt/stack/service
# pointing to the current version.


def venv_dir(component, version=None):
    if version is None:
        return ("/opt/stack/service/{component}/venv"
                .format(component=component))
    return ("/opt/stack/service/{component}-{version}/venv"
            .format(component=component, version=version))


def config_dir(component, version=None):
    if version is None:
        return ("/opt/stack/service/{component}/etc"
                .format(component=component))
    return ("/opt/stack/service/{component}-{version}/etc"
            .format(component=component, version=version))


def bin_dir(component, version=None):
    if version is None:
        return ("/opt/stack/service/{component}/venv/bin"
                .format(component=component))
    return ("/opt/stack/service/{component}-{version}/venv/bin"
            .format(component=component, version=version))


def share_dir(component, version=None):
    if version is None:
        return ("/opt/stack/service/{component}/venv/share"
                .format(component=component))
    return ("/opt/stack/service/{component}-{version}/venv/share"
            .format(component=component, version=version))


def jar_dir(component, version=None):
    if version is None:
        return ("/opt/stack/service/{component}/venv/lib"
                .format(component=component))
    return ("/opt/stack/service/{component}-{version}/venv/lib"
            .format(component=component, version=version))


class FilterModule(object):

    def filters(self):
        return {'venv_dir': venv_dir,
                'config_dir': config_dir,
                'bin_dir': bin_dir,
                'share_dir': share_dir,
                'jar_dir': jar_dir,
                'load_packages': load_packages,
                'package_max_version': package_max_version}
