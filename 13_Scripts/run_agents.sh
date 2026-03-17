#!/bin/bash

echo "Running OS Agents"

./13_Scripts/agent_router.sh discover
./13_Scripts/agent_router.sh scan
./13_Scripts/agent_router.sh research
./13_Scripts/agent_router.sh content
./13_Scripts/agent_router.sh outreach
./13_Scripts/agent_router.sh report