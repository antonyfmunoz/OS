---
step: 1
name: Load Conversation
workflow: conversation_assistant
---

# Step 1: Load Conversation

## Purpose
Load the conversation file for the lead being worked.

## Instructions

1. Ask the user for the lead name or file path
2. Read the file from `03_CRM/Conversations/`
3. Confirm the file loaded and display a summary:
   - Lead name
   - Platform
   - Date of last message
   - Current status
   - Number of messages in thread

## Output
Pass the full conversation content to Step 2.
