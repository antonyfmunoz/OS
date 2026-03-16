#!/bin/bash

echo "Loaded Skills:"
echo ""

find 06_Skills -name "*.md" | sort | while read file
do
echo "- $file"
done