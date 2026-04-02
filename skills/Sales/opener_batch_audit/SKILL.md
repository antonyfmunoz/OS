---
name: opener-batch-audit
description: "Review opener_stats.json after sufficient volume to identify what's working, what's dying, and what to test next — run weekly when volume exceeds 30 DMs/week or after any opener reaches 50 sends."
allowed-tools: "Read, Bash"
version: 1.0
effort: high
---

!`python3 -c "
import sys; sys.path.insert(0,'/opt/OS')
from dotenv import load_dotenv
load_dotenv('/opt/OS/eos_ai/.env')
try:
    from eos_ai.context import load_context_from_env
    ctx = load_context_from_env()
    print(f'Stage: {getattr(ctx,\"stage\",\"?\")}')
    print(f'ICP: {getattr(ctx,\"icp\",\"Men 18-25\")}')
    print(f'Constraint: {getattr(ctx,\"binding_constraint\",\"leads\")}')
except Exception as e:
    print(f'Context: {e}')
"`


# Skill: Opener Batch Audit

## Purpose
Review opener_stats.json after sufficient volume to identify what's working, what's dying, and what to test next.

## Outcome
Outreach Agent retires underperforming openers and builds next iteration from patterns in top performers.

## Decision Criteria
- Run weekly if volume > 30 DMs/week
- Run after any opener reaches 50 sends

## Execution Steps
1. Read opener_stats.json
2. Sort openers by reply rate
3. Identify top performers (>15% reply rate)
4. Identify retiring openers (<10% reply rate after 50 sends)
5. Identify patterns across top performers:
   - Question vs statement structure
   - Specificity level (general vs hyper-personal)
   - Reference type (content, bio, recent post)
   - Length (short vs medium)
6. Generate the next opener to test based on the dominant pattern in top performers
7. Archive retiring openers with their final performance data
8. Update Outreach Agent with new opener and revised testing queue

## Failure Modes
- Retiring an opener before it reaches 50 sends
- Building the next opener without identifying the pattern — just writing something new
- Running more than 3 openers simultaneously
- Promoting an opener to primary before it has statistical significance

## Measurement
- Week-over-week reply rate trend
- Time to identify a winning opener from first test
