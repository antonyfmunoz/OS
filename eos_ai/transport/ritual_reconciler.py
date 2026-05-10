"""
Ritual reconciler — bounded visibility of station action outcomes in rituals.

`ritual.outputs["body_actions"]` already carries `action_id` for every
station action a ritual body proposed (see ritual_body.py). This module
adds the smallest useful consumer for that metadata: a reconcile pass that
looks each action_id up in the ResultStore and mirrors the terminal outcome
onto the ritual's outputs so operators and later callers can answer:

    "Did the open_day ritual actually succeed on my workstation?"

Design rules:
  - No correlation engine. This is a pure dict lookup per action_id.
  - Non-destructive: the original `body_actions` list is updated in place
    with a `result_status` / `result_detail` / `result_fallback` field when
    a matching result is known, and a `result_summary` dict is written onto
    `ritual.outputs` for quick inspection.
  - Idempotent. Running reconcile twice yields the same ritual state.
  - Best-effort. Missing results leave the body entry untouched, never raise.
  - Reversible. Calling a ritual body again overwrites body_actions; the
    reconcile annotations vanish cleanly until reconcile is re-run.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, asdict, field
from typing import Optional

from eos_ai.transport.result_store import ResultStore, get_result_store
from eos_ai.transport.rituals import RitualRegistry


def _log(msg: str) -> None:
    print(f"[substrate.ritual_reconciler] {msg}", file=sys.stderr)


@dataclass
class ReconcileSummary:
    ritual_id: str
    total: int = 0
    with_action_id: int = 0
    matched: int = 0
    unmatched: int = 0
    succeeded: int = 0
    failed: int = 0
    rejected: int = 0
    other: int = 0
    fallbacks: int = 0
    by_kind: dict[str, int] = field(default_factory=dict)
    kind_backfilled: int = 0

    def as_dict(self) -> dict:
        return asdict(self)

    @property
    def fully_resolved(self) -> bool:
        """True when every action_id-bearing body entry now has a result."""
        return self.with_action_id > 0 and self.unmatched == 0

    @property
    def all_succeeded(self) -> bool:
        """True when every resolved body entry reports succeeded."""
        return self.matched > 0 and self.succeeded == self.matched


def reconcile_ritual(
    ritual_id: str,
    *,
    store: Optional[ResultStore] = None,
) -> Optional[ReconcileSummary]:
    """
    Reconcile a single ritual's body actions against ingested results.

    Returns None if the ritual is unknown; otherwise returns a
    ReconcileSummary describing how many body entries got matched to
    stored results. Any matched entry has these fields added in-place:
        result_status   — mirrors ActionStatus.value
        result_detail   — free-text detail from the daemon
        result_fallback — True if the daemon used a graceful-degradation path
    """
    reg = RitualRegistry.default()
    ritual = reg.get(ritual_id)
    if ritual is None:
        _log(f"reconcile: unknown ritual_id {ritual_id!r}")
        return None

    body_actions = ritual.outputs.get("body_actions") or []
    if not isinstance(body_actions, list):
        _log(f"reconcile: ritual {ritual_id} body_actions malformed; skipping")
        return None

    s = store or get_result_store()
    summary = ReconcileSummary(ritual_id=ritual_id, total=len(body_actions))

    for entry in body_actions:
        if not isinstance(entry, dict):
            continue
        aid = entry.get("action_id")
        if not aid:
            continue
        summary.with_action_id += 1

        ir = s.get(aid)
        if ir is None:
            summary.unmatched += 1
            continue

        entry["result_status"] = ir.status
        entry["result_detail"] = ir.detail
        entry["result_fallback"] = ir.is_fallback

        # Back-fill kind onto the stored result if the body entry knows it
        # and the daemon did not stamp one. Keeps old-format results useful
        # for kind-aware reporting without a rewrite.
        body_kind = entry.get("kind")
        if body_kind and not ir.kind:
            ir.kind = str(body_kind)
            try:
                s.put(ir)
                summary.kind_backfilled += 1
            except Exception as e:
                _log(f"kind backfill failed on {aid}: {e}")

        summary.matched += 1
        kind_for_count = ir.kind or (str(body_kind) if body_kind else None)
        if kind_for_count:
            summary.by_kind[kind_for_count] = summary.by_kind.get(kind_for_count, 0) + 1
        status = (ir.status or "").lower()
        if status == "succeeded":
            summary.succeeded += 1
        elif status == "failed":
            summary.failed += 1
        elif status == "rejected":
            summary.rejected += 1
        else:
            summary.other += 1
        if ir.is_fallback:
            summary.fallbacks += 1

    # Persist summary + updated body_actions onto the ritual.
    ritual.outputs["body_actions"] = body_actions
    ritual.outputs["result_summary"] = summary.as_dict()
    try:
        reg._flush()  # noqa: SLF001 — reuse existing persistence path
    except Exception as e:
        _log(f"flush failed on {ritual_id}: {e}")

    return summary


def reconcile_recent(limit: int = 20) -> list[ReconcileSummary]:
    """
    Reconcile the most recent rituals in the registry. Useful as a single
    operator call after a drain pass: "update everything that might have
    pending results." Never raises on individual failures.
    """
    reg = RitualRegistry.default()
    try:
        rituals = list(reg.history())[-limit:]  # newest tail
    except Exception as e:
        _log(f"reconcile_recent: list failed: {e}")
        return []

    out: list[ReconcileSummary] = []
    for ritual in rituals:
        try:
            summary = reconcile_ritual(ritual.ritual_id)
        except Exception as e:
            _log(f"reconcile_recent: {ritual.ritual_id} raised: {e}")
            continue
        if summary is not None:
            out.append(summary)
    return out
