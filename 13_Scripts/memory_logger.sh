#!/bin/bash

echo ""
echo "OS Memory Logger"
echo "-----------------------------"
echo ""

TIMESTAMP=$(date +%Y-%m-%d_%H-%M)

FILE="08_Memory/Conversion_Signals/memory_$TIMESTAMP.md"

echo "# Operational Memory Entry" >> $FILE
echo "Timestamp: $TIMESTAMP" >> $FILE
echo "" >> $FILE

OBS=$1

echo "Observation:" >> $FILE
echo "$OBS" >> $FILE

echo ""
echo "Memory stored in:"
echo $FILE
