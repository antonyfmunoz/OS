"""Context Resolution Engine — "the system already knows" layer.

Resolves operator natural language into fully qualified context from the
Reality Graph. When the operator mentions a project name, this engine
resolves project, repo, workspace, device, documents — without discovery
questions.

Resolution is entirely deterministic: regex extraction, exact/fuzzy name
match, BFS graph traversal. Zero LLM dependency.

Campaign 5.5. UMH substrate layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ── Types ─────────────────────────────────────────────────────────────────


class ResolutionStrategy(str, Enum):
    EXACT_MATCH = "exact_match"
    PATTERN_MATCH = "pattern_match"
    GRAPH_WALK = "graph_walk"
    RECENCY_BIAS = "recency_bias"
    ACTIVE_CONTEXT = "active_context"


@dataclass
class ResolvedContext:
    project_id: str = ""
    project_name: str = ""
    repository_id: str = ""
    repository_name: str = ""
    workspace_id: str = ""
    workspace_name: str = ""
    device_id: str = ""
    active_device: str = ""
    projection: str = ""
    documents: list[dict[str, Any]] = field(default_factory=list)
    infrastructure: list[dict[str, Any]] = field(default_factory=list)
    # Campaign 6 — Operational Reality Model fields
    files: list[dict[str, Any]] = field(default_factory=list)
    decisions: list[dict[str, Any]] = field(default_factory=list)
    active_work: list[dict[str, Any]] = field(default_factory=list)
    approvals: list[dict[str, Any]] = field(default_factory=list)
    constraints: list[dict[str, Any]] = field(default_factory=list)
    knowledge: list[dict[str, Any]] = field(default_factory=list)
    goals: list[dict[str, Any]] = field(default_factory=list)
    unresolved_references: list[str] = field(default_factory=list)
    resolution_chain: list[dict[str, str]] = field(default_factory=list)
    confidence: float = 0.0
    strategy: ResolutionStrategy = ResolutionStrategy.EXACT_MATCH
    resolved_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "project_name": self.project_name,
            "repository_id": self.repository_id,
            "repository_name": self.repository_name,
            "workspace_id": self.workspace_id,
            "workspace_name": self.workspace_name,
            "device_id": self.device_id,
            "active_device": self.active_device,
            "projection": self.projection,
            "documents": self.documents,
            "infrastructure": self.infrastructure,
            "files": self.files,
            "decisions": self.decisions,
            "active_work": self.active_work,
            "approvals": self.approvals,
            "constraints": self.constraints,
            "knowledge": self.knowledge,
            "goals": self.goals,
            "unresolved_references": self.unresolved_references,
            "resolution_chain": self.resolution_chain,
            "confidence": self.confidence,
            "strategy": self.strategy.value,
            "resolved_at": self.resolved_at,
        }

    @property
    def is_resolved(self) -> bool:
        return bool(self.project_id or self.repository_id or self.workspace_id)


# ── Tokenizer ─────────────────────────────────────────────────────────────

_STOP_WORDS = frozenset({
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "to", "of", "in",
    "for", "on", "with", "at", "by", "from", "as", "into", "through",
    "during", "before", "after", "above", "below", "between", "out", "off",
    "up", "down", "and", "but", "or", "nor", "not", "so", "yet", "both",
    "each", "few", "more", "most", "other", "some", "such", "no", "only",
    "same", "than", "too", "very", "just", "about", "use", "using", "check",
    "deploy", "build", "add", "set", "get", "make", "let", "run", "fix",
    "update", "create", "start", "stop", "show", "tell", "give", "take",
    "i", "me", "my", "we", "our", "you", "your", "it", "its", "this",
    "that", "these", "those", "what", "which", "who", "whom", "how",
    "when", "where", "why",
})


def _extract_candidate_names(text: str) -> list[str]:
    """Extract potential entity names from natural language input."""
    candidates: list[str] = []

    quoted = re.findall(r'"([^"]+)"', text)
    candidates.extend(quoted)

    capitalized = re.findall(r'\b([A-Z][a-zA-Z0-9]*(?:\s+[A-Z][a-zA-Z0-9]*)*)\b', text)
    candidates.extend(capitalized)

    words = re.findall(r'\b([a-zA-Z][a-zA-Z0-9_-]{2,})\b', text)
    for word in words:
        if word.lower() not in _STOP_WORDS and word not in candidates:
            candidates.append(word)

    seen: set[str] = set()
    unique: list[str] = []
    for c in candidates:
        lower = c.lower()
        if lower not in seen:
            seen.add(lower)
            unique.append(c)
    return unique


# ── Context Resolution Engine ─────────────────────────────────────────────


class ContextResolutionEngine:
    """Resolves operator input into fully qualified context via RealityGraph."""

    def __init__(
        self,
        reality_graph: Any = None,
        workspace_awareness: Any = None,
        project_registry: Any = None,
        device_awareness: Any = None,
        repository_runtime: Any = None,
        documentation_runtime: Any = None,
        runtime_awareness: Any = None,
        knowledge_runtime: Any = None,
        goal_registry: Any = None,
        decision_registry: Any = None,
    ) -> None:
        self._graph = reality_graph
        self._workspace = workspace_awareness
        self._projects = project_registry
        self._devices = device_awareness
        self._repo_runtime = repository_runtime
        self._doc_runtime = documentation_runtime
        self._runtime_awareness = runtime_awareness
        self._knowledge_runtime = knowledge_runtime
        self._goal_registry = goal_registry
        self._decision_registry = decision_registry

    def resolve(self, text: str) -> ResolvedContext:
        """Main entry: natural language → fully resolved context."""
        ctx = ResolvedContext(resolved_at=time.time())
        candidates = _extract_candidate_names(text)

        if not candidates:
            ctx.confidence = 0.0
            return ctx

        self._resolve_from_candidates(candidates, ctx)
        self._enrich_from_graph(ctx)
        self._enrich_from_runtimes(ctx)
        self._resolve_goals(candidates, ctx)
        self._resolve_decisions(ctx)
        self._merge_active_context(ctx)
        self._compute_confidence(ctx)

        return ctx

    def resolve_entity_reference(self, name: str) -> list[dict[str, Any]]:
        """Find entities matching a text reference. Deterministic."""
        if self._graph is None:
            return []
        entities = self._graph.find_by_name(name)
        return [e.to_dict() for e in entities]

    def populate_orchestrator_context(
        self,
        orchestrator_ctx: Any,
        resolved: ResolvedContext,
    ) -> None:
        """Inject resolved context into OrchestratorContext fields."""
        if resolved.project_name:
            orchestrator_ctx.active_project = resolved.project_name
        if resolved.repository_name:
            orchestrator_ctx.active_repo = resolved.repository_name
        if resolved.workspace_name:
            # active_projection maps to the workspace/projection
            pass
        if resolved.projection:
            orchestrator_ctx.active_projection = resolved.projection
        if resolved.device_id:
            orchestrator_ctx.preferred_execution_device = resolved.device_id
        if resolved.active_device:
            orchestrator_ctx.active_device = resolved.active_device

    # ── Internal resolution steps ─────────────────────────────────────

    def _resolve_from_candidates(
        self,
        candidates: list[str],
        ctx: ResolvedContext,
    ) -> None:
        """Try to resolve each candidate name against known entities."""
        for candidate in candidates:
            resolved = False

            if self._projects is not None:
                project = self._projects.find_by_name(candidate)
                if project is not None and not ctx.project_id:
                    ctx.project_id = project.project_id
                    ctx.project_name = project.name
                    ctx.projection = getattr(project, "projection", "")
                    ctx.strategy = ResolutionStrategy.EXACT_MATCH
                    ctx.resolution_chain.append({
                        "step": "project_registry_match",
                        "candidate": candidate,
                        "resolved_to": project.project_id,
                    })
                    resolved = True

            if self._graph is not None and not resolved:
                entities = self._graph.find_by_name(candidate)
                if entities:
                    for entity in entities:
                        etype = entity.entity_type.value if hasattr(entity.entity_type, "value") else str(entity.entity_type)
                        if etype == "project" and not ctx.project_id:
                            ctx.project_id = entity.source_id
                            ctx.project_name = entity.name
                            ctx.strategy = ResolutionStrategy.PATTERN_MATCH
                            ctx.resolution_chain.append({
                                "step": "graph_name_match",
                                "candidate": candidate,
                                "resolved_to": entity.entity_id,
                                "entity_type": etype,
                            })
                            resolved = True
                        elif etype == "repository" and not ctx.repository_id:
                            ctx.repository_id = entity.source_id
                            ctx.repository_name = entity.name
                            ctx.resolution_chain.append({
                                "step": "graph_name_match",
                                "candidate": candidate,
                                "resolved_to": entity.entity_id,
                                "entity_type": etype,
                            })
                            resolved = True
                        elif etype == "workspace" and not ctx.workspace_id:
                            ctx.workspace_id = entity.source_id
                            ctx.workspace_name = entity.name
                            ctx.resolution_chain.append({
                                "step": "graph_name_match",
                                "candidate": candidate,
                                "resolved_to": entity.entity_id,
                                "entity_type": etype,
                            })
                            resolved = True
                        elif etype == "device" and not ctx.device_id:
                            ctx.device_id = entity.source_id
                            ctx.resolution_chain.append({
                                "step": "graph_name_match",
                                "candidate": candidate,
                                "resolved_to": entity.entity_id,
                                "entity_type": etype,
                            })
                            resolved = True

            if not resolved:
                ctx.unresolved_references.append(candidate)

    def _enrich_from_graph(self, ctx: ResolvedContext) -> None:
        """Walk the graph to fill missing context from what we already resolved."""
        if self._graph is None:
            return

        if ctx.project_id and not ctx.repository_id:
            from substrate.organism.reality_graph import RealityRelationType
            neighbors = self._graph.neighbors(
                f"proj-{ctx.project_id}",
                RealityRelationType.CONTAINS,
            )
            for n in neighbors:
                etype = n.entity_type.value if hasattr(n.entity_type, "value") else str(n.entity_type)
                if etype == "repository":
                    ctx.repository_id = n.source_id
                    ctx.repository_name = n.name
                    ctx.strategy = ResolutionStrategy.GRAPH_WALK
                    ctx.resolution_chain.append({
                        "step": "graph_walk_project_to_repo",
                        "from": f"proj-{ctx.project_id}",
                        "resolved_to": n.entity_id,
                    })
                    break

        if ctx.project_id and not ctx.device_id:
            from substrate.organism.reality_graph import RealityRelationType
            neighbors = self._graph.neighbors(
                f"proj-{ctx.project_id}",
                RealityRelationType.DEPLOYED_TO,
            )
            for n in neighbors:
                etype = n.entity_type.value if hasattr(n.entity_type, "value") else str(n.entity_type)
                if etype == "device":
                    ctx.device_id = n.source_id
                    ctx.resolution_chain.append({
                        "step": "graph_walk_project_to_device",
                        "from": f"proj-{ctx.project_id}",
                        "resolved_to": n.entity_id,
                    })
                    break

        if ctx.repository_id and not ctx.workspace_id:
            from substrate.organism.reality_graph import RealityRelationType
            repo_entity_id = f"repo-{ctx.repository_id}"
            neighbors = self._graph.neighbors(
                repo_entity_id,
                RealityRelationType.CONTAINS,
            )
            for n in neighbors:
                etype = n.entity_type.value if hasattr(n.entity_type, "value") else str(n.entity_type)
                if etype == "workspace":
                    ctx.workspace_id = n.source_id
                    ctx.workspace_name = n.name
                    ctx.resolution_chain.append({
                        "step": "graph_walk_repo_to_workspace",
                        "from": repo_entity_id,
                        "resolved_to": n.entity_id,
                    })
                    break

        if ctx.project_id and not ctx.projection:
            if self._projects is not None:
                project = self._projects.get(ctx.project_id)
                if project and getattr(project, "projection", ""):
                    ctx.projection = project.projection

        if ctx.project_id:
            from substrate.organism.reality_graph import RealityRelationType
            infra_neighbors = self._graph.neighbors(
                f"proj-{ctx.project_id}",
                RealityRelationType.DEPENDS_ON,
            )
            for n in infra_neighbors:
                ctx.infrastructure.append({"entity_id": n.entity_id, "name": n.name})

    def _enrich_from_runtimes(self, ctx: ResolvedContext) -> None:
        """Enrich context from C6 operational reality runtimes."""
        project_entity_id = f"proj-{ctx.project_id}" if ctx.project_id else ""

        if self._repo_runtime is not None and ctx.project_id:
            try:
                if hasattr(self._repo_runtime, "find_files_for_entity") and project_entity_id:
                    files = self._repo_runtime.find_files_for_entity(project_entity_id)
                    ctx.files = [
                        f.to_dict() if hasattr(f, "to_dict") else f
                        for f in files
                    ]
                elif hasattr(self._repo_runtime, "snapshot"):
                    snap = self._repo_runtime.snapshot()
                    if snap and snap.get("important_files"):
                        ctx.files = snap["important_files"][:10]
                ctx.resolution_chain.append({"step": "repo_runtime_enrichment", "files_found": str(len(ctx.files))})
            except Exception as exc:
                logger.debug("Repository runtime enrichment failed: %s", exc)

        if self._doc_runtime is not None and ctx.project_id:
            try:
                if hasattr(self._doc_runtime, "find_docs_for_entity") and project_entity_id:
                    docs = self._doc_runtime.find_docs_for_entity(project_entity_id)
                    for doc in docs:
                        doc_dict = doc.to_dict() if hasattr(doc, "to_dict") else doc
                        ctx.documents.append(doc_dict)
                        if doc_dict.get("decision_count", 0) > 0:
                            ctx.decisions.append({
                                "source_doc": doc_dict.get("name", ""),
                                "decision_count": doc_dict.get("decision_count", 0),
                            })
                        if doc_dict.get("constraint_count", 0) > 0:
                            for _ in range(doc_dict.get("constraint_count", 0)):
                                ctx.constraints.append({
                                    "source_doc": doc_dict.get("name", ""),
                                })
                ctx.resolution_chain.append({"step": "doc_runtime_enrichment", "docs_found": str(len(ctx.documents))})
            except Exception as exc:
                logger.debug("Documentation runtime enrichment failed: %s", exc)

        if self._runtime_awareness is not None:
            try:
                active = self._runtime_awareness.active_work()
                ctx.active_work = active[:10]
                ctx.resolution_chain.append({"step": "runtime_awareness_enrichment", "active_work": str(len(ctx.active_work))})
            except Exception as exc:
                logger.debug("Runtime awareness enrichment failed: %s", exc)

        if self._knowledge_runtime is not None and ctx.project_id:
            try:
                if hasattr(self._knowledge_runtime, "find_for_entity") and project_entity_id:
                    entries = self._knowledge_runtime.find_for_entity(project_entity_id)
                    for entry in entries:
                        entry_dict = entry.to_dict() if hasattr(entry, "to_dict") else entry
                        ctx.knowledge.append(entry_dict)
                        if entry_dict.get("knowledge_type") == "decision":
                            ctx.decisions.append({
                                "summary": entry_dict.get("summary", ""),
                                "source": "knowledge_registry",
                            })
                        elif entry_dict.get("knowledge_type") == "constraint":
                            ctx.constraints.append({
                                "summary": entry_dict.get("summary", ""),
                                "source": "knowledge_registry",
                            })
                ctx.resolution_chain.append({"step": "knowledge_runtime_enrichment", "knowledge_found": str(len(ctx.knowledge))})
            except Exception as exc:
                logger.debug("Knowledge runtime enrichment failed: %s", exc)

    def _resolve_goals(self, candidates: list[str], ctx: ResolvedContext) -> None:
        """Match candidate names against goal titles in the registry."""
        if self._goal_registry is None:
            return
        try:
            all_goals = self._goal_registry.all_goals()
            for goal in all_goals:
                goal_title = goal.title.lower() if hasattr(goal, "title") else ""
                for candidate in candidates:
                    if candidate.lower() in goal_title or goal_title in candidate.lower():
                        ctx.goals.append({
                            "goal_id": goal.goal_id,
                            "title": goal.title,
                            "type": goal.goal_type.value if hasattr(goal.goal_type, "value") else str(goal.goal_type),
                            "status": goal.status.value if hasattr(goal.status, "value") else str(goal.status),
                        })
                        break
            if ctx.goals:
                ctx.resolution_chain.append({"step": "goal_registry_match", "goals_found": str(len(ctx.goals))})
        except Exception as exc:
            logger.debug("Goal registry resolution failed: %s", exc)

    def _resolve_decisions(self, ctx: ResolvedContext) -> None:
        """Enrich decisions from DecisionRegistry for resolved goals/projects."""
        if self._decision_registry is None:
            return
        try:
            for goal_dict in ctx.goals:
                goal_id = goal_dict.get("goal_id", "")
                if goal_id:
                    related = self._decision_registry.decisions_for_goal(goal_id)
                    for d in related:
                        ctx.decisions.append({
                            "decision_id": d.decision_id,
                            "title": d.title,
                            "status": d.status.value if hasattr(d.status, "value") else str(d.status),
                            "source": "decision_registry",
                        })
            if ctx.decisions:
                ctx.resolution_chain.append({
                    "step": "decision_registry_enrichment",
                    "decisions_found": str(len(ctx.decisions)),
                })
        except Exception as exc:
            logger.debug("Decision registry enrichment failed: %s", exc)

    def _merge_active_context(self, ctx: ResolvedContext) -> None:
        """Merge in active workspace/device awareness."""
        if self._workspace is not None:
            try:
                active = self._workspace.detect_active_workspace()
                if not ctx.active_device and active.get("device"):
                    ctx.active_device = active["device"]
            except Exception as exc:
                logger.debug("Workspace awareness unavailable: %s", exc)

        if self._devices is not None:
            try:
                if not ctx.active_device:
                    ctx.active_device = self._devices.detect_active_device()
            except Exception as exc:
                logger.debug("Device awareness unavailable: %s", exc)

    def _compute_confidence(self, ctx: ResolvedContext) -> None:
        """Score resolution confidence based on what was resolved."""
        score = 0.0
        if ctx.project_id:
            score += 0.25
        if ctx.repository_id:
            score += 0.15
        if ctx.workspace_id:
            score += 0.1
        if ctx.device_id:
            score += 0.1
        if ctx.projection:
            score += 0.05
        if ctx.active_device:
            score += 0.05
        if ctx.files:
            score += 0.1
        if ctx.documents:
            score += 0.1
        if ctx.decisions:
            score += 0.05
        if ctx.active_work:
            score += 0.05
        if ctx.constraints:
            score += 0.05
        if ctx.knowledge:
            score += 0.05
        if ctx.goals:
            score += 0.05

        penalty = len(ctx.unresolved_references) * 0.05
        ctx.confidence = max(0.0, min(1.0, score - penalty))
