
from schema import Location

machine_subnet = [10, 10]
unknown_switch_offset = 100
ports_per_switch = 30

class BadAddress(Exception):
    pass

def normalise_mac_address(a):
    try:
        bits = a.split(':')
        if len(bits) != 6:
            raise BadAddress
        v = []
        for b in bits:
            try:
                v.append(int(b, 16))
            except ValueError:
                raise BadAddress
            if v[-1] < 0 or v[-1] > 0xff:
                raise BadAddress
    except BadAddress:
        raise BadAddress("Bad MAC address: %s" % a)
    return ':'.join(['%02X' % b for b in v])


def normalise_ip_address(a):
    try:
        octets = a.split('.')
        if len(octets) != 4:
            raise Exception("Bad IP address: %s" % a)
        v = []
        for b in octets:
            try:
                v.append(int(b, 10))
            except ValueError:
                raise Exception("Bad IP address: %s" % a)
            if v[-1] < 0 or v[-1] > 0xff:
                raise BadAddress
    except BadAddress:
        raise BadAddress("Bad IP address: %s" % a)
    return '.'.join(['%d' % b for b in v])


def get_ip_for_location(location, part=False, reverse=False):
    assert len(location.row) == 1
    row_num = ord(location.row) - ord('A') + 1
    octets = [row_num, location.column]
    if not part:
        octets = machine_subnet + octets
    if reverse:
        octets.reverse()
    return '.'.join([str(i) for i in octets])


def get_ip_for_unknown_switchport(switch_id, port, part=False, reverse=False):
    octets = [unknown_switch_offset + switch_id, port]
    if not part:
        octets = machine_subnet + octets
    if reverse:
	octets.reverse()
    return '.'.join([str(i) for i in octets])


def get_location_for_ip(ip_address, session=None):
    if session is None:
        with SessionGen(commit=False) as session:
            return get_location_for_ip(ip_address, session)

    try:
        ip = normalise_ip_address(ip_address)
    except:
        return False
    bits = [int(x,10) for x in ip.split('.')]
    if bits[:2] == machine_subnet:
        row_idx = bits[2]
        if row_idx > 26:
            return None
        row = chr(row_idx + ord('A') - 1)
        col = bits[3]
        return session.query(Location).filter(Location.row==row).filter(Location.column==col).first()
    else:
        return None
