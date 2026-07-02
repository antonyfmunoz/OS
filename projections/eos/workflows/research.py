"""Research workflow — governed research with outcome tracking.

Steps: define_question → gather_sources → synthesize → store_findings

Deterministic-first: keyword extraction and source selection are
rule-based. AI enhances synthesis when available.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from projections.eos.workflows.types import WorkflowStep

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")
_FINDINGS_DIR = os.path.join(_REPO_ROOT, "data", "umh", "research")


@dataclass
class ResearchQuery:
    topic: str
    keywords: list[str] = field(default_factory=list)
    scope: str = "broad"
    depth: str = "standard"


@dataclass
class ResearchFinding:
    source: str
    content: str
    relevance: float = 0.0


class ResearchWorkflow:
    """Multi-step research workflow through governed mutation."""

    def __init__(self, org_id: str = "", venture_id: str = "") -> None:
        self._org_id = org_id
        self._venture_id = venture_id
        self._query: ResearchQuery | None = None
        self._findings: list[ResearchFinding] = []
        self._synthesis: str = ""

    def steps(self, topic: str) -> list[WorkflowStep]:
        return [
            WorkflowStep(
                name="define_question",
                mutation_name="command_submit",
                intent=f"Define research question: {topic[:80]}",
                execute_fn=lambda: self._define_question(topic),
            ),
            WorkflowStep(
                name="gather_sources",
                mutation_name="command_submit",
                intent=f"Gather sources for: {topic[:80]}",
                execute_fn=self._gather_sources,
            ),
            WorkflowStep(
                name="synthesize",
                mutation_name="command_submit",
                intent=f"Synthesize research on: {topic[:80]}",
                execute_fn=self._synthesize,
            ),
            WorkflowStep(
                name="store_findings",
                mutation_name="file_write",
                intent=f"Store research findings: {topic[:80]}",
                execute_fn=self._store_findings,
            ),
        ]

    def _define_question(self, topic: str) -> tuple[str, bool]:
        keywords = self._extract_keywords(topic)
        scope = "deep" if len(keywords) <= 2 else "broad"
        self._query = ResearchQuery(
            topic=topic,
            keywords=keywords,
            scope=scope,
        )
        return (
            f"Research defined: {topic} "
            f"(keywords: {', '.join(keywords)}, scope: {scope})",
            True,
        )

    def _gather_sources(self) -> tuple[str, bool]:
        if not self._query:
            return ("no research question defined", False)

        self._findings = []

        wiki_findings = self._search_knowledge_base(self._query.keywords)
        self._findings.extend(wiki_findings)

        doc_findings = self._search_docs(self._query.keywords)
        self._findings.extend(doc_findings)

        if not self._findings:
            self._findings.append(ResearchFinding(
                source="none",
                content=f"No local sources found for: {self._query.topic}",
                relevance=0.0,
            ))

        return (
            f"Gathered {len(self._findings)} findings from local sources",
            True,
        )

    def _synthesize(self) -> tuple[str, bool]:
        if not self._query or not self._findings:
            return ("no findings to synthesize", False)

        parts = [f"# Research: {self._query.topic}\n"]
        parts.append(f"**Keywords**: {', '.join(self._query.keywords)}\n")
        parts.append(f"**Sources found**: {len(self._findings)}\n")

        for i, finding in enumerate(self._findings, 1):
            parts.append(
                f"\n## Finding {i} (from {finding.source})\n"
                f"{finding.content[:500]}\n"
            )

        self._synthesis = "\n".join(parts)

        try:
            from adapters.models.model_router import call_with_fallback

            result = call_with_fallback(
                prompt=(
                    f"Synthesize these research findings into a concise summary:\n\n"
                    f"{self._synthesis[:3000]}\n\n"
                    f"Provide: key insights, gaps, and recommended next steps."
                ),
                system="You are a research synthesizer. Be direct and specific.",
                task_type="fast_response",
            )
            if result.output and len(result.output.strip()) > 50:
                self._synthesis += f"\n\n## AI Synthesis\n{result.output.strip()}"
        except Exception:
            self._synthesis += "\n\n## Summary\nAI synthesis unavailable. Review findings above."

        return (f"Synthesized {len(self._findings)} findings", True)

    def _store_findings(self) -> tuple[str, bool]:
        if not self._query or not self._synthesis:
            return ("nothing to store", False)

        os.makedirs(_FINDINGS_DIR, exist_ok=True)
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        slug = re.sub(r"[^a-z0-9]+", "_", self._query.topic.lower())[:40]
        filename = f"{date_str}_{slug}.md"
        filepath = os.path.join(_FINDINGS_DIR, filename)

        with open(filepath, "w") as f:
            f.write(self._synthesis)

        return (f"Findings stored: {filepath}", True)

    def _extract_keywords(self, topic: str) -> list[str]:
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "shall", "can",
            "of", "in", "to", "for", "with", "on", "at", "by", "from",
            "about", "into", "through", "during", "before", "after",
            "and", "but", "or", "not", "no", "so", "if", "then", "than",
            "what", "how", "why", "when", "where", "who", "which",
            "this", "that", "these", "those", "i", "me", "my", "we",
            "our", "you", "your", "it", "its", "they", "them", "their",
        }
        words = re.findall(r"[a-z]+", topic.lower())
        return [w for w in words if w not in stop_words and len(w) > 2][:8]

    def _search_knowledge_base(self, keywords: list[str]) -> list[ResearchFinding]:
        findings = []
        wiki_dir = os.path.join(_REPO_ROOT, "knowledge")
        if not os.path.isdir(wiki_dir):
            return findings

        for root, _, files in os.walk(wiki_dir):
            if "__pycache__" in root:
                continue
            for f in files:
                if not f.endswith(".md"):
                    continue
                path = os.path.join(root, f)
                try:
                    with open(path) as fh:
                        content = fh.read()
                    matches = sum(1 for kw in keywords if kw in content.lower())
                    if matches >= 1:
                        rel = os.path.relpath(path, _REPO_ROOT)
                        excerpt = content[:300].replace("\n", " ")
                        findings.append(ResearchFinding(
                            source=f"knowledge/{rel}",
                            content=excerpt,
                            relevance=matches / len(keywords),
                        ))
                except OSError:
                    continue

        findings.sort(key=lambda f: f.relevance, reverse=True)
        return findings[:10]

    def _search_docs(self, keywords: list[str]) -> list[ResearchFinding]:
        findings = []
        docs_dir = os.path.join(_REPO_ROOT, "docs")
        if not os.path.isdir(docs_dir):
            return findings

        for root, _, files in os.walk(docs_dir):
            if "__pycache__" in root:
                continue
            for f in files:
                if not f.endswith(".md"):
                    continue
                path = os.path.join(root, f)
                try:
                    with open(path) as fh:
                        content = fh.read()
                    matches = sum(1 for kw in keywords if kw in content.lower())
                    if matches >= 2:
                        rel = os.path.relpath(path, _REPO_ROOT)
                        excerpt = content[:300].replace("\n", " ")
                        findings.append(ResearchFinding(
                            source=f"docs/{rel}",
                            content=excerpt,
                            relevance=matches / len(keywords),
                        ))
                except OSError:
                    continue

        findings.sort(key=lambda f: f.relevance, reverse=True)
        return findings[:5]
