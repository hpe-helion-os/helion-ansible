#! /usr/bin/env python
#
# A Python module to combine baremetalConfig.yml and servers.yml
# Command line args are a path to a baremetalConfig.yml and a path
# to a servers.yml file. Output is YAML to stdout.
#
# (c) Copyright 2015 Hewlett Packard Enterprise Development Company
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http:www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
import datetime
import os
import sys
import yaml

cp_primary_key = 'ip-addr'
bm_primary_key = 'pxe_ip_addr'

already_done_msg = 'CP input is already combined'

class CPnetwork(object):
    def __init__(self, bm_data):
        # Fields not listed here will be dropped from the incoming BM
        # data. This is deliberate because old BM files often contain
        # obsolete fields aka noise.
        self.data = {
            'subnet': bm_data['subnet'],
            'netmask': bm_data['netmask'],
            'server-interface': bm_data['server_interface']
        }

    def render(self):
        return self.data


class CPserver(object):
    # Fields not listed here will be dropped from the incoming BM
    # data. This is deliberate because old BM files often contain
    # obsolete fields aka noise. Per-node fields that already have
    # equivalents in servers.yml are *deliberately* omitted because
    # we want the values coming from servers.yml to take precedence.
    fieldmap = {
        'pxe_mac_addr': 'mac-addr',
        'ilo_ip': 'ilo-ip',
        'ilo_user': 'ilo-user',
        'ilo_password': 'ilo-password',
        'ilo_extras': 'ilo-extras',
        'kopt_extras': 'kopt-extras',
        'kopts_extra': 'kopt-extras',
        'moonshot': 'moonshot' }

    def __init__(self, existing_data):
        self.data = existing_data

    def merge(self, bm_data):
        if self.data[cp_primary_key] != bm_data[bm_primary_key]:
            raise ValueError('primary key mismatch ("%s", "%s")' %
                             (self.data[cp_primary_key], bm_data[bm_primary_key]))
        for (key, value) in bm_data.iteritems():
            if key in self.data:
                # Existing data from servers.yml takes precedence.
                continue
            try:
                key = self.fieldmap[key]
                self.data[key] = value
            except KeyError:
                # Obsolete field - noise.
                pass

    def render(self):
        return self.data


class CPserverlist(object):
    def __init__(self, cp_yaml, bm_yaml):
        if bm_yaml['product'] != cp_yaml['product']:
            raise AttributeError(
                'incompatible versions %s and %s' %
                (bm_yaml['product'], cp_yaml['product']))
        bm_server_list = bm_yaml['baremetal_servers']
        self.servers = list()
        for item in cp_yaml['servers']:
            primary = item[cp_primary_key]
            cp_server = CPserver(item)
            for bm_item in bm_server_list:
                if primary == bm_item[bm_primary_key]:
                    cp_server.merge(bm_item)
                    break
            else:
                print >> sys.stderr, 'no BM data for %s %s' % (cp_primary_key, primary)
                # TODO Raise an error? I checked with our model architects... no.
            self.servers.append(cp_server)

    def render(self):
        return [item.render() for item in self.servers]


class CPmerged(object):
    def __init__(self, cp_yaml, bm_yaml):
        if 'baremetal' in cp_yaml:
            raise AttributeError(already_done_msg)
        self.product = cp_yaml['product']
        self.cp_net = CPnetwork(bm_yaml['baremetal_network'])
        self.cp_servers = CPserverlist(cp_yaml, bm_yaml)

    def render(self):
        result = {
            'product': self.product,
            'baremetal': self.cp_net.render(),
            'servers': self.cp_servers.render() }
        return result


def combine(cp_file, bm_file):
    cp_yaml = yaml.safe_load(cp_file)
    bm_yaml = yaml.safe_load(bm_file)
    obj = CPmerged(cp_yaml, bm_yaml)
    return obj.render()


def get_header(cp_file):
    result = ''
    for line in cp_file:
        l2 = line.lstrip()
        if len(l2) == 0 or l2[0] == '#':
            result += line
        else:
            break
    return result


def main():
    if len(sys.argv) != 3:
        print >> sys.stderr, 'usage: %s <baremetalConfig.yml> <servers.yml>' % sys.argv[0]
        exit(22)

    bm_file = file(sys.argv[1])
    cp_file = file(sys.argv[2])

    header = get_header(cp_file)
    cp_file.seek(0)
    try:
        result = combine(cp_file, bm_file)
    except AttributeError as e:
        if str(e) == already_done_msg:
            print >> sys.stderr, already_done_msg
            exit(22)
        else:
            raise e

    # dump will produce valid YAML, but is difficult to read for humans,
    # so let's go with print statements to make the output as close to the
    # existing manual style used in our examples.
    # print yaml.dump(result, default_flow_style=False)

    print header
    print '# Autogenerated %sZ' % datetime.datetime.utcnow().isoformat()
    print '# baremetal: %s' % sys.argv[1]
    print '# CP: %s' % sys.argv[2]

    product = result['product']
    net = result['baremetal']
    servers = result['servers']
    print '''---
  product:
    version: %s

  baremetal:
    subnet: %s
    netmask: %s
    server-interface: %s

  servers:''' % (product['version'], net['subnet'], net['netmask'], net['server-interface'])

    mandatory = ('id', 'ip-addr', 'role')
    for svr in servers:
        print '''
    - %s: %s''' % (mandatory[0], svr[mandatory[0]])
        for key in mandatory[1:]:
            print '      %s: %s' % (key, svr[key])
        for key in sorted(svr.keys()):
            if key in mandatory:
                continue
            print '      %s: %s' % (key, svr[key])

if __name__ == '__main__':
    main()
