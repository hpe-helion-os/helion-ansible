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
# In case you are tempted to import from non-built-in libraries, think twice:
# this module will be imported by monasca-agent which must therefore be able
# to import any dependent modules.

import logging
from monasca_setup import agent_config
import monasca_setup.detection
from monasca_setup.detection.utils import _get_dimensions
log = logging.getLogger(__name__)


class CinderLMDetect(monasca_setup.detection.ArgsPlugin):
    """Detect if we will be monitoring Cinder."""
    CHECK_NAME = 'cinderlm_check'

    def __init__(self, template_dir, overwrite=True, args=None):
        super(CinderLMDetect, self).__init__(
            template_dir, overwrite, args)

    def _detect(self):
        """Run detection, set self.available True if config is detected."""
        # (Called during superclass __init__).
        self.available = True

    def build_config(self):
        """Build the config as a Plugins object and return."""
        config = agent_config.Plugins()
        parameters = {'name': self.CHECK_NAME}

        # set service and component
        dimensions = _get_dimensions('block-storage', None)
        if len(dimensions) > 0:
            parameters['dimensions'] = dimensions

        config[self.CHECK_NAME] = {'init_config': None,
                                   'instances': [parameters]}
        log.info("\tEnabling the CinderLMDetect plugin %s" % config)
        return config

    def dependencies_installed(self):
        """Return True if dependencies are installed."""
        return True
