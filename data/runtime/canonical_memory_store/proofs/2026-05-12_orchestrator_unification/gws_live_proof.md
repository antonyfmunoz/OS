# GWS Live Proof — GenericIngestionOrchestrator + GWSSource

> Date: 2026-05-12
> Verdict: COMPLETE_CYCLE

## What was tested

A real Google Workspace document ("SKILL.md", 14462 chars) was read via
`GWSDocumentScanner` → wrapped by `GWSSource` → ingested through
`GenericIngestionOrchestrator`. Full 6-stage canonical pipeline completed.

## Results

| Metric | Value |
|--------|-------|
| Verdict | COMPLETE_CYCLE |
| Duration | 1527.88ms |
| Signal ID | SIG-9013c2846674 |
| Memory ID | mem-11bec8e549454d5c |
| Observations | 7 |
| Entities added | 7 |
| Domains detected | architecture, runtime, governance, transport, identity |
| Memories before | 12 |
| Memories after | 13 |
| Promotion | promoted |

## Pipeline stages completed

1. perceive — signal created from GWSSource.read()
2. interpret — plain_text classification, 5 domains detected
3. decompose — 7 PrimitiveObservations extracted
4. map — 7 entities + facts written to world model
5. persist — canonical memory entry written to memories.jsonl (12→13)
6. query_back — entry searchable (rank 13 of 13)

## Source adapter behavior

- `GWSSource.exists()` — short-circuited via pre-fetched doc_meta
- `GWSSource.read()` — delegated to `scanner.read_doc()`, returned RawContent
- `GWSSource.metadata()` — mapped GWS fields to standard dict
- Content caching worked (read called once despite multiple pipeline references)

## Proof artifacts

- `gws_live_proof.json` — machine-readable proof
- `gws_live/` — 6 proof files from orchestrator._write_proofs()
