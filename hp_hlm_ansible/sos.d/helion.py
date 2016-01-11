# Copyright (C) 2014 Hewlett-Packard Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import os
import os.path
from sos.plugins import Plugin, DebianPlugin


class Helion(Plugin):
    """Helion related information
    """
    plugin_name = "helion"

    option_list = [("log", "gathers all helion logs", "slow", False)]


class DebianHelion(Helion, DebianPlugin):
    """Helion related information for Debian distributions
    """

    def setup(self):
        super(DebianHelion, self).setup()

        sudo_user = os.getenv("SUDO_USER", "")
        user_home_path = os.path.expanduser("~" + sudo_user)

        self.add_copy_spec([
            os.path.join(user_home_path, ".ansible.cfg"),
            os.path.join(user_home_path, ".ansible", "ansible.log"),
            "/etc/",
            "/mnt/state/etc/",
            "/opt/stack/service/*/etc/",
            "/opt/stack/venv/etc/",
            "/opt/stack/venv/*/META-INF/",
            "/var/log/mysql/",
            "/var/lib/mysql/*.log",
            "/var/log/stunnel4/",
            "/var/log/haproxy*",
            "/var/log/keepalived*",
        ])
