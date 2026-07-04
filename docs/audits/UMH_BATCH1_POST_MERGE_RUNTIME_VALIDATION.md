# UMH Batch 1 — Post-Merge Runtime Deployment Validation

**Date:** 2026-07-04
**Verifier:** orchestrator (VPS `srv1500858` / `100.77.233.50`)
**Scope:** deploy merged Batch 1 to VPS + Beast, restart the mesh daemons, and validate the full-stack mesh trust boundary live. Deployment/validation only — no code changes.

---

## Commit / node status

| Item | Status |
|---|---|
| `origin/main` | **`fc0a96304`** (target ✓; `fc0a96304` is ancestor-or-equal) |
| VPS `/opt/OS` checkout | **fast-forwarded `92b4d1959` → `fc0a96304`** (runtime-state files untouched; incoming commits touch no `data/umh/` files) |
| Beast `C:\dev\dev\OS` mirror | **fast-forwarded `be74ff721` → `fc0a96304`** |
| Beast node-side P0-002 code present | ✓ `substrate/execution/mesh_verdict.py`, `client.py::_validate_verdict`, `config.py::auth_header` + URL-token-free |
| VPS mesh server | **restarted on merged code** — was a stale orphan (PID 714086, started Jun 28, holding :8094/:8095, spawned by a stray Claude shell nohup) + a parallel systemd instance. Orphan killed; canonical `umh-mesh.service` restarted → **PID 2395889, started 2026-07-04 08:26:55**, owns :8094/:8095. |
| Beast mesh node daemon | **restarted** via documented path — Task Scheduler `\UMH_NodeDaemon` (`python launcher.py`, Session 1 ONLOGON): `schtasks /end` → `/run`. Status: Running. |

## Daemon restart method

- **VPS mesh server:** `systemctl stop umh-mesh` → kill stale orphan holding the ports → `systemctl restart umh-mesh` (canonical systemd unit `/etc/systemd/system/umh-mesh.service`, `Restart=always`). This is a **host process**, not Docker — Docker restart does not touch it.
- **Beast node daemon:** `schtasks /end /tn "\UMH_NodeDaemon"` → `schtasks /run /tn "\UMH_NodeDaemon"` — keeps the daemon in interactive Session 1 per the browser-verification law.

## Live full-stack handshake — ACHIEVED on merged code

Server log (`journalctl -u umh-mesh`, 2026-07-04 08:27), Beast daemon connecting to the freshly-restarted merged server:

```
08:27:36 [transports.node_mesh.registry] node registered: windows-desktop (windows DESKTOP-LVGUIQ9)
08:27:36 [transports.node_mesh.server]   node connected: windows-desktop (windows DESKTOP-LVGUIQ9, 21 peripherals)
08:27:36 [substrate.sockets.capability_socket] capability handler registered: node-windows-desktop (7 capabilities)
```

The Beast node authenticated and registered end-to-end on merged code — the WS header-auth path works live.

## Validation results

| # | Behavior | Method | Result |
|---|---|---|---|
| 1 | Confirm main ≥ fc0a96304 | git | **PASS** |
| 2 | Pull main on VPS | ff-only | **PASS** (→ fc0a96304) |
| 3 | Pull main to Beast mirror | ff-only | **PASS** (→ fc0a96304) |
| 4 | Restart Beast mesh daemon (safe path) | Task Scheduler end/run | **PASS** (Running; node connected) |
| 5 | Node connects via `Authorization` header, not URL | deployed `config.py` (`ws_url` token-free + `auth_header` bearer) + live WS connect | **PASS** — node registered over header-auth WS; no token in URL in deployed code |
| 6 | Node identity binding | live registry: `node registered: windows-desktop` (bound id, not arbitrary) | **PASS** |
| 7 | Token-for-node-A cannot register as node-B | deployed `mesh_verdict.verify_verdict` on Beast: token bound to `windows-desktop` rejected for `vps` (`reject other-node: True`); server `_handle_hello` binding check (unit + Linux-live 3/3 pre-merge) | **PASS** (verdict-binding live on deployed Beast code; WS hello-binding proven pre-merge) |
| 8 | Write-class without verdict rejected node-side | deployed `mesh_verdict.is_write_class` + `client._validate_verdict` (live logic on Beast: write-class classified, no-secret → empty → fail-closed) | **PASS (logic)** — see §Blocker for full-dispatch confirmation |
| 9 | Write-class with valid verdict proceeds | requires provisioned verdict secret on both ends | **BLOCKED** — secret unprovisioned (see below) |
| 10 | Risk-downgrade attack rejected | deployed `_effective_write_class` (live on Beast: `is_write_class(read_only)=False`, `(reversible_write)=True`) | **PASS (logic)** |
| 11 | Remote terminal write emits verdict/trace | requires provisioned relay + verdict secret to exercise a real dispatch | **BLOCKED** — secret unprovisioned |
| 12 | No fail-open mesh path remains | live server: `/dispatch` → `mesh relay fail-closed: UMH_MESH_RELAY_SECRET unset — refusing request`; `/nodes` + `/health` → **HTTP 401** without auth | **PASS** — server refuses every ungoverned/unauth request live |
| 13 | Mainline P0 gates after Beast sync | on live VPS main: dependency-direction PASS, mesh-firewall PASS, pytest-collection exit 0/15247 PASS, mesh+fail-closed suites 49 passed. `check_ungoverned_mutations --all` exits 1 but **all flags are vendored `saas/node_modules/*.d.ts`** (drizzle-orm/hono/@types-node/zod) — **0 real UMH violations, 0 P0 files flagged** (pre-existing gate-scope gap: node_modules not excluded; independent of Batch 1) | **PASS** (0 P0-relevant violations) |

## Proof artifacts

- Server log excerpt (node handshake + fail-closed refusals): `journalctl -u umh-mesh --since "2026-07-04 08:26"`.
- Live unauth rejections: `GET :8095/nodes` → 401, `GET :8095/health` → 401, `POST :8095/dispatch` → fail-closed refusal.
- Deployed-code verdict proof on Beast: `sign+verify(self)=True`, `reject other-node=True`, `no-secret→get_verdict_secret()=""`, `is_write_class(reversible_write)=True / (read_only)=False`.
- Pre-merge Beast node-side proof (9/9, win32 py3.14.4): `UMH_BATCH1_APPROVAL_READINESS.md`.

## Blocker (deployment-config, not code)

**`UMH_MESH_RELAY_SECRET` and `UMH_MESH_VERDICT_SECRET` are not provisioned** — absent from 1Password (`UMH-Production`), the VPS `umh-mesh.service` environment, and Beast. These are **new secrets introduced by WP-P0-002**; they were never created because the feature is new.

Consequence — and this is the fail-closed design working as intended:
- The server **correctly refuses all remote dispatch** (`fail-closed: UMH_MESH_RELAY_SECRET unset`). No fail-open path.
- Write-class dispatch (items 9, 11) **cannot be exercised end-to-end** until the secret is provisioned on both ends. This is a **deployment-configuration gap, not a code defect** — the merged code is correct and is proven to enforce fail-closed live.
- The node-side security *logic* (items 5–8, 10, 12) is validated live on deployed code and the running server.

**Provisioning is an operator credential decision** (generate the shared secret, store in 1Password `UMH-Production`, inject into `umh-mesh.service` env via `op` and into Beast's node env per the credential-injection law). I have not invented secret values. Recommended next action:
1. Operator authorizes creation of `UMH_MESH_RELAY_SECRET` + `UMH_MESH_VERDICT_SECRET` in 1Password `UMH-Production`.
2. Inject into `umh-mesh.service` (via `op run`/env drop-in) and Beast node env; restart both.
3. Re-run items 9 + 11 for the full write-class dispatch handshake (verdict-signed remote `tmux_send` → trace event).

## Batch 2 clearance

Batch 1 code is **merged and green on main** (all P0 gates PASS; collect-only exit 0 / 15247; fail-closed + auth enforced live on the running mesh server; node handshake achieved on merged code). The two BLOCKED items (9, 11) are **runtime credential provisioning**, not code correctness, and do not gate P1 spine-convergence work.

**Batch 2 (P1 Spine Convergence) is CLEARED to begin** — with one carried operational task: provision the mesh secrets so remote write-class dispatch is functional in production (until then, remote dispatch correctly fails closed and is unavailable, which is safe).
