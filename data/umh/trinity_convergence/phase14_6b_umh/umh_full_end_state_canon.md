# UMH Full End-State Canon

Phase: 14.6B-UMH (revised 14.6F)
Status: RATIFIED -- all 18 P0 decisions operator-approved (2026-06-04)
Revision note: Revised in Phase 14.6F to align with 18 ratified P0 decisions (2026-06-04).

## Vision

UMH at end-state is a private Jarvis system -- a reality-isomorphic intelligence harness (DEC-146C-001, RATIFIED 2026-06-04). Product name: "Universal Meta Harness" (DEC-146B-UMH-001, RATIFIED 2026-06-04). UMH builds, maintains, and acts through an integrated approximation of reality across 12 layers: physical, digital, cognitive, biological, social, economic, symbolic, operational, software, memory, source-truth, and OS-level reality. The reality model is the central organizing model through which UMH understands intent, state, constraints, resources, possible actions, consequences, and feedback across the founder's entire operational, creative, and personal domains.

**Materialization Principle (DEC-146C-002, RATIFIED 2026-06-04):** At end-state, UMH fully embodies the materialization principle. If a human can imagine an outcome, UMH simulates the path from imagination to materialization. Missing knowledge, resources, tools, capital, information, skill, access, or time become typed gaps and acquisition paths -- research loops, resource acquisition loops, experiment loops, work packets, delegation paths, agent paths, financing paths, and time-bound execution paths. Outcomes violating physical reality, law, safety, ethics, or non-negotiable constraints are met with the nearest lawful/safe/materializable alternative.

## Cockpit End-State

The cockpit becomes the operator's complete interface into UMH's 12-layer reality model (DEC-146C-003, RATIFIED 2026-06-04). It is part of the indivisible Stage 1 organism -- Cockpit without a reality model is only a dashboard; a reality model without Cockpit is inaccessible to the operator. It is the reality-model rendering surface through which the operator observes, commands, and governs the full UMH ecosystem. Three interaction modes:

- **Voice** -- natural language commands and ambient listening
- **Text** -- structured chat with operator/DEX dialogue
- **Visual** -- 27+ panels for real-time system state, execution traces, governance decisions

Ambient display mode shows passive system health, active executions, and incoming signals without requiring operator input. Proactive alerting surfaces anomalies, opportunities, and required decisions before the operator asks.

## Projection Maturity

All execution flows through a single unified path: Substrate -> SignalRouter -> Spine (DEC-146B-UMH-003, RATIFIED 2026-06-04). Dead workstation code (26,671 lines) is extracted for conceptual value into design docs, then deleted (DEC-146B-UMH-004, RATIFIED 2026-06-04). Projection access uses abstract port pattern via substrate/sockets/projection_port.py (DEC-146B-UMH-005, RATIFIED 2026-06-04).

Each projection matures into a governed SaaS-grade product:

| Projection | Domain | End-State |
|---|---|---|
| EntrepreneurOS (EOS) | Business | Full venture management -- clients, offers, transactions, analytics, outreach automation. Beast branch is canonical codebase (DEC-146B-EOS-001). Clerk auth (DEC-146B-EOS-003). MVP R1-R5 (DEC-146B-EOS-002). |
| CreatorOS | Creator workflow | Content + Community + Courses + Sales (DEC-146B-COS-001). Clerk auth first, blocks all else (DEC-146B-COS-002). GitHub canonical after baseline verify (DEC-146B-COS-003). |
| LyfeOS | Life management | PRD v2.0 canonical (DEC-146B-LOS-001). Clerk after CreatorOS proves pattern (DEC-146B-LOS-002). Fly.io is Trinity standard (DEC-146B-LOS-003). |

Cross-projection orchestration enables actions in one domain to trigger governed responses in others (e.g., a business win triggers content creation in CreatorOS and financial update in LyfeOS).

## Autonomous Operation

- **Overnight autonomous execution** with governed cadence running low-risk improvements
- **Morning summary** delivered at session start covering overnight actions, decisions deferred, and anomalies detected
- **Dry-run simulation** for all autonomous proposals before operator approval
- **Deliberation council** evaluates multi-perspective tradeoffs for medium+ risk decisions

## Intelligence End-State

- Multi-model routing with cost/quality optimization per task type
- Deterministic spine always functional -- AI enhances but never blocks
- Agent specialization with learned preferences per domain
- Meta-learning across projections for cross-domain pattern recognition
- Intelligence serves reality-model construction -- every LLM call either observes, updates, or reasons over the reality model (DEC-146C-001)
- 12-layer reality model progressively deepens with each interaction, ingestion, and execution outcome
- **Materialization gap typing:** Missing capability creates typed gaps (research loops, resource acquisition loops, experiment loops, work packets, delegation paths, agent paths, financing paths, time-bound execution paths) -- not terminal failure (DEC-146C-002)

## Multi-Device Coordination

| Device | Role |
|---|---|
| VPS | Coordination brain, always-on orchestration, lightweight services |
| Beast (Windows GPU) | Heavy compute, large models, media processing, full repo mirror |
| Mobile (iPhone) | Quick commands, notifications, approval flows |
| Tablet (iPad) | Full cockpit access via browser, code editing via code-server |
| Tailscale mesh | Private network binding all nodes |

## Meta-IDE Integration

End-state includes a forked VS Code IDE embedded in the cockpit, providing:

- Code editing with substrate-aware intelligence
- Governed commit flows with pre-commit gate integration
- Agent-assisted development sessions tracked as organism work units

## Computer Vision and Browser Agents

- Browser automation for web tasks (research, form filling, monitoring)
- Computer vision for screenshot analysis and UI verification
- Sandboxed execution environments for untrusted operations

## Observability

- Full distributed tracing across all execution paths
- Neon-backed trace persistence with query interface
- Quality scoring and feedback loops on every execution
- Error recording with centralized error taxonomy

## Disaster Recovery

- All state in Neon Postgres (replicated, backed up)
- Stateless services rebuildable from Docker images
- Configuration in version control (substrate/) and runtime config store
- Node failure isolation -- any single node can go down without system halt

## Multi-Tenant Capability

The substrate is architecturally multi-tenant (UMH_ORG_ID, RLS policies) even though current deployment is single-user. This enables future scaling to:

- Multiple operators per organization
- SaaS productization of projections
- White-label deployment of the substrate
