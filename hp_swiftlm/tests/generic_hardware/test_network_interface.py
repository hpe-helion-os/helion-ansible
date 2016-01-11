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


import mock
import unittest

import six

from swiftlm.generic_hardware import network_interface


if six.PY2:
    BUILTIN_OPEN = '__builtin__.open'
    COMMANDS_MODULE = 'commands'
else:
    BUILTIN_OPEN = 'builtins.open'
    COMMANDS_MODULE = 'subprocess'


class TestNetworkInterface(unittest.TestCase):

    @mock.patch(COMMANDS_MODULE + '.getoutput')
    def test_get_interface_data(self, mock_command):
        mock_data = ['0'] * 17
        mock_data[4] = '123'
        # float value doesn't make sense in real world but useful
        # to test that a float value would be tolerated if it occurred in
        # any of the output fields
        mock_data[9] = '1.23'
        mock_data[15] = '321'
        mock_command.return_value = ' '.join(mock_data)

        d = network_interface.get_interface_data('interface_name')

        self.assertEqual(d['interface'], 'interface_name')
        self.assertEqual(d['rx']['bytes'], 0)
        self.assertEqual(d['rx']['drop'], 123)
        self.assertEqual(d['tx']['bytes'], 1.23)
        self.assertEqual(d['tx']['carrier'], 321)
