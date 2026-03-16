#!/bin/bash

LEADS_DIR="03_CRM/Lead_Signals"
OUTPUT_DIR="03_CRM/Outreach_Messages/instgram_dm_queue"

for file in $LEADS_DIR/*.md
do

claude "

You are generating a natural Instagram DM.

Context:
This person commented on a post.

Read the lead signal:

$(cat $file)

Goal:
Start a conversation about discipline and productivity without sounding like a sales pitch.

Write a short DM that:

• mirrors their language
• shows you understand their frustration
• asks a question to continue conversation

Tone:
casual
curious
not pushy

Output only the message.

" > "$OUTPUT_DIR/$(basename $file)"

done