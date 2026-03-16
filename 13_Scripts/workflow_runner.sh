#!/bin/bash

WORKFLOW=$1

echo ""
echo "EntrepreneurOS Workflow Runner"
echo "--------------------------------"
echo "Running workflow: $WORKFLOW"
echo ""

case $WORKFLOW in

signal_intelligence)
claude --dangerously-skip-permissions "Execute the signal intelligence workflow located in 05_Workflows/research/signal_intelligence. Process signals in 01_Inbox/raw_signals and store insights in 07_Knowledge/ICP."
;;

content_engine)
claude --dangerously-skip-permissions "Execute the content engine workflow. Use market intelligence reports in 07_Knowledge/Reports/Market_Reports to generate hooks, video ideas, and discussion prompts. Save the output to 09_Content/Content_Ideas."
;;

outreach_pipeline)
claude --dangerously-skip-permissions "Execute the outreach pipeline workflow. Generate outreach messages using ICP insights and store lead data in 03_CRM."
;;

outreach_engine)
claude --dangerously-skip-permissions "Execute the outreach engine workflow. Use market intelligence reports in 07_Knowledge/Reports/Market_Reports to generate outreach messages for the ICP. Save outputs to 03_CRM/Outreach_Messages."
;;

market_intelligence_report)
claude --dangerously-skip-permissions "Generate a market intelligence report using all ICP insights in 07_Knowledge/ICP. Summarize pain patterns, psychological states, language patterns, and content opportunities. Store the report in 07_Knowledge/Reports/Market_Reports."
;;

conversation_assistant)
claude --dangerously-skip-permissions "Analyze a sales conversation located in 03_CRM/Conversations and generate the best next response to move the conversation toward a call."
;;

dm_pipeline)
./13_Scripts/dm_drafter.sh
;;

*)
echo "Unknown workflow."
echo ""
echo "Available workflows:"
echo "signal_intelligence"
echo "content_engine"
echo "outreach_pipeline"
echo "outreach_engine"
echo "market_intelligence_report"
echo "conversation_assistant"
echo "dm_pipeline"
;;

esac