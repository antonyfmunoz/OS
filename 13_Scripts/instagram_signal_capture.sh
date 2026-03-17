#!/bin/bash

echo ""
echo "OS Instagram Signal Capture"
echo "---------------------------------------"
echo ""

TIMESTAMP=$(date +%Y-%m-%d_%H-%M)

FILE="01_Inbox/raw_signals/instagram_signals/instagram_comments_$TIMESTAMP.md"

echo "# Instagram Signal" >> $FILE
echo "Captured: $TIMESTAMP" >> $FILE
echo "" >> $FILE

echo "Paste Instagram comment signals below."
echo "Press CTRL+D when finished."
echo ""

cat >> $FILE

echo ""
echo "Signal saved to:"
echo $FILE
