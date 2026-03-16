#!/bin/bash

echo ""
echo "EntrepreneurOS Agent Orchestrator"
echo "---------------------------------"

echo ""
echo "Running Research Agent"
./13_Scripts/signal_harvester.sh

echo ""
echo "Running Intelligence Agent"
./13_Scripts/os.sh research
./13_Scripts/os.sh report

echo ""
echo "Running Content Agent"
./13_Scripts/os.sh content

echo ""
echo "Running Outreach Agent"
./13_Scripts/os.sh outreach

echo ""
echo "Running Sales Agent"
./13_Scripts/workflow_runner.sh conversation_assistant

echo ""
echo "Orchestration complete."