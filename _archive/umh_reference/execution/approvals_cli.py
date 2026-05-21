"""UMH Execution Approvals CLI — human-operable approval control surface.

Usage:
    python3 -m umh.execution.approvals list
    python3 -m umh.execution.approvals show <approval_id>
    python3 -m umh.execution.approvals approve <approval_id>
    python3 -m umh.execution.approvals deny <approval_id>
    python3 -m umh.execution.approvals --json list

Only changes approval state. Never executes the underlying mutation.
"""

from __future__ import annotations

import json
import sys

sys.path.insert(0, "/opt/OS")

from umh.execution.approval import ApprovalStatus, get_approval_store


def _format_approval(req) -> str:
    """Format a single approval for human-readable output."""
    expired_marker = " [EXPIRED]" if req.is_expired() else ""
    return (
        f"  {req.id}\n"
        f"    operation:   {req.operation}\n"
        f"    capability:  {req.capability_type}\n"
        f"    risk:        {req.risk_level}\n"
        f"    status:      {req.status.value}{expired_marker}\n"
        f"    created_at:  {req.created_at}\n"
        f"    expires_at:  {req.expires_at}\n"
        f"    inputs:      {req.inputs_summary or '(none)'}"
    )


def cmd_list(as_json: bool = False) -> int:
    """List all approvals."""
    store = get_approval_store()
    approvals = store.list_all()

    if as_json:
        print(json.dumps([r.to_dict() for r in approvals], indent=2))
        return 0

    if not approvals:
        print("No approvals found.")
        return 0

    print(f"Approvals ({len(approvals)}):")
    print("-" * 50)
    for req in approvals:
        print(_format_approval(req))
        print()
    return 0


def cmd_show(approval_id: str, as_json: bool = False) -> int:
    """Show details of a specific approval."""
    store = get_approval_store()
    req = store.get(approval_id)

    if req is None:
        msg = f"Approval not found: {approval_id}"
        if as_json:
            print(json.dumps({"error": msg}))
        else:
            print(f"ERROR: {msg}")
        return 1

    if as_json:
        print(json.dumps(req.to_dict(), indent=2))
    else:
        print(_format_approval(req))
    return 0


def cmd_approve(approval_id: str, as_json: bool = False) -> int:
    """Approve a pending approval request."""
    store = get_approval_store()
    req = store.get(approval_id)

    if req is None:
        msg = f"Approval not found: {approval_id}"
        if as_json:
            print(json.dumps({"error": msg}))
        else:
            print(f"ERROR: {msg}")
        return 1

    if req.is_expired():
        req.status = ApprovalStatus.EXPIRED
        msg = f"Cannot approve: {approval_id} has expired"
        if as_json:
            print(json.dumps({"error": msg, "status": "expired"}))
        else:
            print(f"ERROR: {msg}")
        return 1

    if req.status != ApprovalStatus.PENDING:
        msg = f"Cannot approve: {approval_id} status is {req.status.value}"
        if as_json:
            print(json.dumps({"error": msg, "status": req.status.value}))
        else:
            print(f"ERROR: {msg}")
        return 1

    result = store.approve(approval_id)
    if result is None:
        msg = f"Approval not found: {approval_id}"
        if as_json:
            print(json.dumps({"error": msg}))
        else:
            print(f"ERROR: {msg}")
        return 1

    if result.status == ApprovalStatus.EXPIRED:
        msg = f"Cannot approve: {approval_id} expired during approval"
        if as_json:
            print(json.dumps({"error": msg, "status": "expired"}))
        else:
            print(f"ERROR: {msg}")
        return 1

    if as_json:
        print(json.dumps({"approved": approval_id, "status": "approved"}))
    else:
        print(f"APPROVED: {approval_id}")
        print(f"  operation: {result.operation}")
        print(f"  capability: {result.capability_type}")
    return 0


def cmd_deny(approval_id: str, as_json: bool = False) -> int:
    """Deny a pending approval request."""
    store = get_approval_store()
    req = store.get(approval_id)

    if req is None:
        msg = f"Approval not found: {approval_id}"
        if as_json:
            print(json.dumps({"error": msg}))
        else:
            print(f"ERROR: {msg}")
        return 1

    if req.status == ApprovalStatus.CONSUMED:
        msg = f"Cannot deny: {approval_id} already consumed"
        if as_json:
            print(json.dumps({"error": msg, "status": "consumed"}))
        else:
            print(f"ERROR: {msg}")
        return 1

    result = store.deny(approval_id)
    if result is None:
        msg = f"Approval not found: {approval_id}"
        if as_json:
            print(json.dumps({"error": msg}))
        else:
            print(f"ERROR: {msg}")
        return 1

    if as_json:
        print(json.dumps({"denied": approval_id, "status": "denied"}))
    else:
        print(f"DENIED: {approval_id}")
        print(f"  operation: {result.operation}")
        print(f"  capability: {result.capability_type}")
    return 0


USAGE = """Usage: python3 -m umh.execution.approvals <command> [args]

Commands:
  list                   List all approvals
  show <approval_id>     Show details of a specific approval
  approve <approval_id>  Approve a pending approval
  deny <approval_id>     Deny a pending approval

Options:
  --json                 Output in JSON format
"""


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    args = argv if argv is not None else sys.argv[1:]

    as_json = "--json" in args
    args = [a for a in args if a != "--json"]

    if not args:
        print(USAGE)
        return 1

    command = args[0]

    if command == "list":
        return cmd_list(as_json=as_json)
    elif command == "show":
        if len(args) < 2:
            print("ERROR: show requires an approval_id")
            return 1
        return cmd_show(args[1], as_json=as_json)
    elif command == "approve":
        if len(args) < 2:
            print("ERROR: approve requires an approval_id")
            return 1
        return cmd_approve(args[1], as_json=as_json)
    elif command == "deny":
        if len(args) < 2:
            print("ERROR: deny requires an approval_id")
            return 1
        return cmd_deny(args[1], as_json=as_json)
    else:
        print(f"ERROR: Unknown command: {command}")
        print(USAGE)
        return 1


if __name__ == "__main__":
    sys.exit(main())
