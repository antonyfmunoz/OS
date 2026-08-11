"""EDL — the edit decision list. THE contract of the cut system.

Everything speaks EDL: Claude writes one from a transcript, the Phase 2 UI
edits one on a timeline, the cutter executes one with ffmpeg. An edit is a
text file — versionable, diffable, regenerable.

Schema (JSON):
{
  "version": 1,
  "source": "path or beast path of the source video",
  "clips": [ {"start": 12.4, "end": 31.9, "label": "hook"} , ... ],  # kept, in order
  "captions": true,            # burn word captions from the transcript
  "vertical": false,           # 9:16 center crop for shorts
  "output": "clip_01.mp4"
}
"""
from __future__ import annotations

import json
from pathlib import Path

SCHEMA_VERSION = 1


class EDLError(ValueError):
    pass


def validate(edl: dict) -> dict:
    """Validate an EDL dict. Returns it normalized; raises EDLError."""
    if edl.get("version") != SCHEMA_VERSION:
        raise EDLError("unsupported EDL version %r" % edl.get("version"))
    if not edl.get("source"):
        raise EDLError("source required")
    clips = edl.get("clips")
    if not clips or not isinstance(clips, list):
        raise EDLError("clips must be a non-empty list")
    prev_end = None
    for i, c in enumerate(clips):
        try:
            start, end = float(c["start"]), float(c["end"])
        except (KeyError, TypeError, ValueError):
            raise EDLError("clip %d needs numeric start/end" % i)
        if end <= start:
            raise EDLError("clip %d: end (%s) must be > start (%s)" % (i, end, start))
        c["start"], c["end"] = start, end
        c.setdefault("label", "clip%02d" % i)
        prev_end = end
    edl.setdefault("captions", False)
    edl.setdefault("vertical", False)
    edl.setdefault("output", "cut_output.mp4")
    if "/" in edl["output"] or "\\" in edl["output"]:
        raise EDLError("output must be a bare filename")
    return edl


def load(path: str | Path) -> dict:
    with open(path) as f:
        return validate(json.load(f))


def duration(edl: dict) -> float:
    return round(sum(c["end"] - c["start"] for c in edl["clips"]), 3)
