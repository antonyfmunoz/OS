#!/usr/bin/env python3
"""
Control Layer v2 — Remote Execution smoke test.

Verifies the queue→daemon→executor→ack loop end-to-end without ever
introducing networking, threads, or a second pipeline.

Checks:
    1.  enqueue command on a test node
    2.  daemon run-once processes it
    3.  result returned correctly (ok=True)
    4.  ack removes from pending queue
    5.  invalid (mismatched) node → skipped
    6.  malformed envelope → rejected safely (and drained)
    7.  queue cap respected (MAX_QUEUE_PER_NODE)
    8.  multiple commands batch processed
    9.  idempotent ack (duplicate ack → ok)
   10.  hot-path imports remain clean
"""

from __future__ import annotations

import json
import sys
import uuid

sys.path.insert(0, "/opt/OS")

from eos_ai.substrate import control_bridge as bridge  # noqa: E402
from eos_ai.substrate import control_commands as cc  # noqa: E402
from eos_ai.substrate.remote_executor import RemoteExecutor  # noqa: E402
from eos_ai.substrate import remote_identity  # noqa: E402


RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, ok, detail))
    marker = "PASS" if ok else "FAIL"
    print(f"  [{marker}] {name}{(' — ' + detail) if detail else ''}")


def _fresh_node() -> str:
    return f"smoke_{uuid.uuid4().hex[:8]}"


def test_enqueue_and_run_once() -> None:
    print("\n[1-4] enqueue → run_once → result → ack drains queue")
    node = _fresh_node()
    cmd = cc.make_command("run_shell", {"cmd": "echo hello"}, node_id=node)
    enq = bridge.send_command(cmd)
    check("enqueue ok", enq["ok"], enq.get("reason", ""))

    ex = RemoteExecutor()
    out = ex.poll_once(node)
    check("poll processed 1", out["processed"] == 1, f"processed={out['processed']}")
    if out["results"]:
        r = out["results"][0]
        check("result ok=True", bool(r.get("ok")), str(r))
        check("result has stdout 'hello'", "hello" in (r.get("stdout") or ""), r.get("stdout", ""))

    depth = bridge.queue_depth(node)
    check("queue drained after ack", depth == 0, f"depth={depth}")
    bridge.clear_queue(node)


def test_invalid_node_skipped() -> None:
    print("\n[5] command targeted at OTHER node is not picked up")
    real = _fresh_node()
    other = _fresh_node()
    cmd = cc.make_command("run_shell", {"cmd": "echo nope"}, node_id=other)
    bridge.send_command(cmd)

    ex = RemoteExecutor()
    out = ex.poll_once(real)
    check(
        "real node sees nothing",
        out["processed"] == 0 and out["skipped"] == 0,
        f"processed={out['processed']} skipped={out['skipped']}",
    )
    # And the other node still owns it.
    check("other node retains command", bridge.queue_depth(other) == 1)
    bridge.clear_queue(other)


def test_malformed_rejected() -> None:
    print("\n[6] malformed envelope (bad action) is rejected & drained")
    node = _fresh_node()
    # Bypass send_command's validator by writing directly via internal state.
    # Easier path: enqueue a valid envelope then mutate via raw dict insertion.
    raw_cmd = cc.make_command("run_shell", {"cmd": "echo ok"}, node_id=node)
    bridge.send_command(raw_cmd)
    # Now corrupt by injecting a raw row directly into the queue.
    state = bridge._load_state()  # noqa: SLF001
    state["pending"].setdefault(node, []).append(
        {
            "action": "definitely_not_allowed",
            "payload": {},
            "issued_by": "smoke",
            "node_id": node,
            "target": "local",
            "command_id": f"cmd_{uuid.uuid4().hex[:12]}",
            "created_at": 0.0,
        }
    )
    bridge._save_state(state)  # noqa: SLF001

    ex = RemoteExecutor()
    out = ex.poll_once(node)
    has_invalid_marker = any(
        "invalid_envelope" in str(r.get("reason", "")) for r in out["results"]
    )
    check(
        "malformed flagged invalid_envelope",
        has_invalid_marker,
        json.dumps(out["results"], default=str),
    )
    check("queue drained after malformed handling", bridge.queue_depth(node) == 0)
    bridge.clear_queue(node)


def test_queue_cap() -> None:
    print("\n[7] queue cap (MAX_QUEUE_PER_NODE=100) respected")
    node = _fresh_node()
    accepted = 0
    rejected = 0
    for _ in range(bridge.MAX_QUEUE_PER_NODE + 5):
        r = bridge.send_command(
            cc.make_command("run_shell", {"cmd": "echo x"}, node_id=node)
        )
        if r["ok"]:
            accepted += 1
        elif r.get("reason") == "queue_full":
            rejected += 1
    check(
        "exactly MAX_QUEUE_PER_NODE accepted",
        accepted == bridge.MAX_QUEUE_PER_NODE,
        f"accepted={accepted}",
    )
    check("overflow rejected with queue_full", rejected == 5, f"rejected={rejected}")
    bridge.clear_queue(node)


def test_batch_processing() -> None:
    print("\n[8] multiple commands processed in single poll (HARD_BATCH_CAP=10)")
    node = _fresh_node()
    for i in range(7):
        bridge.send_command(
            cc.make_command("run_shell", {"cmd": f"echo {i}"}, node_id=node)
        )
    ex = RemoteExecutor()
    out = ex.poll_once(node)
    check("batch processed 7", out["processed"] == 7, f"processed={out['processed']}")
    check("queue empty after batch", bridge.queue_depth(node) == 0)
    bridge.clear_queue(node)


def test_idempotent_ack() -> None:
    print("\n[9] duplicate ack is a safe no-op")
    node = _fresh_node()
    cmd = cc.make_command("run_shell", {"cmd": "echo dup"}, node_id=node)
    bridge.send_command(cmd)
    first = bridge.ack_command(cmd.command_id, result={"smoke": True})
    second = bridge.ack_command(cmd.command_id, result={"smoke": True})
    check("first ack ok", first["ok"], first.get("reason", ""))
    check(
        "second ack ok (idempotent)",
        second["ok"],
        f"reason={second.get('reason')}",
    )
    bridge.clear_queue(node)


def test_hot_path_imports() -> None:
    print("\n[10] hot-path imports remain clean")
    try:
        import importlib

        for mod in (
            "eos_ai.gateway",
            "eos_ai.cognitive_loop",
            "eos_ai.model_router",
            "eos_ai.agent_runtime",
            "eos_ai.primitives",
        ):
            importlib.import_module(mod)
        check("hot-path imports clean", True)
    except Exception as e:  # noqa: BLE001
        check("hot-path imports clean", False, f"{type(e).__name__}: {e}")


def test_identity() -> None:
    print("\n[bonus] remote_identity helpers")
    nid = remote_identity.get_node_id()
    check("get_node_id non-empty", bool(nid), nid)
    cmd = cc.make_command("run_shell", {"cmd": "echo y"}, node_id=nid)
    check("scope match", remote_identity.validate_command_scope(cmd, nid))
    check(
        "scope mismatch detected",
        not remote_identity.validate_command_scope(cmd, "definitely_not_this_node"),
    )


def main() -> int:
    print("=" * 60)
    print("Control Layer v2 — Remote Execution Smoke Test")
    print("=" * 60)

    test_enqueue_and_run_once()
    test_invalid_node_skipped()
    test_malformed_rejected()
    test_queue_cap()
    test_batch_processing()
    test_idempotent_ack()
    test_identity()
    test_hot_path_imports()

    print("\n" + "=" * 60)
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    total = len(RESULTS)
    print(f"RESULT: {passed}/{total} checks passed")
    print("=" * 60)
    if passed != total:
        for name, ok, detail in RESULTS:
            if not ok:
                print(f"  FAIL: {name} — {detail}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
