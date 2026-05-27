"""
Completion Claim Verifier — runs at Stop hook.

Checks if the session's last output contains completion claims
(100%, exhaustive, complete, done, all files) and validates them
against filesystem ground truth.

This exists because AFM had to ask 5 times for a truly complete
audit on 2026-05-27. Memory rules weren't enough. This is the
mechanical gate.
"""

import json
import os
import subprocess
import sys


COMPLETION_SIGNALS = [
    "100%",
    "exhaustive",
    "every file",
    "every directory",
    "all files",
    "complete audit",
    "complete inventory",
    "full coverage",
    "fully covered",
    "zero gaps",
]

COUNT_KEYWORDS = [
    "total files",
    "grand total",
    "file count",
    "files across",
]


def get_file_count(path: str = "/opt/OS") -> int:
    """Ground truth file count via find."""
    excludes = [
        "-not", "-path", "*/.git/*",
        "-not", "-path", "*/node_modules/*",
        "-not", "-path", "*/__pycache__/*",
        "-not", "-path", "*/.mypy_cache/*",
        "-not", "-path", "*/.ruff_cache/*",
        "-not", "-path", "*/.pytest_cache/*",
    ]
    cmd = ["find", path, "-type", "f"] + excludes
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return len(result.stdout.strip().split("\n"))


def main():
    """Check if completion claim needs verification warning."""
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            sys.exit(0)

        data = json.loads(raw)
        transcript = data.get("transcript_summary", "") or data.get("stop_reason", "")

        has_completion_claim = any(
            sig.lower() in transcript.lower() for sig in COMPLETION_SIGNALS
        )
        has_count_claim = any(
            kw.lower() in transcript.lower() for kw in COUNT_KEYWORDS
        )

        if has_completion_claim or has_count_claim:
            actual = get_file_count()
            print(
                f"[Verify] Completion claim detected. "
                f"Ground truth: {actual:,} files in /opt/OS. "
                f"If your reported total differs, the claim is wrong.",
                file=sys.stderr,
            )

    except Exception as e:
        print(f"[Verify] hook error (non-blocking): {e}", file=sys.stderr)

    sys.exit(0)


if __name__ == "__main__":
    main()
