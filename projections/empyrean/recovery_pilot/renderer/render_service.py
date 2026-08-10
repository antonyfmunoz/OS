"""C0 — the Link Principle renderer: token -> record -> template -> surface.

Build ONCE, reuse everywhere: Pipeline Snapshot, Job Pipeline Audit,
onboarding, scoreboard, candidate intake, operator compact.

TEST MODE: records come from a local record store (JSON files under
data/records/); rendered surfaces land in data/output/. In production the
record lookup swaps to the Notion runtime — same interface.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from . import link_tokens

_ROOT = Path(os.environ.get("UMH_ROOT", "/opt/OS")) / "projections/empyrean/recovery_pilot"
RECORD_STORE = _ROOT / "data" / "records"
OUTPUT_DIR = _ROOT / "data" / "output"

# template key -> renderer callable registered by generators at import time
_TEMPLATES: dict = {}


def register_template(kind: str, render_fn) -> None:
    """Generators register their render function under a record 'kind'."""
    _TEMPLATES[kind] = render_fn


def put_record(record_ref: str, kind: str, data: dict) -> None:
    """Store a record the renderer can serve (test-mode local store)."""
    RECORD_STORE.mkdir(parents=True, exist_ok=True)
    with open(RECORD_STORE / ("%s.json" % record_ref), "w") as f:
        json.dump({"kind": kind, "data": data}, f, indent=1, default=str)


def get_record(record_ref: str) -> dict | None:
    path = RECORD_STORE / ("%s.json" % record_ref)
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def render_for_token(token: str) -> Path | None:
    """The full C0 pipeline: token -> record lookup -> template -> surface.

    Returns the path of the rendered HTML file, or None (invalid token,
    missing record, or unregistered template — each distinctly journaled
    by the layers involved).
    """
    record_ref = link_tokens.resolve(token)
    if record_ref is None:
        return None
    record = get_record(record_ref)
    if record is None:
        return None
    render_fn = _TEMPLATES.get(record["kind"])
    if render_fn is None:
        return None
    html = render_fn(record["data"])
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUTPUT_DIR / ("%s.html" % record_ref)
    out.write_text(html)
    return out
