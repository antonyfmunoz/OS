#!/bin/bash

echo ""
echo "EntrepreneurOS Lead Qualification"
echo "---------------------------------"
echo ""

TIMESTAMP=$(date +%Y-%m-%d_%H-%M)

INPUT_FOLDER="01_Inbox/raw_signals"
OUTPUT_FILE="03_CRM/Lead_Signals/leads_$TIMESTAMP.md"

echo "# Qualified Lead Signals" >> $OUTPUT_FILE
echo "Generated: $TIMESTAMP" >> $OUTPUT_FILE
echo "" >> $OUTPUT_FILE

echo "Scanning signals..."

grep -i -E "wasting|discipline|potential|focus|procrastinat|stuck|direction" $INPUT_FOLDER/*.md >> $OUTPUT_FILE

echo ""
echo "Lead qualification complete."

echo "Saved to:"
echo $OUTPUT_FILE
