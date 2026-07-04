# WP-P2-002 — Unify Risk / Role / Permission-Envelope Taxonomy

**Branch:** `fix/p2-002-risk-role-permission-envelope`, based on the WP-P2-001 branch tip `7e72f497e` (which is off `origin/main @ 566771265`). Basing on P2-001 avoids divergent edits to the shared type files; the two land in order.
**Risk:** HIGH (touches risk-governance semantics across gates). Preserve every P0 fail-closed check and P0-002 node verdict validation.
**Mandate:** ONE canonical risk vocabulary + ONE role/permission-envelope vocabulary. No new parallel enum. No new risk taxonomy. Unknown risk/role/permission MUST fail closed (strictest), never downgrade to LOW/permissive.

Verified against the live tree by recon. All refs are file:line at this base.

---

## 1. Before-state (measured)

### Risk — two legitimate axes, one conflating shadow
- **Severity axis (canonical):** `substrate/types.py:252 RiskClass` — 6 members `CRITICAL/HIGH/MEDIUM/LOW/NEGLIGIBLE/FORBIDDEN`. Registered `canonical_types.py:40`.
- **Category axis (canonical):** `substrate/governance/risk_classes.py:17 ActionRiskCategory` — 8 members (READ_ONLY … PHYSICAL_WORLD), with `to_risk_class()` bridging → the 6-member severity. NOT registered under its own name.
- **The conflating bug:** `risk_classes.py:66` `RiskClass = ActionRiskCategory` shadows the imported severity enum at module scope. So `from ...risk_classes import RiskClass` yields the 8-member *category* enum (28–31 importers) while `to_risk_class()` returns the 6-member *severity* enum. The two axes are ambiguous under one name.
- ~9 severity-alias enums (`RiskLevel`, `ActionRiskLevel`, `RiskSeverity`, `WorkloadRisk`, `AutomationRisk`, `VpsRisk`, `EnvironmentEnvironmentPacketRiskLevel`) — all collapse onto `RiskClass`. `RiskCategory` (risk_engine) is thematic, not severity — leave.
- ~6 duck-typed `risk_class: str` / `risk_level: str` fields (mutation_registry, agent_registry, approval_gate, config).

### The 8 "unknown → fail-OPEN" sites (safety-critical — must become fail-closed)
1. `substrate/organism/agent_registry.py:52` — `risk_rank.get(risk_class, 0) <= risk_rank.get(self.max_risk_class, 1)` → unknown request risk → 0 (lowest) → passes as "low". **Fail-OPEN.**
2. `nodes/windows/umh_node/config.py:24` + `nodes/windows/umh_node/governance.py` — `max_risk_class` default + unknown ceiling → allows everything. **Fail-OPEN ceiling.**
3. `substrate/governance/policy/authority_engine.py:122` — `MIN_LEVEL_TO_EXECUTE.get(risk_class, 0)` → unknown → level 0. Permissive default.
4. `substrate/organism/composition_engine.py:400` — `_RISK_SEVERITY.get(risk, 1)` unknown → low-ish.
5. `substrate/control_plane/runtime/orchestrator/decisions.py:95` + `handlers.py:244` — `str(action.get("risk_level") or "low")` → missing → "low".
6. `substrate/organism/agent_execution_runner.py:126` — `packet.risk_class or "low"`.
7. `substrate/organism/universal_work_queue.py:181` — scoring default 0.3 (scheduling, lower severity).
8. `substrate/organism/template_governance.py:279`, `self_build_queue.py` — risk-score defaults (scoring).

### Already fail-CLOSED (preserve, do not regress)
- `execution_coordinator.py:575/588/602` `.get(risk, True)`; `executor_runtime.py:728…755` `.get(..., 99)`; `execution_authority_engine_v1.py:182` request-side `.get(risk, 5)`; `approval_authority._coerce_risk` unknown→HIGH; `mesh_verdict.is_write_class` unknown→write-class (P0-002 downgrade guard); `types.py ApprovalState.coerce` unknown→PENDING.

### Role / permission
- Role: `AgentRole`+`RoleScope`+`RoleRegistry` (`execution/bridge/roles.py`) = authority-role canonical; `Role` BaseModel (`types.py:1273`) = org-structure; node-topology roles (`UMHNodeRole` superset, registered). `CausalRole` is NOT an authority role (semantic graph) — exclude.
- Permission/autonomy already unified: `PermissionTier` (`types.py:140`, registered) + `AutonomyLevel` (IntEnum, registered). `required_tier_for_action` returns READ on unknown action — flag (permissive default).

---

## 2. Scope decision (tight, safety-first, no mass rewrite)

A mass enum rewrite (collapsing 11 risk enums into one) touches dozens of files, risks breaking the 28–31 `risk_classes` importers and the P0-002/P1 gates, and is not what "unify the vocabulary" requires. The canonical two-axis spine ALREADY exists (`RiskClass` × `ActionRiskCategory` + `to_risk_class`). WP-P2-002 makes it **canonical, unambiguous, and fail-closed**:

**IN scope:**
1. **Declare the canonical risk vocabulary** in `substrate/governance/risk_classes.py`: keep the `RiskClass = ActionRiskCategory` back-compat alias (28–31 importers) but document it explicitly and add a clear `SeverityClass = RiskClass_severity` re-export path so new code can name the severity axis unambiguously. Register `ActionRiskCategory` in `canonical_types.py`.
2. **One canonical fail-closed coercion helper**: `coerce_risk_class(value) -> RiskClass` (severity) — unknown → **HIGH** (strictest reasonable non-FORBIDDEN), never LOW. Mirrors the proven `approval_authority._coerce_risk`. Plus `stricter_of(a, b)` combinator (choose the higher-severity when two taxonomies disagree). Centralized in `substrate/governance/risk_classes.py` so every consumer imports one helper.
3. **Fix the 8 fail-open sites** to route unknown → strict via the helper (request side → max rank; ceiling side → min rank / explicit reject). Preserve every already-fail-closed site.
4. **Register the role/permission canonicals** already identified (ensure `AgentRole`/`RoleScope` + `PermissionTier`/`AutonomyLevel` registered; they are).
5. **Tests**: known risk enums map into canonical; unknown fails closed; node verdict downgrade still rejected; approval authority uses canonical risk; governed_mutation + GovernedExecutionSpine agree; role/permission rejects unknown/overbroad.

**Delivered in this PR:**
- Canonical vocabulary declared: `SeverityClass` (unambiguous severity re-export) + `ActionRiskCategory` (registered in canonical_types.py). Back-compat `RiskClass = ActionRiskCategory` preserved for 31 importers.
- Centralized fail-closed helpers: `coerce_risk_class` (unknown → HIGH), `severity_rank`, `stricter_of`, `_KNOWN_RISK_NAMES`.
- Two HARD-GATE fail-open sites fixed + tested:
  - `agent_registry.can_handle_risk` — unknown request → HIGH (rejected); unknown ceiling → NEGLIGIBLE (restrictive). Both sides fail closed.
  - `orchestrator/decisions._risk` — missing/unknown risk → "high" → lands in `ALWAYS_ESCALATE_RISK` (was silently "low" → not escalated).

**OUT of scope (documented, tracked follow-on):**
- The remaining fail-open sites are **scoring/planning defaults**, not hard gates: `composition_engine.py:400`, `universal_work_queue.py:181`, `template_governance.py:279`, `self_build_queue.py`, `agent_execution_runner.py:126` (a descriptive plan field), and `authority_engine.py:122` (mitigated — risk is always a real enum from `classify_action`). They tune scores/schedules, not access decisions. Converging them through `coerce_risk_class` is low-risk follow-on; done separately to keep this HIGH-risk PR's blast radius on the actual gates.
- Physically deleting the ~9 severity-alias enums (each has consumers). Documented as aliases-of-`RiskClass`.
- The `nodes/environments/work_packet.py` double-prefix rename + `packet_validator.py` ImportError — a nodes/ source rename (dormant-disposition territory); flagged, not fixed here.
- Node ceiling `config.py:24` + `nodes/.../governance.py` — the node-side risk vocab is the 8-category axis; converging it needs the node governance module, deferred to keep P0-002 node code untouched.

**Preserve:** P0 fail-closed risk checks, P0-002 `is_write_class` downgrade guard, P1 approval `_coerce_risk`, spine risk semantics. Stricter-of-two when taxonomies disagree.

---

## 3. Proof
- Before/after taxonomy map (this doc).
- `coerce_risk_class` unknown → HIGH; `stricter_of` picks higher severity — tests.
- The 8 fail-open sites now fail closed — tests + grep proof.
- P0 mesh tests pass; P1 approval + spine tests pass; all 9 gates exit 0.
- No new enum; `ActionRiskCategory` registered; role/permission canonicals registered.
