"""
Ritual runner — shell-callable entry points for open_day / close_day.

Wires the RitualRegistry into existing cron scripts with the smallest
possible surface: a module that can be invoked as

    python3 -m runtime.transport.ritual_runner open_day start
    python3 -m runtime.transport.ritual_runner open_day finish <ritual_id>
    python3 -m runtime.transport.ritual_runner close_day start
    python3 -m runtime.transport.ritual_runner close_day finish <ritual_id>
    python3 -m runtime.transport.ritual_runner status

`start` prints the new ritual_id to stdout so bash callers can capture it:

    RID=$(python3 -m runtime.transport.ritual_runner open_day start)
    ...
    python3 -m runtime.transport.ritual_runner open_day finish "$RID"

This is deliberately additive — existing cron scripts keep running exactly
as they do today. Ritual capture is a one-line prepend/append that can be
inserted without touching the body of any cron job.
"""

from __future__ import annotations

import sys
from datetime import date

from execution.transport.ritual_body import (
    RitualPolicy,
    run_close_day_body,
    run_open_day_body,
)
from execution.transport.rituals import (
    RitualKind,
    RitualRegistry,
    RitualState,
)


def _apply_ritual_state(
    policy: RitualPolicy | None,
    ritual_id: str,
    ritual_kind: str,
    ritual_state: str,
) -> None:
    """Best-effort operator-state hook. Never raises."""
    try:
        node_id = policy.station_node_id if policy else None
        if not node_id:
            return
        # Pull readiness/scene from the ritual outputs the body just wrote.
        scene = None
        scene_reason = None
        readiness_class = None
        readiness_age = None
        try:
            r = RitualRegistry.default().get(ritual_id)
            if r is not None:
                outputs = getattr(r, "outputs", {}) or {}
                sd = outputs.get("scene_decision") or {}
                if isinstance(sd, dict):
                    scene = sd.get("scene")
                    scene_reason = sd.get("reason")
                rd = outputs.get("readiness") or {}
                if isinstance(rd, dict):
                    readiness_class = rd.get("classification")
                    readiness_age = rd.get("heartbeat_age_s")
        except Exception:
            pass

        from execution.transport.operator_transitions import apply_ritual

        apply_ritual(
            node_id,
            ritual_id=ritual_id,
            ritual_kind=ritual_kind,
            ritual_state=ritual_state,
            scene=scene,
            scene_reason=scene_reason,
            readiness_classification=readiness_class,
            readiness_age_s=readiness_age,
        )
    except Exception as e:
        print(f"[ritual] operator_state hook failed: {e}", file=sys.stderr)


def _today_inputs() -> dict:
    return {"date": date.today().isoformat()}


# ─── Public programmatic API ─────────────────────────────────────────────────

def start_open_day(
    inputs: dict | None = None,
    policy: RitualPolicy | None = None,
) -> str:
    reg = RitualRegistry.default()
    r = reg.start(RitualKind.OPEN_DAY, inputs=inputs or _today_inputs())
    reg.advance(r.ritual_id, RitualState.GATHERING)
    print(f"[ritual] open_day started ritual_id={r.ritual_id}", file=sys.stderr)
    if policy is not None:
        try:
            run_open_day_body(r.ritual_id, policy)
        except Exception as e:
            # Body is best-effort — never take down the ritual.
            print(f"[ritual] open_day body failed: {e}", file=sys.stderr)
    _apply_ritual_state(policy, r.ritual_id, "open_day", "started")
    return r.ritual_id


def finish_open_day(
    ritual_id: str,
    outputs: dict | None = None,
    policy: RitualPolicy | None = None,
) -> None:
    reg = RitualRegistry.default()
    reg.advance(ritual_id, RitualState.BRIEFING)
    reg.advance(ritual_id, RitualState.HANDOFF)
    reg.complete(ritual_id, outputs=outputs or {})
    print(f"[ritual] open_day completed ritual_id={ritual_id}", file=sys.stderr)
    _apply_ritual_state(policy, ritual_id, "open_day", "finished")


def start_close_day(
    inputs: dict | None = None,
    policy: RitualPolicy | None = None,
) -> str:
    reg = RitualRegistry.default()
    r = reg.start(RitualKind.CLOSE_DAY, inputs=inputs or _today_inputs())
    reg.advance(r.ritual_id, RitualState.GATHERING)
    print(f"[ritual] close_day started ritual_id={r.ritual_id}", file=sys.stderr)
    if policy is not None:
        try:
            run_close_day_body(r.ritual_id, policy)
        except Exception as e:
            print(f"[ritual] close_day body failed: {e}", file=sys.stderr)
    _apply_ritual_state(policy, r.ritual_id, "close_day", "started")
    return r.ritual_id


def finish_close_day(
    ritual_id: str,
    outputs: dict | None = None,
    policy: RitualPolicy | None = None,
) -> None:
    reg = RitualRegistry.default()
    reg.advance(ritual_id, RitualState.BRIEFING)
    reg.advance(ritual_id, RitualState.HANDOFF)
    reg.complete(ritual_id, outputs=outputs or {})
    print(f"[ritual] close_day completed ritual_id={ritual_id}", file=sys.stderr)
    _apply_ritual_state(policy, ritual_id, "close_day", "finished")


def fail_ritual(ritual_id: str, reason: str) -> None:
    RitualRegistry.default().fail(ritual_id, reason)
    print(f"[ritual] failed ritual_id={ritual_id} reason={reason}", file=sys.stderr)


# ─── CLI ─────────────────────────────────────────────────────────────────────

_USAGE = (
    "usage: python3 -m runtime.transport.ritual_runner "
    "{open_day|close_day} {start|finish <ritual_id>} "
    "| status"
)


def _main(argv: list[str]) -> int:
    if not argv:
        print(_USAGE, file=sys.stderr)
        return 2

    cmd = argv[0]

    if cmd == "status":
        reg = RitualRegistry.default()
        active = reg.active()
        if not active:
            print("no active rituals")
            return 0
        for r in active:
            print(f"{r.ritual_id}\t{r.kind.value}\t{r.state.value}\t{r.started_at}")
        return 0

    if cmd in ("open_day", "close_day"):
        if len(argv) < 2:
            print(_USAGE, file=sys.stderr)
            return 2
        action = argv[1]
        if action == "start":
            rid = start_open_day() if cmd == "open_day" else start_close_day()
            print(rid)  # stdout: the ritual id, for bash capture
            return 0
        if action == "finish":
            if len(argv) < 3:
                print("error: finish requires <ritual_id>", file=sys.stderr)
                return 2
            ritual_id = argv[2]
            try:
                if cmd == "open_day":
                    finish_open_day(ritual_id)
                else:
                    finish_close_day(ritual_id)
            except KeyError as e:
                print(f"error: {e}", file=sys.stderr)
                return 1
            return 0
        print(_USAGE, file=sys.stderr)
        return 2

    print(_USAGE, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
