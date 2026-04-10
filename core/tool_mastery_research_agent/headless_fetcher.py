"""Headless rendering fetch path for the Tool Mastery Research Agent.

Phase 4 unlock: docs sites built as client-rendered SPAs (Next.js,
Docusaurus, Mintlify, Nuxt, etc.) return an empty shell to urllib.
The prose lives in hydrated DOM, not the HTTP body. This module
reaches *through* that shell with a real browser (Playwright Chromium)
and captures the rendered DOM after JS has executed.

Design constraints (mirrors the rest of the agent):
    - Pure execution, no LLM calls, no parsing beyond DOM capture.
    - Only activated as a **retry** for sources the static fetcher
      already tried and the signal gate already dropped. We never
      render speculatively.
    - Strict per-run budget. Browsers are expensive; a runaway render
      pass is a worse failure mode than a missed source.
    - Provenance is explicit: any source re-captured via this path
      has its origin stamped ``headless_render@<iso8601>`` and the
      capture file is rewritten in-place so the downstream signal
      pass re-reads the hydrated body.

Honest boundaries:
    - This does NOT bypass bot walls (Cloudflare challenges, login
      walls, hCaptcha). If the SPA renders only after auth, the
      capture will be the login shell and the signal gate will still
      drop it — correctly.
    - We do not parse the DOM. We hand the rendered HTML back to the
      existing sanitizer pipeline unchanged so research and author
      agents continue to agree on what counts as prose.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import FetchedSource, FetchStatus

# Strict defaults — headless is expensive and we'd rather under-fetch
# than launch an uncapped browser pass.
DEFAULT_MAX_RENDERS = 6
RENDER_TIMEOUT_MS = 20_000
NAVIGATION_WAIT = "networkidle"
MAX_RENDER_BYTES = 3_000_000  # 3 MB cap on rendered DOM


# ---------------------------------------------------------------------------
# SPA heuristics
# ---------------------------------------------------------------------------

# Signatures that strongly suggest a client-rendered shell. We match on
# the *already-fetched* static HTML — the point is to avoid spinning up
# a browser for sites that just happen to be short.
_SPA_MARKERS: tuple[bytes, ...] = (
    b'id="__next"',  # Next.js
    b'id="__nuxt"',  # Nuxt
    b'id="root"',  # CRA / Vite React
    b'id="app"',  # Vue / generic
    b"window.__NEXT_DATA__",  # Next.js hydration payload
    b"__NUXT__",
    b"docusaurus",  # Docusaurus
    b"mintlify",  # Mintlify
    b"gatsby",  # Gatsby
    b"data-reactroot",  # React SSR shell
)

# Small body + lots of <script> + almost no prose = likely SPA shell.
_LIKELY_SHELL_MAX_BODY_CHARS = 20_000
_LIKELY_SHELL_MIN_SCRIPT_COUNT = 3

_SCRIPT_TAG_RE = re.compile(rb"<script\b", re.IGNORECASE)
_BODY_TEXT_RE = re.compile(rb">([^<]{40,})<")


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def is_likely_spa(raw_bytes: bytes) -> tuple[bool, str]:
    """Return (is_spa, reason) for a static HTML body.

    Two independent triggers, either sufficient:

    1. **Framework marker**: an explicit Next.js/Nuxt/Docusaurus/etc.
       signature in the body. These are unambiguous — the site
       *declares* itself client-rendered.

    2. **Script-heavy HTML shell**: the body is HTML with at least
       one <script> tag. We defer the "is the prose too thin" question
       to the signal gate — the caller only invokes us on sources the
       signal gate already dropped, so reaching this function already
       means prose was insufficient. Our only job here is to confirm
       the body is an HTML doc that could plausibly hydrate more.

    The pypi case (no scripts, plain server-rendered HTML) correctly
    returns False: no amount of rendering will add prose that isn't
    already there.
    """
    if not raw_bytes:
        return False, "empty body"

    # Framework markers — strongest signal.
    for marker in _SPA_MARKERS:
        if marker in raw_bytes:
            return True, f"framework marker: {marker.decode('ascii', 'replace')}"

    # Must look like HTML at all.
    lower_head = raw_bytes[:2048].lower()
    if b"<html" not in lower_head and b"<!doctype html" not in lower_head:
        return False, "not an HTML document"

    script_count = len(_SCRIPT_TAG_RE.findall(raw_bytes))
    if script_count >= 1:
        return (
            True,
            f"script-bearing HTML (scripts={script_count}, body={len(raw_bytes)}B) "
            "— signal gate already flagged low prose, rendering may hydrate more",
        )

    return False, (
        f"static HTML with no scripts ({len(raw_bytes)}B) — "
        "rendering cannot unlock prose that isn't there"
    )


# ---------------------------------------------------------------------------
# Render report — embedded in artifact notes / manifest
# ---------------------------------------------------------------------------


@dataclass
class RenderAttempt:
    """One headless render attempt, successful or not."""

    url: str
    raw_path: str
    activated: bool = False  # did we actually launch the browser?
    reason: str = ""  # why activated / why not
    rendered_bytes: int = 0
    rendered_at: str = ""
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "raw_path": self.raw_path,
            "activated": self.activated,
            "reason": self.reason,
            "rendered_bytes": self.rendered_bytes,
            "rendered_at": self.rendered_at,
            "error": self.error,
        }


@dataclass
class RenderPassReport:
    """Summary of the headless pass across all retry candidates."""

    attempts: list[RenderAttempt] = field(default_factory=list)
    budget: int = 0
    rendered: int = 0
    succeeded: int = 0
    skipped_budget: int = 0
    playwright_available: bool = True
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "budget": self.budget,
            "rendered": self.rendered,
            "succeeded": self.succeeded,
            "skipped_budget": self.skipped_budget,
            "playwright_available": self.playwright_available,
            "note": self.note,
            "attempts": [a.to_dict() for a in self.attempts],
        }


# ---------------------------------------------------------------------------
# Render pass
# ---------------------------------------------------------------------------


def _load_playwright():
    """Import Playwright lazily so the module stays optional at import time."""
    try:
        from playwright.sync_api import sync_playwright  # type: ignore

        return sync_playwright, None
    except Exception as err:  # pragma: no cover - import guard
        return None, f"{type(err).__name__}: {err}"


def _render_one(playwright_ctx, url: str) -> tuple[bytes, str | None]:
    """Render a single URL and return (rendered_html_bytes, error)."""
    browser = None
    try:
        browser = playwright_ctx.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0 Safari/537.36 "
                "EOS-ToolMasteryResearchAgent/1.0-headless"
            ),
        )
        page = context.new_page()
        page.set_default_timeout(RENDER_TIMEOUT_MS)
        page.goto(url, wait_until=NAVIGATION_WAIT, timeout=RENDER_TIMEOUT_MS)
        html = page.content()
        return html.encode("utf-8")[:MAX_RENDER_BYTES], None
    except Exception as err:  # noqa: BLE001 — render errors are per-URL
        return b"", f"{type(err).__name__}: {err}"
    finally:
        if browser is not None:
            try:
                browser.close()
            except Exception:  # pragma: no cover
                pass


def render_low_signal_sources(
    *,
    candidates: list[FetchedSource],
    run_dir: Path,
    max_renders: int = DEFAULT_MAX_RENDERS,
) -> tuple[list[FetchedSource], RenderPassReport]:
    """Re-capture low-signal candidates using a headless browser.

    ``candidates`` are the FetchedSource records that currently sit at
    status OK but whose static body looks like an SPA shell — the
    caller (artifact.build_artifact) is responsible for filtering down
    to the right retry set before calling in here.

    Returns (updated_sources, report). Updated sources are new
    FetchedSource objects with origin stamped ``headless_render`` and
    ``raw_path`` pointing at the rewritten capture file. The caller is
    responsible for replacing the old records in the fetched list.
    """
    report = RenderPassReport(budget=max_renders)
    updated: list[FetchedSource] = []

    if not candidates:
        report.note = "no candidates supplied"
        return updated, report

    sync_playwright, import_err = _load_playwright()
    if sync_playwright is None:
        report.playwright_available = False
        report.note = f"playwright unavailable: {import_err}"
        for cand in candidates:
            report.attempts.append(
                RenderAttempt(
                    url=cand.ref.url,
                    raw_path=cand.raw_path or "",
                    activated=False,
                    reason="playwright unavailable",
                    error=import_err,
                )
            )
        return updated, report

    with sync_playwright() as pw:
        for cand in candidates:
            if report.rendered >= max_renders:
                report.skipped_budget += 1
                report.attempts.append(
                    RenderAttempt(
                        url=cand.ref.url,
                        raw_path=cand.raw_path or "",
                        activated=False,
                        reason=f"render budget exceeded (cap={max_renders})",
                    )
                )
                continue

            if not cand.raw_path:
                report.attempts.append(
                    RenderAttempt(
                        url=cand.ref.url,
                        raw_path="",
                        activated=False,
                        reason="no raw_path to rewrite",
                    )
                )
                continue

            report.rendered += 1
            rendered_bytes, err = _render_one(pw, cand.ref.url)
            rendered_at = _iso_now()

            if err or not rendered_bytes:
                report.attempts.append(
                    RenderAttempt(
                        url=cand.ref.url,
                        raw_path=cand.raw_path,
                        activated=True,
                        reason="render failed",
                        rendered_bytes=len(rendered_bytes),
                        rendered_at=rendered_at,
                        error=err or "empty render",
                    )
                )
                continue

            # Rewrite the capture in-place so the signal pass re-reads
            # the hydrated DOM. raw_path is stored relative to run_dir
            # (fetcher writes `out_path.relative_to(raw_dir.parent)` and
            # raw_dir.parent == run_dir).
            abs_raw = run_dir / cand.raw_path
            try:
                abs_raw.parent.mkdir(parents=True, exist_ok=True)
                abs_raw.write_bytes(rendered_bytes)
            except OSError as werr:
                report.attempts.append(
                    RenderAttempt(
                        url=cand.ref.url,
                        raw_path=cand.raw_path,
                        activated=True,
                        reason="write failed",
                        rendered_bytes=len(rendered_bytes),
                        rendered_at=rendered_at,
                        error=f"write error: {werr}",
                    )
                )
                continue

            # Replace the SourceRef's origin with the render stamp so
            # provenance downstream is explicit. We build a new object
            # instead of mutating to keep dataclass semantics clean.
            new_ref = type(cand.ref)(
                url=cand.ref.url,
                tier=cand.ref.tier,
                label=cand.ref.label,
                origin=f"headless_render@{rendered_at}",
            )
            updated.append(
                FetchedSource(
                    ref=new_ref,
                    status=FetchStatus.OK,
                    http_status=cand.http_status,
                    content_type="text/html; rendered=headless",
                    bytes=len(rendered_bytes),
                    raw_path=cand.raw_path,
                    fetched_at=rendered_at,
                )
            )
            report.succeeded += 1
            report.attempts.append(
                RenderAttempt(
                    url=cand.ref.url,
                    raw_path=cand.raw_path,
                    activated=True,
                    reason="rendered ok",
                    rendered_bytes=len(rendered_bytes),
                    rendered_at=rendered_at,
                )
            )

    report.note = (
        f"rendered {report.rendered}/{len(candidates)}, "
        f"succeeded {report.succeeded}, skipped_budget {report.skipped_budget}"
    )
    return updated, report
