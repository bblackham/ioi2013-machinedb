#!/usr/bin/env python

from schema import Switch, Machine, Location
from SQLUtils import Base, SessionGen

switches = [
    ( "uqc-302-ag01", "Rm 302",         "172.16.0.4"),
    ( "uqc-302-ag02", "Rm 302",         "172.16.0.5"),
    ( "uqc-258-as01", "Board Rm",       "172.16.0.6"),
    ( "uqc-258-as02", "Board Rm",       "172.16.0.7"),
    ( "uqc-258-as03", "Board Rm",       "172.16.0.8"),
    ( "uqc-255-as01", "VIP Rm",         "172.16.0.9"),
    ( "uqc-226-a13-as01",  "Conference Rm",  "172.16.0.10"),
    ( "uqc-226-a8-as01",   "Conference Rm",  "172.16.0.11"),
    ( "uqc-226-bc16-as01", "Conference Rm",  "172.16.0.12"),
    ( "uqc-226-de16-as01", "Conference Rm",  "172.16.0.13"),
    ( "uqc-226-fg16-as01", "Conference Rm",  "172.16.0.14"),
    ( "uqc-226-hi13-as01", "Conference Rm",  "172.16.0.15"),
    ( "uqc-226-jk13-as01", "Conference Rm",  "172.16.0.16"),
    ( "uqc-226-lm13-as01", "Conference Rm",  "172.16.0.17"),
    ( "uqc-226-no13-as01", "Conference Rm",  "172.16.0.18"),
    ( "uqc-226-pq13-as01", "Conference Rm",  "172.16.0.19"),
    ( "uqc-226-rs16-as01", "Conference Rm",  "172.16.0.20"),
    ( "uqc-226-tu16-as01", "Conference Rm",  "172.16.0.21"),
    ( "uqc-226-v15-as01",  "Conference Rm",  "172.16.0.22"),
    ( "uqc-226-v8-as01",   "Conference Rm",  "172.16.0.23"),
    ( "uqc-226-tu6-as01",  "Conference Rm",  "172.16.0.24"),
    ( "uqc-226-rs6-as01",  "Conference Rm",  "172.16.0.25"),
    ( "uqc-226-pq6-as01",  "Conference Rm",  "172.16.0.26"),
    ( "uqc-226-no6-as01",  "Conference Rm",  "172.16.0.27"),
    ( "uqc-226-lm6-as01",  "Conference Rm",  "172.16.0.28"),
    ( "uqc-226-jk6-as01",  "Conference Rm",  "172.16.0.29"),
    ( "uqc-226-hi6-as01",  "Conference Rm",  "172.16.0.30"),
    ( "uqc-226-fg6-as01",  "Conference Rm",  "172.16.0.31"),
    ( "uqc-226-de6-as01",  "Conference Rm",  "172.16.0.32"),
    ( "uqc-226-bc6-as01",  "Conference Rm",  "172.16.0.33"),
    ( "server-switch-spare", "Board Rm", ""),
]

locations = [
    ('A', ((3, 7), (14, 19))),
    ('B', ((1, 9), (12, 19))),
    ('C', ((1, 9), (12, 19))),
    ('D', ((1, 9), (12, 19))),
    ('E', ((1, 9), (12, 19))),
    ('F', ((1, 9), (12, 17))),
    ('G', ((1, 9), (12, 17))),
    ('H', ((1, 9), (12, 18))),
    ('I', ((1, 9), (12, 18))),
    ('J', ((1, 9), (12, 19))),
    ('K', ((1, 9), (12, 19))),
    ('L', ((1, 9), (12, 19))),
    ('M', ((1, 9), (12, 19))),
    ('N', ((1, 9), (12, 19))),
    ('O', ((1, 9), (12, 19))),
    ('P', ((1, 9), (12, 17))),
    ('Q', ((1, 9), (12, 17))),
    ('R', ((1, 9), (12, 17))),
    ('S', ((1, 9), (12, 17))),
    ('T', ((1, 9), (12, 19))),
    ('U', ((1, 9), (12, 19))),
]

Base.metadata.drop_all()
Base.metadata.create_all()

with SessionGen(commit=True) as session:
    for name, location, ip in switches:
        session.add(Switch(name=name, location=location, ip=ip))

    for row, columns in locations:
        for first, last in columns:
            for column in xrange(first, last+1):
                session.add(Location(row=row, column=column))
