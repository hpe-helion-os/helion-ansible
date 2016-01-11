#!/usr/bin/python

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

import json
import shlex
import sys
from urlparse import urlparse


def main():
    url = ''
    factname ='urlparse_result'
    try:
        args_file = sys.argv[1]
        args_data = file(args_file).read()
        arguments = shlex.split(args_data)
    except (IndexError, IOError):
        arguments = sys.argv  # Running interactively
    for arg in arguments:
        if "=" in arg:
            (key, value) = arg.split('=')
            if key == 'url':
                url = value
            elif key == 'factname':
                factname = value

    result = urlparse(url)
    ret = {}
    ret['failed'] = False
    ret['rc'] = 0
    ret['ansible_facts'] = {factname: {'scheme': result.scheme,
                                       'hostname': result.hostname,
                                       'port': result.port}}
    print(json.dumps(ret))


if __name__ == '__main__':
    main()


