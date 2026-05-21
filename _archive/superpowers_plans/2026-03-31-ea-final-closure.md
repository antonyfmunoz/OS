# EA Final Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the EA (Executive Assistant) system with terminology renames across the codebase, venture primitive abstraction, and 9 remaining EA feature gaps.

**Architecture:** Three sequential phases — Phase 1 renames terminology everywhere, Phase 2 adds venture primitives to context, Phase 3 adds day reminders, quality gate, meeting minutes, OKR tracking, event management, speaking/PR tracking, board workflows, announcements, and travel completeness. Each phase depends on the prior.

**Tech Stack:** Python 3.12, discord.py (commands.Context), PostgreSQL/Neon via psycopg2, python-dotenv, zoneinfo, dateutil

---

## File Map

**Phase 1 — Renames:**
- Delete: `eos_ai/drip_matrix.py`, `eos_ai/buyback_rate.py`, `eos_ai/perfect_week.py`
- Create: `eos_ai/task_yield_matrix.py`, `eos_ai/founder_rate.py`, `eos_ai/ideal_week.py`
- Modify in-place: `eos_ai/martell_patterns.py`
- Modify imports: `eos_ai/cognitive_loop.py`, `eos_ai/daily_sync.py`, `eos_ai/weekly_review.py`, `eos_ai/week_architect.py`, `eos_ai/ea_best_practices.py`, `eos_ai/portfolio_advisor.py`, `eos_ai/orchestrator.py`, `eos_ai/skill_registry_v2.py`, `eos_ai/founder_capture.py`
- Update commands + imports: `13_Scripts/discord_bot.py`
- Update docs: `12_Agents/executive_assistant.md`, all files in `06_Skills/`

**Phase 2 — Primitives:**
- Modify: `eos_ai/context.py` (add `load_ventures_from_env`, `ventures` field to `EOSContext`)

**Phase 3 — EA gaps:**
- Create: `scripts/day_reminder.py`, `scripts/midday_checkin.py`, `eos_ai/okr_tracker.py`, `eos_ai/event_manager.py`
- Modify: `eos_ai/quality_gate.py`, `eos_ai/meetings.py`, `eos_ai/travel_manager.py`, `eos_ai/stakeholder_map.py`, `eos_ai/doc_creator.py`, `eos_ai/eod_closing_loop.py`, `13_Scripts/discord_bot.py`, `eos_ai/weekly_review.py`
- Add crontab entries

---

## Task 1: Phase 1 — Create renamed Python modules

Create `task_yield_matrix.py`, `founder_rate.py`, and `ideal_week.py` as renamed copies of the originals with all terminology updated.

**Files:**
- Create: `eos_ai/task_yield_matrix.py`
- Create: `eos_ai/founder_rate.py`
- Create: `eos_ai/ideal_week.py`

- [ ] **Step 1: Read originals**

```bash
cat /opt/OS/eos_ai/drip_matrix.py
cat /opt/OS/eos_ai/buyback_rate.py
cat /opt/OS/eos_ai/perfect_week.py
```

- [ ] **Step 2: Create `eos_ai/task_yield_matrix.py`**

Copy `drip_matrix.py` content with these replacements applied (logic unchanged, only identifiers/strings renamed):

| Old | New |
|-----|-----|
| `DRIP Matrix` | `Task Yield Matrix` |
| `classify_task_drip` | `classify_task_yield` |
| `run_drip_audit` | `run_yield_audit` |
| `format_drip_report` | `format_yield_report` |
| `'drip_audit'` | `'yield_audit'` |
| `'dex_drip'` | `'dex_yield'` |
| `DRIP Matrix Audit` | `Task Yield Matrix Audit` |
| `buyback_priority` | `founder_priority` |
| `**🔍 DRIP Matrix Audit:**` | `**🔍 Task Yield Audit:**` |

Also update the LLM prompt line `"buyback_priority": "immediate|soon|later|never"` to `"founder_priority": "immediate|soon|later|never"`.

The function `classify_task_drip` calls itself internally — replace with `classify_task_yield`.
The function `run_drip_audit` calls `classify_task_drip` — replace with `classify_task_yield`.

- [ ] **Step 3: Create `eos_ai/founder_rate.py`**

Copy `buyback_rate.py` content with these replacements:

| Old | New |
|-----|-----|
| `Buyback Rate` | `Founder Rate` |
| `Buyback Loop` | `Leverage Loop` |
| `BBR` | `FR` |
| `calculate_buyback_rate` | `calculate_founder_rate` |
| `store_buyback_rate` | `store_founder_rate` |
| `get_current_buyback_rate` | `get_current_founder_rate` |
| `detect_pain_line` | `detect_delegation_threshold` |
| `'buyback_rate'` (event_type string) | `'founder_rate'` |
| `'dex_buyback'` | `'dex_founder_rate'` |
| `[BuybackRate]` (log prefixes) | `[FounderRate]` |

Keep all other function names unchanged: `log_time_block`, `get_time_audit_summary`, `add_to_no_list`, `get_no_list`, `check_against_no_list`.

The docstring formula line: `Founder Rate = Annual income / 2000 hours / 4` (was Buyback Rate).

`calculate_founder_rate` — the returned dict key `buyback_rate` → `founder_rate`. Also update `interpretation` string.

`store_founder_rate` calls `calculate_founder_rate` — update both.

`detect_delegation_threshold` — update the log prefix `[BuybackRate] detect_pain_line failed` → `[FounderRate] detect_delegation_threshold failed`.

- [ ] **Step 4: Create `eos_ai/ideal_week.py`**

Copy `perfect_week.py` content with these replacements:

| Old | New |
|-----|-----|
| `Perfect Week` | `Ideal Week` |
| `get_perfect_week` | `get_ideal_week` |
| `save_perfect_week` | `save_ideal_week` |
| `'perfect_week'` (event_type) | `'ideal_week'` |
| `'dex_perfect_week'` | `'dex_ideal_week'` |
| `create_camcorder_playbook` | `create_process_capture` |
| `Camcorder Method` | `Process Capture` |
| `camcorder_` (filepath prefix) | `process_capture_` |
| `save_preloaded_year` | `save_annual_architecture` |
| `get_preloaded_year` | `get_annual_architecture` |
| `'preloaded_year'` (event_type) | `'annual_architecture'` |
| `[PerfectWeek]` (log prefixes) | `[IdealWeek]` |

`DEFAULT_PERFECT_WEEK` → `DEFAULT_IDEAL_WEEK` (variable name change).
`get_ideal_week` returns `DEFAULT_IDEAL_WEEK` instead of `DEFAULT_PERFECT_WEEK`.

The `create_process_capture` function: the filepath changes from `camcorder_{safe_name}` to `process_capture_{safe_name}`. The SkillV2 id changes from `camcorder_{safe_name}` to `process_capture_{safe_name}`.

`get_current_quarter_rocks` calls `get_annual_architecture` — update.

- [ ] **Step 5: Verify new files import cleanly**

```bash
cd /opt/OS && python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from eos_ai.task_yield_matrix import classify_task_yield, run_yield_audit, format_yield_report
from eos_ai.founder_rate import calculate_founder_rate, store_founder_rate, get_current_founder_rate, detect_delegation_threshold
from eos_ai.ideal_week import get_ideal_week, save_ideal_week, create_process_capture, save_annual_architecture, get_annual_architecture
print('new modules: clean')
"
```

Expected: `new modules: clean`

- [ ] **Step 6: Commit**

```bash
cd /opt/OS
git add eos_ai/task_yield_matrix.py eos_ai/founder_rate.py eos_ai/ideal_week.py
git commit -m "feat: create renamed terminology modules (task_yield_matrix, founder_rate, ideal_week)"
```

---

## Task 2: Phase 1 — Update martell_patterns.py in-place

**Files:**
- Modify: `eos_ai/martell_patterns.py`

- [ ] **Step 1: Read the file**

```bash
cat /opt/OS/eos_ai/martell_patterns.py
```

- [ ] **Step 2: Apply replacements**

| Old | New |
|-----|-----|
| `TIME_ASSASSIN_SIGNALS` | `LEVERAGE_KILLER_SIGNALS` |
| `detect_time_assassin` | `detect_leverage_killer` |
| `Time Assassin` | `Leverage Killer` |
| `Time Assassins` | `Leverage Killers` |
| `check_131_rule` | `check_solution_standard` |
| `1:3:1 Rule` | `Solution Standard` |
| `1:3:1` | `Solution Standard` (in strings only — in the docstring and intervention strings) |

The dict keys `'staller'`, `'speed_demon'`, etc. stay unchanged.
The module docstring "5 Time Assassins" → "5 Leverage Killers".
The intervention strings `"⚠️ **Time Assassin detected: The Staller**"` → `"⚠️ **Leverage Killer detected: The Staller**"`.
`check_solution_standard` — the docstring and internal variable names `problem_signals`, `option_signals` stay, only function name changes.

- [ ] **Step 3: Verify**

```bash
cd /opt/OS && python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from eos_ai.martell_patterns import LEVERAGE_KILLER_SIGNALS, detect_leverage_killer, check_solution_standard
print('martell_patterns: clean')
"
```

Expected: `martell_patterns: clean`

- [ ] **Step 4: Commit**

```bash
cd /opt/OS
git add eos_ai/martell_patterns.py
git commit -m "refactor: rename martell_patterns terminology (leverage killers, solution standard)"
```

---

## Task 3: Phase 1 — Update all import files (non-discord)

Update every Python file that imports from the renamed modules.

**Files:**
- Modify: `eos_ai/cognitive_loop.py`
- Modify: `eos_ai/daily_sync.py`
- Modify: `eos_ai/weekly_review.py`
- Modify: `eos_ai/week_architect.py`
- Modify: `eos_ai/ea_best_practices.py`
- Modify: `eos_ai/portfolio_advisor.py`
- Modify: `eos_ai/orchestrator.py`
- Modify: `eos_ai/skill_registry_v2.py`
- Modify: `eos_ai/founder_capture.py`

- [ ] **Step 1: Find all occurrences to update**

```bash
grep -rn "from eos_ai.drip_matrix\|from eos_ai.buyback_rate\|from eos_ai.perfect_week\|from eos_ai.martell_patterns import detect_time_assassin\|from eos_ai.martell_patterns import check_131_rule\|detect_time_assassin\|check_131_rule\|classify_task_drip\|run_drip_audit\|format_drip_report\|get_perfect_week\|save_perfect_week\|get_preloaded_year\|save_preloaded_year\|calculate_buyback_rate\|store_buyback_rate\|get_current_buyback_rate\|detect_pain_line\|create_camcorder_playbook" \
  /opt/OS/eos_ai/ --include="*.py" | grep -v "__pycache__\|task_yield_matrix\|founder_rate\|ideal_week"
```

- [ ] **Step 2: Read each affected file and apply replacements**

For each file found, read it then apply these import and call-site replacements:

**Import line replacements:**
```python
# OLD → NEW
from eos_ai.drip_matrix import classify_task_drip  →  from eos_ai.task_yield_matrix import classify_task_yield
from eos_ai.drip_matrix import run_drip_audit  →  from eos_ai.task_yield_matrix import run_yield_audit
from eos_ai.drip_matrix import run_drip_audit, format_drip_report  →  from eos_ai.task_yield_matrix import run_yield_audit, format_yield_report
from eos_ai.buyback_rate import calculate_buyback_rate  →  from eos_ai.founder_rate import calculate_founder_rate
from eos_ai.buyback_rate import calculate_buyback_rate, store_buyback_rate  →  from eos_ai.founder_rate import calculate_founder_rate, store_founder_rate
from eos_ai.buyback_rate import get_current_buyback_rate  →  from eos_ai.founder_rate import get_current_founder_rate
from eos_ai.buyback_rate import check_against_no_list  →  from eos_ai.founder_rate import check_against_no_list
from eos_ai.buyback_rate import detect_pain_line  →  from eos_ai.founder_rate import detect_delegation_threshold
from eos_ai.perfect_week import get_perfect_week  →  from eos_ai.ideal_week import get_ideal_week
from eos_ai.perfect_week import get_current_quarter_rocks  →  from eos_ai.ideal_week import get_current_quarter_rocks
from eos_ai.perfect_week import create_camcorder_playbook  →  from eos_ai.ideal_week import create_process_capture
from eos_ai.perfect_week import get_preloaded_year  →  from eos_ai.ideal_week import get_annual_architecture
from eos_ai.martell_patterns import detect_time_assassin, check_131_rule  →  from eos_ai.martell_patterns import detect_leverage_killer, check_solution_standard
from eos_ai.martell_patterns import detect_time_assassin  →  from eos_ai.martell_patterns import detect_leverage_killer
```

**Call-site replacements (after imports are fixed):**
```python
classify_task_drip(  →  classify_task_yield(
run_drip_audit(  →  run_yield_audit(
format_drip_report(  →  format_yield_report(
calculate_buyback_rate(  →  calculate_founder_rate(
store_buyback_rate(  →  store_founder_rate(
get_current_buyback_rate(  →  get_current_founder_rate(
detect_pain_line(  →  detect_delegation_threshold(
get_perfect_week(  →  get_ideal_week(
save_perfect_week(  →  save_ideal_week(
get_preloaded_year(  →  get_annual_architecture(
save_preloaded_year(  →  save_annual_architecture(
create_camcorder_playbook(  →  create_process_capture(
detect_time_assassin(  →  detect_leverage_killer(
check_131_rule(  →  check_solution_standard(
```

**String references in weekly_review.py:**
- `'DRIP Scan'` or `'DRIP Matrix'` in display strings → `'Task Yield Matrix'`
- `perfect_week` variable name (local variable in week_architect.py) → `ideal_week`
- `Antony's perfect week template:` in LLM prompt strings → `Antony's ideal week template:`

- [ ] **Step 3: Verify all imports resolve**

```bash
cd /opt/OS && python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
import eos_ai.cognitive_loop
import eos_ai.daily_sync
import eos_ai.weekly_review
import eos_ai.week_architect
import eos_ai.ea_best_practices
import eos_ai.portfolio_advisor
import eos_ai.orchestrator
import eos_ai.skill_registry_v2
import eos_ai.founder_capture
print('all imports: clean')
"
```

Expected: `all imports: clean`

- [ ] **Step 4: Delete the old files**

```bash
rm /opt/OS/eos_ai/drip_matrix.py
rm /opt/OS/eos_ai/buyback_rate.py
rm /opt/OS/eos_ai/perfect_week.py
```

- [ ] **Step 5: Re-verify with old files gone**

```bash
cd /opt/OS && python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from eos_ai.task_yield_matrix import classify_task_yield, run_yield_audit, format_yield_report
from eos_ai.founder_rate import calculate_founder_rate, get_current_founder_rate, detect_delegation_threshold
from eos_ai.ideal_week import get_ideal_week, save_annual_architecture, get_annual_architecture
print('terminology rename clean')
"
```

Expected: `terminology rename clean`

- [ ] **Step 6: Commit**

```bash
cd /opt/OS
git add -u
git add eos_ai/cognitive_loop.py eos_ai/daily_sync.py eos_ai/weekly_review.py eos_ai/week_architect.py eos_ai/ea_best_practices.py eos_ai/portfolio_advisor.py eos_ai/orchestrator.py eos_ai/skill_registry_v2.py eos_ai/founder_capture.py
git commit -m "refactor: update all imports for renamed terminology modules"
```

---

## Task 4: Phase 1 — Update discord_bot.py and docs

**Files:**
- Modify: `13_Scripts/discord_bot.py`
- Modify: `12_Agents/executive_assistant.md`
- Modify: all files in `06_Skills/` (grep for affected terms)

- [ ] **Step 1: Read discord_bot.py around relevant sections**

```bash
grep -n "drip_matrix\|buyback_rate\|perfect_week\|martell_patterns\|email_gps\|drip\|buyback\|camcorder\|perfectweek\|DRIP\|Buyback\|Time Assassin\|1:3:1\|Email GPS" \
  /opt/OS/13_Scripts/discord_bot.py | grep -v __pycache__
```

- [ ] **Step 2: Apply import replacements in discord_bot.py**

Apply the same import and call-site replacements from Task 3.

Additionally apply command name renames (only the `name=` parameter in `@bot.command`):
```python
@bot.command(name='drip')       →  @bot.command(name='yield')
@bot.command(name='buyback')    →  @bot.command(name='founderrate')
@bot.command(name='camcorder')  →  @bot.command(name='processcapture')
@bot.command(name='perfectweek') → @bot.command(name='idealweek')
```

Update the docstring/help strings for each renamed command:
```python
# drip → yield command docstring
"""Task Yield Matrix audit. Usage: !yield task1, task2, task3"""

# buyback → founderrate command docstring
"""Set or view Founder Rate. Usage: !founderrate [annual income] or !founderrate"""

# camcorder → processcapture command docstring
"""Create a playbook from how you do a task. Usage: !processcapture [task name] | [describe how you do it]"""

# perfectweek → idealweek command docstring
"""View your ideal week template."""
```

Update in-message string references:
- `!drip` (in usage strings and suggestions) → `!yield`
- `!buyback` → `!founderrate`
- `!camcorder` → `!processcapture`
- `!perfectweek` → `!idealweek`
- `**DRIP Matrix Audit**` → `**Task Yield Audit**`
- `Buyback Rate:` → `Founder Rate:`
- `buyback_rate` in result dict access → `founder_rate` (e.g., `rate["buyback_rate"]` → `rate["founder_rate"]`)

The `!driveaudit` command stays unchanged.

The `preloaded year format:` hint string in the `!year` command → `annual architecture format:`.

In the cognitive_loop.py 1:3:1 rule section:
```python
# cognitive_loop.py already references check_solution_standard after Task 3
# Update the string:
'## 1:3:1 Rule Alert\n'  →  '## Solution Standard Alert\n'
'Apply the 1:3:1 Rule:'  →  'Apply the Solution Standard:'
```

- [ ] **Step 3: Update executive_assistant.md**

```bash
cat /opt/OS/12_Agents/executive_assistant.md
```

Replace terminology strings (not Python, just documentation):
- `DRIP Matrix` → `Task Yield Matrix`
- `Buyback Rate` → `Founder Rate`
- `Buyback Loop` → `Leverage Loop`
- `Time Assassins` → `Leverage Killers`
- `Time Assassin` → `Leverage Killer`
- `Camcorder Method` → `Process Capture`
- `Perfect Week` → `Ideal Week`
- `Preloaded Year` → `Annual Architecture`
- `Pain Line` → `Delegation Threshold`
- `1:3:1 Rule` → `Solution Standard`
- `10-80-10` → `Ownership Split`
- `Replacement Ladder` → `Delegation Ladder`
- `Email GPS` → `Inbox Architecture`

- [ ] **Step 4: Update skill files**

```bash
grep -rn "DRIP Matrix\|Buyback Rate\|Time Assassin\|Camcorder Method\|Perfect Week\|Preloaded Year\|Pain Line\|1:3:1 Rule\|10-80-10\|Replacement Ladder\|Email GPS" \
  /opt/OS/06_Skills/ 2>/dev/null
```

For each file found, apply the same doc-string replacements from Step 3.

- [ ] **Step 5: Verify discord_bot.py imports**

```bash
cd /opt/OS && python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
import ast
with open('/opt/OS/13_Scripts/discord_bot.py') as f:
    src = f.read()
ast.parse(src)
print('discord_bot.py: syntax clean')
"
```

Expected: `discord_bot.py: syntax clean`

- [ ] **Step 6: Full import check**

```bash
cd /opt/OS && python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from eos_ai.task_yield_matrix import classify_task_yield
from eos_ai.founder_rate import calculate_founder_rate
from eos_ai.ideal_week import get_ideal_week
print('terminology rename clean')
"
```

Expected: `terminology rename clean`

- [ ] **Step 7: Commit**

```bash
cd /opt/OS
git add 13_Scripts/discord_bot.py 12_Agents/executive_assistant.md 06_Skills/
git add eos_ai/cognitive_loop.py
git commit -m "refactor: update discord commands and docs to new terminology"
```

---

## Task 5: Phase 2 — Venture registry in context.py

**Files:**
- Modify: `eos_ai/context.py`

- [ ] **Step 1: Read context.py**

```bash
cat /opt/OS/eos_ai/context.py
```

- [ ] **Step 2: Add `ventures` field and `load_ventures_from_env` to context.py**

The current file has `EOSContext` dataclass and `load_context_from_env()`. Add after the existing content:

```python
from dataclasses import dataclass, field
import os
import json
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")


@dataclass
class EOSContext:
    org_id: str
    user_id: str
    portfolio_id: str | None = None
    active_venture_id: str | None = None
    active_agent_id: str | None = None
    ventures: list = field(default_factory=list)


def load_ventures_from_env() -> list[dict]:
    """
    Load venture/company primitives from environment.
    Falls back to empty list if not configured.
    Format: VENTURES_JSON env var containing JSON array.
    """
    raw = os.getenv('VENTURES_JSON', '[]')
    try:
        return json.loads(raw)
    except Exception:
        return []


def load_context_from_env() -> EOSContext:
    return EOSContext(
        org_id=os.environ["EOS_ORG_ID"],
        user_id=os.environ["EOS_USER_ID"],
        portfolio_id=os.environ.get("EOS_PORTFOLIO_ID"),
        ventures=load_ventures_from_env(),
    )
```

Note: `dataclass` is already imported if it exists in the original — check and don't double-import. Add `field` import if missing. Add `json` import if missing.

- [ ] **Step 3: Verify**

```bash
cd /opt/OS && python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from eos_ai.context import load_context_from_env, load_ventures_from_env
ventures = load_ventures_from_env()
ctx = load_context_from_env()
print(f'ventures loaded: {len(ventures)}')
print(f'ctx.ventures: {len(ctx.ventures)}')
print('context: clean')
"
```

Expected:
```
ventures loaded: 0
ctx.ventures: 0
context: clean
```
(0 is correct — VENTURES_JSON not yet set in env)

- [ ] **Step 4: Search for hardcoded venture strings to document**

```bash
grep -rn "lyfe_institute\|empyrean_creative\|personal_brand" \
  /opt/OS/eos_ai/ --include="*.py" | grep -v __pycache__ | head -20
```

Note the occurrences for the next step. **Do not replace them now** — the venture-lookup pattern will be added to the code organically as the system evolves. The `VENTURES_JSON` env var is the abstraction layer.

- [ ] **Step 5: Add VENTURES_JSON to .env.example**

```bash
cat /opt/OS/.env.example 2>/dev/null || echo "not found"
```

Add to `.env.example`:

```bash
# Venture registry — JSON array of venture configs
# Each venture: id, name, stage, channel, offer, icp, north_star,
#               binding_constraint, notion_tasks_db, discord_channel_id
VENTURES_JSON='[
  {
    "id": "lyfe_institute",
    "name": "Lyfe Institute",
    "stage": "pre-revenue",
    "channel": "instagram_dms",
    "offer": "Initiate Arena — $750 90-day program",
    "icp": "Men 18-25",
    "north_star": "$10K MRR",
    "binding_constraint": "First sale",
    "notion_tasks_db": "",
    "discord_channel_id": ""
  },
  {
    "id": "empyrean_creative",
    "name": "Empyrean Creative",
    "stage": "pre-revenue",
    "channel": "outbound",
    "offer": "AI infrastructure B2B",
    "icp": "SMB operators",
    "north_star": "$10K MRR",
    "binding_constraint": "First client",
    "notion_tasks_db": "",
    "discord_channel_id": ""
  },
  {
    "id": "personal_brand",
    "name": "Antony F. Munoz",
    "stage": "building",
    "channel": "content",
    "offer": "Personal brand",
    "icp": "Founders and operators",
    "north_star": "10K followers",
    "binding_constraint": "Consistent content",
    "notion_tasks_db": "",
    "discord_channel_id": ""
  }
]'
```

- [ ] **Step 6: Commit**

```bash
cd /opt/OS
git add eos_ai/context.py .env.example
git commit -m "feat: add venture registry to context (load_ventures_from_env, VENTURES_JSON)"
```

---

## Task 6: Phase 3 Part 1 — Day reminder + mid-day check-in + EOD next-day preview

**Files:**
- Create: `scripts/day_reminder.py`
- Create: `scripts/midday_checkin.py`
- Modify: `eos_ai/eod_closing_loop.py`

- [ ] **Step 1: Create scripts directory if needed**

```bash
mkdir -p /opt/OS/scripts /opt/OS/logs
```

- [ ] **Step 2: Read eod_closing_loop.py**

```bash
cat /opt/OS/eos_ai/eod_closing_loop.py
```

Identify the closing section — the last assembled `sections` list block or final `message` construction — to know where to insert the next-day preview.

- [ ] **Step 3: Create `scripts/day_reminder.py`**

```python
"""
Day Reminder — fires reminders throughout the day.
Runs every 5 minutes via cron.
Checks for events starting in the next 10-15 minutes
and fires a Discord alert if not already sent.
"""

import os
import sys
import asyncio
import discord
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

sys.path.insert(0, '/opt/OS')
load_dotenv('/opt/OS/eos_ai/.env')
load_dotenv('/opt/OS/13_Scripts/.env')

PDT = ZoneInfo('America/Los_Angeles')
STATE_FILE = '/tmp/day_reminder_state.json'
GENERAL_CHANNEL_ID = int(os.getenv('DISCORD_GENERAL_CHANNEL_ID', '0'))


async def check_and_remind():
    from eos_ai.gws_connector import GWSConnector
    from eos_ai.person_recognition import build_intelligence_profile

    gws = GWSConnector()
    now = datetime.now(PDT)

    try:
        with open(STATE_FILE) as f:
            sent = json.load(f)
    except Exception:
        sent = {}

    cutoff = (now - timedelta(hours=24)).isoformat()
    sent = {k: v for k, v in sent.items() if v > cutoff}

    try:
        events = gws.get_upcoming_events(days=1)
    except Exception:
        return

    alerts = []
    for event in events:
        event_id = event.get('id', '')
        if not event_id or event_id in sent:
            continue

        start_raw = event.get('start', '')
        if isinstance(start_raw, dict):
            start_raw = start_raw.get('dateTime', '')
        if not start_raw:
            continue

        try:
            from dateutil.parser import parse as _parse
            event_start = _parse(str(start_raw)).astimezone(PDT)
            minutes_until = (event_start - now).total_seconds() / 60

            if 8 <= minutes_until <= 15:
                title = event.get('title', event.get('summary', 'Meeting'))
                attendees = event.get('attendees', [])
                attendee_email = next(
                    (a.get('email') for a in attendees if not a.get('self')),
                    ''
                )

                person_context = ''
                if attendee_email:
                    try:
                        profile = build_intelligence_profile(email=attendee_email)
                        if profile and getattr(profile, 'notes', ''):
                            person_context = f'\n💡 {profile.notes[:100]}'
                    except Exception:
                        pass

                time_str = event_start.strftime('%-I:%M %p')
                meet_link = event.get('meet_link', '')

                alert = (
                    f'⏰ **{title}** in ~{int(minutes_until)} min ({time_str})'
                    + (f'\n🔗 {meet_link}' if meet_link else '')
                    + person_context
                )
                alerts.append((event_id, alert))
        except Exception:
            continue

    if not alerts:
        return

    intents = discord.Intents.default()
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        channel = client.get_channel(GENERAL_CHANNEL_ID)
        if channel:
            for event_id, alert in alerts:
                await channel.send(alert)
                sent[event_id] = now.isoformat()

        with open(STATE_FILE, 'w') as f:
            json.dump(sent, f)

        await client.close()

    await client.start(os.getenv('DISCORD_BOT_TOKEN'))


if __name__ == '__main__':
    asyncio.run(check_and_remind())
```

- [ ] **Step 4: Create `scripts/midday_checkin.py`**

```python
"""
Mid-day check-in — runs at 12:30pm PDT.
Surfaces afternoon agenda, urgent pending items,
and one afternoon priority.
"""

import os
import sys
import asyncio
import discord
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

sys.path.insert(0, '/opt/OS')
load_dotenv('/opt/OS/eos_ai/.env')
load_dotenv('/opt/OS/13_Scripts/.env')

PDT = ZoneInfo('America/Los_Angeles')
GENERAL_CHANNEL_ID = int(os.getenv('DISCORD_GENERAL_CHANNEL_ID', '0'))


async def midday_checkin():
    from eos_ai.gws_connector import GWSConnector
    from eos_ai.context import load_context_from_env
    from eos_ai.db import get_conn
    from eos_ai.model_router import get_router, TaskType
    import json as _json
    from dateutil.parser import parse as _parse

    ctx = load_context_from_env()
    gws = GWSConnector()
    router = get_router()
    model = router.route(TaskType.FAST_RESPONSE)
    now = datetime.now(PDT)

    try:
        events = gws.get_upcoming_events(days=1)
        afternoon = []
        for e in events:
            start = e.get('start', '')
            if isinstance(start, dict):
                start = start.get('dateTime', '')
            try:
                dt = _parse(str(start)).astimezone(PDT)
                if dt.hour >= 12 and dt.date() == now.date():
                    afternoon.append(
                        f'{dt.strftime("%-I:%M %p")}: '
                        f'{e.get("title", e.get("summary", "Event"))}'
                    )
            except Exception:
                continue
    except Exception:
        afternoon = []

    try:
        with get_conn(ctx.org_id) as cur:
            cur.execute('''
                SELECT payload_json FROM events
                WHERE org_id = %s
                AND event_type IN ('email_draft_pending', 'dex_question')
                AND (payload_json->>'status' = 'pending_approval'
                     OR payload_json->>'answered' IS NULL)
                AND created_at >= NOW() - INTERVAL '24 hours'
                LIMIT 5
            ''', (str(ctx.org_id),))
            pending = cur.fetchall()
    except Exception:
        pending = []

    afternoon_text = '\n'.join(afternoon) if afternoon else 'Clear afternoon'
    pending_text = f'{len(pending)} items pending approval' if pending else 'Nothing pending'

    summary = router.call(model, f"""You are DEX, EA to the founder.
Mid-day check-in. Be brief — 3 sentences max.

Afternoon schedule:
{afternoon_text}

Pending items: {pending_text}

Surface anything urgent. Confirm afternoon is on track.
Suggest one afternoon priority if relevant.""").strip()

    message = (
        f'🌤️ **Mid-day — {now.strftime("%-I:%M %p")}**\n\n'
        f'{summary}'
        + (f'\n\n**Afternoon:**\n' + '\n'.join(f'• {e}' for e in afternoon[:4]) if afternoon else '')
    )

    intents = discord.Intents.default()
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        channel = client.get_channel(GENERAL_CHANNEL_ID)
        if channel:
            await channel.send(message[:1900])
        await client.close()

    await client.start(os.getenv('DISCORD_BOT_TOKEN'))


if __name__ == '__main__':
    asyncio.run(midday_checkin())
```

- [ ] **Step 5: Add next-day preview to eod_closing_loop.py**

Read the file to find the section where `sections` list is assembled (look for the final message construction block near the end of the main function). Add this block just before the final message assembly:

```python
    # Next day preview
    try:
        from eos_ai.gws_connector import GWSConnector
        from datetime import timedelta
        from dateutil.parser import parse as _parse
        gws = GWSConnector()
        tomorrow_str = (datetime.now(PDT) + timedelta(days=1)).strftime('%Y-%m-%d')
        tomorrow_events = []
        for e in gws.get_upcoming_events(days=2):
            start = e.get('start', '')
            if isinstance(start, dict):
                start = start.get('dateTime', '')
            try:
                dt = _parse(str(start)).astimezone(PDT)
                if dt.date().isoformat() == tomorrow_str:
                    tomorrow_events.append(
                        f'• {dt.strftime("%-I:%M %p")} — '
                        f'{e.get("title", e.get("summary", "Event"))}'
                    )
            except Exception:
                pass
        if tomorrow_events:
            sections.append('**📅 Tomorrow:**')
            sections.extend(tomorrow_events[:4])
            sections.append('')
    except Exception:
        pass
```

- [ ] **Step 6: Add crontab entries**

```bash
# View current crontab
crontab -l

# Add the two new entries (edit crontab carefully — don't remove existing entries)
(crontab -l 2>/dev/null; echo "*/5 * * * * cd /opt/OS && python3 scripts/day_reminder.py >> /opt/OS/logs/day_reminder.log 2>&1") | crontab -
(crontab -l 2>/dev/null; echo "30 12 * * * cd /opt/OS && python3 scripts/midday_checkin.py >> /opt/OS/logs/midday.log 2>&1") | crontab -

# Verify
crontab -l | grep -E "day_reminder|midday"
```

- [ ] **Step 7: Verify scripts parse correctly**

```bash
cd /opt/OS && python3 -c "
import ast
for f in ['scripts/day_reminder.py', 'scripts/midday_checkin.py']:
    with open(f) as fh: src = fh.read()
    ast.parse(src)
    print(f'{f}: syntax clean')
"
```

Expected:
```
scripts/day_reminder.py: syntax clean
scripts/midday_checkin.py: syntax clean
```

- [ ] **Step 8: Commit**

```bash
cd /opt/OS
git add scripts/day_reminder.py scripts/midday_checkin.py eos_ai/eod_closing_loop.py
git commit -m "feat: add day reminders, midday check-in, and EOD next-day preview"
```

---

## Task 7: Phase 3 Part 2 — Quality gate

**Files:**
- Modify: `eos_ai/quality_gate.py`
- Modify: `13_Scripts/discord_bot.py`

- [ ] **Step 1: Read quality_gate.py**

```bash
cat /opt/OS/eos_ai/quality_gate.py
```

Note the existing class-based structure. We add module-level functions alongside it.

- [ ] **Step 2: Add `quality_check` and `gate_outgoing_email` to quality_gate.py**

Append to the end of the file (after existing code):

```python

VOICE_STANDARDS = """
Antony Munoz's voice standards:
- Direct and confident. No hedging.
- Warm but not overly casual
- No corporate speak or filler phrases
- Short sentences preferred
- Clear next step always included in outreach
- Never uses: "I hope this email finds you well",
  "Please don't hesitate", "As per my previous email",
  "Circling back", "Touching base", "Quick question"
"""


def quality_check(
    content: str,
    content_type: str = 'email',
    recipient_context: str = '',
) -> dict:
    """
    Run quality check on outgoing communication.

    Returns:
    {
      "approved": bool,
      "score": 0-10,
      "issues": ["list of issues"],
      "suggestions": ["list of suggestions"],
      "revised_version": "improved version if score < 8, else empty string"
    }
    """
    try:
        from eos_ai.model_router import get_router, TaskType
        router = get_router()
        model = router.route(TaskType.FAST_RESPONSE)

        result = router.call(model, f"""You are a quality control editor
for Antony Munoz's outgoing communications.

Voice standards:
{VOICE_STANDARDS}

Content type: {content_type}
Recipient context: {recipient_context or 'Unknown'}

Content to review:
{content}

Check for:
1. Voice consistency with standards above
2. Grammar and spelling errors
3. Clarity — is the message clear?
4. Call to action — is there a clear next step?
5. Tone appropriateness for recipient
6. Prohibited phrases
7. Length appropriateness

Return JSON only:
{{"approved": true/false, "score": 0-10, "issues": ["issue 1"], "suggestions": ["suggestion 1"], "revised_version": "improved version if score < 8, else empty string"}}""").strip()

        if '```' in result:
            result = result.split('```')[1].replace('json', '').strip()
        import json as _j
        return _j.loads(result)
    except Exception as e:
        logger.warning(f'[QualityGate] check failed: {e}')
        return {
            'approved': True,
            'score': 7,
            'issues': [],
            'suggestions': [],
            'revised_version': '',
        }


def gate_outgoing_email(
    subject: str,
    body: str,
    to_email: str = '',
    auto_revise: bool = True,
    ctx=None,
) -> dict:
    """
    Full quality gate for outgoing email.
    If score < 8 and auto_revise=True, returns revised version.
    Logs result to Neon.
    """
    import json as _j
    result = quality_check(
        content=f'Subject: {subject}\n\n{body}',
        content_type='email',
        recipient_context=to_email,
    )

    try:
        from eos_ai.context import load_context_from_env
        from eos_ai.db import get_conn
        ctx = ctx or load_context_from_env()
        with get_conn(ctx.org_id) as cur:
            cur.execute('''
                INSERT INTO events
                (org_id, event_type, payload_json, handled_by)
                VALUES (%s, %s, %s, %s)
            ''', (
                str(ctx.org_id),
                'quality_gate_check',
                _j.dumps({
                    'subject': subject,
                    'to': to_email,
                    'score': result.get('score'),
                    'approved': result.get('approved'),
                    'issues': result.get('issues', []),
                }),
                'quality_gate',
            ))
    except Exception:
        pass

    return result
```

- [ ] **Step 3: Read discord_bot.py around `!approve_followup` handler**

```bash
grep -n "approve_followup\|cmd_approve_followup" /opt/OS/13_Scripts/discord_bot.py | head -10
```

Read lines around that function (±40 lines).

- [ ] **Step 4: Add `!proofread` command to discord_bot.py**

Find the last `@bot.command` block in discord_bot.py and append after it (before the `bot.run()` call):

```python
@bot.command(name='proofread')
async def cmd_proofread(ctx: commands.Context, *, content: str = ''):
    """Proofread outgoing communications. Usage: !proofread [paste your text here]"""
    if not content:
        await ctx.reply(
            'Usage: `!proofread [paste your email or message here]`'
        )
        return
    try:
        from eos_ai.quality_gate import quality_check
        await ctx.reply('🔍 Running quality check...')
        result = quality_check(content)
        score = result.get('score', 0)
        approved = result.get('approved', False)
        issues = result.get('issues', [])
        suggestions = result.get('suggestions', [])
        revised = result.get('revised_version', '')

        emoji = '✅' if approved else '⚠️'
        lines = [f'{emoji} **Quality Score: {score}/10**']
        if issues:
            lines.append('\n**Issues:**')
            for i in issues:
                lines.append(f'• {i}')
        if suggestions:
            lines.append('\n**Suggestions:**')
            for s in suggestions:
                lines.append(f'• {s}')
        if revised:
            lines.append(f'\n**Revised version:**\n```\n{revised[:600]}\n```')

        await ctx.reply('\n'.join(lines)[:1900])
    except Exception as e:
        await ctx.reply(f'❌ Error: {e}')
```

- [ ] **Step 5: Wire quality gate into `cmd_approve_followup`**

Read the `cmd_approve_followup` function. Find where the draft is retrieved and approved. Before the actual send/approval, insert:

```python
        # Quality gate before approval
        try:
            from eos_ai.quality_gate import gate_outgoing_email
            qr = gate_outgoing_email(
                subject='Follow-up',
                body=draft,
                to_email=payload.get('to_email', ''),
            )
            if not qr.get('approved') and qr.get('revised_version'):
                await ctx.reply(
                    f'⚠️ Quality score: {qr["score"]}/10\n'
                    f'Issues: {", ".join(qr["issues"][:2])}\n'
                    f'Auto-revised version ready — sending improved version.'
                )
                draft = qr['revised_version']
        except Exception:
            pass
```

- [ ] **Step 6: Verify**

```bash
cd /opt/OS && python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from eos_ai.quality_gate import quality_check, gate_outgoing_email
print('quality_gate: clean')
import ast
with open('/opt/OS/13_Scripts/discord_bot.py') as f: src = f.read()
ast.parse(src)
print('discord_bot.py: syntax clean')
"
```

Expected: both lines print cleanly.

- [ ] **Step 7: Commit**

```bash
cd /opt/OS
git add eos_ai/quality_gate.py 13_Scripts/discord_bot.py
git commit -m "feat: add quality gate check and proofread command"
```

---

## Task 8: Phase 3 Part 3 — Meeting minutes

**Files:**
- Modify: `eos_ai/meetings.py`
- Modify: `13_Scripts/discord_bot.py`

- [ ] **Step 1: Read meetings.py**

```bash
cat /opt/OS/eos_ai/meetings.py
```

Find: (a) the end of the file to append `draft_meeting_minutes`, (b) `update_meeting_outcome` function to wire auto-draft.

- [ ] **Step 2: Add `draft_meeting_minutes` to meetings.py**

Append to the end of meetings.py:

```python

def draft_meeting_minutes(
    title: str,
    person: str,
    outcomes: str,
    open_loops: str,
    duration_minutes: int = 60,
    attendee_emails: list = None,
    ctx=None,
) -> dict:
    """
    Draft formal meeting minutes and queue for distribution.
    Returns dict with 'minutes' str and 'drive_file' dict.
    """
    import json as _j
    try:
        from eos_ai.model_router import get_router, TaskType
        from eos_ai.gws_connector import GWSConnector
        from eos_ai.context import load_context_from_env
        from eos_ai.db import get_conn
        from datetime import datetime
        from zoneinfo import ZoneInfo
        router = get_router()
        model = router.route(TaskType.FAST_RESPONSE)
        PDT = ZoneInfo('America/Los_Angeles')
        now = datetime.now(PDT)

        minutes = router.call(model, f"""Draft formal meeting minutes.

Meeting: {title}
Attendees: Antony Munoz, {person}
Date: {now.strftime('%B %d, %Y')}
Duration: {duration_minutes} minutes

Outcomes/decisions: {outcomes}
Open loops/action items: {open_loops}

Format:
# Meeting Minutes — {title}
**Date:** {now.strftime('%B %d, %Y')}
**Attendees:** Antony Munoz, {person}
**Duration:** {duration_minutes} min

## Summary
[2 sentence summary]

## Decisions Made
[bullet list of decisions]

## Action Items
[bullet list with owner and timeline]

## Next Steps
[what happens next and when]

Keep it professional and concise.""").strip()

        gws = GWSConnector()
        drive_file = {}
        try:
            drive_file = gws.create_document(
                title=f'Minutes — {title} — {now.strftime("%Y-%m-%d")}',
                content=minutes,
            )
        except Exception:
            pass

        ctx = ctx or load_context_from_env()
        try:
            with get_conn(ctx.org_id) as cur:
                cur.execute('''
                    INSERT INTO events
                    (org_id, event_type, payload_json, handled_by)
                    VALUES (%s, %s, %s, %s)
                ''', (
                    str(ctx.org_id),
                    'meeting_minutes',
                    _j.dumps({
                        'title': title,
                        'person': person,
                        'minutes': minutes,
                        'drive_id': drive_file.get('id', ''),
                        'attendee_emails': attendee_emails or [],
                        'created_at': now.isoformat(),
                    }),
                    'dex_meetings',
                ))
        except Exception:
            pass

        return {
            'minutes': minutes,
            'drive_file': drive_file,
            'attendee_emails': attendee_emails or [],
        }
    except Exception as e:
        logger.warning(f'[Meetings] draft_meeting_minutes failed: {e}')
        return {}
```

- [ ] **Step 3: Wire auto-draft into `update_meeting_outcome`**

Read `update_meeting_outcome` in meetings.py. Find where `status == 'Completed'` is handled and outcomes are captured. After that section, add:

```python
    # Auto-draft meeting minutes after completion
    if status == 'Completed' and outcomes:
        try:
            mins_result = draft_meeting_minutes(
                title=f'Meeting with {person}',
                person=person,
                outcomes=outcomes,
                open_loops=open_loops or '',
                attendee_emails=[email] if email else [],
                ctx=ctx,
            )
            if mins_result.get('minutes'):
                import requests as _req
                import os as _os
                webhook = _os.getenv('DISCORD_BRIEF_WEBHOOK')
                if webhook:
                    _req.post(webhook, json={
                        'content': (
                            f'📋 **Meeting minutes drafted:** {title}\n'
                            f'Saved to Drive. `!approve_followup` to distribute.'
                        )
                    }, timeout=5)
        except Exception as e:
            logger.warning(f'[Meetings] Minutes auto-draft failed: {e}')
```

Note: Check that `person`, `email`, `outcomes`, `open_loops`, and `title` variables are in scope at the insertion point. Adapt variable names to match what `update_meeting_outcome` actually uses.

- [ ] **Step 4: Add `!minutes` command to discord_bot.py**

Append before the `bot.run()` call:

```python
@bot.command(name='minutes')
async def cmd_minutes(ctx: commands.Context, *, args: str = ''):
    """Draft meeting minutes. Usage: !minutes [title] | [person] | [outcomes] | [action items]"""
    if '|' not in args:
        await ctx.reply(
            'Usage: `!minutes [meeting title] | [person] | [outcomes] | [action items]`\n'
            'Example: `!minutes Sales call | John Smith | Agreed on pricing | Send contract by Friday`'
        )
        return
    try:
        from eos_ai.meetings import draft_meeting_minutes
        parts = [p.strip() for p in args.split('|')]
        result = draft_meeting_minutes(
            title=parts[0],
            person=parts[1] if len(parts) > 1 else 'Attendee',
            outcomes=parts[2] if len(parts) > 2 else '',
            open_loops=parts[3] if len(parts) > 3 else '',
        )
        if result.get('minutes'):
            await ctx.reply(
                f'📋 **Minutes drafted:**\n'
                f'```\n{result["minutes"][:800]}\n```\n'
                f'Saved to Drive.'
            )
        else:
            await ctx.reply('❌ Failed to draft minutes.')
    except Exception as e:
        await ctx.reply(f'❌ Error: {e}')
```

- [ ] **Step 5: Verify**

```bash
cd /opt/OS && python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from eos_ai.meetings import draft_meeting_minutes
print('meetings: clean')
import ast
with open('/opt/OS/13_Scripts/discord_bot.py') as f: src = f.read()
ast.parse(src)
print('discord_bot.py: syntax clean')
"
```

- [ ] **Step 6: Commit**

```bash
cd /opt/OS
git add eos_ai/meetings.py 13_Scripts/discord_bot.py
git commit -m "feat: add meeting minutes drafting and !minutes command"
```

---

## Task 9: Phase 3 Part 4 — OKR tracker

**Files:**
- Create: `eos_ai/okr_tracker.py`
- Modify: `13_Scripts/discord_bot.py`
- Modify: `eos_ai/weekly_review.py`

- [ ] **Step 1: Create `eos_ai/okr_tracker.py`**

```python
"""
OKR Tracker — tracks Objectives and Key Results per venture.
Weekly check-in cadence. Stored in Neon events table.
"""

import json
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent / '.env')
logger = logging.getLogger(__name__)
PDT = ZoneInfo('America/Los_Angeles')


def set_okr(
    objective: str,
    key_results: list,
    venture_id: str,
    quarter: str = None,
    ctx=None,
) -> bool:
    """
    Set an OKR for a venture.
    key_results: [{"kr": str, "target": float, "unit": str, "current": float}]
    """
    try:
        from eos_ai.context import load_context_from_env
        from eos_ai.db import get_conn
        ctx = ctx or load_context_from_env()
        now = datetime.now(PDT)
        if not quarter:
            month = now.month
            quarter = f'Q{(month - 1) // 3 + 1} {now.year}'

        with get_conn(ctx.org_id) as cur:
            cur.execute('''
                INSERT INTO events
                (org_id, event_type, payload_json, handled_by)
                VALUES (%s, %s, %s, %s)
            ''', (
                str(ctx.org_id),
                'okr',
                json.dumps({
                    'objective': objective,
                    'key_results': key_results,
                    'venture_id': venture_id,
                    'quarter': quarter,
                    'created_at': now.isoformat(),
                }),
                'dex_okr',
            ))
        return True
    except Exception as e:
        logger.warning(f'[OKR] set_okr failed: {e}')
        return False


def get_okrs(venture_id: str = None, ctx=None) -> list:
    """Get current quarter OKRs, optionally filtered by venture."""
    try:
        from eos_ai.context import load_context_from_env
        from eos_ai.db import get_conn
        ctx = ctx or load_context_from_env()
        now = datetime.now(PDT)
        current_quarter = f'Q{(now.month - 1) // 3 + 1} {now.year}'

        with get_conn(ctx.org_id) as cur:
            cur.execute('''
                SELECT id, payload_json FROM events
                WHERE org_id = %s
                AND event_type = 'okr'
                AND payload_json->>'quarter' = %s
                ORDER BY created_at DESC
            ''', (str(ctx.org_id), current_quarter))
            rows = cur.fetchall()

        results = []
        for r in rows:
            payload = r['payload_json']
            if isinstance(payload, str):
                payload = json.loads(payload)
            if venture_id and payload.get('venture_id') != venture_id:
                continue
            payload['event_id'] = str(r['id'])
            results.append(payload)
        return results
    except Exception as e:
        logger.warning(f'[OKR] get_okrs failed: {e}')
        return []


def generate_okr_report(ctx=None) -> str:
    """Generate OKR progress report for all ventures."""
    okrs = get_okrs(ctx=ctx)
    if not okrs:
        return 'No OKRs set for this quarter. Use `!okr set` to add objectives.'

    now = datetime.now(PDT)
    quarter = f'Q{(now.month - 1) // 3 + 1}'
    lines = [f'**🎯 OKR Report — {quarter}:**']
    for okr in okrs:
        venture = okr.get('venture_id', 'Unknown')
        objective = okr.get('objective', '')
        lines.append(f'\n**{venture} — {objective}**')
        for kr in okr.get('key_results', []):
            target = float(kr.get('target', 0))
            current = float(kr.get('current', 0))
            unit = kr.get('unit', '')
            pct = (current / target * 100) if target > 0 else 0
            bar = '█' * int(pct / 10) + '░' * (10 - int(pct / 10))
            lines.append(
                f'• {kr["kr"]}\n'
                f'  [{bar}] {pct:.0f}% ({unit}{current:.0f} / {unit}{target:.0f})'
            )
    return '\n'.join(lines)
```

- [ ] **Step 2: Add OKR commands to discord_bot.py**

Append before `bot.run()`:

```python
@bot.command(name='okr')
async def cmd_okr(ctx: commands.Context, subcommand: str = 'report', *, args: str = ''):
    """OKR tracking. Usage: !okr report | !okr set [venture] | [objective] | [KR description, target, unit]"""
    if subcommand == 'report':
        try:
            from eos_ai.okr_tracker import generate_okr_report
            report = generate_okr_report()
            await ctx.reply(report[:1900])
        except Exception as e:
            await ctx.reply(f'❌ Error: {e}')

    elif subcommand == 'set':
        if '|' not in args:
            await ctx.reply(
                'Usage: `!okr set [venture_id] | [objective] | [KR description], [target], [unit]`\n'
                'Example: `!okr set lyfe_institute | Hit first sale | Revenue, 750, $`'
            )
            return
        try:
            from eos_ai.okr_tracker import set_okr
            parts = [p.strip() for p in args.split('|')]
            venture_id = parts[0]
            objective = parts[1] if len(parts) > 1 else ''
            key_results = []
            for kr_str in parts[2:]:
                kr_parts = [p.strip() for p in kr_str.split(',')]
                if kr_parts:
                    key_results.append({
                        'kr': kr_parts[0],
                        'target': float(kr_parts[1]) if len(kr_parts) > 1 else 100,
                        'unit': kr_parts[2] if len(kr_parts) > 2 else '',
                        'current': 0,
                    })
            ok = set_okr(objective=objective, key_results=key_results, venture_id=venture_id)
            if ok:
                await ctx.reply(
                    f'🎯 **OKR set for {venture_id}:**\n'
                    f'Objective: {objective}\n'
                    f'{len(key_results)} key result(s) added.'
                )
            else:
                await ctx.reply('❌ Failed to set OKR.')
        except Exception as e:
            await ctx.reply(f'❌ Error: {e}')
    else:
        await ctx.reply('Usage: `!okr report` or `!okr set [venture] | [objective] | [KRs...]`')
```

- [ ] **Step 3: Wire OKR report into weekly_review.py**

Read `weekly_review.py`. Find the section where `sections` list is assembled (look for portfolio health or similar blocks). Add after it:

```python
        # OKR progress
        try:
            from eos_ai.okr_tracker import generate_okr_report
            okr_report = generate_okr_report(ctx)
            if 'No OKRs' not in okr_report:
                sections.append(okr_report)
                sections.append('')
        except Exception:
            pass
```

- [ ] **Step 4: Verify**

```bash
cd /opt/OS && python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from eos_ai.okr_tracker import set_okr, get_okrs, generate_okr_report
print('okr_tracker: clean')
import ast
with open('/opt/OS/13_Scripts/discord_bot.py') as f: src = f.read()
ast.parse(src)
print('discord_bot.py: syntax clean')
"
```

- [ ] **Step 5: Commit**

```bash
cd /opt/OS
git add eos_ai/okr_tracker.py 13_Scripts/discord_bot.py eos_ai/weekly_review.py
git commit -m "feat: add OKR tracker, !okr command, and weekly OKR report"
```

---

## Task 10: Phase 3 Part 5 — Event manager

**Files:**
- Create: `eos_ai/event_manager.py`
- Modify: `13_Scripts/discord_bot.py`

- [ ] **Step 1: Create `eos_ai/event_manager.py`**

```python
"""
Event Manager — coordinates conferences, offsites, client dinners,
team events, and speaking engagements. Distinct from calendar events —
these are multi-day or multi-stakeholder events requiring logistics.
"""

import json
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / '.env')
logger = logging.getLogger(__name__)
PDT = ZoneInfo('America/Los_Angeles')


def create_event(
    name: str,
    event_type: str,
    date: str,
    location: str = '',
    attendees: list = None,
    budget: float = 0,
    notes: str = '',
    ctx=None,
) -> dict:
    """
    Create an event record with AI-generated logistics checklist.
    event_type: conference|offsite|client_dinner|team_event|speaking|podcast|media
    """
    try:
        from eos_ai.context import load_context_from_env
        from eos_ai.db import get_conn
        from eos_ai.model_router import get_router, TaskType
        ctx = ctx or load_context_from_env()
        router = get_router()
        model = router.route(TaskType.FAST_RESPONSE)

        checklist_raw = router.call(model, f"""Generate a logistics checklist for this event.

Event: {name}
Type: {event_type}
Date: {date}
Location: {location or 'TBD'}
Attendees: {len(attendees or [])}
Budget: ${budget:,.0f}

Return JSON only:
{{"checklist": [{{"item": "task description", "owner": "DEX or Founder", "due": "X days before", "done": false}}]}}""").strip()

        if '```' in checklist_raw:
            checklist_raw = checklist_raw.split('```')[1].replace('json', '').strip()
        checklist_data = json.loads(checklist_raw).get('checklist', [])

        event = {
            'name': name,
            'type': event_type,
            'date': date,
            'location': location,
            'attendees': attendees or [],
            'budget': budget,
            'notes': notes,
            'checklist': checklist_data,
            'status': 'planning',
            'created_at': datetime.now(PDT).isoformat(),
        }

        with get_conn(ctx.org_id) as cur:
            cur.execute('''
                INSERT INTO events
                (org_id, event_type, payload_json, handled_by)
                VALUES (%s, %s, %s, %s)
            ''', (
                str(ctx.org_id),
                'managed_event',
                json.dumps(event),
                'dex_events',
            ))

        return event
    except Exception as e:
        logger.warning(f'[EventManager] create_event failed: {e}')
        return {}


def get_events(upcoming_only: bool = True, ctx=None) -> list:
    """Get managed events, ordered by date ascending."""
    try:
        from eos_ai.context import load_context_from_env
        from eos_ai.db import get_conn
        ctx = ctx or load_context_from_env()

        with get_conn(ctx.org_id) as cur:
            cur.execute('''
                SELECT id, payload_json FROM events
                WHERE org_id = %s
                AND event_type = 'managed_event'
                ORDER BY (payload_json->>'date') ASC
                LIMIT 20
            ''', (str(ctx.org_id),))
            rows = cur.fetchall()

        results = []
        now_str = datetime.now(PDT).strftime('%Y-%m-%d')
        for r in rows:
            payload = r['payload_json']
            if isinstance(payload, str):
                payload = json.loads(payload)
            if upcoming_only and payload.get('date', '') < now_str:
                continue
            payload['event_id'] = str(r['id'])
            results.append(payload)
        return results
    except Exception as e:
        logger.warning(f'[EventManager] get_events failed: {e}')
        return []


def log_speaking_engagement(
    event_name: str,
    organizer: str,
    organizer_email: str,
    date: str,
    topic: str = '',
    format: str = 'talk',
    status: str = 'inquired',
    ctx=None,
) -> bool:
    """
    Log a speaking engagement or podcast appearance.
    format: talk|panel|podcast|interview|workshop|webinar
    status: inquired|confirmed|preparing|completed|declined
    """
    try:
        from eos_ai.context import load_context_from_env
        from eos_ai.db import get_conn
        ctx = ctx or load_context_from_env()

        with get_conn(ctx.org_id) as cur:
            cur.execute('''
                INSERT INTO events
                (org_id, event_type, payload_json, handled_by)
                VALUES (%s, %s, %s, %s)
            ''', (
                str(ctx.org_id),
                'speaking_engagement',
                json.dumps({
                    'event_name': event_name,
                    'organizer': organizer,
                    'organizer_email': organizer_email,
                    'date': date,
                    'topic': topic,
                    'format': format,
                    'status': status,
                    'logged_at': datetime.now(PDT).isoformat(),
                }),
                'dex_speaking',
            ))
        return True
    except Exception as e:
        logger.warning(f'[EventManager] log_speaking failed: {e}')
        return False


def draft_talking_points(
    topic: str,
    audience: str,
    duration_minutes: int = 30,
    format: str = 'talk',
    ctx=None,
) -> str:
    """Draft talking points for a speaking engagement."""
    try:
        from eos_ai.context import load_context_from_env
        from eos_ai.model_router import get_router, TaskType
        ctx = ctx or load_context_from_env()
        router = get_router()
        model = router.route(TaskType.ANALYSIS)

        ventures = getattr(ctx, 'ventures', [])
        venture_context = '\n'.join(
            f'- {v.get("name")}: {v.get("offer", "")}' for v in ventures
        ) if ventures else 'Entrepreneur and founder'

        return router.call(model, f"""Draft talking points for a speaking engagement.

Speaker: Antony Munoz
Ventures: {venture_context}
Topic: {topic}
Audience: {audience}
Format: {format}
Duration: {duration_minutes} minutes

Create:
# Talking Points: {topic}

## Opening hook
[Strong opening — story, statistic, or provocative question]

## Core message
[The one thing the audience should remember]

## Key points (3-5)
[Each with supporting evidence or story]

## Stories to tell
[2-3 personal stories that illustrate the points]

## Audience takeaways
[3 specific things they can do immediately]

## Closing
[Memorable close + call to action]

## Q&A prep
[5 likely questions with strong answers]

Antony's brand: tactical luxury, Vigilante Architect, cinematic and structured tone.""").strip()
    except Exception as e:
        return f'Talking points unavailable: {e}'


def log_pr_media_inquiry(
    outlet: str,
    contact_name: str,
    contact_email: str,
    topic: str,
    deadline: str = '',
    inquiry_type: str = 'interview',
    ctx=None,
) -> bool:
    """
    Log a PR or media inquiry.
    inquiry_type: interview|quote|feature|podcast|press_release
    """
    try:
        from eos_ai.context import load_context_from_env
        from eos_ai.db import get_conn
        ctx = ctx or load_context_from_env()

        with get_conn(ctx.org_id) as cur:
            cur.execute('''
                INSERT INTO events
                (org_id, event_type, payload_json, handled_by)
                VALUES (%s, %s, %s, %s)
            ''', (
                str(ctx.org_id),
                'pr_media_inquiry',
                json.dumps({
                    'outlet': outlet,
                    'contact_name': contact_name,
                    'contact_email': contact_email,
                    'topic': topic,
                    'deadline': deadline,
                    'type': inquiry_type,
                    'status': 'received',
                    'logged_at': datetime.now(PDT).isoformat(),
                }),
                'dex_pr',
            ))
        return True
    except Exception as e:
        logger.warning(f'[EventManager] log_pr failed: {e}')
        return False
```

- [ ] **Step 2: Add event commands to discord_bot.py**

Append before `bot.run()`:

```python
@bot.command(name='event')
async def cmd_event(ctx: commands.Context, *, args: str = ''):
    """Manage events. Usage: !event list | !event [name] | [type] | [date] | [location] | [budget]"""
    if not args or args.strip() == 'list':
        try:
            from eos_ai.event_manager import get_events
            events = get_events()
            if not events:
                await ctx.reply(
                    '📅 No upcoming events.\n'
                    'Create: `!event [name] | [type] | [date] | [location] | [budget]`\n'
                    'Types: conference, offsite, client_dinner, team_event, speaking, podcast'
                )
                return
            lines = [f'📅 **Upcoming events ({len(events)}):**']
            for e in events[:6]:
                lines.append(
                    f'• {e["name"]} — {e["type"]} — '
                    f'{e["date"]} — {e.get("location", "TBD")}'
                )
                incomplete = sum(1 for c in e.get('checklist', []) if not c.get('done'))
                if incomplete:
                    lines.append(f'  ⚠️ {incomplete} checklist items open')
            await ctx.reply('\n'.join(lines))
        except Exception as e:
            await ctx.reply(f'❌ Error: {e}')
        return

    if '|' in args:
        parts = [p.strip() for p in args.split('|')]
        try:
            from eos_ai.event_manager import create_event
            budget = 0.0
            if len(parts) > 4:
                try:
                    budget = float(parts[4].replace('$', '').replace(',', ''))
                except ValueError:
                    budget = 0.0
            event = create_event(
                name=parts[0],
                event_type=parts[1] if len(parts) > 1 else 'other',
                date=parts[2] if len(parts) > 2 else '',
                location=parts[3] if len(parts) > 3 else '',
                budget=budget,
            )
            if event.get('name'):
                checklist_count = len(event.get('checklist', []))
                await ctx.reply(
                    f'📅 **Event created: {event["name"]}**\n'
                    f'Type: {event["type"]} | Date: {event["date"]}\n'
                    f'✅ {checklist_count} checklist items generated'
                )
            else:
                await ctx.reply('❌ Failed to create event.')
        except Exception as e:
            await ctx.reply(f'❌ Error: {e}')
    else:
        await ctx.reply(
            'Usage:\n'
            '`!event list` — view upcoming events\n'
            '`!event [name] | [type] | [date] | [location] | [budget]` — create event'
        )


@bot.command(name='talkingpoints')
async def cmd_talkingpoints(ctx: commands.Context, *, args: str = ''):
    """Draft talking points. Usage: !talkingpoints [topic] | [audience] | [duration min] | [format]"""
    parts = [p.strip() for p in args.split('|')]
    if len(parts) < 2:
        await ctx.reply(
            'Usage: `!talkingpoints [topic] | [audience] | [duration min] | [format]`\n'
            'Formats: talk, panel, podcast, interview, workshop, webinar'
        )
        return
    try:
        from eos_ai.event_manager import draft_talking_points
        await ctx.reply('📝 Drafting talking points...')
        topic = parts[0]
        audience = parts[1]
        duration = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 30
        fmt = parts[3] if len(parts) > 3 else 'talk'
        points = draft_talking_points(topic, audience, duration, fmt)
        for i in range(0, len(points), 1900):
            await ctx.reply(points[i:i + 1900])
    except Exception as e:
        await ctx.reply(f'❌ Error: {e}')


@bot.command(name='pr')
async def cmd_pr(ctx: commands.Context, *, args: str = ''):
    """Log PR inquiry. Usage: !pr [outlet] | [contact] | [email] | [topic] | [deadline]"""
    if '|' not in args:
        await ctx.reply(
            'Usage: `!pr [outlet] | [contact name] | [email] | [topic] | [deadline]`\n'
            'Example: `!pr TechCrunch | Jane Smith | jane@tc.com | AI in business | March 15`'
        )
        return
    try:
        from eos_ai.event_manager import log_pr_media_inquiry
        parts = [p.strip() for p in args.split('|')]
        ok = log_pr_media_inquiry(
            outlet=parts[0],
            contact_name=parts[1] if len(parts) > 1 else '',
            contact_email=parts[2] if len(parts) > 2 else '',
            topic=parts[3] if len(parts) > 3 else '',
            deadline=parts[4] if len(parts) > 4 else '',
        )
        if ok:
            await ctx.reply(
                f'📰 PR inquiry logged: {parts[0]}\n'
                f'Contact: {parts[1] if len(parts) > 1 else "Unknown"}'
            )
        else:
            await ctx.reply('❌ Failed to log PR inquiry.')
    except Exception as e:
        await ctx.reply(f'❌ Error: {e}')
```

- [ ] **Step 3: Verify**

```bash
cd /opt/OS && python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from eos_ai.event_manager import create_event, get_events, log_speaking_engagement, draft_talking_points, log_pr_media_inquiry
print('event_manager: clean')
import ast
with open('/opt/OS/13_Scripts/discord_bot.py') as f: src = f.read()
ast.parse(src)
print('discord_bot.py: syntax clean')
"
```

- [ ] **Step 4: Commit**

```bash
cd /opt/OS
git add eos_ai/event_manager.py 13_Scripts/discord_bot.py
git commit -m "feat: add event manager, speaking/PR logging, !event !talkingpoints !pr commands"
```

---

## Task 11: Phase 3 Parts 7 — Board + investor workflows

**Files:**
- Modify: `eos_ai/stakeholder_map.py`
- Modify: `13_Scripts/discord_bot.py`
- Modify: `eos_ai/weekly_review.py` (or `eos_ai/relationship_nurture.py` if it exists)

- [ ] **Step 1: Read stakeholder_map.py**

```bash
cat /opt/OS/eos_ai/stakeholder_map.py
```

Note existing `add_stakeholder`, `get_stakeholders`, `generate_stakeholder_brief` signatures.

- [ ] **Step 2: Add board member functions to stakeholder_map.py**

Append to end of file:

```python

def add_board_member(
    name: str,
    email: str,
    venture_id: str,
    role: str = 'advisor',
    notes: str = '',
    ctx=None,
) -> bool:
    """Add a board member or advisor via add_stakeholder."""
    return add_stakeholder(
        name=name,
        venture=venture_id,
        role=role,
        influence='high',
        status='active',
        notes=notes,
        email=email,
        ctx=ctx,
    )


def get_board_members(venture_id: str = None, ctx=None) -> list:
    """Get all board members and advisors (high-influence stakeholders)."""
    stakeholders = get_stakeholders(venture=venture_id, ctx=ctx)
    return [
        s for s in stakeholders
        if s.get('role', '').lower() in
        ('advisor', 'board member', 'investor', 'mentor')
        or s.get('influence') == 'high'
    ]


def generate_board_update_brief(venture_id: str, ctx=None) -> str:
    """Generate a concise board/advisor update for a venture."""
    import json as _j
    try:
        from eos_ai.context import load_context_from_env
        from eos_ai.db import get_conn
        from eos_ai.model_router import get_router, TaskType
        ctx = ctx or load_context_from_env()
        router = get_router()
        model = router.route(TaskType.ANALYSIS)

        ventures = getattr(ctx, 'ventures', [])
        venture = next(
            (v for v in ventures if v['id'] == venture_id),
            {'name': venture_id}
        )

        with get_conn(ctx.org_id) as cur:
            cur.execute('''
                SELECT payload_json FROM events
                WHERE org_id = %s
                AND event_type IN ('decision', 'pipeline_entry',
                    'meeting_scheduled', 'revenue')
                AND created_at >= NOW() - INTERVAL '30 days'
                ORDER BY created_at DESC
                LIMIT 15
            ''', (str(ctx.org_id),))
            rows = cur.fetchall()

        activity = []
        for r in rows:
            p = r['payload_json']
            if isinstance(p, str):
                p = _j.loads(p)
            activity.append(str(p)[:100])

        return router.call(model, f"""Draft a board/advisor update
for {venture.get('name', venture_id)}.

Venture context:
- Stage: {venture.get('stage', 'unknown')}
- Offer: {venture.get('offer', 'unknown')}
- North star: {venture.get('north_star', 'unknown')}
- Binding constraint: {venture.get('binding_constraint', 'unknown')}

Recent activity (last 30 days):
{chr(10).join(activity[:10])}

Format as a concise board update under 200 words:
- Headline (one sentence on current state)
- Progress this month
- Key challenges
- What we need from advisors/board
- Next 30 days focus

Direct, no fluff.""").strip()
    except Exception as e:
        return f'Board brief unavailable: {e}'
```

- [ ] **Step 3: Check if relationship_nurture.py exists**

```bash
ls /opt/OS/eos_ai/relationship_nurture.py 2>/dev/null || echo "not found"
```

If it exists, read it and add the board contact staleness check. If not, add to weekly_review.py.

Add to whichever file handles the relationship nurture cadence (look for the section that checks contacts):

```python
    # Board/advisor contact check
    try:
        from eos_ai.stakeholder_map import get_board_members
        board = get_board_members()
        cold_board = []
        for b in board:
            try:
                from eos_ai.person_recognition import score_relationship_health
                health = score_relationship_health(
                    name=b.get('name', ''),
                    email=b.get('email', ''),
                )
                if health.get('days_since_contact', 0) > 30:
                    cold_board.append({
                        **b,
                        'days_since': health.get('days_since_contact', '?')
                    })
            except Exception:
                pass
        if cold_board:
            lines.append('\n⚠️ **Board/advisors needing contact:**')
            for b in cold_board[:3]:
                lines.append(
                    f'• {b["name"]} — {b["days_since"]}d since last contact'
                )
    except Exception:
        pass
```

- [ ] **Step 4: Add board_update command to discord_bot.py**

Append before `bot.run()`:

```python
@bot.command(name='board_update')
async def cmd_board_update(ctx: commands.Context, venture_id: str = ''):
    """Generate board update brief. Usage: !board_update [venture_id]"""
    if not venture_id:
        await ctx.reply(
            'Usage: `!board_update [venture_id]`\n'
            'Example: `!board_update lyfe_institute`'
        )
        return
    try:
        from eos_ai.stakeholder_map import generate_board_update_brief
        await ctx.reply('📋 Generating board update...')
        brief = generate_board_update_brief(venture_id)
        await ctx.reply(f'📋 **Board Update — {venture_id}:**\n{brief[:1900]}')
    except Exception as e:
        await ctx.reply(f'❌ Error: {e}')
```

- [ ] **Step 5: Verify**

```bash
cd /opt/OS && python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from eos_ai.stakeholder_map import add_board_member, get_board_members, generate_board_update_brief
print('stakeholder_map: clean')
import ast
with open('/opt/OS/13_Scripts/discord_bot.py') as f: src = f.read()
ast.parse(src)
print('discord_bot.py: syntax clean')
"
```

- [ ] **Step 6: Commit**

```bash
cd /opt/OS
git add eos_ai/stakeholder_map.py 13_Scripts/discord_bot.py eos_ai/weekly_review.py
git commit -m "feat: add board member tracking, board update brief, !board_update command"
```

---

## Task 12: Phase 3 Part 8 — Announcements and memos

**Files:**
- Modify: `eos_ai/doc_creator.py`
- Modify: `13_Scripts/discord_bot.py`

- [ ] **Step 1: Read doc_creator.py**

```bash
cat /opt/OS/eos_ai/doc_creator.py
```

Note existing functions (`create_briefing_doc`, `create_presentation_outline`, `fact_check`) to avoid conflicts.

- [ ] **Step 2: Add `draft_announcement` and `draft_crisis_communication` to doc_creator.py**

Append to end of file:

```python

def draft_announcement(
    topic: str,
    audience: str,
    key_message: str,
    context: str = '',
    announcement_type: str = 'internal',
    ctx=None,
) -> str:
    """
    Draft an announcement or memo.
    announcement_type: internal|team|public|press_release
    """
    try:
        from eos_ai.model_router import get_router, TaskType
        router = get_router()
        model = router.route(TaskType.FAST_RESPONSE)

        templates = {
            'internal': 'internal team announcement',
            'team': 'team memo',
            'public': 'public announcement',
            'press_release': 'press release',
        }

        return router.call(model, f"""Draft a {templates.get(announcement_type, 'announcement')}.

Topic: {topic}
Audience: {audience}
Key message: {key_message}
Context: {context}
Author: Antony Munoz

Voice: direct, warm, clear. No corporate speak.
Include: what's happening, why it matters, what people need to do or know.
Keep it concise and actionable. Format appropriately for the type.""").strip()
    except Exception as e:
        logger.warning(f'[DocCreator] draft_announcement failed: {e}')
        return f'Announcement draft unavailable: {e}'


def draft_crisis_communication(
    situation: str,
    affected_parties: str,
    what_happened: str,
    what_we_are_doing: str,
    ctx=None,
) -> str:
    """Draft crisis communication following acknowledge-factual-action structure."""
    try:
        from eos_ai.model_router import get_router, TaskType
        router = get_router()
        model = router.route(TaskType.FAST_RESPONSE)

        return router.call(model, f"""Draft a crisis communication.

Situation: {situation}
Affected parties: {affected_parties}
What happened: {what_happened}
What we are doing: {what_we_are_doing}

Guidelines:
1. Acknowledge first — no deflection
2. Be factual — no speculation
3. State what you know and what you don't know
4. State concrete next steps with timeline
5. Provide contact for questions
6. Antony's voice — direct, accountable, calm

Format:
Subject: [clear subject line]

[Body — structured, under 200 words]

[Antony Munoz]""").strip()
    except Exception as e:
        logger.warning(f'[DocCreator] draft_crisis_communication failed: {e}')
        return f'Crisis communication unavailable: {e}'
```

- [ ] **Step 3: Check that logger is defined in doc_creator.py**

```bash
grep -n "^logger\|^import logging" /opt/OS/eos_ai/doc_creator.py | head -5
```

If `logger` is not defined, add at the top of the appended section:

```python
import logging as _logging
_doc_logger = _logging.getLogger(__name__)
```

And replace `logger.warning` in the new functions with `_doc_logger.warning`. Alternatively, if `logger` is already defined at module level, use it as-is.

- [ ] **Step 4: Add !announce and !crisis commands to discord_bot.py**

Append before `bot.run()`:

```python
@bot.command(name='announce')
async def cmd_announce(ctx: commands.Context, *, args: str = ''):
    """Draft announcement. Usage: !announce [topic] | [audience] | [key message] | [type: internal/public/press]"""
    parts = [p.strip() for p in args.split('|')]
    if len(parts) < 3:
        await ctx.reply(
            'Usage: `!announce [topic] | [audience] | [key message] | [type]`\n'
            'Types: internal, team, public, press_release\n'
            'Example: `!announce New program launch | Existing clients | Game of Lyfe is live | public`'
        )
        return
    try:
        from eos_ai.doc_creator import draft_announcement
        draft = draft_announcement(
            topic=parts[0],
            audience=parts[1],
            key_message=parts[2],
            announcement_type=parts[3] if len(parts) > 3 else 'internal',
        )
        await ctx.reply(
            f'📢 **Announcement draft:**\n```\n{draft[:1500]}\n```'
        )
    except Exception as e:
        await ctx.reply(f'❌ Error: {e}')


@bot.command(name='crisis')
async def cmd_crisis(ctx: commands.Context, *, args: str = ''):
    """Draft crisis communication. Usage: !crisis [situation] | [affected parties] | [what happened] | [what we are doing]"""
    parts = [p.strip() for p in args.split('|')]
    if len(parts) < 3:
        await ctx.reply(
            'Usage: `!crisis [situation] | [affected parties] | [what happened] | [what we are doing]`'
        )
        return
    try:
        from eos_ai.doc_creator import draft_crisis_communication
        draft = draft_crisis_communication(
            situation=parts[0],
            affected_parties=parts[1] if len(parts) > 1 else 'Stakeholders',
            what_happened=parts[2] if len(parts) > 2 else '',
            what_we_are_doing=parts[3] if len(parts) > 3 else '',
        )
        await ctx.reply(
            f'🚨 **Crisis communication draft:**\n```\n{draft[:1500]}\n```'
        )
    except Exception as e:
        await ctx.reply(f'❌ Error: {e}')
```

- [ ] **Step 5: Verify**

```bash
cd /opt/OS && python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from eos_ai.doc_creator import draft_announcement, draft_crisis_communication
print('doc_creator: clean')
import ast
with open('/opt/OS/13_Scripts/discord_bot.py') as f: src = f.read()
ast.parse(src)
print('discord_bot.py: syntax clean')
"
```

- [ ] **Step 6: Commit**

```bash
cd /opt/OS
git add eos_ai/doc_creator.py 13_Scripts/discord_bot.py
git commit -m "feat: add announcement and crisis communication drafting, !announce !crisis commands"
```

---

## Task 13: Phase 3 Part 9 — Travel completeness

**Files:**
- Modify: `eos_ai/travel_manager.py`
- Modify: `13_Scripts/discord_bot.py`

- [ ] **Step 1: Read travel_manager.py**

```bash
cat /opt/OS/eos_ai/travel_manager.py
```

Note existing functions (`detect_travel_event`, `build_travel_brief`, `log_trip`, `research_flights`, `research_hotels`, `research_restaurants`).

- [ ] **Step 2: Add three functions to travel_manager.py**

Append to end of file:

```python

def generate_trip_itinerary(
    trip_name: str,
    destination: str,
    start_date: str,
    end_date: str,
    meetings: list = None,
    hotel: str = '',
    ctx=None,
) -> str:
    """Generate a day-by-day trip itinerary document and save to Drive."""
    try:
        from eos_ai.model_router import get_router, TaskType
        from eos_ai.gws_connector import GWSConnector
        router = get_router()
        model = router.route(TaskType.ANALYSIS)

        meetings_text = '\n'.join(f'- {m}' for m in (meetings or [])) if meetings else 'No meetings confirmed yet'

        itinerary = router.call(model, f"""Generate a detailed trip itinerary.

Trip: {trip_name}
Destination: {destination}
Dates: {start_date} to {end_date}
Hotel/Base: {hotel or 'TBD'}
Confirmed meetings:
{meetings_text}

Create:
# Trip Itinerary: {trip_name}

## Overview
[destination, dates, purpose]

## Pre-departure checklist
- [ ] Confirm flights
- [ ] Confirm hotel
- [ ] Pack essentials
- [ ] Download offline maps

## Day-by-day schedule
[For each day from {start_date} to {end_date}: morning / afternoon / evening with times]

## Logistics
- Ground transport options
- Key addresses and contacts
- Local timezone vs home timezone (PDT)

## Meeting prep notes
[For each confirmed meeting]

## Post-trip
- [ ] File expense receipts
- [ ] Send follow-up emails
- [ ] Update CRM records

Keep it practical and specific.""").strip()

        gws = GWSConnector()
        try:
            gws.create_document(
                title=f'Itinerary — {trip_name} — {start_date}',
                content=itinerary,
            )
        except Exception:
            pass

        return itinerary
    except Exception as e:
        logger.warning(f'[Travel] generate_trip_itinerary failed: {e}')
        return f'Itinerary unavailable: {e}'


def log_loyalty_program(
    program: str,
    provider: str,
    account_number: str = '',
    points_balance: int = 0,
    tier: str = '',
    ctx=None,
) -> bool:
    """Track a travel loyalty program membership."""
    try:
        from eos_ai.context import load_context_from_env
        from eos_ai.db import get_conn
        from datetime import datetime
        from zoneinfo import ZoneInfo
        ctx = ctx or load_context_from_env()
        PDT = ZoneInfo('America/Los_Angeles')

        with get_conn(ctx.org_id) as cur:
            cur.execute('''
                INSERT INTO events
                (org_id, event_type, payload_json, handled_by)
                VALUES (%s, %s, %s, %s)
            ''', (
                str(ctx.org_id),
                'loyalty_program',
                json.dumps({
                    'program': program,
                    'provider': provider,
                    'account_number': account_number,
                    'points_balance': points_balance,
                    'tier': tier,
                    'updated_at': datetime.now(PDT).isoformat(),
                }),
                'dex_travel',
            ))
        return True
    except Exception as e:
        logger.warning(f'[Travel] log_loyalty failed: {e}')
        return False


def reconcile_trip_expenses(
    trip_name: str,
    expenses: list,
    ctx=None,
) -> dict:
    """
    Post-trip expense reconciliation.
    expenses: [{"description": str, "amount": float, "category": str}]
    """
    try:
        from eos_ai.expense_tracker import store_expense
        total = 0.0
        stored = 0
        for exp in expenses:
            exp_copy = {**exp, 'trip': trip_name, 'source': 'trip_reconciliation'}
            if store_expense(exp_copy, ctx):
                total += float(exp.get('amount', 0))
                stored += 1

        return {
            'trip': trip_name,
            'expenses_logged': stored,
            'total': total,
        }
    except Exception as e:
        return {'error': str(e)}
```

- [ ] **Step 3: Check that `json` and `logger` are available in travel_manager.py**

```bash
grep -n "^import json\|^logger\|^import logging" /opt/OS/eos_ai/travel_manager.py | head -5
```

If missing, the new functions use `json.dumps` — ensure `import json` is at the top. If `logger` is not defined, replace with `print` or add `import logging; logger = logging.getLogger(__name__)`.

- [ ] **Step 4: Add !itinerary command to discord_bot.py**

Append before `bot.run()`:

```python
@bot.command(name='itinerary')
async def cmd_itinerary(ctx: commands.Context, *, args: str = ''):
    """Generate trip itinerary. Usage: !itinerary [trip name] | [destination] | [start date] | [end date] | [hotel optional]"""
    parts = [p.strip() for p in args.split('|')]
    if len(parts) < 3:
        await ctx.reply(
            'Usage: `!itinerary [trip name] | [destination] | [start date] | [end date] | [hotel]`\n'
            'Example: `!itinerary NYC Trip | New York | 2026-04-10 | 2026-04-13 | The Beekman Hotel`'
        )
        return
    try:
        from eos_ai.travel_manager import generate_trip_itinerary
        await ctx.reply('✈️ Generating itinerary...')
        itinerary = generate_trip_itinerary(
            trip_name=parts[0],
            destination=parts[1],
            start_date=parts[2],
            end_date=parts[3] if len(parts) > 3 else parts[2],
            hotel=parts[4] if len(parts) > 4 else '',
        )
        await ctx.reply(
            f'✈️ **Itinerary: {parts[0]}**\n'
            f'```\n{itinerary[:1500]}\n```\nSaved to Drive.'
        )
    except Exception as e:
        await ctx.reply(f'❌ Error: {e}')
```

- [ ] **Step 5: Verify**

```bash
cd /opt/OS && python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from eos_ai.travel_manager import generate_trip_itinerary, log_loyalty_program, reconcile_trip_expenses
print('travel_manager: clean')
import ast
with open('/opt/OS/13_Scripts/discord_bot.py') as f: src = f.read()
ast.parse(src)
print('discord_bot.py: syntax clean')
"
```

- [ ] **Step 6: Commit**

```bash
cd /opt/OS
git add eos_ai/travel_manager.py 13_Scripts/discord_bot.py
git commit -m "feat: add trip itinerary, loyalty tracking, expense reconciliation, !itinerary command"
```

---

## Task 14: Final verification and deploy

- [ ] **Step 1: Full import check — all new modules**

```bash
cd /opt/OS && python3 -c "
import sys; sys.path.insert(0, '/opt/OS')

# Phase 1 - Terminology
from eos_ai.task_yield_matrix import classify_task_yield, run_yield_audit, format_yield_report
from eos_ai.founder_rate import calculate_founder_rate, get_current_founder_rate, detect_delegation_threshold
from eos_ai.ideal_week import get_ideal_week, save_annual_architecture, get_annual_architecture
from eos_ai.martell_patterns import LEVERAGE_KILLER_SIGNALS, detect_leverage_killer, check_solution_standard
print('terminology: clean')

# Phase 2 - Primitives
from eos_ai.context import load_context_from_env, load_ventures_from_env
ventures = load_ventures_from_env()
print(f'ventures loaded: {len(ventures)}')

# Phase 3 - New modules
from eos_ai.quality_gate import quality_check, gate_outgoing_email
from eos_ai.okr_tracker import get_okrs, generate_okr_report
from eos_ai.event_manager import create_event, get_events, draft_talking_points, log_pr_media_inquiry, log_speaking_engagement
from eos_ai.travel_manager import generate_trip_itinerary, log_loyalty_program
from eos_ai.doc_creator import draft_announcement, draft_crisis_communication
from eos_ai.meetings import draft_meeting_minutes
from eos_ai.stakeholder_map import generate_board_update_brief
print('all modules: clean')
"
```

Expected: all three lines print cleanly.

- [ ] **Step 2: discord_bot.py syntax check**

```bash
cd /opt/OS && python3 -c "
import ast
with open('/opt/OS/13_Scripts/discord_bot.py') as f: src = f.read()
ast.parse(src)
print('discord_bot.py: syntax clean')
"
```

- [ ] **Step 3: Full EOS import check**

```bash
cd /opt/OS && python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
import eos_ai
print('eos_ai package: clean')
"
```

- [ ] **Step 4: Run daily_sync smoke test**

```bash
cd /opt/OS && python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from eos_ai.context import load_context_from_env
from eos_ai.daily_sync import DailySync
ctx = load_context_from_env()
ds = DailySync(ctx)
print('DailySync initialized: ok')
" 2>&1 | head -20
```

- [ ] **Step 5: Deploy**

```bash
cd /opt/OS
docker compose restart os-discord os-webhook
sleep 15
docker logs os-discord --tail 15
```

Expected: logs show `online` or `started`, no `Error` or `Traceback`.

- [ ] **Step 6: Final commit if any cleanup needed**

```bash
cd /opt/OS
git status
# commit any uncommitted files
git add -u
git commit -m "chore: final cleanup after EA system closure build"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Task covering it |
|---|---|
| drip_matrix.py → task_yield_matrix.py | Task 1 |
| buyback_rate.py → founder_rate.py | Task 1 |
| perfect_week.py → ideal_week.py | Task 1 |
| martell_patterns.py terminology update | Task 2 |
| All import files updated | Task 3 |
| discord_bot.py command renames | Task 4 |
| executive_assistant.md + skill files | Task 4 |
| Venture registry in context.py | Task 5 |
| VENTURES_JSON env var | Task 5 |
| Day reminder (every 5 min cron) | Task 6 |
| Mid-day check-in (12:30pm cron) | Task 6 |
| EOD next-day preview | Task 6 |
| quality_check + gate_outgoing_email | Task 7 |
| !proofread command | Task 7 |
| Quality gate in approve_followup | Task 7 |
| draft_meeting_minutes | Task 8 |
| Auto-draft on meeting completion | Task 8 |
| !minutes command | Task 8 |
| OKR tracker module | Task 9 |
| !okr command | Task 9 |
| OKR in weekly review | Task 9 |
| Event manager module | Task 10 |
| !event command | Task 10 |
| Speaking engagement logging | Task 10 |
| Talking points drafting | Task 10 |
| PR inquiry logging | Task 10 |
| !talkingpoints !pr commands | Task 10 |
| Board member functions | Task 11 |
| Board contact staleness check | Task 11 |
| !board_update command | Task 11 |
| draft_announcement | Task 12 |
| draft_crisis_communication | Task 12 |
| !announce !crisis commands | Task 12 |
| generate_trip_itinerary | Task 13 |
| log_loyalty_program | Task 13 |
| reconcile_trip_expenses | Task 13 |
| !itinerary command | Task 13 |
| Full verification + deploy | Task 14 |

**Gaps found and addressed:**
- `email_gps.py` is NOT renamed (not in spec's file rename list) — only string references in docs updated in Task 4 ✓
- `scripts/` directory creation handled in Task 6 Step 1 ✓
- `json` import availability in travel_manager.py flagged in Task 13 Step 3 ✓
- `logger` availability in doc_creator.py flagged in Task 12 Step 3 ✓
- Relationship_nurture.py existence check flagged in Task 11 Step 3 ✓
