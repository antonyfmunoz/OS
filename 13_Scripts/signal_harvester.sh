#!/bin/bash

echo ""
echo "OS Signal Harvester"
echo "--------------------------------"
echo ""

TIMESTAMP=$(date +%Y-%m-%d_%H-%M)

OUTPUT_FILE="01_Inbox/raw_signals/signal_$TIMESTAMP.md"

echo "# Market Signal Capture" >> $OUTPUT_FILE
echo "Captured: $TIMESTAMP" >> $OUTPUT_FILE
echo "" >> $OUTPUT_FILE

echo "Searching Google Trends..."

ICP_KEYWORDS="productivity|mindset|entrepreneur|business|focus|discipline|habit|motivation|self.improvement|success|goal|hustle|startup|burnout|anxiety|mental health|overwhelm|procrastinat|consistency|routine|system|workflow|time management|money|income|freelance|side hustle|career|growth|coaching|accountability"

curl -s "https://trends.google.com/trending/rss?geo=US" \
| grep -o '<title>[^<]*</title>' \
| sed 's/<title>//;s/<\/title>//' \
| tail -n +2 \
| grep -iE "$ICP_KEYWORDS" \
>> $OUTPUT_FILE

echo "" >> $OUTPUT_FILE

echo ""
echo "Importing Instagram signals..."

cat 01_Inbox/raw_signals/instagram_signals/instagram_comments/*.md >> $OUTPUT_FILE 2>/dev/null

echo "Signal harvest complete."

echo "Saved to:"
echo $OUTPUT_FILE
