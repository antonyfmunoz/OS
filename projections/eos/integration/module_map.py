"""EOS app-body module map — WP-P4-EOS-APP-MODULE-MAP-001.

Read surface over the source-to-substrate module map produced from the VERIFIED
EntrepreneurOS Beast app body. The map document itself lives at
data/umh/projection_reconciliation/eos_app_module_map.json and records, per
Beast module: what it is, which UMH layer it maps to, its copy policy, and
whether mutating it needs owner approval.

Two invariants this accessor enforces (both regression-tested):

1. **Source authority is the Beast.** The map's provenance block pins the Beast
   repo/branch/head from the #179 readiness harness. data/repos/entrepreneuros
   is an inspection mirror only — the map says so explicitly and this module
   never reads app code at all (the map is the read model).

2. **Build-mappability is gated on live build safety.** ``build_mappable_modules()``
   returns rows ONLY while ``eos_readiness()['source_build_safe']`` is True
   (source_current + runtime_ready + backed_up + full mirror + VERIFIED). If the
   Beast drifts, the mappable set collapses to [] — a build orchestrator can
   never pick a slice from a stale map.

Imports are downward only (projection → same-package / substrate), the accessor
is side-effect-free, env-disabled-safe, and never raises.
"""

from __future__ import annotations

import json
import os
from typing import Any

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")
_MAP_PATH = os.path.join(
    _REPO_ROOT, "data", "umh", "projection_reconciliation", "eos_app_module_map.json"
)

_EMPTY_MAP: dict[str, Any] = {
    "map_id": "eos_app_module_map",
    "projection_id": "eos",
    "provenance": {},
    "modules": [],
}


def load_eos_app_module_map(map_path: str = "") -> dict[str, Any]:
    """Return the raw EOS app-module map document, or a safe empty envelope.

    Never raises: a missing or malformed map file yields the empty envelope
    (no provenance, no modules), which downstream consumers treat as
    "nothing is mappable".
    """
    path = map_path or _MAP_PATH
    if not os.path.exists(path):
        return dict(_EMPTY_MAP)
    try:
        with open(path, "r") as f:
            doc = json.load(f)
    except (json.JSONDecodeError, OSError):
        return dict(_EMPTY_MAP)
    if not isinstance(doc, dict) or not isinstance(doc.get("modules"), list):
        return dict(_EMPTY_MAP)
    return doc


def build_mappable_modules(map_path: str = "") -> list[dict[str, Any]]:
    """Return the module rows a build orchestrator may plan a slice from.

    Fail-closed on every input:
    - eos_readiness() must report source_build_safe=True (live Beast truth,
      not the map's snapshot) — otherwise [].
    - The map's recorded provenance head must match the current VERIFIED
      Beast head — a map built from an older commit is not mappable.
    - Rows whose copy_policy is not an explicit no-copy/no-further-copy value
      are dropped (this packet sanctions mapping, not copying).
    - Only projection_id == "eos" maps are honored (CreatorOS/LyfeOS excluded).
    """
    doc = load_eos_app_module_map(map_path)
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

    allowed_copy_policies = {"do_not_copy", "already_mirrored_no_further_copy"}
    rows: list[dict[str, Any]] = []
    for module in doc.get("modules", []):
        if not isinstance(module, dict):
            continue
        if module.get("copy_policy") not in allowed_copy_policies:
            continue
        rows.append(
            {
                **module,
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
