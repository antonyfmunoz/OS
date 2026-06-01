# Operational Diagnostic — 2026-05-12

> Audited: 2026-05-13 01:21 UTC

## System Snapshot

| Metric | Value | Status |
|--------|-------|--------|
| RAM total | 7,940 MB | — |
| RAM used | 4,888 MB (62%) | OK |
| RAM available | 3,052 MB | OK |
| Swap total | 4,095 MB | — |
| Swap used | 3,504 MB (85.5%) | CRITICAL |
| Disk | 80/96 GB (83%) | Watch |
| Containers | 2 running (os-discord, os-webhook) | OK |
| Load (1m) | 0.05 per CPU | OK |

RAM is fine. Load is fine. **Swap at 85.5% is the sole trigger for
the critical pressure gate.**

## Pressure Gate Analysis

**Gate location:** `runtime/provider_state.py:216` →
calls `runtime/work_state.py:83` (`_measure_pressure()`)

**Triggering condition:**
```
CRITICAL: load_per_cpu > 10.0 OR swap_pct > 80.0
HIGH:     load_per_cpu > 5.0  OR swap_pct > 50.0
MODERATE: load_per_cpu > 2.0  OR swap_pct > 20.0
LOW:      otherwise
```

**What happens when gate fires:**
- `allow_execution()` returns `False` when pressure == CRITICAL
  (model_router.py lines 982, 1045 — cc_sdk escalation and heavy
  path both call `get_system_state().allow_execution()`)
- `allow_agent_spawn()` returns `False` when pressure == HIGH or
  CRITICAL (discord_bot.py subagent creation)
- Direct model_router `call_with_fallback()` invocations from
  `orchestrator._decompose_llm()` do NOT check the gate — they call
  the module-level function which tries providers directly. BUT the
  cc_sdk escalation path is gated.

**Current state: FIRING.** Swap at 85.5% exceeds the 80% threshold
by 5.5 percentage points. The gate has been firing continuously since
swap crossed 80%.

**Impact on today's builds:** The decomposer's LLM extraction calls
`call_with_fallback()` at module level (runtime/model_router.py:755).
This function tries providers in priority order. The cc_sdk path
(lines 982, 1045) is gated by `allow_execution()` — but the Gemini,
Groq, Anthropic paths are NOT gated. So the LLM decomposer was
**not blocked by the pressure gate** — it was blocked by the providers
themselves being down (Anthropic: credit error, Gemini: quota
exhausted). The heuristic fallback triggered because all providers
returned empty, not because the gate blocked them.

## Top Consumers + Categorization

| # | Process | RSS (MB) | %MEM | Category | Evidence |
|---|---------|----------|------|----------|----------|
| 1 | VS Code Extension Host | 745 | 9.3% | RESTARTABLE | IDE server, reconnects |
| 2 | VS Code Pylance | 573 | 7.2% | RESTARTABLE | Language server, stateless |
| 3 | Claude Code CLI | 480 | 6.0% | CRITICAL | Active session (this one) |
| 4 | discord_bot.py | 292 | 3.6% | CRITICAL | Live runtime service |
| 5–19 | 15x zombie pytest | 1,705 total | 21.0% | **IDLE** | Started May 8, 0:06–0:09 CPU time each, Sl state, no progress in 5 days |

**The 15 zombie pytest processes consume 1,705 MB and produce no
value.** They are leftover from a test run on May 8 that was never
cleaned up. Each holds ~113–232 MB of RSS and has accumulated 6–9
seconds of CPU time over 5 days — they are completely idle.

## Gemini 403 Root Cause

**NOT a 403.** The actual error is **429 RESOURCE_EXHAUSTED**.

**Exact error:**
```
429 RESOURCE_EXHAUSTED
Quota: generativelanguage.googleapis.com/generate_content_free_tier_requests
Limit: 20 requests/day per model (FREE TIER)
quotaId: GenerateRequestsPerDayPerProjectPerModel-FreeTier
```

**Root cause: The Gemini API key is on the FREE TIER, which allows
only 20 requests per day per model.** Today's build phases
(decomposer-depth, persist-all, domain-bridge, authority-tier)
consumed those 20 requests during LLM extraction calls, and
subsequent attempts hit the quota wall.

This is NOT:
- ~~Billing disabled~~ — free tier has no billing
- ~~Auth issue~~ — key authenticates successfully (403 would mean
  auth failure)
- ~~API not enabled~~ — API is enabled, quota just exhausted

**API key source:** `GEMINI_API_KEY` env var loaded from
`runtime/.env` via dotenv.

## Resolution Plan A — Swap Pressure

**Root cause:** 15 zombie pytest processes from May 8 consuming
1,705 MB total. Killing them will reclaim ~1.7 GB from swap.

**Recommended action:**
```bash
# Kill all zombie pytest processes
pkill -f "python3 -m pytest tests/"

# Wait 30s for kernel to reclaim swap pages
sleep 30

# Verify swap dropped
free -m
```

**Why this is right:** All 15 processes have been idle for 5 days
(Sl state, 6-9s CPU time). They are leftover test runs, not running
services. No data loss risk. discord_bot.py and Claude Code are
unaffected.

**Expected post-action state:**
- Swap: ~1,800 MB used (44%) → pressure drops to MODERATE
- `allow_execution()` → True
- `allow_agent_spawn()` → True

**Verification command:**
```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from runtime.work_state import _measure_pressure, _get_swap_pct
print(f'swap: {_get_swap_pct()}%')
print(f'pressure: {_measure_pressure().value}')
"
```

**Alternative actions if primary fails:**
1. If swap doesn't drop immediately after kill: the kernel holds
   dirty pages in swap until they're accessed. Run
   `sync && sleep 60` and re-check — swap reclaim is asynchronous.
2. If still above 80%: VS Code server processes (745+573 = 1,318 MB)
   are the next candidates. These reconnect automatically:
   ```bash
   pkill -f ".vscode-server/cli/servers"
   ```
   Only do this if the pytest kill doesn't bring swap under 50%.

**Risk notes:** None. Zombie pytest processes have no open files,
no network connections, no database handles. pkill sends SIGTERM,
which pytest handles gracefully.

## Resolution Plan B — Gemini Quota

**Root cause:** Free-tier Gemini API key. 20 requests/day limit per
model. Unsuitable for a development pipeline that makes 3-10 LLM
calls per ingestion run.

**Recommended action (priority order):**

1. **Upgrade to paid tier (immediate fix):**
   - Go to https://ai.google.dev/pricing
   - Or https://console.cloud.google.com → APIs & Services → 
     Gemini API → Quotas
   - Switch from free tier to pay-as-you-go
   - Gemini 2.5 Flash: $0.15/1M input tokens, $0.60/1M output tokens
   - At current usage (~50 calls/day × ~2K tokens each): ~$0.02/day
   - No code change needed — same API key works

2. **Alternative: create a new GCP project with billing enabled:**
   - Create project at https://console.cloud.google.com
   - Enable Generative Language API
   - Create new API key
   - Update `GEMINI_API_KEY` in `/opt/OS/runtime/.env`

3. **Alternative: shift primary to Groq (no quota issue):**
   - Groq key is active (available=True in router)
   - Groq serves Llama 3.3 70B — quality score 0.55 vs Gemini 0.65
   - No code change needed: when Gemini returns empty, router already
     falls to Groq
   - But Groq has its own rate limits (free tier: 30 req/min,
     14,400/day) — much more generous

**No code change needed downstream.** When Gemini returns a non-empty
response, model_router already uses it. The quota error causes
`_call_gemini()` to return `""`, and the router falls through to
the next provider.

**Verification command (after fix):**
```bash
python3 -c "
import os, sys
sys.path.insert(0, '/opt/OS')
from dotenv import load_dotenv
load_dotenv('/opt/OS/runtime/.env')
from google import genai
from google.genai import types as genai_types
client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
r = client.models.generate_content(
    model='gemini-2.5-flash',
    contents='Say hello.',
    config=genai_types.GenerateContentConfig(max_output_tokens=20),
)
print(f'OK: {r.text}')
"
```

## Verification Protocol (Post-Fix Checks)

After killing zombie pytest processes:

```bash
# 1. Confirm pytests are gone
pgrep -c -f "python3 -m pytest" && echo "STILL RUNNING" || echo "CLEAN"

# 2. Check swap
free -m | grep Swap

# 3. Check pressure gate
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from runtime.work_state import _measure_pressure, _get_swap_pct
from runtime.provider_state import get_system_state
swap = _get_swap_pct()
pressure = _measure_pressure()
state = get_system_state()
print(f'swap: {swap}%')
print(f'pressure: {pressure.value}')
print(f'allow_execution: {state.allow_execution()}')
print(f'allow_agent_spawn: {state.allow_agent_spawn()}')
"

# 4. Verify model_router can reach providers
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from runtime.model_router import get_router, MODEL_REGISTRY
router = get_router()
for name, cfg in MODEL_REGISTRY.items():
    print(f'{name}: available={cfg.available}')
"
```

After fixing Gemini quota:

```bash
# 5. Test Gemini directly
python3 -c "
import os, sys
sys.path.insert(0, '/opt/OS')
from dotenv import load_dotenv
load_dotenv('/opt/OS/runtime/.env')
from google import genai
from google.genai import types
client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
r = client.models.generate_content(
    model='gemini-2.5-flash',
    contents='Say hello.',
    config=types.GenerateContentConfig(max_output_tokens=20),
)
print(f'Gemini OK: {r.text}')
"
```
