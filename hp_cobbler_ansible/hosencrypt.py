#!/usr/bin/env python
#
# A utility to encrypt passwords for auxiliary HOS systems like IPMI.
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

from subprocess import PIPE, Popen

encryption_env = 'HOS_USER_PASSWORD_ENCRYPT_KEY'

class aes256:
    prefix = '@hos_aes256@'
    def __init__(self, key):
        pass

    def encrypt(self, raw):
        return ""

    def decrypt(self, cooked):
        return ""

class openssl:
    prefix = '@hos@'

    def __init__(self, key=None):
        pass

    def delegate(self, cmd, value):
        # Note that I'm passing the environment variable's name to the subprocess, not its value.
        argv = ('/usr/bin/openssl', 'aes-256-cbc', '-a', cmd, '-pass', 'env:%s' % encryption_env)
        p = Popen(argv, close_fds=True, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        result = p.communicate(input=value)
        if p.returncode != 0:
            errmsg = result[1].strip()
            if errmsg.startswith('bad decrypt'):
                errmsg = 'incorrect encryption key'
            elif errmsg.startswith('error reading input file') or errmsg.startswith('bad magic number'):
                errmsg = 'bad input data'
            raise OSError('openssl: %s' % errmsg)
        return result[0].strip()

    def encrypt(self, raw):
        return self.delegate('-salt', raw)

    def decrypt(self, cooked):
        # openssl expects a newline at the end of the string.
        if cooked[-1] != '\n':
            cooked += '\n'
        return self.delegate('-d', cooked)

def main():
    import getpass
    import sys

    obj = openssl()
    if len(sys.argv) > 1 and sys.argv[1] == '-d':
        value = getpass.getpass('encrypted value? ')
        if value.startswith(obj.prefix):
            value = value[len(obj.prefix):]
        x = obj.decrypt(value)
        print x
    else:
        value = getpass.getpass('unencrypted value? ')
        x = obj.encrypt(value)
        print obj.prefix + x

if __name__ == '__main__':
    main()
