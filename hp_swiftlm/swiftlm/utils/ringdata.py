"""
Copyright (c) 2010-2015 OpenStack Foundation

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

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


import array
import json
import struct
from gzip import GzipFile
from io import BufferedReader

try:
    import cPickle as pickle
except ImportError:
    import pickle


class RingData(object):
    """Partitioned consistent hashing ring data (used for serialization)."""

    def __init__(self, replica2part2dev_id, devs, part_shift):
        self.devs = devs
        self._replica2part2dev_id = replica2part2dev_id
        self._part_shift = part_shift

    @classmethod
    def deserialize_v1(cls, gz_file):
        json_len, = struct.unpack('!I', gz_file.read(4))
        ring_dict = json.loads(gz_file.read(json_len))
        ring_dict['replica2part2dev_id'] = []
        partition_count = 1 << (32 - ring_dict['part_shift'])
        for _ in range(ring_dict['replica_count']):
            x = array.array('H', gz_file.read(2 * partition_count))
            ring_dict['replica2part2dev_id'].append(x)

        return ring_dict

    @classmethod
    def load(cls, filename):
        """
        Load ring data from a file.

        :param filename: Path to a file serialized by the save() method.
        :returns: A RingData instance containing the loaded data.
        """
        gz_file = GzipFile(filename, 'rb')
        # Python 2.6 GzipFile doesn't support BufferedIO
        if hasattr(gz_file, '_checkReadable'):
            gz_file = BufferedReader(gz_file)

        # See if the file is in the new format
        magic = gz_file.read(4)
        if magic == 'R1NG':
            # Not sure if this is intended to be unpacked into a tuple
            # Leave the comma unless it has been proven not to be needed
            version, = struct.unpack('!H', gz_file.read(2))
            if version == 1:
                ring_data = cls.deserialize_v1(gz_file)
            else:
                raise Exception('Unknown ring format version %d' % version)
        else:
            # Assume old-style pickled ring
            gz_file.seek(0)
            ring_data = pickle.load(gz_file)

        if not hasattr(ring_data, 'devs'):
            ring_data = RingData(
                ring_data['replica2part2dev_id'],
                ring_data['devs'],
                ring_data['part_shift']
            )
        return ring_data
