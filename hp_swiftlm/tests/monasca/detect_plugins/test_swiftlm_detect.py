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
import tempfile
import unittest
from shutil import rmtree
from swiftlm.monasca.detect_plugins.swiftlm_detect import SwiftLMDetect


class TestSwiftLMDetect(unittest.TestCase):
    def setUp(self):
        self.testdir = tempfile.mkdtemp()
        self.detect = SwiftLMDetect(self.testdir)

    def tearDown(self):
        rmtree(self.testdir, ignore_errors=True)

    def _test_detect(self, service):
        self.detect.SWIFTLM_DIR = self.testdir
        conf_file = service + '.conf'
        conf_path = os.path.join(self.testdir, conf_file)
        with open(conf_path, 'wb'):
            self.detect._detect()
        self.assertTrue(self.detect.available)

    def test_detect_server(self):
        self._test_detect('swiftlm-scan')

    def test_detect_none(self):
        self.detect.SWIFT_DIR = self.testdir
        self.detect._detect()
        self.assertFalse(self.detect.available)
