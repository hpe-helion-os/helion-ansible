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


from collections import defaultdict
import os


class FakeLogger(object):
    def __init__(self):
        self._lines = defaultdict(list)
        self._all_lines = []
        self.errors_logged = 0

    def dump(self):
        result = ''
        for line in self._all_lines:
            result += line + '\n'
        return result

    def _stash(self, level, msg):
        self._lines[level].append(msg)
        msg = level.upper() + ': ' + msg
        self._all_lines.append(msg)
        print 'FakeLogger: %s' % msg

    def debug(self, msg):
        self._stash('debug', msg)

    def info(self, msg):
        self._stash('info', msg)

    def warn(self, msg):
        self._stash('warn', msg)

    def error(self, msg):
        self.errors_logged += 1
        self._stash('error', msg)

    def exception(self, msg):
        self.errors_logged += 1
        self._stash('exception', str(msg))

    def get_lines_for_level(self, level):
        return self._lines.get(level) or []

    def get_lines_for_all_levels(self):
        result = []
        for key in self._lines.keys():
            result.extend(self._lines[key])
        return result


def create_fake_process_entry(proc_dir, proc_num, proc_name):
    """
    Create files in process directory that are tested by swift_services.
    :param proc_dir: name of to level process dir
    :param proc_num: a process number
    :param proc_name: the process name
    :return: None
    """
    proc_num_dir = os.path.join(proc_dir, str(proc_num))
    if not os.path.exists(proc_num_dir):
        os.makedirs(proc_num_dir)
    for filename in ('comm', 'cmdline'):
        with open(os.path.join(proc_num_dir, filename), 'wb') as f:
            s = 'swift-' + proc_name
            f.write(s.encode('UTF-8'))


def create_fake_process_entries(proc_dir, proc_list):
    """
    Create fake process files for all processes in proc_list
    :param proc_dir: name of to level process dir
    :param proc_list: list iof process names
    :return: None
    """
    for num, service in enumerate(proc_list):
        create_fake_process_entry(proc_dir, num, service)


def create_etc_file(dir_, name, rel_path=None, content=None):
    if rel_path:
        os.makedirs(os.path.join(dir_, rel_path))
        path = os.path.join(dir_, rel_path, name)
    else:
        path = os.path.join(dir_, name)
    with open(path, 'wb') as f:
        if content:
            f.write(content)
    return path


def create_valid_non_proxy_fileset(etc_dir, srv_dir):
    create_etc_file(etc_dir, 'rsyslog.conf', content='blah')
    create_etc_file(etc_dir, 'rsyncd.conf', content='blah')
    create_etc_file(etc_dir, 'swift.conf', rel_path='swift', content='blah')
    for dir_ in (os.path.join(etc_dir, 'swift', 'object-server', '1'),
                 os.path.join(srv_dir, 'node', '1')):
        if not os.path.exists(dir_):
            os.makedirs(dir_)


def create_valid_proxy_fileset(etc_dir):
    create_etc_file(etc_dir, 'rsyslog.conf', content='blah')
    create_etc_file(etc_dir, 'swift.conf', rel_path='etc', content='blah')
    os.makedirs(os.path.join(etc_dir, 'swift', 'object-server', '1'))
