# Phase 0 Discovery — Ontology-Domain Bridge

> Date: 2026-05-12

## Business primitive inventory

`runtime/primitives.py` defines 13 `KnowledgePrimitive` instances in
`PRIMITIVE_LIBRARY`, each with:
- `id`: slug (e.g., `offer_optimization`)
- `domain`: category (sales, hiring, marketing, finance, growth, validation)
- `principle`: the business rule as a sentence
- `stage_applicability`: dict mapping stage int → bool
- `validity_conditions`: contextual rules with warnings/alternatives
- `prerequisite_ids`: dependency chain
- `common_misapplication`: anti-pattern text

### By domain

| Domain     | Primitive IDs                                        | Count |
|------------|------------------------------------------------------|-------|
| sales      | offer_optimization, outreach_before_content,         | 3     |
|            | pricing_psychology                                   |       |
| hiring     | hire_salesperson, hire_top_down, hire_bottom_up       | 3     |
| marketing  | paid_advertising, content_strategy                   | 2     |
| finance    | unit_economics, cash_flow_management                 | 2     |
| growth     | retention_over_acquisition, referral_flywheel        | 2     |
| validation | conversation_first                                   | 1     |

### Stage primitives (separate structure)

`STAGE_PRIMITIVES` maps stage int (1-6) to dicts with `name`, `focus`,
`rules`, `not_yet`. These are advisory context, not individual entities.

## Ontology observation shape (bridge input)

Each `PrimitiveObservation` has:
- `observation_id`: `obs-{hex8}`
- `primitive_type`: PrimitiveType enum (state/change/constraint/resource/
  signal/action/outcome/feedback/goal/time)
- `label`: semantic name (≤80 chars)
- `description`: semantic explanation (≤300 chars)
- `confidence`: 0.0–1.0
- `evidence`: verbatim source span
- `is_inferred`: bool

## Mapping analysis

### What "mapping" means

A domain bridge takes an ontology observation and asks: "Does this
observation relate to a business domain, and if so, which business
primitive(s) does it inform?"

Two levels of matching:
1. **Domain assignment** — which business domain (sales, hiring, etc.)
   does the observation relate to?
2. **Primitive identification** — which specific KnowledgePrimitive
   (offer_optimization, hire_salesperson, etc.) does it activate?

### Candidate mapping table

| Ontology type | Keyword pattern in label/description            | Business domain | Business primitive(s)                    | Mapping type |
|---------------|------------------------------------------------|----------------|------------------------------------------|-------------|
| constraint    | hire, hiring, recruit, team, salesperson        | hiring         | hire_salesperson, hire_top_down,          | STRUCTURAL  |
|               |                                                |                | hire_bottom_up                           |             |
| constraint    | offer, price, pricing, value prop               | sales          | offer_optimization, pricing_psychology   | STRUCTURAL  |
| constraint    | outreach, DM, direct message, cold              | sales          | outreach_before_content                  | STRUCTURAL  |
| constraint    | content, audience, followers, brand              | marketing      | content_strategy                         | STRUCTURAL  |
| constraint    | paid, ads, advertising, acquisition, CAC         | marketing      | paid_advertising                         | STRUCTURAL  |
| constraint    | revenue, cash, profit, runway, burn              | finance        | cash_flow_management, unit_economics     | STRUCTURAL  |
| constraint    | retain, churn, retention, NPS                    | growth         | retention_over_acquisition               | STRUCTURAL  |
| constraint    | referral, word of mouth                          | growth         | referral_flywheel                        | STRUCTURAL  |
| constraint    | conversation, ICP, customer discovery, validate  | validation     | conversation_first                       | STRUCTURAL  |
| action        | hire, recruit, build team                        | hiring         | hire_*                                   | STRUCTURAL  |
| action        | outreach, DM, prospect, cold email               | sales          | outreach_before_content                  | STRUCTURAL  |
| action        | price, charge, anchor                            | sales          | pricing_psychology                       | STRUCTURAL  |
| action        | scale, grow, expand                              | growth         | (stage-dependent)                        | SEMANTIC    |
| goal          | revenue, profit, $XK/month                       | finance        | unit_economics, cash_flow_management     | STRUCTURAL  |
| goal          | close, convert, sale, customer                   | sales          | offer_optimization                       | STRUCTURAL  |
| goal          | retain, reduce churn                              | growth         | retention_over_acquisition               | STRUCTURAL  |
| state         | stage, pre-revenue, bootstrapped                  | (stage detect) | (all, via stage gate)                    | STRUCTURAL  |
| state         | revenue $X, ARR, MRR                              | finance        | unit_economics                           | STRUCTURAL  |
| resource      | offer, product, service, program                  | sales          | offer_optimization                       | STRUCTURAL  |
| resource      | channel, platform, funnel                         | marketing      | content_strategy, paid_advertising       | STRUCTURAL  |
| resource      | team, employee, contractor                        | hiring         | hire_bottom_up, hire_salesperson          | STRUCTURAL  |
| signal        | objection, churn signal, cancellation             | growth         | retention_over_acquisition               | SEMANTIC    |
| feedback      | customer feedback, review, NPS                    | growth         | retention_over_acquisition,              | SEMANTIC    |
|               |                                                |                | referral_flywheel                        |             |
| outcome       | conversion, close rate, revenue gain              | sales          | offer_optimization                       | SEMANTIC    |
| change        | price change, offer iteration                     | sales          | pricing_psychology, offer_optimization   | SEMANTIC    |
| time          | (any)                                             | —              | —                                        | NO_MAP      |

### Summary counts

- **STRUCTURAL mappings: 18** — unambiguous from keyword patterns in
  label/description text
- **SEMANTIC mappings: 5** — need LLM disambiguation (e.g., "scale" could
  be growth, hiring, or infrastructure)
- **NO_MAP: 1** — `time` observations rarely map to business primitives

### V1 implementation scope

V1 implements STRUCTURAL mappings only. The mapping algorithm:
1. Lowercase the observation's `label` + `description`
2. Check against keyword sets per business domain
3. If domain matched, narrow to specific primitive ID(s) by checking
   primitive-specific keywords against the observation text
4. Return `DomainProjection` with domain_id, domain_primitive_type
   (the primitive ID), and properties extracted from the observation

### Fields the decomposer produces vs what business primitives need

| Business primitive field     | Available from observation? | Source             |
|------------------------------|----------------------------|--------------------|
| domain                       | YES (from keyword match)   | bridge logic       |
| primitive_type (business ID) | YES (from keyword match)   | bridge logic       |
| principle text               | NO                         | PRIMITIVE_LIBRARY  |
| stage_applicability          | NO                         | PRIMITIVE_LIBRARY  |
| validity_conditions          | NO                         | PRIMITIVE_LIBRARY  |
| evidence                     | YES                        | observation.evidence |
| confidence                   | YES                        | observation.confidence |

The bridge does NOT need to reconstruct KnowledgePrimitive instances.
It identifies WHICH primitive an observation relates to and creates a
projection that links the two. The full KnowledgePrimitive metadata
lives in PRIMITIVE_LIBRARY and can be looked up by ID.

## Stop condition check

- **Zero structural mappings?** NO — 18 structural mappings identified.
- **Fields decomposer can't produce?** NO — the bridge only needs
  label, description, primitive_type, confidence, and evidence, all of
  which are present on every PrimitiveObservation.

## Architecture decision

The bridge is a **domain-specific projection**, not a type conversion.
It answers: "This ontology observation about [constraint: 'AI must
translate questions to concerns'] is relevant to the [business]
domain, specifically the [conversation_first] primitive."

The projection is a separate memory entry that:
- Back-references the ontology observation
- Carries the business domain + primitive ID
- Preserves confidence and evidence from the observation
- Can be queried by business consumers using domain vocabulary
