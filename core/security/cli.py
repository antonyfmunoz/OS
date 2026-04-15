"""
cli.py — Operator CLI for the EOS security layer.

Usage
-----
    python3 -m core.security.cli user create <id> --role operator
    python3 -m core.security.cli user list
    python3 -m core.security.cli user disable <id>
    python3 -m core.security.cli user auth <id> --key <api_key>
    python3 -m core.security.cli role list
    python3 -m core.security.cli approval list
    python3 -m core.security.cli approval show <request_id>
    python3 -m core.security.cli approval approve <request_id> --token <token>
    python3 -m core.security.cli approval reject  <request_id> --token <token>
    python3 -m core.security.cli audit tail --limit 20
    python3 -m core.security.cli audit verify
    python3 -m core.security.cli env show [prod|sandbox|dev]

This CLI is the operator's interface to the security subsystem. It's
deliberately thin — every command maps to one call on one of the
security submodules.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, "/opt/OS")

from core.security.approval import ApprovalQueue
from core.security.audit import AuditLog
from core.security.context import SecurityContext
from core.security.environments import env_for_name
from core.security.identity import AuthError, IdentityStore
from core.security.rbac import RBACEngine, RoleName


# ─── Users ──────────────────────────────────────────────────────────────────


def cmd_user_create(args: argparse.Namespace) -> int:
    store = IdentityStore()
    try:
        user, raw_key = store.create_user(
            user_id=args.user_id,
            role=args.role,
            display_name=args.display or args.user_id,
        )
    except ValueError as exc:
        print(f"error: {exc}")
        return 1
    print(f"created user {user.user_id} (role={user.role})")
    print(f"api_key: {raw_key}")
    print("save this — it will not be shown again")
    return 0


def cmd_user_list(_: argparse.Namespace) -> int:
    store = IdentityStore()
    users = store.list_users()
    if not users:
        print("(no users)")
        return 0
    for u in users:
        flag = " [disabled]" if u.disabled else ""
        print(f"{u.user_id:20} {u.role:10} {u.display_name}{flag}")
    return 0


def cmd_user_disable(args: argparse.Namespace) -> int:
    store = IdentityStore()
    try:
        u = store.disable_user(args.user_id)
    except KeyError as exc:
        print(f"error: {exc}")
        return 1
    print(f"disabled {u.user_id}")
    return 0


def cmd_user_role(args: argparse.Namespace) -> int:
    store = IdentityStore()
    try:
        u = store.assign_role(args.user_id, args.role)
    except KeyError as exc:
        print(f"error: {exc}")
        return 1
    print(f"{u.user_id} → role={u.role}")
    return 0


def cmd_user_auth(args: argparse.Namespace) -> int:
    store = IdentityStore()
    try:
        token = store.authenticate(args.user_id, args.key)
    except AuthError as exc:
        print(f"auth failed: {exc}")
        return 1
    print(token.raw)
    return 0


# ─── Roles ──────────────────────────────────────────────────────────────────


def cmd_role_list(_: argparse.Namespace) -> int:
    engine = RBACEngine()
    for role in engine.list_roles():
        print(json.dumps(role.as_dict(), indent=2))
    return 0


# ─── Approvals ──────────────────────────────────────────────────────────────


def cmd_approval_list(_: argparse.Namespace) -> int:
    q = ApprovalQueue()
    pending = q.list_pending()
    if not pending:
        print("(no pending approvals)")
        return 0
    for req in pending:
        print(
            f"{req.request_id}  {req.risk:8}  {req.action_type:12}  "
            f"{req.target:40}  requester={req.requester}"
        )
    return 0


def cmd_approval_show(args: argparse.Namespace) -> int:
    q = ApprovalQueue()
    req = q.get(args.request_id)
    if req is None:
        print(f"no such request: {args.request_id}")
        return 1
    print(json.dumps(req.as_dict(), indent=2))
    return 0


def cmd_approval_approve(args: argparse.Namespace) -> int:
    sec = SecurityContext.default()
    try:
        decided = sec.approve(
            approver_token=args.token,
            request_id=args.request_id,
            reason=args.reason or "",
        )
    except Exception as exc:
        print(f"error: {exc}")
        return 1
    print(f"approved {decided.request_id} by {decided.approver}")
    return 0


def cmd_approval_reject(args: argparse.Namespace) -> int:
    sec = SecurityContext.default()
    try:
        decided = sec.reject(
            approver_token=args.token,
            request_id=args.request_id,
            reason=args.reason or "",
        )
    except Exception as exc:
        print(f"error: {exc}")
        return 1
    print(f"rejected {decided.request_id} by {decided.approver}")
    return 0


# ─── Audit ──────────────────────────────────────────────────────────────────


def cmd_audit_tail(args: argparse.Namespace) -> int:
    log = AuditLog()
    events = log.tail(args.limit)
    for ev in events:
        line = (
            f"{ev.timestamp}  {ev.outcome:8}  {ev.action:20}  "
            f"{ev.user or '-':15}  {ev.target[:50]}"
        )
        print(line)
    return 0


def cmd_audit_verify(_: argparse.Namespace) -> int:
    log = AuditLog()
    ok, detail = log.verify_chain()
    print(("OK  " if ok else "FAIL ") + detail)
    return 0 if ok else 1


# ─── Env ────────────────────────────────────────────────────────────────────


def cmd_env_show(args: argparse.Namespace) -> int:
    sec_env = env_for_name(args.tier or "prod")
    print(json.dumps(sec_env.to_dict(), indent=2))
    return 0


# ─── Parser ─────────────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python3 -m core.security.cli")
    sub = p.add_subparsers(dest="group", required=True)

    # user
    user = sub.add_parser("user").add_subparsers(dest="cmd", required=True)
    uc = user.add_parser("create")
    uc.add_argument("user_id")
    uc.add_argument("--role", required=True, choices=[r.value for r in RoleName])
    uc.add_argument("--display", default="")
    uc.set_defaults(func=cmd_user_create)

    ul = user.add_parser("list")
    ul.set_defaults(func=cmd_user_list)

    ud = user.add_parser("disable")
    ud.add_argument("user_id")
    ud.set_defaults(func=cmd_user_disable)

    ur = user.add_parser("role")
    ur.add_argument("user_id")
    ur.add_argument("--role", required=True, choices=[r.value for r in RoleName])
    ur.set_defaults(func=cmd_user_role)

    ua = user.add_parser("auth")
    ua.add_argument("user_id")
    ua.add_argument("--key", required=True)
    ua.set_defaults(func=cmd_user_auth)

    # role
    role = sub.add_parser("role").add_subparsers(dest="cmd", required=True)
    role_list = role.add_parser("list")
    role_list.set_defaults(func=cmd_role_list)

    # approval
    approval = sub.add_parser("approval").add_subparsers(dest="cmd", required=True)
    al = approval.add_parser("list")
    al.set_defaults(func=cmd_approval_list)

    as_ = approval.add_parser("show")
    as_.add_argument("request_id")
    as_.set_defaults(func=cmd_approval_show)

    ap = approval.add_parser("approve")
    ap.add_argument("request_id")
    ap.add_argument("--token", required=True)
    ap.add_argument("--reason", default="")
    ap.set_defaults(func=cmd_approval_approve)

    ar = approval.add_parser("reject")
    ar.add_argument("request_id")
    ar.add_argument("--token", required=True)
    ar.add_argument("--reason", default="")
    ar.set_defaults(func=cmd_approval_reject)

    # audit
    audit = sub.add_parser("audit").add_subparsers(dest="cmd", required=True)
    at = audit.add_parser("tail")
    at.add_argument("--limit", type=int, default=50)
    at.set_defaults(func=cmd_audit_tail)

    av = audit.add_parser("verify")
    av.set_defaults(func=cmd_audit_verify)

    # env
    envp = sub.add_parser("env").add_subparsers(dest="cmd", required=True)
    es = envp.add_parser("show")
    es.add_argument("tier", nargs="?", default="prod")
    es.set_defaults(func=cmd_env_show)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
