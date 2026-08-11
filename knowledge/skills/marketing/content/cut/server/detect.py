"""Filler-word (A5) and silence (A6) detection — pure computation.

Both run over the word timestamps, synchronously, with no model call: this
is the deterministic spine of the editor. The UI turns each hit into a
pre-selected strike candidate the operator confirms.
"""

from __future__ import annotations

import re

DEFAULT_FILLERS = [
    "um",
    "uh",
    "like",
    "you know",
    "sort of",
    "kind of",
    "i mean",
    "basically",
    "actually",
    "literally",
]

DEFAULT_SILENCE_THRESHOLD = 1.0
SILENCE_PAD = 0.15
MIN_SILENCE_STRIKE = 0.05

_PUNCT = re.compile(r"[^\w']+", re.UNICODE)


def _norm(word: str) -> str:
    """Lowercase, strip punctuation — 'Um,' and 'um' are the same filler."""
    return _PUNCT.sub("", (word or "").strip().lower())


def find_fillers(words: list[dict], fillers: list[str] | None = None) -> list[dict]:
    """Match single- and multi-word fillers over the word stream.

    Multi-word phrases ("you know") are matched over a sliding window, and
    longer phrases win: "sort of" is reported once, never as "sort" + "of".
    """
    # Coerce every entry: a caller-supplied list may hold non-strings, and a
    # filler list is never worth a 500.
    phrases = [str(f).strip().lower() for f in (fillers or DEFAULT_FILLERS) if str(f).strip()]
    by_length = sorted(phrases, key=lambda p: len(p.split()), reverse=True)
    normed = [_norm(w.get("word", "")) for w in words]

    hits: list[dict] = []
    i = 0
    while i < len(words):
        matched = False
        for phrase in by_length:
            tokens = phrase.split()
            n = len(tokens)
            if i + n > len(words):
                continue
            if normed[i : i + n] == tokens:
                span = words[i : i + n]
                hits.append(
                    {
                        "seg": span[0].get("seg", 0),
                        "word": phrase,
                        "start": round(float(span[0]["start"]), 3),
                        "end": round(float(span[-1]["end"]), 3),
                        "text": " ".join((w.get("word") or "").strip() for w in span),
                    }
                )
                i += n
                matched = True
                break
        if not matched:
            i += 1
    return hits


def find_silences(words: list[dict], threshold: float = DEFAULT_SILENCE_THRESHOLD) -> list[dict]:
    """Report inter-word gaps longer than `threshold` seconds.

    Gaps are measured across segment boundaries — whisper's segmentation is
    a rendering detail, not a pause.
    """
    gaps: list[dict] = []
    for prev, nxt in zip(words, words[1:]):
        length = float(nxt["start"]) - float(prev["end"])
        if length > threshold:
            gaps.append(
                {
                    "after_word": (prev.get("word") or "").strip(),
                    "start": round(float(prev["end"]), 3),
                    "end": round(float(nxt["start"]), 3),
                    "length": round(length, 3),
                }
            )
    return gaps


def silence_strikes(gaps: list[dict], pad: float = SILENCE_PAD) -> list[dict]:
    """Convert gaps to strike ranges, keeping `pad` seconds of air each side."""
    strikes = []
    for g in gaps:
        start = float(g["start"]) + pad
        end = float(g["end"]) - pad
        if end - start > MIN_SILENCE_STRIKE:
            strikes.append({"start": round(start, 3), "end": round(end, 3)})
    return strikes


def apply_strikes(clips: list[dict], strikes: list[dict]) -> list[dict]:
    """Remove `strikes` from `clips` (A3, server side).

    Each strike either deletes a clip it covers, trims an edge, or splits a
    clip in two. Result is sorted, non-overlapping, and label-preserving.
    """
    result = [dict(c) for c in clips]
    for strike in sorted(strikes, key=lambda s: float(s["start"])):
        s_start, s_end = float(strike["start"]), float(strike["end"])
        if s_end <= s_start:
            continue
        next_round: list[dict] = []
        for clip in result:
            c_start, c_end = float(clip["start"]), float(clip["end"])
            if s_end <= c_start or s_start >= c_end:
                next_round.append(clip)  # no overlap
                continue
            if s_start <= c_start and s_end >= c_end:
                continue  # clip fully struck
            if s_start > c_start and s_end < c_end:  # split
                left = dict(clip)
                left["end"] = round(s_start, 3)
                right = dict(clip)
                right["start"] = round(s_end, 3)
                right["label"] = "%s_b" % clip.get("label", "clip")
                next_round.extend([left, right])
                continue
            trimmed = dict(clip)
            if s_start <= c_start:
                trimmed["start"] = round(s_end, 3)
            else:
                trimmed["end"] = round(s_start, 3)
            if float(trimmed["end"]) - float(trimmed["start"]) > 0.01:
                next_round.append(trimmed)
        result = next_round
    result.sort(key=lambda c: float(c["start"]))
    return result
