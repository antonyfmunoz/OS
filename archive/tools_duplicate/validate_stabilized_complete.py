"""
Live validation: premature-COMPLETE fix for Builder path.

Sends a multi-section report task to dex_builder_main, monitors
watcher events, captures logs, and reconstructs the timeline.

Usage:
    python3 /opt/OS/scripts/validate_stabilized_complete.py
"""
from __future__ import annotations

import json
import os
import sys
import time

sys.path.insert(0, "/opt/OS")

VALIDATION_PROMPT = (
    "Audit error handling patterns across all files in eos/substrate/ "
    "— read at least 12 files. Produce a structured report with these exact "
    "sections: 1) Executive Summary (3-4 sentences on overall error handling "
    "quality), 2) Findings (catalog every bare except, silent pass, missing "
    "logging, and untyped exception catch you find — cite file and line), "
    "3) Action Items (exactly 8 numbered items, each with file path, current "
    "problem, and specific fix), 4) Risk Assessment (rank the 3 worst "
    "offenders by production impact), 5) Next Steps (prioritized remediation "
    "plan with effort estimates per item). Be thorough and cite real code."
)


def _ts() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def main() -> None:
    from umh.substrate.claude_session_bridge import ask_session

    target = "vps"
    session = "dex_product_main"

    print(f"[validate] start: {_ts()}")
    print(f"[validate] prompt_len={len(VALIDATION_PROMPT)}")
    print(f"[validate] sending to {session}...")

    t0 = time.monotonic()
    result = ask_session(
        target,
        session,
        VALIDATION_PROMPT,
        poll_interval_s=2.0,
        max_polls=150,  # 5 min max
    )
    elapsed = time.monotonic() - t0

    ok = result.get("ok", False)
    reply = result.get("reply_text", "")
    watcher_used = result.get("watcher", False)

    print(f"\n[validate] done: {_ts()}")
    print(f"[validate] ok={ok}")
    print(f"[validate] watcher_used={watcher_used}")
    print(f"[validate] elapsed={elapsed:.1f}s")
    print(f"[validate] reply_len={len(reply)}")

    # Save full reply for comparison
    out_path = "/opt/OS/logs/validation_reply.txt"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        f.write(reply)
    print(f"[validate] reply saved to {out_path}")

    # Check expected structure
    checks = {
        "has_executive_summary": "executive summary" in reply.lower() or "summary" in reply.lower(),
        "has_findings": "finding" in reply.lower(),
        "has_action_items": "action item" in reply.lower() or "action items" in reply.lower(),
        "has_risk": "risk" in reply.lower(),
        "has_next_steps": "next step" in reply.lower(),
        "has_7plus_numbered": sum(1 for i in range(1, 10) if f"{i}." in reply or f"{i})" in reply) >= 7,
        "over_700_chars": len(reply) > 700,
    }
    print(f"\n[validate] structure checks:")
    for k, v in checks.items():
        status = "PASS" if v else "FAIL"
        print(f"  {status}: {k}")

    all_pass = all(checks.values())
    print(f"\n[validate] overall: {'PASS' if all_pass else 'FAIL'}")

    if not ok:
        print(f"[validate] FAILURE: ask_session returned ok=False")
        print(f"[validate] result: {json.dumps(result, indent=2, default=str)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
