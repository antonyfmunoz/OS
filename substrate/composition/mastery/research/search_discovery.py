"""Deterministic search candidate generator for the Research Agent.

When registry + MCP discovery return nothing, we still need a way to
*propose* primary sources without hallucinating. This module generates
candidate URLs from explicit pattern families keyed off the tool slug.

Design principles (see CLAUDE.md "Tool Mastery Engine" + the
Operationalization Principle):

1. **No LLM, no search provider, no network.** Every candidate is
   constructed algorithmically from the slug. Nothing is "looked up",
   nothing is invented.
2. **Candidates are proposals, not claims.** A generated URL only
   means "this is where a source of kind X *would* live if it exists".
   The operator must approve before the fetcher ever touches it.
3. **Pattern families are explicit.** Adding a new family is a code
   change, visible in review. There is no hidden heuristic layer.
4. **Honest labelling.** Every candidate carries the family that
   produced it and a ``generated`` origin tag so downstream consumers
   can see it came from pattern expansion, not from the registry.

This module deliberately does NOT call :func:`discover_sources`;
composition is the agent's job.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable

from .models import SourceRef, SourceTier


# ---------------------------------------------------------------------------
# Slug normalisation
# ---------------------------------------------------------------------------


_SLUG_SPLIT = re.compile(r"[^a-z0-9]+")


def _tokenize(slug: str) -> list[str]:
    """Split a slug into lowercase tokens, dropping empty pieces."""
    return [t for t in _SLUG_SPLIT.split(slug.strip().lower()) if t]


def _join(tokens: Iterable[str], sep: str) -> str:
    return sep.join(t for t in tokens if t)


def _variants(slug: str) -> dict[str, str]:
    """Compute canonical textual variants of a slug.

    Returns a dict with:
        flat   -> "foobar"
        snake  -> "foo_bar"
        kebab  -> "foo-bar"
        dotted -> "foo.bar"   (useful for vendor domain guesses)
        head   -> first token only, e.g. "foo"
    """
    tokens = _tokenize(slug)
    if not tokens:
        return {"flat": "", "snake": "", "kebab": "", "dotted": "", "head": ""}
    return {
        "flat": _join(tokens, ""),
        "snake": _join(tokens, "_"),
        "kebab": _join(tokens, "-"),
        "dotted": _join(tokens, "."),
        "head": tokens[0],
    }


# ---------------------------------------------------------------------------
# Candidate dataclass
# ---------------------------------------------------------------------------


@dataclass
class Candidate:
    """A proposed source URL generated from a pattern family.

    Candidates are NOT SourceRefs until an operator approves them.
    Keeping the type distinct is load-bearing: it stops accidental
    plumbing of unapproved URLs into the fetcher.
    """

    url: str
    family: str  # e.g. "pypi", "npm", "github_repo_guess"
    tier: SourceTier
    rationale: str  # one-line "why we generated this"
    rank: int = 0  # lower = higher confidence within a family

    def to_dict(self) -> dict[str, object]:
        return {
            "url": self.url,
            "family": self.family,
            "tier": self.tier.value,
            "rationale": self.rationale,
            "rank": self.rank,
        }

    def to_source_ref(self) -> SourceRef:
        """Promote to a SourceRef after approval."""
        return SourceRef(
            url=self.url,
            tier=self.tier,
            label=f"{self.family} candidate",
            origin="generated",
        )


@dataclass
class CandidatePlan:
    """All generated candidates for a tool, plus the slug variants used."""

    tool_slug: str
    variants: dict[str, str] = field(default_factory=dict)
    candidates: list[Candidate] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "tool_slug": self.tool_slug,
            "variants": dict(self.variants),
            "candidates": [c.to_dict() for c in self.candidates],
            "notes": list(self.notes),
        }


# ---------------------------------------------------------------------------
# Pattern families
# ---------------------------------------------------------------------------
#
# Each family is a pure function: (variants) -> list[Candidate]. Adding
# a new family is a three-line change and is visible in code review.
# Ranks within a family are strictly for display ordering — the
# operator makes the actual decision.


def _family_pypi(v: dict[str, str]) -> list[Candidate]:
    out: list[Candidate] = []
    for rank, name in enumerate([v["snake"], v["kebab"], v["flat"]]):
        if not name:
            continue
        out.append(
            Candidate(
                url=f"https://pypi.org/project/{name}/",
                family="pypi",
                tier=SourceTier.OFFICIAL_PACKAGE,
                rationale=f"PyPI project page for '{name}'",
                rank=rank,
            )
        )
    return _dedupe(out)


def _family_npm(v: dict[str, str]) -> list[Candidate]:
    out: list[Candidate] = []
    for rank, name in enumerate([v["kebab"], v["flat"], v["snake"]]):
        if not name:
            continue
        out.append(
            Candidate(
                url=f"https://www.npmjs.com/package/{name}",
                family="npm",
                tier=SourceTier.OFFICIAL_PACKAGE,
                rationale=f"npm package page for '{name}'",
                rank=rank,
            )
        )
    return _dedupe(out)


def _family_github_search(v: dict[str, str]) -> list[Candidate]:
    """GitHub *search* URLs — safe because they never resolve to a
    fabricated repo. They always land on a real search results page.
    """
    query = v["kebab"] or v["flat"]
    if not query:
        return []
    return [
        Candidate(
            url=f"https://github.com/search?q={query}&type=repositories",
            family="github_search",
            tier=SourceTier.OFFICIAL_REPO,
            rationale=f"GitHub repository search for '{query}'",
            rank=0,
        ),
    ]


def _family_github_repo_guess(v: dict[str, str]) -> list[Candidate]:
    """Common 'vendor/tool' repo guesses.

    We only emit a handful of the most conventional shapes. These are
    *guesses* and are labelled as such in the rationale — the operator
    is expected to reject any that don't resolve.
    """
    out: list[Candidate] = []
    name = v["kebab"] or v["flat"]
    if not name:
        return out
    # vendor==tool pattern (very common for single-word projects)
    out.append(
        Candidate(
            url=f"https://github.com/{name}/{name}",
            family="github_repo_guess",
            tier=SourceTier.OFFICIAL_REPO,
            rationale=f"conventional '{name}/{name}' repo guess (verify before trust)",
            rank=0,
        )
    )
    # first-token org, full kebab repo
    if v["head"] and v["head"] != name:
        out.append(
            Candidate(
                url=f"https://github.com/{v['head']}/{name}",
                family="github_repo_guess",
                tier=SourceTier.OFFICIAL_REPO,
                rationale=f"conventional '{v['head']}/{name}' repo guess",
                rank=1,
            )
        )
    return _dedupe(out)


def _family_vendor_domain(v: dict[str, str]) -> list[Candidate]:
    """Guess canonical vendor site and docs subdomain.

    These are *structurally* canonical — e.g. `docs.<tool>.com` is a
    real convention — but they are guesses: the domain may not exist
    or may belong to someone else. Operator must verify.
    """
    out: list[Candidate] = []
    base = v["flat"] or v["kebab"].replace("-", "")
    if not base:
        return out
    out.extend(
        [
            Candidate(
                url=f"https://{base}.com",
                family="vendor_domain",
                tier=SourceTier.OFFICIAL_DOCS,
                rationale=f"guessed vendor site '{base}.com'",
                rank=0,
            ),
            Candidate(
                url=f"https://docs.{base}.com",
                family="vendor_domain",
                tier=SourceTier.OFFICIAL_DOCS,
                rationale=f"guessed docs subdomain 'docs.{base}.com'",
                rank=1,
            ),
            Candidate(
                url=f"https://www.{base}.com/docs",
                family="vendor_domain",
                tier=SourceTier.OFFICIAL_DOCS,
                rationale=f"guessed docs path 'www.{base}.com/docs'",
                rank=2,
            ),
            Candidate(
                url=f"https://{base}.io",
                family="vendor_domain",
                tier=SourceTier.OFFICIAL_DOCS,
                rationale=f"guessed vendor site '{base}.io' (common for dev tools)",
                rank=3,
            ),
            Candidate(
                url=f"https://{base}.ai",
                family="vendor_domain",
                tier=SourceTier.OFFICIAL_DOCS,
                rationale=f"guessed vendor site '{base}.ai' (common for AI tools)",
                rank=4,
            ),
        ]
    )
    return out


def _family_api_reference(v: dict[str, str]) -> list[Candidate]:
    """Canonical API reference subpaths under a guessed docs host."""
    base = v["flat"]
    if not base:
        return []
    return [
        Candidate(
            url=f"https://docs.{base}.com/api",
            family="api_reference",
            tier=SourceTier.OFFICIAL_API_REF,
            rationale=f"guessed API reference at 'docs.{base}.com/api'",
            rank=0,
        ),
        Candidate(
            url=f"https://docs.{base}.com/reference",
            family="api_reference",
            tier=SourceTier.OFFICIAL_API_REF,
            rationale=f"guessed API reference at 'docs.{base}.com/reference'",
            rank=1,
        ),
    ]


_FAMILIES = (
    _family_vendor_domain,
    _family_api_reference,
    _family_github_search,
    _family_github_repo_guess,
    _family_pypi,
    _family_npm,
)


def _dedupe(candidates: list[Candidate]) -> list[Candidate]:
    """Drop duplicate URLs while preserving first occurrence order."""
    seen: set[str] = set()
    out: list[Candidate] = []
    for c in candidates:
        if c.url in seen:
            continue
        seen.add(c.url)
        out.append(c)
    return out


def generate_candidates(tool_slug: str) -> CandidatePlan:
    """Run every pattern family against the slug and return a plan.

    Ordering: the returned ``candidates`` list is grouped by family in
    the order declared in ``_FAMILIES`` (vendor first, then API, then
    GitHub, then packages). Within each family, lower ``rank`` wins.
    """
    plan = CandidatePlan(tool_slug=tool_slug)
    variants = _variants(tool_slug)
    plan.variants = variants

    if not any(variants.values()):
        plan.notes.append(f"slug {tool_slug!r} produced no usable tokens")
        return plan

    collected: list[Candidate] = []
    for family_fn in _FAMILIES:
        family_candidates = family_fn(variants)
        family_candidates.sort(key=lambda c: c.rank)
        collected.extend(family_candidates)

    plan.candidates = _dedupe(collected)
    plan.notes.append(
        f"generated {len(plan.candidates)} candidates across "
        f"{len({c.family for c in plan.candidates})} families — "
        "none have been fetched; operator approval required"
    )
    return plan
