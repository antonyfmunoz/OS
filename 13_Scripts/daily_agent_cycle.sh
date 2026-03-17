#!/bin/bash

echo " "
echo "OS Daily Agent Cycle"
echo "————————————————"
echo " "

echo "Step A: Scraping Instagram Signals"
python 13_Scripts/apify_scraper.py

echo ""
echo "Step B: ICP Scoring and Lead Qualification"
python 13_Scripts/icp_scorer.py

echo ""
echo "Step 0: Harvesting Signals"
./13_Scripts/signal_harvester.sh

echo ""
echo "Step 1: Lead Qualification"
./13_Scripts/lead_qualifier.sh

echo " "
echo "Step 2: Signal Intelligence"
./13_Scripts/os.sh research

echo " "
echo "Step 3: Market Intelligence Report"
./13_Scripts/os.sh report

echo " "
echo "Step 4: Content Generation"
./13_Scripts/os.sh content

echo " "
echo "Step 5: Outreach Message Generation"
./13_Scripts/os.sh outreach

echo " "
echo "Step 6: Founder Briefing"
./13_Scripts/founder_briefing.sh

echo " "
echo "Daily cycle complete."
echo " "
