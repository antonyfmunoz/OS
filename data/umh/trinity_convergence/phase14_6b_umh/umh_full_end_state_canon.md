# UMH Full End-State Canon

Phase: 14.6B-UMH
Status: DRAFT

## Vision

UMH at end-state is a private Jarvis system -- a fully autonomous intelligence substrate that governs the founder's entire operational surface across business, creative, and personal domains.

## Cockpit End-State

The cockpit becomes a full command center with three interaction modes:

- **Voice** -- natural language commands and ambient listening
- **Text** -- structured chat with operator/DEX dialogue
- **Visual** -- 27+ panels for real-time system state, execution traces, governance decisions

Ambient display mode shows passive system health, active executions, and incoming signals without requiring operator input. Proactive alerting surfaces anomalies, opportunities, and required decisions before the operator asks.

## Projection Maturity

Each projection matures into a governed SaaS-grade product:

| Projection | Domain | End-State |
|---|---|---|
| EntrepreneurOS (EOS) | Business | Full venture management -- clients, offers, transactions, analytics, outreach automation |
| CreatorOS | Creator workflow | Content pipeline, audience analytics, brand management, publishing automation |
| LyfeOS | Life management | Health tracking, relationship management, financial oversight, habit systems |

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
