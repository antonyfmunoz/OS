# C31 Phase 2A Report — P0 Runtime Safety

**Date:** 2026-06-29
**Branch:** worktree-c31-phase2a
**Scope:** Remove immediate runtime crash risk + make Tier 1 failures observable.

---

## 1. P0 Fix: Missing `discord_output_policy` Import

**Problem:** `services/discord_bot_commands.py:156` imports `substrate.execution.bridge.discord_output_policy.get_display_name` — module did not exist. Unguarded import inside `with _WATCHERS_LOCK:` block would crash at runtime when listing active watchers.

**Fix:** Created `substrate/execution/bridge/discord_output_policy.py` (15 lines).
- Provides `get_display_name(name: str) -> str`
- Strips common prefixes (`cc_`, `session_`, `watcher_`, `bridge_`), replaces underscores with spaces, title-cases
- Only consumer: `services/discord_bot_commands.py:156`

**Verification:** `py_compile` passes on both files.

---

## 2. Tier 1 Silent Exception Fixes (30 blocks across 5 files)

Every `except: pass` / `except Exception: pass` replaced with `logger.debug("...", exc_info=True)`.

| File | Blocks Fixed | What They Guard |
|------|-------------|-----------------|
| `substrate/__init__.py` | 6 | Reality query, EventSpine emit, model init (instance/canonical/memory/event_spine) |
| `substrate/control_plane/orchestrator/orchestrator.py` | 9 | Venture KPIs, DB queries (tasks/approvals/interactions/reply_rate), knowledge graph patterns, reality context, behavioral patterns, budget cycle |
| `adapters/models/cc_sdk.py` | 6 | Provider state tracking, CPU load check, orphan process cleanup, PID snapshot, backpressure gate |
| `substrate/execution/bridge/session_discord_bridge.py` | 5 | Discord UI view timeouts (3), channel ID parsing (2) |
| `substrate/execution/pipeline.py` | 4 | Event listener dispatch, outcome recording, memory reconciliation, completeness evaluation |

**Changes per file:**
- Added `import logging` and `logger = logging.getLogger(__name__)` where missing (orchestrator.py, session_discord_bridge.py, pipeline.py)
- Existing loggers in substrate/__init__.py and cc_sdk.py reused

**Post-fix count:** 0 silent exceptions remain in these 5 files.

---

## 3. os-discord Restart Investigation

**Finding:** Not actionable.

- **RestartCount: 2**, both on 2026-06-19 at 22:52:37–22:52:38 (sub-second restart).
- **Single instability event**, not two separate incidents over 9 days.
- **OOMKilled: false**. No OOM signals in `dmesg`.
- **Restart policy: `on-failure`** — container exited non-zero, Docker restarted automatically.
- **Root cause not determinable** — crash logs from June 19 lost on restart.
- **Container stable since** — 10 days continuous operation, no errors beyond expected Perplexity/Groq rate limits (fallback providers).
- **Recommendation:** Would need persistent log collection (journald or external log driver) to diagnose past crashes. Current `json-file` driver loses pre-restart logs.

---

## 4. Test Results

| Suite | Result |
|-------|--------|
| `tests/substrate/` | **70/70 passed** (0.30s) |
| `tests/adapters/` | **50/50 passed** (1.14s) |
| `py_compile` (all 7 modified files) | **All pass** |

No regressions introduced.

---

## 5. Files Modified

| File | Change |
|------|--------|
| `substrate/execution/bridge/discord_output_policy.py` | **NEW** — get_display_name() |
| `substrate/__init__.py` | 6 except:pass → logger.debug |
| `substrate/control_plane/orchestrator/orchestrator.py` | + import logging/logger, 9 except:pass → logger.debug |
| `adapters/models/cc_sdk.py` | 6 except:pass → logger.debug |
| `substrate/execution/bridge/session_discord_bridge.py` | + import logging/logger, 5 except:pass → logger.debug |
| `substrate/execution/pipeline.py` | + import logging/logger, 4 except:pass → logger.debug |

**Total:** 1 new file (15 lines), 5 files modified (30 silent exceptions fixed), 0 files deleted.

---

## 6. What This Does NOT Fix (Out of Scope)

- Tier 2 silent exceptions (107 blocks in organism/bridge) — Phase 2A scope is Tier 1 only
- Tier 3 silent exceptions (380 blocks in scripts/transports) — deferred
- Speculative workstation architecture (32 files) — Phase 2B
- Dependency boundary enforcement — Phase 2C
- Adapter engine wiring — Phase 2C
