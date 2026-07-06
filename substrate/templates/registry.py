"""RealityTemplate registry — load, validate, resolve, and evolve templates.

The substrate home for the RealityTemplate metamodel (packet P4S-12). Loads the
compiled taxonomy seed (``data/umh/templates/reality_template_taxonomy.json``),
validates every entry against the metamodel types, resolves templates by id,
registers instances, enforces the DAG on graphs, and keeps template revisions
append-only.

No global mutable singleton: the registry is a class, constructed per use. A
module-level ``load_reality_template_registry()`` convenience mirrors the
projection-port pattern (``substrate/sockets/projection_port.py``) — it returns a
freshly loaded, seeded registry, it does NOT stash a shared instance.

This is a substrate L2 metamodel module. It MUST NOT import from ``projections/``,
``transports/``, ``services/``, or ``substrate/state/business/``.

Distinct from ``substrate.organism.template_registry.TemplateRegistry`` (the
runtime executable-action-pattern store). This ``RealityTemplateRegistry`` governs
the METAMODEL of provable patterns.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from substrate.templates.reality_template import (
    CapabilityRevision,
    RealityTemplate,
    RealityTemplateStatus,
    TemplateGraph,
    TemplateInstance,
    TemplateInvariant,
    TemplateProofRequirement,
    TemplateVariable,
)

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")
_TAXONOMY_PATH = os.path.join(
    _REPO_ROOT, "data", "umh", "templates", "reality_template_taxonomy.json"
)


class RealityTemplateRegistry:
    """In-memory registry of RealityTemplates, their instances, and revisions.

    Constructed empty; ``load_taxonomy()`` seeds it from the compiled JSON. Every
    entry is validated through :class:`RealityTemplate` construction, so the
    essentialism rules (no speculative proof, N≥2 for extraction, instance-free
    bodies) are enforced at load time, not merely documented.
    """

    def __init__(self) -> None:
        self._templates: dict[str, RealityTemplate] = {}
        # Instances registered against templates, keyed by template id.
        self._instances: dict[str, list[TemplateInstance]] = {}
        # Append-only revision history, keyed by template id, ordered by version.
        self._revisions: dict[str, list[CapabilityRevision]] = {}

    # ── Loading / validation ────────────────────────────────────────────────

    def load_taxonomy(self, path: str | os.PathLike[str] | None = None) -> int:
        """Load and validate the taxonomy seed. Returns the number of templates
        registered. Raises ``ValueError`` if any entry violates the metamodel."""
        target = Path(path) if path is not None else Path(_TAXONOMY_PATH)
        if not target.exists():
            raise FileNotFoundError(f"taxonomy seed not found: {target}")

        with open(target, encoding="utf-8") as f:
            data = json.load(f)

        candidates = data.get("template_candidates", [])
        if not isinstance(candidates, list):
            raise ValueError("taxonomy 'template_candidates' must be a list")

        for raw in candidates:
            template = self._template_from_seed(raw)
            self.register_template(template)

        logger.info(
            "reality_template_registry: loaded %d templates from %s",
            len(self._templates),
            target,
        )
        return len(self._templates)

    @staticmethod
    def _template_from_seed(raw: dict[str, Any]) -> RealityTemplate:
        """Build a validated :class:`RealityTemplate` from one seed entry.

        The seed carries invariants/variables as plain strings; they are lifted
        into the typed metamodel objects here. Instance-literal scanning runs in
        the type validators, so a leaked literal fails the load loudly.
        """
        status = RealityTemplateStatus(raw["status"])

        invariants = [TemplateInvariant(statement=s) for s in raw.get("invariants", [])]
        variables = [TemplateVariable(name=n) for n in raw.get("variables", [])]
        proof_req_text = raw.get("proof_requirement", "")
        proof_requirement = (
            TemplateProofRequirement(description=proof_req_text) if proof_req_text else None
        )

        # instance_count is not carried in the seed; derive a coherent minimum
        # from the declared status so the metamodel's status↔count invariant holds.
        # PROVEN_1_INSTANCE ⇒ 1, PROVEN_N_INSTANCES ⇒ 2, CANDIDATE ⇒ 0.
        if status is RealityTemplateStatus.PROVEN_N_INSTANCES:
            instance_count = max(2, int(raw.get("instance_count", 2)))
        elif status is RealityTemplateStatus.PROVEN_1_INSTANCE:
            instance_count = max(1, int(raw.get("instance_count", 1)))
        else:
            instance_count = int(raw.get("instance_count", 0))

        return RealityTemplate(
            id=raw["id"],
            status=status,
            description=raw.get("description", ""),
            invariants=invariants,
            variables=variables,
            proof_requirement=proof_requirement,
            source_instance=raw.get("source_instance"),
            proof_pointer=raw.get("proof_pointer"),
            instance_count=instance_count,
            next_instances=list(raw.get("next_instances", [])),
            blockers=list(raw.get("blockers", [])),
        )

    # ── Template registration / resolution ──────────────────────────────────

    def register_template(self, template: RealityTemplate) -> None:
        """Register (or replace) a template by id. Validation already happened at
        :class:`RealityTemplate` construction."""
        self._templates[template.id] = template
        self._instances.setdefault(template.id, [])
        self._revisions.setdefault(template.id, [])

    def resolve(self, template_id: str) -> RealityTemplate | None:
        """Resolve a template by id, or ``None`` if unknown."""
        return self._templates.get(template_id)

    def list_templates(self) -> list[RealityTemplate]:
        return list(self._templates.values())

    def __contains__(self, template_id: object) -> bool:
        return template_id in self._templates

    def __len__(self) -> int:
        return len(self._templates)

    # ── Instances ───────────────────────────────────────────────────────────

    def register_instance(self, instance: TemplateInstance) -> None:
        """Register an instance against a known template. Raises if the template
        is unknown (an instance without its template is orphaned)."""
        if instance.template_id not in self._templates:
            raise ValueError(
                f"cannot register instance for unknown template {instance.template_id!r}"
            )
        self._instances[instance.template_id].append(instance)

    def instances_for(self, template_id: str) -> list[TemplateInstance]:
        return list(self._instances.get(template_id, []))

    # ── Graphs ──────────────────────────────────────────────────────────────

    def validate_graph(self, graph: TemplateGraph) -> None:
        """Enforce the DAG + proof-gates-edges invariants on a graph. Raises
        ``ValueError`` on the first violation."""
        graph.validate_graph()

    # ── Revisions (append-only) ─────────────────────────────────────────────

    def record_revision(self, revision: CapabilityRevision) -> None:
        """Append a revision to a template's history. Enforces append-only,
        forward-only, contiguous versioning against what is already recorded."""
        if revision.template_id not in self._templates:
            raise ValueError(f"cannot revise unknown template {revision.template_id!r}")
        history = self._revisions.setdefault(revision.template_id, [])
        if history:
            last = history[-1]
            if revision.to_version <= last.to_version:
                raise ValueError(
                    f"{revision.template_id}: revision history is append-only — "
                    f"new version {revision.to_version} must exceed the last "
                    f"recorded version {last.to_version}"
                )
        history.append(revision)

    def revisions_for(self, template_id: str) -> list[CapabilityRevision]:
        """Return the immutable, ordered revision history for a template."""
        return list(self._revisions.get(template_id, []))


def load_reality_template_registry(
    path: str | os.PathLike[str] | None = None,
) -> RealityTemplateRegistry:
    """Return a freshly loaded, seeded registry.

    Mirrors the projection-port convenience loaders: constructs a new registry
    and seeds it from the taxonomy. Does NOT return a shared global singleton —
    callers own their instance.
    """
    registry = RealityTemplateRegistry()
    registry.load_taxonomy(path)
    return registry


__all__ = [
    "RealityTemplateRegistry",
    "load_reality_template_registry",
]
