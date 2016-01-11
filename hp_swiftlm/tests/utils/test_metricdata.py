#!/usr/bin/python

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


import unittest
import mock

from swiftlm.utils.metricdata import MetricData
from swiftlm.utils.values import Severity


class TestMetricData(unittest.TestCase):
    dimensions = {'dimen1': 1, 'dimen2': 2}
    messages = {'ok': 'ok', 'fail': 'fail'}

    def test_create_metricdata(self):
        r = MetricData(name='name', messages={})

        self.assertEqual('swiftlm.name', r.name)
        self.assertEqual('', r.message)
        self.assertEqual(None, r.value)
        self.assertIn('hostname', r.dimensions)

    def test_equality_behaviour(self):
        m_a = MetricData('name', self.messages, self.dimensions)
        m_b = MetricData('name', self.messages, self.dimensions)
        self.assertEqual(m_a, m_b)

        m_a = MetricData('name', self.messages, self.dimensions)
        m_b = MetricData('not-name', self.messages, self.dimensions)
        self.assertNotEqual(m_a, m_b)

        m_a = MetricData('name', {'a': 1}, self.dimensions)
        m_b = MetricData('name', {'b': 2}, self.dimensions)
        self.assertEqual(m_a, m_b,
                         'Message dictionaries should not '
                         'affect equality of MetricData instances')

        m_a = MetricData('name', self.messages, self.dimensions)
        m_b = MetricData('name', self.messages, {})
        self.assertNotEqual(m_a, m_b)

        m_a = MetricData('name', self.messages, self.dimensions)
        m_b = MetricData('name', self.messages, self.dimensions)
        m_a.message = 'ok'
        m_b.message = 'fail'
        self.assertNotEqual(m_a, m_b)

        m_a = MetricData('name', self.messages, self.dimensions)
        m_b = MetricData('name', self.messages, self.dimensions)
        m_a.value = 1
        m_b.value = 2
        self.assertNotEqual(m_a, m_b)

    def test_dict_behaviour(self):
        r = MetricData(name='name', messages={})

        r['test'] = 1000
        # dimension values must be strings so we check they are converted
        # properly
        self.assertEqual('1000', r['test'])
        del r['test']

        self.assertNotIn('test', r)

    def test_response_child(self):
        r = MetricData(name='name', messages={'a': 'b'})
        r['test'] = 'test'

        c = r.child(dimensions={'test2': 'test2'})
        self.assertIn('test', c)
        self.assertIn('test2', c)
        self.assertDictEqual({'a': 'b'}, c.messages)
        self.assertEqual('swiftlm.name', c.name)

        c = r.child()
        self.assertIn('test', c)
        self.assertNotIn('test2', c)

    def test_message(self):
        r = MetricData(
            name='name',
            messages={
                'ok': 'test message',
                'test': 'test with meta {test_value}',
            }
        )

        # Test automatic message assignment when a the Status Enum is used
        # as the value
        self.assertEqual('', r.message)
        r.value = Severity.ok
        self.assertEqual('test message', r.message)

        # Test that an error is raised when trying to use a message without
        # providing all of the dimension values first.
        with self.assertRaisesRegexp(ValueError, 'requires a dimension value'):
            r.message = 'test'

        r['test_value'] = '123'
        r.message = 'test'

        self.assertEqual('test with meta 123', str(r))
