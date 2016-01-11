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

def hos_user_password_encrypt(value, key=None, *args, **kw):
    # If a key is supplied to the filter, use it. Make sure
    # we stash any existing key value in the envirionment,
    # as os.environ() changes will persist.
    key_stash = None

    def _backup_env_key():
        if 'HOS_USER_PASSWORD_ENCRYPT_KEY' in os.environ:
            key_stash = os.environ['HOS_USER_PASSWORD_ENCRYPT_KEY']
        os.environ['HOS_USER_PASSWORD_ENCRYPT_KEY'] = key

    def _restore_env_key():
        # Restore the stashed key
        if key_stash is None:
            del os.environ['HOS_USER_PASSWORD_ENCRYPT_KEY']
        else:
            os.environ['HOS_USER_PASSWORD_ENCRYPT_KEY'] = key_stash

    if key is not None:
        _backup_env_key()

    if 'HOS_USER_PASSWORD_ENCRYPT_KEY' not in os.environ:
        return value

    if (os.environ['HOS_USER_PASSWORD_ENCRYPT_KEY'] is None
            or os.environ['HOS_USER_PASSWORD_ENCRYPT_KEY'] == ""):
        _restore_env_key()
        return value

    obj = hosencrypt_class()
    result = obj.prefix + obj.encrypt(value)

    _restore_env_key()

    return result

class FilterModule(object):
    def filters(self):
        return { 'hos_user_password_encrypt': hos_user_password_encrypt }
