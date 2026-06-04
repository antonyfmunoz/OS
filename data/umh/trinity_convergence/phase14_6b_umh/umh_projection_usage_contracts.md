# UMH Projection Usage Contracts

**Phase:** 14.6B-UMH | **Status:** DRAFT | **Provenance:** CODE_RESOLVED_CURRENT_TRUTH + OPERATOR_CORRECTION

---

## Current Integration Pattern

All three projections follow an identical socket-based integration pattern implemented in projections/*/integration/:

### Signal Contract

Each projection declares signal types it emits via SignalDescriptor objects:

- **EOS:** contact_created, deal_created, activity_logged
- **CreatorOS:** post_created, product_listed, revenue_recorded
- **LyfeOS:** quest_completed, daily_log_created, stats_updated

### Capability Contract

Each projection declares capabilities it exposes via CapabilityDescriptor objects:

- **EOS:** noop, create_contact, create_deal, update_deal_stage, log_activity (5 capabilities)
- **CreatorOS:** noop, create_post, create_product, record_revenue (4 capabilities)
- **LyfeOS:** noop, create_quest, complete_quest, log_daily_reflection (4 capabilities)

### Polling Contract

Each projection configures polling intervals:

- **EOS:** 15s default (crm_contacts, crm_deals, crm_activities)
- **CreatorOS:** 60s default (posts, products, revenue)
- **LyfeOS:** 30s default (quests, user_daily_logs, vision_goals)

### Outcome Contract

Each projection implements dual writeback:

1. Source row update (umh_status column on the polled table)
2. Audit table insert (umh_outcomes table with severity ladder)

### Configuration Contract

Each projection loads from environment:

- DATABASE_URL (required)
- USER_IDS (optional, comma-separated)
- POLL_INTERVAL (optional, seconds)

### ID Type Contract

- **EOS:** text UUIDs
- **CreatorOS:** serial integers
- **LyfeOS:** serial integers

## Current Implementation Status

| Projection | manifest | signals | handlers | outcomes | correlation | tables | poller |
|-----------|----------|---------|----------|----------|-------------|--------|--------|
| EOS | YES | YES | YES | YES | YES | YES | YES |
| CreatorOS | YES | YES | YES | YES | YES | YES | NO |
| LyfeOS | YES | YES | NO | NO | NO | NO | NO |

EOS is the most complete with all 7 integration components including a background poller.
CreatorOS has 6 of 7 (no poller).
LyfeOS has only 2 of 7 (manifest + signals).

## What Projections CAN Access via UMH

1. Ingestion pipeline -- raw data to structured signals
2. Signal interpretation -- intent classification of projection events
3. Decomposition -- breaking events into primitive observations
4. Memory -- store and recall context relevant to projection domain
5. Model routing -- LLM calls through UMH's provider chain
6. Governance -- risk classification and approval gates
7. Execution -- governed action execution back into projection database
8. Audit -- trace recording of all actions taken
9. Cross-product intelligence -- when multiple projections are connected

## What Projections CANNOT Access

1. Other projections' raw data (without explicit cross-projection policy)
2. Cockpit operator commands and decisions
3. Substrate internals (type system, governance engine, memory implementation)
4. External tool credentials
5. Infrastructure details (VPS, Docker, Tailscale)

## Future Projection Access Methods

Beyond the current polled-table pattern, projections may access UMH via:

1. Direct API calls to substrate endpoints
2. MCP server connections
3. Event stream subscriptions
4. Webhook push from projection to UMH
5. Embedded AI assistants powered by UMH pipeline
6. CLI tools
7. SDK libraries

## Gaps

1. LyfeOS integration is incomplete (only manifest + signals)
2. CreatorOS has no poller (integration waits for manual trigger or external call)
3. No versioning on integration contracts
4. No health check mechanism for projection connections
5. No circuit breaker for projection database failures
6. No rate limiting on projection signal emission
7. ProductConnectionManager violates architecture (substrate imports from projections)
8. Projection manifests are shallow compared to corrected 14.6B product canons
