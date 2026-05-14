# Obsolete R8 Migration Scripts — 2026-05-14

## Reason

All 4 scripts were one-shot tooling for the R8 migration arc:
- r8b_generate_bridges.py — generated eos_ai/ temporary bridge modules
- r8d_generate_shims.py — generated eos_ai/ compatibility shims
- r8_import_graph_snapshot.py — captured import graph for migration verification
- r8_compare_import_graphs.py — diffed two import graph snapshots

The eos_ai/ shim layer was deleted in Wave 6 (commit 1c320aaf).
The migration arc is complete. These generators have no further purpose.

## Files (4)

- r8b_generate_bridges.py
- r8d_generate_shims.py
- r8_import_graph_snapshot.py
- r8_compare_import_graphs.py
