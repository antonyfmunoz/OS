---
type: codebase-function
file: scripts/action_system.py
line: 340
generated: 2026-04-12
---

# ActionSystem.assess_impact

**File:** [[scripts-action_system-py]] | **Line:** 340
**Signature:** `assess_impact(action) → Impact`

**Class:** [[scripts-action_system-py-ActionSystem]]

Use the graph to describe the blast radius of this action.

For targets that are files in the graph, this returns direct
dependents and dependencies plus critical-hub flagging. For
non-file targets (commands, scripts-by-name) it returns an
...

## Calls

- [[scripts-action_system-py-ActionSystem-_critical_hub_set]]
- [[scripts-action_system-py-ActionSystem-_graph]]
- [[scripts-action_system-py-_rel_to_root]]
- [[scripts-query_graph-py-GraphQuery-centrality]]
- [[scripts-query_graph-py-GraphQuery-dependencies]]
- [[scripts-query_graph-py-GraphQuery-dependents]]

## Called By

- [[scripts-action_system-py-ActionSystem-evaluate_risk]]
- [[scripts-action_system-py-ActionSystem-propose]]
