# Phase 8.1 — Dependency Graph

**Date**: 2026-05-28
**Status**: COMPLETE
**Goal**: Build dependency model showing how UMH subsystems depend on each other.

## What Was Built

### substrate/organism/dependency_graph.py

**Core entities:**
- `DependencyNode` — a node in the graph
- `DependencyEdge` — directed edge with type and strength
- `DependencyType` — runtime, code, data, governance, interface, deployment, memory, event, execution, operator
- `DependencyStrength` — hard, soft, optional
- `CriticalPath` — longest chain with risk assessment
- `DependencyGraph` — full graph with analysis methods

**Analysis capabilities:**
- `upstream()` / `downstream()` — what depends on what
- `orphaned_nodes()` — nodes with no connections
- `circular_dependencies()` — DFS cycle detection
- `critical_paths()` — longest dependency chains
- `weak_dependencies()` — soft/optional edges
- `missing_dependencies()` — edges pointing outside the graph

**28 known dependency edges** encoded from observed wiring (daemon→subsystem relationships,
adapter chains, governance flow, execution pipeline).

**Extraction result:**
- 80 nodes (from WorldModel), 28 edges
- 0 cycles (clean DAG)
- 55 orphaned nodes (panels, stores, etc. — expected for leaf nodes)
- Critical path length: 4

### API Integration
- Bridge handler: `organism.dependency_graph` in organism_bridge.py
- Route: `GET /api/umh/organism/dependency-graph`

### Tests
- 20 tests in `substrate/organism/tests/test_dependency_graph.py`
- Covers: node/edge creation, traversal, cycle detection, critical paths, orphan detection, serialization, integration, persistence
- **20/20 PASS**

## Success Criteria
The organism can answer "what depends on what?" and identify critical paths. **MET.**
