#!/bin/sh

if [ "$1" = "mac" ]
then
    echo "connect
new lease
set hardware-address = $2
open
set ends = 00:00:00:00
update
refresh" | omshell

elif [ "$1" = "ip" ]
then
    echo "connect
new lease
set ip-address = $2
open
set ends = 00:00:00:00
update
refresh" | omshell

else
    echo "Usage: $0 [mac|ip] <address>"
fi
