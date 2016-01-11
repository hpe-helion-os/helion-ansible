#!/usr/bin/env python
# encoding: utf-8

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

from optparse import OptionParser
from optparse import OptionParser
import sys
import subprocess
import os
from yaml import safe_load, safe_dump, scanner
from swiftlm.rings.hlm_model import InputModel
from swiftlm.rings.ring_builder import RingBuilder, RingDelta
from swiftlm.rings.ring_model import RingSpecifications, RingSpecification, \
    SwiftModelException, DriveConfigurations, DriveConfiguration

DEFAULT_ETC = '/etc/swiftlm'
DEFAULT_INPUT_VARS = 'input-model.yml'
DEFAULT_BUILDER_DIR = 'builder_dir'
DEFAULT_HOSTS = 'hosts.hf'
DEFAULT_SWIFT_RING_BUILDER_CONSUMES = 'swift_ring_builder_consumes.yml'
DEFAULT_RING_DELTA = os.path.join('deploy_dir', 'ring-delta.yml')
DEFAULT_OSCONFIG = 'drive_configurations'

usage = '''

    % {cmd} [--make-delta [--weight-step <value> ] [--stop-on-warnings]]
            [--rebalance [--dry-run]]
            [--report [--detail=summary|full]]
            [--etc <dirname>]
            [--input-vars <filename> --hosts <hosts-file>
            [--swift-ring-builder-consumes <swift-ring-builder-consumes-file>]
            [--osconfig <dirname>]
            [--builder_dir <dirname>]
            [--ring-delta <filename> [--format yaml|json]
            [--storage-policies --region-name <region-name>]
            [--help]

Examples:

    Example 1:

    Create a ring-delta file given an input model and (possibly) existing
    rings. The results are written to the ./ring-delta.yml file. If a ring
    does not exist in ./builder_dir, the ring-delta file will contain
    directives to create the ring.

    % {cmd} --make-delta
            --input-vars ./input-model.yml --hosts ./hosts.hf
            --swift-ring-builder-consumes ./swift-ring-builder-consumes.yml
            --builder_dir ./builder_dir
            --osconfig ./osconfig
            --ring-delta ./ring-delta.yml

    Example 2:

    Update and rebalance (usually existing) rings given a ring-delta file.
    The command reads the ./ring-delta.yml file and updates the rings
    in ./builder_dir. Add --dry-run to see what commands would be issued
    to swift-ring-builder:

    % {cmd} --rebalance
            --builder_dir ./builder_dir
            --ring-delta ./ring-delta.yml

    Example 3:
    Rebalance existing rings. This is similar to the above command except
    there is no ring-delta file to process.

    % {cmd} --rebalance
            --builder_dir ./builder_dir

    Example 4:

    Build, update and rebalance rings given an input model and (possibly)
    existing rings. This command compresses examples 1 and 2 above into
    a single command.

    % {cmd} --make-delta --rebalance
            --input-vars ./input-model.yml --hosts ./hosts.hf
            --swift-ring-builder-consumes ./swift-ring-builder-consumes.yml
            --builder_dir ./builder_dir
            --osconfig ./osconfig
            --ring-delta /tmp/ring-delta.json --format json

    Example 5:

    Rebalance rings after adding or removing a number of servers
    The --weight-step option prevents weights being moved too
    quickly on the new servers. --weight-step is only needed if it
    is not present in the ring-specifications.

    % {cmd} --make-delta --rebalance --weight-step 4.0

    Example 6:

    Print storage policy information (useful in ansible playbooks)
    about a specific region:

    % {cmd} --storage-policies --region-name region1
            --input-vars ./group_vars/all

    Example 7:

    Show  the actions that would be performed if a --rebalance is performed
    using a ring delta file as specified by the --ring-delta option. These
    variants give different levels of detail:

    % {cmd} --report --detail summary
            --builder-dir ./builder_dir --ring-delta /tmp/ring-delta.yaml

    % {cmd} --report --detail detail
            --builder-dir ./builder_dir --ring-delta /tmp/ring-delta.yaml

    % {cmd} --make-delta --rebalance --dry-run
            --builder-dir ./builder_dir --ring-delta /tmp/ring-delta.yaml

    '''.format(cmd=os.path.basename(__file__))


def main():
    parser = OptionParser(usage=usage)
    parser.add_option('--etc', dest='etc',
                      default=DEFAULT_ETC,
                      help='Overrides /etc/swiftlm (for testing)')
    parser.add_option('--input-vars', dest='input_vars', default=None,
                      help='The name of yaml containing vars')
    parser.add_option('--builder-dir', dest='builder_dir', default=None,
                      help='Builder file directory')
    parser.add_option('--osconfig', dest='osconfig', default=None,
                      help='Directory where drive size data files exist.'
                           ' If omitted, the correct weights cannot'
                           ' be assigned to drives.')
    parser.add_option('--hosts', dest='hosts', default=None,
                      help='Hosts file (/etc/hosts or ./net/hosts.hf)')
    parser.add_option('--swift-ring-builder-consumes',
                      dest='swift_ring_builder_consumes',
                      default=None,
                      help='File containing the SWF_RNG variable')
    parser.add_option('--ring-delta', dest='ring_delta', default=None,
                      help='Name of ring-delta file (as output or input'
                           ' A value of "-" (on output means to write'
                           ' to stdout')
    parser.add_option('--format', dest='fmt', default='yaml',
                      help='One of yaml or json.'
                           ' When used with --ring-delta, specifies the'
                           ' format of the file.')
    parser.add_option('--detail', dest='detail', default='summary',
                      help='Level of detail to use with --report.'
                           ' Use summary or full')
    parser.add_option('--report', dest='report', default=False,
                      action="store_true",
                      help='Explain what the ring delta represents.'
                           ' Optionally use --detail.')
    parser.add_option('--dry-run', dest='dry_run', default=False,
                      action="store_true",
                      help='Show the proposed swift-ring-builder commands')
    parser.add_option('--make-delta', dest='make_delta', default=False,
                      action="store_true",
                      help='Make a ring delta file')
    parser.add_option('--rebalance', dest='rebalance', default=False,
                      action="store_true",
                      help='Build (or rebalance) rings')
    parser.add_option('--storage-policies', dest='storage_policies',
                      default=False,
                      action="store_true",
                      help='Extract storage policy data.'
                           ' Use this to register the storage_policies'
                           ' variable.')
    parser.add_option('--region-name', dest='region_name', default=None,
                      help='Region name for use with --storage-policies')
    parser.add_option('--size-to-weight', dest='size_to_weight',
                      default=float(1024 * 1024 * 1024),
                      help='Conversion factor for size to weight. Default is'
                           ' 1GB is weight of 1 (a 4Tb drive would be assigned'
                           ' a weight of 4096')
    parser.add_option('--weight-step', dest='weight_step',
                      default=None,
                      help='When set, weights are changed by at most this'
                           ' value. Overrides value in ring specification.')
    parser.add_option('--allow-partitions', dest='allow_partitions',
                      default=False, action='store_true',
                      help='Allow devices to be assigned to partitions.'
                           ' Default is to use a full disk drive.')
    parser.add_option('--stop-on-warnings', dest='stop_on_warnings',
                      default=False, action='store_true',
                      help='Used with --make-delta. Exit with error if there'
                           ' are model missmatch warnings.'
                           ' Default is to only exit with error for errors.')
    (options, args) = parser.parse_args()

    if not options.input_vars:
        options.input_vars = os.path.join(options.etc, DEFAULT_INPUT_VARS)
    if not options.builder_dir:
        options.builder_dir = os.path.join(options.etc, DEFAULT_BUILDER_DIR)
    if not options.hosts:
        options.hosts = os.path.join(options.etc, DEFAULT_HOSTS)
    if not options.swift_ring_builder_consumes:
        options.swift_ring_builder_consumes = os.path.join(
            options.etc, DEFAULT_SWIFT_RING_BUILDER_CONSUMES)
    if not options.ring_delta:
        options.ring_delta = os.path.join(options.etc, DEFAULT_RING_DELTA)
    if not options.osconfig:
        options.osconfig = os.path.join(options.etc, DEFAULT_OSCONFIG)

    #
    # Work out what we need to do. Validate arguments needed by an action
    # are present.
    #
    actions = []
    if options.storage_policies:
        actions.append('input-from-model')
        actions.append('emit-storage-policies')

        if not options.region_name:
            print('Need --region-name')
            sys.exit(1)

    if options.make_delta:
        actions.append('init-delta')
        actions.append('input-from-model')
        actions.append('read-builder-dir')
        actions.append('open-osconfig-dir')
        actions.append('make-delta')
        actions.append('write-to-delta')

        if not options.ring_delta:
            print('Need --ring-delta file to write to')
            sys.exit(1)
        if not (options.input_vars and options.hosts and
                options.osconfig and options.swift_ring_builder_consumes):
            print('Need --input-vars, --hosts and --osconfig and'
                  ' --swift-ring-builder-consumes inputs')
            sys.exit(1)
        if not options.builder_dir:
            print('Need --builder-dir option')
            sys.exit(1)
        if options.fmt not in ['yaml', 'json']:
            print('Invalid value for --format')

    if options.report:
        actions.append('init-delta')
        actions.append('read-from-delta')
        actions.append('report')

        if not options.ring_delta:
            print('Need --ring-delta file as input')
            sys.exit(1)
        if options.detail not in ['summary', 'full']:
            print('Invalid value for --detail')
            sys.exit(1)

    if options.rebalance:
        actions.append('init-delta')
        actions.append('open-builder-dir')
        actions.append('read-from-delta')
        actions.append('rebalance')

        if not options.ring_delta:
            print('Need --ring-delta file as input')
            sys.exit(1)
        if options.fmt not in ['yaml', 'json']:
            print('Invalid value for --format')

    if len(actions) == 0:
        print('Missing an option to perform some action')
        sys.exit(1)
    if options.storage_policies and (options.make_delta or
                                     options.rebalance or
                                     options.report):
        print('Do not mix --storage-policies with other actions')
        sys.exit(1)
    if options.report and (options.make_delta or
                           options.rebalance or
                           options.storage_policies):
        print('Do not mix --report with other actions')
        sys.exit(1)

    #
    # Perform actions
    #
    if 'init-delta' in actions:
        delta = RingDelta()

    if 'input-from-model' in actions:
        try:
            input_model_fd = open(options.input_vars, 'r')
            hosts_fd = open(options.hosts, 'r')
            consumes_fd = open(options.swift_ring_builder_consumes, 'r')
        except IOError as err:
            print('ERROR: %s' % err)
            sys.exit(1)
        try:
            input_vars = safe_load(input_model_fd)
            consumes_model = safe_load(consumes_fd)
        except scanner.ScannerError as err:
            print('ERROR in %s: %s' % (options.input_vars, err))
            sys.exit(err)
        try:
            input_model = InputModel(config=input_vars, hosts_fd=hosts_fd,
                                     consumes=consumes_model)
            ring_model = RingSpecifications(model=input_vars)
        except SwiftModelException as err:
            sys.exit(err)

    if 'emit-storage-policies' in actions:
        obj_ring_policies = ring_model.get_storage_policies(
            options.region_name)
        print('%s' % safe_dump(obj_ring_policies, default_flow_style=False))

        # Unlike the following actions, we exit after this action
        sys.exit(0)

    if 'open-builder-dir' or 'read-builder-dir' in actions:
        try:
            read_write = False
            if 'read-builder-dir' in actions:
                read_write = True
            rings = RingBuilder(options.builder_dir, True)
        except IOError as err:
            print('ERROR: %s' % err)
            sys.exit(1)

    if 'open-osconfig-dir' in actions:
        drive_configurations = osconfig_load(options.osconfig)

    if 'make-delta' in actions:
        try:
            generate_delta(input_model, ring_model, rings,
                           drive_configurations, options, delta)
        except SwiftModelException as err:
            print('ERROR: %s' % err)
            sys.exit(1)

    if 'write-to-delta' in actions:
        if options.ring_delta == '-':
            write_to_file_fd = sys.stdout
        else:
            write_to_file_fd = open(options.ring_delta, 'w')
        delta.write_to_file(write_to_file_fd, options.fmt)

    if 'read-from-delta' in actions:
        if options.ring_delta == '-':
            print('--ring-delta=- is invalid (read from stdin not supported)')
            sys.exit(1)
        try:
            delta = RingDelta()
            read_from_delta_fd = open(options.ring_delta, 'r')
            delta.read_from_file(read_from_delta_fd, options.fmt)
        except IOError as err:
            print('ERROR: %s' % err)
            sys.exit(1)

    if 'report' in actions:
        print(delta.get_report(options.detail))

    if 'rebalance' in actions:
        rebalance(delta, rings, options.dry_run)


def osconfig_load(osconfig_dir):
    drive_configurations = DriveConfigurations()
    for host in os.listdir(osconfig_dir):
        filename = os.path.join(osconfig_dir, host, 'drive_configuration.yml')
        if os.path.exists(filename):
            with open(filename) as fd:
                try:
                    model_in_file = safe_load(fd)
                    drive_configuration = DriveConfiguration()
                    items = model_in_file.get('hlm_drive_configuration', [])
                    for item in items:
                        drive_configuration.load_model(item)
                        drive_configurations.add(drive_configuration)
                except IOError as err:
                    print('ERROR: %s' % err)
                    sys.exit(1)
    return drive_configurations


def generate_delta(input_model, ring_model, rings, drive_configurations,
                   options, delta):
    """
    Generate delta between input model and existing rings
    :param input_model: The input
    :param ring_model: Ring specifications (from input model)
    :param rings: The existing rings
    :param drive_configurations: device size data from probing hardware
    :param options: options to control ring building
    :param delta: The delta to generate
    :return: Nothing -- the output is in the delta argument
    """

    model_errors = []
    model_warnings = []

    # Run through the input model and find ring specifications
    for ksregion in ring_model.keystone_ring_specifications:
        region_name = ksregion.region_name
        for ringspec in ksregion.rings:
            ring_name = ringspec.name
            delta.register_ring(region_name, ring_name, ringspec)
            if not rings.builder_rings.get((region_name, ring_name)):
                # Ring is in input model, but no builder file exists
                delta.delta_ring_actions[(region_name,
                                          ring_name)] = ['add']

    # Cross check that we have ring specifications for each region referenced
    # by servers in the input model.
    try:
        device_regions = set()
        ringspec_regions = set()
        for device_info in input_model.iter_devices():
            device_regions.add(device_info.region_name)
        for ksregion in ring_model.keystone_ring_specifications:
            region_name = ksregion.region_name
            ringspec_regions.add(region_name)
        for region_name in device_regions:
            if region_name not in ringspec_regions:
                model_errors.append('Model Mismatch:'
                                    ' Cannot find rings for region %s'
                                    ' in the ring-specifications.'
                                    ' This error may cause many subsequent'
                                    ' errors.' %
                                    region_name)
        for region_name in ringspec_regions:
            if region_name not in device_regions:
                model_warnings.append('Warning: The ring-specifications'
                                      ' have rings for region %s. However,'
                                      ' there are no Swift disk devices using'
                                      ' these rings.' % region_name)
    except SwiftModelException as err:
        model_errors.append(err)

    # Run through the builder files and match them against the model
    for region_name, ring_name in rings.builder_rings.keys():
        if delta.delta_rings.get((region_name, ring_name)):
            # Ring already exists
            delta.delta_ring_actions[(region_name,
                                      ring_name)] = ['present']
            # See if replica count in model has changed
            model_ring = ring_model.get_ringspec(region_name, ring_name)
            builder_ring = rings.get_ringspec(region_name, ring_name)
            if model_ring.replica_count != builder_ring.replica_count:
                delta.delta_ring_actions[(region_name, ring_name)].append(
                    'set-replica-count')
        else:
            # Found builder file, but ring not in model anymore
            delta.register_ring(region_name, ring_name,
                                rings.builder_rings.get(region_name,
                                                        ring_name))
            delta.delta_ring_actions[(region_name, ring_name)] = ['remove']

    # Run through all devices in the input model
    try:
        for device_info in input_model.iter_devices():

            # Update the device info with the region and zone id from the
            # ring specifications.
            if device_info.rack_id:
                region_id, zone_id = ring_model.get_region_zone(
                    device_info.region_name, device_info.ring_name,
                    device_info.rack_id,)
            else:
                # For now, allow null rack ids in the input vars
                region_id, zone_id = (-1, -1)
            not_found_in = ''
            if not region_id:
                not_found_in = 'swift-regions'
            if not zone_id:
                not_found_in = 'swift-zones'
            if not_found_in:
                model_errors.append('Model Mismatch:'
                                    ' Cannot find rack %s in'
                                    ' "ring-specifications". Check the "%s"'
                                    ' item for region %s ring %s.'
                                    ' Server is %s' % (device_info.rack_id,
                                                       not_found_in,
                                                       device_info.region_name,
                                                       device_info.ring_name,
                                                       device_info.server_name)
                                    )
            # -1 means not defined, default to 1
            if region_id == -1:
                region_id = 1
            if zone_id == -1:
                zone_id = 1
            device_info.region_id = region_id
            device_info.zone_id = zone_id

            # See if the device is in a builder file of an existing ring
            found = False
            for in_ring_device_info in rings.flat_device_list:
                if device_info.is_same_device(in_ring_device_info):
                    found = True
                    break

            for ip_address in input_model.aliases(device_info.server_ip):
                hw_size, hw_fulldrive = drive_configurations.get_hw(
                    ip_address, device_info)
                if hw_size:
                    break

            if found:
                device_info.presence = 'present'
                if hw_size:
                    target_weight = '{:.2f}'.format(
                        float(hw_size) / float(options.size_to_weight) or 1.0)
                    current_weight = '{:.2f}'.format(
                        float(in_ring_device_info.weight))
                    step = (options.weight_step or
                            ring_model.get_weight_step(
                                device_info.region_name,
                                device_info.ring_name) or
                            target_weight)
                    change = float(target_weight) - float(current_weight)
                    if change > 0:
                        # Weight being changed upwards
                        target_weight = min(float(target_weight),
                                            float(current_weight) +
                                            float(step))
                        target_weight = '{:.2f}'.format(
                            float(target_weight))
                    elif change < 0:
                        target_weight = max(float(target_weight),
                                            float(current_weight) -
                                            float(step))
                        target_weight = '{:.2f}'.format(
                            float(target_weight))
                    else:
                        # Unchanged
                        target_weight = current_weight
                    if target_weight != current_weight:
                        weight = target_weight
                        device_info.weight = weight
                        device_info.presence = 'set-weight'
                    else:
                        # Unchanged
                        device_info.weight = in_ring_device_info.weight
                else:
                    # Do not have size information for the drive. Lets assume
                    # the existing weight is ok
                    device_info.weight = in_ring_device_info.weight
            else:
                device_info.presence = 'add'
                if not hw_size:
                    model_errors.append('Model Mismatch:'
                                        ' Cannot find drive %s on'
                                        ' %s (%s)' % (device_info.device_name,
                                                      device_info.server_name,
                                                      device_info.server_ip))
                elif not hw_fulldrive and not options.allow_partitions:
                    model_errors.append('Model Mismatch:'
                                        ' Drive %s on %s (%s) has'
                                        ' several partitions' %
                                        (device_info.device_name,
                                         device_info.server_name,
                                         device_info.server_ip))
                else:
                    target_weight = '{:.2f}'.format(
                        float(hw_size) / float(options.size_to_weight) or 1.0)
                    weight_step = (options.weight_step or
                                   ring_model.get_weight_step(
                                       device_info.region_name,
                                       device_info.ring_name))
                    if weight_step:
                        if (float(target_weight) > float(weight_step)):
                            target_weight = '{:.2f}'.format(float(weight_step))
                    device_info.weight = target_weight
            delta.append_device(device_info)
    except SwiftModelException as err:
        model_errors.append(err)
    delta.sort()

    # Run through all devices in builder files
    for in_ring_device_info in rings.flat_device_list:
        found = False
        for device_info in input_model.iter_devices():
            if device_info.is_same_device(in_ring_device_info):
                found = True
                break
        if not found:
            in_ring_device_info.presence = 'remove'
            delta.append_device(in_ring_device_info)

    if model_errors:
        for model_error in model_errors:
            print(model_error)
        raise SwiftModelException('There are errors or mismatches between'
                                  ' the input model and the configuration'
                                  ' of server(s).\n'
                                  ' Cannot proceed. Correct the errors'
                                  ' and try again')
    if model_warnings and options.stop_on_warnings:
        for model_warning in model_warnings:
            print(model_warning)
        raise SwiftModelException('There are minor mismatches between the'
                                  ' input model and the configuration of'
                                  ' servers. These are warning severity.'
                                  ' We recommend you correct the errors.')


def rebalance(delta, rings, dry_run):

    for region_name, ring_name in delta.delta_rings.keys():
        if not os.path.isdir(rings.builder_dir):
            os.mkdir(rings.builder_dir)
        if not os.path.isdir(os.path.join(rings.builder_dir,
                                          'region-%s' %
                                          region_name)):
            os.mkdir(os.path.join(rings.builder_dir, 'region-%s' %
                                  region_name))
    cmds = []
    for region_name, ring_name in delta.delta_rings.keys():
        if 'add' in delta.delta_ring_actions.get((region_name, ring_name)):
            ringspec = delta.delta_rings.get((region_name, ring_name))
            cmds.append(rings.command_ring_create(region_name, ringspec))
        if 'set-replica-count' in delta.delta_ring_actions.get((region_name,
                                                                ring_name)):
            ringspec = delta.delta_rings.get((region_name, ring_name))
            cmds.append(rings.command_set_replica_count(region_name, ringspec))

    for device_info in delta.delta_devices:
        if device_info.presence == 'add':
            cmds.append(rings.command_device_add(device_info))
        elif device_info.presence == 'remove':
            cmds.append(rings.command_device_remove(device_info))
        elif device_info.presence == 'set-weight':
            cmds.append(rings.command_device_set_weight(device_info))

    for region_name, ring_name in delta.delta_rings.keys():
        ringspec = delta.delta_rings.get((region_name, ring_name))
        cmds.append(rings.command_rebalance(region_name, ringspec))

    if dry_run:
        for cmd in cmds:
            print('DRY-RUN: %s' % cmd)

    else:
        for cmd in cmds:
            print('Running: %s' % cmd)
            status, output = rings.run_cmd(cmd)
            if status > 0:
                print('ERROR: %s' % output)
                sys.exit(status)
            elif status < 0:
                print('NOTE: %s' % output)
    return cmds

if __name__ == '__main__':
    main()
