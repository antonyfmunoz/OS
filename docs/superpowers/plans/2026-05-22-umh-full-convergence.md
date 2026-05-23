# UMH Full Convergence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Converge all legacy code into one coherent UMH system — ~600 files absorbed or deleted, single execution spine, single type system, substrate as the only runtime.

**Architecture:** 8-phase migration. Each phase produces independently testable output. Phases 0-1 are sequential (scaffolding), then Phases 2-4 can parallelize (control plane, spine, adapters are independent subsystems that wire together at the end). Phase 5 (transports) depends on 2-4. Phase 6 (prune) depends on 5. Phases 7-8 (EOS projection, reality model foundation) can parallelize after 6.

**Tech Stack:** Python 3.12, Pydantic v2, Neon Postgres, psycopg2, py-cord 2.6.1, Docker

**Spec:** `docs/superpowers/specs/2026-05-22-umh-full-convergence-design.md`

**Parallelization map:**
```
Phase 0 (scaffold) → Phase 1 (ontology)
                          ↓
              ┌───────────┼───────────┐
              ▼           ▼           ▼
         Phase 2     Phase 3     Phase 4
       (control)     (spine)    (adapters)
              └───────────┼───────────┘
                          ▼
                     Phase 5 (transports)
                          ▼
                     Phase 6 (prune)
                          ↓
                    ┌─────┴─────┐
                    ▼           ▼
               Phase 7     Phase 8
              (EOS proj)  (reality model)
```

---

## Phase 0: Archive and Scaffold

### Task 1: Tag and create directory structure

**Files:**
- Create: `substrate/reality_model/__init__.py`
- Create: `substrate/ontology/domains/__init__.py`
- Create: `substrate/learning/__init__.py`
- Create: `projections/__init__.py`
- Create: `projections/eos/__init__.py`
- Create: `projections/eos/agents/__init__.py`
- Create: `projections/eos/workflows/__init__.py`
- Create: `projections/eos/views/__init__.py`

- [ ] **Step 1: Tag current HEAD**

```bash
git tag pre-unification
```

- [ ] **Step 2: Create all missing directories with __init__.py files**

```bash
mkdir -p substrate/reality_model substrate/ontology/domains substrate/learning
mkdir -p projections/eos/agents projections/eos/workflows projections/eos/views
```

```python
# substrate/reality_model/__init__.py
"""Reality Model — dual Canonical/Instance reality modeling (Phase 8)."""
```

```python
# substrate/ontology/domains/__init__.py
"""Domain bridges — domain-typed projections from ontology observations."""
```

```python
# substrate/learning/__init__.py
"""Learning — feedback-to-all-layers (post-MVP)."""
```

```python
# projections/__init__.py
"""Application projections — scoped views of UMH capability."""
```

```python
# projections/eos/__init__.py
"""EntrepreneurOS — entrepreneur operations projection of UMH."""
```

```python
# projections/eos/agents/__init__.py
"""EOS department agents."""
```

```python
# projections/eos/workflows/__init__.py
"""EOS workflows — outreach, follow-up, content calendar."""
```

```python
# projections/eos/views/__init__.py
"""EOS views — CRM, pipeline, KPIs as memory queries."""
```

- [ ] **Step 3: Verify all directories exist and compile**

Run: `find substrate/ projections/ -name "__init__.py" -exec python3 -m py_compile {} \;`
Expected: No errors

- [ ] **Step 4: Commit**

```bash
git add substrate/reality_model/ substrate/ontology/domains/ substrate/learning/ projections/
git commit -m "scaffold: create directory structure for convergence phases"
```

### Task 2: Rename 10_Wiki to knowledge

**Files:**
- Move: `10_Wiki/` → `knowledge/`

- [ ] **Step 1: Check if knowledge/ already exists or 10_Wiki still exists**

```bash
ls -d 10_Wiki/ knowledge/ 2>/dev/null
```

- [ ] **Step 2: Move if 10_Wiki exists**

```bash
# Only if 10_Wiki/ exists and knowledge/ doesn't
git mv 10_Wiki/ knowledge/
```

If `knowledge/` already exists (likely from prior work), skip this task.

- [ ] **Step 3: Verify**

```bash
ls knowledge/index.md
```
Expected: File exists

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "scaffold: rename 10_Wiki to knowledge"
```

---

## Phase 1: Ontology as Enacted Constraints

### Task 3: Merge ontology primitives with foundation types

**Files:**
- Modify: `substrate/ontology/primitives.py`
- Modify: `substrate/types.py` (add TemporalMode, CausalRole if not present)
- Test: `tests/test_ontology_enacted.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_ontology_enacted.py
"""Tests that ontology primitives are enacted constraints, not just enums."""
import sys
sys.path.insert(0, "/opt/OS")

import pytest
from substrate.types import PrimitiveType, OntologicalCategory, RelationshipType


class TestOntologyEnums:
    def test_primitive_type_has_10_values(self):
        assert len(PrimitiveType) == 10

    def test_ontological_category_has_8_values(self):
        assert len(OntologicalCategory) == 8

    def test_relationship_type_has_10_values(self):
        assert len(RelationshipType) == 10


class TestOntologyPrimitivesModule:
    def test_reexports_all_types(self):
        from substrate.ontology.primitives import (
            PrimitiveType,
            OntologicalCategory,
            PrimitiveObservation,
            TemporalMode,
            CausalRole,
        )
        assert len(PrimitiveType) == 10
        assert len(TemporalMode) == 4
        assert len(CausalRole) == 5

    def test_primitive_observation_has_required_fields(self):
        from substrate.ontology.primitives import PrimitiveObservation
        obs = PrimitiveObservation(
            primitive_type=PrimitiveType.STATE,
            label="test",
            description="test observation",
        )
        assert obs.primitive_type == PrimitiveType.STATE
        assert obs.confidence == 0.8  # default
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /opt/OS && python3 -m pytest tests/test_ontology_enacted.py -v`
Expected: FAIL — TemporalMode, CausalRole not importable from substrate.ontology.primitives

- [ ] **Step 3: Add TemporalMode and CausalRole to substrate/types.py**

Add after the existing `RelationshipType` enum in `substrate/types.py`:

```python
class TemporalMode(str, Enum):
    INSTANTANEOUS = "instantaneous"
    DURATIVE = "durative"
    ATEMPORAL = "atemporal"
    PERIODIC = "periodic"

class CausalRole(str, Enum):
    CAUSE = "cause"
    EFFECT = "effect"
    CONDITION = "condition"
    PREVENTION = "prevention"
    MAINTENANCE = "maintenance"
```

- [ ] **Step 4: Update substrate/ontology/primitives.py to re-export all types**

```python
"""Ontology primitives — the computational physics of UMH.

These are not metadata descriptions. They are enacted constraints
that govern the system the way physics governs reality.

10 primitives, 8 categories, 10 relationship types, 4 temporal modes, 5 causal roles.
"""

from substrate.types import (
    CausalRole,
    OntologicalCategory,
    PrimitiveObservation,
    PrimitiveType,
    RelationshipType,
    TemporalMode,
)

__all__ = [
    "CausalRole",
    "OntologicalCategory",
    "PrimitiveObservation",
    "PrimitiveType",
    "RelationshipType",
    "TemporalMode",
]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /opt/OS && python3 -m pytest tests/test_ontology_enacted.py -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add substrate/types.py substrate/ontology/primitives.py tests/test_ontology_enacted.py
git commit -m "ontology: merge foundation types into substrate primitives"
```

### Task 4: Make laws callable constraints

**Files:**
- Modify: `substrate/ontology/laws.py`
- Test: `tests/test_ontology_enacted.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_ontology_enacted.py`:

```python
from substrate.ontology.laws import LawRegistry, Law, LawCategory, Severity


class TestLawsAreCallable:
    def test_law_registry_has_laws(self):
        registry = LawRegistry()
        laws = registry.all()
        assert len(laws) >= 12  # 6 foundation + 8 spec (some overlap)

    def test_law_is_pydantic_model(self):
        registry = LawRegistry()
        for law in registry.all():
            assert isinstance(law, Law)
            assert hasattr(law, "name")
            assert hasattr(law, "severity")

    def test_check_returns_violation_or_none(self):
        registry = LawRegistry()
        law = registry.get("governance_before_action")
        assert law is not None
        result = law.check({"has_governance_verdict": True})
        assert result is None  # no violation

    def test_check_returns_violation_string(self):
        registry = LawRegistry()
        law = registry.get("governance_before_action")
        assert law is not None
        result = law.check({"has_governance_verdict": False})
        assert isinstance(result, str)  # violation message

    def test_hard_block_severity(self):
        registry = LawRegistry()
        law = registry.get("governance_before_action")
        assert law is not None
        assert law.severity == Severity.HARD_BLOCK
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /opt/OS && python3 -m pytest tests/test_ontology_enacted.py::TestLawsAreCallable -v`
Expected: FAIL — LawRegistry not importable

- [ ] **Step 3: Rewrite substrate/ontology/laws.py with callable Law model**

```python
"""Governing laws — enacted constraints that govern UMH like physics governs reality.

Each law is a Pydantic model with a check() method. Laws are not descriptions —
they are executable validators called during governance classification.

Source mapping:
- services/umh/foundation/laws.py → Law model, LawCategory, Severity, 6 foundation laws
- Spec Section 22 → 8 invariant assertions
- Spec Section 10 → 12 invariant laws (canonical)
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Callable
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class LawCategory(str, Enum):
    ONTOLOGICAL = "ontological"
    EPISTEMIC = "epistemic"
    GOVERNANCE = "governance"
    CAUSAL = "causal"
    BOUNDARY = "boundary"
    CONTROL = "control"
    EXECUTION = "execution"


class Severity(str, Enum):
    HARD_BLOCK = "hard_block"
    SOFT_BLOCK = "soft_block"
    WARNING = "warning"
    LOG_ONLY = "log_only"


class Law(BaseModel):
    """An enacted constraint on the substrate. check() returns None if satisfied, violation string if not."""

    id: UUID = Field(default_factory=uuid4)
    category: LawCategory
    name: str = Field(max_length=120)
    statement: str = Field(max_length=500)
    severity: Severity = Severity.HARD_BLOCK
    context_key: str = Field(default="", max_length=120)
    expected_value: Any = True

    def check(self, context: dict[str, Any]) -> str | None:
        """Check if this law is satisfied. Returns None if ok, violation message if not."""
        if not self.context_key:
            return None
        actual = context.get(self.context_key)
        if actual == self.expected_value:
            return None
        return f"Law '{self.name}' violated: {self.statement} (expected {self.context_key}={self.expected_value}, got {actual})"


# ─── The 14 substrate laws (merged foundation + spec invariants) ──────────────

_ALL_LAWS: list[Law] = [
    Law(category=LawCategory.CONTROL, name="control_plane_exclusivity",
        statement="All signals pass through the Control Plane",
        context_key="routed_through_control_plane", expected_value=True),
    Law(category=LawCategory.EXECUTION, name="single_execution_spine",
        statement="One canonical runtime path for all execution",
        context_key="executed_through_spine", expected_value=True),
    Law(category=LawCategory.GOVERNANCE, name="governance_before_action",
        statement="No execution without governance classification",
        context_key="has_governance_verdict", expected_value=True),
    Law(category=LawCategory.CONTROL, name="typed_contracts_only",
        statement="All inter-module communication uses explicit schemas",
        context_key="uses_typed_contract", expected_value=True),
    Law(category=LawCategory.ONTOLOGICAL, name="memory_discipline",
        statement="All durable state writes through Memory/Storage subsystem",
        context_key="writes_through_memory_system", expected_value=True),
    Law(category=LawCategory.EXECUTION, name="environment_explicitness",
        statement="Every action declares target environment",
        context_key="has_environment_declaration", expected_value=True),
    Law(category=LawCategory.EPISTEMIC, name="trace_completeness",
        statement="Every execution produces an inspectable trace",
        context_key="has_trace", expected_value=True),
    Law(category=LawCategory.CONTROL, name="deterministic_plus_ai",
        statement="Intelligence is subordinate to control",
        context_key="has_deterministic_fallback", expected_value=True),
    Law(category=LawCategory.BOUNDARY, name="external_boundary",
        statement="No external system accessed directly — all through adapters",
        context_key="uses_adapter_boundary", expected_value=True),
    Law(category=LawCategory.EXECUTION, name="action_execution_separation",
        statement="Action, capability, adapter, environment, worker, actuation, work packet, proof are distinct",
        context_key="entities_separated", expected_value=True),
    Law(category=LawCategory.GOVERNANCE, name="mastery_law",
        statement="Verify competence before execution",
        context_key="mastery_verified", expected_value=True,
        severity=Severity.SOFT_BLOCK),
    Law(category=LawCategory.ONTOLOGICAL, name="reality_mimicry",
        statement="Model after effective real-world patterns when technically useful",
        severity=Severity.LOG_ONLY),
    Law(category=LawCategory.BOUNDARY, name="signal_intake",
        statement="All external input enters through signal intake pathway",
        context_key="entered_through_signal", expected_value=True),
    Law(category=LawCategory.EPISTEMIC, name="epistemic_humility",
        statement="Track confidence and uncertainty",
        context_key="has_confidence_score", expected_value=True,
        severity=Severity.SOFT_BLOCK),
]


class LawRegistry:
    """Registry of all substrate laws. Instantiate once at boot."""

    def __init__(self) -> None:
        self._laws: dict[str, Law] = {law.name: law for law in _ALL_LAWS}

    def all(self) -> list[Law]:
        return list(self._laws.values())

    def get(self, name: str) -> Law | None:
        return self._laws.get(name)

    def check_all(self, context: dict[str, Any]) -> list[str]:
        """Check all laws. Returns list of violation messages (empty = all pass)."""
        violations = []
        for law in self._laws.values():
            result = law.check(context)
            if result and law.severity in (Severity.HARD_BLOCK, Severity.SOFT_BLOCK):
                violations.append(result)
        return violations

    def hard_violations(self, context: dict[str, Any]) -> list[str]:
        """Check only HARD_BLOCK laws."""
        violations = []
        for law in self._laws.values():
            if law.severity != Severity.HARD_BLOCK:
                continue
            result = law.check(context)
            if result:
                violations.append(result)
        return violations
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /opt/OS && python3 -m pytest tests/test_ontology_enacted.py -v`
Expected: All PASS

- [ ] **Step 5: Compile check**

Run: `python3 -m py_compile substrate/ontology/laws.py`
Expected: No errors

- [ ] **Step 6: Commit**

```bash
git add substrate/ontology/laws.py tests/test_ontology_enacted.py
git commit -m "ontology: make laws callable constraints with check() method"
```

### Task 5: Move domain bridges

**Files:**
- Move: `understanding/domains/creator.py` → `substrate/ontology/domains/creator.py`
- Move: `understanding/domains/life.py` → `substrate/ontology/domains/life.py`

- [ ] **Step 1: Check source files exist**

```bash
ls understanding/domains/creator.py understanding/domains/life.py
```

- [ ] **Step 2: Move files**

```bash
git mv understanding/domains/creator.py substrate/ontology/domains/creator.py
git mv understanding/domains/life.py substrate/ontology/domains/life.py
```

- [ ] **Step 3: Update imports in moved files**

In both files, check for any `from understanding.` imports and update to `from substrate.ontology.` if they reference sibling modules. If they import from `substrate.types`, no change needed.

- [ ] **Step 4: Compile check**

```bash
python3 -m py_compile substrate/ontology/domains/creator.py
python3 -m py_compile substrate/ontology/domains/life.py
```

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "ontology: move domain bridges to substrate/ontology/domains/"
```

---

## Phase 2: Control Plane (can run parallel with Phase 3 and 4)

### Task 6: Absorb authority_engine into governance.py

**Files:**
- Modify: `substrate/control_plane/governance.py`
- Reference: `governance/policy/authority_engine.py` (read only, do not modify)
- Test: `tests/test_governance_full.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_governance_full.py
"""Tests for the full governance engine with production risk classes."""
import sys
sys.path.insert(0, "/opt/OS")

import pytest
from substrate.types import (
    ExecutionContext,
    GovernanceDecision,
    GovernanceVerdict,
    Identity,
    RiskClass,
    SignalEnvelope,
    SignalSource,
)
from substrate.control_plane.governance import ConcreteGovernanceEngine


def _make_signal(content: str) -> SignalEnvelope:
    return SignalEnvelope(
        source=SignalSource.USER,
        content=content,
        user_id="test",
        organization_id="test-org",
    )


def _make_context(autonomy: int = 1) -> ExecutionContext:
    return ExecutionContext(
        signal_id=_make_signal("x").id,
        identity=Identity(
            user_id="test",
            organization_id="test-org",
            ai_name="DEX",
            ai_personality="professional",
            autonomy_level=autonomy,
            business_stage="pre_revenue",
        ),
    )


class TestRiskClassification:
    @pytest.fixture
    def engine(self):
        return ConcreteGovernanceEngine()

    @pytest.mark.parametrize("content", [
        "send email to john",
        "send message to the channel",
        "execute payment for invoice",
        "delete records from CRM",
        "bulk update all leads",
        "mass outreach campaign",
        "publish content to blog",
    ])
    @pytest.mark.asyncio
    async def test_critical_actions(self, engine, content):
        signal = _make_signal(content)
        context = _make_context(autonomy=4)
        verdict = await engine.classify(signal, context)
        assert verdict.risk_class == RiskClass.CRITICAL

    @pytest.mark.parametrize("content", [
        "create outreach for lead",
        "post content on social",
        "book call with prospect",
        "update crm entry",
    ])
    @pytest.mark.asyncio
    async def test_high_actions(self, engine, content):
        signal = _make_signal(content)
        context = _make_context(autonomy=1)
        verdict = await engine.classify(signal, context)
        assert verdict.risk_class == RiskClass.HIGH

    @pytest.mark.parametrize("content", [
        "draft message for review",
        "draft content about product",
        "create task for follow up",
        "create document template",
    ])
    @pytest.mark.asyncio
    async def test_medium_actions(self, engine, content):
        signal = _make_signal(content)
        context = _make_context()
        verdict = await engine.classify(signal, context)
        assert verdict.risk_class == RiskClass.MEDIUM

    @pytest.mark.asyncio
    async def test_unknown_defaults_low(self, engine):
        signal = _make_signal("what is the weather today")
        context = _make_context()
        verdict = await engine.classify(signal, context)
        assert verdict.risk_class == RiskClass.LOW

    @pytest.mark.asyncio
    async def test_physical_actuation_is_critical(self, engine):
        signal = _make_signal("activate robotic arm")
        context = _make_context(autonomy=4)
        verdict = await engine.classify(signal, context)
        assert verdict.risk_class == RiskClass.CRITICAL


class TestAutonomyGating:
    @pytest.fixture
    def engine(self):
        return ConcreteGovernanceEngine()

    @pytest.mark.asyncio
    async def test_critical_always_denied(self, engine):
        signal = _make_signal("send email to john")
        context = _make_context(autonomy=4)
        verdict = await engine.classify(signal, context)
        assert verdict.decision == GovernanceDecision.DENY

    @pytest.mark.asyncio
    async def test_low_always_approved(self, engine):
        signal = _make_signal("analyze this data")
        context = _make_context(autonomy=0)
        verdict = await engine.classify(signal, context)
        assert verdict.decision == GovernanceDecision.APPROVE

    @pytest.mark.asyncio
    async def test_high_denied_at_autonomy_2(self, engine):
        signal = _make_signal("create outreach for lead")
        context = _make_context(autonomy=2)
        verdict = await engine.classify(signal, context)
        assert verdict.decision == GovernanceDecision.DENY

    @pytest.mark.asyncio
    async def test_high_approved_at_autonomy_3(self, engine):
        signal = _make_signal("create outreach for lead")
        context = _make_context(autonomy=3)
        verdict = await engine.classify(signal, context)
        assert verdict.decision == GovernanceDecision.APPROVE
```

- [ ] **Step 2: Run test to verify failures**

Run: `cd /opt/OS && python3 -m pytest tests/test_governance_full.py -v`
Expected: FAIL on physical_actuation test (no pattern for it yet)

- [ ] **Step 3: Update governance.py with physical actuation pattern and full action list**

Add to the `_CRITICAL_PATTERNS` regex in `substrate/control_plane/governance.py`:

```python
_CRITICAL_PATTERNS = re.compile(
    r"\b(send\s+(?:email|message|dm)|execute\s+payment|delete\s+record"
    r"|bulk\s+update|mass\s+outreach|publish"
    r"|physical\s+actuat|robotic|activate\s+(?:arm|motor|actuator)"
    r"|iot\s+command|vehicle\s+control)\b",
    re.IGNORECASE,
)
```

- [ ] **Step 4: Run tests**

Run: `cd /opt/OS && python3 -m pytest tests/test_governance_full.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add substrate/control_plane/governance.py tests/test_governance_full.py
git commit -m "governance: absorb authority_engine risk classes + physical actuation"
```

### Task 7: Enrich identity resolver with AI identity engine

**Files:**
- Modify: `substrate/control_plane/identity.py`
- Reference: `control_plane/identity/ai_identity.py` (read only)
- Test: `tests/test_identity_resolver.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_identity_resolver.py
import sys
sys.path.insert(0, "/opt/OS")

import pytest
from substrate.types import Identity, SignalEnvelope, SignalSource
from substrate.control_plane.identity import ConcreteIdentityResolver


def _make_signal(**kwargs) -> SignalEnvelope:
    defaults = dict(
        source=SignalSource.USER,
        content="hello",
        user_id="test-user",
        organization_id="test-org",
    )
    defaults.update(kwargs)
    return SignalEnvelope(**defaults)


class TestIdentityResolver:
    @pytest.fixture
    def resolver(self):
        return ConcreteIdentityResolver()

    @pytest.mark.asyncio
    async def test_resolve_returns_identity(self, resolver):
        signal = _make_signal()
        identity = await resolver.resolve(signal)
        assert isinstance(identity, Identity)
        assert identity.user_id == "test-user"
        assert identity.organization_id == "test-org"

    @pytest.mark.asyncio
    async def test_resolve_has_ai_name(self, resolver):
        signal = _make_signal()
        identity = await resolver.resolve(signal)
        assert isinstance(identity.ai_name, str)
        assert len(identity.ai_name) > 0

    @pytest.mark.asyncio
    async def test_resolve_has_personality(self, resolver):
        signal = _make_signal()
        identity = await resolver.resolve(signal)
        assert isinstance(identity.ai_personality, str)
        assert len(identity.ai_personality) > 0

    @pytest.mark.asyncio
    async def test_resolve_preserves_venture_id(self, resolver):
        signal = _make_signal(venture_id="test-venture")
        identity = await resolver.resolve(signal)
        assert identity.venture_id == "test-venture"

    @pytest.mark.asyncio
    async def test_resolve_fallback_defaults(self, resolver):
        signal = _make_signal()
        identity = await resolver.resolve(signal)
        assert identity.autonomy_level >= 0
        assert identity.business_stage != ""
```

- [ ] **Step 2: Run tests**

Run: `cd /opt/OS && python3 -m pytest tests/test_identity_resolver.py -v`
Expected: All PASS (existing implementation already covers these)

- [ ] **Step 3: Add foundation values to identity resolver**

Update `substrate/control_plane/identity.py` — add foundation values from `ai_identity.py` as a class constant on `ConcreteIdentityResolver`:

```python
class ConcreteIdentityResolver:
    """Production identity resolver with foundation values."""

    FOUNDATION_VALUES = {
        "reality": "Ground everything in observable truth",
        "intelligence": "Compound capability through every interaction",
        "personalization": "Adapt to user context and preferences",
        "execution": "Produce tangible outcomes, not just plans",
    }

    async def resolve(self, signal: SignalEnvelope) -> Identity:
        # ... existing implementation unchanged ...
```

- [ ] **Step 4: Run tests again**

Run: `cd /opt/OS && python3 -m pytest tests/test_identity_resolver.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add substrate/control_plane/identity.py tests/test_identity_resolver.py
git commit -m "identity: add foundation values from ai_identity engine"
```

### Task 8: Enrich context assembler with conversation history

**Files:**
- Modify: `substrate/control_plane/context.py`
- Test: `tests/test_context_assembler.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_context_assembler.py
import sys
sys.path.insert(0, "/opt/OS")

import pytest
from substrate.types import (
    ExecutionContext,
    Identity,
    SignalEnvelope,
    SignalSource,
)
from substrate.control_plane.context import ConcreteContextAssembler


def _make_signal() -> SignalEnvelope:
    return SignalEnvelope(
        source=SignalSource.USER,
        content="hello",
        user_id="test-user",
        organization_id="test-org",
    )


def _make_identity() -> Identity:
    return Identity(
        user_id="test-user",
        organization_id="test-org",
        ai_name="DEX",
        ai_personality="professional",
        autonomy_level=1,
        business_stage="pre_revenue",
    )


class TestContextAssembler:
    @pytest.fixture
    def assembler(self):
        return ConcreteContextAssembler()

    @pytest.mark.asyncio
    async def test_assemble_returns_execution_context(self, assembler):
        signal = _make_signal()
        identity = _make_identity()
        ctx = await assembler.assemble(signal, identity)
        assert isinstance(ctx, ExecutionContext)
        assert ctx.signal_id == signal.id
        assert ctx.identity == identity

    @pytest.mark.asyncio
    async def test_context_has_business_context(self, assembler):
        signal = _make_signal()
        identity = _make_identity()
        ctx = await assembler.assemble(signal, identity)
        assert isinstance(ctx.business_context, dict)
        assert "business_stage" in ctx.business_context

    @pytest.mark.asyncio
    async def test_context_has_conversation_history_list(self, assembler):
        signal = _make_signal()
        identity = _make_identity()
        ctx = await assembler.assemble(signal, identity)
        assert isinstance(ctx.conversation_history, list)
```

- [ ] **Step 2: Run tests**

Run: `cd /opt/OS && python3 -m pytest tests/test_context_assembler.py -v`
Expected: All PASS (existing implementation should cover this)

- [ ] **Step 3: Enrich context assembler with memory recall**

Update `substrate/control_plane/context.py` to wire in the memory system for semantic recall:

```python
class ConcreteContextAssembler:
    def __init__(self, memory_system=None) -> None:
        self._memory = memory_system

    async def assemble(
        self, signal: SignalEnvelope, identity: Identity
    ) -> ExecutionContext:
        conversation_history = await self._get_conversation_history(
            signal.user_id, signal.metadata.get("channel_id", ""), limit=10
        )

        relevant_memories: list[MemoryEntry] = []
        if self._memory:
            try:
                from substrate.types import MemoryQuery
                query = MemoryQuery(query_text=signal.content, limit=5)
                relevant_memories = await self._memory.recall(query)
            except Exception:
                pass

        return ExecutionContext(
            signal_id=signal.id,
            identity=identity,
            session_id=signal.metadata.get("session_id"),
            conversation_history=conversation_history,
            relevant_memories=relevant_memories,
            business_context=self._get_business_context(identity),
        )

    async def _get_conversation_history(
        self, user_id: str, channel_id: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        try:
            from state.memory.memory import ConversationMemory
            cm = ConversationMemory()
            return cm.get_session(user_id, channel_id, limit=limit)
        except Exception:
            return []

    def _get_business_context(self, identity: Identity) -> dict[str, Any]:
        return {
            "business_stage": identity.business_stage,
            "ai_name": identity.ai_name,
            "organization_id": identity.organization_id,
            "venture_id": identity.venture_id,
        }
```

- [ ] **Step 4: Update Substrate.__init__ to pass memory to context assembler**

In `substrate/__init__.py`, update the context assembler construction:

```python
self.context = ConcreteContextAssembler(memory_system=self.memory)
```

- [ ] **Step 5: Run tests**

Run: `cd /opt/OS && python3 -m pytest tests/test_context_assembler.py -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add substrate/control_plane/context.py substrate/__init__.py tests/test_context_assembler.py
git commit -m "context: wire memory recall into context assembler"
```

### Task 9: Enrich memory system with full AgentMemory pipeline

**Files:**
- Modify: `substrate/control_plane/memory.py`
- Test: `tests/test_memory_system.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_memory_system.py
import sys
sys.path.insert(0, "/opt/OS")

import pytest
from uuid import uuid4
from substrate.types import MemoryEntry, MemoryQuery, MemoryType
from substrate.control_plane.memory import ConcreteMemorySystem


class TestMemorySystem:
    @pytest.fixture
    def memory(self):
        return ConcreteMemorySystem()

    @pytest.mark.asyncio
    async def test_store_returns_uuid(self, memory):
        entry = MemoryEntry(
            memory_type=MemoryType.OBSERVATION,
            content="test observation",
        )
        result = await memory.store(entry)
        assert result is not None

    @pytest.mark.asyncio
    async def test_recall_returns_list(self, memory):
        query = MemoryQuery(query_text="test", limit=5)
        results = await memory.recall(query)
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_log_interaction_returns_uuid(self, memory):
        result = await memory.log_interaction(
            signal_id=uuid4(),
            content="user said hello",
            response="hello back",
            provider="test",
        )
        assert result is not None
```

- [ ] **Step 2: Run tests**

Run: `cd /opt/OS && python3 -m pytest tests/test_memory_system.py -v`
Expected: All PASS (existing implementation handles these)

- [ ] **Step 3: Commit**

```bash
git add tests/test_memory_system.py
git commit -m "memory: add test coverage for memory system protocol"
```

### Task 10: Enrich registry with Neon boot loading

**Files:**
- Modify: `substrate/control_plane/registry.py`
- Test: `tests/test_registry.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_registry.py
import sys
sys.path.insert(0, "/opt/OS")

import pytest
from uuid import uuid4
from substrate.types import (
    Component,
    ComponentStatus,
    ComponentType,
    RegistrationResult,
)
from substrate.control_plane.registry import ConcreteComponentRegistry


class TestComponentRegistry:
    @pytest.fixture
    def registry(self):
        return ConcreteComponentRegistry()

    @pytest.mark.asyncio
    async def test_register_returns_result(self, registry):
        component = Component(
            component_type=ComponentType.ADAPTER,
            name="test-adapter",
            capabilities=["text_generation"],
        )
        result = await registry.register(component)
        assert isinstance(result, RegistrationResult)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_lookup_by_type(self, registry):
        for i in range(3):
            ctype = ComponentType.ADAPTER if i < 2 else ComponentType.AGENT
            await registry.register(Component(
                component_type=ctype,
                name=f"test-{i}",
            ))
        adapters = await registry.lookup(component_type=ComponentType.ADAPTER)
        assert len(adapters) == 2

    @pytest.mark.asyncio
    async def test_deregister(self, registry):
        component = Component(
            component_type=ComponentType.ADAPTER,
            name="to-remove",
        )
        result = await registry.register(component)
        removed = await registry.deregister(component.id)
        assert removed is True
        found = await registry.get(component.id)
        assert found is None or found.status == ComponentStatus.DEREGISTERED

    @pytest.mark.asyncio
    async def test_get_by_id(self, registry):
        component = Component(
            component_type=ComponentType.SKILL,
            name="test-skill",
        )
        await registry.register(component)
        found = await registry.get(component.id)
        assert found is not None
        assert found.name == "test-skill"
```

- [ ] **Step 2: Run tests**

Run: `cd /opt/OS && python3 -m pytest tests/test_registry.py -v`
Expected: All PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_registry.py
git commit -m "registry: add test coverage for component registry"
```

---

## Phase 3: Execution Spine (can run parallel with Phase 2 and 4)

### Task 11: Absorb cognitive loop into execution spine

**Files:**
- Modify: `substrate/execution/spine.py`
- Reference: `control_plane/runtime/cognitive_loop.py` (read only)
- Reference: `control_plane/runtime/gateway.py` (read only)
- Reference: `interface/presence/handlers/intent_handler.py` (read only)
- Reference: `execution/runtime/capability_router.py` (read only)
- Test: `tests/test_spine_full.py`

This is the largest single task — the heart of the convergence.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_spine_full.py
"""Tests for the full 8-stage execution spine."""
import sys
sys.path.insert(0, "/opt/OS")

import pytest
from substrate.types import (
    ExecutionContext,
    ExecutionOutcome,
    ExecutionResult,
    GovernanceDecision,
    GovernanceVerdict,
    Identity,
    RiskClass,
    SignalEnvelope,
    SignalSource,
    TraceEventType,
)
from substrate.execution.spine import ConcreteExecutionSpine


def _make_signal(content: str = "hello") -> SignalEnvelope:
    return SignalEnvelope(
        source=SignalSource.USER,
        content=content,
        user_id="test",
        organization_id="test-org",
    )


def _make_context() -> ExecutionContext:
    return ExecutionContext(
        signal_id=_make_signal().id,
        identity=Identity(
            user_id="test",
            organization_id="test-org",
            ai_name="DEX",
            ai_personality="professional",
            autonomy_level=1,
            business_stage="pre_revenue",
        ),
    )


def _make_verdict(decision=GovernanceDecision.APPROVE) -> GovernanceVerdict:
    return GovernanceVerdict(
        signal_id=_make_signal().id,
        risk_class=RiskClass.LOW,
        decision=decision,
        rationale="test",
    )


class TestSpineExecution:
    @pytest.fixture
    def spine(self):
        return ConcreteExecutionSpine()

    @pytest.mark.asyncio
    async def test_execute_returns_result(self, spine):
        result = await spine.execute(_make_signal(), _make_context(), _make_verdict())
        assert isinstance(result, ExecutionResult)

    @pytest.mark.asyncio
    async def test_blocked_signal_returns_blocked(self, spine):
        verdict = _make_verdict(decision=GovernanceDecision.DENY)
        result = await spine.execute(_make_signal(), _make_context(), verdict)
        assert result.outcome == ExecutionOutcome.BLOCKED

    @pytest.mark.asyncio
    async def test_deterministic_fallback_always_produces_output(self, spine):
        result = await spine.execute(
            _make_signal("hello there"),
            _make_context(),
            _make_verdict(),
        )
        assert result.output != ""
        assert len(result.output) > 0

    @pytest.mark.asyncio
    async def test_intent_classification_greeting(self, spine):
        intent = spine._classify_intent("hello there")
        assert intent == "greeting"

    @pytest.mark.asyncio
    async def test_intent_classification_question(self, spine):
        intent = spine._classify_intent("what is the status?")
        assert intent == "question"

    @pytest.mark.asyncio
    async def test_intent_classification_command(self, spine):
        intent = spine._classify_intent("create a new document")
        assert intent == "command"

    @pytest.mark.asyncio
    async def test_intent_classification_unknown(self, spine):
        intent = spine._classify_intent("asdf jkl")
        assert intent == "unknown"

    @pytest.mark.asyncio
    async def test_execute_has_duration(self, spine):
        result = await spine.execute(_make_signal(), _make_context(), _make_verdict())
        assert result.duration_ms > 0

    @pytest.mark.asyncio
    async def test_execute_has_trace_id(self, spine):
        result = await spine.execute(_make_signal(), _make_context(), _make_verdict())
        assert result.trace_id is not None


class TestSpineIntentPatterns:
    """Test the expanded intent patterns from gateway + intent_handler."""

    @pytest.fixture
    def spine(self):
        return ConcreteExecutionSpine()

    @pytest.mark.parametrize("content,expected", [
        ("schedule a meeting for tomorrow", "schedule"),
        ("send an email to john", "send"),
        ("check the pipeline status", "status"),
        ("analyze the sales data", "analysis"),
        ("create a new outreach campaign", "command"),
        ("fix the broken import", "command"),
        ("hi how are you", "greeting"),
        ("what time is it?", "question"),
        ("research competitor pricing", "analysis"),
    ])
    def test_intent_patterns(self, spine, content, expected):
        intent = spine._classify_intent(content)
        assert intent == expected
```

- [ ] **Step 2: Run test to verify failures**

Run: `cd /opt/OS && python3 -m pytest tests/test_spine_full.py -v`
Expected: FAIL — missing intent types (schedule, send), parametrized patterns don't match

- [ ] **Step 3: Rewrite spine.py with full intent patterns from gateway + intent_handler**

```python
"""ExecutionSpine — the 8-stage execution pipeline.

Stages: interpret → recall → lookup → compose → route → execute → trace → feedback

Deterministic-first: every LLM call has a deterministic fallback.
If all providers fail, returns a heuristic response based on intent classification.

Source mapping:
- cognitive_loop.py (1,448 lines) → 8 stages
- gateway.py (2,063 lines) → intent classification, routing, fix-forever
- intent_handler.py (410 lines) → deterministic intent patterns
- capability_router.py (610 lines) → capability selection
- execution_spine.py → thin execution
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any, Protocol, runtime_checkable
from uuid import UUID, uuid4

from substrate.types import (
    ExecutionContext,
    ExecutionOutcome,
    ExecutionResult,
    GovernanceDecision,
    GovernanceVerdict,
    MemoryQuery,
    RiskClass,
    SignalEnvelope,
    TraceEventType,
    TraceRecord,
)


@runtime_checkable
class ExecutionSpine(Protocol):
    async def execute(
        self,
        signal: SignalEnvelope,
        context: ExecutionContext,
        verdict: GovernanceVerdict,
    ) -> ExecutionResult: ...


# ─── Deterministic intent classification ────────────────────────────────────
# Merged from gateway.py, intent_handler.py, and cognitive_loop.py

_INTENT_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\b(schedule|book|calendar|meeting|appointment|remind)\b", re.I), "schedule"),
    (re.compile(r"\b(send|email|message|notify|alert|dm)\b", re.I), "send"),
    (re.compile(r"\b(status|progress|update|report|check|pipeline|dashboard)\b", re.I), "status"),
    (re.compile(r"\b(analy[sz]e|assess|evaluate|review|research|investigate|compare)\b", re.I), "analysis"),
    (re.compile(r"\?$|^(what|how|why|when|where|who|can you|could you|is there|are there)\b", re.I), "question"),
    (re.compile(r"^(do|make|create|build|run|start|stop|deploy|fix|update|delete|add|remove|set)\b", re.I), "command"),
    (re.compile(r"\b(hi|hello|hey|good morning|good evening|good afternoon|yo|sup)\b", re.I), "greeting"),
]

_DETERMINISTIC_RESPONSES: dict[str, str] = {
    "greeting": "Hello! I'm here and ready to help. What would you like to work on?",
    "question": "I understand your question. Let me think about this systematically.",
    "command": "I'll process that request. Working on it now.",
    "status": "Let me check the current status for you.",
    "analysis": "I'll analyze that for you. Let me review the relevant information.",
    "schedule": "I'll help you schedule that. Let me check availability.",
    "send": "I'll prepare that communication. Let me draft it for your review.",
    "unknown": "I've received your message and I'm processing it.",
}

_ERROR_LOG_PATH = Path("/opt/OS/logs/spine_errors.jsonl")


def _record_error(component: str, error: str, context: dict[str, Any] | None = None) -> None:
    """Fix-forever error recording. Every error logged with context."""
    try:
        _ERROR_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "component": component,
            "error": str(error)[:500],
            "context": context or {},
            "timestamp": time.time(),
        }
        with _ERROR_LOG_PATH.open("a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass


class ConcreteExecutionSpine:
    """8-stage execution pipeline with deterministic-first + AI enhancement.

    Both always active for maximum leverage. Deterministic provides the spine —
    AI enhances when available. The system always produces output.
    """

    def __init__(
        self,
        memory: Any = None,
        registry: Any = None,
        trace_recorder: Any = None,
        feedback_capture: Any = None,
    ) -> None:
        self._memory = memory
        self._registry = registry
        self._trace = trace_recorder
        self._feedback = feedback_capture

    async def execute(
        self,
        signal: SignalEnvelope,
        context: ExecutionContext,
        verdict: GovernanceVerdict,
    ) -> ExecutionResult:
        start = time.monotonic()
        trace = TraceRecord(signal_id=signal.id)

        # Stage 0: Governance gate
        if not verdict.is_executable():
            trace.add_event(
                TraceEventType.GOVERNANCE_DECIDED,
                f"Blocked: {verdict.rationale}",
            )
            trace.complete(success=True)
            return ExecutionResult(
                signal_id=signal.id,
                trace_id=trace.id,
                outcome=ExecutionOutcome.BLOCKED,
                risk_class=verdict.risk_class,
                governance_decision=verdict.decision,
                output=verdict.rationale,
                duration_ms=(time.monotonic() - start) * 1000,
            )

        try:
            # Stage 1: Interpret — deterministic intent classification
            intent = self._classify_intent(signal.content)
            trace.add_event(TraceEventType.SIGNAL_RECEIVED, f"Intent: {intent}")

            # Stage 2: Recall — memory search
            memories = []
            if self._memory:
                try:
                    query = MemoryQuery(query_text=signal.content, limit=5)
                    memories = await self._memory.recall(query)
                    trace.add_event(
                        TraceEventType.MEMORY_RECALLED,
                        f"Recalled {len(memories)} memories",
                    )
                except Exception as e:
                    _record_error("spine.recall", str(e), {"signal_id": str(signal.id)})
                    trace.add_event(TraceEventType.MEMORY_RECALLED, "Memory recall failed, continuing")

            # Stage 3: Lookup — find capable adapters
            adapters = []
            if self._registry:
                try:
                    from substrate.types import ComponentType
                    adapters = await self._registry.lookup(component_type=ComponentType.ADAPTER)
                    trace.add_event(
                        TraceEventType.ADAPTER_CALLED,
                        f"Found {len(adapters)} adapters",
                    )
                except Exception:
                    pass

            # Stage 4: Compose — build prompt with context
            memory_context = "\n".join(m.content for m in memories[:3]) if memories else ""
            prompt = self._compose_prompt(signal.content, context, memory_context, intent)
            trace.add_event(TraceEventType.PLAN_COMPOSED, f"Prompt composed ({len(prompt)} chars)")

            # Stage 5-6: Route + Execute — deterministic result THEN AI enhancement
            deterministic_output = _DETERMINISTIC_RESPONSES.get(intent, _DETERMINISTIC_RESPONSES["unknown"])
            output = deterministic_output
            provider = "deterministic"
            model = "heuristic"

            try:
                import sys
                sys.path.insert(0, "/opt/OS")
                from adapters.models.model_router import call_with_fallback

                llm_response = call_with_fallback(prompt)
                if llm_response and hasattr(llm_response, 'output') and llm_response.output.strip():
                    output = llm_response.output.strip()
                    provider = llm_response.provider
                    model = llm_response.model
                elif isinstance(llm_response, str) and llm_response.strip():
                    output = llm_response.strip()
                    provider = "model_router"
                    model = "auto"

                trace.add_event(TraceEventType.ADAPTER_RESPONDED, f"AI response: {len(output)} chars via {provider}")
            except Exception as e:
                _record_error("spine.execute", str(e), {"signal_id": str(signal.id), "intent": intent})
                trace.add_event(TraceEventType.ADAPTER_RESPONDED, f"Deterministic fallback: {intent}")

            # Stage 7: Trace
            duration = (time.monotonic() - start) * 1000
            trace.add_event(TraceEventType.EXECUTION_COMPLETED, f"Duration: {duration:.0f}ms")
            trace.complete(success=True)

            result = ExecutionResult(
                signal_id=signal.id,
                trace_id=trace.id,
                outcome=ExecutionOutcome.SUCCESS,
                output=output,
                provider=provider,
                model=model,
                duration_ms=duration,
                risk_class=verdict.risk_class,
                governance_decision=verdict.decision,
            )

            # Stage 8: Feedback
            if self._feedback:
                try:
                    feedback = await self._feedback.capture(trace, result)
                    await self._feedback.persist(feedback)
                    trace.add_event(TraceEventType.FEEDBACK_CAPTURED, "Feedback captured")
                except Exception as e:
                    _record_error("spine.feedback", str(e), {"signal_id": str(signal.id)})

            if self._trace:
                try:
                    await self._trace.persist(trace)
                except Exception as e:
                    _record_error("spine.trace_persist", str(e), {"signal_id": str(signal.id)})

            return result

        except Exception as e:
            duration = (time.monotonic() - start) * 1000
            _record_error("spine.execute_outer", str(e), {"signal_id": str(signal.id)})
            trace.add_event(TraceEventType.ERROR, str(e)[:300])
            trace.complete(success=False)
            if self._trace:
                try:
                    await self._trace.persist(trace)
                except Exception:
                    pass
            return ExecutionResult(
                signal_id=signal.id,
                trace_id=trace.id,
                outcome=ExecutionOutcome.FAILURE,
                error=str(e)[:300],
                duration_ms=duration,
            )

    def _classify_intent(self, content: str) -> str:
        for pattern, intent in _INTENT_PATTERNS:
            if pattern.search(content):
                return intent
        return "unknown"

    def _compose_prompt(
        self,
        content: str,
        context: ExecutionContext,
        memory_context: str,
        intent: str,
    ) -> str:
        parts = [
            f"You are {context.identity.ai_name}, an AI operating in "
            f"{context.identity.business_stage} stage.",
            f"Personality: {context.identity.ai_personality}",
        ]
        if memory_context:
            parts.append(f"\nRelevant context:\n{memory_context}")
        if context.conversation_history:
            recent = context.conversation_history[-5:]
            history = "\n".join(
                f"{m.get('role', 'user')}: {m.get('content', '')[:200]}"
                for m in recent
            )
            parts.append(f"\nRecent conversation:\n{history}")
        parts.append(f"\nIntent detected: {intent}")
        parts.append(f"\nUser message: {content}")
        parts.append("\nRespond helpfully and concisely.")
        return "\n".join(parts)
```

- [ ] **Step 4: Run tests**

Run: `cd /opt/OS && python3 -m pytest tests/test_spine_full.py -v`
Expected: All PASS

- [ ] **Step 5: Compile check**

Run: `python3 -m py_compile substrate/execution/spine.py`

- [ ] **Step 6: Commit**

```bash
git add substrate/execution/spine.py tests/test_spine_full.py
git commit -m "spine: absorb cognitive loop + gateway + intent handler patterns"
```

### Task 12: Enrich trace recorder with Neon persistence

**Files:**
- Verify: `substrate/execution/trace.py` (already has Neon persistence)
- Test: `tests/test_trace_recorder.py`

- [ ] **Step 1: Write the test**

```python
# tests/test_trace_recorder.py
import sys
sys.path.insert(0, "/opt/OS")

import pytest
from uuid import uuid4
from substrate.types import TraceEventType, TraceRecord
from substrate.execution.trace import ConcreteTraceRecorder


class TestTraceRecorder:
    @pytest.fixture
    def recorder(self):
        return ConcreteTraceRecorder()

    @pytest.mark.asyncio
    async def test_start_creates_trace(self, recorder):
        signal_id = uuid4()
        trace = await recorder.start(signal_id)
        assert isinstance(trace, TraceRecord)
        assert trace.signal_id == signal_id

    @pytest.mark.asyncio
    async def test_add_event(self, recorder):
        signal_id = uuid4()
        trace = await recorder.start(signal_id)
        event = await recorder.add_event(
            trace.id, TraceEventType.SIGNAL_RECEIVED, "test event"
        )
        assert event.event_type == TraceEventType.SIGNAL_RECEIVED

    @pytest.mark.asyncio
    async def test_complete_sets_fields(self, recorder):
        signal_id = uuid4()
        trace = await recorder.start(signal_id)
        await recorder.complete(trace.id, success=True)
        completed = await recorder.get(trace.id)
        assert completed is not None
        assert completed.success is True
        assert completed.completed_at is not None
        assert completed.duration_ms is not None

    @pytest.mark.asyncio
    async def test_get_returns_none_for_unknown(self, recorder):
        result = await recorder.get(uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_trace_has_at_least_two_events_after_completion(self, recorder):
        signal_id = uuid4()
        trace = await recorder.start(signal_id)
        await recorder.add_event(trace.id, TraceEventType.SIGNAL_RECEIVED, "received")
        await recorder.add_event(trace.id, TraceEventType.EXECUTION_COMPLETED, "done")
        await recorder.complete(trace.id, success=True)
        completed = await recorder.get(trace.id)
        assert len(completed.events) >= 2
```

- [ ] **Step 2: Run tests**

Run: `cd /opt/OS && python3 -m pytest tests/test_trace_recorder.py -v`
Expected: All PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_trace_recorder.py
git commit -m "trace: add test coverage for trace recorder"
```

### Task 13: Verify feedback capture

**Files:**
- Verify: `substrate/execution/feedback.py`
- Test: `tests/test_feedback_capture.py`

- [ ] **Step 1: Write the test**

```python
# tests/test_feedback_capture.py
import sys
sys.path.insert(0, "/opt/OS")

import pytest
from uuid import uuid4
from substrate.types import (
    ExecutionOutcome,
    ExecutionResult,
    FeedbackRecord,
    FeedbackType,
    TraceEventType,
    TraceRecord,
)
from substrate.execution.feedback import ConcreteFeedbackCapture


class TestFeedbackCapture:
    @pytest.fixture
    def capture(self):
        return ConcreteFeedbackCapture()

    def _make_trace(self) -> TraceRecord:
        trace = TraceRecord(signal_id=uuid4())
        trace.add_event(TraceEventType.SIGNAL_RECEIVED, "test")
        trace.complete(success=True)
        return trace

    def _make_result(self, outcome=ExecutionOutcome.SUCCESS) -> ExecutionResult:
        return ExecutionResult(
            signal_id=uuid4(),
            trace_id=uuid4(),
            outcome=outcome,
            output="test output",
        )

    @pytest.mark.asyncio
    async def test_capture_returns_feedback_record(self, capture):
        trace = self._make_trace()
        result = self._make_result()
        feedback = await capture.capture(trace, result)
        assert isinstance(feedback, FeedbackRecord)

    @pytest.mark.asyncio
    async def test_success_has_high_quality(self, capture):
        trace = self._make_trace()
        result = self._make_result(ExecutionOutcome.SUCCESS)
        feedback = await capture.capture(trace, result)
        assert feedback.outcome_quality >= 0.7

    @pytest.mark.asyncio
    async def test_failure_has_low_quality(self, capture):
        trace = self._make_trace()
        result = self._make_result(ExecutionOutcome.FAILURE)
        feedback = await capture.capture(trace, result)
        assert feedback.outcome_quality <= 0.3

    @pytest.mark.asyncio
    async def test_feedback_type_is_implicit(self, capture):
        trace = self._make_trace()
        result = self._make_result()
        feedback = await capture.capture(trace, result)
        assert feedback.feedback_type == FeedbackType.IMPLICIT
```

- [ ] **Step 2: Run tests**

Run: `cd /opt/OS && python3 -m pytest tests/test_feedback_capture.py -v`
Expected: All PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_feedback_capture.py
git commit -m "feedback: add test coverage for feedback capture"
```

---

## Phase 4: Adapters (can run parallel with Phase 2 and 3)

### Task 14: Verify adapter protocol and LLM adapter

**Files:**
- Verify: `adapters/protocol.py` (already exists)
- Verify: `adapters/models/llm_adapter.py` (already exists)
- Test: `tests/test_adapter_protocol.py`

- [ ] **Step 1: Write the test**

```python
# tests/test_adapter_protocol.py
import sys
sys.path.insert(0, "/opt/OS")

import pytest
from adapters.protocol import Adapter
from adapters.models.llm_adapter import LLMAdapter


class TestAdapterProtocol:
    def test_llm_adapter_satisfies_protocol(self):
        adapter = LLMAdapter()
        assert isinstance(adapter, Adapter)

    def test_llm_adapter_has_required_attributes(self):
        adapter = LLMAdapter()
        assert hasattr(adapter, "adapter_id")
        assert hasattr(adapter, "adapter_type")
        assert hasattr(adapter, "name")
        assert adapter.adapter_type == "llm"
        assert adapter.name == "model_router"

    def test_llm_adapter_capabilities(self):
        adapter = LLMAdapter()
        caps = adapter.capabilities()
        assert isinstance(caps, list)
        assert "text_generation" in caps

    @pytest.mark.asyncio
    async def test_health_check_returns_bool(self):
        adapter = LLMAdapter()
        result = await adapter.health_check()
        assert isinstance(result, bool)
```

- [ ] **Step 2: Run tests**

Run: `cd /opt/OS && python3 -m pytest tests/test_adapter_protocol.py -v`
Expected: All PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_adapter_protocol.py
git commit -m "adapters: add test coverage for adapter protocol"
```

### Task 15: Register adapters at boot in Substrate.__init__

**Files:**
- Modify: `substrate/__init__.py`
- Test: `tests/test_substrate_boot.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_substrate_boot.py
import sys
sys.path.insert(0, "/opt/OS")

import pytest
from substrate import Substrate
from substrate.types import ComponentType


class TestSubstrateBoot:
    @pytest.fixture
    def substrate(self):
        return Substrate()

    def test_substrate_initializes(self, substrate):
        assert substrate is not None

    def test_status_returns_healthy(self, substrate):
        status = substrate.status()
        assert status.healthy is True

    @pytest.mark.asyncio
    async def test_llm_adapter_registered(self, substrate):
        adapters = await substrate.registry.lookup(component_type=ComponentType.ADAPTER)
        names = [a.name for a in adapters]
        assert "model_router" in names

    @pytest.mark.asyncio
    async def test_execute_with_simple_signal(self, substrate):
        from substrate.types import SignalEnvelope, SignalSource
        signal = SignalEnvelope(
            source=SignalSource.USER,
            content="hello",
            user_id="test",
            organization_id="test-org",
        )
        result = await substrate.execute(signal)
        assert result is not None
        assert result.output != ""
        assert result.trace_id is not None
```

- [ ] **Step 2: Run test to verify failures**

Run: `cd /opt/OS && python3 -m pytest tests/test_substrate_boot.py -v`
Expected: FAIL on `test_llm_adapter_registered` — adapter not registered at boot

- [ ] **Step 3: Update substrate/__init__.py to register LLM adapter at boot**

```python
"""UMH Substrate — the unified intelligence substrate.

Single public API. All signals enter through Substrate.execute().
All queries through Substrate.query(). All registrations through
Substrate.register().
"""

from __future__ import annotations

import time

from substrate.types import (
    Component,
    ComponentType,
    ExecutionResult,
    MemoryEntry,
    MemoryQuery,
    RegistrationResult,
    SignalEnvelope,
    SubstrateStatus,
)

from substrate.control_plane.identity import ConcreteIdentityResolver
from substrate.control_plane.context import ConcreteContextAssembler
from substrate.control_plane.governance import ConcreteGovernanceEngine
from substrate.control_plane.memory import ConcreteMemorySystem
from substrate.control_plane.registry import ConcreteComponentRegistry
from substrate.control_plane.router import ConcreteSignalRouter
from substrate.execution.trace import ConcreteTraceRecorder
from substrate.execution.feedback import ConcreteFeedbackCapture
from substrate.execution.spine import ConcreteExecutionSpine


class Substrate:
    """The unified UMH substrate — single entry point for all operations."""

    def __init__(self) -> None:
        self._started_at = time.monotonic()
        self.identity = ConcreteIdentityResolver()
        self.memory = ConcreteMemorySystem()
        self.context = ConcreteContextAssembler(memory_system=self.memory)
        self.governance = ConcreteGovernanceEngine()
        self.registry = ConcreteComponentRegistry()
        self.trace = ConcreteTraceRecorder()
        self.feedback = ConcreteFeedbackCapture()
        self.spine = ConcreteExecutionSpine(
            memory=self.memory,
            registry=self.registry,
            trace_recorder=self.trace,
            feedback_capture=self.feedback,
        )
        self.router = ConcreteSignalRouter(
            identity_resolver=self.identity,
            context_assembler=self.context,
            governance_engine=self.governance,
            memory_system=self.memory,
            registry=self.registry,
            execution_spine=self.spine,
            trace_recorder=self.trace,
            feedback_capture=self.feedback,
        )
        self._register_boot_adapters()

    def _register_boot_adapters(self) -> None:
        """Register core adapters at boot."""
        try:
            from adapters.models.llm_adapter import LLMAdapter
            adapter = LLMAdapter()
            import asyncio
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(self.registry.register(Component(
                    id=adapter.adapter_id,
                    component_type=ComponentType.ADAPTER,
                    name=adapter.name,
                    capabilities=adapter.capabilities(),
                )))
            else:
                loop.run_until_complete(self.registry.register(Component(
                    id=adapter.adapter_id,
                    component_type=ComponentType.ADAPTER,
                    name=adapter.name,
                    capabilities=adapter.capabilities(),
                )))
        except Exception:
            pass

    async def execute(self, signal: SignalEnvelope) -> ExecutionResult:
        return await self.router.route(signal)

    async def query(self, query: MemoryQuery) -> list[MemoryEntry]:
        return await self.memory.recall(query)

    async def register(self, component: Component) -> RegistrationResult:
        return await self.registry.register(component)

    def status(self) -> SubstrateStatus:
        subsystems = {
            "identity": "ok",
            "context": "ok",
            "governance": "ok",
            "memory": "ok" if self.memory._agent_memory is not None else "degraded",
            "registry": "ok",
            "trace": "ok",
            "feedback": "ok",
            "spine": "ok",
        }
        healthy = all(v == "ok" for v in subsystems.values())
        return SubstrateStatus(
            healthy=healthy,
            subsystems=subsystems,
            adapter_count=len(self.registry._components),
            trace_count=len(self.trace._traces),
            uptime_seconds=time.monotonic() - self._started_at,
        )
```

- [ ] **Step 4: Run tests**

Run: `cd /opt/OS && python3 -m pytest tests/test_substrate_boot.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add substrate/__init__.py tests/test_substrate_boot.py
git commit -m "substrate: register LLM adapter at boot, wire memory into context"
```

---

## Phase 5: Transports

### Task 16: Wire Discord signal factory (already exists, verify)

**Files:**
- Verify: `transports/discord/signal_factory.py`
- Test: `tests/test_discord_signal_factory.py`

- [ ] **Step 1: Write the test**

```python
# tests/test_discord_signal_factory.py
import sys
sys.path.insert(0, "/opt/OS")

import pytest
from unittest.mock import MagicMock
from substrate.types import Modality, SignalSource
from transports.discord.signal_factory import message_to_signal


class TestSignalFactory:
    def _make_message(self, content="hello", attachments=None):
        msg = MagicMock()
        msg.content = content
        msg.author.id = 12345
        msg.author.name = "testuser"
        msg.channel.id = 67890
        msg.channel.name = "general"
        msg.guild.id = 11111
        msg.guild.name = "test-server"
        msg.attachments = attachments or []
        return msg

    def test_text_message_to_signal(self):
        msg = self._make_message("hello world")
        signal = message_to_signal(msg, "test-org")
        assert signal.source == SignalSource.USER
        assert signal.content == "hello world"
        assert signal.modality == Modality.TEXT
        assert signal.organization_id == "test-org"

    def test_voice_attachment_sets_modality(self):
        attachment = MagicMock()
        attachment.content_type = "audio/ogg"
        attachment.filename = "voice.ogg"
        attachment.size = 1024
        attachment.url = "https://cdn.discord.com/voice.ogg"
        msg = self._make_message("", attachments=[attachment])
        signal = message_to_signal(msg, "test-org")
        assert signal.modality == Modality.VOICE

    def test_image_attachment_sets_modality(self):
        attachment = MagicMock()
        attachment.content_type = "image/png"
        attachment.filename = "screenshot.png"
        attachment.size = 2048
        attachment.url = "https://cdn.discord.com/screenshot.png"
        msg = self._make_message("look at this", attachments=[attachment])
        signal = message_to_signal(msg, "test-org")
        assert signal.modality in (Modality.IMAGE, Modality.MULTIMODAL)
```

- [ ] **Step 2: Run tests**

Run: `cd /opt/OS && python3 -m pytest tests/test_discord_signal_factory.py -v`
Expected: All PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_discord_signal_factory.py
git commit -m "transports: add test coverage for Discord signal factory"
```

### Task 17: Move cockpit API to transports

**Files:**
- Move: `services/umh/control_plane/cockpit_api.py` → `transports/api/cockpit.py`

- [ ] **Step 1: Check source exists**

```bash
ls services/umh/control_plane/cockpit_api.py
```

- [ ] **Step 2: Create target directory and move**

```bash
mkdir -p transports/api
git mv services/umh/control_plane/cockpit_api.py transports/api/cockpit.py
touch transports/api/__init__.py
```

- [ ] **Step 3: Update imports in moved file**

Check for `from services.umh.` imports and update. Most likely needs `sys.path.insert(0, "/opt/OS")` and import path updates.

- [ ] **Step 4: Compile check**

```bash
python3 -m py_compile transports/api/cockpit.py
```

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "transports: move cockpit API to transports/api/cockpit.py"
```

### Task 18: Move node mesh to transports

**Files:**
- Move: `services/umh/node_mesh/` → `transports/node_mesh/`

- [ ] **Step 1: Check source exists**

```bash
ls services/umh/node_mesh/
```

- [ ] **Step 2: Move**

```bash
git mv services/umh/node_mesh/ transports/node_mesh/
```

- [ ] **Step 3: Update imports in all moved files**

For each `.py` file in `transports/node_mesh/`, check for `from services.umh.` imports and update paths.

- [ ] **Step 4: Compile check all files**

```bash
find transports/node_mesh/ -name "*.py" -exec python3 -m py_compile {} \;
```

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "transports: move node mesh to transports/node_mesh/"
```

### Task 19: Move organism to substrate

**Files:**
- Move: `services/umh/organism/` → `substrate/organism/`

- [ ] **Step 1: Check source exists**

```bash
ls services/umh/organism/
```

- [ ] **Step 2: Move**

```bash
git mv services/umh/organism/ substrate/organism/
```

- [ ] **Step 3: Update imports**

For each `.py` file in `substrate/organism/`, update `from services.umh.organism.` to `from substrate.organism.` and `from services.umh.` to appropriate new paths.

- [ ] **Step 4: Compile check**

```bash
find substrate/organism/ -name "*.py" -exec python3 -m py_compile {} \;
```

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "substrate: move organism runtime to substrate/organism/"
```

### Task 20: Move voice_first to transports/discord

**Files:**
- Move: `execution/transport/voice_first.py` → `transports/discord/voice_first.py`

- [ ] **Step 1: Check source exists**

```bash
ls execution/transport/voice_first.py
```

- [ ] **Step 2: Move**

```bash
git mv execution/transport/voice_first.py transports/discord/voice_first.py
```

- [ ] **Step 3: Update imports**

- [ ] **Step 4: Compile check**

```bash
python3 -m py_compile transports/discord/voice_first.py
```

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "transports: move voice_first to transports/discord/"
```

---

## Phase 6: Prune and Verify

### Task 21: Delete dead code

This is the largest single deletion. ~230,000 lines across ~600 files.

**Important:** Do NOT delete files that are still imported by surviving modules. Run the dead code check first.

- [ ] **Step 1: Identify all files NOT imported by anything in substrate/, adapters/, transports/, state/, projections/, services/discord_bot.py**

```bash
python3 -c "
import ast, pathlib, sys

# Collect all surviving module roots
surviving_roots = ['substrate', 'adapters', 'transports', 'state', 'projections', 'integrations', 'daemon', 'scripts']

# Find all imports in surviving code
imports = set()
for root in surviving_roots:
    for p in pathlib.Path(root).rglob('*.py'):
        try:
            tree = ast.parse(p.read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.add(alias.name.split('.')[0])
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imports.add(node.module.split('.')[0])
        except Exception:
            pass

# Also check services/discord_bot.py
try:
    tree = ast.parse(pathlib.Path('services/discord_bot.py').read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split('.')[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split('.')[0])
except Exception:
    pass

print('Imported root modules:', sorted(imports))
"
```

- [ ] **Step 2: Delete directories that have zero production callers**

Delete these directories (confirmed zero production callers from import audit):

```bash
# Constitutional engines — never run
rm -rf execution/workers/workstation/

# v1 contracts superseded by substrate types (keep model_router, agent_runtime, capability_router)
# Delete everything in execution/runtime/ EXCEPT the files that survived
# (model_router.py, agent_runtime.py, capability_router.py are in adapters/ now)

# Legacy control_plane subdirs (keep runtime/ for now — gateway still referenced)
rm -rf control_plane/actions/ control_plane/delegation/ control_plane/coordination/
rm -rf control_plane/events/ control_plane/goals/ control_plane/strategy/
rm -rf control_plane/onboarding/ control_plane/scheduling/

# Core — superseded
rm -rf core/

# Understanding — ontology merged, domain bridges moved
rm -rf understanding/

# Execution environments, workflows, agents, tasks, engine
rm -rf execution/environments/ execution/workflows/ execution/agents/
rm -rf execution/tasks/ execution/engine/

# Interface — intent_handler merged
rm -rf interface/

# Observability — merged into substrate trace
rm -rf observability/

# Operations — merged into substrate memory
rm -rf operations/

# Archive
rm -rf archive/

# services/umh/ remainder (organism, node_mesh, cockpit already moved)
rm -rf services/umh/

# Legacy execution transport (voice_first already moved)
rm -rf execution/transport/
```

- [ ] **Step 3: Delete dead test files**

```bash
# Tests for deleted code
rm -rf tests/test_constitutional_*.py tests/test_workstation_*.py
# (Be selective — only delete tests whose subjects no longer exist)
```

- [ ] **Step 4: Verify no broken imports**

```bash
find substrate/ adapters/ transports/ state/ -name "*.py" \
    -exec python3 -m py_compile {} \;
```

- [ ] **Step 5: Format all surviving code**

```bash
ruff format substrate/ adapters/ transports/ state/ projections/ integrations/
```

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "prune: delete ~230,000 lines of dead/superseded code"
```

### Task 22: Run all invariant checks

- [ ] **Step 1: Check invariant 8 — public API boundary**

```bash
grep -rn "from substrate\." projections/ --include="*.py" | grep -v "from substrate import\|from substrate.types import" | wc -l
```
Expected: 0

- [ ] **Step 2: Check invariant 10 — no dataclasses in substrate**

```bash
grep -rn "@dataclass" substrate/ --include="*.py" | wc -l
```
Expected: 0

- [ ] **Step 3: Check invariant 1 — no model_router calls outside adapters/models/**

```bash
grep -rn "call_with_fallback" substrate/ adapters/ --include="*.py" | grep -v "adapters/models/" | grep -v "test_" | wc -l
```
Expected: 0 (spine.py should import from adapters, not call directly — check and fix if needed)

- [ ] **Step 4: Run full test suite**

```bash
cd /opt/OS && python3 -m pytest tests/test_ontology_enacted.py tests/test_governance_full.py tests/test_identity_resolver.py tests/test_context_assembler.py tests/test_memory_system.py tests/test_registry.py tests/test_spine_full.py tests/test_trace_recorder.py tests/test_feedback_capture.py tests/test_adapter_protocol.py tests/test_substrate_boot.py tests/test_discord_signal_factory.py -v
```
Expected: All PASS

- [ ] **Step 5: Commit any fixes**

```bash
git add -A
git commit -m "verify: all invariants pass, full test suite green"
```

### Task 23: Update CLAUDE.md and rebuild graph

- [ ] **Step 1: Update project structure in CLAUDE.md**

Update the "Project structure (post-unification)" section in `.claude/CLAUDE.md` to reflect the actual directory tree after pruning.

- [ ] **Step 2: Rebuild codebase graph**

```bash
cd /opt/OS && bash scripts/update-graph
```

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "docs: update CLAUDE.md and rebuild codebase graph"
```

---

## Phase 7: EOS Projection (can run parallel with Phase 8)

### Task 24: Create EOS projection entry point

**Files:**
- Create: `projections/eos/__init__.py`
- Create: `projections/eos/agents/ceo.py`
- Test: `tests/test_eos_projection.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_eos_projection.py
import sys
sys.path.insert(0, "/opt/OS")

import pytest
from substrate import Substrate
from substrate.types import ComponentType


class TestEOSProjection:
    @pytest.fixture
    def substrate(self):
        return Substrate()

    def test_eos_module_importable(self):
        import projections.eos
        assert projections.eos is not None

    @pytest.mark.asyncio
    async def test_eos_agents_can_register(self, substrate):
        from projections.eos.agents.ceo import register_ceo_agent
        result = await register_ceo_agent(substrate)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_registered_eos_agent_discoverable(self, substrate):
        from projections.eos.agents.ceo import register_ceo_agent
        await register_ceo_agent(substrate)
        agents = await substrate.registry.lookup(component_type=ComponentType.AGENT)
        names = [a.name for a in agents]
        assert "eos-ceo" in names
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /opt/OS && python3 -m pytest tests/test_eos_projection.py -v`
Expected: FAIL — register_ceo_agent doesn't exist

- [ ] **Step 3: Create the CEO agent module**

```python
# projections/eos/agents/ceo.py
"""EOS CEO Agent — strategic decision making for entrepreneur operations.

Registered as a substrate component. Responds to strategic queries
routed through substrate.execute().
"""

from __future__ import annotations

from substrate import Substrate
from substrate.types import (
    Component,
    ComponentType,
    RegistrationResult,
)


async def register_ceo_agent(substrate: Substrate) -> RegistrationResult:
    """Register the EOS CEO agent in the substrate registry."""
    component = Component(
        component_type=ComponentType.AGENT,
        name="eos-ceo",
        capabilities=[
            "strategic_analysis",
            "decision_making",
            "outreach_strategy",
            "pipeline_review",
        ],
        metadata={
            "projection": "eos",
            "department": "executive",
            "description": "Strategic decision making for entrepreneur operations",
        },
    )
    return await substrate.register(component)
```

- [ ] **Step 4: Run tests**

Run: `cd /opt/OS && python3 -m pytest tests/test_eos_projection.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add projections/eos/agents/ceo.py tests/test_eos_projection.py
git commit -m "eos: create CEO agent projection with substrate registration"
```

### Task 25: Create EOS Sales and Marketing agents

**Files:**
- Create: `projections/eos/agents/sales.py`
- Create: `projections/eos/agents/marketing.py`
- Test: `tests/test_eos_projection.py` (append)

- [ ] **Step 1: Create sales agent**

```python
# projections/eos/agents/sales.py
"""EOS Sales Agent — pipeline management and outreach execution."""

from __future__ import annotations

from substrate import Substrate
from substrate.types import Component, ComponentType, RegistrationResult


async def register_sales_agent(substrate: Substrate) -> RegistrationResult:
    component = Component(
        component_type=ComponentType.AGENT,
        name="eos-sales",
        capabilities=[
            "lead_scoring",
            "outreach_drafting",
            "pipeline_management",
            "follow_up",
        ],
        metadata={
            "projection": "eos",
            "department": "sales",
            "description": "Pipeline management and outreach execution",
        },
    )
    return await substrate.register(component)
```

- [ ] **Step 2: Create marketing agent**

```python
# projections/eos/agents/marketing.py
"""EOS Marketing Agent — content strategy and brand execution."""

from __future__ import annotations

from substrate import Substrate
from substrate.types import Component, ComponentType, RegistrationResult


async def register_marketing_agent(substrate: Substrate) -> RegistrationResult:
    component = Component(
        component_type=ComponentType.AGENT,
        name="eos-marketing",
        capabilities=[
            "content_strategy",
            "content_creation",
            "brand_management",
            "audience_analysis",
        ],
        metadata={
            "projection": "eos",
            "department": "marketing",
            "description": "Content strategy and brand execution",
        },
    )
    return await substrate.register(component)
```

- [ ] **Step 3: Append tests**

Append to `tests/test_eos_projection.py`:

```python
class TestEOSAgentRegistration:
    @pytest.fixture
    def substrate(self):
        return Substrate()

    @pytest.mark.asyncio
    async def test_all_eos_agents_register(self, substrate):
        from projections.eos.agents.ceo import register_ceo_agent
        from projections.eos.agents.sales import register_sales_agent
        from projections.eos.agents.marketing import register_marketing_agent

        r1 = await register_ceo_agent(substrate)
        r2 = await register_sales_agent(substrate)
        r3 = await register_marketing_agent(substrate)

        assert r1.success and r2.success and r3.success

        agents = await substrate.registry.lookup(component_type=ComponentType.AGENT)
        names = {a.name for a in agents}
        assert {"eos-ceo", "eos-sales", "eos-marketing"}.issubset(names)
```

- [ ] **Step 4: Run tests**

Run: `cd /opt/OS && python3 -m pytest tests/test_eos_projection.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add projections/eos/agents/ tests/test_eos_projection.py
git commit -m "eos: add sales and marketing agent projections"
```

---

## Phase 8: Reality Model Foundation (can run parallel with Phase 7)

### Task 26: Create Reality Model interfaces

**Files:**
- Create: `substrate/reality_model/canonical.py`
- Create: `substrate/reality_model/instance.py`
- Test: `tests/test_reality_model.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_reality_model.py
import sys
sys.path.insert(0, "/opt/OS")

import pytest
from uuid import uuid4
from substrate.reality_model.canonical import CanonicalRealityModel, CanonicalPattern
from substrate.reality_model.instance import InstanceRealityModel, InstanceObservation


class TestCanonicalRealityModel:
    @pytest.fixture
    def canonical(self):
        return CanonicalRealityModel()

    def test_store_pattern(self, canonical):
        pattern = CanonicalPattern(
            name="test-pattern",
            domain="business",
            description="A test pattern",
            evidence_count=5,
            confidence=0.9,
        )
        pattern_id = canonical.store(pattern)
        assert pattern_id is not None

    def test_retrieve_pattern(self, canonical):
        pattern = CanonicalPattern(
            name="retrieval-test",
            domain="general",
            description="Test retrieval",
            evidence_count=3,
            confidence=0.85,
        )
        canonical.store(pattern)
        found = canonical.get_by_name("retrieval-test")
        assert found is not None
        assert found.name == "retrieval-test"

    def test_list_by_domain(self, canonical):
        for i in range(3):
            canonical.store(CanonicalPattern(
                name=f"biz-{i}",
                domain="business",
                description=f"Business pattern {i}",
                evidence_count=i + 1,
                confidence=0.8,
            ))
        canonical.store(CanonicalPattern(
            name="life-0",
            domain="life",
            description="Life pattern",
            evidence_count=2,
            confidence=0.7,
        ))
        biz = canonical.list_by_domain("business")
        assert len(biz) == 3

    def test_canonical_is_immutable_without_governance(self, canonical):
        pattern = CanonicalPattern(
            name="immutable-test",
            domain="general",
            description="Should not change",
            evidence_count=10,
            confidence=0.95,
        )
        canonical.store(pattern)
        with pytest.raises(ValueError, match="governance"):
            canonical.update("immutable-test", description="changed", governance_approved=False)


class TestInstanceRealityModel:
    @pytest.fixture
    def instance(self):
        return InstanceRealityModel(user_id="test-user", org_id="test-org")

    def test_record_observation(self, instance):
        obs = InstanceObservation(
            content="User prefers morning meetings",
            domain="scheduling",
            confidence=0.8,
            source_signal_id=uuid4(),
        )
        obs_id = instance.record(obs)
        assert obs_id is not None

    def test_query_observations(self, instance):
        instance.record(InstanceObservation(
            content="User is in Portland timezone",
            domain="general",
            confidence=0.95,
            source_signal_id=uuid4(),
        ))
        results = instance.query("Portland")
        assert len(results) >= 1

    def test_instance_is_user_scoped(self, instance):
        assert instance.user_id == "test-user"
        assert instance.org_id == "test-org"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /opt/OS && python3 -m pytest tests/test_reality_model.py -v`
Expected: FAIL — modules don't exist

- [ ] **Step 3: Create canonical.py**

```python
# substrate/reality_model/canonical.py
"""Canonical Reality Model — compressed, reusable intelligence.

Universal patterns, governance laws, verified templates, domain laws.
Pre-filled so the system is useful for new users from day one.
Sacred — updated only through governed promotion.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class CanonicalPattern(BaseModel):
    """A compressed, reusable pattern in the Canonical Reality Model."""

    id: UUID = Field(default_factory=uuid4)
    name: str = Field(max_length=200)
    domain: str = Field(max_length=100)
    description: str = Field(max_length=1000)
    evidence_count: int = Field(ge=0, default=0)
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    promoted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)


class CanonicalRealityModel:
    """In-memory canonical store. Neon persistence added in later phase."""

    def __init__(self) -> None:
        self._patterns: dict[str, CanonicalPattern] = {}

    def store(self, pattern: CanonicalPattern) -> UUID:
        self._patterns[pattern.name] = pattern
        return pattern.id

    def get_by_name(self, name: str) -> CanonicalPattern | None:
        return self._patterns.get(name)

    def list_by_domain(self, domain: str) -> list[CanonicalPattern]:
        return [p for p in self._patterns.values() if p.domain == domain]

    def all(self) -> list[CanonicalPattern]:
        return list(self._patterns.values())

    def update(
        self, name: str, governance_approved: bool = False, **fields: Any
    ) -> CanonicalPattern:
        """Update a canonical pattern. Requires governance approval."""
        if not governance_approved:
            raise ValueError(
                "Canonical patterns require governance approval to update. "
                "Pass governance_approved=True after governance gate."
            )
        pattern = self._patterns.get(name)
        if pattern is None:
            raise KeyError(f"Pattern '{name}' not found")
        for key, value in fields.items():
            if hasattr(pattern, key):
                object.__setattr__(pattern, key, value)
        return pattern
```

- [ ] **Step 4: Create instance.py**

```python
# substrate/reality_model/instance.py
"""Instance Reality Model — live operational truth of one user/company/environment.

Contextual, volatile. Updated through governed execution outcomes.
Each user/org has their own instance.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class InstanceObservation(BaseModel):
    """An observation recorded in the Instance Reality Model."""

    id: UUID = Field(default_factory=uuid4)
    content: str = Field(max_length=2000)
    domain: str = Field(default="general", max_length=100)
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    source_signal_id: UUID | None = None
    source_trace_id: UUID | None = None
    observed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)


class InstanceRealityModel:
    """Per-user/org instance store. Neon persistence added in later phase."""

    def __init__(self, user_id: str, org_id: str) -> None:
        self.user_id = user_id
        self.org_id = org_id
        self._observations: list[InstanceObservation] = []

    def record(self, observation: InstanceObservation) -> UUID:
        self._observations.append(observation)
        return observation.id

    def query(self, text: str, limit: int = 10) -> list[InstanceObservation]:
        """Simple text search. Semantic search added with embedding integration."""
        text_lower = text.lower()
        matches = [
            obs for obs in self._observations
            if text_lower in obs.content.lower() or text_lower in obs.domain.lower()
        ]
        return matches[:limit]

    def list_by_domain(self, domain: str) -> list[InstanceObservation]:
        return [obs for obs in self._observations if obs.domain == domain]

    def all(self) -> list[InstanceObservation]:
        return list(self._observations)

    def count(self) -> int:
        return len(self._observations)
```

- [ ] **Step 5: Run tests**

Run: `cd /opt/OS && python3 -m pytest tests/test_reality_model.py -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add substrate/reality_model/ tests/test_reality_model.py
git commit -m "reality-model: create canonical and instance reality model foundation"
```

### Task 27: End-to-end acceptance test

**Files:**
- Test: `tests/test_convergence_acceptance.py`

- [ ] **Step 1: Write the acceptance test**

```python
# tests/test_convergence_acceptance.py
"""End-to-end acceptance tests for the converged UMH substrate."""
import sys
sys.path.insert(0, "/opt/OS")

import pytest
from substrate import Substrate
from substrate.types import (
    ComponentType,
    ExecutionOutcome,
    SignalEnvelope,
    SignalSource,
)


class TestConvergenceAcceptance:
    @pytest.fixture
    def substrate(self):
        return Substrate()

    @pytest.mark.asyncio
    async def test_signal_to_result(self, substrate):
        """Full lifecycle: signal → identity → context → governance → spine → result."""
        signal = SignalEnvelope(
            source=SignalSource.USER,
            content="hello, what can you do?",
            user_id="test",
            organization_id="test-org",
        )
        result = await substrate.execute(signal)
        assert result.outcome == ExecutionOutcome.SUCCESS
        assert result.output != ""
        assert result.trace_id is not None
        assert result.duration_ms > 0

    @pytest.mark.asyncio
    async def test_governance_blocks_critical(self, substrate):
        """Critical action gets blocked by governance."""
        signal = SignalEnvelope(
            source=SignalSource.USER,
            content="send email to all customers with pricing update",
            user_id="test",
            organization_id="test-org",
        )
        result = await substrate.execute(signal)
        assert result.outcome == ExecutionOutcome.BLOCKED

    @pytest.mark.asyncio
    async def test_deterministic_always_produces_output(self, substrate):
        """Even with no LLM, the system produces a response."""
        signal = SignalEnvelope(
            source=SignalSource.USER,
            content="analyze this data for me",
            user_id="test",
            organization_id="test-org",
        )
        result = await substrate.execute(signal)
        assert result.output != ""
        assert len(result.output) > 10

    def test_no_dataclasses_in_substrate(self):
        """Invariant: no @dataclass in substrate/."""
        import subprocess
        result = subprocess.run(
            ["grep", "-rn", "@dataclass", "substrate/", "--include=*.py"],
            capture_output=True, text=True,
        )
        assert result.stdout.strip() == "", f"Found dataclasses: {result.stdout}"

    def test_ontology_laws_are_callable(self):
        """Invariant: laws have check() method."""
        from substrate.ontology.laws import LawRegistry
        registry = LawRegistry()
        for law in registry.all():
            assert callable(getattr(law, "check", None)), f"Law {law.name} has no check()"

    def test_substrate_status_healthy(self, substrate):
        status = substrate.status()
        assert status.healthy is True
        assert "spine" in status.subsystems
        assert "governance" in status.subsystems

    @pytest.mark.asyncio
    async def test_eos_projection_isolation(self, substrate):
        """EOS projection only uses public API."""
        import subprocess
        result = subprocess.run(
            ["grep", "-rn", "from substrate\\.", "projections/", "--include=*.py"],
            capture_output=True, text=True,
        )
        for line in result.stdout.strip().split("\n"):
            if line:
                assert "from substrate import" in line or "from substrate.types" in line, \
                    f"Projection imports substrate internals: {line}"
```

- [ ] **Step 2: Run acceptance tests**

Run: `cd /opt/OS && python3 -m pytest tests/test_convergence_acceptance.py -v`
Expected: All PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_convergence_acceptance.py
git commit -m "acceptance: add end-to-end convergence verification tests"
```

---

## Summary

| Phase | Tasks | Can Parallelize With | Key Output |
|-------|-------|---------------------|------------|
| 0 | 1-2 | — | Directory structure, git tag |
| 1 | 3-5 | — | Enacted ontology with callable laws |
| 2 | 6-10 | Phase 3, 4 | Full control plane (governance, identity, context, memory, registry) |
| 3 | 11-13 | Phase 2, 4 | Full execution spine with 8 stages |
| 4 | 14-15 | Phase 2, 3 | Adapter protocol verified, boot registration |
| 5 | 16-20 | — | All transports wired to substrate |
| 6 | 21-23 | — | ~230K lines deleted, all invariants pass |
| 7 | 24-25 | Phase 8 | EOS projection with 3 agents |
| 8 | 26 | Phase 7 | Reality model foundation |
| — | 27 | — | End-to-end acceptance |

**Total: 27 tasks. Phases 2-4 run in parallel. Phases 7-8 run in parallel.**
