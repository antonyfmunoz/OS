# Template Pattern Promotion — Policy v1
**Phase**: 96.3/96.4  
**Status**: ACTIVE  
**Date**: 2026-05-04
---

## Core Rule
Instance patterns may become reusable templates through a structured abstraction process. Privacy review is mandatory. Ready-for-promotion requires raw details removed, privacy review passed, and founder approval.

## Details
### What Qualifies as a Template Candidate
- A workflow, structure, or pattern observed in instance data
- A document format that could serve other instances
- A decision framework that generalizes beyond one context
- An operational procedure proven effective in practice

### 7 Promotion Statuses
1. **IDENTIFIED** — pattern recognized in instance data
2. **ABSTRACTION_DRAFT** — instance details removed, draft template created
3. **PRIVACY_REVIEW_PENDING** — awaiting privacy review
4. **PRIVACY_REVIEW_PASSED** — confirmed no PII, no instance-specific data
5. **PRIVACY_REVIEW_FAILED** — PII or instance data found; return to abstraction
6. **READY_FOR_PROMOTION** — all checks passed, awaiting founder approval
7. **PROMOTED** — live in TEMPLATE_LIBRARY, available across instances

### Abstraction Requirements
- All names, accounts, and identifiers removed or replaced with placeholders
- Financial figures removed or replaced with `[AMOUNT]` placeholders
- Dates removed or replaced with relative references (`[DATE]`, `[QUARTER]`)
- Proprietary strategy content removed entirely — not abstracted, removed
- Structure and pattern preserved; content replaced

### Privacy Review Checklist
- [ ] No personal names remain
- [ ] No email addresses remain
- [ ] No account identifiers remain
- [ ] No financial figures remain
- [ ] No specific dates that could identify context
- [ ] No proprietary strategy or competitive intelligence
- [ ] No internal project codenames
- [ ] Template is useful without any instance context

### Template Metadata
- `source_instance` — which instance the pattern came from (provenance only)
- `abstraction_date` — when the template was created
- `privacy_review_date` — when privacy review completed
- `promotion_date` — when founder approved
- `usage_count` — how many instances have used this template
- `version` — template version for iteration tracking

## Constraints
- Templates MUST NOT contain any raw instance data
- Privacy review MUST be completed before READY_FOR_PROMOTION
- Founder approval MUST be explicit — no automated promotion to TEMPLATE_LIBRARY
- PRIVACY_REVIEW_FAILED requires return to ABSTRACTION_DRAFT, not a waiver
- Proprietary strategy content MUST be removed, not abstracted
- Templates MUST be independently useful without knowledge of the source instance
- Template provenance (source_instance) is for audit only — not exposed to template users

## References
- `docs/operations/global_canon_vs_instance_memory_doctrine_v1.md` — scope hierarchy
- `docs/operations/instance_specific_ingestion_policy_v1.md` — instance scoping
- `docs/operations/template_candidate_inventory_v1.md` — current candidates
