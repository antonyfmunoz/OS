#!/usr/bin/env python3
"""
Substrate Control Layer v1 — smoke test.

Validates the explicit, bounded execution bridge end-to-end without touching
hot-path or networking. Uses a temporary node_id namespace to keep the live
queue clean.
"""

from __future__ import annotations

import json
import sys
import uuid

sys.path.insert(0, "/opt/OS")

from umh.runtime_engine.substrate import control_bridge as cb  # noqa: E402
from umh.runtime_engine.substrate import control_commands as cc  # noqa: E402
from umh.runtime_engine.substrate import local_executor as lx  # noqa: E402

NODE = f"smoke-{uuid.uuid4().hex[:6]}"
FAILURES: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    status = "PASS" if cond else "FAIL"
    print(f"  [{status}] {name}{(' — ' + detail) if detail and not cond else ''}")
    if not cond:
        FAILURES.append(name)


def main() -> int:
    print(f"Control Layer v1 smoke test (node={NODE})")

    # 1. Command creation
    cmd = cc.make_command("run_shell", {"cmd": "echo hello"}, node_id=NODE)
    check("command_created", isinstance(cmd, cc.ControlCommand) and cmd.command_id.startswith("cmd_"))
    ok, reason = cc.validate(cmd)
    check("envelope_validates", ok, reason)

    # 2. Enqueue
    res = cb.send_command(cmd)
    check("command_enqueued", res.get("ok") is True, json.dumps(res))
    check("queue_depth_is_one", cb.queue_depth(NODE) == 1)

    # 3. Local executor processes pending — run_shell allowed
    drain = lx.process_pending(NODE)
    check("processed_one", drain.get("processed") == 1)
    first = (drain.get("results") or [{}])[0]
    check("run_shell_ok", first.get("ok") is True, json.dumps(first))
    check("run_shell_stdout_has_hello", "hello" in (first.get("stdout") or ""))
    check("queue_drained", cb.queue_depth(NODE) == 0)

    # 4. Blocked shell command rejected safely (not whitelisted)
    blocked = cc.make_command("run_shell", {"cmd": "rm -rf /"}, node_id=NODE)
    cb.send_command(blocked)
    drain2 = lx.process_pending(NODE)
    r = drain2["results"][0]
    check("blocked_shell_rejected", r.get("ok") is False and "shell_not_whitelisted" in (r.get("reason") or ""))

    # 5. write_file inside sandbox
    wf = cc.make_command(
        "write_file",
        {"path": "sandbox/smoke.txt", "content": "hello-sandbox"},
        node_id=NODE,
    )
    cb.send_command(wf)
    r = lx.process_pending(NODE)["results"][0]
    check("write_file_ok", r.get("ok") is True, json.dumps(r))
    check("write_file_inside_sandbox", "/.substrate_sandbox/" in (r.get("path") or ""))

    # 5b. Path escape attempt rejected
    escape = cc.make_command(
        "write_file",
        {"path": "../../../etc/evil.txt", "content": "x"},
        node_id=NODE,
    )
    cb.send_command(escape)
    r = lx.process_pending(NODE)["results"][0]
    check("path_escape_blocked", r.get("ok") is False and r.get("reason") in ("path_escape", "absolute_path_not_allowed"))

    # 6. run_python safe path
    rp = cc.make_command("run_python", {"code": "print(2+2)"}, node_id=NODE)
    cb.send_command(rp)
    r = lx.process_pending(NODE)["results"][0]
    check("run_python_ok", r.get("ok") is True and "4" in (r.get("stdout") or ""), json.dumps(r))

    # 6b. run_python forbidden token
    rp_bad = cc.make_command(
        "run_python", {"code": "import os\nprint(os.listdir('/'))"}, node_id=NODE
    )
    cb.send_command(rp_bad)
    r = lx.process_pending(NODE)["results"][0]
    check("run_python_blocks_import", r.get("ok") is False and "forbidden_token" in (r.get("reason") or ""))

    # 7. Queue bound enforcement
    for _ in range(cb.MAX_QUEUE_PER_NODE):
        cb.send_command(cc.make_command("run_shell", {"cmd": "pwd"}, node_id=NODE))
    overflow = cb.send_command(cc.make_command("run_shell", {"cmd": "pwd"}, node_id=NODE))
    check("queue_bounded", overflow.get("ok") is False and overflow.get("reason") == "queue_full")
    cb.clear_queue(NODE)
    check("queue_clear", cb.queue_depth(NODE) == 0)

    # 8. Malformed envelope handled
    bad = cc.ControlCommand(action="nuke_world", payload={}, issued_by="op", node_id=NODE)
    res_bad = cb.send_command(bad)
    check("malformed_rejected_at_bridge", res_bad.get("ok") is False)
    # Even if we could sneak it in, executor must refuse:
    r = lx.execute_command(bad)
    check("malformed_rejected_at_executor", r.get("ok") is False)

    # 9. Existing operator_interface still imports cleanly
    try:
        from umh.runtime_engine.substrate import operator_interface as oi  # noqa: F401
        check("operator_interface_unaffected", True)
    except Exception as e:  # noqa: BLE001
        check("operator_interface_unaffected", False, repr(e))

    print()
    if FAILURES:
        print(f"FAIL — {len(FAILURES)} check(s): {FAILURES}")
        return 1
    print("ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
