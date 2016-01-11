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

from collections import defaultdict
import json
from monasca_agent.collector import checks
import socket
import subprocess
import threading

OK = 0
WARN = 1
FAIL = 2
UNKNOWN = 3

# name used for metrics reported directly by this module e.g. when a task
# fails or times out. (we need to hard code this name rather than use the
# module name because the module name reported by __name__ is dependant on how
# monasca-agent imports the module)
MODULE_METRIC_NAME = 'cinderlm.cinderlm_check'

SERVICE_NAME = 'block-storage'


def create_task_failed_metric(task_type, task_name):
    """Generate metric to report that a task has raised an exception."""
    return dict(
        metric=MODULE_METRIC_NAME,
        dimensions={'type': task_type,
                    'task': task_name,
                    'service': SERVICE_NAME,
                    'hostname': socket.gethostname()},
        value_meta=dict(
            msg='%s task execution failed: "%s"'
                % (task_type.title(), task_name)),
        value=FAIL)


def create_timed_out_metric(task_type, task_name):
    """Generate metric to report that a task has timed out."""
    return dict(
        metric=MODULE_METRIC_NAME,
        dimensions={'type': task_type,
                    'task': task_name,
                    'service': SERVICE_NAME,
                    'hostname': socket.gethostname()},
        value_meta=dict(
            msg='%s task execution timed out: "%s"'
                % (task_type.title(), task_name)),
        value=FAIL)


def create_success_metric(task_type, task_name):
    """Generate metric to report that a task successful."""
    return dict(
        metric=MODULE_METRIC_NAME,
        dimensions={'type': task_type,
                    'task': task_name,
                    'service': SERVICE_NAME,
                    'hostname': socket.gethostname()},
        value_meta=dict(
            msg='%s task execution succeeded: "%s"'
                % (task_type.title(), task_name)),
        value=OK)


class CommandRunner(object):
    def __init__(self, command):
        self.command = command
        self.stderr = self.stdout = self.returncode = self.exception = None
        self.timed_out = False
        self.process = None

    def run_with_timeout(self, timeout):
        thread = threading.Thread(target=self.run_subprocess)
        thread.start()
        thread.join(timeout)
        if thread.is_alive():
            self.timed_out = True
            if self.process:
                self.process.terminate()

    def run_subprocess(self):
        try:
            self.process = subprocess.Popen(
                self.command, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
            self.stdout, self.stderr = self.process.communicate()
            self.returncode = self.process.returncode
        except Exception as e:  # noqa
            self.exception = e


class CinderLMScan(checks.AgentCheck):
    # set of check tasks implemented
    TASKS = (
        'cinder-services',
    )

    # command args to be used for all calls to shell commands
    COMMAND_ARGS = ['/usr/local/bin/cinder_diag', '--json']
    COMMAND_TIMEOUT = 15.0
    SUBCOMMAND_PREFIX = '--'

    # list of sub-comands each of which is appended to a shell command
    # with the prefix added
    DEFAULT_SUBCOMMANDS = TASKS

    def __init__(self, name, init_config, agent_config, instances=None,
                 logger=None):
        super(CinderLMScan, self).__init__(
            name, init_config, agent_config, instances)
        self.log = logger or self.log

    def log_summary(self, task_type, summary):
        task_count = len(summary.get('tasks', []))
        if task_count == 1:
            msg = 'Ran 1 %s task.' % task_type
        else:
            msg = 'Ran %d %s tasks.' % (task_count, task_type)
        # suppress log noise if no tasks were configured
        logger = self.log.info if task_count else self.log.debug
        logger(msg)

    def _run_command_line_task(self, task_name):
        # we have to call out to a command line
        command = list(self.COMMAND_ARGS)
        command.append(self.SUBCOMMAND_PREFIX + task_name)
        cmd_str = ' '.join(command)
        runner = CommandRunner(command)
        try:
            runner.run_with_timeout(self.COMMAND_TIMEOUT)
        except Exception as e:  # noqa
            self.log.warn('Command "%s" failed with "%s"'
                          % (cmd_str, e))
            metrics = create_task_failed_metric('command', task_name)
        else:
            if runner.exception:
                self.log.warn('Command "%s" failed with "%s"'
                              % (cmd_str, runner.exception))
                metrics = create_task_failed_metric('command', task_name)
            elif runner.timed_out:
                self.log.warn('Command "%s" timed out after %ss'
                              % (cmd_str, self.COMMAND_TIMEOUT))
                metrics = create_timed_out_metric('command', cmd_str)
            elif runner.returncode:
                self.log.warn('Command "%s" failed with status %s'
                              % (cmd_str, runner.returncode))
                metrics = create_task_failed_metric('command', task_name)
            else:
                try:
                    metrics = json.loads(runner.stdout)
                    metrics.append(create_success_metric('command', task_name))
                except (ValueError, TypeError) as e:
                    self.log.warn('Failed to parse json: %s' % e)
                    metrics = create_task_failed_metric('command', task_name)
        return metrics

    def _get_metrics(self, task_names, task_runner):
        reported = []
        summary = defaultdict(list)
        for task_name in task_names:
            summary['tasks'].append(task_name)
            metrics = task_runner(task_name)
            if not isinstance(metrics, list):
                metrics = [metrics]
            for metric in metrics:
                reported.append(metric)
        return reported, summary

    def _csv_to_list(self, csv):
        return [f.strip() for f in csv.split(',') if f]

    def _load_instance_config(self, instance):
        self.log.debug('instance config %s' % str(instance))

        if instance.get('subcommands') is None:
            self.subcommands = self.DEFAULT_SUBCOMMANDS
        else:
            self.subcommands = self._csv_to_list(instance.get('subcommands'))
        self.log.debug('Using subcommands %s' % str(self.subcommands))

    def check(self, instance):
        self._load_instance_config(instance)

        # run command line tasks
        all_metrics, summary = self._get_metrics(
            self.subcommands, self._run_command_line_task)
        self.log_summary('command', summary)

        for metric in all_metrics:
            # apply any instance dimensions that may be configured,
            # overriding any dimension with same key that check has set.
            metric['dimensions'] = self._set_dimensions(metric['dimensions'],
                                                        instance)
            self.log.debug(
                'metric %s %s %s %s'
                % (metric.get('metric'), metric.get('value'),
                   metric.get('value_meta'), metric.get('dimensions')))
            try:
                self.gauge(**metric)
            except Exception as e:  # noqa
                self.log.exception('Exception while reporting metric: %s' % e)
