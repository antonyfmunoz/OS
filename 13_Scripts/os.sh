#!/bin/bash

COMMAND=$1

echo ""
echo "OS Command Interface"
echo "---------------------------------"
echo "Command: $COMMAND"
echo ""

case $COMMAND in

scrape)
./13_Scripts/workflow_runner.sh apify_scrape
;;

score)
./13_Scripts/workflow_runner.sh icp_score
;;

research)
./13_Scripts/workflow_runner.sh signal_intelligence
;;

patterns)
./13_Scripts/workflow_runner.sh pattern_analysis
;;

report)
./13_Scripts/workflow_runner.sh market_intelligence_report
;;

content)
./13_Scripts/workflow_runner.sh content_engine
;;

outreach)
./13_Scripts/workflow_runner.sh outreach_pipeline
;;

*)
echo "Unknown command."
echo ""
echo "Available commands:"
echo ""
echo "os scrape      → scrape Instagram signals via Apify"
echo "os score       → run ICP scorer on raw signals"
echo "os research    → analyze signals"
echo "os patterns    → detect ICP patterns"
echo "os report    → generate ICP report"
echo "os content     → generate content ideas"
echo "os outreach    → generate outreach messages"
;;

esac