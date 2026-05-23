"""Fetcher for the Tool Mastery Research Agent.

Thin, dependency-free HTTP GET over urllib. No HTML parsing, no
browser emulation, no LLM calls. Writes raw captures to disk under
the run directory for full provenance.

Honest boundaries:
    - We do not parse HTML into cleaned prose. Downstream authoring
      is expected to read the raw capture.
    - We do not follow JavaScript. Sites that are JS-only will be
      recorded with whatever the static HTML returned.
    - MCP HTTP endpoints (like stitch) are recorded but we do not
      attempt a POST or handshake — that's the MCP client's job.
"""

from __future__ import annotations

import socket
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from .models import FetchedSource, FetchStatus, SourceRef

USER_AGENT = "EOS-ToolMasteryResearchAgent/1.0 (+https://github.com/antonyfmunoz/OS)"
TIMEOUT_SECONDS = 15
MAX_BYTES = 2_000_000  # 2 MB cap per source
DEFAULT_MAX_FETCHES = 20  # fetch budget cap per run (raised for GitHub repo expansion)


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_filename(url: str, index: int) -> str:
    parsed = urlparse(url)
    host = (parsed.netloc or "unknown").replace(":", "_")
    path = (parsed.path or "/").strip("/").replace("/", "_") or "root"
    stem = f"{index:02d}_{host}_{path}"
    # keep it reasonable
    return (stem[:120] + ".txt").replace("?", "_").replace("#", "_")


def fetch_source(
    ref: SourceRef,
    *,
    raw_dir: Path,
    index: int,
) -> FetchedSource:
    """Fetch a single SourceRef and write the raw body to ``raw_dir``.

    Always returns a FetchedSource — never raises — so callers can
    aggregate a honest per-source status.
    """

    fetched_at = _iso_now()
    parsed = urlparse(ref.url)
    if parsed.scheme not in ("http", "https"):
        return FetchedSource(
            ref=ref,
            status=FetchStatus.UNSUPPORTED_SCHEME,
            fetched_at=fetched_at,
            error=f"scheme {parsed.scheme!r} not supported",
        )

    filename = _safe_filename(ref.url, index)
    raw_dir.mkdir(parents=True, exist_ok=True)
    out_path = raw_dir / filename

    req = urllib.request.Request(
        ref.url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/json;q=0.9,*/*;q=0.5",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            http_status = resp.status
            content_type = resp.headers.get("Content-Type", "")
            body = resp.read(MAX_BYTES + 1)
    except urllib.error.HTTPError as err:
        return FetchedSource(
            ref=ref,
            status=FetchStatus.HTTP_ERROR,
            http_status=err.code,
            fetched_at=fetched_at,
            error=f"HTTP {err.code}: {err.reason}",
        )
    except socket.timeout:
        return FetchedSource(
            ref=ref,
            status=FetchStatus.TIMEOUT,
            fetched_at=fetched_at,
            error=f"timeout after {TIMEOUT_SECONDS}s",
        )
    except (urllib.error.URLError, OSError) as err:
        return FetchedSource(
            ref=ref,
            status=FetchStatus.NETWORK_ERROR,
            fetched_at=fetched_at,
            error=f"network error: {err}",
        )

    truncated = len(body) > MAX_BYTES
    if truncated:
        body = body[:MAX_BYTES]

    try:
        out_path.write_bytes(body)
    except OSError as err:
        return FetchedSource(
            ref=ref,
            status=FetchStatus.NETWORK_ERROR,
            http_status=http_status,
            fetched_at=fetched_at,
            error=f"could not write raw capture: {err}",
        )

    return FetchedSource(
        ref=ref,
        status=FetchStatus.OK,
        http_status=http_status,
        content_type=content_type,
        bytes=len(body) + (1 if truncated else 0),
        raw_path=str(out_path.relative_to(raw_dir.parent)),
        fetched_at=fetched_at,
    )


def fetch_plan(
    sources: list[SourceRef],
    *,
    raw_dir: Path,
    max_fetches: int = DEFAULT_MAX_FETCHES,
) -> list[FetchedSource]:
    """Fetch sources in order, capped by ``max_fetches``.

    Sources beyond the cap are recorded as SKIPPED so the provenance
    remains honest ("we saw it, we chose not to spend a fetch on it")
    rather than silently disappearing from the run.
    """

    results: list[FetchedSource] = []
    for i, ref in enumerate(sources, start=1):
        if i > max_fetches:
            results.append(
                FetchedSource(
                    ref=ref,
                    status=FetchStatus.SKIPPED,
                    fetched_at=_iso_now(),
                    error=(
                        f"fetch budget exceeded (cap={max_fetches}); "
                        "deprioritized by source quality scoring"
                    ),
                )
            )
            continue
        results.append(fetch_source(ref, raw_dir=raw_dir, index=i))
    return results
