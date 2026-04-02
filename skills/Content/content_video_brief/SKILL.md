---
name: content-video-brief
description: "Generate a complete director's brief for any content piece Antony will film — run after a content idea is approved and filming is planned."
allowed-tools: "Read, Bash"
version: 1.0
effort: medium
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


# Skill: Content Video Brief

## Purpose
Generate a complete director's brief for any content piece Antony will film.

## Outcome
Antony can film immediately from this brief without needing to write, plan, or think beyond delivery.

## Decision Criteria
- Any content piece that requires filming
- Run after content idea is approved

## Execution Steps
1. State the hook — the exact first line Antony speaks on camera (one sentence, no more)
2. State the core tension — what is the contradiction or counterintuitive insight at the center?
3. Outline the body — 3-5 bullet points of what gets covered, in sequence
4. State the emotional tone: cinematic, direct, personal, educational, confrontational, etc.
5. State the CTA — exact words for the call to action
6. State the visual framing note — environment, energy, aesthetic direction
7. State the target platform and format: vertical short, horizontal long, etc.

## Failure Modes
- Writing a caption instead of a director's brief
- Not providing the exact hook word-for-word
- Leaving tone or visual direction ambiguous
- Vague CTA ("follow me" instead of "DM me the word SYSTEM")
- Brief that requires Antony to make creative decisions before filming

## Measurement
- Percentage of briefs that require no revision before filming
- Time from brief to filmed content
