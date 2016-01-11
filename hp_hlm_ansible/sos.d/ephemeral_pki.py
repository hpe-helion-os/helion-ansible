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

from sos.plugins import Plugin, DebianPlugin


class EphmeralPki(Plugin, DebianPlugin):
    """Ephemeral CA, certmonger and certificates
    """

    plugin_name = "ephemeral_pki"

    def setup(self):
        self.add_copy_spec([
            "/etc/ssl/certs/ca-certificates.crt",
            "/etc/ssl/from-heat.crt",
            "/etc/ssl/from-heat.key",
            "/etc/ephemeral-ca/",
            "/home/ephemeral-ca/",
            ])
        self.add_cmd_output("getcert list", suggest_filename="getcert_list")
