"""Operationalization Runtime — link capabilities to reusable artifacts.

Answers operator question #11: "What has been operationalized?"

An Operationalization bridges an EmergentCapability to a concrete reusable
form: template, workflow, playbook, or automation. This is the "Learn Once"
layer — what the organization has learned that it never needs to learn again.

Composes with (never duplicates):
  - CapabilityRuntime — links operationalizations to capabilities
  - TemplateRegistry — links to existing template infrastructure
  - TemplateGovernance — reads lifecycle/eligibility data

Gate 6 — Operationalization Runtime. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from collections import Counter
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")
_OP_DIR = os.path.join(_REPO_ROOT, "data", "umh", "operationalizations")
_OP_PATH = os.path.join(_OP_DIR, "operationalizations.jsonl")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Types
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class OperationalizationForm(str, Enum):
    TEMPLATE = "template"
    WORKFLOW = "workflow"
    PLAYBOOK = "playbook"
    AUTOMATION = "automation"


class OperationalizationStatus(str, Enum):
    DRAFT = "draft"
    VALIDATED = "validated"
    PRODUCTION = "production"
    DEPRECATED = "deprecated"


_STATUS_ORDER: dict[OperationalizationStatus, int] = {
    OperationalizationStatus.DRAFT: 0,
    OperationalizationStatus.VALIDATED: 1,
    OperationalizationStatus.PRODUCTION: 2,
    OperationalizationStatus.DEPRECATED: 3,
}


@dataclass
class Operationalization:
    operationalization_id: str = field(default_factory=lambda: f"op-{uuid4().hex[:8]}")
    capability_id: str = ""
    form: OperationalizationForm = OperationalizationForm.TEMPLATE
    name: str = ""
    description: str = ""
    template_id: str = ""
    invariants: list[str] = field(default_factory=list)
    variables: list[str] = field(default_factory=list)
    status: OperationalizationStatus = OperationalizationStatus.DRAFT
    reuse_count: int = 0
    success_rate: float = 0.0
    evidence: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["form"] = self.form.value
        d["status"] = self.status.value
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Operationalization:
        d = dict(d)
        try:
            d["form"] = OperationalizationForm(d.get("form", "template"))
        except ValueError:
            d["form"] = OperationalizationForm.TEMPLATE
        try:
            d["status"] = OperationalizationStatus(d.get("status", "draft"))
        except ValueError:
            d["status"] = OperationalizationStatus.DRAFT
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Invariant extraction — deterministic, no LLM
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def extract_invariants_from_steps(steps: list[dict[str, Any]]) -> dict[str, Any]:
    """Deterministic invariant extraction from template steps.

    Identifies repeating patterns:
    - Actions that appear in every step (structural invariants)
    - Risk classes that never change (governance invariants)
    - Capabilities that are always required (capability invariants)
    """
    if not steps:
        return {"invariants": [], "variables": [], "step_count": 0}

    actions = Counter(s.get("action", "") for s in steps if s.get("action"))
    risk_classes = Counter(s.get("risk_class", "") for s in steps if s.get("risk_class"))
    capabilities = Counter(
        s.get("requires_capability", "") for s in steps if s.get("requires_capability")
    )

    invariants: list[str] = []
    variables: list[str] = []

    if len(risk_classes) == 1:
        invariants.append(f"risk_class={list(risk_classes.keys())[0]}")
    elif len(risk_classes) > 1:
        variables.append("risk_class")

    if len(set(s.get("governance_mode", "") for s in steps)) == 1:
        mode = steps[0].get("governance_mode", "")
        if mode:
            invariants.append(f"governance_mode={mode}")
    else:
        variables.append("governance_mode")

    for cap, count in capabilities.most_common():
        if cap and count == len(steps):
            invariants.append(f"requires_capability={cap}")
        elif cap:
            variables.append(f"capability={cap}")

    for action, count in actions.most_common():
        if action and count > 1:
            variables.append(f"action={action}")

    return {
        "invariants": invariants,
        "variables": variables,
        "step_count": len(steps),
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Reuse scoring — deterministic
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def compute_reuse_score(op: Operationalization) -> dict[str, Any]:
    """Deterministic reuse value score.

    frequency_score = min(1.0, reuse_count / 10)
    reliability_score = success_rate
    form_weight: automation > workflow > playbook > template
    composite = frequency * 0.4 + reliability * 0.4 + form * 0.2
    """
    form_weights: dict[OperationalizationForm, float] = {
        OperationalizationForm.AUTOMATION: 1.0,
        OperationalizationForm.WORKFLOW: 0.75,
        OperationalizationForm.PLAYBOOK: 0.5,
        OperationalizationForm.TEMPLATE: 0.25,
    }
    freq = min(1.0, op.reuse_count / 10.0)
    reliability = op.success_rate
    form_w = form_weights.get(op.form, 0.25)
    composite = freq * 0.4 + reliability * 0.4 + form_w * 0.2
    return {
        "operationalization_id": op.operationalization_id,
        "frequency_score": round(freq, 3),
        "reliability_score": round(reliability, 3),
        "form_weight": round(form_w, 3),
        "composite_score": round(composite, 4),
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Runtime
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class OperationalizationRuntime:
    """Registry and lifecycle for operationalizations."""

    def __init__(self, store_path: str = _OP_PATH) -> None:
        self._path = store_path
        self._lock = threading.Lock()
        self._ops: dict[str, Operationalization] = {}
        self._load()

    # ── Persistence ────────────────────────────────────────────────

    def _load(self) -> None:
        if not os.path.exists(self._path):
            return
        try:
            with open(self._path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        d = json.loads(line)
                        op = Operationalization.from_dict(d)
                        self._ops[op.operationalization_id] = op
                    except (json.JSONDecodeError, TypeError, KeyError) as e:
                        logger.debug("Skip malformed JSONL line: %s", e)
        except OSError as e:
            logger.debug("Cannot read %s: %s", self._path, e)

    def _append(self, op: Operationalization) -> None:
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with open(self._path, "a") as f:
            f.write(json.dumps(op.to_dict(), default=str) + "\n")

    def _rewrite(self) -> None:
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with open(self._path, "w") as f:
            for op in self._ops.values():
                f.write(json.dumps(op.to_dict(), default=str) + "\n")

    # ── Registry ───────────────────────────────────────────────────

    def create(
        self,
        capability_id: str,
        form: OperationalizationForm,
        name: str,
        description: str = "",
        template_id: str = "",
        invariants: list[str] | None = None,
        variables: list[str] | None = None,
    ) -> Operationalization:
        op = Operationalization(
            capability_id=capability_id,
            form=form,
            name=name,
            description=description,
            template_id=template_id,
            invariants=invariants or [],
            variables=variables or [],
        )
        with self._lock:
            self._ops[op.operationalization_id] = op
            self._append(op)

        from substrate.organism.capability_runtime import CapabilityRuntime

        try:
            cr = CapabilityRuntime()
            cr.link_operationalization(capability_id, op.operationalization_id)
        except Exception as e:
            logger.debug("Could not link to CapabilityRuntime: %s", e)

        logger.info("Created operationalization: %s (%s)", op.name, op.operationalization_id)
        return op

    def get(self, operationalization_id: str) -> Operationalization | None:
        return self._ops.get(operationalization_id)

    def list_operationalizations(
        self,
        capability_id: str | None = None,
        form: OperationalizationForm | None = None,
        status: OperationalizationStatus | None = None,
    ) -> list[Operationalization]:
        result = list(self._ops.values())
        if capability_id is not None:
            result = [o for o in result if o.capability_id == capability_id]
        if form is not None:
            result = [o for o in result if o.form == form]
        if status is not None:
            result = [o for o in result if o.status == status]
        result.sort(key=lambda o: o.created_at, reverse=True)
        return result

    # ── Template linkage ───────────────────────────────────────────

    def from_template(self, template_id: str) -> Operationalization | None:
        for op in self._ops.values():
            if op.template_id == template_id:
                return op
        return None

    def link_template(self, operationalization_id: str, template_id: str) -> bool:
        op = self._ops.get(operationalization_id)
        if op is None:
            return False
        with self._lock:
            op.template_id = template_id
            op.updated_at = time.time()
            self._rewrite()
        return True

    # ── Invariant extraction ───────────────────────────────────────

    def extract_invariants(self, template_id: str) -> dict[str, Any]:
        """Extract invariants from a template in the TemplateRegistry."""
        try:
            from substrate.organism.template_registry import TemplateRegistry

            tr = TemplateRegistry()
            tpl = tr.get_template(template_id)
            if tpl is None:
                return {"error": f"template {template_id} not found"}
            steps = [s.to_dict() for s in (tpl.steps or [])]
            return extract_invariants_from_steps(steps)
        except ImportError:
            return {"error": "TemplateRegistry not available"}
        except Exception as e:
            logger.debug("extract_invariants error: %s", e)
            return {"error": str(e)}

    # ── Reuse scoring ──────────────────────────────────────────────

    def reuse_score(self, operationalization_id: str) -> dict[str, Any]:
        op = self._ops.get(operationalization_id)
        if op is None:
            return {"error": f"operationalization {operationalization_id} not found"}
        return compute_reuse_score(op)

    def most_reused(self, n: int = 10) -> list[Operationalization]:
        ranked = sorted(
            self._ops.values(),
            key=lambda o: (o.reuse_count, o.success_rate),
            reverse=True,
        )
        return ranked[:n]

    # ── Status lifecycle ───────────────────────────────────────────

    def update_status(
        self, operationalization_id: str, new_status: OperationalizationStatus
    ) -> bool:
        op = self._ops.get(operationalization_id)
        if op is None:
            return False
        with self._lock:
            op.status = new_status
            op.updated_at = time.time()
            self._rewrite()
        return True

    def record_use(self, operationalization_id: str, success: bool = True) -> bool:
        op = self._ops.get(operationalization_id)
        if op is None:
            return False
        with self._lock:
            op.reuse_count += 1
            total = op.reuse_count
            old_successes = round(op.success_rate * (total - 1))
            new_successes = old_successes + (1 if success else 0)
            op.success_rate = round(new_successes / total, 4) if total > 0 else 0.0
            op.updated_at = time.time()
            self._rewrite()
        return True

    # ── Lineage ────────────────────────────────────────────────────

    def lineage(self, operationalization_id: str) -> dict[str, Any]:
        op = self._ops.get(operationalization_id)
        if op is None:
            return {"error": f"operationalization {operationalization_id} not found"}
        return {
            "operationalization_id": op.operationalization_id,
            "name": op.name,
            "form": op.form.value,
            "status": op.status.value,
            "capability_id": op.capability_id,
            "template_id": op.template_id,
            "invariants": op.invariants,
            "variables": op.variables,
            "reuse_count": op.reuse_count,
            "success_rate": op.success_rate,
            "reuse_score": compute_reuse_score(op)["composite_score"],
        }

    # ── Summary ────────────────────────────────────────────────────

    def summary(self) -> dict[str, Any]:
        by_form: dict[str, int] = Counter(op.form.value for op in self._ops.values())
        by_status: dict[str, int] = Counter(op.status.value for op in self._ops.values())
        total_reuse = sum(op.reuse_count for op in self._ops.values())
        return {
            "total_operationalizations": len(self._ops),
            "by_form": dict(by_form),
            "by_status": dict(by_status),
            "total_reuse_count": total_reuse,
        }
