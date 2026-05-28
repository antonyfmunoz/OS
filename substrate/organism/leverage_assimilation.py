"""External Leverage Assimilation — ingest, classify, and operationalize
external repos, frameworks, and operational patterns.

The assimilation pipeline:
  1. ingest()       — fetch a repo/URL/document into local staging
  2. classify()     — identify what kind of artifact it is (framework,
                      pattern library, config, agent system, etc.)
  3. extract()      — pull reusable primitives (patterns, configs,
                      abstractions, techniques)
  4. detect_redundancy() — compare against existing UMH capabilities
  5. map_leverage() — score each extracted primitive by leverage potential
  6. operationalize() — create UMH-native implementations or adapters

Classification taxonomy:
  AGENT_SYSTEM       — multi-agent orchestration (cortextOS, crew.ai)
  PATTERN_LIBRARY    — operational patterns (Claude.md best practices)
  FRAMEWORK          — full framework (LangChain, AutoGen)
  CONFIG_SYSTEM      — configuration/prompt management
  RUNTIME_SYSTEM     — execution runtime (Codex, OpenCode)
  KNOWLEDGE_BASE     — documentation, wikis, knowledge graphs
  TOOL_INTEGRATION   — MCP servers, API adapters

Leverage scoring (deterministic):
  uniqueness      — does UMH already have this? (0-1)
  applicability   — how broadly useful across UMH? (0-1)
  implementation  — how much work to integrate? (0-1, inverted)
  risk            — integration risk to existing system (0-1, inverted)
  score = 0.35 * uniqueness + 0.30 * applicability
        + 0.20 * (1 - implementation) + 0.15 * (1 - risk)

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class ArtifactType(str, Enum):
    AGENT_SYSTEM = "agent_system"
    PATTERN_LIBRARY = "pattern_library"
    FRAMEWORK = "framework"
    CONFIG_SYSTEM = "config_system"
    RUNTIME_SYSTEM = "runtime_system"
    KNOWLEDGE_BASE = "knowledge_base"
    TOOL_INTEGRATION = "tool_integration"
    UNKNOWN = "unknown"


class PrimitiveType(str, Enum):
    PATTERN = "pattern"
    CONFIG = "config"
    ABSTRACTION = "abstraction"
    TECHNIQUE = "technique"
    PROTOCOL = "protocol"
    ADAPTER = "adapter"
    WORKFLOW = "workflow"


class AssimilationStatus(str, Enum):
    STAGED = "staged"
    CLASSIFIED = "classified"
    EXTRACTED = "extracted"
    SCORED = "scored"
    OPERATIONALIZED = "operationalized"
    REJECTED = "rejected"


_TYPE_SIGNALS: dict[str, ArtifactType] = {
    "agent": ArtifactType.AGENT_SYSTEM,
    "crew": ArtifactType.AGENT_SYSTEM,
    "swarm": ArtifactType.AGENT_SYSTEM,
    "orchestrat": ArtifactType.AGENT_SYSTEM,
    "multi-agent": ArtifactType.AGENT_SYSTEM,
    "pattern": ArtifactType.PATTERN_LIBRARY,
    "best.practice": ArtifactType.PATTERN_LIBRARY,
    "claude.md": ArtifactType.PATTERN_LIBRARY,
    "framework": ArtifactType.FRAMEWORK,
    "langchain": ArtifactType.FRAMEWORK,
    "autogen": ArtifactType.FRAMEWORK,
    "config": ArtifactType.CONFIG_SYSTEM,
    "prompt": ArtifactType.CONFIG_SYSTEM,
    "runtime": ArtifactType.RUNTIME_SYSTEM,
    "codex": ArtifactType.RUNTIME_SYSTEM,
    "opencode": ArtifactType.RUNTIME_SYSTEM,
    "hermes": ArtifactType.RUNTIME_SYSTEM,
    "knowledge": ArtifactType.KNOWLEDGE_BASE,
    "wiki": ArtifactType.KNOWLEDGE_BASE,
    "doc": ArtifactType.KNOWLEDGE_BASE,
    "mcp": ArtifactType.TOOL_INTEGRATION,
    "tool": ArtifactType.TOOL_INTEGRATION,
    "adapter": ArtifactType.TOOL_INTEGRATION,
}


@dataclass
class LeverageScore:
    uniqueness: float = 0.0
    applicability: float = 0.0
    implementation_cost: float = 0.0
    risk: float = 0.0

    @property
    def composite(self) -> float:
        return (
            0.35 * self.uniqueness
            + 0.30 * self.applicability
            + 0.20 * (1.0 - self.implementation_cost)
            + 0.15 * (1.0 - self.risk)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "uniqueness": round(self.uniqueness, 3),
            "applicability": round(self.applicability, 3),
            "implementation_cost": round(self.implementation_cost, 3),
            "risk": round(self.risk, 3),
            "composite": round(self.composite, 3),
        }


@dataclass
class ExtractedPrimitive:
    id: str = ""
    name: str = ""
    primitive_type: PrimitiveType = PrimitiveType.PATTERN
    description: str = ""
    source_artifact: str = ""
    source_location: str = ""
    leverage: LeverageScore = field(default_factory=LeverageScore)
    umh_mapping: str = ""
    operationalized: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id:
            self.id = f"prim-{uuid4().hex[:8]}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "primitive_type": self.primitive_type.value,
            "description": self.description[:300],
            "source_artifact": self.source_artifact,
            "source_location": self.source_location,
            "leverage": self.leverage.to_dict(),
            "umh_mapping": self.umh_mapping,
            "operationalized": self.operationalized,
        }


@dataclass
class AssimilationArtifact:
    id: str = ""
    name: str = ""
    source_url: str = ""
    artifact_type: ArtifactType = ArtifactType.UNKNOWN
    status: AssimilationStatus = AssimilationStatus.STAGED
    primitives: list[ExtractedPrimitive] = field(default_factory=list)
    redundancy_report: dict[str, Any] = field(default_factory=dict)
    created_at: float = 0.0
    classified_at: float = 0.0
    extracted_at: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id:
            self.id = f"art-{uuid4().hex[:8]}"
        if not self.created_at:
            self.created_at = time.time()

    @property
    def leverage_summary(self) -> dict[str, float]:
        if not self.primitives:
            return {"count": 0, "avg_score": 0.0, "max_score": 0.0}
        scores = [p.leverage.composite for p in self.primitives]
        return {
            "count": len(scores),
            "avg_score": round(sum(scores) / len(scores), 3),
            "max_score": round(max(scores), 3),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "source_url": self.source_url,
            "artifact_type": self.artifact_type.value,
            "status": self.status.value,
            "primitives_count": len(self.primitives),
            "leverage_summary": self.leverage_summary,
            "redundancy_report": self.redundancy_report,
            "created_at": self.created_at,
        }


_UMH_CAPABILITIES: set[str] = {
    "runtime_graph",
    "runtime_supervisor",
    "organism_coordinator",
    "workcell_protocol",
    "homeostasis",
    "capability_routing",
    "dag_decomposition",
    "crash_recovery",
    "exponential_backoff",
    "heartbeat_monitoring",
    "parallel_execution",
    "agent_handoff",
    "delegation_tracking",
    "self_critique",
    "governance_gate",
    "risk_classification",
    "deterministic_routing",
    "fallback_chains",
    "persistent_state",
    "event_emission",
    "observability_snapshot",
    "type_coherence_gate",
    "instance_context_gate",
    "model_router",
    "execution_spine",
    "ingestion_pipeline",
    "memory_palace",
    "codebase_graph",
}


class LeverageAssimilator:
    """Ingests external repos/frameworks, extracts reusable primitives,
    scores them by leverage potential, and maps them to UMH integration points.

    Deterministic-first: classification and scoring use keyword matching
    and heuristic rules. LLM-enhanced extraction is optional and has
    a deterministic fallback.
    """

    def __init__(
        self,
        state_dir: str | Path = "data/umh/assimilation",
        umh_capabilities: set[str] | None = None,
    ) -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._artifacts: dict[str, AssimilationArtifact] = {}
        self._umh_capabilities = umh_capabilities or _UMH_CAPABILITIES

    def ingest(
        self,
        name: str,
        source_url: str = "",
        content: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> AssimilationArtifact:
        """Stage an external artifact for assimilation."""
        artifact = AssimilationArtifact(
            name=name,
            source_url=source_url,
            metadata={**(metadata or {}), "content_length": len(content)},
        )

        if content:
            content_path = self._state_dir / "staging" / f"{artifact.id}.txt"
            content_path.parent.mkdir(parents=True, exist_ok=True)
            content_path.write_text(content[:500_000])

        self._artifacts[artifact.id] = artifact
        self._persist_artifact(artifact)

        logger.info("artifact ingested: %s (%s)", name, artifact.id)
        return artifact

    def classify(self, artifact_id: str) -> ArtifactType:
        """Classify an artifact by type using deterministic signals."""
        artifact = self._artifacts.get(artifact_id)
        if artifact is None:
            return ArtifactType.UNKNOWN

        text = f"{artifact.name} {artifact.source_url} {json.dumps(artifact.metadata)}".lower()

        type_scores: dict[ArtifactType, int] = {}
        for signal, atype in _TYPE_SIGNALS.items():
            if signal in text:
                type_scores[atype] = type_scores.get(atype, 0) + 1

        if type_scores:
            best_type = max(type_scores, key=lambda k: type_scores[k])
        else:
            best_type = ArtifactType.UNKNOWN

        artifact.artifact_type = best_type
        artifact.status = AssimilationStatus.CLASSIFIED
        artifact.classified_at = time.time()
        self._persist_artifact(artifact)

        logger.info("artifact classified: %s → %s", artifact_id, best_type.value)
        return best_type

    def extract_primitives(
        self,
        artifact_id: str,
        primitives: list[dict[str, Any]] | None = None,
    ) -> list[ExtractedPrimitive]:
        """Extract reusable primitives from an artifact.

        If primitives are provided directly (e.g., from LLM extraction),
        use them. Otherwise, use deterministic heuristics based on
        artifact type.
        """
        artifact = self._artifacts.get(artifact_id)
        if artifact is None:
            return []

        extracted: list[ExtractedPrimitive] = []

        if primitives:
            for p in primitives:
                prim = ExtractedPrimitive(
                    name=p.get("name", ""),
                    primitive_type=PrimitiveType(p.get("type", "pattern")),
                    description=p.get("description", ""),
                    source_artifact=artifact_id,
                    source_location=p.get("source_location", ""),
                    metadata=p.get("metadata", {}),
                )
                extracted.append(prim)
        else:
            extracted = self._heuristic_extraction(artifact)

        artifact.primitives = extracted
        artifact.status = AssimilationStatus.EXTRACTED
        artifact.extracted_at = time.time()
        self._persist_artifact(artifact)

        logger.info(
            "extracted %d primitives from %s",
            len(extracted),
            artifact_id,
        )
        return extracted

    def _heuristic_extraction(self, artifact: AssimilationArtifact) -> list[ExtractedPrimitive]:
        """Deterministic primitive extraction based on artifact type."""
        type_primitives: dict[ArtifactType, list[dict[str, Any]]] = {
            ArtifactType.AGENT_SYSTEM: [
                {"name": "agent_lifecycle", "type": "protocol", "desc": "Agent start/stop/health lifecycle management"},
                {"name": "task_routing", "type": "pattern", "desc": "Task-to-agent routing logic"},
                {"name": "inter_agent_comm", "type": "protocol", "desc": "Agent-to-agent communication protocol"},
            ],
            ArtifactType.PATTERN_LIBRARY: [
                {"name": "operational_pattern", "type": "pattern", "desc": "Reusable operational pattern"},
                {"name": "config_convention", "type": "config", "desc": "Configuration convention or template"},
            ],
            ArtifactType.FRAMEWORK: [
                {"name": "abstraction_layer", "type": "abstraction", "desc": "Framework abstraction layer"},
                {"name": "plugin_interface", "type": "adapter", "desc": "Plugin/extension interface pattern"},
            ],
            ArtifactType.RUNTIME_SYSTEM: [
                {"name": "execution_model", "type": "protocol", "desc": "Execution model and lifecycle"},
                {"name": "resource_management", "type": "pattern", "desc": "Resource allocation and management"},
            ],
            ArtifactType.TOOL_INTEGRATION: [
                {"name": "adapter_pattern", "type": "adapter", "desc": "Tool adapter implementation pattern"},
            ],
        }

        templates = type_primitives.get(artifact.artifact_type, [
            {"name": "generic_pattern", "type": "pattern", "desc": "Unclassified pattern"},
        ])

        return [
            ExtractedPrimitive(
                name=f"{artifact.name}_{t['name']}",
                primitive_type=PrimitiveType(t["type"]),
                description=t["desc"],
                source_artifact=artifact.id,
            )
            for t in templates
        ]

    def detect_redundancy(self, artifact_id: str) -> dict[str, Any]:
        """Compare extracted primitives against existing UMH capabilities."""
        artifact = self._artifacts.get(artifact_id)
        if artifact is None:
            return {"error": "artifact not found"}

        report: dict[str, Any] = {
            "artifact_id": artifact_id,
            "total_primitives": len(artifact.primitives),
            "redundant": [],
            "novel": [],
            "partial_overlap": [],
        }

        for prim in artifact.primitives:
            prim_tokens = set(prim.name.lower().replace("_", " ").split())
            prim_tokens.update(prim.description.lower().replace("_", " ").split())

            overlap_scores: list[tuple[str, float]] = []
            for cap in self._umh_capabilities:
                cap_tokens = set(cap.lower().replace("_", " ").split())
                intersection = prim_tokens & cap_tokens
                if not intersection:
                    continue
                union = prim_tokens | cap_tokens
                jaccard = len(intersection) / len(union) if union else 0
                overlap_scores.append((cap, jaccard))

            if not overlap_scores:
                report["novel"].append(prim.id)
                prim.leverage.uniqueness = 1.0
            else:
                best_match, best_score = max(overlap_scores, key=lambda x: x[1])
                if best_score > 0.5:
                    report["redundant"].append({
                        "primitive": prim.id,
                        "overlaps_with": best_match,
                        "similarity": round(best_score, 3),
                    })
                    prim.leverage.uniqueness = max(0.0, 1.0 - best_score)
                else:
                    report["partial_overlap"].append({
                        "primitive": prim.id,
                        "closest": best_match,
                        "similarity": round(best_score, 3),
                    })
                    prim.leverage.uniqueness = 1.0 - best_score

        artifact.redundancy_report = report
        self._persist_artifact(artifact)
        return report

    def score_leverage(self, artifact_id: str) -> list[dict[str, Any]]:
        """Score all primitives in an artifact by leverage potential."""
        artifact = self._artifacts.get(artifact_id)
        if artifact is None:
            return []

        for prim in artifact.primitives:
            prim.leverage.applicability = self._score_applicability(prim)
            prim.leverage.implementation_cost = self._score_implementation_cost(prim)
            prim.leverage.risk = self._score_risk(prim)

        artifact.status = AssimilationStatus.SCORED
        self._persist_artifact(artifact)

        ranked = sorted(artifact.primitives, key=lambda p: p.leverage.composite, reverse=True)
        return [p.to_dict() for p in ranked]

    def _score_applicability(self, prim: ExtractedPrimitive) -> float:
        """How broadly useful is this primitive across UMH?"""
        broad_types = {PrimitiveType.PROTOCOL, PrimitiveType.ABSTRACTION, PrimitiveType.PATTERN}
        if prim.primitive_type in broad_types:
            return 0.8
        if prim.primitive_type == PrimitiveType.WORKFLOW:
            return 0.6
        return 0.4

    def _score_implementation_cost(self, prim: ExtractedPrimitive) -> float:
        """How much work to integrate? Higher = more expensive."""
        high_cost_types = {PrimitiveType.ABSTRACTION, PrimitiveType.PROTOCOL}
        if prim.primitive_type in high_cost_types:
            return 0.7
        if prim.primitive_type == PrimitiveType.ADAPTER:
            return 0.5
        return 0.3

    def _score_risk(self, prim: ExtractedPrimitive) -> float:
        """Integration risk to existing system. Higher = riskier."""
        if prim.primitive_type == PrimitiveType.PROTOCOL:
            return 0.6
        if prim.primitive_type == PrimitiveType.ABSTRACTION:
            return 0.5
        return 0.2

    def map_to_umh(self, artifact_id: str) -> dict[str, str]:
        """Map each primitive to its best UMH integration point."""
        artifact = self._artifacts.get(artifact_id)
        if artifact is None:
            return {}

        mapping: dict[str, str] = {}
        integration_points: dict[PrimitiveType, str] = {
            PrimitiveType.PATTERN: "substrate/organism/",
            PrimitiveType.CONFIG: "data/config/",
            PrimitiveType.ABSTRACTION: "substrate/",
            PrimitiveType.TECHNIQUE: "substrate/organism/",
            PrimitiveType.PROTOCOL: "substrate/organism/protocols.py",
            PrimitiveType.ADAPTER: "substrate/organism/runtime_adapters.py",
            PrimitiveType.WORKFLOW: "substrate/execution/loop/",
        }

        for prim in artifact.primitives:
            target = integration_points.get(prim.primitive_type, "substrate/organism/")
            prim.umh_mapping = target
            mapping[prim.id] = target

        self._persist_artifact(artifact)
        return mapping

    def full_pipeline(
        self,
        name: str,
        source_url: str = "",
        content: str = "",
        primitives: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Run the full assimilation pipeline: ingest → classify → extract
        → detect_redundancy → score → map."""
        artifact = self.ingest(name, source_url=source_url, content=content)
        self.classify(artifact.id)
        self.extract_primitives(artifact.id, primitives=primitives)
        redundancy = self.detect_redundancy(artifact.id)
        scored = self.score_leverage(artifact.id)
        umh_map = self.map_to_umh(artifact.id)

        return {
            "artifact": artifact.to_dict(),
            "redundancy": redundancy,
            "scored_primitives": scored,
            "umh_mapping": umh_map,
        }

    def get_artifact(self, artifact_id: str) -> AssimilationArtifact | None:
        return self._artifacts.get(artifact_id)

    def list_artifacts(self) -> list[dict[str, Any]]:
        return [a.to_dict() for a in self._artifacts.values()]

    def _persist_artifact(self, artifact: AssimilationArtifact) -> None:
        path = self._state_dir / "artifacts" / f"{artifact.id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(artifact.to_dict(), indent=2, default=str))

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_artifacts": len(self._artifacts),
            "by_status": self._count_by_status(),
            "total_primitives": sum(len(a.primitives) for a in self._artifacts.values()),
            "umh_capabilities_tracked": len(self._umh_capabilities),
        }

    def _count_by_status(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for a in self._artifacts.values():
            s = a.status.value
            counts[s] = counts.get(s, 0) + 1
        return counts
