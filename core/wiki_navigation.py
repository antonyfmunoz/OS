"""
Wiki Navigation Layer — bridges graph nodes and Obsidian wiki pages.

Provides:
    WikiIndex       — deterministic mapping between graph nodes and wiki pages
    enrich_candidates(candidates, wiki_index) -> candidates with wiki metadata
    wiki_traverse(candidates, wiki_index, max_expansions) -> expanded node IDs
    wiki_rerank_bonus(candidate, wiki_index) -> float bonus in [0, max_bonus]

Contract:
    - Semantic space decides where to look first
    - Wiki layer adds human-curated navigational signal
    - Graph still decides what is true
    - Wiki traversal never overrides graph truth
    - Wiki traversal never explodes context size
"""

import re
import sys
from pathlib import Path

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

WIKI_DIR = Path("/opt/OS/10_Wiki")
VAULT_DIR = Path("/opt/OS/vault")
SUMMARIES_DIR = VAULT_DIR / "memory" / "summaries"

# Wiki knowledge subdirs (not codebase/ or palace/)
_KNOWLEDGE_SUBDIRS = ("concepts", "entities", "decisions", "synthesis")

# Operational files that should not receive wiki bonus
_OPERATIONAL_PATTERNS = re.compile(
    r"(index|log|WIKI_RULES|cloud_palace|retrieval_rules|cloud|daily|dashboard|template)",
    re.I,
)

# Max wiki bonus applied during reranking (bounded)
WIKI_BONUS_MAX = 0.06

# Traversal limits
MAX_TRAVERSAL_EXPANSIONS = 3
MAX_TRAVERSAL_HOPS = 1


# ---------------------------------------------------------------------------
# WikiIndex — lazy, deterministic, no LLM
# ---------------------------------------------------------------------------


class WikiIndex:
    """Bidirectional index between graph nodes and wiki knowledge pages.

    Sources:
        1. Summary promoted_to fields (summary → wiki slug → graph nodes)
        2. Wiki page wikilinks (wiki page → referenced graph nodes)
        3. Wiki page slug → graph node substring match
    """

    def __init__(self) -> None:
        self._built = False
        # wiki_slug -> wiki page path (relative to /opt/OS)
        self.slug_to_path: dict[str, str] = {}
        # wiki_slug -> list of graph node IDs it references/promotes
        self.slug_to_nodes: dict[str, list[str]] = {}
        # graph node_id -> wiki_slug (if mapped)
        self.node_to_slug: dict[str, str] = {}
        # wiki_slug -> set of outgoing wikilink targets (slugs)
        self.slug_outgoing: dict[str, set[str]] = {}
        # wiki_slug -> count of incoming links from other wiki pages
        self.slug_incoming_count: dict[str, int] = {}
        # wiki_slug -> bool: has a summary with promoted_to pointing here
        self.slug_has_promotion: dict[str, bool] = {}

    def build(self, graph: dict | None = None) -> "WikiIndex":
        """Build the index. Cheap — file scan only, no embeddings."""
        if self._built:
            return self
        self._scan_wiki_pages()
        self._scan_summaries()
        if graph is not None:
            self._map_nodes_to_wiki(graph)
        self._compute_incoming_counts()
        self._built = True
        return self

    def _scan_wiki_pages(self) -> None:
        """Index all wiki knowledge pages and their outgoing wikilinks."""
        for subdir in _KNOWLEDGE_SUBDIRS:
            d = WIKI_DIR / subdir
            if not d.exists():
                continue
            for md in d.glob("*.md"):
                slug = md.stem
                rel_path = str(md.relative_to(Path("/opt/OS")))
                self.slug_to_path[slug] = rel_path
                self.slug_to_nodes.setdefault(slug, [])

                try:
                    content = md.read_text(encoding="utf-8")
                except Exception:
                    continue
                # Extract outgoing [[wikilinks]]
                links = {m.strip() for m in re.findall(r"\[\[([^\]|#]+)", content)}
                self.slug_outgoing[slug] = links

    def _scan_summaries(self) -> None:
        """Parse promoted_to from summary frontmatter."""
        if not SUMMARIES_DIR.exists():
            return
        for md in SUMMARIES_DIR.glob("*.md"):
            try:
                content = md.read_text(encoding="utf-8")
            except Exception:
                continue
            fm = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
            if not fm:
                continue
            promoted: list[str] = []
            in_promoted = False
            for line in fm.group(1).split("\n"):
                if line.startswith("promoted_to:"):
                    in_promoted = True
                    continue
                if in_promoted:
                    if line.startswith("- "):
                        promoted.append(line[2:].strip())
                    else:
                        in_promoted = False
            for slug in promoted:
                self.slug_has_promotion[slug] = True

    def _map_nodes_to_wiki(self, graph: dict) -> None:
        """Map graph node IDs to wiki slugs via deterministic rules.

        Rules (applied in priority order):
        1. Wiki page wikilinks that reference a file path → direct mapping
        2. Slug substring match against node ID (e.g. 'memory-pipeline' matches
           nodes containing 'memory' in the path)
        3. Summary promoted_to → nodes related to that concept area

        Only files section is mapped (classes/functions inherit from parent file).
        """
        graph_files = set(graph.get("files", {}).keys())

        for slug, outgoing in self.slug_outgoing.items():
            for link in outgoing:
                # Direct file reference: [[eos_ai/memory.py]] or similar
                normalized = link.replace("/", "/")
                if normalized in graph_files:
                    if normalized not in self.node_to_slug:
                        self.node_to_slug[normalized] = slug
                    if normalized not in self.slug_to_nodes.get(slug, []):
                        self.slug_to_nodes.setdefault(slug, []).append(normalized)

        # Keyword mapping: wiki slug components → matching file nodes
        for slug in self.slug_to_path:
            # Split slug into keywords (e.g. 'memory-pipeline' → ['memory', 'pipeline'])
            keywords = [k for k in slug.split("-") if len(k) > 3]
            if not keywords:
                continue
            for node_id in graph_files:
                # Node ID is a file path like eos_ai/memory.py
                node_lower = node_id.lower()
                if any(kw in node_lower for kw in keywords):
                    if node_id not in self.node_to_slug:
                        self.node_to_slug[node_id] = slug
                    if node_id not in self.slug_to_nodes.get(slug, []):
                        self.slug_to_nodes.setdefault(slug, []).append(node_id)

    def _compute_incoming_counts(self) -> None:
        """Count incoming wikilinks for each wiki slug."""
        counts: dict[str, int] = {slug: 0 for slug in self.slug_to_path}
        for slug, outgoing in self.slug_outgoing.items():
            for target in outgoing:
                # Normalize: [[summaries/foo]] → take final component
                targets = [target]
                if "/" in target:
                    targets.append(target.rsplit("/", 1)[-1])
                for t in targets:
                    if t in counts:
                        counts[t] += 1
        self.slug_incoming_count = counts

    # -- Public query methods ------------------------------------------------

    def get_wiki_for_node(self, node_id: str) -> dict | None:
        """Return wiki metadata for a graph node, or None."""
        slug = self.node_to_slug.get(node_id)
        if not slug:
            return None
        return {
            "wiki_slug": slug,
            "wiki_path": self.slug_to_path.get(slug, ""),
            "outgoing_wikilinks": sorted(self.slug_outgoing.get(slug, set())),
            "incoming_link_count": self.slug_incoming_count.get(slug, 0),
            "promoted_summary_present": self.slug_has_promotion.get(slug, False),
        }

    def get_nodes_for_slug(self, slug: str) -> list[str]:
        """Return graph node IDs mapped to a wiki slug."""
        return self.slug_to_nodes.get(slug, [])

    def is_operational(self, slug: str) -> bool:
        """True if this slug is an operational/meta file (no bonus)."""
        return bool(_OPERATIONAL_PATTERNS.search(slug))


# ---------------------------------------------------------------------------
# Enrichment — attach wiki metadata to candidates
# ---------------------------------------------------------------------------


def enrich_candidates(
    candidates: list[dict],
    wiki_index: WikiIndex,
) -> list[dict]:
    """Attach wiki metadata to each candidate (non-destructive enrichment).

    Adds 'wiki' key to candidates that have a mapped wiki page.
    Candidates without a mapping get wiki=None.
    """
    for c in candidates:
        c["wiki"] = wiki_index.get_wiki_for_node(c["node_id"])
    return candidates


# ---------------------------------------------------------------------------
# Traversal — bounded 1-hop wiki expansion
# ---------------------------------------------------------------------------


def wiki_traverse(
    candidates: list[dict],
    wiki_index: WikiIndex,
    max_expansions: int = MAX_TRAVERSAL_EXPANSIONS,
) -> list[str]:
    """Traverse 1 hop through wikilinks from top wiki-mapped candidates.

    Returns additional node IDs discovered via wiki navigation.
    Capped aggressively. Ignores operational pages.

    Only considers candidates that have wiki mappings.
    Traverses outgoing wikilinks from their mapped wiki pages.
    For each linked wiki page, returns its mapped graph nodes.
    """
    expansion_node_ids: list[str] = []
    existing_ids = {c["node_id"] for c in candidates}
    expansions_used = 0

    for c in candidates:
        if expansions_used >= max_expansions:
            break
        wiki = c.get("wiki")
        if not wiki:
            continue

        slug = wiki["wiki_slug"]
        outgoing = wiki_index.slug_outgoing.get(slug, set())

        for linked_slug in outgoing:
            if expansions_used >= max_expansions:
                break
            # Skip operational pages
            if wiki_index.is_operational(linked_slug):
                continue
            # Skip if not a known wiki knowledge page
            if linked_slug not in wiki_index.slug_to_path:
                continue

            # Get graph nodes mapped to this linked wiki page
            linked_nodes = wiki_index.get_nodes_for_slug(linked_slug)
            for nid in linked_nodes:
                if nid not in existing_ids:
                    expansion_node_ids.append(nid)
                    existing_ids.add(nid)
                    expansions_used += 1
                    if expansions_used >= max_expansions:
                        break

    return expansion_node_ids


# ---------------------------------------------------------------------------
# Rerank bonus — bounded wiki signal
# ---------------------------------------------------------------------------


def wiki_rerank_bonus(candidate: dict) -> float:
    """Compute a bounded rerank bonus from wiki signal.

    Returns a float in [0, WIKI_BONUS_MAX].

    Bonus components:
        - has_wiki_page:          0.02  (curated knowledge exists)
        - promoted_summary:       0.02  (editorial bridge exists)
        - meaningful_links:       0.01  (outgoing navigational links)
        - incoming_authority:     0.01  (other pages link here)

    Total max = 0.06, which is enough to prefer curated knowledge
    when tied but not enough to override better semantic/graph matches.
    """
    wiki = candidate.get("wiki")
    if not wiki:
        return 0.0

    bonus = 0.0

    # Has a wiki page at all
    bonus += 0.02

    # Has promoted summary (editorial bridge from conversation → wiki)
    if wiki.get("promoted_summary_present"):
        bonus += 0.02

    # Has meaningful outgoing links (navigational value)
    outgoing = wiki.get("outgoing_wikilinks", [])
    if len(outgoing) >= 2:
        bonus += 0.01

    # Has incoming authority (other pages reference this)
    incoming = wiki.get("incoming_link_count", 0)
    if incoming >= 1:
        bonus += 0.01

    return min(bonus, WIKI_BONUS_MAX)
