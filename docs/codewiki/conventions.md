---
type: codewiki-page
dir: (cross-cutting)
---

# Conventions & Operating Laws

**The non-negotiable rules that govern every change to UMH.** Most are mechanically enforced by a pre-commit gate or a regression test — this page names each law and exactly WHERE it is enforced, so you can verify rather than trust. Sources: `CLAUDE.md`, `.claude/CLAUDE.md`, and the `.claude/rules/*.md` law files. Every enforcement script named below exists under `scripts/`.

## The two operating principles

These govern every build, configuration, and execution (`CLAUDE.md`):

1. **Tool Mastery Engine (TME)** — a UMH substrate subsystem, not a tutorial database. Before using any external tool, check `skills/tools/{toolname}/`: if a current skill exists, load it; if missing, research official docs exhaustively and create the skill; if stale, re-research. Created tool skills trigger independently in future sessions. *Where:* the `/tool-mastery-engine` skill + `skills/tools/`.
2. **Operationalization Principle** — after anything works: document → skill or template → never rebuild from scratch → always improvable. UMH compounds with every execution. *Where:* the `/operationalization-principle` skill, run after any successful execution.

## Retrieval hierarchy (NON-NEGOTIABLE)

AI never starts blind. Knowledge is retrieved in strict order — you may only drop to the next tier when the prior one cannot answer:

```
Palace → Graph → Summaries → Raw Source → Logs / Transcripts
```

- **Palace** — `knowledge/palace/rooms/<room>.md` names the concern and its highest-value files.
- **Graph** — `python3 scripts/query_graph.py <deps|dependents|path|critical|centrality|search>` answers every structural question. Never `Read` a Python/JS/TS/SQL file before running at least one graph query for it; never `Grep` a symbol the graph already indexes.
- **Summaries** — `data/node_summaries.json`, one line per file/class/function.
- **Raw source** — only when graph + summary cannot answer, and you can state which query was insufficient.
- **Logs** — last resort.

*Where:* `CLAUDE.md` Cognition Stack + `knowledge/retrieval_rules.md`; freshness checked by `scripts/session_bootstrap.py` and `scripts/verify_knowledge_system.py`.

## Deterministic-First Principle (NON-NEGOTIABLE)

The deterministic layer is the spine — it always works; AI is a cognitive enhancement, not a dependency. Every LLM call MUST have a deterministic fallback that produces a usable result. Build the deterministic result first (rules/regex/lookup), then try AI enhancement, keep whichever is better. The acceptance test: "all LLM providers are down — does the system still produce output?" must be yes. Routing, classification, validation, and scheduling are the deterministic spine; content generation and synthesis are AI-enhanced with template fallback. *Where:* review discipline + the router contract in `adapters/models/model_router.py` (see [tech-stack.md](tech-stack.md)).

## CPU Gate Law (NON-NEGOTIABLE)

UMH must never saturate CPU on any host — Hostinger throttled the VPS for a full week after a runaway process. Single choke point: **`substrate/execution/cpu_gate.py`** (`cpu_gate_check(caller)`, `gated_subprocess_run(...)`, `gated_popen(...)` — the gated wrappers return `None` when CPU is overloaded, and callers must handle that gracefully). **Never** use raw `subprocess.run/Popen/call/check_output/check_call` in `substrate/`, `adapters/`, `transports/`, or `services/`. Six-layer defense (innermost → outermost): (1) substrate cpu_gate 1.8/core, (2) `cc_sdk` gate 1.5/core, (3) Docker CPU caps 0.25–0.35/container, (4) `cron-run` wrapper, (5) `watch_graph` 4.0 threshold, (6) systemd watchdog (3.0 SIGSTOP / 4.0 SIGKILL). *Where:* pre-commit Gate 5, **`scripts/check_cpu_gate.py`**, blocks any new raw subprocess call in gated dirs. All 120 legacy violations were migrated; zero remain.

## Type Coherence Law

Before defining any Enum, `BaseModel`, or `@dataclass`, check `substrate/canonical_types.py` (~1,040 registered types). If the name exists → import it, never redefine. Never create a parallel type system. Canonical homes: `substrate/types.py` (general domain types), `substrate/contracts/agent_types.py` (TaskType, ModelProvider), `substrate/execution/runtime/capability_router.py` (Capability). Legacy homonyms live in a shrink-only `LEGACY_DUPLICATES_META` ledger. *Where:* **`scripts/check_type_divergence.py`** (pre-commit blocks new divergence; `--registry-audit` is a fail-closed CI check; `--all` is capped by `tests/test_type_divergence.py`).

## Instance Context Law

**Canonical** (`substrate/`) = universal mechanisms; **Instance** = identity loaded at runtime from BIS/env/config. Before writing any string literal in `substrate/`, ask: "would this be different for a different UMH user?" If yes it's instance context — use runtime lookup. Always instance: AI name (`get_ai_name()`), founder/company/venture/product names (BIS), IPs/hosts (env), node IDs (registry). Code carries ZERO tenant data; the founder (AFM) is "instance 0", reached through the same resolution path a future tenant would use. *Where:* **`scripts/check_instance_leak.py`** (pre-commit, whole-tree zero-tolerance) + `scripts/check_secret_patterns.py`.

## Projection Boundary Law

Two layers that must never mix: **Substrate** (`substrate/`, universal, works for any projection) and **Projections** (`projections/`, applications like EOS/CreatorOS/LyfeOS built on the substrate). Before writing any identifier in `substrate/`, ask: "would this differ for a different projection?" `EntrepreneurOS*` class names, `EOS_*` env vars, and `eos-*` prefixes are projection-specific. Projections register at runtime through abstract ports: `substrate/sockets/projection_port.py` is the ONE canonical projection-registration surface (not to be confused with `substrate/organism/projection_port.py`, the organism state-broadcast port). *Where:* **`scripts/check_projection_leak.py`** + `scripts/check_projection_registry_reads.py`.

## Architecture Layer Law

Four layers with strictly one-way downward dependency — never upward, never sideways between peers:

```
projections/  →  transports/  →  adapters/  →  substrate/
```

`substrate/` may import nothing above it; to reach upward it exposes an abstract port in `substrate/sockets/`. `saas/` is the EOS projection ONLY and imports UMH HTTP infra from `transports/api/http/`. `services/` holds deployment entrypoints only — no business logic. *Where:* **`scripts/check_dependency_direction.py`** (pre-commit), with a shrink-only `LEGACY_VIOLATIONS` allowlist. See [architecture.md](architecture.md).

## Ontology / Metamodel Layer Law (Gate 13)

Substrate defines the **rules of worlds**, never the **contents of one world**. Four ontology layers: L1 External Reality Model (`substrate/reality_model/`), L2 Platform Metamodel (`substrate/types.py`, `substrate/ontology/`), L3 Projection Domain Models (`projections/`), L4 Semantic Grounding (`substrate/understanding/domains/`). L2 must never import L3 domain state. The **set** of ontology/reality/domain homes is frozen — a new home may not appear silently, and same-name modules that are distinct concerns (organism `world_model.py` self-model vs. understanding world-model; execution-policy `domain_registry.py` vs. L4 `BridgeRegistry`) must not be merged. *Where:* **`scripts/check_ontology_homes.py`** (Gate 13) + `scripts/check_ontology_layers.py`, with a shrink-only `LEGACY_ONTOLOGY_LEAKS` ledger.

## Credential Injection Law (NON-NEGOTIABLE)

Computer-use credentials are never plaintext CLI args, hardcoded strings, or unprotected env. All flow through 1Password: `op run --env-file=<tpl>` resolves `op://vault/item/field` URIs and injects them; template files use URIs, never raw secrets. Executor-side injection matters because env vars don't transit SSH. `validate_credential_source()` in `substrate/execution/credential_gate.py` runs before any authenticated computer use. *Where:* **`scripts/check_credential_injection.py`** blocks plaintext password patterns in subprocess/SSH calls.

## Device Naming Protocol

Never hardcode a device display name as a raw string ("VPS", "Beast", "Windows"). Format is `tailscale-hostname (device-type)`. Single source of truth: `infra/device_registry.json`; frontend imports from `cockpit/src/renderer/constants/devices.ts`; the `/workspace/mesh-nodes` API returns canonical names. *Where:* `.claude/rules/device-naming.md` (review discipline).

## Browser Verification Law (NON-NEGOTIABLE)

Browser-based verification (Playwright, DevTools, any MCP browser tool) NEVER runs on the orchestrator — it is headless with bundled Chromium and no display, producing false-positive evidence. All browser verification runs on executor-roled nodes (from `infra/device_registry.json`) with an interactive desktop session, via `browser_evidence_collector.trigger_collection()` routing through the mesh daemon's HTTP relay (`POST :8095/dispatch`) — never raw SSH (which lands in the display-less Session 0). *Where:* `.claude/rules/browser-verification.md` + `.claude/rules/credential-injection.md`.

## Client-Failure Observability Law (NON-NEGOTIABLE)

When a user-facing failure cannot be seen in server logs, STOP writing fixes and INSTRUMENT the client first — a diagnostic that makes an invisible failure visible beats any number of plausible fixes. If a client-side symptom survives one fix, the next change must be a diagnostic beacon (reference: `cockpit/src/renderer/api/voice-diag.ts` → `POST /api/umh/voice/diag` → `[VoiceClientDiag]` log). Never await a non-essential call on a user-blocking path. This law cost a full day and six wrong fixes (mobile voice, 2026-07-09) before a beacon found the real cause in one tap. *Where:* partially enforced by Gate 14, **`scripts/check_voice_runtime_divergence.py`**; the rest is review discipline.

## Cockpit Deploy Gate (NON-NEGOTIABLE)

Never run `flyctl deploy` directly for the cockpit. Always use **`bash cockpit/deploy.sh`** — the gate verifies `nginx.conf.template`, `Dockerfile`, and `start.sh` match main before deploying (preventing a worktree/branch deploy from shipping stale auth config), and blocks if the obsolete `nginx.conf` still exists. This rule exists because a worktree deploy once shipped without API-key injection, causing 401 on every cockpit API call. *Where:* `cockpit/deploy.sh`.

## Completion Standards & Inventory Verification Protocol (NON-NEGOTIABLE)

Every rule here was violated and caused a real failure:

- Never claim "done" without a verification pass that tries to break your own work; the verification pass must be MORE thorough than the implementation.
- Never claim a count is correct without comparing it to an independent measurement (`find`, `wc`, `grep -c`); never say "100%" without showing the matching numbers.
- When any output claims to be exhaustive: run `find /opt/OS -type f` (with standard excludes), sum your table, reconcile before reporting. Count ALL file types; every top-level dir and every non-empty subdir must appear.
- After code changes to `services/`, restart affected Docker containers and verify clean startup from logs. Docker is Python 3.11 — no 3.12+ syntax.
- Re-audit as a hostile reviewer after fixing. The user should never have to ask for the same thing twice.

*Where:* `CLAUDE.md` (Completion Standards + Inventory & Audit Verification Protocol) + `CLAUDE.local.md`; review discipline reinforced by the memory index.

## Plan File Immutability (NON-NEGOTIABLE)

Plan files in `~/.claude/plans/` are immutable once written. Every new plan gets its own file — never reuse or overwrite a filename. Re-entering plan mode archives the existing plan first (`cp {file} {file}-archived-<date>.md`). The only allowed edit is marking sections COMPLETED. Designs lost to overwrites are irrecoverable. *Where:* `CLAUDE.md` (Plan File Immutability) — review discipline.

## Node Role Discipline (NON-NEGOTIABLE)

Each device stores only what its role requires; never duplicate across nodes. The VPS is the lightweight always-on coordination brain (runtime, services, orchestration only — no large models, no archive dirs, no old proofs, no `node_modules` for inactive frontends). The Beast is the GPU workhorse holding full repos, large models, and heavy compute. Worktrees are removed immediately after merge; local branches deleted after merge; `git gc --prune=now` after bulk cleanup. *Where:* `CLAUDE.md` (Node Role Discipline) — review discipline. Violations (a 32GB `data/archive` on the VPS) are flagged in [health-findings.md](health-findings.md).

## Git conventions

Solo-founder phase: commit directly to `main`. Use feature branches for experimental or risky changes. Commit messages are lowercase imperative and specific. Parallel executor agents may READ `/opt/OS` but must branch/commit ONLY in their own isolated worktree — the main checkout is the live runtime's file source (containers volume-mount it), so a branch-switch there corrupts production. Secrets always in `.env` / 1Password — never committed, never hardcoded. Generated files use `YYYY-MM-DD` in the filename. *Where:* `CLAUDE.md` Protocol layers + universal rules.

## See also

- [architecture.md](architecture.md) — the layer model these laws protect
- [tech-stack.md](tech-stack.md) — the runtime and providers the laws govern
- [health-findings.md](health-findings.md) — where the codebase currently drifts from these laws
- [services-runtime.md](services-runtime.md) — the deploy targets the gates protect
