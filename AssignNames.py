#!/usr/bin/env python

from SQLUtils import Session, SessionGen
from schema import Location
import sys
import csv
import random

def get_names(fn):
    with open(fn) as f:
        reader = csv.reader(f, delimiter=',', quotechar="'")
        for row in reader:
            yield row

def get_locations():
    return [ '%c%d' % (l.row, l.column) for l in Session().query(Location).all() ]

def gen_random(names, locs):
    random.shuffle(names)
    return gen_ordered(names, locs)

def gen_ordered(names, locs):
    for loc, name in zip(locs, names):
        name.insert(0, loc)
        yield name

if __name__ == '__main__':
    names = list(get_names('/home/b/names'))
    locations = get_locations()

    result = None
    if '--random' in sys.argv:
        result = gen_random(names, locations)
    else:
        result = gen_ordered(names, locations)

    writer = csv.writer(sys.stdout, delimiter=',', quotechar="'", quoting=csv.QUOTE_NONNUMERIC)
    for row in result:
        writer.writerow(row)
