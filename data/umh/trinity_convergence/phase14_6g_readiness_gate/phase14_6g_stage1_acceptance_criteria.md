---
phase: "14.6G"
status: "DRAFT"
operator_approved: false
allows_implementation: false
date: "2026-06-04"
provenance: "READINESS_GATE"
sources:
  - "DEC-146C-003 -- Indivisible Stage 1 Organism (Option B, RATIFIED)"
  - "umh_cockpit_jarvis_doctrine.md -- 10 acceptance criteria"
  - "umh_execution_boundary_model.md -- governance model"
  - "Codebase survey of existing infrastructure"
---

# Phase 14.6G: Stage 1 Acceptance Criteria

## What This Is

Testable acceptance criteria for UMH Stage 1 minimum viability. These are derived from the 10 operator-specified criteria in DEC-146C-003 and expanded into verifiable test conditions.

## The 10 Acceptance Criteria (Testable)

### AC-1: Cockpit as Primary Interface

**Canon source:** "Operator can use Cockpit/Jarvis as primary interface"

| Test | Condition | Verification |
|------|-----------|--------------|
| AC-1.1 | Cockpit loads at the designated URL without errors | HTTP 200 from Cockpit route, no console errors |
| AC-1.2 | Cockpit renders at least: WorldModel, Approvals, Execution, Memory, Self-Build panels | DOM check for 5 required panel components |
| AC-1.3 | Cockpit degrades gracefully when backend is unreachable | Shows "backend unreachable" state, not blank/spinner |
| AC-1.4 | Voice and text input channels both accept commands | Text input submits; voice capture triggers transcription pipeline |

### AC-2: Intent Capture and Memory Persistence

**Canon source:** "UMH can capture intent and preserve it in memory/source truth"

| Test | Condition | Verification |
|------|-----------|--------------|
| AC-2.1 | Operator text input is persisted to ConversationMemory | Query Neon `umh_conversations` table after input; row exists |
| AC-2.2 | Intent classification produces a typed intent | Spine stage 1 (Interpret) returns non-null intent type |
| AC-2.3 | Persisted intent survives session restart | Kill Cockpit, restart, query memory; intent still present |
| AC-2.4 | Memory semantic search retrieves persisted intent | `semantic_search()` with intent keywords returns the stored entry |

### AC-3: Usable Reality Model

**Canon source:** "UMH can maintain a usable reality model (work, products, companies, files, artifacts, agents, blockers)"

| Test | Condition | Verification |
|------|-----------|--------------|
| AC-3.1 | CanonicalRealityModel loads from persistence | `canonical.load()` returns model with >0 observations |
| AC-3.2 | InstanceRealityModel loads from persistence | `instance.load()` returns model with >0 observations |
| AC-3.3 | Cockpit WorldModelPanel displays observations from reality model | API GET `/api/umh/reality-model/canonical` returns observations; panel renders them |
| AC-3.4 | Reality model covers at minimum: ventures, agents, files, blockers | Query model for each entity type; all return results |
| AC-3.5 | Observations have confidence scores that decay over time | Observation loaded >1 day old has lower confidence than fresh observation |

### AC-4: Work Packet Generation from Intent

**Canon source:** "UMH can generate work packets from operator intent"

| Test | Condition | Verification |
|------|-----------|--------------|
| AC-4.1 | High-level operator intent produces at least one work packet | Submit intent through Cockpit; WorkPacket created with objective, risk_level, acceptance_criteria |
| AC-4.2 | Work packets have required fields | Each packet has: objective, affected_files, acceptance_criteria, risk_level, approval_requirement |
| AC-4.3 | Work packets are persisted | `load_packets()` returns previously created packets |
| AC-4.4 | Work packets are visible in Cockpit | GET `/api/umh/work-packets` returns packet list; Cockpit panel renders them |
| AC-4.5 | Complex intent decomposes into multiple linked packets | Submit multi-step intent; result is >1 packet with dependency_links |

### AC-5: Work Routing to Agents/Tools

**Canon source:** "UMH can route work packets to agents/tools"

| Test | Condition | Verification |
|------|-----------|--------------|
| AC-5.1 | Work packet with code task routes to Claude Code | Packet with `affected_files: [*.py]` routes to CC SDK capability |
| AC-5.2 | Work packet with shell task routes to shell executor | Packet with shell command routes to subprocess capability |
| AC-5.3 | Work packet with GitHub task routes to GitHub adapter | Packet referencing PR/issue routes to GitHub capability |
| AC-5.4 | Work packet with doc task routes to documentation capability | Packet referencing .md files routes to doc capability |
| AC-5.5 | Routing uses call_with_fallback for LLM-enhanced routing | Model router fallback chain activates when primary provider unavailable |

### AC-6: Governed Execution Approval Gates

**Canon source:** "UMH can govern risky actions through approval gates" (governed execution component)

| Test | Condition | Verification |
|------|-----------|--------------|
| AC-6.1 | READ_ONLY actions execute without approval | Risk classification returns NEGLIGIBLE; no approval prompt |
| AC-6.2 | SAFE_WRITE actions execute without approval | Risk classification returns LOW; no approval prompt |
| AC-6.3 | IRREVERSIBLE_WRITE actions require operator approval | Risk classification returns HIGH; approval request appears in Cockpit |
| AC-6.4 | FINANCIAL/SECURITY actions require operator approval | Risk classification returns CRITICAL; approval request appears in Cockpit |
| AC-6.5 | Operator can approve/deny through Cockpit Approvals panel | Click approve → action executes; click deny → action blocked |
| AC-6.6 | Denied actions do not execute | Deny approval; verify no mutation occurred |
| AC-6.7 | FORBIDDEN actions are always blocked | Submit FORBIDDEN-class action; verify immediate rejection without approval prompt |

### AC-7: Output Verification

**Canon source:** "UMH can verify outputs (tests, audit reports, diffs, review packets)"

| Test | Condition | Verification |
|------|-----------|--------------|
| AC-7.1 | Completed work packet triggers verification step | After execution, verification function runs and produces result |
| AC-7.2 | Code changes trigger diff generation | Work packet that modifies .py produces git diff |
| AC-7.3 | Test-related changes trigger test run | Work packet modifying test file triggers pytest |
| AC-7.4 | Verification result is persisted with work packet | Query work packet after verification; result attached |
| AC-7.5 | Failed verification blocks packet completion | Verification failure → packet status remains PENDING, not COMPLETE |

### AC-8: Reality Model Update After Outcomes

**Canon source:** "UMH can update memory/reality model after outcomes"

| Test | Condition | Verification |
|------|-----------|--------------|
| AC-8.1 | Successful work packet outcome updates reality model | Complete a packet; query reality model; new observation exists reflecting outcome |
| AC-8.2 | Failed work packet outcome updates reality model with failure | Fail a packet; query reality model; failure observation exists |
| AC-8.3 | Reality model update is governance-gated | Canonical reality model mutation requires HIGH risk approval |
| AC-8.4 | Instance reality model updates freely from outcomes | Instance model update after outcome does not require approval |
| AC-8.5 | Updated reality model is visible in Cockpit | After update, WorldModelPanel shows new observation |

### AC-9: Governed Self-Improvement

**Canon source:** "UMH can work on itself through governed self-improvement work packets"

| Test | Condition | Verification |
|------|-----------|--------------|
| AC-9.1 | AutonomousCadence discovers improvement candidates | `run_cycle()` returns >0 candidates from template registry |
| AC-9.2 | Candidates are filtered by risk level | Only LOW risk candidates pass cadence filter |
| AC-9.3 | Self-improvement packets require operator approval | Generated self-improvement packet has `approval_requirement: true` |
| AC-9.4 | Dry-run mode produces proposals without executing | `dry_run_only=True` generates proposal; no code mutation occurs |
| AC-9.5 | Approved self-improvement executes through governed spine | After approval, packet routes through ExecutionSpine with full governance |

### AC-10: Build Projections from Inside UMH

**Canon source:** "UMH can build and improve projection apps from inside the UMH operating loop"

| Test | Condition | Verification |
|------|-----------|--------------|
| AC-10.1 | Operator can submit "build EOS feature X" as intent | Intent accepted; work packets generated targeting saas/ or projections/eos/ |
| AC-10.2 | Work packets for projection code route to correct codebase | Packet with `affected_files: [saas/src/*.tsx]` routes to appropriate capability |
| AC-10.3 | Projection work packets respect architecture layer law | Generated packets do not violate dependency direction (projections → substrate, never reverse) |
| AC-10.4 | Projection work packets are governance-gated | Packets modifying projection code classified as MEDIUM+ risk; require approval |
| AC-10.5 | UMH can build CreatorOS and LyfeOS after Stage 1 | No hardcoded EOS-only logic in work packet routing; projection-agnostic |

## Summary

| Criterion | Test Count | Depends On |
|-----------|------------|------------|
| AC-1: Cockpit Interface | 4 | Wave 1 |
| AC-2: Intent + Memory | 4 | Wave 1 |
| AC-3: Reality Model | 5 | Wave 1 |
| AC-4: Work Packets | 5 | Wave 2 |
| AC-5: Agent Routing | 5 | Wave 2 |
| AC-6: Governed Approval | 7 | Wave 2 |
| AC-7: Verification | 5 | Wave 3 |
| AC-8: Reality Update | 5 | Wave 3 |
| AC-9: Self-Improvement | 5 | Wave 3 |
| AC-10: Projection Build | 5 | Wave 3 |
| **Total** | **50** | |

All 50 tests must pass before Stage 1 is declared minimum viable. Each test is independently verifiable. No test requires subjective judgment.
