#!/usr/bin/env python

from SQLUtils import SessionGen
from schema import Switch, Machine, Location, LocationMapping
from common import unknown_switch_offset, ports_per_switch, get_ip_for_location, get_ip_for_unknown_switchport

port_range = lambda: xrange(1, ports_per_switch+1)

# For each switch and each switchport, generate its corresponding DHCP
# configuration line, and DNS line.

zones = {
    'unknown.ioi': '',
    'contestant.ioi': '',
    '10.10.in-addr.arpa': '',
}

class_decls = []
pool_decls = []
with SessionGen(commit=False) as session:
    switches = session.query(Switch).all()
    locations = session.query(Location).all()

    # Construct DNS entries for unknown switchports.
    for switch in switches:
        for port in port_range():
            # In unknown.ioi
            zones['unknown.ioi'] += "%s-%d\tIN\tA\t%s\n" % (switch.name, port, get_ip_for_unknown_switchport(switch.id, port))
            zones['10.10.in-addr.arpa'] += "%s\tIN\tPTR\t%s-%d.unknown.ioi.\n" % (get_ip_for_unknown_switchport(switch.id, port, part=True, reverse=True), switch.name, port)

    # Construct DNS entries for locations.
    for location in locations:
        # In unknown.ioi
        zones['contestant.ioi'] += "%s%d\tIN\tA\t%s\n" % (location.row, location.column, get_ip_for_location(location))
        zones['10.10.in-addr.arpa'] += "%s\tIN\tPTR\t%s%d.contestant.ioi.\n" % (get_ip_for_location(location, part=True, reverse=True), location.row, location.column)

    locationmaps = session.query(LocationMapping).join(Location).join(Machine).join(Switch).all()
    # Construct mapping from location to LocationMapping entry.
    loc_to_mapping = {}
    sp_to_mapping = {}
    mac_to_mapping = {}
    for lm in locationmaps:
        loc_to_mapping[(lm.location.row, lm.location.column)] = lm
        sp_to_mapping[(lm.switch.name, lm.switch_port)] = lm
        if lm.machine is not None:
            mac_to_mapping[lm.machine.mac_address] = lm

    for switch in switches:
        for port in port_range():
            class_decls.append(
'''class "%(remote_id)s-%(circuit_id)d" { match if substring(option agent.remote-id, 2, 100) = "%(remote_id)s" and substring(option agent.circuit-id, 5, 1) = encode-int(%(circuit_id)d, 8); }''' % {
                'remote_id': switch.name,
                'circuit_id': port,
                })

            # Has this port been assigned to a location?
            lm = sp_to_mapping.get((switch.name, port))

            if lm is not None:
                pool_decls.append('host machine_%(machine_id)d { hardware ethernet %(mac_address)s; fixed-address %(ip_address)s; }' % {
                        'machine_id': lm.machine.id,
                        'mac_address': lm.machine.mac_address,
                        'ip_address': get_ip_for_location(lm.location),
                })
            else:
                pool_decls.append('pool { allow members of "%(remote_id)s-%(circuit_id)d"; range %(ip_address)s; default-lease-time 300; max-lease-time 600; }' % {
                        'remote_id': switch.name,
                        'circuit_id': port,
                        'ip_address': get_ip_for_unknown_switchport(switch.id, port),
                })

for zone, text in zones.items():
    f=file('/etc/bind/zones/primary/' + zone, 'w')
    f.write('''$TTL	300
@	IN	SOA	ioi. root.ioi. (
			      1		; Serial
			    300		; Refresh
			    300		; Retry
			2419200		; Expire
			    300 )	; Negative Cache TTL
@	IN	NS	dotone.ioi.
''')
    f.write(text)
    f.close()

f=file('/etc/dhcp/dhcpd-classes.conf', 'w')
for l in class_decls:
	f.write(l + '\n')
f.close()
f=file('/etc/dhcp/dhcpd-pools.conf', 'w')
for l in pool_decls:
	f.write(l + '\n')
f.close()

# jkprint '''
# jk%(class_decls)s
# jk
# jk%(pool_decls)s
# jk''' %{
# jk	'class_decls': '\n'.join(class_decls),
# jk	'pool_decls': '\n            '.join(pool_decls)
# jk}
# jk
