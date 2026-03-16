# Skill: Process Signal Queue

## Purpose

Process raw signals stored in the inbox and convert them into structured ICP intelligence.

This skill scans the raw signal inbox and runs the signal intelligence workflow on each signal.

---

## Input

Source folder:

01_Inbox/raw_signals

Signals may include:

- Reddit posts
    
- Instagram comments
    
- Quora questions
    
- YouTube comments
    
- DM conversations
    
- forum discussions
    

---

## Process

1. Scan the folder:
    

01_Inbox/raw_signals

2. For each signal file:
    

- Load the signal text
    
- Run the skill:
    

06_Skills/research/analyze_icp_signal.md

3. Generate an ICP insight entry.
    
4. Save the insight to:
    

07_Knowledge/ICP

5. Move the processed signal to:
    

01_Inbox/processed_signals

## Result

Signals are analyzed once, converted into intelligence, and archived.
    

---

## Output

Save the insight to:

07_Knowledge/ICP

Naming format:

insight_.md

---

## Result

Raw signals are converted into permanent ICP intelligence stored in the knowledge base.