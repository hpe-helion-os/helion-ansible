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


import unittest
from yaml import safe_load
import os
import tempfile

from swiftlm.cli.supervisor import generate_delta, rebalance
from swiftlm.rings.ring_model import RingSpecifications, RingSpecification,\
    DeviceInfo, DriveConfiguration, DriveConfigurations, SwiftModelException, \
    KeystoneRegionRings
from swiftlm.rings.hlm_model import InputModel, DeviceInfo
from swiftlm.rings.ring_builder import RingDelta, RingBuilder

from tests.data.ring_padawan import padawan_input_model, padawan_net_hosts, \
    padawan_swf_rng_consumes, padawan_drive_configurations, expected_cmds


class FakeRingBuilder(RingBuilder):

    def __init__(self, builder_dir, region_name, fake_rings, replica_count):
        super(FakeRingBuilder, self).__init__(builder_dir, False)
        for ring_name in fake_rings:
            self.register_ring(region_name, ring_name, replica_count, 100)

    def load_fake_ring_data(self, delta):
        for device_info in delta.delta_devices:
            self.flat_device_list.append(device_info)

    def fake_set_weights(self, new_weight):
        for device_info in self.flat_device_list:
            device_info['weight'] = new_weight


class DummyInputOptions(object):

    def __init__(self):
        self.size_to_weight = float(1024 * 1024 * 1024)
        self.allow_partitions = False
        self.stop_on_warnings = True
        self.weight_step = None


def dummy_osconfig_load(text):
    model = safe_load(text)
    drive_configurations = DriveConfigurations()
    for dc_model in model.get('hlm_drive_configuration'):
        drive_configuration = DriveConfiguration()
        drive_configuration.load_model(dc_model)
        drive_configurations.add(drive_configuration)
    return drive_configurations


def cmd_key(cmd):
    """ Sort key on builder file, then command, then args """
    verb, ringname, args = cmd
    return ringname + '.' + verb + '.' + '.'.join(args)


def cmd_parse(text):
    """ Get rid of spurious differences """
    if text == '':
        return None
    words = text.split()
    if len(words) == 0:
        return None
    ringname = os.path.basename(words[1])
    verb = words[2]
    args = words[3:]
    return (verb, ringname, args)


def assert_cmds_are_same(test_case, expected, actual):
    expected_args = []
    actual_args = []
    for cmd in expected:
        cmd_tuple = cmd_parse(cmd)
        if cmd_tuple:
            expected_args.append(cmd_tuple)

    for cmd in actual:
        cmd_tuple = cmd_parse(cmd)
        if cmd_tuple:
            actual_args.append(cmd_tuple)

    # test_case.maxDiff = None
    expected_args.sort(key=cmd_key)
    actual_args.sort(key=cmd_key)
    test_case.assertEquals(expected_args, actual_args)


def verb_ringname_args_in_cmds(verb, ringname, args, cmds):
    for cmd in cmds:
        cmdverb, cmdringname, cmdargs = cmd_parse(cmd)
        if cmdverb == verb and cmdringname == ringname:
            if not cmdargs:
                return True  # verb, ring match; don't care about args
            if cmdargs == args:
                return True  # verb, ring, args match
    return False


def cleanup(path):
    for name in os.listdir(path):
        if os.path.isdir(os.path.join(path, name)):
            cleanup(os.path.join(path, name))
        else:
            os.unlink(os.path.join(path, name))
    os.rmdir(path)


class TestPadawan(unittest.TestCase):

    def setUp(self):
        # Use to generate temporary name
        tf = tempfile.NamedTemporaryFile()
        self.builder_dir = os.path.basename(tf.name) + '-swiftlm-builder-dir'
        os.mkdir(self.builder_dir)

    def tearDown(self):
        cleanup(self.builder_dir)

    def test_build_rings(self):
        options = DummyInputOptions()
        input_model = InputModel(config=safe_load(padawan_input_model),
                                 hosts_fd=padawan_net_hosts,
                                 consumes=padawan_swf_rng_consumes)
        ring_model = RingSpecifications(model=safe_load(
                                        padawan_input_model))
        rings = RingBuilder(self.builder_dir, False)
        drive_configurations = dummy_osconfig_load(
            padawan_drive_configurations)
        delta = RingDelta()
        generate_delta(input_model, ring_model, rings,
                       drive_configurations, options, delta)
        cmds = rebalance(delta, rings, True)
        assert_cmds_are_same(self, expected_cmds, cmds)

    def test_missmatched_region_names(self):
        options = DummyInputOptions()
        input_model = InputModel(config=safe_load(padawan_input_model),
                                 hosts_fd=padawan_net_hosts,
                                 consumes=padawan_swf_rng_consumes)
        ring_model = RingSpecifications(model=safe_load(padawan_input_model))
        rings = RingBuilder(self.builder_dir, False)
        drive_configurations = dummy_osconfig_load(
            padawan_drive_configurations)
        delta = RingDelta()

        # Change region_name in rings
        for region_rings in ring_model.keystone_ring_specifications:
            region_rings.region_name = 'junk'
        self.assertRaises(SwiftModelException, generate_delta, input_model,
                          ring_model, rings, drive_configurations, options,
                          delta)
        # Put back original
        ring_model = RingSpecifications(model=safe_load(padawan_input_model))

        # Add a region - but not used
        keystone_region_rings = KeystoneRegionRings(self)
        keystone_region_rings.region_name = 'unusedrregion'
        ring_model.keystone_ring_specifications.append(keystone_region_rings)
        # Does not stop
        options.stop_on_warnings = False
        generate_delta(input_model, ring_model, rings,
                       drive_configurations, options, delta)
        # Stops on warnings
        options.stop_on_warnings = True
        self.assertRaises(SwiftModelException, generate_delta, input_model,
                          ring_model, rings, drive_configurations, options,
                          delta)

    def test_change_replica_count(self):
        options = DummyInputOptions()
        input_model = InputModel(config=safe_load(padawan_input_model),
                                 hosts_fd=padawan_net_hosts,
                                 consumes=padawan_swf_rng_consumes)
        ring_model = RingSpecifications(model=safe_load(
                                        padawan_input_model))
        rings = FakeRingBuilder(self.builder_dir, 'regionone', ['container'],
                                4.0)
        drive_configurations = dummy_osconfig_load(
            padawan_drive_configurations)
        delta = RingDelta()
        generate_delta(input_model, ring_model, rings,
                       drive_configurations, options, delta)
        cmds = rebalance(delta, rings, True)
        # Fake container ring has replica-count of 4.0, check that we
        # change it to match the model (3.0)
        self.assertTrue(verb_ringname_args_in_cmds('set_replicas',
                                                   'container.builder',
                                                   ['3.0'], cmds))
        # Validate we don't attempt to re-create container
        self.assertTrue(not verb_ringname_args_in_cmds('create',
                                                       'container.builder',
                                                       None, cmds))
        # Validate other rings are created
        self.assertTrue(verb_ringname_args_in_cmds('create',
                                                   'account.builder',
                                                   ['17', '3.0', '24'], cmds))
        self.assertTrue(verb_ringname_args_in_cmds('create',
                                                   'object-0.builder',
                                                   ['17', '3.0', '24'], cmds))

    def test_noop(self):
        options = DummyInputOptions()
        input_model = InputModel(config=safe_load(padawan_input_model),
                                 hosts_fd=padawan_net_hosts,
                                 consumes=padawan_swf_rng_consumes)
        ring_model = RingSpecifications(model=safe_load(
                                        padawan_input_model))
        rings = FakeRingBuilder(self.builder_dir, 'regionone',
                                ['account', 'container', 'object-0',
                                 'object-1'],
                                3.0)
        drive_configurations = dummy_osconfig_load(
            padawan_drive_configurations)
        delta = RingDelta()
        generate_delta(input_model, ring_model, rings,
                       drive_configurations, options, delta)
        # Load the fake builder rings with the delta i.e., make it look as
        # though we had just done a rebalance() using input model
        rings.load_fake_ring_data(delta)

        # make a new delta and rebalance
        delta = RingDelta()
        generate_delta(input_model, ring_model, rings,
                       drive_configurations, options, delta)
        cmds = rebalance(delta, rings, True)
        # account, container, object-0:
        #     3 x rebalance (only) (which is point of this test)
        # object-1 has
        #     1 x set replica count
        #     2 x set weights
        #     1 x rebalance
        # total: 7
        self.assertTrue(len(cmds) == 7)

    def test_set_weight_no_step(self):
        options = DummyInputOptions()
        input_model = InputModel(config=safe_load(padawan_input_model),
                                 hosts_fd=padawan_net_hosts,
                                 consumes=padawan_swf_rng_consumes)
        ring_model = RingSpecifications(model=safe_load(
                                        padawan_input_model))
        rings = FakeRingBuilder(self.builder_dir, 'regionone',
                                ['account', 'container', 'object-0'],
                                3.0)
        drive_configurations = dummy_osconfig_load(
            padawan_drive_configurations)
        delta = RingDelta()
        generate_delta(input_model, ring_model, rings,
                       drive_configurations, options, delta)
        # Load the fake builder rings with the delta i.e., make it look as
        # though we had just done a rebalance() using input model
        rings.load_fake_ring_data(delta)

        # Change the weights to a small value
        rings.fake_set_weights(1.0)

        # make a new delta and rebalance
        delta = RingDelta()
        generate_delta(input_model, ring_model, rings,
                       drive_configurations, options, delta)
        cmds = rebalance(delta, rings, True)
        self.assertTrue('account.builder  set_weight'
                        ' 192.168.245.2/disk0 18.63' in ' '.join(cmds))

    def test_set_weight_with_step(self):
        options = DummyInputOptions()
        input_model = InputModel(config=safe_load(padawan_input_model),
                                 hosts_fd=padawan_net_hosts,
                                 consumes=padawan_swf_rng_consumes)
        ring_model = RingSpecifications(model=safe_load(
                                        padawan_input_model))
        rings = FakeRingBuilder(self.builder_dir, 'regionone',
                                ['account', 'container', 'object-0'],
                                3.0)
        drive_configurations = dummy_osconfig_load(
            padawan_drive_configurations)
        delta = RingDelta()
        generate_delta(input_model, ring_model, rings,
                       drive_configurations, options, delta)
        # Load the fake builder rings with the delta i.e., make it look as
        # though we had just done a rebalance() using input model
        rings.load_fake_ring_data(delta)

        # Change the weights to a small value
        rings.fake_set_weights(1.0)

        # This make delta has a weight_step
        options.weight_step = '10.0'
        delta = RingDelta()
        generate_delta(input_model, ring_model, rings,
                       drive_configurations, options, delta)
        cmds = rebalance(delta, rings, True)
        self.assertTrue('account.builder  set_weight'
                        ' 192.168.245.2/disk0 11.00' in ' '.join(cmds))

        # Go through another cycle -- update as though last step built
        # the rings - use small step
        rings = FakeRingBuilder(self.builder_dir, 'regionone',
                                ['account', 'container', 'object-0'],
                                3.0)
        rings.load_fake_ring_data(delta)
        options.weight_step = '1.0'
        delta = RingDelta()
        generate_delta(input_model, ring_model, rings,
                       drive_configurations, options, delta)
        cmds = rebalance(delta, rings, True)
        self.assertTrue('account.builder  set_weight'
                        ' 192.168.245.2/disk0 12.00' in ' '.join(cmds))

        # Go through another cycle -- the step is large enough that final
        # target weight is reached
        rings = FakeRingBuilder(self.builder_dir, 'regionone',
                                ['account', 'container', 'object-0'],
                                3.0)
        rings.load_fake_ring_data(delta)
        options.weight_step = '10.0'
        delta = RingDelta()
        generate_delta(input_model, ring_model, rings,
                       drive_configurations, options, delta)
        cmds = rebalance(delta, rings, True)
        self.assertTrue('account.builder  set_weight'
                        ' 192.168.245.2/disk0 18.63' in ' '.join(cmds))

    def test_set_weight_down(self):

        options = DummyInputOptions()
        input_model = InputModel(config=safe_load(padawan_input_model),
                                 hosts_fd=padawan_net_hosts,
                                 consumes=padawan_swf_rng_consumes)
        ring_model = RingSpecifications(model=safe_load(
                                        padawan_input_model))
        rings = FakeRingBuilder(self.builder_dir, 'regionone',
                                ['account', 'container', 'object-0'],
                                3.0)
        drive_configurations = dummy_osconfig_load(
            padawan_drive_configurations)
        delta = RingDelta()
        generate_delta(input_model, ring_model, rings,
                       drive_configurations, options, delta)
        # Load the fake builder rings with the delta i.e., make it look as
        # though we had just done a rebalance() using input model
        rings.load_fake_ring_data(delta)

        # Change the weights to a large value
        rings.fake_set_weights(30.0)

        # This make delta has a weight_step
        options.weight_step = '10.0'
        delta = RingDelta()
        generate_delta(input_model, ring_model, rings,
                       drive_configurations, options, delta)
        cmds = rebalance(delta, rings, True)
        self.assertTrue('account.builder  set_weight'
                        ' 192.168.245.2/disk0 20.00' in ' '.join(cmds))

        # Go through another cycle -- update as though last step built
        # the rings - use small step
        rings = FakeRingBuilder(self.builder_dir, 'regionone',
                                ['account', 'container', 'object-0'],
                                3.0)
        rings.load_fake_ring_data(delta)
        options.weight_step = '1.0'
        delta = RingDelta()
        generate_delta(input_model, ring_model, rings,
                       drive_configurations, options, delta)
        cmds = rebalance(delta, rings, True)
        self.assertTrue('account.builder  set_weight'
                        ' 192.168.245.2/disk0 19.00' in ' '.join(cmds))

        # Go through another cycle -- the step is large enough that final
        # target weight is reached
        rings = FakeRingBuilder(self.builder_dir, 'regionone',
                                ['account', 'container', 'object-0'],
                                3.0)
        rings.load_fake_ring_data(delta)
        options.weight_step = '10.0'
        delta = RingDelta()
        generate_delta(input_model, ring_model, rings,
                       drive_configurations, options, delta)
        cmds = rebalance(delta, rings, True)
        self.assertTrue('account.builder  set_weight'
                        ' 192.168.245.2/disk0 18.63' in ' '.join(cmds))

    def test_add_servers(self):
        # This test uses same process as test_build_rings() above -- so it
        # appears as though all servers are being added to an existing
        # system. With --weight-step=10, the resulting weights are limited
        # to 10.0
        options = DummyInputOptions()
        input_model = InputModel(config=safe_load(padawan_input_model),
                                 hosts_fd=padawan_net_hosts,
                                 consumes=padawan_swf_rng_consumes)
        ring_model = RingSpecifications(model=safe_load(
                                        padawan_input_model))
        rings = RingBuilder(self.builder_dir, False)
        drive_configurations = dummy_osconfig_load(
            padawan_drive_configurations)
        # Set limit to weight
        options.weight_step = '10'
        delta = RingDelta()
        generate_delta(input_model, ring_model, rings,
                       drive_configurations, options, delta)
        cmds = rebalance(delta, rings, True)
        self.assertTrue('--device disk0'
                        ' --meta padawan-ccp-c1-m3:disk0:/dev/sdc'
                        ' --weight 10.00' in ' '.join(cmds))
        self.assertTrue('--device lvm0 --meta'
                        ' padawan-ccp-c1-m2:lvm0:/dev/hlm-vg/LV_SWFAC'
                        ' --weight 10.00' in ' '.join(cmds))
