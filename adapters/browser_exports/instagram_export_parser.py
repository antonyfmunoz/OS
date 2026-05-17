"""Instagram curation analyst — classifies saved posts and scores harness candidates.

Parses Instagram's saved_posts.json export, classifies each item by content type,
fetches GitHub repo metadata for software saves, and produces a curation report
ranking harness candidates against current UMH placeholders.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from governance.policy.authority_tier import T4_SUPPORTING, validate_tier
from understanding.perception.source import RawContent, Source

logger = logging.getLogger(__name__)

# Current UMH placeholders for comparison
CURRENT_PLACEHOLDERS: dict[str, dict[str, str]] = {
    "software_creation": {"name": "Goose", "org": "Block", "license": "Apache-2.0"},
    "desktop_control": {
        "name": "UI-TARS-desktop",
        "org": "ByteDance",
        "license": "Apache-2.0",
    },
    "voice_interaction": {"name": "Voice-Pro", "org": "unknown", "license": "unknown"},
    "creative_generation": {
        "name": "Open Generative AI",
        "org": "unknown",
        "license": "unknown",
    },
}

# License scoring
_PERMISSIVE_LICENSES = {
    "apache-2.0",
    "mit",
    "bsd-2-clause",
    "bsd-3-clause",
    "isc",
    "unlicense",
    "0bsd",
    "wtfpl",
}
_OTHER_PERMISSIVE = {"mpl-2.0", "artistic-2.0", "zlib"}
_COPYLEFT_LICENSES = {"gpl-2.0", "gpl-3.0", "agpl-3.0", "lgpl-2.1", "lgpl-3.0"}


@dataclass
class HarnessCandidate:
    """A GitHub repo evaluated as potential UMH harness component."""

    repo_url: str
    name: str
    license: str
    stars: int
    language: str
    capability_category: str
    overall_score: float
    scores: dict[str, float]
    readme_summary: str


@dataclass
class ClassifiedSave:
    """A single Instagram save classified by type."""

    url: str
    save_type: str  # github | youtube | twitter | article | app | person | aesthetic
    title: str
    capability_category: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class InstagramCurationReport:
    """Full curation analysis of Instagram saved posts."""

    total_saves: int
    classified: dict[str, int]  # type -> count
    harness_candidates: list[HarnessCandidate]
    placeholder_comparison: dict[str, list[HarnessCandidate]]  # capability -> ranked
    generated_at: str
    all_saves: list[ClassifiedSave] = field(default_factory=list)


class InstagramSaveSource:
    """Wraps a classified Instagram save as an ingestion Source."""

    source_type: str = "instagram_save"

    def __init__(self, save: ClassifiedSave, *, authority_tier: int = T4_SUPPORTING) -> None:
        self._save = save
        self.authority_tier: int = validate_tier(authority_tier)
        self._cached_content: RawContent | None = None

    @property
    def source_id(self) -> str:
        url_hash = hashlib.sha256(self._save.url.encode()).hexdigest()[:12]
        return f"instagram_save:{self._save.save_type}:{url_hash}"

    def exists(self) -> bool:
        return True

    def read(self) -> RawContent:
        if self._cached_content is not None:
            return self._cached_content

        payload = {
            "url": self._save.url,
            "save_type": self._save.save_type,
            "title": self._save.title,
            "capability_category": self._save.capability_category,
            "metadata": self._save.metadata,
        }
        serialized = json.dumps(payload, ensure_ascii=False, indent=2)
        encoded = serialized.encode("utf-8")
        sha = hashlib.sha256(encoded).hexdigest()

        self._cached_content = RawContent(
            content=serialized,
            content_type="application/x-instagram-save+json",
            size_bytes=len(encoded),
            sha256=sha,
        )
        return self._cached_content

    def metadata(self) -> dict[str, Any]:
        return {
            "url": self._save.url,
            "save_type": self._save.save_type,
            "title": self._save.title,
            "capability_category": self._save.capability_category,
        }


# Protocol conformance
_check: type[Source] = InstagramSaveSource  # type: ignore[assignment]


def _classify_url(url: str) -> str:
    """Classify a URL by content type."""
    parsed = urlparse(url)
    domain = parsed.netloc.lower().replace("www.", "")

    if "github.com" in domain:
        return "github"
    if "youtube.com" in domain or "youtu.be" in domain:
        return "youtube"
    if "twitter.com" in domain or "x.com" in domain:
        return "twitter"
    if any(d in domain for d in ("apps.apple.com", "play.google.com", "producthunt.com")):
        return "app"
    if any(d in domain for d in ("medium.com", "substack.com", "dev.to", "arxiv.org", "blog")):
        return "article"

    # Check path patterns
    path = parsed.path.lower()
    if re.search(r"/(@|profile|user)/", path):
        return "person"

    return "article"  # Default to article for unknown URLs


def _categorize_capability(repo_name: str, description: str, topics: list[str]) -> str:
    """Determine capability category from repo metadata."""
    combined = f"{repo_name} {description} {' '.join(topics)}".lower()

    if any(
        kw in combined
        for kw in (
            "code",
            "coding",
            "ide",
            "copilot",
            "agent",
            "agentic",
            "software",
            "developer",
            "programming",
        )
    ):
        return "software_creation"
    if any(
        kw in combined for kw in ("desktop", "gui", "automation", "browser", "ui-", "screen", "rpa")
    ):
        return "desktop_control"
    if any(kw in combined for kw in ("voice", "speech", "tts", "stt", "audio", "whisper", "talk")):
        return "voice_interaction"
    if any(
        kw in combined
        for kw in (
            "generat",
            "diffus",
            "image",
            "video",
            "art",
            "creative",
            "music",
            "3d",
        )
    ):
        return "creative_generation"
    if any(
        kw in combined
        for kw in ("ingest", "parse", "extract", "scrape", "crawl", "etl", "pipeline")
    ):
        return "ingestion"
    if any(kw in combined for kw in ("infra", "deploy", "docker", "k8s", "cloud", "server", "db")):
        return "infrastructure"

    return "other"


def _score_license(license_key: str) -> float:
    """Score a license for harness suitability."""
    key = license_key.lower().strip()
    if key in _PERMISSIVE_LICENSES:
        return 1.0
    if key in _OTHER_PERMISSIVE:
        return 0.5
    if key in _COPYLEFT_LICENSES:
        return 0.0
    if key in ("", "none", "other", "noassertion"):
        return 0.0
    return 0.3  # Unknown license


def _score_activity(pushed_at: str | None) -> float:
    """Score based on recency of last push."""
    if not pushed_at:
        return 0.1

    try:
        last_push = datetime.fromisoformat(pushed_at.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return 0.1

    now = datetime.now(tz=timezone.utc)
    days_ago = (now - last_push).days

    if days_ago <= 30:
        return 1.0
    if days_ago <= 90:
        return 0.7
    if days_ago <= 365:
        return 0.3
    return 0.1


def _score_maturity(stars: int) -> float:
    """Score based on star count as maturity proxy."""
    if stars >= 10000:
        return 1.0
    if stars >= 1000:
        return 0.7
    if stars >= 100:
        return 0.4
    return 0.2


def _fetch_github_metadata(owner: str, repo: str) -> dict[str, Any] | None:
    """Fetch repo metadata from GitHub API. Returns None on failure."""
    try:
        import requests
    except ImportError:
        logger.error("requests not installed — cannot fetch GitHub metadata")
        return None

    token = os.getenv("GITHUB_TOKEN", "")
    headers: dict[str, str] = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"

    url = f"https://api.github.com/repos/{owner}/{repo}"
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            logger.warning("GitHub API returned %d for %s/%s", resp.status_code, owner, repo)
            return None
        return resp.json()
    except Exception as e:
        logger.error("GitHub API request failed for %s/%s: %s", owner, repo, e)
        return None


def _fetch_readme_summary(owner: str, repo: str) -> str:
    """Fetch first ~500 chars of README from GitHub."""
    try:
        import requests
    except ImportError:
        return ""

    token = os.getenv("GITHUB_TOKEN", "")
    headers: dict[str, str] = {"Accept": "application/vnd.github.v3.raw"}
    if token:
        headers["Authorization"] = f"token {token}"

    url = f"https://api.github.com/repos/{owner}/{repo}/readme"
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            return ""
        text = resp.text[:500]
        # Strip markdown formatting for summary
        text = re.sub(r"[#*_`]", "", text)
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
        return text.strip()
    except Exception:
        return ""


def _parse_github_url(url: str) -> tuple[str, str] | None:
    """Extract owner/repo from a GitHub URL."""
    parsed = urlparse(url)
    parts = [p for p in parsed.path.strip("/").split("/") if p]
    if len(parts) >= 2:
        return parts[0], parts[1]
    return None


def _evaluate_github_repo(url: str) -> HarnessCandidate | None:
    """Fully evaluate a GitHub repo as a harness candidate."""
    parsed = _parse_github_url(url)
    if not parsed:
        return None

    owner, repo = parsed
    meta = _fetch_github_metadata(owner, repo)
    if not meta:
        # Return minimal candidate without API data
        return HarnessCandidate(
            repo_url=url,
            name=repo,
            license="unknown",
            stars=0,
            language="unknown",
            capability_category="other",
            overall_score=0.0,
            scores={
                "license": 0.0,
                "activity": 0.1,
                "maturity": 0.2,
                "gap_fit": 0.0,
            },
            readme_summary="",
        )

    license_info = meta.get("license") or {}
    license_key = (
        license_info.get("spdx_id", "unknown") if isinstance(license_info, dict) else "unknown"
    )
    stars = meta.get("stargazers_count", 0)
    language = meta.get("language", "unknown") or "unknown"
    pushed_at = meta.get("pushed_at")
    description = meta.get("description", "") or ""
    topics = meta.get("topics", []) or []

    capability = _categorize_capability(repo, description, topics)
    readme = _fetch_readme_summary(owner, repo)

    # Compute scores
    license_score = _score_license(license_key)
    activity_score = _score_activity(pushed_at)
    maturity_score = _score_maturity(stars)

    # Gap fit: 1.0 if matches a placeholder category, else 0.3
    gap_fit_score = 1.0 if capability in CURRENT_PLACEHOLDERS else 0.3

    # Weighted average
    overall = (
        license_score * 0.25 + activity_score * 0.25 + maturity_score * 0.25 + gap_fit_score * 0.25
    )

    return HarnessCandidate(
        repo_url=url,
        name=repo,
        license=license_key,
        stars=stars,
        language=language,
        capability_category=capability,
        overall_score=round(overall, 3),
        scores={
            "license": license_score,
            "activity": activity_score,
            "maturity": maturity_score,
            "gap_fit": gap_fit_score,
        },
        readme_summary=readme,
    )


def parse_instagram_saves(saved_posts_path: Path) -> InstagramCurationReport:
    """Parse Instagram saved posts and produce a curation report.

    Args:
        saved_posts_path: Path to saved_posts.json from Instagram export.

    Returns:
        InstagramCurationReport with classifications and harness candidates.
    """
    saved_posts_path = Path(saved_posts_path)

    try:
        raw = json.loads(saved_posts_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.error("Failed to read saved posts: %s", e)
        return InstagramCurationReport(
            total_saves=0,
            classified={},
            harness_candidates=[],
            placeholder_comparison={},
            generated_at=datetime.now(tz=timezone.utc).isoformat(),
        )

    # Instagram export format: list of saved items or nested structure
    posts: list[dict[str, Any]] = []
    if isinstance(raw, list):
        posts = raw
    elif isinstance(raw, dict):
        # Various possible structures — check most specific keys first
        if "saved_saved_media" in raw:
            posts = raw["saved_saved_media"]
        elif "saved_media" in raw:
            posts = raw["saved_media"]
        elif "posts" in raw:
            posts = raw["posts"]
        elif "saves" in raw:
            posts = raw["saves"]
        else:
            posts = [raw]

    classified_counts: dict[str, int] = {}
    all_saves: list[ClassifiedSave] = []
    github_urls: list[str] = []

    for post in posts:
        # Extract URL from Instagram save structure
        url = ""
        title = ""

        if isinstance(post, dict):
            # Try common Instagram export field names
            url = post.get("href", "") or post.get("url", "") or post.get("link", "")
            # Look in nested string_map_data or media
            if not url and "string_map_data" in post:
                smd = post["string_map_data"]
                if isinstance(smd, dict):
                    for val in smd.values():
                        if isinstance(val, dict) and val.get("href"):
                            url = val["href"]
                            break
            title = post.get("title", post.get("caption", ""))
            if isinstance(title, dict):
                title = title.get("text", "") or title.get("value", "")

        if not url:
            continue

        save_type = _classify_url(url)
        classified_counts[save_type] = classified_counts.get(save_type, 0) + 1

        # Determine capability category based on type and content
        capability = "other"
        if save_type == "github":
            github_urls.append(url)
            # Will be categorized during evaluation
            capability = "software_creation"  # provisional

        classified_save = ClassifiedSave(
            url=url,
            save_type=save_type,
            title=str(title)[:200],
            capability_category=capability,
            metadata={"raw_post": post} if save_type == "github" else {},
        )
        all_saves.append(classified_save)

    # Evaluate GitHub repos as harness candidates
    harness_candidates: list[HarnessCandidate] = []
    for gh_url in github_urls:
        candidate = _evaluate_github_repo(gh_url)
        if candidate:
            harness_candidates.append(candidate)
            # Update the corresponding save's capability category
            for save in all_saves:
                if save.url == gh_url:
                    save.capability_category = candidate.capability_category
                    break

    # Sort candidates by overall score descending
    harness_candidates.sort(key=lambda c: c.overall_score, reverse=True)

    # Build placeholder comparison
    placeholder_comparison: dict[str, list[HarnessCandidate]] = {}
    for candidate in harness_candidates:
        cap = candidate.capability_category
        if cap in CURRENT_PLACEHOLDERS:
            if cap not in placeholder_comparison:
                placeholder_comparison[cap] = []
            placeholder_comparison[cap].append(candidate)

    report = InstagramCurationReport(
        total_saves=len(all_saves),
        classified=classified_counts,
        harness_candidates=harness_candidates,
        placeholder_comparison=placeholder_comparison,
        generated_at=datetime.now(tz=timezone.utc).isoformat(),
        all_saves=all_saves,
    )

    logger.info(
        "Instagram curation: %d saves, %d GitHub repos, %d harness candidates",
        report.total_saves,
        classified_counts.get("github", 0),
        len(harness_candidates),
    )

    return report


def saves_to_sources(report: InstagramCurationReport) -> list[InstagramSaveSource]:
    """Convert classified saves into Source objects for ingestion."""
    return [InstagramSaveSource(save) for save in report.all_saves]
