"""substrate.templates — the RealityTemplate metamodel home (packet P4S-12).

The L2 ontology of provable patterns: RealityTemplate → TemplateInstance →
TemplateGraph/TemplateEdge → CapabilityRevision. See
``docs/REALITY_TEMPLATE_GRAPH.md`` and the seed
``data/umh/templates/reality_template_taxonomy.json``.

Instance-agnostic substrate subsystem. Never imports projections/transports/
services/ or substrate.state.business.
"""

from __future__ import annotations

from substrate.templates.reality_template import (
    CapabilityRevision,
    RealityTemplate,
    RealityTemplateStatus,
    TemplateEdge,
    TemplateGraph,
    TemplateInstance,
    TemplateInvariant,
    TemplateProofRequirement,
    TemplateVariable,
    configure_instance_denylist,
)
from substrate.templates.registry import (
    RealityTemplateRegistry,
    load_reality_template_registry,
)

__all__ = [
    "RealityTemplateStatus",
    "TemplateInvariant",
    "TemplateVariable",
    "TemplateProofRequirement",
    "RealityTemplate",
    "TemplateInstance",
    "TemplateEdge",
    "TemplateGraph",
    "CapabilityRevision",
    "configure_instance_denylist",
    "RealityTemplateRegistry",
    "load_reality_template_registry",
]
