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

import os.path
import imp

path = os.path.dirname(os.path.realpath(__file__))

hosencrypt = imp.load_source('hosencrypt', path + '/../hosencrypt.py')

encryption_class = 'openssl'

hosencrypt_class = getattr(hosencrypt, encryption_class)

def hos_user_password_decrypt(value, *args, **kw):
    if not value.startswith(hosencrypt_class.prefix):
        return value
    obj = hosencrypt_class()
    return obj.decrypt(value[len(obj.prefix):])

class FilterModule(object):
    def filters(self):
        return { 'hos_user_password_decrypt': hos_user_password_decrypt }
