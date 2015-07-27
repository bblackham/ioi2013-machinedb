#!/usr/bin/env python

import os, sys, math

import tornado.httpserver
import tornado.web
import traceback
import time
from datetime import datetime, timedelta
from tornado.web import RequestHandler
from SQLUtils import Session, SessionGen
from sqlalchemy.exc import IntegrityError

from schema import ARPEntry, Machine, Location, LocationMapping, MachineStatus, GlobalsEntry, Switch
from common import get_location_for_ip

from os import system

from cms.db.User import User

import logger

global restricted_access_only
restricted_access_only = True
    
# --------------------------------------- Helper Functions --------------------------------------

def str_to_num(s):
    try:
        return int(s)
    except exceptions.ValueError:
        return 0

def timestr_to_ctime(s):
    return (time.mktime(s.timetuple()) if s is not None else 0)

def lookup_arp_entry_from_ip(ip_address, session=None):
    if session is None:
        with SessionGen(commit=False) as session:
            return lookup_arp_entry_from_ip(ip_address, session)
    else:
        results = session.query(ARPEntry).\
                filter(ARPEntry.ip_address==ip_address).\
                all()
        if len(results) > 0:
            return results[0]
        else:
            return None

def lookup_mac_address_from_ip(ip_address, session=None):
    arp = lookup_arp_entry_from_ip(ip_address, session)
    return arp.ip_address if arp is not None else ''

def lookup_user_from_ip(ip_address, session):
    results = session.query(User).\
            filter(User.ip == ip_address).all()
    if len(results) > 0:
        return results[0]
    else:
        return None

def enable_contestant_machine_reimage():
    system('rm -rf /srv/tftp/pxelinux.cfg/01-*')

def disable_contestant_machines_reimage(arp_entry, session):
    f = file('/srv/tftp/pxelinux.cfg/01-%s' % arp_entry.mac_address.replace(':','-').lower(), 'w')
    f.write('''default syslinux/chain.c32\nappend hd0\n''')
    f.close()

def get_current_image_version(session):
    invalid_ver = "-10000"
    if not session:
        return invalid_ver
    gb = session.query(GlobalsEntry).first()
    if not gb or not gb.current_image_version:
        return invalid_ver
    return gb.current_image_version

def set_current_image_version(version, session):
    if not session:
        return "No database session."
    if not version or len(version) <= 0:
        return "Invalid version."
    gb = session.query(GlobalsEntry).first()
    if not gb:
        gb = GlobalsEntry(current_image_version = version)
        session.add(gb)
        enable_contestant_machine_reimage()
    else:
        if gb.current_image_version != version:
            enable_contestant_machine_reimage()
        gb.current_image_version = version
    return None

def check_if_machine_needs_reimage(arp_entry, session):
    reimage_val = 0
    continueboot_val = 1
    if not arp_entry or not session:
        return reimage_val
    machine = session.query(Machine).filter(Machine.mac_address==arp_entry.mac_address).first()
    if not machine:
        return reimage_val
    if not machine.status:
        return reimage_val
    if str_to_num(machine.status.image_version) != str_to_num(get_current_image_version(session)):
        return reimage_val
    return continueboot_val

def free_dhcpd_lease(mac_address_to_kill):
    system("./free-lease.sh mac %s" % mac_address_to_kill)
    # system("./GenerateConfigs.py && /etc/init.d/isc-dhcp-server restart")

def free_dhcpd_lease_up(ip_address_to_kill):
    system("./free-lease.sh ip %s" % ip_address_to_kill)

# --------------------------------------- Request Handlers --------------------------------------

class BaseHandler(RequestHandler):
    def prepare(self):
        """This method is executed at the beginning of each request.

        """
        self.set_header("Cache-Control", "no-cache, must-revalidate")

        self.sql_session = Session()
        self.r_params = self.render_params()
        self.r_params["warning"] = ""
        self.r_params["success"] = ""

    def render_params(self):
        """Return the default render params used by almost all handlers.

        return (dict): default render params

        """
        global restricted_access_only
        ret = {}

        ip_address = self.request.remote_ip
        arp_entry = lookup_arp_entry_from_ip(ip_address, self.sql_session)
        machine = None
        lm = None
        if arp_entry:
            machine = self.sql_session.query(Machine).filter(Machine.mac_address==arp_entry.mac_address).first()
            if machine:
                lm = self.sql_session.query(LocationMapping).filter(LocationMapping.machine==machine).first()

        # If a machine has no location mapping, then we assume it's not a contestant machine.
        self.allow_restricted_access = True if lm is None else False
        if not restricted_access_only:
            self.allow_restricted_access = True

        ret["ip_address"] = ip_address
        ret["arp_entry"] = arp_entry
        ret["machine"] = machine
        ret["lm"] = lm

        ret["location"] = str(lm.location) if lm is not None else ''
        ret["asset_number"] = machine.asset_number if machine is not None else ''
        ret["notes"] = machine.notes if machine is not None else ''

        location_for_ip = get_location_for_ip(ip_address, self.sql_session)
        ret["location_for_ip"] = str(location_for_ip) if location_for_ip is not None else ''
        ret["network_unknown"] = location_for_ip is None

        ret["show_sidebar"] = True
        ret["restricted_access_only"] = str(restricted_access_only)
        ret["restricted_access_only_checkbox"] = 'checked' if restricted_access_only else ''

        return ret

    def finish(self, *args, **kwds):
        """ Finishes this response, ending the HTTP request.

        We override this method in order to properly close the database.

        """
        if hasattr(self, "sql_session"):
            try:
                self.sql_session.close()
            except Exception as error:
                logger.warning("Couldn't close SQL connection: %r" % error)
        try:
            tornado.web.RequestHandler.finish(self, *args, **kwds)
        except IOError:
            # When the client closes the connection before we reply,
            # Tornado raises an IOError exception, that would pollute
            # our log with unnecessarily critical messages
            logger.debug("Connection closed before our reply.")

    def write_error(self, status_code, **kwargs):
        if "exc_info" in kwargs and \
                kwargs["exc_info"][0] != tornado.web.HTTPError:
            exc_info = kwargs["exc_info"]
            logger.error(
                "Uncaught exception (%r) while processing a request: %s" %
                (exc_info[1], ''.join(traceback.format_exception(*exc_info))))

        # We assume that if r_params is defined then we have at least
        # the data we need to display a basic template with the error
        # information. If r_params is not defined (i.e. something went
        # *really* bad) we simply return a basic textual error notice.
        if hasattr(self, 'r_params'):
            self.render("error.html", status_code=status_code, **self.r_params)
        else:
            self.write("A critical error has occurred :-(")
            self.finish()

    def try_commit(self):
        try:
            self.sql_session.commit()
        except IntegrityError as error:
            self.r_params["warning"] = "Operation failed: %s" % str(error)
            self.sql_session.rollback()
            return False
        else:
            self.r_params["success"] = "Data succesfully updated."
            return True


class MainHandler(BaseHandler):
    def get(self):
        if self.allow_restricted_access is False:
            self.write("Access denied."); return
        self.render("index.html", **self.r_params)

    def post(self):
        if self.allow_restricted_access is False:
            self.write("Access denied."); return

        location_str = self.get_argument("location", "")
        asset_number = self.get_argument("asset_number", "")
        notes = self.get_argument("notes", "")

        self.r_params["location"] = location_str
        self.r_params["asset_number"] = asset_number
        self.r_params["notes"] = notes

        # Check if it is a valid location.
        location = Location.parse(location_str, self.sql_session)
        if location is None:
            logger.warning("Invalid location entered: `%s'" % location_str)
            self.r_params["warning"] = "`%s' is not a valid location!" % location_str

        arp_entry = self.r_params["arp_entry"]
        if location is not None and arp_entry is not None:
            # Update data if necessary.

            # Update the machine information (asset number and notes).
            machine = self.r_params["machine"]
            if machine is None:
                machine = Machine(
                        mac_address=arp_entry.mac_address,
                        asset_number=asset_number,
                        notes=notes)
                self.sql_session.add(machine)
                logger.info(
                        "New machine with MAC %s has asset number '%s'" % (
                            arp_entry.mac_address, asset_number))
            else:
                if asset_number != machine.asset_number:
                    logger.info(
                            "Changed machine with MAC %s from asset number '%s' to '%s'" % (
                                arp_entry.mac_address,
                                machine.asset_number,
                                asset_number))
                machine.asset_number = asset_number
                machine.notes = notes

            # Is there already a machine here?
            existing = self.sql_session.query(LocationMapping).filter(LocationMapping.location==location).first()
            if existing and existing.machine != machine:
                logger.warning("Existing machine with MAC address %s at location %s on switch %s port %d got bumped!" % (
                    existing.machine.mac_address, existing.location, existing.switch.name, existing.switch_port))
                self.sql_session.delete(existing)

            # Now create the location mapping.
            lm = self.sql_session.query(LocationMapping).filter(LocationMapping.machine==machine).first()
            if lm is None:
                lm = LocationMapping(
                        location=location,
                        machine=machine,
                        switch=arp_entry.switch,
                        switch_port=arp_entry.switch_port)
                self.sql_session.add(lm)
                logger.info(
                        "New location mapping. Machine with MAC %s is at location %s on switch %s port %d" % (
                            machine.mac_address,
                            location,
                            arp_entry.switch.name,
                            arp_entry.switch_port))
                free_dhcpd_lease(machine.mac_address)
            else:
                if lm.location != location:
                    logger.info(
                            "Changed location of machine with MAC %s from '%s' to '%s'" % (
                                machine.mac_address,
                                str(lm.location),
                                str(location)))
                lm.location = location
                free_dhcpd_lease(machine.mac_address)

            if self.try_commit():
                self.r_params.update(self.render_params())
            else:
                logger.error("Commit failed")

        self.render("index.html", **self.r_params)

class UserInfoHandler(BaseHandler):
    def get(self):
        ip_address = self.request.remote_ip

        user = lookup_user_from_ip(ip_address, self.sql_session)
 
        arp_entry = lookup_arp_entry_from_ip(ip_address, self.sql_session)
        machine = None
        lm = None
        ms = None
        if arp_entry:
            machine = self.sql_session.query(Machine).filter(Machine.mac_address==arp_entry.mac_address).first()
            if machine:
                lm = self.sql_session.query(LocationMapping).filter(LocationMapping.machine==machine).first()
                ms = machine.status
            else:
                machine = Machine(
                        mac_address=arp_entry.mac_address,
                        asset_number="",
                        notes="")
                self.sql_session.add(machine)

        location = str(lm.location) if lm is not None else 'Location unknown'

        new_image_ver = str(self.get_argument("ver", ""))
        image_version_was_different = False
        if len(new_image_ver) > 0 and machine:
            if ms is None:
                ms = MachineStatus(
                        machine=machine,
                        image_version = new_image_ver,
                        last_heartbeat = datetime.now(),
                        status="?")
                self.sql_session.add(ms)
                image_version_was_different = True
            else:
                image_version_was_different = (ms.image_version != new_image_ver)
                ms.image_version = new_image_ver
                ms.last_heartbeat = datetime.now()
            image_version = machine.status.image_version
        elif ms:
            image_version = ms.image_version
        else:
            image_version = "-2"

        if arp_entry:
            if image_version_was_different and \
                    image_version == get_current_image_version(self.sql_session):
                disable_contestant_machines_reimage(arp_entry, self.sql_session)
 
        newl = "\n"
        if user is None:
            class User:
                def __init__(self):
                    self.username = 'none'
                    self.first_name = 'No'
                    self.last_name = 'Contestant'
                    self.email ='none@none.com'

                    class Contest:
                        def __init__(self):
                            self.start = datetime.now() + timedelta(hours=34)

                    self.contest = Contest()
            user = User()
        self.write(unicode(user.first_name) + " " + unicode(user.last_name) + newl)
        self.write(str(user.username) + newl)
        self.write(str(location) + newl)
        self.write(newl)
        self.write("ip: " + str(ip_address) + newl)
        self.write("username: " + unicode(user.username) + newl)
        self.write("first_name: " + unicode(user.first_name) + newl)
        self.write("last_name: " + unicode(user.last_name) + newl)
        self.write("email: " + str(user.email) + newl)
        self.write("starting_time: " + str(timestr_to_ctime(user.contest.start + timedelta(hours=10))) + newl)
        self.write("image_version: " + str(image_version) + newl)

        if not self.try_commit():
            logger.error("UserInfoHandler Commit failed")

class ImageVersionHandler(BaseHandler):
    def get(self):
        if self.allow_restricted_access is False:
            self.write("Access denied."); return
        self.r_params["current_image_version"] = get_current_image_version(self.sql_session)
        self.render("imagever.html", **self.r_params)

    def post(self):
        if self.allow_restricted_access is False:
            self.write("Access denied."); return
        new_image_ver = self.get_argument("current_image_version", None)
        error = set_current_image_version(new_image_ver, self.sql_session)
        if not error:
            if not self.try_commit():
                logger.error("ImageVersionHandler Commit failed")
        else:
            self.r_params["warning"] = error
        self.r_params["current_image_version"] = get_current_image_version(self.sql_session)
        self.render("imagever.html", **self.r_params)

class AccessRestrictionHandler(BaseHandler):
    def get(self):
        if self.allow_restricted_access is False:
            self.write("Access denied."); return
        self.render("access.html", **self.r_params)

    def post(self):
        if self.allow_restricted_access is False:
            self.write("Access denied."); return
        global restricted_access_only
        raccess = self.get_argument("access_restriction_checkbox", None)
        restricted_access_only = True if raccess is not None else False
        self.r_params["restricted_access_only"] = str(restricted_access_only)
        self.r_params["restricted_access_only_checkbox"] = 'checked' if restricted_access_only else ''
        self.render("access.html", **self.r_params)

class IPListHandler(BaseHandler):
    def get(self):
        if self.allow_restricted_access is False:
            self.write("Access denied."); return
        newl = "\n"
        lm_entries = self.sql_session.query(LocationMapping).all()
        arp_entries = self.sql_session.query(ARPEntry).all()
        for lm in lm_entries:
            if not lm or not lm.machine or not lm.machine.mac_address:
                continue
            for arp in arp_entries:
                if arp.mac_address == lm.machine.mac_address:
                    self.write(str(arp.ip_address) + newl)
                    break


class MachineInfoHandler(BaseHandler):
    def get(self):
        if self.allow_restricted_access is False:
            self.write("Access denied."); return
        mid = self.get_argument("id", None)
        if mid is None:
            self.r_params["warning"] = "Please specify a machine ID. "

        machine = self.sql_session.query(Machine).filter(Machine.id==mid).first()
        stat = None
        lm = None
        arp = None

        self.r_params['id'] = str(mid)
        self.r_params['mac_address'] = "??:??:??:??:??"
        self.r_params['asset_number'] = ""
        self.r_params['notes'] = ""
        self.r_params['location'] = "??"
        self.r_params['image_version'] = ""
        self.r_params['current_image_version'] = get_current_image_version(self.sql_session)
        self.r_params['status'] = ""
        self.r_params['last_heartbeat'] = "?"
        self.r_params['ip'] = "?.?.?.?"
        self.r_params['switchport'] = ""
        self.r_params['switchname'] = ""
        self.r_params['switchlocation'] = ""
        self.r_params['switchip'] = "?.?.?.?"

        if machine:
            self.r_params['mac_address'] = str(machine.mac_address)
            self.r_params['asset_number'] = str(machine.asset_number)
            self.r_params['notes'] = str(machine.notes)
            stat = machine.status
            lm = self.sql_session.query(LocationMapping).filter(LocationMapping.machine==machine).first()
            arp = self.sql_session.query(ARPEntry).filter(ARPEntry.mac_address==machine.mac_address).first()
        else:
            self.r_params["warning"] += "Unknown machine."
        if lm:
            self.r_params['location'] = str(lm.location)
        if stat:
            self.r_params['image_version'] = str(stat.image_version)
            self.r_params['status'] = str(stat.status)
            self.r_params['last_heartbeat'] = str(stat.last_heartbeat)
        if arp:
            self.r_params['ip'] = str(arp.ip_address)
            self.r_params['switchport'] = str(arp.switch_port)
        if lm and lm.switch:
            self.r_params['switchname'] = str(lm.switch.name)
            self.r_params['switchlocation'] = str(lm.switch.location)
            self.r_params['switchip'] = str(lm.switch.ip)

        self.render("machine.html", **self.r_params)

class OverviewHandler(BaseHandler):
    def get_machine_status_as_css_class(self, machine, current_image_version):
        result = 'success'

        if machine.status is not None:
            if machine.status.image_version != current_image_version:
                result = 'warning'
            if datetime.now() > machine.status.last_heartbeat + timedelta(seconds=121):
                result = 'danger'
        else:
            result = 'inverse'

        return 'btn-' + result

    def get(self):
        if self.allow_restricted_access is False:
            self.write("Access denied."); return
        locations = self.sql_session.query(Location).all()
        rows = sorted(list(set(map(lambda L: L.row, locations))))
        cols = sorted(list(set(map(lambda L: L.column, locations))))
        cols = range(cols[0], cols[-1] + 1)  # add missing columns
        civ = get_current_image_version(self.sql_session);

        locations = [ (L.row, L.column) for L in locations ]

        machines = dict(map(
            lambda lm: ((lm.location.row, lm.location.column), lm.machine),
            self.sql_session.query(LocationMapping).all()
        ))

        classes = dict(map(
            lambda k: (k, self.get_machine_status_as_css_class(machines[k], civ)),
            machines.keys()
        ))

        statuses = dict(map(
            lambda lm: ((lm.location.row, lm.location.column), lm.machine.status),
            self.sql_session.query(LocationMapping).all()
        ))

        self.r_params['locations'] = locations
        self.r_params['rows'] = rows
        self.r_params['cols'] = cols
        self.r_params['machines'] = machines
        self.r_params['classes'] = classes
        self.r_params['statuses'] = statuses

        bars = {}
        bars['success'] = len([v for v in classes.itervalues() if v == 'btn-success'])
        bars['warning'] = len([v for v in classes.itervalues() if v == 'btn-warning'])
        bars['danger']  = len([v for v in classes.itervalues() if v == 'btn-danger' ])

        # Log scale, w00t
        safe_log = lambda x: 0 if x < 1 else math.log(x + 1)
        bar_sum = sum(map(safe_log, bars.itervalues()))
        for k,v in bars.iteritems():
            bars[k] = safe_log(v) / bar_sum * 100

        self.r_params['bars'] = bars

        self.r_params["show_sidebar"] = False

        self.r_params["cnt_left_up"] = \
            len([1 for k,v in classes.iteritems()
                if k[1] < 10 and v == 'btn-success'])
        self.r_params["cnt_left_down"] = \
            len([1 for k,v in classes.iteritems()
                if k[1] < 10 and v != 'btn-success'])
        self.r_params["cnt_left_missing"] = \
            180 - self.r_params["cnt_left_up"] - self.r_params["cnt_left_down"]

        self.r_params["cnt_right_up"] = \
            len([1 for k,v in classes.iteritems()
                if k[1] > 10 and v == 'btn-success'])
        self.r_params["cnt_right_down"] = \
            len([1 for k,v in classes.iteritems()
                if k[1] > 10 and v != 'btn-success'])
        self.r_params["cnt_right_missing"] = \
            146 - self.r_params["cnt_right_up"] - self.r_params["cnt_right_down"]


        self.render("overview.html", **self.r_params)

class EvictMachineHandler(BaseHandler):
    def get(self):
        if self.allow_restricted_access is False:
            self.write("Access denied."); return
        self.r_params['switchname'] = ""; self.r_params['switchport'] = ""; self.r_params['log'] = []
        self.render("evict.html", **self.r_params)

    def post(self):
        if self.allow_restricted_access is False:
            self.write("Access denied."); return
        self.r_params['switchname'] = ""; self.r_params['switchport'] = ""; self.r_params['log'] = []
        newl = "\n"; tb = "----"
        switchname = str(self.get_argument("switchname", ""))
        switchport = str(self.get_argument("switchport", ""))
        if len(switchname) <= 0 or len(switchport) <= 0:
            self.r_params['warning'] = "Empty switch name or port."
            self.render("evict.html", **self.r_params)
            return

        self.r_params['log'].append("Finding switch in table..." + newl)
        self.r_params['switchname'] = switchname
        self.r_params['switchport'] = switchport
        switch = self.sql_session.query(Switch).filter(Switch.name == switchname).first()
        if not switch:
            self.r_params['warning'] = "Could not find the given switch."
            self.render("evict.html", **self.r_params)
            return
        self.r_params['log'].append(tb+"Switch found %s %s %s" % (switch.name, switch.location, switch.ip) + newl)

        self.r_params['log'].append("Deleting all LM entries.." + newl)
        lms = self.sql_session.query(LocationMapping).\
            filter(LocationMapping.switch == switch).filter(LocationMapping.switch_port == switchport).all()
        for lm in lms:
            # Delete LM
            self.r_params['log'].append(tb+"%s: Deleting LM id %d." % (str(lm.location), lm.id))
            self.sql_session.delete(lm)

        self.r_params['log'].append("Deleting all ARP entries.." + newl)
        arp_entries = self.sql_session.query(ARPEntry).\
            filter(ARPEntry.switch == switch).filter(ARPEntry.switch_port == switchport).all()
        for arp in arp_entries:
            self.r_params['log'].append(tb+"ARP %s %s" % (arp.mac_address, arp.ip_address) + newl)
            # Delete ARP entry
            free_dhcpd_lease_up(arp.ip_address)
            self.sql_session.delete(arp)

        if not self.try_commit():
            logger.error("EvictMachineHandler Commit failed")

        self.render("evict.html", **self.r_params)        
           

# --------------------------------------- Main --------------------------------------

class SetupWebServer(tornado.web.Application):
    """Service that runs the web server serving the contestants.

    """
    def __init__(self):
        print "IOI 2013 Contestant Management Web Server"
        parameters = {
            "template_path": os.path.join(os.path.dirname(__file__), "templates"),
            "static_path": os.path.join(os.path.dirname(__file__), "static"),
            "debug": '--debug' in sys.argv,
        }

        print "Starting Tornado...";
        tornado.web.Application.__init__(self, handlers, **parameters)

        listen_port = 2013 + int(sys.argv[1])
        listen_address = '0.0.0.0'

        print "Ready, listening for requests...";
        self.http_server = tornado.httpserver.HTTPServer(self, xheaders=True)
        self.http_server.listen(listen_port, address=listen_address)
        self.instance = tornado.ioloop.IOLoop.instance()

    def run(self):
        self.instance.start()


handlers = [
    (r"/", MainHandler),
    (r"/info", UserInfoHandler),
    (r"/iplist", IPListHandler),
    (r"/machine", MachineInfoHandler),
    (r"/overview", OverviewHandler),
    (r"/imagever", ImageVersionHandler),
    (r"/evict", EvictMachineHandler),
    (r"/access", AccessRestrictionHandler),
]


if __name__ == "__main__":
    SetupWebServer().run()
