# UMH Roadmap from Reality

**Generated**: 2026-05-27 from coherence convergence audit
**Source of truth**: Actual codebase state, not aspirational docs

---

## Current State (observed)

- **Production path works**: Discord → discord_bot.py → gateway.py → cognitive_loop.py → agent_runtime.py → model_router.py → LLM chain → response
- **Substrate layer exists**: types.py (30+ Pydantic models), spine.py (8-stage pipeline), governance, memory, router — all import clean
- **5 parallel execution paths**: Only Path A (gateway) is production-hot. Paths B-E exist but aren't wired to live traffic
- **11 governance systems**: ExecutionAuthorityEngine is canonical. Others are experimental/dormant
- **22 memory components**: AgentMemory + ConversationMemory are production. Others are design-phase
- **Docker orchestration works**: 4 services (os-discord, os-operator, os-webhook, os-scraper) + umh-mesh systemd

---

## P0: Blocks Production Reliability

| # | Task | Why | Files |
|---|------|-----|-------|
| 1 | Create `runtime_execution_result_v1.py` | Blocks substrate_command_handler import chain | `substrate/execution/runtime/` |
| 2 | Fix test_tier_propagates_through_pipeline | Patches wrong module path, only pre-existing test failure | `tests/test_authority_tier.py` |

---

## P1: Execution Path Convergence

**Goal**: All traffic flows through SignalEnvelope → ConcreteExecutionSpine → governed execution

| # | Task | Dependencies |
|---|------|-------------|
| 3 | Wire gateway.py to create SignalEnvelope on inbound | None |
| 4 | Route SignalEnvelope through ConcreteSignalRouter | #3 |
| 5 | Execute via ConcreteExecutionSpine 8-stage pipeline | #4 |
| 6 | Retire cognitive_loop.py direct LLM calls | #5 verified |
| 7 | Create ConcreteActuator for final execution stage | #5 |

**Validation**: Discord bot processes a message through full spine pipeline end-to-end.

---

## P2: Governance Kernel

**Goal**: Single GovernanceKernel replaces 11 scattered governance systems

| # | Task | Dependencies |
|---|------|-------------|
| 8 | Build GovernanceKernel with 4-tier permission model | P1 complete |
| 9 | Migrate ExecutionAuthorityEngine into kernel | #8 |
| 10 | Wire risk classification into kernel | #8 |
| 11 | Add governance audit trail to Neon | #9 |

**Design**: `docs/system/governance_kernel_design.md`

---

## P3: Memory Kernel

**Goal**: Unified memory system with 10 strata

| # | Task | Dependencies |
|---|------|-------------|
| 12 | Build MemoryKernel interface | P1 complete |
| 13 | Integrate AgentMemory + ConversationMemory | #12 |
| 14 | Add semantic memory layer | #12 |
| 15 | Wire memory queries into spine pipeline | #13 |

**Design**: `docs/system/memory_kernel_design.md`

---

## P4: Quality Hardening

| # | Task | Dependencies |
|---|------|-------------|
| 16 | Fix ~592 silent except-pass blocks | None (ongoing) |
| 17 | Add structured logging to governance decisions | P2 |
| 18 | Health check endpoints for all services | None |
| 19 | Integration test suite for full spine pipeline | P1 |

---

## P5: Scale Preparation

| # | Task | Dependencies |
|---|------|-------------|
| 20 | Multi-org RLS validation suite | None |
| 21 | Windows Beast distributed execution | P1 |
| 22 | EntrepreneurOS projection hardening | P1 + P2 |

---

## Architecture Reference

```
Production path (current):
  Discord → services/discord_bot.py
    → substrate/control_plane/runtime/gateway.py
    → substrate/control_plane/runtime/cognitive_loop.py
    → adapters/models/agent_runtime.py
    → adapters/models/model_router.py (call_with_fallback)
    → LLM chain: cc_sdk → Gemini → Groq → Ollama

Target path (post-P1):
  Transport → SignalEnvelope
    → ConcreteSignalRouter.route()
    → ConcreteExecutionSpine.execute() [8 stages]
    → GovernanceKernel.authorize()
    → ConcreteActuator.actuate()
    → FeedbackCapture.capture()

Dependency direction (enforced):
  projections → transports → adapters → substrate
  substrate is innermost — never reaches outward
```
