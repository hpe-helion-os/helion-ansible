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


# Python library for running hpssacli commnads

import re
try:
    import configparser
except ImportError:
    import ConfigParser as configparser

from swiftlm.utils.metricdata import MetricData
from swiftlm.utils.values import Severity
from swiftlm.utils.utility import run_cmd
from swiftlm import CONFIG_FILE


LOCK_FILE_COMMAND = '/usr/bin/flock -w 10 /var/lock/hpssacli-swiftlm.lock '
BASE_RESULT = MetricData(
    name=__name__,
    messages={
        'no_battery': 'No cache battery',
        'unknown': 'hpssacli command failed: {error}',
        'controller_status': '{sub_component} status is {status}',
        'physical_drive': 'Drive {serial}: {box}:{bay} has status: {status}',
        'l_drive': 'Logical Drive {logical_drive} has status: {status}',
        'l_cache': 'Logical Drive {logical_drive} has cache status: {caching}',
        'ok': 'OK',
        'fail': 'FAIL',
    }
)


def is_cont_heading(line):
    """
    Returns "True" if the line is the controller heading
    example: Smart Array P410 in Slot 1
    """
    if ("Slot" in line) and (not line[0].isspace()):
        return True
    else:
        return False


def get_smart_array_info():
    """
    parses controller data from hpssacli in the form.
    returns a dict.
    key's are lowercased versions of the key name on each line,
    including special characters.
    Values are not changed.

    keys 'model' and 'slot' are parsed from the first line

    Smart Array P410 in Slot 1
       Bus Interface: PCI
       Slot: 1
       Serial Number: PACCR0M9VZ41S4Q
       Cache Serial Number: PACCQID12061TTQ
       RAID 6 (ADG) Status: Disabled
       Controller Status: OK
       Hardware Revision: C
       Firmware Version: 6.60
       Rebuild Priority: Medium
       Expand Priority: Medium
       Surface Scan Delay: 15 secs
       Surface Scan Mode: Idle
       Queue Depth: Automatic
       Monitor and Performance Delay: 60  min
       Elevator Sort: Enabled
       Degraded Performance Optimization: Disabled
       Inconsistency Repair Policy: Disabled
       Wait for Cache Room: Disabled
       Surface Analysis Inconsistency Notification: Disabled
       Post Prompt Timeout: 15 secs
       Cache Board Present: True
       Cache Status: OK
       Cache Ratio: 25% Read / 75% Write
       Drive Write Cache: Disabled
       Total Cache Size: 256 MB
       Total Cache Memory Available: 144 MB
       No-Battery Write Cache: Disabled
       Cache Backup Power Source: Batteries
       Battery/Capacitor Count: 1
       Battery/Capacitor Status: OK
       SATA NCQ Supported: True
       Number of Ports: 2 Internal only
       Encryption Supported: False
       Driver Name: hpsa
       Driver Version: 3.4.0
       Driver Supports HP SSD Smart Path: False

    Smart Array P440ar in Slot 0 (Embedded) (HBA Mode)
       Bus Interface: PCI
       Slot: 0
       Serial Number: PDNLH0BRH7V7GC
       Cache Serial Number: PDNLH0BRH7V7GC
       Controller Status: OK
       Hardware Revision: B
       Firmware Version: 2.14
       Controller Temperature (C): 50
       Number of Ports: 2 Internal only
       Driver Name: hpsa
       Driver Version: 3.4.4
       HBA Mode Enabled: True
       PCI Address (Domain:Bus:Device.Function): 0000:03:00.0
       Negotiated PCIe Data Rate: PCIe 3.0 x8 (7880 MB/s)
       Controller Mode: HBA
       Controller Mode Reboot: Not Required
       Current Power Mode: MaxPerformance
       Host Serial Number: MXQ51906YF
    """
    results = []
    controller_result = BASE_RESULT.child()
    controller_result.name += '.' + 'smart_array'

    rc = run_cmd(LOCK_FILE_COMMAND + 'hpssacli ctrl all show detail')

    if rc.exitcode != 0:
        if 'Error: No controllers detected.' in str(rc.output):
            return []
        r = MetricData.single('check.failure',
                              Severity.fail,
                              '{check} failed with: {error}',
                              {'check': controller_result.name,
                               'error': str(rc.output),
                               'component': 'swiftlm-scan'})
        return [r]

    if rc.output:
        lines = rc.output.split('\n')
    else:
        r = MetricData.single('check.failure',
                              Severity.fail,
                              '{check} failed with: {error}',
                              {'check': controller_result.name,
                               'error': 'No usable output from hpssacli',
                               'component': 'swiftlm-scan'})
        return [r]

    controllers = []
    info = {}
    for line in lines:

        # Ignore blank lines
        if (not line) or (line.isspace()) or (line == "\n"):
            continue

        if is_cont_heading(line):

            if info:
                controllers.append(info)

            # To get controller model, assume that the line is in the form:
            # <model> in Slot <slot>
            model = line.strip().split("in Slot")[0].strip()
            info = {'model': model}
            continue

        k, v = line.split(':', 1)
        k = k.strip().lower()
        v = v.strip()
        info[k] = v

    if info:
        controllers.append(info)

    controller_slots = []

    for c in controllers:
        results.extend(check_controller(c, controller_result))
        if c.get('slot'):
            controller_slots.append(c.get('slot'))

    return results, controller_slots


def check_controller(c, base):
    results = []
    base = base.child(dimensions={
        'serial': c.get('serial number', 'NA'),
        'model': c.get('model', 'NA'),
        'slot': c.get('slot', 'NA'),
        'component': 'controller',
    })

    # Firmware version
    try:
        f = c.get('firmware version', '0')
        f = float(f)
    except ValueError:
        f = 0
    r = base.child()
    r.name += '.' + 'firmware'
    r.value = f
    results.append(r)

    # Battery count
    try:
        bc = c.get('battery/capacitor count', '0')
        bc = int(bc)
    except ValueError:
        bc = 0
    r = base.child()
    r['sub_component'] = 'battery/capacitor count'
    r['count'] = bc
    if bc < 1:
        r.value = Severity.fail
        r.message = 'no_battery'
    else:
        r.value = Severity.ok
    results.append(r)

    # Statuses
    for i in ('controller', 'cache', 'battery/capacitor'):
        s = c.get(i + ' status', 'NA')
        r = base.child()
        r['sub_component'] = i
        r['status'] = s
        if s != 'OK':
            r.value = Severity.fail
            r.message = 'controller_status'
        else:
            r.value = Severity.ok
        results.append(r)

    return results


def get_physical_drive_info(slot):
    """
    Parses drive data from hpssacli in the form.
    There are multiple drives in the output.

    array A
      physicaldrive 2C:1:1
         Port: 2C
         Box: 1
         Bay: 1
         Status: OK
         Drive Type: Data Drive
         Interface Type: SAS
         Size: 2 TB
         Native Block Size: 512
         Rotational Speed: 7200
         Firmware Revision: HPD3
         Serial Number:         YFJMHTZD
         Model: HP      MB2000FBUCL
         Current Temperature (C): 27
         Maximum Temperature (C): 38
         PHY Count: 2
         PHY Transfer Rate: 6.0Gbps, Unknown
    """
    results = []
    drive_result = BASE_RESULT.child(dimensions={
        'controller_slot': str(slot),
    })
    drive_result.name += '.physical_drive'
    rc = run_cmd(
        LOCK_FILE_COMMAND + 'hpssacli ctrl slot=%s pd all show detail' % slot)

    if rc.exitcode != 0:

        r = MetricData.single('check.failure',
                              Severity.fail,
                              '{check} slot: {slot} failed with: {error}',
                              {'check': drive_result.name,
                               'slot': slot,
                               'error': str(rc.output),
                               'component': 'swiftlm-scan'})
        return [r]

    # Remove blank lines and strip trailing/leading spaces for each line
    lines = [l.strip() for l in rc.output.split('\n') if l.strip()]

    if not lines:
        r = MetricData.single('check.failure',
                              Severity.fail,
                              '{check} slot: {slot} failed with: {error}',
                              {'check': drive_result.name,
                               'slot': slot,
                               'error': 'No usable output from hpssacli',
                               'component': 'swiftlm-scan'})
        return [r]

    if is_cont_heading(lines[0]):
        lines = lines[1:]

    drives = []
    drive_info = {}
    for line in lines:
        # The first two lines for each drive are special.

        # The physicaldrive line will contain 2 colons and duplicates
        # information so we drop it.
        cc = line.count(':')
        if cc > 1:
            continue

        # The Array # line may be useful in the future but does not follow
        # the format of colon seperated infommation.
        # It is also the only delimiter between drives. We create a new
        # drive_info dict when we see it.
        if line.startswith('array '):
            if drive_info:
                drives.append(drive_info)
                drive_info = {}
            drive_info['array'] = line.split()[1]
            continue

        k, v = line.split(':', 1)
        k = k.strip().lower()
        v = v.strip()
        drive_info[k] = v

    # Have to add the last drive.
    if drive_info:
        drives.append(drive_info)

    for d in drives:
        results.extend(check_physical_drive(d, drive_result))

    return results


def check_physical_drive(d, base):
    r = base.child(dimensions={
        'status': d.get('status', 'NA'),
        'serial': d.get('serial number', 'NA'),
        'box': d.get('box', 'NA'),
        'bay': d.get('bay', 'NA'),
        'component': 'physical_drive',
    })

    if d.get('status', 'NA') != 'OK':
        r.value = Severity.fail
        r.message = 'physical_drive'
    else:
        r.value = Severity.ok

    return [r]


def get_logical_drive_info(slot, cache_check=True):
    """
    array L
      Logical Drive: 12
         Size: 1.8 TB
         Fault Tolerance: 0
         Heads: 255
         Sectors Per Track: 32
         Cylinders: 65535
         Strip Size: 256 KB
         Full Stripe Size: 256 KB
         Status: OK
         Caching:  Enabled
         Unique Identifier: 600508B1001CEA938043498011A76404
         Disk Name: /dev/sdl
         Mount Points: /srv/node/disk11 1.8 TB Partition Number 2
         OS Status: LOCKED
         Logical Drive Label: AF3C73D8PACCR0M9VZ41S4QEB69
         Drive Type: Data
         LD Acceleration Method: Controller Cache

    BUG:
    It appears that the current build of hpssacli has a bug and outputs
    Disk Name and Mount Points on the same line. We work around this by
    checking for these specifically but that could fail if they change
    """
    results = []
    drive_result = BASE_RESULT.child()
    drive_result.name += '.' + 'logical_drive'
    rc = run_cmd(
        LOCK_FILE_COMMAND + 'hpssacli ctrl slot=%s ld all show detail' % slot)

    if rc.exitcode != 0:

        r = MetricData.single('check.failure',
                              Severity.fail,
                              '{check} slot: {slot} failed with: {error}',
                              {'check': drive_result.name,
                               'slot': slot,
                               'error': str(rc.output),
                               'component': 'swiftlm-scan'})
        return [r]

    # Remove blank lines and strip trailing/leading spaces for each line
    lines = [l.strip() for l in rc.output.split('\n') if l.strip()]
    if not lines:
        r = MetricData.single('check.failure',
                              Severity.fail,
                              '{check} slot: {slot} failed with: {error}',
                              {'check': drive_result.name,
                               'slot': slot,
                               'error': 'No usable output from hpssacli',
                               'component': 'swiftlm-scan'})
        return [r]

    # First line should be the controller model and slot number.
    # We already have this so remove it if it exists
    if is_cont_heading(lines[0]):
        lines = lines[1:]

    drives = []
    drive_info = {}
    for line in lines:

        # If we see two colons we have to assume that it is a bugged version
        # of hpssacli and split them accordingly.
        cc = line.count(':')
        if cc == 2:
            _, dn, mp = line.split(':')
            drive_info['disk name'] = dn.strip().split()[0]
            drive_info['mount points'] = mp.strip()
            continue

        # The Array # line may be useful in the future but does not follow
        # the format of colon seperated infommation.
        # It is also the only delimiter between drives. We create a new
        # drive_info dict when we see it.
        if line.startswith('array '):
            if drive_info:
                drives.append(drive_info)
                drive_info = {}
            drive_info['array'] = line.split()[1]
            continue

        k, v = line.split(':', 1)
        k = k.strip().lower()
        v = v.strip()
        drive_info[k] = v

    # Have to add the last drive.
    if drive_info:
        drives.append(drive_info)

    for d in drives:
        results.extend(check_logical_drive(d, drive_result, cache_check))

    return results


def check_logical_drive(d, base, cache_check):
    results = []
    base = base.child(dimensions={
        'status': d.get('status', 'NA'),
        'component': 'logical_drive',
        'logical_drive': d.get('array', 'NA'),
        'caching': d.get('caching', 'NA')
    })

    r = base.child()
    r['sub_component'] = 'lun_status'
    if d.get('status', 'NA') != 'OK':
        r.value = Severity.fail
        r.message = 'l_drive'
    else:
        r.value = Severity.ok
    results.append(r)

    if cache_check:
        r = base.child()
        r['sub_component'] = 'cache_status'
        if d.get('caching', 'NA') != 'Enabled':
            r.value = Severity.fail
            r.message = 'l_cache'
        else:
            r.value = Severity.ok
        results.append(r)

    return results


def main():
    """Check controller and drive information with hpssacli"""
    cache_check = True
    try:
        cp = configparser.RawConfigParser()
        cp.read(CONFIG_FILE)
        cc = cp.getboolean('hpssacli', 'check_cache')
        if not cc:
            cache_check = False
    except Exception:
        pass

    results, slots = get_smart_array_info()

    for slot in slots:
        results.extend(get_physical_drive_info(slot))
        results.extend(get_logical_drive_info(slot,
                                              cache_check=cache_check))

    return results
