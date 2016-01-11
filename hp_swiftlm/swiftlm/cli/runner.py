#!/usr/bin/env python
# encoding: utf-8

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

from __future__ import print_function

import argparse
import pkg_resources
import json
import sys
import traceback
import yaml

from swiftlm.utils.metricdata import MetricData
from swiftlm.utils.values import Severity


def display_json(metrics, pretty):
    kwargs = {}
    if pretty:
        kwargs = {
            'sort_keys': True,
            'indent': 2,
        }

    print(json.dumps(metrics, **kwargs))


def display_yaml(metrics, pretty):
    yaml.add_representer(Severity, Severity.yaml_repr, yaml.SafeDumper)
    kwargs = {}
    if pretty:
        kwargs = {'default_flow_style': False}

    print(yaml.safe_dump(metrics, **kwargs))


FORMATS = {
    'json': display_json,
    'yaml': display_yaml,
}


def construct_parser(plugins):
    parser = argparse.ArgumentParser(description='XXX')

    # Create a flag for each plugin that adds the matching function to the
    # selected list if it appears on the command line.
    selection_group = parser.add_argument_group(
        'Available Checks',
        'Select one or more of the available checks to run as a subset.'
    )
    for name, unloaded_func in plugins.items():
        func = unloaded_func.load()
        help_string = func.__doc__ or 'Reserved for future use.'

        selection_group.add_argument(
            '--' + name,
            dest='selected',
            action='append_const',
            const=func,
            help=help_string
        )

    parser.add_argument(
        '--format',
        choices=FORMATS.keys(),
        default='json',
        help='Format output (default: %(default)s).'
    )
    parser.add_argument(
        '-p', '--pretty',
        action='store_true',
        help='Format output in a more easy to read way.'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='count'
    )

    return parser


def parse_args():
    ps = pkg_resources.get_entry_map('swiftlm', 'swiftlm.plugins')
    p = construct_parser(ps)
    args = p.parse_args()

    # we make the common case easy, No selected flags indicate that we should
    # run all diagnostics.
    if args.selected is None:
        args.selected = [f.load() for f in ps.values()]

    return args


def main():
    args = parse_args()
    metrics = []

    for func in args.selected:
        try:
            r = func()
            if isinstance(r, list) and r and isinstance(r[0], MetricData):
                metrics.extend([result.metric() for result in r])
            elif isinstance(r, MetricData):
                metrics.append(r.metric())
        except:   # noqa
            t, v, tb = sys.exc_info()
            backtrace = ' '.join(traceback.format_exception(t, v, tb))
            r = MetricData.single('check.failure',
                                  Severity.fail,
                                  '{check} failed with: {error}',
                                  {'check': str(func),
                                   'error': backtrace.replace('\n', ' '),
                                   'component': 'swiftlm-scan',
                                   'service': 'object-storage'})
            metrics.append(r.metric())
            pass

    FORMATS[args.format](metrics, args.pretty)


if __name__ == '__main__':
    main()
