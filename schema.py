
import re

from sqlalchemy.types import \
    Boolean, Integer, String, DateTime
from sqlalchemy.schema import Column, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship, backref

from SQLUtils import Base

class Switch(Base):
    __tablename__ = 'net_switches'

    id = Column(
        Integer,
        primary_key=True)

    name = Column(
        String,
        nullable=False)

    location = Column(
        String,
        nullable=True)

    ip = Column(
        String,
        nullable=True)

class Machine(Base):
    __tablename__ = 'net_machines'
    __table_args__ = (
        UniqueConstraint('mac_address'),
    )

    id = Column(
        Integer,
        primary_key=True)

    mac_address = Column(
        String,
        nullable=False)

    asset_number = Column(
        String,
        nullable=True)

    notes = Column(
        String,
        nullable=True)

class MachineStatus(Base):
    __tablename__ = 'net_machinestatus'

    id = Column(
        Integer,
        primary_key=True)

    machine_id = Column(
        Integer,
        ForeignKey(Machine.id,
                   onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
        index=True)
    machine = relationship(Machine, uselist=False, backref=backref('status', uselist=False))

    image_version = Column(
        String,
        nullable=True)

    status = Column(
        String,
        nullable=False)

    last_heartbeat = Column(
        DateTime,
        nullable=False)


class Location(Base):
    __tablename__ = 'net_locations'

    id = Column(
        Integer,
        primary_key=True)

    row = Column(
        String,
        nullable=False,
        index=True)

    column = Column(
        Integer,
        nullable=False,
        index=True)

    def __str__(self):
        return self.row + str(self.column)

    @staticmethod
    def parse(text, session):
        r = re.compile(r'^([A-Z]+)([0-9]+)$', re.IGNORECASE)
        m = r.match(text)
        if m:
            row = m.group(1)
            column = m.group(2)
            return session.query(Location).\
                    filter(Location.row==row).\
                    filter(Location.column==column).\
                    first()
        return None


class LocationMapping(Base):
    __tablename__ = 'net_locationmappings'
    __table_args__ = (
        UniqueConstraint('location_id'),
        UniqueConstraint('machine_id'),
        UniqueConstraint('switch_id', 'switch_port'),
    )

    id = Column(
        Integer,
        primary_key=True)

    location_id = Column(
        Integer,
        ForeignKey(Location.id,
                   onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
        index=True)
    location = relationship(Location, uselist=False, backref=backref('mapping', uselist=False))

    machine_id = Column(
        Integer,
        ForeignKey(Machine.id,
                   onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
        index=True)
    machine = relationship(Machine)

    switch_id = Column(
        Integer,
        ForeignKey(Switch.id,
                   onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
        index=True)
    switch = relationship(Switch)

    switch_port = Column(
        Integer,
        nullable=False,
        index=True)

class ARPEntry(Base):
    __tablename__ = 'net_arp'
    __table_args__ = (
        UniqueConstraint('mac_address'),
    )

    mac_address = Column(
        String,
        primary_key=True)

    ip_address = Column(
        String,
        primary_key=True)

    switch_id = Column(
        Integer,
        ForeignKey(Switch.id,
                   onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
        index=True)
    switch = relationship(Switch)

    switch_port = Column(
        Integer,
        nullable=True)

    updated = Column(
        DateTime,
        nullable=False)

class GlobalsEntry(Base):
    __tablename__ = 'net_globals'

    current_image_version = Column(
        String,
        primary_key=True)
    
