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

from sos.plugins import Plugin, DebianPlugin, UbuntuPlugin

class OpenStackIronic(Plugin):
    """Openstack ironic
    """
    plugin_name = "openstack_ironic"
    profiles = ("openstack",)

    option_list = [("log", "gathers openstack nova logs", "slow", True),
                   ("cmds", "gathers openstack nova commands", "slow", False)]

    def setup(self):
        # TODO(kerrin) logs are currently in /var/log/upstart which we collect
        # already. Need to update ironic logging and log /var/log/ironic
        self.add_copy_spec("/etc/ironic")

        if self.get_option("cmds"):
            self.add_cmd_output(
                'bash -c "source /root/stackrc ; ironic node-list"',
                suggest_filename = "ironic_node_list")
            self.add_cmd_output(
                'bash -c "source /root/stackrc ; ironic chassis-list"',
                suggest_filename = "ironic_chassis_list")
            self.add_cmd_output(
                'bash -c "source /root/stackrc ; ironic port-list"',
                suggest_filename = "ironic_port_list")
            self.add_cmd_output(
                'bash -c "source /root/stackrc ; ironic driver-list"',
                suggest_filename = "ironic_driver_list")


class DebianOpenStackIronic(OpenStackIronic, DebianPlugin, UbuntuPlugin):

    files = ["/etc/ironic/ironic.conf"]
