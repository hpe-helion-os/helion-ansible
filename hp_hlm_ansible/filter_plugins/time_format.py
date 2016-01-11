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

import time


# J2 expressions are repeatedly re-evaluated.
# Often, we want a single timestamp. So, we have a single
# default which is the time this filter gets initialised -
# that'll be fixed close to the time that ansible kicks off.
_time = time.gmtime()


def time_format(format, now=False):
    if now:
        return time.strftime(format, time.gmtime())

    return time.strftime(format, _time)


class FilterModule(object):

    def filters(self):
        return {'time_format': time_format}
