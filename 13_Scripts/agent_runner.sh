#!/bin/bash

echo "Starting OS Agents"

while true
do

echo "Running Target Discovery"
python 13_Scripts/instagram_target_discovery.py

echo "Running Instagram Scanner"
python 13_Scripts/instagram_scanner.py

echo "Running Signal Intelligence"
./13_Scripts/os.sh research

echo "Running Content Engine"
./13_Scripts/os.sh content

echo "Running Outreach Pipeline"
./13_Scripts/os.sh outreach

echo "Sleeping for 2 hours..."

sleep 7200

done