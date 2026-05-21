"""
Composition Engine — converts user intent into structured pipelines.

Deterministic intent matching (no LLM) for the MVP. Recognises a fixed
set of pipeline patterns and builds the corresponding step sequence.

Sits between the user-facing interface and the pipeline runner:
  Intent string → CompositionEngine.compose() → Pipeline → Pipeline.run()

Supported patterns:
  1. research_and_summarize — search + open + extract + summarize
  2. open_and_extract_url   — open a URL + extract its content
  3. simple_local_action    — open a URL in the local browser

Design rules (mirror substrate conventions):
- Deterministic — regex matching only, no LLM.
- Additive only — does not modify any existing module.
- Best-effort — unrecognised intents return a sensible fallback.
"""

from __future__ import annotations

import re
import sys
from typing import Any, Optional

from umh.substrate.pipeline import Pipeline, PipelineStep


# ─── Constants ────────────────────────────────────────────────────────────────

_LOG_PREFIX = "[substrate.composition_engine]"


def _log(msg: str) -> None:
    print(f"{_LOG_PREFIX} {msg}", file=sys.stderr)


# ─── URL Extraction ──────────────────────────────────────────────────────────

_URL_RE = re.compile(r"https?://[^\s\"'<>]+")


def _extract_url(text: str) -> Optional[str]:
    """Extract the first HTTP(S) URL from text."""
    match = _URL_RE.search(text)
    return match.group(0) if match else None


# ─── Intent Patterns ─────────────────────────────────────────────────────────

# Pattern 1: research + summarize
_RESEARCH_RE = re.compile(
    r"(research|look up|find information|investigate|look into)"
    r".*"
    r"(summarize|summary|summarise|recap|overview|digest|report)",
    re.IGNORECASE,
)

# Pattern 2: open URL + extract
_OPEN_EXTRACT_RE = re.compile(
    r"(open|go to|navigate to|visit|load)"
    r".*"
    r"(extract|scrape|get content|pull content|grab content|read content|get the .* content)",
    re.IGNORECASE,
)

# Pattern 3: simple open/navigate action
_SIMPLE_OPEN_RE = re.compile(
    r"(open|go to|navigate to|visit|launch|browse)"
    r"\s+"
    r"(browser\s+)?"
    r"(and\s+)?"
    r"(go to\s+)?"
    r"(https?://[^\s]+|[\w]+\.[\w]+)",
    re.IGNORECASE,
)

# Pattern 3 alt: "open browser and go to <url>"
_BROWSER_OPEN_RE = re.compile(
    r"open\s+browser\s+and\s+go\s+to\s+(https?://[^\s]+|[\w]+\.[\w]+)",
    re.IGNORECASE,
)

# Pattern 4: play media — "play Turks by NAV", "put on some Kendrick"
_PLAY_MEDIA_RE = re.compile(
    r"(play|put on|listen to|queue up|throw on)\s+(.+)",
    re.IGNORECASE,
)

# Pattern 5: search + open — "search for X", "look up X", "find X online"
_SEARCH_OPEN_RE = re.compile(
    r"(search\s+(?:for\s+)?|look\s+up\s+|find\s+(?:me\s+)?|google\s+)"
    r"(.+?)(?:\s+(?:online|on the web|on google))?$",
    re.IGNORECASE,
)

# Pattern 6: pull up — "pull up YouTube", "pull up my calendar"
_PULL_UP_RE = re.compile(
    r"pull\s+up\s+(https?://[^\s]+|[\w]+\.[\w]+[^\s]*|.+)",
    re.IGNORECASE,
)


# ─── Pipeline Builders ───────────────────────────────────────────────────────


def _build_research_pipeline(intent: str, context: dict[str, Any]) -> Pipeline:
    """Build a research-and-summarize pipeline.

    Steps: search_web → open_url (top result) → extract_content → summarize_content
    """
    # Extract the research topic by removing the action verbs
    topic = re.sub(
        r"(research|look up|find information|investigate|look into"
        r"|and|then|summarize|summary|summarise|recap|overview"
        r"|digest|report|them|it|the results|for me)",
        "",
        intent,
        flags=re.IGNORECASE,
    ).strip()

    if not topic:
        topic = intent  # fallback to full intent

    steps = [
        PipelineStep.new(
            "search_web",
            "search_web",
            input_data={"query": topic},
        ),
        PipelineStep.new(
            "open_url",
            "open_url",
            input_data={"url_source": "step_results.search_web.top_url"},
            requirements=["url_open"],
        ),
        PipelineStep.new(
            "extract_content",
            "extract_content",
            input_data={"url_source": "step_results.search_web.top_url"},
        ),
        PipelineStep.new(
            "summarize_content",
            "summarize_content",
            input_data={
                "content_source": "step_results.extract_content.text",
                "topic": topic,
            },
        ),
    ]

    return Pipeline.new(
        "research_and_summarize",
        steps,
        context={**context, "intent": intent, "topic": topic},
    )


def _build_open_extract_pipeline(
    intent: str, url: str, context: dict[str, Any]
) -> Pipeline:
    """Build an open-and-extract pipeline.

    Steps: open_url → extract_content
    """
    steps = [
        PipelineStep.new(
            "open_url",
            "open_url",
            input_data={"url": url},
            requirements=["url_open"],
        ),
        PipelineStep.new(
            "extract_content",
            "extract_content",
            input_data={"url": url},
        ),
    ]

    return Pipeline.new(
        "open_and_extract_url",
        steps,
        context={**context, "intent": intent, "url": url},
    )


def _build_simple_open_pipeline(
    intent: str, url: str, context: dict[str, Any]
) -> Pipeline:
    """Build a simple open-URL pipeline.

    Steps: open_url
    """
    steps = [
        PipelineStep.new(
            "open_url",
            "open_url",
            input_data={"url": url},
            requirements=["url_open"],
        ),
    ]

    return Pipeline.new(
        "simple_local_action",
        steps,
        context={**context, "intent": intent, "url": url},
    )


def _build_play_media_pipeline(
    intent: str, query: str, context: dict[str, Any]
) -> Pipeline:
    """Build a play-media pipeline.

    Converts a media request into a YouTube search URL and opens it
    on the local workstation browser.
    """
    from urllib.parse import quote_plus

    search_url = f"https://www.youtube.com/results?search_query={quote_plus(query)}"
    steps = [
        PipelineStep.new(
            "open_url",
            "open_url",
            input_data={"url": search_url},
            requirements=["url_open"],
        ),
    ]

    return Pipeline.new(
        "play_media",
        steps,
        context={**context, "intent": intent, "media_query": query, "url": search_url},
    )


def _build_search_open_pipeline(
    intent: str, query: str, context: dict[str, Any]
) -> Pipeline:
    """Build a search-and-open pipeline.

    Opens a Google search for the query on the local workstation browser.
    """
    from urllib.parse import quote_plus

    search_url = f"https://www.google.com/search?q={quote_plus(query)}"
    steps = [
        PipelineStep.new(
            "open_url",
            "open_url",
            input_data={"url": search_url},
            requirements=["url_open"],
        ),
    ]

    return Pipeline.new(
        "search_and_open",
        steps,
        context={**context, "intent": intent, "search_query": query, "url": search_url},
    )


# Well-known site names → URLs (no dots needed in input)
_KNOWN_SITES: dict[str, str] = {
    "youtube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "gmail": "https://mail.google.com",
    "calendar": "https://calendar.google.com",
    "notion": "https://www.notion.so",
    "github": "https://github.com",
    "twitter": "https://twitter.com",
    "x": "https://x.com",
    "reddit": "https://www.reddit.com",
    "spotify": "https://open.spotify.com",
    "instagram": "https://www.instagram.com",
    "linkedin": "https://www.linkedin.com",
    "discord": "https://discord.com/app",
    "slack": "https://app.slack.com",
    "chatgpt": "https://chatgpt.com",
    "claude": "https://claude.ai",
}


def _resolve_site_name(name: str) -> Optional[str]:
    """Resolve a well-known site name to its URL. Returns None if unknown."""
    return _KNOWN_SITES.get(name.lower().strip())


# ─── Composition Engine ──────────────────────────────────────────────────────


class CompositionEngine:
    """Converts user intent into structured pipelines.

    Deterministic pattern matching for the MVP. No LLM calls.
    Patterns are checked in specificity order: most specific first.
    """

    def compose(
        self, intent: str, context: Optional[dict[str, Any]] = None
    ) -> Pipeline:
        """Convert a user request into a pipeline.

        If ``context`` contains a ``correlation_id``, it flows through to
        the pipeline and all spine events emitted during execution.

        Args:
            intent: Natural language intent string.
            context: Optional context dict passed through to the pipeline.
                     May include ``correlation_id`` for event spine tracking.

        Returns:
            A Pipeline ready for execution via pipeline.run().
        """
        ctx = context or {}
        url = _extract_url(intent)

        _log(f"composing intent: {intent!r}")

        # 1. Research + summarize (most complex pattern)
        if _RESEARCH_RE.search(intent):
            _log("matched pattern: research_and_summarize")
            return _build_research_pipeline(intent, ctx)

        # 2. Open URL + extract content
        if _OPEN_EXTRACT_RE.search(intent) and url:
            _log(f"matched pattern: open_and_extract_url → {url}")
            return _build_open_extract_pipeline(intent, url, ctx)

        # 3. Simple open/navigate with URL
        if url:
            # Check for explicit browser open pattern
            browser_match = _BROWSER_OPEN_RE.search(intent)
            if browser_match:
                target_url = browser_match.group(1)
                if not target_url.startswith("http"):
                    target_url = f"https://{target_url}"
                _log(f"matched pattern: simple_local_action (browser) → {target_url}")
                return _build_simple_open_pipeline(intent, target_url, ctx)

            if _SIMPLE_OPEN_RE.search(intent):
                _log(f"matched pattern: simple_local_action → {url}")
                return _build_simple_open_pipeline(intent, url, ctx)

        # 4. Simple open with domain-like target (no explicit URL)
        simple_match = _SIMPLE_OPEN_RE.search(intent)
        if simple_match:
            target = simple_match.group(5)  # the URL-like capture group
            if not target.startswith("http"):
                target = f"https://{target}"
            _log(f"matched pattern: simple_local_action (inferred) → {target}")
            return _build_simple_open_pipeline(intent, target, ctx)

        # 4b. Open/launch + known site name (no dot needed)
        # Catches "open YouTube", "launch Gmail", "visit Notion"
        open_verb_match = re.match(
            r"(open|go to|navigate to|visit|launch|browse)\s+(.+)",
            intent,
            re.IGNORECASE,
        )
        if open_verb_match:
            site_target = open_verb_match.group(2).strip()
            site_resolved = _resolve_site_name(site_target)
            if site_resolved:
                _log(
                    f"matched pattern: simple_local_action (known site) → {site_resolved}"
                )
                return _build_simple_open_pipeline(intent, site_resolved, ctx)

        # 5. "pull up X" — resolve known site or treat as open
        pull_match = _PULL_UP_RE.search(intent)
        if pull_match:
            target_text = pull_match.group(1).strip()
            resolved = _resolve_site_name(target_text)
            if resolved:
                _log(f"matched pattern: pull_up (known site) → {resolved}")
                return _build_simple_open_pipeline(intent, resolved, ctx)
            # If it looks like a domain, open it
            if "." in target_text:
                target_url = (
                    target_text
                    if target_text.startswith("http")
                    else f"https://{target_text}"
                )
                _log(f"matched pattern: pull_up (domain) → {target_url}")
                return _build_simple_open_pipeline(intent, target_url, ctx)
            # Otherwise search for it
            _log(f"matched pattern: pull_up (search) → {target_text!r}")
            return _build_search_open_pipeline(intent, target_text, ctx)

        # 6. Play media — "play Turks by NAV", "put on Kendrick"
        play_match = _PLAY_MEDIA_RE.search(intent)
        if play_match:
            query = play_match.group(2).strip()
            if query:
                _log(f"matched pattern: play_media → {query!r}")
                return _build_play_media_pipeline(intent, query, ctx)

        # 7. Search + open — "search for X", "look up X", "google X"
        search_match = _SEARCH_OPEN_RE.search(intent)
        if search_match:
            query = search_match.group(2).strip()
            if query:
                _log(f"matched pattern: search_and_open → {query!r}")
                return _build_search_open_pipeline(intent, query, ctx)

        # 8. Known site name without action verb — "YouTube", "Gmail"
        site_url = _resolve_site_name(intent.strip())
        if site_url:
            _log(f"matched pattern: known_site → {site_url}")
            return _build_simple_open_pipeline(intent, site_url, ctx)

        # Fallback: treat the whole intent as a research topic
        _log("no specific pattern matched — falling back to research_and_summarize")
        return _build_research_pipeline(intent, ctx)


# ─── Exports ──────────────────────────────────────────────────────────────────

__all__ = [
    "CompositionEngine",
]
