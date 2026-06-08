# Phase 14.13O — Mesh Relay Security Hardening Seal Report

**Date:** 2026-06-08
**Verdict:** SHIPPED

## Original Security Findings

### Finding 1: Firewall bypass via top-of-chain INPUT insert (MEDIUM)
The 14.13N code used `iptables -I INPUT 1` to insert an ACCEPT rule at the
very top of the INPUT chain, before all ufw/tailscale policy rules. While
scoped to Docker CIDR and port 8095, the position could bypass more specific
policy rules if the firewall was later expanded.

### Finding 2: Under-validated config-driven port reaches iptables --dport (MEDIUM)
The relay port was derived from `config.port + 1` and passed directly to
`iptables --dport` without validation. A misconfigured config.toml could
inject an arbitrary port into the firewall rule.

## Exploitability Assessment

Neither finding was exploitable in context:
- Config TOML is root-owned on VPS
- Port is hardcoded 8094 in config
- Docker CIDR source restriction limits scope
- VPS is behind Tailscale with no public port exposure for 8095

Both were fixed as defense-in-depth before expanding workstation control.

## Fixes Applied

### Workcell A — Port Validation
- `_validate_relay_port()` rejects non-integer, <1024, >65535
- Called before any iptables command or relay bind
- Raises ValueError with descriptive message on failure

### Workcell B — Dedicated Chain
- Created `UMH_MESH_RELAY` iptables chain
- INPUT appends jump to dedicated chain (not top-of-chain insert)
- Chain contains exactly: scoped ACCEPT + RETURN
- Traffic not matching falls through to normal INPUT processing
- Legacy top-of-chain ACCEPT auto-removed on startup

### Workcell C — Idempotency
- Chain is flushed and rebuilt on every startup
- Jump added only if not already present (`-C` check first)
- Tested: 3 restarts, rule count stable at 1/1/0 each time

### Workcell D — Diagnostic Script
- `scripts/check_mesh_relay_firewall.py` — 7-point check:
  1. Port validation (range 1024-65535)
  2. Docker bridge CIDR match
  3. Dedicated chain exists
  4. Exactly 1 scoped ACCEPT rule in chain
  5. Exactly 1 INPUT jump
  6. No legacy top-of-chain ACCEPT
  7. No duplicate rules
- All 7 checks PASS

## Regression Results

### Firewall Check: 7/7 PASS

### Workstation Command Regression: 4/4 PASS

| Test | Intent | Result |
|------|--------|--------|
| open spotify | workstation_control | ok=true, status=executed |
| show approvals | approval_query | deterministic, no LLM |
| start my workday | startup_sequence | 6 providers healthy |
| message on instagram | workstation_control | blocked (governance) |

### Idempotency: 3/3 PASS
- 3 consecutive restarts
- INPUT→UMH_MESH_RELAY jumps: always 1
- Chain ACCEPT rules: always 1
- Legacy rules: always 0

## Files Modified

| File | Change |
|------|--------|
| transports/node_mesh/run.py | Port validation, dedicated chain, legacy cleanup |
| scripts/check_mesh_relay_firewall.py | New diagnostic script (7-point check) |

## Remaining Limitations

1. **No HTTP relay auth token** — relay accepts any request from Docker CIDR.
   Defense-in-depth suggests adding a shared-secret header. Not blocking for
   current scope (single-operator VPS, Tailscale-only network).

2. **iptables not persistent across reboot** — rule is recreated on mesh
   server startup. If mesh server doesn't start, Docker containers can't
   reach relay. Acceptable since relay is useless without mesh server.

3. **VPS API health check shows "unreachable" in startup** — os-operator
   checks localhost:8091 which is itself inside Docker. Cosmetic.

## Verdict Criteria

- [x] Relay port strictly validated (1024-65535, integer only)
- [x] Unsafe top-of-chain ACCEPT removed (dedicated chain instead)
- [x] Firewall rules idempotent (3 restarts, no duplicates)
- [x] Relay still works (Docker→relay→Beast confirmed)
- [x] Beast workstation execution still works (Spotify launched)
- [x] Approval query remains deterministic (no LLM)
- [x] Provider health remains truthful (6 providers)
- [x] Security seal report exists (this document)
