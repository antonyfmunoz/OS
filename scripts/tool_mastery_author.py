#!/usr/bin/env python3
"""Tool Mastery author dispatcher.

Thin shim that runs the Tool Mastery Author Agent against a research
artifact. This script is the target of `tool_mastery.author` actions
queued by the Research Agent through the Control Plane.

Two modes:

    1. Direct invocation
        python3 scripts/tool_mastery_author.py \\
            --tool stitch \\
            --artifact /opt/OS/logs/tool_mastery_research/stitch/<stamp>/research_artifact.json

    2. Action-file consumption (used by the dispatcher when draining
       the deferred queue)
        python3 scripts/tool_mastery_author.py \\
            --consume-action /opt/OS/logs/deferred/<id>.json

Exit codes:
    0 — author run succeeded (READY or PARTIAL)
    1 — author run failed (verifier failed or no sources)
    2 — bad invocation
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, "/opt/OS")

from core.tool_mastery_author_agent.agent import author  # noqa: E402
from core.tool_mastery_author_agent.models import AuthorRequest, AuthorStatus  # noqa: E402


def _run(
    tool: str, artifact: Path, *, force_rewrite: bool, allow_scaffold: bool
) -> int:
    if not artifact.is_file():
        print(f"error: artifact not found: {artifact}", file=sys.stderr)
        return 2
    request = AuthorRequest(
        tool_slug=tool,
        artifact_path=str(artifact),
        allow_scaffold=allow_scaffold,
        force_rewrite=force_rewrite,
    )
    result = author(request)
    payload = result.to_dict()
    print(json.dumps(payload, indent=2))
    ok_states = {
        AuthorStatus.AUTHORED_READY.value,
        AuthorStatus.AUTHORED_PARTIAL.value,
    }
    return 0 if result.status.value in ok_states else 1


def _consume_action(path: Path) -> int:
    if not path.is_file():
        print(f"error: action file not found: {path}", file=sys.stderr)
        return 2
    payload = json.loads(path.read_text(encoding="utf-8"))
    action = payload.get("action", payload)
    inputs = action.get("inputs", {})
    tool = inputs.get("tool")
    artifact_path = inputs.get("artifact_path")
    if not tool or not artifact_path:
        print(
            f"error: action {path} missing inputs.tool or inputs.artifact_path",
            file=sys.stderr,
        )
        return 2
    return _run(
        tool=tool,
        artifact=Path(artifact_path),
        force_rewrite=bool(inputs.get("force_rewrite", False)),
        allow_scaffold=bool(inputs.get("allow_scaffold", True)),
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--tool", help="tool slug (snake_case)")
    ap.add_argument("--artifact", type=Path, help="path to research_artifact.json")
    ap.add_argument(
        "--consume-action",
        type=Path,
        help="path to a Control Plane action JSON file (deferred queue entry)",
    )
    ap.add_argument(
        "--force-rewrite",
        action="store_true",
        help="overwrite existing human-authored skill files (destructive)",
    )
    ap.add_argument(
        "--no-scaffold",
        action="store_true",
        help="refuse to create a new skill if one does not exist",
    )
    args = ap.parse_args(argv)

    if args.consume_action:
        return _consume_action(args.consume_action)

    if not args.tool or not args.artifact:
        print(
            "error: either --consume-action or both --tool and --artifact are required",
            file=sys.stderr,
        )
        return 2

    return _run(
        tool=args.tool,
        artifact=args.artifact,
        force_rewrite=args.force_rewrite,
        allow_scaffold=not args.no_scaffold,
    )


if __name__ == "__main__":
    sys.exit(main())
