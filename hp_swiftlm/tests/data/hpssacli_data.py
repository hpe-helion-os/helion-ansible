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


PHYSICAL_DRIVE_DATA = """

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
PHYSICAL_DRIVE_STATUS_FAIL = PHYSICAL_DRIVE_DATA.replace(
    'Status: OK', 'Status: FAIL')

LOGICAL_DRIVE_DATA = """

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
"""
LOGICAL_DRIVE_LUN_FAIL = LOGICAL_DRIVE_DATA.replace(
    'Status: OK', 'Status: Fail')
LOGICAL_DRIVE_CACHE_FAIL = LOGICAL_DRIVE_DATA.replace(
    'Caching:  Enabled', 'Caching: Disabled')
# Places Disk Name and Mount Points on the same line.
LOGICAL_DRIVE_DATA_BUGGED = """

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
         Disk Name: /dev/sdl  \
    Mount Points: /srv/node/disk11 1.8 TB Partition Number 2
         OS Status: LOCKED
         Logical Drive Label: AF3C73D8PACCR0M9VZ41S4QEB69
         Drive Type: Data
         LD Acceleration Method: Controller Cache
"""

SMART_ARRAY_DATA = """

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
   PCI Address (Domain:Bus:Device.Function): 0000:03:00.0
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
"""

SMART_ARRAY_CONTROLLER_FAIL = SMART_ARRAY_DATA.replace(
    "Controller Status: OK", "Controller Status: FAIL")
SMART_ARRAY_CACHE_FAIL = SMART_ARRAY_DATA.replace(
    "Cache Status: OK", "Cache Status: FAIL")
SMART_ARRAY_BATTERY_FAIL = SMART_ARRAY_DATA.replace(
    "Battery/Capacitor Status: OK", "Battery/Capacitor Status: FAIL")
SMART_ARRAY_BATTERY_COUNT_FAIL = SMART_ARRAY_DATA.replace(
    "Battery/Capacitor Count: 1", "Battery/Capacitor Count: 0")

SMART_ARRAY_DATA_2_CONT = """

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
   PCI Address (Domain:Bus:Device.Function): 0000:03:00.0
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

Smart Array P410 in Slot 3
   Bus Interface: PCI
   Slot: 3
   Serial Number: PACCR0M9VZ41S4P
   Cache Serial Number: PACCQID12061TTP
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
   PCI Address (Domain:Bus:Device.Function): 0000:03:00.0
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

"""
