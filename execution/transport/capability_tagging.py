"""
Capability tagging — additive pre-routing layer.

This module annotates incoming gateway requests with the set of capabilities
they would *like* a target node to have. It does NOT change routing. The
model_router and gateway continue to make their own decisions; tags live on
request["required_capabilities"] as observable metadata.

Why this is valuable before capability-aware routing exists:
  - Telemetry: every request in the gateway event log can be inspected for
    "what capability did we actually need?" without guessing from content.
  - Future integration: when capability routing lands, it will consume these
    tags instead of re-parsing the prompt.
  - Debuggability: a voice request that never gets a microphone_input tag
    tells us the classifier is wrong, not the router.

Usage:
    from execution.transport.capability_tagging import tag_request

    caps = tag_request(request)   # returns list[str], also mutates request
"""

from __future__ import annotations

from typing import Any

from execution.transport.capabilities import Capability


# ─── Classifier rules ────────────────────────────────────────────────────────
# Kept as plain data so the rules are auditable and easy to extend. Each rule
# is (predicate, capability_slug). Predicates run against a normalized dict.

def _text(request: dict) -> str:
    return (request.get("prompt") or "").lower()


def _comm_type(request: dict) -> str:
    return (request.get("comm_type") or "").lower()


def _channel(request: dict) -> str:
    return (request.get("channel") or "").lower()


def _is_voice(request: dict) -> bool:
    if _comm_type(request) in {"voice", "audio"}:
        return True
    if _channel(request) in {"voice", "voice_live", "pikastream"}:
        return True
    # Heuristic: media_type hint some subsystems pass
    media = (request.get("media_type") or "").lower()
    return media in {"voice", "audio"}


def _is_browser(request: dict) -> bool:
    text = _text(request)
    browser_words = (
        "browser", "navigate to", "open url", "scrape", "crawl",
        "fill out form", "click through", "web flow",
    )
    return any(w in text for w in browser_words)


def _is_workstation(request: dict) -> bool:
    text = _text(request)
    workstation_words = (
        "on my workstation", "on my mac", "on my computer", "local machine",
        "focus my", "switch my workspace", "my desktop", "play sound",
        "speak this",
    )
    return any(w in text for w in workstation_words)


def _is_long_running(request: dict) -> bool:
    text = _text(request)
    long_words = (
        "watch for", "monitor until", "keep running", "background",
        "every hour", "every minute", "loop until",
    )
    if any(w in text for w in long_words):
        return True
    return bool(request.get("long_running"))


# ─── Public API ──────────────────────────────────────────────────────────────

def tag_request(request: dict[str, Any]) -> list[str]:
    """
    Inspect a gateway request and return the list of capability slugs that
    would be required to serve it on a capability-routed substrate. Also
    writes the list to `request["required_capabilities"]` for observability.

    Every reasoning request implicitly needs REASONING, so that tag is added
    to every classified request. Other capabilities are additive on top.

    Never raises — if inspection fails, returns an empty list and leaves the
    request unmutated.
    """
    try:
        tags: list[str] = [Capability.REASONING.value]

        if _is_voice(request):
            tags.append(Capability.MICROPHONE_INPUT.value)
            tags.append(Capability.AUDIO_OUTPUT.value)

        if _is_browser(request):
            tags.append(Capability.BROWSER_CONTROL.value)

        if _is_workstation(request):
            # Workstation commands imply audio output (the usual payload is
            # PLAY_SOUND / SPEAK_TEXT in this MVP phase). Full computer
            # control is deliberately NOT auto-tagged — it has to be
            # requested explicitly once the policy allows it.
            tags.append(Capability.AUDIO_OUTPUT.value)

        if _is_long_running(request):
            tags.append(Capability.LONG_RUNNING_SESSION.value)

        # Dedupe while preserving order
        seen: set[str] = set()
        deduped: list[str] = []
        for tag in tags:
            if tag not in seen:
                seen.add(tag)
                deduped.append(tag)

        request["required_capabilities"] = deduped
        return deduped
    except Exception as e:
        import sys
        print(f"[substrate.capability_tagging] failed: {e}", file=sys.stderr)
        return []
