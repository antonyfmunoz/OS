---
name: draft-arena-content-post
description: "Write a single short-form content post for the active offer that attracts the ICP and drives engagement or DM replies — run when a content idea or ICP insight is ready to be turned into a post."
allowed-tools: "Read, Bash"
version: 1.0
effort: medium
trigger: both
context: fork
---

!`python3 /opt/OS/scripts/bis_context.py --fields name,icp,offer,stage,primary_channel,binding_constraint,north_star`


# Skill: Draft Arena Content Post

## Purpose

Write a single short-form content post for the active offer that attracts the ICP and drives engagement or DM replies.

---

## Outcome

A ready-to-post caption — under 150 words, no preamble, no explanations. Just the post. Opening line works as a standalone hook.

---

## Best-Practice Benchmark

The opening line must stop the scroll when read alone. If it doesn't create curiosity, friction, or pattern interruption in isolation, it fails before the rest of the post gets read.

---

## Decision Criteria

- End with a question if: you want comments and engagement
- End with a CTA (DM "ready" or link in bio) if: you want direct conversion action
- No hashtags unless specifically requested
- Stay under 150 words — every word must earn its place

---

## Execution Steps

1. Load content input — one of:
   - A content idea from: `09_Content/Content_Ideas/`
   - An ICP insight from: `07_Knowledge/ICP/`
   - A direct topic provided inline
2. Identify the core tension: what limiting belief does the ICP hold?
3. Write the opening line — pattern interrupt, scroll-stop, or identity challenge
4. Read the opening line alone. If it doesn't create curiosity or friction: rewrite it
5. Build 2-3 lines that deepen the pain or reframe the problem
6. Write the close:
   - Option A: a question that provokes comments
   - Option B: a call to action (DM "ready" or link in bio)
7. Review: under 150 words? No hashtags? No preamble? Opening line standalone? If no to any: fix.

---

## Failure Modes

- Opening line that requires the rest of the post to make sense (not standalone)
- Generic hooks that could come from any coach or creator account
- Posts that explain the offer instead of creating curiosity
- Closing with both a question and a CTA (pick one)
- Exceeding 150 words — length kills the format

---

## Measurement

- Engagement rate per post (comments + saves vs. reach)
- DM reply rate for posts ending with CTA
- Scroll-stop rate if video content includes this hook as text overlay

---

## Improvement Opportunities

- Tag each post with the ICP insight or content idea that inspired it
- Track which opening line formats (identity challenge, statistics, direct provocation) convert best
- Build a hook swipe file from posts that outperform in the first 24 hours


## Gotchas
- Add failures here as they occur.
- This section compounds over time.
