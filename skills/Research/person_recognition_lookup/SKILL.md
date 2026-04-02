---
name: person-recognition-lookup
description: "Check if a person is known to the system and what the relationship context is — run before any first contact, outreach generation, or sales call."
allowed-tools: "Read, Bash"
trigger: both
effort: high
context: fork
version: 1.0
---

# Skill: Person Recognition Lookup

## Purpose
Before any interaction with a person, check if they are known to the system and what the relationship context is.

## Outcome
No agent ever contacts someone who is already in a relationship with Antony as if they were a stranger.

## Decision Criteria
- Any first contact with a new person
- Run before any outreach is generated
- Run before any sales call

## Execution Steps
1. Check Notion Pipeline/CRM for name or handle
2. Check Neon memory for prior interactions
3. Check meeting history — have they appeared on a call before?
4. Check last 30 days Discord mentions
5. Synthesize relationship status:
   - Unknown — proceed with standard approach
   - Known lead — pull relationship context, surface to Sales Agent
   - Known contact (non-lead) — flag to DEX before any outreach
   - Warm relationship — never use cold opener, flag to DEX for personal outreach

## Failure Modes
- Skipping this check and cold-messaging someone Antony has an existing relationship with
- Checking only one source — people appear in multiple systems
- Treating a known lead as unknown because they're in a different system

## Measurement
- Zero instances of cold-messaging a known contact
