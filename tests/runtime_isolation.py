"""Test-only isolation of live runtime state — the Group A whole-tree unblocker.

Why this exists
---------------
28 test files (the "Group A" manifest below) constructed runtime objects that
resolved into the LIVE production runtime store at ``/opt/OS/data/runtime``.
Under a whole-tree run those files did not merely read stale data — they stalled
past any usable bound, because the live store grows without limit under normal
production activity (``organism/learning/signal_feed.jsonl`` was measured at
16,467,491,885 bytes during one diagnostic window and 273,707,273 bytes in a
later one, after production rotated it). Three authoritative whole-tree shards
each hit a 10,800s bound and completed 72% / 9% / 39% of their assigned files.

The coupling was proven causally, not inferred: the SAME file at the SAME commit
goes from a 60s+ timeout to ``30 passed in 0.43s`` when — and only when — the
runtime-state root is redirected. Nothing else differs between the two runs.

Two distinct resolution paths reach live state, and BOTH must be closed:

A. **Canonical resolution.** ``substrate/state/runtime_paths.py::runtime_state_root``
   reads ``UMH_STATE_DIR`` first, then ``$UMH_ROOT/data/runtime/umh``. It reads
   the environment on EVERY call and caches nothing, so redirecting the env var
   is sufficient for this path and needs no production change.

B. **Relative-path bypass.** A number of modules build runtime paths that never
   pass through ``runtime_state_path()`` at all — e.g.
   ``Path("data/runtime/mesh_nodes.json")`` in ``compute_fabric_runtime.py`` and
   ``distributed_runtime.py``, the proof directories in
   ``execution_authority_engine_v1.py`` / ``live_local_runtime_execution_v1.py``
   / ``workpacket_execution_gate_v1.py``, and the bootstrap store list in
   ``runtime_bootstrap_state_v1.py``. These are RELATIVE, so they resolve against
   the process working directory. Redirecting ``UMH_STATE_DIR`` does not move
   them; changing the working directory does.

Closing (B) with a temporary cwd is what makes this correction test-only. The
alternative — rewriting those literals to go through ``runtime_state_path()`` —
would be a production change, and this seam deliberately does not make one.

Scope discipline
----------------
The fixture is applied to an EXACT manifest (``GROUP_A_FILES``), not
repository-wide. A blanket autouse fixture would silently change the working
directory for ~495 files whose semantics were never validated under it; that is
a larger behavioural change than the defect being fixed. Files opt in by exact
name, so the blast radius equals the proven-affected set.

What this seam does NOT claim
-----------------------------
It does not fix the ~30 module-level ``_REPO_ROOT = os.environ.get("UMH_ROOT",
"/opt/OS")`` globals across ``substrate/organism/``. Those are import-time caches
of the SOURCE tree, a different concern from runtime state, and no authorized
Group A test was shown to depend on them. They are out of scope here rather than
silently assumed fixed.

It also does not fix ``tests/test_stage1_acceptance_e2e.py``, whose stall is an
unbounded HTTP call to a live service (see ``tests/bounded_http.py``), nor
``tests/test_strategic_context_runtime.py`` (Group B), which is finite and fails
a deterministic key-set assertion identically on the accepted baseline.
"""

from __future__ import annotations

import os
from pathlib import Path

# The live production runtime root these tests must never touch.
LIVE_RUNTIME_ROOT = "/opt/OS/data/runtime"

# Marker written into every isolated root so test-originated activity can be
# distinguished from concurrent production activity by inspection alone.
SENTINEL_NAME = ".umh_test_isolated_root"

# Minimum directory skeleton created inside the isolated cwd. These mirror the
# RELATIVE literals that bypass runtime_state_path(); creating them empty keeps
# the tests self-contained. Live production stores are never copied in — an
# empty isolated store is the point.
_RELATIVE_STORE_DIRS = (
    "data/runtime",
    "data/runtime/local_worker_runtime/inbox",
    "data/runtime/local_worker_runtime/processed",
    "data/runtime/local_worker_runtime/failed",
    "data/runtime/runtime_proofs",
    "data/runtime/spine_dispatch_queue/inbox",
    "data/runtime/spine_dispatch_queue/outbox",
    "data/runtime/spine_dispatch_queue/archive",
    "data/runtime/spine_dispatch_queue/results",
    "data/runtime/spine_gate_proofs",
    "data/runtime/spine_proofs",
    "data/runtime/sync_proofs",
    "data/runtime/live_execution_proofs",
    "data/runtime/execution_authority_proofs",
    "data/runtime/workpacket_execution_gate_proofs",
    "data/runtime/browser_profiles",
)

# ── The exact Group A manifest ───────────────────────────────────────────────
# 28 unique files. Reconciled disposition under isolation at the time of this
# correction: 22 CLEAN_PASS, 5 FINITE_FAILURE (pre-existing, identical on the
# accepted baseline 5f3c0d64c), 1 TIMEOUT (test_stage1_acceptance_e2e.py, an
# external-service dependency corrected separately in tests/bounded_http.py).
GROUP_A_FILES: frozenset[str] = frozenset(
    {
        "test_agent_workforce_runtime.py",
        "test_c19_integration.py",
        "test_c21_3_attention_vision.py",
        "test_c22_acceptance.py",
        "test_c22_product_factory.py",
        "test_c22_production_ops_runtime.py",
        "test_c22_production_planning.py",
        "test_c22_production_review.py",
        "test_capability_catalog_slice_a.py",
        "test_capability_intelligence_integration.py",
        "test_execution_fabric_runtime.py",
        "test_executive_brief_runtime.py",
        "test_executive_portfolio_runtime.py",
        "test_gate3_governed_work_runtime.py",
        "test_gate4_intent_runtime.py",
        "test_gate4_workstation_convergence.py",
        "test_governance_runtime.py",
        "test_governed_execution_runtime.py",
        "test_organism_coordination_engine.py",
        "test_organism_portfolio_runtime.py",
        "test_phase14_8c_wave3.py",
        "test_phase23_engineering_proof_loop.py",
        "test_phase25_workspace_observation.py",
        "test_prediction_portfolio_runtime.py",
        "test_resource_allocation_runtime.py",
        "test_scenario_intelligence_engine.py",
        "test_stage1_acceptance_e2e.py",
        "test_type_divergence.py",
    }
)


class IsolationSetupError(RuntimeError):
    """Raised when an isolated runtime root cannot be established.

    Fail CLOSED. If isolation cannot be set up, the test must not run — falling
    back to the live production store is precisely the defect being corrected,
    and a silently-unisolated test is worse than a failing one because it
    reports a pass while touching production state.
    """


def build_isolated_root(base: Path) -> Path:
    """Create a minimal isolated runtime root and return it.

    Contains only the empty relative-store skeleton plus a sentinel file. Never
    copies live production data — an empty store is what makes the isolation
    meaningful.
    """
    base = Path(base)
    try:
        for rel in _RELATIVE_STORE_DIRS:
            (base / rel).mkdir(parents=True, exist_ok=True)
        (base / SENTINEL_NAME).write_text(
            "UMH test-isolated runtime root — not production state\n", encoding="utf-8"
        )
    except OSError as exc:  # pragma: no cover — surfaced via IsolationSetupError
        raise IsolationSetupError(f"cannot build isolated runtime root at {base}: {exc}") from exc
    if not (base / SENTINEL_NAME).exists():
        raise IsolationSetupError(f"isolated root sentinel missing at {base}")
    return base


def assert_outside_live_runtime(path: Path | str) -> None:
    """Refuse any candidate root that resolves inside the live runtime tree.

    A temp dir that somehow resolved under ``/opt/OS/data/runtime`` would defeat
    the entire correction while still looking isolated, so this is checked
    explicitly rather than assumed from ``mktemp`` semantics.
    """
    resolved = os.path.realpath(str(path))
    live = os.path.realpath(LIVE_RUNTIME_ROOT)
    if resolved == live or resolved.startswith(live + os.sep):
        raise IsolationSetupError(
            f"isolated root {resolved} resolves inside the live runtime store {live}"
        )


def is_group_a(path: Path | str) -> bool:
    """True when the given test file is in the exact Group A manifest."""
    return Path(str(path)).name in GROUP_A_FILES
