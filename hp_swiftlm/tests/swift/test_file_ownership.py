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
from shutil import rmtree
import tempfile
import mock
import unittest

from swiftlm.swift import file_ownership as FO
from swiftlm.utils.values import ServerType


class TestFileOwnership(unittest.TestCase):

    def test_add_result(self):
        results = set()
        FO.add_result(results, '/test/path', 'missing')

        self.assertEqual(len(results), 1)

        x = next(iter(results))
        self.assertEqual(str(x), 'Path: /test/path is missing')

    @mock.patch('os.stat')
    @mock.patch('pwd.getpwuid')
    def test_is_swift_owned(self, mock_owner, mock_stat):
        mock_owner.return_value = mock.Mock(pw_name='swift')
        self.assertTrue(FO._is_swift_owned(set(), '/test/file/path'))

        mock_owner.return_value = mock.Mock(pw_name='not-swift')
        self.assertFalse(FO._is_swift_owned(set(), '/test/file/path'))

    @mock.patch('os.stat')
    @mock.patch('os.path.isfile')
    def test_is_empty_file(self, mock_isfile, mock_stat):
        mock_isfile.return_value = True

        mock_stat.return_value = mock.Mock(st_size=1024)
        self.assertFalse(FO._is_empty_file(set(), '/test/file/path'))

        mock_stat.return_value = mock.Mock(st_size=0)
        self.assertTrue(FO._is_empty_file(set(), '/test/file/path'))


class TestMain(unittest.TestCase):

    def setUp(self):
        # setup fake directories and patch file_ownership to use them
        self.testdir = tempfile.mkdtemp()
        self.etc_dir = os.path.join(self.testdir, 'etc')
        os.makedirs(self.etc_dir)
        self.srv_dir = os.path.join(self.testdir, 'srv')
        os.makedirs(self.srv_dir)
        self.orig_conf_dir = FO.CONF_DIR
        self.orig_swift_dir = FO.SWIFT_DIR
        self.orig_node_dir = FO.NODE_DIR
        FO.SWIFT_DIR = os.path.join(self.etc_dir, 'swift')
        FO.CONF_DIR = self.etc_dir
        FO.NODE_DIR = os.path.join(self.srv_dir, 'node')

    def tearDown(self):
        FO.SWIFT_DIR = self.orig_swift_dir
        FO.CONF_DIR = self.orig_conf_dir
        FO.NODE_DIR = self.orig_node_dir
        rmtree(self.testdir)

    def _test_missing(self, missing):
        results = FO.main()
        self.assertEqual(len(missing), len(results))
        expected = []
        for name in missing:
            expected.append('Path: %s is missing' % name)
        for result in results:
            self.assertTrue(str(result) in expected,
                            'result %s not in expected %s'
                            % (result, expected))
            expected.remove(str(result))
        self.assertFalse(expected)

    def test_all_missing_not_proxy(self):
        with mock.patch('swiftlm.swift.file_ownership.server_type',
                        lambda x: x != ServerType.proxy):
            self._test_missing((os.path.join(self.etc_dir, 'rsyncd.conf'),
                               os.path.join(self.etc_dir, 'rsyslog.conf'),
                               os.path.join(self.etc_dir, 'swift'),
                               os.path.join(self.etc_dir, 'swift'),
                               os.path.join(self.srv_dir, 'node')))

    def test_all_missing_proxy(self):
        with mock.patch('swiftlm.swift.file_ownership.server_type',
                        lambda x: x == ServerType.proxy):
            self._test_missing((os.path.join(self.etc_dir, 'rsyslog.conf'),
                               os.path.join(self.etc_dir, 'swift'),
                               os.path.join(self.etc_dir, 'swift')))

    def _create_etc_file(self, name, rel_path=None, content=None):
        if rel_path:
            os.makedirs(os.path.join(self.etc_dir, rel_path))
            path = os.path.join(self.etc_dir, rel_path, name)
        else:
            path = os.path.join(self.etc_dir, name)
        with open(path, 'wb') as f:
            if content:
                f.write(content)
        return path

    def _test_empty(self, empty):
        # fake file ownership to be 'swift'
        with mock.patch('pwd.getpwuid') as mock_pwuid:
            mock_pwuid.return_value = mock.Mock(pw_name='swift')
            results = FO.main()
        self.assertEqual(len(empty), len(results), results)
        expected = []
        for path in empty:
            expected.append(
                'Path: %s should not be empty'
                % os.path.join(self.etc_dir, path))
        for result in results:
            self.assertTrue(str(result) in expected,
                            '%s not in %s' % (result, expected))
            expected.remove(str(result))
        self.assertFalse(expected)

    def test_no_empty_files(self):
        os.makedirs(os.path.join(self.srv_dir, 'node'))
        self._create_etc_file('rsyslog.conf', content='blah')
        self._create_etc_file('rsyncd.conf', content='blah')
        self._create_etc_file('swift.conf', rel_path='swift', content='blah')
        with mock.patch('swiftlm.swift.file_ownership.server_type',
                        lambda x: x == ServerType.proxy):
            self._test_empty([])

    def test_empty_rsyncd_file_not_proxy(self):
        os.makedirs(os.path.join(self.srv_dir, 'node'))
        self._create_etc_file('rsyslog.conf', content='blah')
        empty = self._create_etc_file('rsyncd.conf')
        self._create_etc_file('swift.conf', rel_path='swift', content='blah')
        with mock.patch('swiftlm.swift.file_ownership.server_type',
                        lambda x: x != ServerType.proxy):
            self._test_empty([empty])

    def test_empty_rsyncd_file_proxy(self):
        os.makedirs(os.path.join(self.srv_dir, 'node'))
        self._create_etc_file('rsyslog.conf', content='blah')
        empty = self._create_etc_file('rsyncd.conf')
        self._create_etc_file('swift.conf', rel_path='swift', content='blah')
        with mock.patch('swiftlm.swift.file_ownership.server_type',
                        lambda x: x == ServerType.proxy):
            self._test_empty([])

    def test_empty_rsyslog_file_not_proxy(self):
        os.makedirs(os.path.join(self.srv_dir, 'node'))
        empty = self._create_etc_file('rsyslog.conf')
        self._create_etc_file('rsyncd.conf', content='blah')
        self._create_etc_file('swift.conf', rel_path='swift', content='blah')
        with mock.patch('swiftlm.swift.file_ownership.server_type',
                        lambda x: x != ServerType.proxy):
            self._test_empty([empty])

    def test_empty_rsyslog_file_proxy(self):
        os.makedirs(os.path.join(self.srv_dir, 'node'))
        empty = self._create_etc_file('rsyslog.conf')
        self._create_etc_file('rsyncd.conf', content='blah')
        self._create_etc_file('swift.conf', rel_path='swift', content='blah')
        with mock.patch('swiftlm.swift.file_ownership.server_type',
                        lambda x: x == ServerType.proxy):
            self._test_empty([empty])

    def test_empty_swift_files(self):
        os.makedirs(os.path.join(self.srv_dir, 'node'))
        self._create_etc_file('rsyslog.conf', content='blah')
        self._create_etc_file('rsyncd.conf', content='blah')
        empty1 = self._create_etc_file('swift.conf', rel_path='swift')
        empty2 = self._create_etc_file('object-server.conf',
                                       rel_path='swift/object-server')
        with mock.patch('swiftlm.swift.file_ownership.server_type',
                        lambda x: x != ServerType.proxy):
            self._test_empty([empty1, empty2])

    def test_root_dir_does_not_need_to_be_owned(self):
        self._create_etc_file('rsyslog.conf', content='blah')
        self._create_etc_file('rsyncd.conf', content='blah')
        os.makedirs(os.path.join(self.etc_dir, 'swift'))
        os.makedirs(os.path.join(self.srv_dir, 'node'))
        with mock.patch('swiftlm.swift.file_ownership.server_type',
                        lambda x: x != ServerType.object):
            results = FO.main()
        self.assertEqual(0, len(results))

    def test_child_dir_does_need_to_be_owned(self):
        self._create_etc_file('rsyslog.conf', content='blah')
        self._create_etc_file('rsyncd.conf', content='blah')
        bad_path1 = os.path.join(self.etc_dir, 'swift', 'object-server')
        bad_path2 = os.path.join(self.srv_dir, 'node', '1')
        bad_path3 = os.path.join(self.srv_dir, 'node', '2')
        os.makedirs(bad_path1)
        os.makedirs(bad_path2)
        os.makedirs(bad_path3)
        with mock.patch('swiftlm.swift.file_ownership.server_type',
                        lambda x: x != ServerType.object):
            with mock.patch('pwd.getpwuid') as mock_pwuid:
                mock_pwuid.return_value = mock.Mock(pw_name='not-swift')
                results = FO.main()
                self.assertEqual(3, len(results))
                expected = ['Path: %s is not owned by swift' % bad_path1,
                            'Path: %s is not owned by swift' % bad_path2,
                            'Path: %s is not owned by swift' % bad_path3]
                for result in results:
                    self.assertTrue(str(result) in expected)
                    expected.remove(str(result))
                self.assertFalse(expected)

    def test_grandchild_swift_dir_does_need_to_be_owned(self):
        self._create_etc_file('rsyslog.conf', content='blah')
        self._create_etc_file('rsyncd.conf', content='blah')
        bad_path1 = os.path.join(self.etc_dir, 'swift', 'object-server')
        bad_path2 = os.path.join(self.etc_dir, 'swift', 'object-server', '1')
        os.makedirs(bad_path2)
        with mock.patch('swiftlm.swift.file_ownership.server_type',
                        lambda x: x != ServerType.object):
            with mock.patch('pwd.getpwuid') as mock_pwuid:
                mock_pwuid.return_value = mock.Mock(pw_name='not-swift')
                results = FO.main()
                self.assertEqual(2, len(results))
                expected = ['Path: %s is not owned by swift' % bad_path1,
                            'Path: %s is not owned by swift' % bad_path2]
                for result in results:
                    self.assertTrue(str(result) in expected)
                    expected.remove(str(result))
                self.assertFalse(expected)

    def test_grandchild_node_dir_does_not_need_to_be_owned(self):
        # check in /srv/node only reports one level down
        os.makedirs(os.path.join(self.etc_dir, 'swift'))
        self._create_etc_file('rsyslog.conf', content='blah')
        self._create_etc_file('rsyncd.conf', content='blah')
        bad_path1 = os.path.join(self.srv_dir, 'node', '1')
        bad_path2 = os.path.join(self.srv_dir, 'node', '1', 'sdb1')
        bad_path3 = os.path.join(self.srv_dir, 'node', '2')
        bad_path4 = os.path.join(self.srv_dir, 'node', '2', 'sda1')
        os.makedirs(bad_path2)
        os.makedirs(bad_path4)
        with mock.patch('swiftlm.swift.file_ownership.server_type',
                        lambda x: x == ServerType.object):
            with mock.patch('pwd.getpwuid') as mock_pwuid:
                mock_pwuid.return_value = mock.Mock(pw_name='not-swift')
                results = FO.main()
                self.assertEqual(2, len(results), results)
                expected = ['Path: %s is not owned by swift' % bad_path1,
                            'Path: %s is not owned by swift' % bad_path3]
                for result in results:
                    self.assertTrue(str(result) in expected)
                    expected.remove(str(result))
                self.assertFalse(expected)

    def test_dirs_are_owned(self):
        self._create_etc_file('rsyslog.conf', content='blah')
        self._create_etc_file('rsyncd.conf', content='blah')
        path1 = os.path.join(self.etc_dir, 'swift', 'object-server', '1')
        path2 = os.path.join(self.srv_dir, 'node', '1')
        os.makedirs(path1)
        os.makedirs(path2)
        with mock.patch('swiftlm.swift.file_ownership.server_type',
                        lambda x: x == ServerType.object):
            with mock.patch('pwd.getpwuid') as mock_pwuid:
                mock_pwuid.return_value = mock.Mock(pw_name='swift')
                results = FO.main()
                self.assertEqual(0, len(results))
