#!/usr/bin/env python3
"""
Stop hook: auto-dispatch a report to cockpit chat and Discord
when a Claude Code session completes work.

Reads recent git commits on the current branch to build a summary.
Only dispatches if the session actually produced commits (not a
read-only or conversational session).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))

REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")


def _detect_git_dir() -> str:
    """Use the actual working directory for git commands — handles worktrees."""
    cwd = os.getcwd()
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5, cwd=cwd,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass
    return REPO_ROOT


_GIT_DIR = _detect_git_dir()


def _git(args: list[str]) -> str:
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            timeout=10,
            cwd=_GIT_DIR,
        )
        return result.stdout.strip()
    except Exception:
        return ""


def _recent_session_commits(minutes: int = 30) -> list[dict[str, str]]:
    since = f"{minutes} minutes ago"
    log = _git([
        "log",
        f"--since={since}",
        "--format=%H|%s|%an",
        "--no-merges",
    ])
    if not log:
        return []
    commits = []
    for line in log.strip().split("\n"):
        parts = line.split("|", 2)
        if len(parts) == 3:
            commits.append({
                "hash": parts[0][:8],
                "message": parts[1],
                "author": parts[2],
            })
    return commits


def _extract_metadata(commits: list[dict[str, str]]) -> dict[str, str]:
    meta: dict[str, str] = {}
    for c in commits:
        msg = c["message"].lower()
        if "phase" in msg:
            for word in c["message"].split():
                if word.replace(".", "").replace(":", "").replace(",", "").isdigit() or \
                   (word.count(".") == 1 and all(p.isdigit() for p in word.split("."))):
                    meta["phase"] = word.rstrip(":,")
                    break
        if "pr #" in msg or "pr#" in msg:
            for word in c["message"].split():
                stripped = word.lstrip("#").rstrip(",:.)")
                if stripped.isdigit():
                    meta["pr"] = stripped
                    break
    return meta


def _find_audit_file(commits: list[dict[str, str]]) -> str | None:
    for c in commits:
        diff = _git(["diff-tree", "--no-commit-id", "-r", "--name-only", c["hash"]])
        for f in diff.split("\n"):
            if f.startswith("docs/audits/") and f.endswith(".md"):
                full = os.path.join(_GIT_DIR, f)
                if os.path.isfile(full):
                    return full
    return None


def dispatch() -> bool:
    commits = _recent_session_commits(minutes=30)
    if not commits:
        return False

    ai_commits = [c for c in commits if "Claude" in c.get("author", "")]
    if not ai_commits:
        ai_commits = commits

    title_commit = ai_commits[0]["message"]
    if len(title_commit) > 80:
        title_commit = title_commit[:77] + "..."

    summary_lines = []
    for c in ai_commits[:10]:
        summary_lines.append(f"- `{c['hash']}` {c['message']}")
    summary = "\n".join(summary_lines)

    file_count = 0
    stat = _git(["diff", "--stat", f"HEAD~{len(ai_commits)}", "HEAD"])
    if stat:
        last_line = stat.strip().split("\n")[-1]
        summary += f"\n\n{last_line}"
        for word in last_line.split():
            if word.isdigit():
                file_count = int(word)
                break

    meta = _extract_metadata(ai_commits)
    audit_file = _find_audit_file(ai_commits)

    from substrate.organism.report_dispatcher import Report, ReportDispatcher

    report = Report(
        title=title_commit,
        summary=summary,
        body=f"{len(ai_commits)} commits, {file_count} files changed",
        file_path=audit_file,
        metadata=meta,
    )
    dispatcher = ReportDispatcher()
    result = dispatcher.dispatch_report(report)
    return result.cockpit_sent


def main() -> None:
    try:
        dispatched = dispatch()
        if dispatched:
            print("[AutoReport] Report dispatched to cockpit + Discord", file=sys.stderr)
        else:
            print("[AutoReport] No commits to report", file=sys.stderr)
    except Exception as e:
        print(f"[AutoReport] Failed: {e}", file=sys.stderr)
    sys.exit(0)


if __name__ == "__main__":
    main()
