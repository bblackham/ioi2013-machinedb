#!/usr/bin/env python

import sys

from common import normalise_mac_address, normalise_ip_address
from schema import ARPEntry, Switch, LocationMapping
from SQLUtils import SessionGen
from datetime import datetime

from os import system

import logger

if len(sys.argv) != 5:
    print "Usage: UpdateARPEntry.py <MAC address> <IP address> <switch name> <switch port>"
    sys.exit(1)

mac_address = normalise_mac_address(sys.argv[1])
ip_address = normalise_ip_address(sys.argv[2])
switch_name = sys.argv[3]
switch_port = int(sys.argv[4])

with SessionGen(commit=True) as session:
    #logger.info("ARPEntry mac: " + str(mac_address) + " ip:" + str(ip_address) + " switch name:" + str(sys.argv[3]) + " switch port:" + str(sys.argv[4]) )

    old_entries = session.query(ARPEntry).filter(ARPEntry.mac_address == mac_address).all()
    for e in old_entries:
        session.delete(e)

    old_entries = session.query(ARPEntry).filter(ARPEntry.ip_address == ip_address).all()
    for e in old_entries:
        session.delete(e)

    switch = session.query(Switch).filter(Switch.name==switch_name).first()
    if switch is None:
        logger.info("Created new switch '%s'" % switch_name)
        switch = Switch(name=switch_name)
        session.add(switch)

    lms = session.query(LocationMapping).filter(LocationMapping.switch == switch).filter(LocationMapping.switch_port == switch_port).all()
    for lm in lms:
        if lm.machine.mac_address != mac_address:
            session.delete(lm)

    arp_entries = session.query(ARPEntry).filter(ARPEntry.switch == switch).filter(ARPEntry.switch_port == switch_port).all()
    for arp in arp_entries:
        if arp.mac_address != mac_address:
            session.delete(arp)

    session.add(ARPEntry(
        mac_address=mac_address,
        ip_address=ip_address,
        switch=switch,
        switch_port=switch_port,
        updated=datetime.now()))

