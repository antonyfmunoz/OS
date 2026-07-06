"""EOS action-executor seam map — WP-P4-EOS-ACTION-EXECUTOR-SEAM-001.

Read surface over the source-to-substrate SEAM map for the EntrepreneurOS
action-execution model (propose → approve → execute → record → retry → learn).
The map document lives at
data/umh/projection_reconciliation/eos_action_executor_seam_map.json and pins,
per seam: the Beast source module, its semantic responsibility, the closest
UMH runtime primitive, and the substrate target owner.

Follows the exact invariants of module_map.py (WP #181):

1. **Source authority is the Beast** — provenance pins repo/branch/head from
   the #179 harness; data/repos is an inspection mirror only. This module
   never reads app code; the map is the read model.

2. **Seam availability is gated on live build safety** — ``mappable_seams()``
   returns rows ONLY while ``eos_readiness()['source_build_safe']`` is True
   and the map's recorded head matches the live VERIFIED Beast head. A seam
   map recorded against a drifted Beast is never actionable.

3. **Semantics only, no code** — the map carries prose responsibilities and
   substrate targets, never copied Beast source (regression-tested).

Imports are downward only, side-effect-free, env-disabled-safe, never raises.
"""

from __future__ import annotations

import json
import os
from typing import Any

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")
_SEAM_MAP_PATH = os.path.join(
    _REPO_ROOT, "data", "umh", "projection_reconciliation", "eos_action_executor_seam_map.json"
)

# The closed set of UMH runtime primitives a seam may map to. A seam naming
# anything else is malformed — the whole point is landing on primitives the
# substrate already owns.
UMH_SEAM_PRIMITIVES = frozenset(
    {
        "WorkPacket",
        "Operation",
        "Approval",
        "Proof",
        "Trace",
        "RuntimeNode",
        "AdapterCall",
        "CapabilityPathway",
    }
)

_EMPTY_MAP: dict[str, Any] = {
    "map_id": "eos_action_executor_seam_map",
    "projection_id": "eos",
    "provenance": {},
    "seams": [],
}


def load_eos_action_seam_map(map_path: str = "") -> dict[str, Any]:
    """Return the raw action-executor seam map, or a safe empty envelope.

    Never raises: missing/malformed file yields the empty envelope, which
    downstream consumers treat as "no seams are actionable".
    """
    path = map_path or _SEAM_MAP_PATH
    if not os.path.exists(path):
        return dict(_EMPTY_MAP)
    try:
        with open(path, "r") as f:
            doc = json.load(f)
    except (json.JSONDecodeError, OSError):
        return dict(_EMPTY_MAP)
    if not isinstance(doc, dict) or not isinstance(doc.get("seams"), list):
        return dict(_EMPTY_MAP)
    return doc


def mappable_seams(map_path: str = "") -> list[dict[str, Any]]:
    """Return the seam rows an implementation packet may plan from.

    Fail-closed on every input, mirroring module_map.build_mappable_modules():
    - eos_readiness() must report source_build_safe=True (live Beast truth).
    - The map's recorded provenance head must match the live VERIFIED head.
    - Rows must map to a primitive in UMH_SEAM_PRIMITIVES and carry a
      non-empty substrate target owner; malformed rows are dropped.
    - Only projection_id == "eos" maps are honored.
    """
    doc = load_eos_action_seam_map(map_path)
    if doc.get("projection_id") != "eos":
        return []

    try:
        from projections.eos.integration.readiness import eos_readiness

        readiness = eos_readiness()
    except Exception:
        return []

    if readiness.get("source_build_safe") is not True:
        return []

    provenance = doc.get("provenance", {})
    if not provenance.get("head") or provenance.get("head") != readiness.get("beast_head"):
        return []
    if provenance.get("beast_verification") != "VERIFIED":
        return []

    rows: list[dict[str, Any]] = []
    for seam in doc.get("seams", []):
        if not isinstance(seam, dict):
            continue
        if seam.get("umh_primitive") not in UMH_SEAM_PRIMITIVES:
            continue
        if not str(seam.get("target_owner", "")).strip():
            continue
        rows.append(
            {
                **seam,
                "provenance": {
                    "beast_repo": provenance.get("beast_repo"),
                    "operating_branch": provenance.get("operating_branch"),
                    "head": provenance.get("head"),
                    "beast_probe_at": provenance.get("beast_probe_at"),
                    "beast_verification": provenance.get("beast_verification"),
                },
                "source_build_safe": True,
            }
        )
    return rows
