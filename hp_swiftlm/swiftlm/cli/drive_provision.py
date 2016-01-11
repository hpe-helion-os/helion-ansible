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

"""
This is a python script that will discover the unpartitioned drives on a node,
format them by partitioning and creating a filesystem for them. Both the
partition and the filesystem will then be identically labelled in the format
x"h"z where:

    x = 8 characters representing the ip address of the node in hex
    z = 3 digits representing the disk number

The script will aslo allow the operator to chose individual options to perform
to the disks with different parameters such as:

    --check -c
    --mount -m
    --label -l
    --partition -p
    --all -a
"""

import os
import commands
import sys
import time
import ConfigParser
import socket
import subprocess
import threading
import json
import signal
from optparse import OptionParser
from random import randint
from swiftlm.utils.drivedata import Drive, LogicalVol, DISK_MOUNT, LVM_MOUNT, \
    SwiftlmInvalidConfig

# TODO - Will need to convert most if not all of the output messages to log
# entries when logging is setup

host_file = "/etc/hosts"
conf_file = "/etc/swift/hlm_storage.conf"
thread_timeout = 1800

supported_file_systems = ["xfs"]
disk_model_file = "/etc/swift/disk_models.yml"


class TimeoutError(Exception):
        pass


# TODO - Will need to use config processor / HLM input to
# determine the IP or what interface to check. For now will just return the
# IP that corresponds to the hostname
def get_my_ip(hostname):
    """
    Get node's IP address that corresponds to the hostname
    """
    return socket.gethostbyname(socket.gethostname())


def three_dig_format(digit):
    """
    Create string of 3 digits given any digit < 1000
    """
    if digit.isdigit() and len(digit) < 4:
        if len(digit) == 3:
            return digit
        elif len(digit) == 2:
            return "0" + digit
        elif len(digit) == 1:
            return "00" + digit


def get_ip_label(ip):
    """
    Format ip address of the node and convert into label

    The label will consist of hexadecimal values of the ip. Each octet will be
    converted into it's corresponding hex value and the whole label will be
    saved as an 8 character string. For example, 10.255.0.192 would have a
    label of 0AFF00C0
    """
    ip_label = ""

    for octet in ip.split("."):
        hex_val = hex(int(octet))[2:]

        if len(hex_val) == 1:
            hex_val = "0" + hex_val

        ip_label += hex_val

    return ip_label


def get_drive_partitions(parted_d):
    """
    Returns all partition of a given drives
    """
    status, output = commands.getstatusoutput('/sbin/parted ' + parted_d +
                                              ' print')

    if status == 0:
        if "unrecognised disk label" in output:
            return []
        else:
            partitions = output.split("Flags")[2].split("\n")
    else:
        print("Error reading %s - %s" % (parted_d, output))
        sys.exit(1)

    # Remove blank entries
    for p in partitions:
        if not p:
            partitions.remove(p)

    return partitions


def is_lvm(name):
    """
    Check if device is marked as an lvm
    """
    if "lvm" in name:
        return True
    return False


def is_partition(device):
    """
    Check is a device is a partition
    """
    if device[-1].isdigit():
        return True
    return False


def check_data_matches(cp_input_list, all_drives):
    """
    Verify config processor data and hardware match

    :param cp_input_list: list of tuples that show the devices selected by the
                          configuration(drive/part/lvm name, swift device name)
    :param all_drives: all the devices on a node
    :return data_conflict: boolean value giving conflict status
    """
    data_conflict = False

    for cp_device, swift_name in cp_input_list:

        # Check for lvm
        if is_lvm(swift_name):

            if not os.path.islink(cp_device):
                print ("%s is targeted for swift use but volume is not found"
                       % (cp_device))
                data_conflict = True
            continue

        # Partition if last character is a digit
        elif is_partition(cp_device):

            # Asssume no more than 9 partitions in a drive
            partition = swift_name[-1]
            drive = cp_device[0:-1]

        else:
            drive = cp_device

        if drive in all_drives:
            # Need to check partitions
            if is_partition(cp_device):

                part_match = False

                partitions = get_drive_partitions(drive)

                for part in partitions:
                    if part:
                        part = ' '.join(part.split())

                        if part[0] == partition:
                            part_match = True

                if not part_match:
                    print ("%s%s is targeted for swift use but device %s does "
                           "not have partition %s"
                           % (drive, partition, drive, partition))
                    data_conflict = True

        else:
            print ("%s is targeted for swift use but device is not found"
                   % (drive))
            data_conflict = True

    return data_conflict


def handler(signum, frame):
    """
    Handler that is called if the parted command is > 10 seconds. This will
    then kill the parted command.
    """
    pid_out = commands.getoutput('ps -A')

    for line in pid_out.splitlines():
        if 'parted' in line:
            pid = int(line.split(None, 1)[0])
            os.kill(pid, signal.SIGKILL)

    raise TimeoutError("Parted command is hanging for device")


def find_parted_drives(drives):
    """
    Find partitioned devices

    This goes through each device on he node. If there is no partition present
    it will be added to a list for later partitioning. Output is divided into
    partitioned and unpartitioned drives

    : param drives: list of all drives
    : return partitioned_drives: list of partitioned drives
    : return umpartitioned_drives: list of unpartitioned drives
    """
    partitioned_drives = []
    unpartitioned_drives = []

    signal.signal(signal.SIGALRM, handler)

    for drive in drives:

        status = -1
        signal.alarm(20)

        try:
            status, output = commands.getstatusoutput('/sbin/parted ' +
                                                      drive + ' print')
        except TimeoutError as exc:
            print("%s %s - killing command" % (exc, drive))

        if status == 0 and "Error" not in output:
            partitioned_drives.append(drive)
        elif status == -1:
            continue
        else:
            unpartitioned_drives.append(drive)

    # Disable the alarm
    signal.alarm(0)

    return partitioned_drives, unpartitioned_drives


def get_disk_label_no(drive_partitions, ip_label):
    """
    Returns the swift disk number of a partition that has already been
    labelled
    """
    partitions = drive_partitions.split()

    num = "-1"

    for part in partitions:
        if (ip_label + "h") in part:
            _, num = part.strip("]'").split("h")

    return num


def separate_labelled_devices(ip_label, parted_drives, supported_file_systems,
                              raw_drives, boot_label):
    """
    Separate drives that are already labelled (including boot flags)

    Finds drives that are labelled correctly. It also keeps a
    record of the disk numbers that are labelled

    :param ip_label: hex representation of the ip address that is used for the
                     swift device labels
    :param parted_drives: list of devices that are already partitioned
    :param supported_file_systems: filesystems that are supported
    :param raw_drives: drives that are not yet partitioned
    :param boot_lablel: label associated with any boot device
    :return unlabelled_drives: drives that have not been labelled yet
    :return raw_drives: drives that have not been formatted yet
    :return dsk_label_list: list of devices that have been labelled and their
                            device number
    :return unlabelled_partitions: partitions that have not been labelled yet
    """
    unlabelled_drives = []
    dsk_label_list = []
    unlabelled_partitions = []

    for a_drive in parted_drives:
        drive_partitions = get_drive_partitions(a_drive)

        # Regular drive (one partition)
        if len(drive_partitions) == 1:

            drive_partition = str(drive_partitions)

            if ip_label not in drive_partition:
                raw = False
                for fs in supported_file_systems:
                    if fs in drive_partition:
                        unlabelled_drives.append(a_drive)
                        raw = True
                if not raw:
                    if boot_label not in drive_partitions:
                        raw_drives.append(a_drive)
            # Keep a record of the disk numbers
            else:

                number = get_disk_label_no(drive_partition, ip_label)
                if number is not "-1":
                    dsk_label_list.append([str(int(number)), a_drive + "1"])

        # Raw drive (no partitions)
        elif len(drive_partitions) == 0:

            raw_drives.append(a_drive)

        # Drive with multiple partitions
        else:

            for drive_part in drive_partitions:
                if boot_label not in drive_part:
                    if ip_label not in drive_part:
                        unlabelled_partitions.append(a_drive + drive_part[1])
                    else:
                        number = get_disk_label_no(drive_part, ip_label)
                        if number is not "-1":
                            dsk_label_list.append([str(int(number)),
                                                  a_drive + drive_part[1]])

    return unlabelled_drives, raw_drives, dsk_label_list, unlabelled_partitions


def create_volume_fs(cp_input_list, disk_label_list, iplabel):
    """
    Create xfs filesystems for any volumes that don't have one. Also, add
    labelled volumes to list

    As well as adding the labelled volumes to the disk label list this will
    return a list of unlabelled volumes. Furthermore, any unlabelled volume
    that doesn't have an xfs filesystem will be give one.

    :param cp_input_list: list of tuples that show the devices selected by the
                          configuration (drive/part/lvm name, swift device
                          name)
    :param disk_label_list: list of devices that are labelled and their swift
                            device number ("v" is with the swift number if the
                            device is an lvm)
    :param iplabel: hex representation of the ip address that is used for the
                    swift device labels
    :return blank_volumes: volumes that have yet to be labelled
    :return disk_label_list: list of devices that have been labelled and their
                             device number
    """
    blank_volumes = []

    for full_vol, swift_name in cp_input_list:

        # Only interested in logical volumes
        if "lvm" in swift_name:

            lvm_l_stat, lvm_l_out = \
                commands.getstatusoutput("/usr/sbin/xfs_admin -l " +
                                         full_vol)

            # Create an xfs filesystem if there is not already one present
            if lvm_l_stat != 0:

                # Make sure that the volume is not being used already
                # 1) Check if it has another filesystem
                ext_status, _ = \
                    commands.getstatusoutput("/sbin/e2label" + full_vol)

                if ext_status == 0:
                    print("Cannot proceed - %s has a non-compatible swift fs"
                          % (full_vol))
                    sys.exit(1)

                # 2) Check if already mounted. * Note - os.path.ismount()
                # can't be used as cannot be certain of mount point at this
                # stage
                _, mount_status = commands.getstatusoutput("df")

                logical_vol = full_vol.split("/")[-1]

                if logical_vol in mount_status:
                    print("Cannot proceed - %s is already mounted"
                          % (full_vol))
                    sys.exit(1)

                lvm_xfs_stat, lvm_xfs_out = \
                    commands.getstatusoutput("/sbin/mkfs.xfs -f -i size=1024" +
                                             " " + full_vol)

                if lvm_xfs_stat != 0:
                    print("Error: Failed to create filesystem for volume %s"
                          " - %s" % (full_vol, lvm_xfs_out))
                    sys.exit(1)

                blank_volumes.append(full_vol)

            # Otherwise check if labelled correctly
            else:
                if (iplabel + "v") in lvm_l_out:
                    nop, number = lvm_l_out.strip('"').split("v")
                    disk_label_list.append(["v" + str(int(number)), full_vol])
                else:
                    blank_volumes.append(full_vol)

    return blank_volumes, disk_label_list


def format_drives(blank_drives, unparted_drives, fs, cp_input_list):
    """
    Partition all raw drives

    As well as partitioning and adding a fs to a drive, the function will also
    add them to the unlabelled drives list

    :param blank_drives: list of partitioned drives that do not have a swift
                         label
    :param unparted_drives: list of drives that need to be partitioned
    :param fs: type of filesystem to create
    :parama cp_input_list: list of tuples that show the devices selected by
                           the configuration(drive/part/lvm name, swift device
                           name)
    :return blank_drives: see above
    """
    for unparted in unparted_drives:

        if cp_input_list:
            # Make sure that the drive is marked for swift use by the config
            # processor
            config_match = False

            for full_vol, swift_name in cp_input_list:
                if unparted == full_vol:
                    config_match = True

            if not config_match:
                print("%s has not been selected for swift use" % (unparted))
                continue

        # Partition the drive:
        create_status, create_output = \
            commands.getstatusoutput("/sbin/parted -s " + unparted +
                                     " mklabel gpt")

        if create_status != 0:
            print("Error: Failed to create partition table for disk %s - %s"
                  % (unparted, create_output))
            sys.exit(1)

        partition_status, partition_output = \
            commands.getstatusoutput("/sbin/parted -s -- " + unparted +
                                     " mkpart primary 1 -1")

        if partition_status != 0:
            print("Error: Failed to create partition table for disk %s - %s"
                  % (unparted, partition_output))
            sys.exit(1)

        blockdev_retry_max = 5
        blockdev_retry_count = 0

        while blockdev_retry_count < blockdev_retry_max:
            blockdev_status, blockdev_output = \
                commands.getstatusoutput("/sbin/blockdev --rereadpt " +
                                         unparted)

            if blockdev_status != 0:
                blockdev_retry_count += 1
                time.sleep(1)
            else:
                break

        if blockdev_retry_max == blockdev_retry_count:
            print("Error: Failed to reread the disks partition table %s - %s"
                  % (unparted, blockdev_output))
            sys.exit(1)

        # Need to introduce a delay between creating the partition and the
        # file system
        time.sleep(1)

        # Only supports xfs for now
        if fs == "xfs":
            filesys_status, filesys_output = \
                commands.getstatusoutput("/sbin/mkfs.xfs -f -i size=1024 " +
                                         unparted + "1")

        if filesys_status != 0:
            print("Error: Failed to create filesystem for disk %s - %s"
                  % (unparted, filesys_output))
            sys.exit(1)

        blank_drives.append(unparted)

    return blank_drives


def confirm_config(device, cp_input_list):
    """
    Confirm that the drive is marked for swift use by the config processor

    :param device: the device that is being checked
    :param cp_input_list: list of tuples that show the devices selected by the
                          configuration(drive/part/lvm name, swift device
                          name)
    :return config_match: Boolen to tell if the device is in the confuration
                          processor
    :return config_disk_val: Device number that is suggested for label use
    """
    config_match = False
    config_disk_val = -1

    if cp_input_list:
        for full_vol, swift_name in cp_input_list:
            if device == full_vol:
                config_match = True
                # Remove "disk"
                config_disk_val = swift_name[4:]

    return config_match, config_disk_val


def get_full_vol_label(vol_val, disk_label_list, cp_input_list, ip_label):
    """
    Returns the full fs label for a swift logical volume

    :param vol_val: swift volume number suggested by the config processor
    :param disk_label_list: list of devices that are labelled and their swift
                            device number ("v" is with the swift number if the
                            device is an lvm)
    :param cp_input_list: list of tuples that show the devices selected by the
                          configuration(drive/part/lvm name, swift device
                          name)
    :param ip_label: hex representation of the ip address that is used for the
                     swift device labels
    :return full_vol_label:
    :return: actual volume number (v + digit)
    """
    vol_count = 0
    # Create an array with just the label number for volumes
    temp_vol_labels = []

    for disk_label in disk_label_list:
        # Only include logical volumes which are highlighted by a "v" in
        # the swift device number
        if "v" in disk_label[0]:
            temp_vol_labels.append(int(disk_label[0][1:]))

    vol_number_found = False

    # If the volume number is already in use, select the next available value
    if cp_input_list:
        if int(vol_val) not in temp_vol_labels:
            vol_count = vol_val
            vol_number_found = True

    if not vol_number_found:
        vol_lab_match = True
        while vol_lab_match:
            if vol_count in temp_vol_labels:
                vol_count = vol_count + 1
            else:
                vol_lab_match = False

    full_vol_label = ip_label + "v" + three_dig_format(str(vol_count))

    return full_vol_label, "v" + str(vol_count)


def get_full_label(disk_val, disk_label_list, cp_input_list, ip_label):
    """
    Returns the full fs and partition label for a swift "disk"

    :param disk_val: swift device number suggested by the config processor
    :param disk_label_list: list of devices that are labelled and their swift
                            number ("v" is with the swift number if the device
                            is an lvm)
    :param cp_input_list: list of tuples that show the devices selected by the
                          configuration(drive/part/lvm name, swift device
                          name)
    :param ip_label: hex representation of the ip address that is used for the
                     swift device labels
    :return full_label: full label to be used on a partiton/file system
    :return disk_count: three-digit format of the device number
    """
    disk_count = 0
    # Create an array with just the label number for disks/partitions
    temp_labels = []

    for disk_label in disk_label_list:
        # Don't include logical volumes
        if "v" not in disk_label[0]:
            temp_labels.append(int(disk_label[0]))

    disk_number_found = False

    # If the disk number is already in use, select the next available value
    if cp_input_list:
        if int(disk_val) not in temp_labels:
            disk_count = disk_val
            disk_number_found = True

    if not disk_number_found:
        lab_match = True
        while lab_match:
            if disk_count in temp_labels:
                disk_count = disk_count + 1
            else:
                lab_match = False

    full_label = ip_label + "h" + three_dig_format(str(disk_count))

    return full_label, disk_count


def label_volumes(blank_volumes, ip_label, disk_label_list, cp_input_list):
    """
    Label the filesystem of a logical volume

    :param blank_volumes: volumes that have not been labelled yet
    :param disk_label_list: list of devices that are labelled and their swift
                            device number ("v" is with the swift number if the
                            device is an lvm)
    :param ip_label: hex representation of the ip address that is used for the
                     swift device labels
    :param cp_input_list: list of tuples that show the devices selected by the
                          configuration(drive/part/lvm name, swift device
                          name)
    :return disk_label_list: see above
    """
    for blank_vol in blank_volumes:

        # No need to confirm that volume is marked for swift use as only
        # volumes in the config processor are included from the start

        swift_vol_match = False

        for full_vol, swift_name in cp_input_list:
            if blank_vol == full_vol:
                # Remove "lvm"
                config_vol_val = swift_name[3:]
                swift_vol_match = True

        if not swift_vol_match:
            print("%s has not been selected for swift use" % (blank_vol))
            continue

        full_label, volume_number = get_full_vol_label(config_vol_val,
                                                       disk_label_list,
                                                       cp_input_list, ip_label)

        vol_label_status, vol_label_output = \
            commands.getstatusoutput('/usr/sbin/xfs_admin -L "' + full_label +
                                     '" ' + blank_vol)

        if vol_label_status != 0:
            print("Error labelling xfs volume %s - %s"
                  % (blank_vol, vol_label_output))
            sys.exit(1)

        disk_label_list.append([str(volume_number), blank_vol])

    return disk_label_list


def label_drives(blank_drives, ip_label, fs, disk_label_list, cp_input_list):
    """
    Label the partition and filesystem of a drive

    :param blank_drives: drives that have not been labelled yet
    :param disk_label_list: list of devices that are labelled and their swift
                            device number ("v" is with the swift number if the
                            device is an lvm)
    :param ip_label: hex representation of the ip address that is used for the
                     swift device labels
    :param cp_input_list: list of tuples that show the devices selected by the
                          configuration(drive/part/lvm name, swift device
                          name)
    :return disk_label_list: see above
    """
    for blank in blank_drives:

        config_match, config_disk_val = confirm_config(blank, cp_input_list)

        if not config_match:
            print("%s has not been selected for swift use" % (blank))
            continue

        full_label, disk_number = get_full_label(config_disk_val,
                                                 disk_label_list,
                                                 cp_input_list, ip_label)

        p_lab_status, p_lab_output = \
            commands.getstatusoutput('/sbin/parted -s ' + blank +
                                     ' name 1 "' + full_label + '"')

        if p_lab_status != 0:
            print("Error labelling partition %s - %s"
                  % (blank, p_lab_output))
            sys.exit(1)

        time.sleep(1)

        xfs_label_status, xfs_label_output = \
            commands.getstatusoutput('/usr/sbin/xfs_admin -L "' +
                                     full_label + '" ' + blank + '1')

        if xfs_label_status != 0:
            print("Error labelling xfs partition %s - %s"
                  % (blank, xfs_label_output))
            # Revert the partition label back
            os.system('/sbin/parted -s ' + blank + ' name 1 "primary"')
            sys.exit(1)

        disk_label_list.append([str(disk_number), blank + "1"])

    return disk_label_list


def label_partitions(blank_partitions, ip_label, fs, disk_label_list,
                     cp_input_list):
    """
    Label particular partitions and filesystems in a drive

    :param blank_partitions: partitions that have not been labelled yet
    :param disk_label_list: list of devices that are labelled and their swift
                            device number ("v" is with the swift number if the
                            device is an lvm)
    :param ip_label: hex representation of the ip address that is used for the
                     swift device labels
    :param cp_input_list: list of tuples that show the devices selected by the
                          configuration(drive/part/lvm name, swift device
                          name)
    :return disk_label_list: see above
    """
    for blank_p in blank_partitions:

        config_match, config_disk_no = confirm_config(blank_p, cp_input_list)

        if not config_match:
            print("%s has not been selected for swift use" % (blank_p))
            continue

        full_label, disk_number = get_full_label(config_disk_no,
                                                 disk_label_list,
                                                 cp_input_list, ip_label)

        p_lab_status, p_lab_output = \
            commands.getstatusoutput('/sbin/parted -s ' + blank_p[:-1] +
                                     ' name ' + blank_p[-1] + ' "' +
                                     full_label + '"')

        if p_lab_status != 0:
            print("Error labelling partition %s - %s"
                  % (blank_p, p_lab_output))
            sys.exit(1)

        time.sleep(1)

        # Make sure that there is a filesystem to label
        part_status, part_output = \
            commands.getstatusoutput('/sbin/parted -s ' + blank_p + ' p')

        # Add the fs to the partition if it isn't there already
        if fs not in part_output and fs == "xfs":

            create_fs_stat, create_fs_out = \
                commands.getstatusoutput('/sbin/mkfs.xfs -f -i size=1024 ' +
                                         blank_p)

            if create_fs_stat != 0:
                print("Error: Failed to create filesystem for partition %s "
                      "- %s" % (blank_p, create_fs_out))
                sys.exit(1)

        fs_label_status, fs_label_output = \
            commands.getstatusoutput('/usr/sbin/xfs_admin -L "' +
                                     full_label + '" ' + blank_p)

        if fs_label_status != 0:
            print("Error labelling xfs partition %s - %s"
                  % (blank_p, fs_label_output))
            # Revert the partition label back
            os.system('/sbin/parted -s ' + blank_p[:-1] + ' name ' +
                      blank_p[-1] + ' "primary"')
            sys.exit(1)

        disk_label_list.append([str(disk_number), blank_p])

    return disk_label_list


def mount_by_label(mount_point, mount_label, return_val):
    """
    Mount a device by it's label

    :param mount_point: directory that device will be mounted to
    :param mount_label: device's label
    :param return_val: list of device mounting results
    """
    command = "/bin/mount -o noatime,nodiratime,nobarrier,logbufs=8 -L " + \
              mount_label + " " + mount_point

    child = subprocess.Popen(command, shell=True, stderr=subprocess.PIPE)

    (outtext, errtext) = child.communicate()
    rc = child.returncode
    if rc != 0:
        return_val.append(command + ": status: " + str(rc) + " (ERROR) -  " +
                          errtext + "\n")
    else:
        return_val.append(command + ": status: " + str(rc) + " (SUCCESS)\n")


def mount_devices(ip_label, disk_label_list, mount_dir, cp_input_list):
    """
    Function to mount all labelled devices. Returns a list of
    mounted drives

    :param ip_label: hex representation of the ip address that is used for the
                     swift device labels
    :param disk_label_list: list of devices that are labelled and their swift
                            device number ("v" is with the swift number if the
                            device is an lvm)
    :param mount_dir: directory where the devices will be mounted to
    :param cp_input_list: list of tuples that show the devices selected by the
                          configuration(drive/part/lvm name, swift device
                          name)
    """
    mounts_to_check = []
    return_results = []
    mount_threads = []

    if not os.path.isdir(mount_dir):
        cmd_status, cmd_output = \
            commands.getstatusoutput("/bin/mkdir " + mount_dir)

        if cmd_status != 0:
            print("Error creating mount directory %s" % (mount_dir))
            sys.exit(1)

    for label_no in disk_label_list:

        # Logical volumes
        if "v" in label_no[0]:
            if cp_input_list:
                mount_vol_match = False
                for full_vol, swift_name in cp_input_list:
                    if ("lvm" + label_no[0][1:]) == swift_name:
                        # Remove "v" from label_no val when creating mount
                        # point
                        mount_point = os.path.join(mount_dir,
                                                   "lvm" + label_no[0][1:])
                        mount_vol_match = True
                if not mount_vol_match:
                    print("Not mounting lvm%s - it isn't marked for swift use"
                          % (label_no[0][1:]))
                    continue
            else:
                mount_point = os.path.join(mount_dir, "lvm" + label_no[0][1:])

        else:
            if cp_input_list:
                mount_match = False
                for full_vol, swift_name in cp_input_list:
                    if ("disk" + label_no[0]) == swift_name:
                        mount_point = mount_dir + "disk" + label_no[0]
                        mount_match = True
                if not mount_match:
                    print("Not mounting disk%s - it isn't marked for swift use"
                          % (label_no[0]))
                    continue
            else:
                mount_point = mount_dir + "disk" + label_no[0]

        # Create mount dir if it doesn't exist
        if not os.path.isdir(mount_point):
            cmp_status, cmp_output = \
                commands.getstatusoutput("/bin/mkdir " + mount_point)

            if cmp_status != 0:
                print("Error creating mount point %s - %s"
                      % (mount_point, cmp_output))
                sys.exit(1)

        # Make sure that the directories are owned by root:root
        chown_status, chown_out = \
            commands.getstatusoutput("/bin/chown root:root " + mount_point)

        if chown_status != 0:
            print("Error changing ownership of %s - %s"
                  % (mount_point, chown_out))
            sys.exit(1)

        if "v" in label_no[0]:
            mount_label = ip_label + "v" + three_dig_format(label_no[0][1:])
        else:
            mount_label = ip_label + "h" + three_dig_format(label_no[0])

        # Check if already mounted
        if os.path.ismount(mount_point):
            print("%s is already mounted" % (mount_point))
        else:
            t = threading.Thread(target=mount_by_label, args=(mount_point,
                                                              mount_label,
                                                              return_results))
            t.start()
            mount_threads.append(t)
        mounts_to_check.append([mount_label, mount_point])

    for mt in mount_threads:
        mt.join(thread_timeout)

    # TODO - this will soon be logged instead of printed out
    if return_results:
        print ("%s" % ("Running: ".join(return_results)))

    # Confirm that the drives are mounted
    for drives in mounts_to_check:
        if os.path.isdir(drives[1]):

            # Double-check the directories are owned by swift:swift
            # NOTE - there is a corner-case where the thread_timeout value
            # expires and the ownership will not be changed here (the mount
            # thread may complete at a later time). In this case, it is
            # necessary that the diags pick up bad ownership asap
            chwn_status, chwn_out = \
                commands.getstatusoutput("/bin/chown swift:swift " +
                                         drives[1])

            if chwn_status != 0:
                print("Error changing ownership of %s - %s"
                      % (drives[1], chwn_out))
                sys.exit(1)

            print("Mounted to %s with label %s" % (drives[1], drives[0]))


def get_product_name():
    '''
    Returns the type of node (product)
    '''
    prod_stat, prod_out = commands.getstatusoutput("dmidecode -s \
                                                   system-product-name")

    if prod_stat != 0:
        print("Error getting node product name - %s"
              % (prod_out))
        sys.exit(1)
    else:
        return prod_out


def generate_drive_info(my_ip, mount_dir, disk_label_list):
    '''
    Gather all the partitioned and labelled drive data on the node into a
    single array of element.

    :param my_ip: ip address of the node
    :param mount_dir: directory where the swift devices were mounted to
    :param disk_label_list: list of devices that are labelled and their swift
                            device number ("v" is with the swift number if the
                            device is an lvm)
    :return node_info: array with all the device information of the node
    '''
    server_type = get_product_name()

    node_info = {"hostname": socket.getfqdn(), "ip_addr": my_ip,
                 "model": server_type}
    drive_info = []

    for lab in disk_label_list:

        # Get the size of the drive
        size_status, size_output = \
            commands.getstatusoutput("/sbin/blockdev --getsize64 " + lab[1])

        if size_status == 0:
            size = ((float(size_output)/1024)/1024)/1024

        else:
            print("Error getting size of %s - %s" % (lab[1], size_output))
            sys.exit(1)

        # Check if drive is mounted
        if "v" in lab[0]:
            mount_to_check = os.path.join(mount_dir, LVM_MOUNT + lab[0][1:])
        else:
            mount_to_check = os.path.join(mount_dir, DISK_MOUNT + lab[0])

        if os.path.ismount(mount_to_check):
            is_mounted = True
        else:
            is_mounted = False

        if "v" in lab[0]:
            drive_info.append({"name": lab[1],
                               "swift_drive_name": "lvm" + lab[0][1:],
                               "size_gb": size,
                               "mounted": str(is_mounted)})
        else:
            drive_info.append({"name": lab[1],
                               "swift_drive_name": "disk" + lab[0],
                               "size_gb": size,
                               "mounted": str(is_mounted)})

    node_info["devices"] = drive_info

    return node_info


def write_to_info_file(node_data, fact_file):
    '''
    Create json file with drive info

    File that captures all the partitioned and labeled drive data on the
    node and writes it to a json file. The data is presented in the following
    format:

    {
        "model": "<node_type>",
        "hostname": "<hostname_of_node>",
        "ip_addr": "<IP_that_corresponds_to_hostname>",
        "devices": [
            {
                "size_gb": "device_size_in_gb",
                "mounted": "<True/False>",
                "name": "/dev/sd<X[0-9]>",
                "swift_drive_name": "disk<A>"
            },
            ...
        ]
    }

    '''

    # Add a randon integer in case there is corruption due to the script being
    # run concurrently
    temp_file = "/tmp/tmp_swift_data" + str(randint(0, 999)) + ".txt"

    file_to_write = open(temp_file, "w")

    file_to_write.write(json.dumps(node_data, indent=4,
                                   separators=(',', ': ')))

    file_to_write.close()

    # Check of the directory of the destination file exists:
    if not os.path.isdir(os.path.dirname(fact_file)):
        print("Cannot write fact file - %s is not a directroy"
              % (os.path.dirname(fact_file)))
        sys.exit(1)

    os.rename(temp_file, fact_file)

    if not os.path.isfile(fact_file):
        print("Error writing file %s" % (fact_file))
        sys.exit(1)


def main():

    # Make sure that the user is root
    if not os.geteuid() == 0:
        print("Script must be run as root")
        sys.exit(1)

    args = OptionParser()

    args.add_option("-v", "--verbose", dest="verbose", action="store_true",
                    help="Give a more verbose output")
    args.add_option("-a", "--all_actions", dest="all_actions",
                    action="store_true",
                    help="Perform all actions on the the drives")
    args.add_option("-p", "--partition", dest="partition", action="store_true",
                    help="Only partition the drives")
    args.add_option("-l", "--label", dest="label", action="store_true",
                    help="Only label the drives")
    args.add_option("-m", "--mount", dest="mount", action="store_true",
                    help="Only mount the drives")
    args.add_option("-c", "--check", dest="check", action="store_true",
                    help="Check config data and hardware match")
    options, arguments = args.parse_args()

    # Get confuration data from /etc/swift/hlm_storage.conf
    if os.path.isfile(conf_file):

        if options.verbose:
            print("Using config data from %s" % (conf_file))

        parser = ConfigParser.RawConfigParser()
        parser.read(conf_file)

        try:
            boot_label = parser.get("swift_config", "boot_label")
        except ConfigParser.NoOptionError:
            boot_label = "boot"

        try:
            disk_pattern = parser.get("swift_config", "disk_pattern")
        except ConfigParser.NoOptionError:
            disk_pattern = "/dev/sd[a-z]\+$"

        try:
            fs = parser.get("swift_config", "file_system")
        except ConfigParser.NoOptionError:
            fs = "xfs"

        try:
            mount_dir = parser.get("swift_config", "mount_dir")
        except ConfigParser.NoOptionError:
            mount_dir = "/srv/node/"

        try:
            fact_file = parser.get("swift_config", "fact_file")
        except ConfigParser.NoOptionError:
            fact_file = "/etc/ansible/facts.d/swift_drive_info.fact"

    else:

        boot_label = "boot"
        disk_pattern = "/dev/sd[a-z]\+$"
        fs = "xfs"
        mount_dir = "/srv/node/"
        fact_file = "/etc/ansible/facts.d/swift_drive_info.fact"

        if options.verbose:
            print("No %s - using default values" % (conf_file))

            print("*****************************")
            print("Boot Label = %s" % (boot_label))
            print("Disk Pattern = %s" % (disk_pattern))
            print("File System  = %s" % (fs))
            print("Mount Directory = %s" % (mount_dir))
            print("File Prefix = %s" % (fact_file))
            print("Not using config processor drive entries")
            print("*****************************")

    # Get disk info from the disk_models.yml
    if os.path.isfile(disk_model_file):
        cp_input_list = []

        try:
            swift_drives = Drive.load(disk_model_file)
        except SwiftlmInvalidConfig as exc:
            print("ERROR: %s" % (exc))
            sys.exit(1)

        for e_drive in swift_drives:
            cp_input_list.append((e_drive.device, e_drive.swift_device_name))

        try:
            swift_log_vols = LogicalVol.load(disk_model_file)
        except SwiftlmInvalidConfig as exc:
            print("ERROR: %s" % (exc))
            sys.exit(1)

        for e_vol in swift_log_vols:
            full_vol = "/dev/" + str(e_vol.lvg) + "/" + e_vol.lvm
            cp_input_list.append((full_vol, e_vol.swift_lvm_name))

    else:
        print("Cannot continue - %s not present" % (disk_model_file))
        sys.exit(1)

    # No need to continue if there are no swift drives/lvms
    if not cp_input_list:
        print("No swift devicess specified in input model for this node")
        sys.exit(0)

    mounted = []

    my_hostname = socket.getfqdn()

    my_ip = get_my_ip(my_hostname)

    ip_label = get_ip_label(my_ip)

    if options.verbose:
        print("IP hex label = %s" % (ip_label))

    status, all_drives = commands.getstatusoutput('ls /dev/sd* | grep "' +
                                                  disk_pattern + '"')

    if status != 0:
        print("Error determining disks on the node")
        sys.exit(1)

    all_drives = all_drives.split('\n')

    data_conflict = check_data_matches(cp_input_list, all_drives)

    if data_conflict:
        sys.exit(1)

    if options.check:
        sys.exit(0)

    parted_drives, raw_drives = find_parted_drives(all_drives)

    blank_drives, unparted_drives, disk_label_list, blank_partitions = \
        separate_labelled_devices(ip_label, parted_drives,
                                  supported_file_systems,
                                  raw_drives, boot_label)

    blank_volumes, disk_label_list = create_volume_fs(cp_input_list,
                                                      disk_label_list,
                                                      ip_label)

    if options.verbose:
        print("Current disk label list = %s" % (str(disk_label_list)))
        print("Unpartitioned disk list = %s" % (str(unparted_drives)))
        print("Unlabelled disk list = %s" % (str(blank_drives)))
        print("Unlabelled partition list = %s" % (str(blank_partitions)))
        print("Unlabelled volume list = %s" % (str(blank_volumes)))

    if options.all_actions or options.partition:
        if not unparted_drives:
            print("No drives that need to be partitioned")
        else:
            print("The following drives are not partitioned - %s"
                  % (str(unparted_drives)))
            blank_drives = format_drives(blank_drives, unparted_drives,
                                         fs, cp_input_list)

    if options.all_actions or options.label:
        if not blank_drives:
            print("No one-partition drives that need to be labelled")
        else:
            print("Label the following drives - %s" % (str(blank_drives)))
            disk_label_list = label_drives(blank_drives, ip_label, fs,
                                           disk_label_list, cp_input_list)
        if not blank_partitions:
            print("No multiple partition drives that need to be labelled")
        else:
            print("Label the following partitions - %s"
                  % (str(blank_partitions)))
            disk_label_list = label_partitions(blank_partitions, ip_label, fs,
                                               disk_label_list, cp_input_list)
        if not blank_volumes:
            print("No volumes that need to be labelled")
        else:
            print("Label the following volumes - %s"
                  % (str(blank_volumes)))
            disk_label_list = label_volumes(blank_volumes, ip_label,
                                            disk_label_list, cp_input_list)

    if options.all_actions or options.mount:
        if not disk_label_list:
            print("No drives ready to be mounted")
        else:
            mount_devices(ip_label, disk_label_list, mount_dir, cp_input_list)

    node_drive_info = generate_drive_info(my_ip, mount_dir, disk_label_list)

    write_to_info_file(node_drive_info, fact_file)


if __name__ == '__main__':
    main()
