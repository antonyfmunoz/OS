# Hermes Adapter Parity Audit

## Date: 2026-06-10

## Adapter Comparison Matrix

| Capability | CC SDK | Groq/Gemini (API) | Ollama (local) | Beast Ollama | **Hermes** |
|---|---|---|---|---|---|
| generate() | YES | YES | YES | YES | **YES** |
| chat/session | YES (tmux) | stateless | stateless | stateless | **YES (VPS-managed)** |
| health() | binary check + CPU gate | API key check | localhost check | remote check | **YES (mesh + binary + verified)** |
| streaming | YES (CLI) | YES (API) | YES (API) | NO | **NO (pseudo-streaming)** |
| cancel | process kill | N/A | N/A | N/A | **YES (best-effort kill)** |
| token count | YES (SDK) | YES (API) | YES (API) | YES (API) | **estimated (chars/4)** |
| diagnostics | binary/auth check | key check | connection | connection | **YES (full)** |
| providers | known | known | model list | model list | **YES (config show, secrets stripped)** |
| models | known | known | API list | API list | **YES (config show)** |
| benchmark | N/A | N/A | N/A | N/A | **YES (10-test suite)** |
| capabilities registry | implicit | implicit | implicit | implicit | **YES (explicit)** |
| role matrix | purpose routing | purpose routing | purpose routing | purpose routing | **YES (benchmark-gated)** |
| backpressure | CPU gate | provider state | provider state | provider state | **YES (provider state)** |
| error codes | mixed | HTTP status | connection errors | connection errors | **YES (structured HERMES_*)** |
| metadata | partial | partial | partial | partial | **YES (full: runtime, node, transport, purpose, grounding)** |

## Hermes Unique Features (not in other adapters)

1. **Explicit capability registry** — `CAPABILITY_STATES` dict declares what's supported/unsupported/unknown
2. **Role matrix with benchmark gating** — roles assigned by test results, not assumption
3. **Structured error codes** — `HERMES_TIMEOUT`, `HERMES_AUTH`, `HERMES_UNAVAILABLE`, `HERMES_UNSUPPORTED_OPERATION`
4. **Actionable diagnostics** — blockers include recovery actions
5. **VPS-managed sessions** — conversation history preserved across stateless CLI calls
6. **Secret stripping** — provider inventory auto-redacts keys/tokens/secrets

## Hermes Limitations (honest)

1. **No native streaming** — Hermes CLI is synchronous; pseudo-streaming via heartbeat only
2. **No native sessions** — VPS prepends history to each call; not true server-side sessions
3. **Estimated tokens** — chars/4 approximation, not real token count
4. **Latency** — 9-15s per call (network + CLI startup + LLM inference)
5. **Single concurrent call** — one hermes process at a time on Beast
6. **No vision** — not proven; blocked in role matrix
7. **No tool use** — Hermes CLI doesn't expose tool-calling interface to UMH

## Operation Support Matrix

| Operation | Status | Notes |
|---|---|---|
| hermes.generate | SUPPORTED | base64-encoded prompt via PowerShell |
| hermes.health | SUPPORTED | liveness probe + binary check |
| hermes.providers | SUPPORTED | config show, secrets stripped |
| hermes.models | SUPPORTED | config show extraction |
| hermes.capabilities | SUPPORTED | explicit registry |
| hermes.diagnostics | SUPPORTED | full state + blockers + recovery |
| hermes.benchmark | SUPPORTED | 10-test suite with role assignment |
| hermes.cancel | SUPPORTED | best-effort process kill |
| hermes.stream | UNSUPPORTED | CLI is synchronous |
| hermes.session.create | SUPPORTED | VPS-managed |
| hermes.session.send | SUPPORTED | history prepended |
| hermes.session.read | SUPPORTED | turn history |
| hermes.session.list | SUPPORTED | active session list |
| hermes.session.close | SUPPORTED | status → closed |

## Verdict

Hermes has **full adapter parity** for all operations that are structurally possible given its CLI nature. Where parity is impossible (streaming, native sessions, exact tokens), the limitation is explicitly declared in the capability registry with clear reason and workaround documented.
