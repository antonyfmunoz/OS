# Projection Read-Surface Discipline

A **projection read surface** is a read-only HTTP endpoint that reports the state
of a projection (readiness, health, status, activation) over the substrate. This
rule defines the ONE legal shape for such surfaces so that adding the next one
does not drift into cockpit sprawl, substrate leakage, or duplicate readiness
models.

Reference implementation: `GET /eos/activation`
(`transports/api/cockpit_core_eos_routes.py`) backed by
`projections/eos/integration/readiness.py::eos_readiness()`, established by the
EOS activation slice (PR #171).

## The discipline (six invariants)

A conforming projection read surface MUST:

1. **Projection-owned accessor.** The read logic lives in a single named function
   under `projections/<name>/` (e.g. `eos_readiness()`), never inline in the
   transport route.
2. **Thin transport wrapper.** The route body is: lazy-import the accessor, call
   it, return it. No `org_id` plumbing, no object construction, no reshaping.
3. **Lazy projection import.** The `from projections.<name>...` import is INSIDE
   the handler function, not at module top. (This keeps the transport module
   importable without eagerly loading projection code, and is why
   `cockpit_core_eos_routes.py` is grandfathered in the dependency-direction
   gate's `LEGACY_VIOLATIONS`.)
4. **`try/except` → dict.** Success returns the accessor's dict; failure returns a
   stable error dict. A read surface NEVER raises a 500.
5. **No domain-model expansion in the route.** The accessor returns an already
   flat, JSON-serializable dict. The route never iterates, reshapes, or builds
   domain objects (`SomeView(...)`, `SomeEngine(...)`, `SomeRuntime(...)`).
6. **No direct registry/file read in the route or accessor.** Projection state is
   read through canonical substrate ports (e.g.
   `substrate.sockets.projection_port.load_umh_projection_seed` /
   `get_default_projection_port`), never by opening
   `data/umh/projection_registry.json` (already enforced by the Projection
   Registry Reads gate).

The accessor itself MUST additionally:

- **Import only downward** (projection → substrate / same-package). It MUST NOT
  import `transports/`. (Projections may legally import transports elsewhere —
  e.g. `projections/eos/workflows/runner.py` uses
  `transports.api.governed.governed_mutation` for a WRITE path — but a *read
  surface accessor* stays substrate-composed.)
- **Be env-disabled-safe** — return a stable "disconnected"/not-ready dict when
  the projection's env is unset, never raise.
- **Be side-effect-free** — no mutation, no writes.
- **Return a stable flat shape** — a fixed set of scalar/small-dict keys, covered
  by a shape test.

## Current EOS conformance (truthful baseline)

As of this rule, exactly **one** EOS route conforms: `/eos/activation`. The other
five predate the discipline and are **sanctioned legacy / follow-on debt**, NOT
proof the surface is clean:

| Route | Status | Why |
|---|---|---|
| `/eos/activation` | **conforms** | thin wrapper over `eos_readiness()`, no inline construction |
| `/eos/pipeline` | legacy | builds `PipelineView(...)` + expands `.stages` inline |
| `/eos/kpis` | legacy | builds `KPIView(...)` + expands `.cards` inline |
| `/eos/activity` | legacy | builds `ActivityView(...)` + expands `.entries` inline |
| `/eos/accountability` | legacy | imports substrate directly, builds `AccountabilityEngine(...)` inline |
| `/eos/intelligence` | legacy | imports substrate directly, builds `IntelligenceRuntime()` inline |

The regression test (`tests/test_projection_read_surface_discipline.py`) holds a
**shrink-only allowlist** of these five legacy routes. New `/eos/*` routes are
NOT added to the allowlist — they must conform. When a legacy route is later
refactored to the discipline, it is removed from the allowlist (the list only
ever shrinks).

## Sanctioned substrate exception

`substrate/integrations/product_connections.py` (`ProductConnectionManager`)
reads the same EOS config as `eos_readiness()` but is a **substrate-owned**,
process-wide singleton and a grandfathered `substrate → projections` legacy
import. It is the sanctioned legacy exception, not the pattern. New projection
read surfaces use a projection-owned accessor (like `eos_readiness()`) and do NOT
route through this singleton — `eos_readiness()` deliberately re-reads env fresh
instead.

## Scope

This rule governs **EOS** read surfaces (`projections/eos/*` + `/eos/*` routes)
today, because EOS is the only projection with a real governed read surface;
CreatorOS and LyfeOS are integration-only shells. Generalize to all projections
only when a second projection ships a governed read surface — do not write a
universal all-projections law over surfaces that do not exist yet.

## Do NOT (yet)

- Do NOT extract a `projection_read_route()` helper/factory — only one route
  conforms (N=1); a factory now would abstract a single instance.
- Do NOT add a strict inline-construction pre-commit gate — it would immediately
  flag the five legacy routes and pull a refactor into scope. The regression
  test with a shrink-only allowlist is the right instrument until the pattern
  repeats across projections.
