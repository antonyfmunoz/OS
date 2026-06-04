# UMH Projection Data Boundary and Privacy Model

**Phase:** 14.6B-UMH
**Status:** DRAFT
**Provenance:** OPERATOR_CORRECTION + INFERRED_PROFESSIONAL_GAP

---

## Importance

This model is critical because LyfeOS may include sensitive personal, health, identity, emotional, trauma, relationship, journaling, and performance data. CreatorOS handles audience/customer data. EOS handles company/team data. Each requires scoped data boundaries.

## Data Categories

### 1. Product-Local Private Data
Data that stays entirely within the projection's own database.
- EOS: CRM contacts, deal stages, activity logs, company structure
- CreatorOS: post drafts, unpublished products, revenue details, audience lists
- LyfeOS: journal entries, therapy notes, trauma logs, emotional state, health metrics, relationship data
**UMH access:** NONE unless explicitly shared via signal emission

### 2. UMH-Visible Metadata
Projection data that UMH can see through declared signal types.
- EOS: contact_created, deal_created, activity_logged (3 signal types)
- CreatorOS: post_created, product_listed, revenue_recorded (3 signal types)
- LyfeOS: quest_completed, daily_log_created, stats_updated (3 signal types)
**Rule:** Only data included in SignalEnvelope content field is visible to UMH.

### 3. UMH-Governed Source Truth
Data that UMH classifies, reasons about, and stores as source truth.
- Decomposed primitive observations from projection signals
- Memory entries created from projection interactions
- Trace records of actions taken on projection data
**Rule:** Source truth is UMH-owned but derived from projection signals.

### 4. UMH Memory-Eligible Data
Data that may be promoted to UMH's canonical memory store.
- Patterns detected across projection interactions
- Decisions made about projection operations
- Quality scores from projection-related executions
**Rule:** Memory promotion follows canonical memory store rules. Sensitive data should be excluded.

### 5. Audit-Only Data
Data recorded for governance and compliance but not used for reasoning.
- Approval decisions and rationale
- Execution traces with event types
- Error recordings from projection operations
**Rule:** Audit data is append-only. Should avoid capturing sensitive payloads.

### 6. Sensitive Excluded Data
Data that MUST NOT enter UMH under any circumstances.
- LyfeOS: Therapy session content, trauma narratives, self-harm indicators, medication details, relationship intimate details
- CreatorOS: Audience personal identifiers (beyond what creators share), payment card details
- EOS: Employee SSNs, salary details, termination records, legal case details
**Rule:** HARD BOUNDARY. No exceptions. Signal emitters must filter.

### 7. Operator-Private Data
Data visible only to the operator via Cockpit.
- Cockpit commands and decisions
- Operator preferences and configuration
- Cross-product intelligence synthesis
- Infrastructure status
**Rule:** Operator data never exposed to projection end-users.

### 8. End-User Private Product Data
Data owned by the end-user within their projection.
- LyfeOS user's personal journal, quests, daily logs
- CreatorOS creator's content, audience, revenue
- EOS team member's tasks, communications
**Rule:** End-user data governed by projection-specific privacy policy.

### 9. Projection-Shared Data
Data shared between projections through UMH orchestration.
- Cross-product insights (e.g., "content that performed well in CreatorOS -> EOS marketing")
- Shared user identity across projections
- Coordination signals between projections
**Rule:** OPT-IN ONLY. Requires explicit policy. Operator approval for sensitive categories.

### 10. Cross-Product Synthesis Data
Intelligence synthesized from multiple projections.
- Combined analytics across EOS + CreatorOS
- Life-work balance insights from LyfeOS + EOS
- Content-to-revenue correlation from CreatorOS + EOS
**Rule:** Synthesis happens in UMH. Results accessible via Cockpit. May be fed back to individual projections only if policy allows.

## Rules

1. UMH must NOT ingest all product data by default -- only declared signal types
2. Projection data shared with UMH must be permissioned and scoped via signal descriptors
3. Embedded projection AI must know what data it can access (capability descriptors)
4. Cockpit access to end-user data must be governed (operator has broad access but audit-logged)
5. Sensitive LyfeOS data (therapy, health, trauma) requires EXPLICIT exclusion policy
6. CreatorOS audience/customer data requires scoped permission per creator
7. EOS company/team data requires org-level boundaries
8. Audit logs should avoid leaking sensitive payloads where possible
9. Data provenance must be tracked (which projection, which signal type, when)
10. Cross-product synthesis must be opt-in or policy-governed

## Current Implementation Status

| Concern | Status | Evidence |
|---------|--------|---------|
| Signal-scoped data access | IMPLEMENTED | Each projection declares exactly which signals it emits |
| Capability-scoped writeback | IMPLEMENTED | Each projection declares exactly which capabilities it exposes |
| Sensitive data filtering | NOT IMPLEMENTED | No filter in signal emitters for sensitive content |
| Cross-projection isolation | PARTIAL | Separate DATABASE_URLs provide physical isolation |
| Privacy policy per projection | NOT IMPLEMENTED | No privacy policy framework exists |
| Audit log payload filtering | NOT IMPLEMENTED | Full signal content may appear in traces |
| Data provenance tracking | PARTIAL | Signal source tracked but no formal provenance chain |
| Operator data access audit | NOT IMPLEMENTED | No log of what operator viewed |

## Gaps

### P0 -- Must Resolve Before Cockpit Governs Implementation
1. No sensitive data exclusion mechanism in signal emitters
2. No privacy policy framework for projections
3. No data classification tags on SignalEnvelope

### P1 -- Must Resolve Before Trinity Feature Build
1. LyfeOS data could contain therapy/health content -- needs explicit exclusion
2. No mechanism to revoke/forget user data across projections
3. No data retention policy
4. Audit logs may contain sensitive payloads

### P2 -- Before Production Scale
1. Cross-product synthesis needs opt-in consent mechanism
2. GDPR/privacy compliance framework
3. Data portability (user export)
4. Right to deletion
