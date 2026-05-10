"""
TTS reply sanitization — strip Claude Code / provider footer noise.

Purpose
-------
Claude Code tmux sessions (and legacy provider responses) sometimes append
metadata that is useful in a chat transcript but WRONG to speak aloud:

  - provider/model name lines          ("gemini-2.5-flash • 1,240 tok")
  - token / cost stats                 ("Tokens: 1.2k  Cost: $0.003")
  - skill footer blocks                ("★ Insight ─── ... ────")
  - separator bars                     ("───────────────")
  - signature tails                    ("— DEX", "— EOS")

`sanitize_tts_reply` returns ONLY the spoken body. It is:

  - pure (no I/O, no imports from hot-path)
  - bounded in length
  - safe on malformed input (never raises)
  - idempotent

Used by the Discord pseudo-live path to produce `spoken_text` that feeds a
Discord message sent with `tts=True`. The un-sanitized reply may still be
shown in chat as `display_text`, but TTS speaks ONLY the sanitized body.
"""

from __future__ import annotations

import re

# Max spoken body length — TTS should be short; Discord's soft cap is 2000
# but spoken replies beyond ~1200 chars are painful. Bounded here.
_DEFAULT_MAX_CHARS = 1200

# Patterns that identify a "this line is footer / meta noise, drop it".
# Each is applied per-line, case-insensitive.
_LINE_DROP_PATTERNS: tuple[re.Pattern[str], ...] = (
    # Separator bars: ── ─── ━━ ═══ ---- ____ **** (3+ of the same char)
    re.compile(r"^\s*[─━═\-_*=·•]{3,}\s*$"),
    # Skill/insight footer sentinels
    re.compile(r"^\s*[★☆✦✧✪✯✰]+\s*insight", re.IGNORECASE),
    re.compile(r"^\s*insight\s*[─━=\-]{3,}", re.IGNORECASE),
    # Provider / model badges
    re.compile(r"^\s*(provider|model)\s*[:=]\s*", re.IGNORECASE),
    re.compile(
        r"^\s*(claude|gemini|gpt|ollama|groq|anthropic|openai|perplexity)[\-\s]",
        re.IGNORECASE,
    ),
    # Token / cost / latency stats
    re.compile(r"^\s*tokens?\s*[:=]", re.IGNORECASE),
    re.compile(r"^\s*cost\s*[:=]", re.IGNORECASE),
    re.compile(r"^\s*latency\s*[:=]", re.IGNORECASE),
    re.compile(r"^\s*usage\s*[:=]", re.IGNORECASE),
    re.compile(r"^\s*\d[\d,\.]*\s*(tok|tokens|ms|s)\b", re.IGNORECASE),
    # Skill invocation lines
    re.compile(r"^\s*\[skill[:\s]", re.IGNORECASE),
    re.compile(r"^\s*skill[:=]\s*", re.IGNORECASE),
    re.compile(r"^\s*using\s+skill\b", re.IGNORECASE),
    # Debug / trace breadcrumbs
    re.compile(r"^\s*\[(debug|trace|router|model_router|gateway)\]", re.IGNORECASE),
    # Signature tails ("— DEX", "-- EOS")
    re.compile(r"^\s*[—\-–]{1,2}\s*(dex|eos|claude|assistant)\s*$", re.IGNORECASE),
    # EOS cognitive loop footer lines (⚙ model, 🪙 cost ⏱ time 📊 tokens)
    re.compile(r".*⚙", re.IGNORECASE),
    re.compile(r".*⏱", re.IGNORECASE),
    re.compile(r".*\btokens\b", re.IGNORECASE),
    re.compile(r".*\bassistant/session\b", re.IGNORECASE),
    re.compile(r".*\bclaude_cli\b", re.IGNORECASE),
)

# Inline patterns — scrubbed from within a retained line (not the whole line).
_INLINE_SCRUB_PATTERNS: tuple[re.Pattern[str], ...] = (
    # "(1,240 tokens, $0.003)" tail
    re.compile(r"\s*\(\s*\d[\d,\.]*\s*(tokens?|tok)[^)]*\)\s*$", re.IGNORECASE),
    # trailing "• provider • model" badges
    re.compile(
        r"\s*•\s*(claude|gemini|gpt|ollama|groq|anthropic)[^\n]*$", re.IGNORECASE
    ),
)

# If we detect one of these markers in the text, EVERYTHING from that marker
# onward is considered footer and dropped. This handles multi-line footer
# blocks separated from the body by a clear sentinel.
_FOOTER_CUT_SENTINELS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^\s*[★☆✦✧✪✯✰]+\s*insight", re.IGNORECASE),
    re.compile(r"^\s*---\s*$"),
    re.compile(r"^\s*provider\s*[:=]", re.IGNORECASE),
    re.compile(r"^\s*tokens?\s*[:=]", re.IGNORECASE),
    # EOS cognitive loop footer block starts with ─── divider
    re.compile(r"^\s*[─]{3,}\s*$"),
)


def _clip(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max(1, max_chars - 1)].rstrip() + "…"


def sanitize_tts_reply(
    text: object,
    *,
    max_chars: int = _DEFAULT_MAX_CHARS,
) -> str:
    """Return the clean spoken body of `text`, stripping footer / meta noise.

    Contract:
      - Never raises.
      - Always returns a str (possibly empty).
      - Idempotent: sanitize(sanitize(x)) == sanitize(x).
      - Bounded to `max_chars` (default 1200).
    """
    try:
        if text is None:
            return ""
        if not isinstance(text, str):
            try:
                text = str(text)
            except Exception:  # noqa: BLE001
                return ""

        if not text.strip():
            return ""

        lines = text.splitlines()

        # 1. Footer-cut sentinels — drop from first sentinel onward.
        cut_at: int | None = None
        for i, line in enumerate(lines):
            for pat in _FOOTER_CUT_SENTINELS:
                if pat.match(line):
                    cut_at = i
                    break
            if cut_at is not None:
                break
        if cut_at is not None:
            lines = lines[:cut_at]

        # 2. Per-line drop patterns.
        kept: list[str] = []
        for line in lines:
            drop = False
            for pat in _LINE_DROP_PATTERNS:
                if pat.match(line):
                    drop = True
                    break
            if drop:
                continue
            # 3. Inline scrubs on retained lines.
            cleaned = line
            for pat in _INLINE_SCRUB_PATTERNS:
                cleaned = pat.sub("", cleaned)
            kept.append(cleaned.rstrip())

        # 4. Collapse runs of blank lines and trim ends.
        out_lines: list[str] = []
        blank_run = 0
        for ln in kept:
            if not ln.strip():
                blank_run += 1
                if blank_run <= 1:
                    out_lines.append("")
            else:
                blank_run = 0
                out_lines.append(ln)
        while out_lines and not out_lines[0].strip():
            out_lines.pop(0)
        while out_lines and not out_lines[-1].strip():
            out_lines.pop()

        body = "\n".join(out_lines).strip()
        if not body:
            return ""

        return _clip(body, max_chars=max(50, int(max_chars)))
    except Exception:  # noqa: BLE001 — boundary: never raise
        return ""


__all__ = ["sanitize_tts_reply"]
