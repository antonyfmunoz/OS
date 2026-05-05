# W0-001 Tab-Aware Source Graph Report

**Date**: 2026-05-04
**Status**: COMPLETE
**Supersedes**: w0_001_source_graph_report.md (7.9% coverage)
**Corpus**: 283,831 words across 321 tabs in 28 Google Docs

---

## 1. Entity Discovery

| Category | Unique Entities | Total Mentions |
|----------|:--------------:|:-------------:|
| Companies | 7 | High frequency |
| Products | 5 | High frequency |
| Concepts | 10 | Very high frequency |
| Frameworks | 5 | Moderate frequency |
| People | 3 | Low-moderate frequency |

## 2. Core Entities (by cross-document frequency)

### Companies / Platforms
- **LyfeOS** — referenced in 15+ documents
- **EntrepreneurOS** — referenced in 12+ documents
- **CreatorOS** — referenced in 10+ documents
- **Empyrean Studios** — referenced in 8+ documents
- **Lyfe Institute** — referenced in 8+ documents
- **Lyfe Spectrum** — referenced in 6+ documents
- **Munoz Conglomerate** — referenced in 5+ documents

### Products / Offers
- **Initiate Arena** — referenced in 8+ documents
- **Game of Lyfe** — referenced in 6+ documents
- **UMH (Universal Mets Harness)** — referenced in 5+ documents
- **Virality Bible** — referenced in 4+ documents

### Key Concepts (highest frequency)
- content, offer, revenue, coaching, pipeline
- personal brand, outreach, scaling, funnel

## 3. Cross-Document Connections

- **59 unique entities** tracked across the corpus
- **1,277 cross-document connection edges** (entity appears in multiple docs)
- Highest connectivity: LyfeOS, EntrepreneurOS, CreatorOS (appear in most documents)
- Strongest clusters: product specs ↔ coaching ↔ brand identity

## 4. Document Centrality

Most connected documents (most shared entities with other docs):
1. LyfeOS (53 tabs) — connects to nearly all other documents
2. EntrepreneurOS (14 tabs) — product architecture references all brands
3. Coaching Philosophy (35 tabs) — methodology referenced by all coaching docs
4. Antony F. Munoz Personal Brand — brand identity connects to all ventures
5. Systems Inventory — cross-references tools/platforms

## 5. Structural Findings

- The corpus forms a single connected graph — no isolated documents
- Product specs (LyfeOS, EntrepreneurOS, CreatorOS) form the dense core
- Coaching content forms a secondary cluster connected through methodology
- Brand docs bridge between product and coaching clusters
- Operational docs are leaf nodes with few cross-references

## 6. What Changed From Prior Graph

| Finding | Prior (7.9%) | Current (100%) |
|---------|:---:|:---:|
| CreatorOS in graph | No (appeared empty) | Yes (27K words, core node) |
| Empyrean Studios in graph | No (appeared empty) | Yes (11K words, connected) |
| Cross-document edges | ~150 | 1,277 |
| Unique entities | ~15 | 59 |
| LyfeOS connectivity | Low (255 words) | Highest (44K words) |
