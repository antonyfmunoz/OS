#!/bin/bash

COMMAND=$1

case $COMMAND in

research)

./13_Scripts/os.sh research

;;

content)

./13_Scripts/os.sh content

;;

discover)

python 13_Scripts/instagram_target_discovery.py

;;

scan)

python 13_Scripts/instagram_scanner.py

;;

outreach)

./13_Scripts/dm_drafter.sh

;;

report)

./13_Scripts/os.sh report

;;

*)

echo "Unknown command"

;;

esac