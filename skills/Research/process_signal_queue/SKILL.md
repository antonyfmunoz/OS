---
name: process-signal-queue
description: "Process raw signals stored in the inbox and convert them into structured ICP intelligence — run before every outreach cycle to ensure the signal queue is at zero."
allowed-tools: "Read, Bash"
trigger: both
effort: high
context: fork
version: 1.0
---

# Skill: Process Signal Queue

## Purpose

Process raw signals stored in the inbox and convert them into structured ICP intelligence. Scans the raw signal inbox, runs signal analysis on each signal, and archives processed signals.

---

## Outcome

All raw signals in `01_Inbox/raw_signals` analyzed, converted to ICP insights in `07_Knowledge/ICP`, and moved to `01_Inbox/processed_signals`. Zero unprocessed signals remain.

---

## Best-Practice Benchmark

Every signal that enters the inbox must be processed before the next outreach cycle runs. Unprocessed signals are lost intelligence. The queue should be at zero before any outreach is generated.

---

## Decision Criteria

- Process all signals in queue regardless of apparent quality — let the analysis determine ICP match
- Archive immediately after processing — do not leave signals in raw_signals after analysis
- If a signal file is malformed or empty: log the error, archive it, continue
- Stop and flag if: more than 50 signals are queued (signals a scraper issue, not normal volume)

---

## Execution Steps

1. Scan folder: `01_Inbox/raw_signals`
2. List all signal files
3. For each signal file:
   a. Load the signal text
   b. Run skill: `skills/Research/analyze_icp_signal.md`
   c. If ICP match is HIGH or MEDIUM: generate ICP insight and save to `07_Knowledge/ICP/insight_[slug].md`
   d. Move the processed signal to: `01_Inbox/processed_signals`
4. Report: total processed, total insights saved, total skipped (low/no ICP match)

---

## Failure Modes

- Leaving signals in raw_signals after processing (creates duplicate processing risk)
- Skipping signals that seem low quality — analysis determines quality, not appearance
- Processing without archiving (queue never clears)
- Running outreach generation before the signal queue is cleared

---

## Measurement

- Queue clearance rate: % of signals processed per cycle (target: 100%)
- Insight yield rate: % of processed signals that produce a saved insight
- Processing latency: time from signal arrival to processing (target: within 24 hours)

---

## Improvement Opportunities

- Add signal source tagging at ingestion (Reddit vs. Instagram vs. YouTube) to enable source quality tracking
- Build a duplicate detection check before processing to avoid redundant insights
- Automate queue size alerting if volume exceeds 50 (indicates scraper issue)


## Gotchas
- Add failures here as they occur.
- This section compounds over time.
