"""AI edit + highlight selection (D7, A7).

`call_with_fallback` is the MODULE-level router entry point — imported
directly rather than through substrate.sockets.intelligence_port, which
returns None when no adapter is registered. The router never raises and
never returns None; when every provider is down it returns a typed result
whose provider is "deterministic" (or model "circuit_breaker"). That is the
degradation signal — checking `not result.output` would be dead code.

Both entry points are non-destructive: they return a PROPOSED EDL and a
note. Saving is the caller's decision (and the UI's Apply button).
"""

from __future__ import annotations

import json
import logging
import re

from adapters.models.model_router import call_with_fallback

logger = logging.getLogger("cutstudio.ai")

DEGRADED_NOTE = "editor model unavailable — edit manually"

MAX_SEGMENTS = 400

EDIT_SYSTEM = (
    "You revise a video edit decision list (EDL) from a transcript. "
    'Return ONLY JSON: {"clips":[{"start":<seconds>,"end":<seconds>,'
    '"label":"short-name"}],"note":"one sentence"}. '
    "Times must come from the provided transcript timestamps and stay inside "
    "the media duration. Keep clips in chronological order. Never invent "
    "timestamps."
)

HIGHLIGHTS_SYSTEM = (
    "You select the strongest short-clip candidates from a transcript. "
    'Return ONLY JSON: {"candidates":[{"start":<seconds>,"end":<seconds>,'
    '"hook_line":"...","reason":"...","score":{"hook":0-99,'
    '"flow":0-99,"value":0-99,"overall":0-99}}]} with times from the '
    "provided word timestamps, each clip 20-<target> seconds, a self-contained "
    "thought, and a strong first line. Never invent timestamps."
)


def is_degraded(result) -> bool:
    """True when the router produced a fallback rather than a real answer."""
    return (
        getattr(result, "provider", "") == "deterministic"
        or getattr(result, "model", "") == "circuit_breaker"
    )


def compact_transcript(transcript: dict, limit: int = MAX_SEGMENTS) -> str:
    """Segments as `[start-end] text` lines — compact enough for a long VOD."""
    lines = []
    for seg in (transcript.get("segments") or [])[:limit]:
        text = (seg.get("text") or "").strip()
        if text:
            lines.append("[%.2f-%.2f] %s" % (seg.get("start", 0), seg.get("end", 0), text))
    return "\n".join(lines)


def _extract_json(text: str) -> dict | None:
    """Pull the first JSON object out of a model response."""
    if not text:
        return None
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    candidate = fenced.group(1) if fenced else None
    if candidate is None:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            return None
        candidate = text[start : end + 1]
    try:
        parsed = json.loads(candidate)
        return parsed if isinstance(parsed, dict) else None
    except ValueError:
        return None


def _clamp_clips(clips, duration: float) -> list[dict]:
    """Coerce model output into valid, ordered, in-bounds clips."""
    out = []
    for i, c in enumerate(clips or []):
        try:
            start = max(0.0, float(c["start"]))
            end = min(float(duration), float(c["end"]))
        except (KeyError, TypeError, ValueError):
            continue
        if end - start <= 0.05:
            continue
        out.append(
            {
                "start": round(start, 3),
                "end": round(end, 3),
                "label": str(c.get("label") or "clip%02d" % i)[:60],
            }
        )
    out.sort(key=lambda c: c["start"])
    return out


def revise_edl(edl: dict, transcript: dict, instruction: str, duration: float) -> dict:
    """Ask the router for a revised EDL. Returns {edl, note} — never saves."""
    prompt = (
        "TRANSCRIPT (seconds):\n%s\n\nCURRENT EDL CLIPS:\n%s\n\n"
        "MEDIA DURATION: %.2f seconds\n\nINSTRUCTION: %s"
        % (
            compact_transcript(transcript),
            json.dumps(edl.get("clips") or [], indent=0),
            duration,
            instruction,
        )
    )
    result = call_with_fallback(prompt=prompt, system=EDIT_SYSTEM, task_type="analysis")
    if is_degraded(result):
        logger.info("ai edit degraded: provider=%s model=%s", result.provider, result.model)
        return {"edl": edl, "note": DEGRADED_NOTE}

    parsed = _extract_json(result.output or "")
    if not parsed:
        return {"edl": edl, "note": "could not parse the editor response — edit manually"}

    clips = _clamp_clips(parsed.get("clips"), duration)
    if not clips:
        return {"edl": edl, "note": "the editor proposed no usable clips"}

    proposed = dict(edl)
    proposed["clips"] = clips
    return {"edl": proposed, "note": str(parsed.get("note") or "")[:400]}


def _overlap(a: dict, b: dict) -> float:
    """Overlap of two candidates as a fraction of the shorter one."""
    lo = max(a["start"], b["start"])
    hi = min(a["end"], b["end"])
    if hi <= lo:
        return 0.0
    shorter = min(a["end"] - a["start"], b["end"] - b["start"])
    return (hi - lo) / shorter if shorter > 0 else 0.0


def find_highlights(
    transcript: dict, duration: float, count: int = 4, target_seconds: float = 45.0
) -> dict:
    """Rank short-clip candidates (A7). Returns {candidates, note}."""
    prompt = (
        "TRANSCRIPT (seconds):\n%s\n\nMEDIA DURATION: %.2f seconds\n"
        "count: %d\ntarget_seconds: %.0f"
        % (compact_transcript(transcript), duration, count, target_seconds)
    )
    result = call_with_fallback(prompt=prompt, system=HIGHLIGHTS_SYSTEM, task_type="analysis")
    if is_degraded(result):
        logger.info("highlights degraded: provider=%s", result.provider)
        return {"candidates": [], "note": DEGRADED_NOTE}

    parsed = _extract_json(result.output or "")
    if not parsed:
        return {"candidates": [], "note": "could not parse the highlight response"}

    candidates: list[dict] = []
    for c in parsed.get("candidates") or []:
        try:
            start = max(0.0, float(c["start"]))
            end = min(float(duration), float(c["end"]))
        except (KeyError, TypeError, ValueError):
            continue
        if end - start < 5.0:  # too short to be a clip
            continue
        raw_score = c.get("score") if isinstance(c.get("score"), dict) else {}
        score = {}
        for axis in ("hook", "flow", "value", "overall"):
            try:
                score[axis] = max(0, min(99, int(float(raw_score.get(axis, 0)))))
            except (TypeError, ValueError):
                score[axis] = 0
        candidates.append(
            {
                "start": round(start, 3),
                "end": round(end, 3),
                "hook_line": str(c.get("hook_line") or "")[:200],
                "reason": str(c.get("reason") or "")[:400],
                "score": score,
            }
        )

    candidates.sort(key=lambda c: c["score"]["overall"], reverse=True)
    kept: list[dict] = []
    for cand in candidates:  # drop >50% overlaps, best-scoring wins
        if all(_overlap(cand, k) <= 0.5 for k in kept):
            kept.append(cand)
    return {"candidates": kept[: max(1, count)], "note": ""}
