#!/bin/bash
intf=`ip addr | grep -A2 UP | tail -1 | awk '{print $NF}'`
cidr=`ip addr | grep -A2 UP | tail -1 | awk '{print $2}'`
gateway=`ip route | grep default | awk '{print $3}'`
echo source "/etc/network/interfaces.d/*" > /etc/network/interfaces
echo auto lo >> /etc/network/interfaces
echo iface lo inet loopback >> /etc/network/interfaces
echo auto ${intf}  > /etc/network/interfaces.d/${intf}
echo iface ${intf} inet static >>  /etc/network/interfaces.d/${intf}
echo address ${cidr} >>  /etc/network/interfaces.d/${intf}
