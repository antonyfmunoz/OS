---
name: tailscale
description: "Use when connecting devices over Tailscale, configuring ACLs, MagicDNS, exit nodes, subnet routes, Funnel/Serve, debugging tailnet connectivity, generating auth keys, or scripting tailscale CLI."
allowed-tools: "Read, Bash, Write, Edit"
version: 1.0
source_url: "https://tailscale.com/kb"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "tailscale 1.80.x"
sdk_version: "tsnet (Go), REST API v2"
speed_category: stable
---

# Tool: tailscale

## What This Tool Does

Tailscale is a zero-config mesh VPN built on WireGuard. It decouples the
**control plane** (key distribution, identity, ACL evaluation, NAT traversal
coordination) from the **data plane** (peer-to-peer WireGuard tunnels between
nodes). Tailscale runs the coordination server; your traffic flows directly
between devices wherever NAT and firewalls allow, falling back to encrypted
DERP relays only when no direct path exists.

Core capabilities:

- **Identity-based mesh networking** — each node authenticates against your
  identity provider (Google, GitHub, Microsoft, Okta, OIDC) and receives a
  stable `100.x.y.z` tailnet IP
- **MagicDNS** — every device gets `<hostname>.<tailnet-name>.ts.net` plus a
  short-name lookup, resolved by `100.100.100.100`
- **ACL-enforced firewall** — default-deny HuJSON policy file with a `tests:`
  block for unit-testing network policy, evaluated at every node
- **Tailscale SSH** — replaces `~/.ssh/authorized_keys` with tailnet identity
  and ACL `ssh` rules
- **Serve & Funnel** — private HTTPS (tailnet-only) or public HTTPS (edge
  terminated at Tailscale) with LetsEncrypt certs auto-provisioned for `*.ts.net`
- **Exit nodes, subnet routers, Taildrop, Tailscale Drive** — egress pinning,
  LAN bridging, file transfer, WebDAV shares

The mental shift Tailscale enables is simple: stop deciding which ports to
expose and which keys to distribute. Instead decide *which devices belong to
your tailnet and what tag they carry*. Everything else follows from policy.

## EOS Integration

Tailscale is the private network layer for every EOS device. The VPS
(`100.77.233.50`) is the hub, and every dev surface reaches it over the tailnet:

- **VPS (`os-vps`)** — primary node, tagged `tag:server`, key expiry
  **disabled** in admin console, Tailscale SSH enabled, services bound to
  `tailscale0` only
- **iPhone (Termius)** — SSH over tailnet from anywhere, no public port 22
- **iPad (Safari + code-server)** — code-server bound to tailnet IP, reached
  via `tailscale serve` on `https://os-vps.<tailnet>.ts.net`
- **Windows VS Code** — Remote-SSH over tailnet via MagicDNS short name
- **Ephemeral agent containers** — tagged `tag:agent`, minted with ephemeral
  auth keys via OAuth client, auto-removed on shutdown

Canonical EOS firewall pattern (UFW):

```bash
sudo ufw default deny incoming
sudo ufw allow in on tailscale0
sudo ufw allow 22/tcp          # temporary — removed once Tailscale SSH is primary
sudo ufw allow 443/tcp         # Discord webhook + marketing only
sudo ufw enable
```

Canonical EOS service bind pattern (never `0.0.0.0`):

```bash
TS_IP=$(tailscale ip -4)
uvicorn services.webhook:app --host $TS_IP --port 8000
```

The tailnet *is* the bastion. Nothing EOS runs is exposed to the public
internet except the Discord webhook and the marketing site. If the VPS
"feels slow," the first diagnostic is always `tailscale netcheck` followed
by `tailscale ping --until-direct vps-prod` to confirm direct vs DERP.

## Authentication

Tailscale supports four distinct authentication paths:

**1. Interactive OAuth login** — `tailscale up` opens a browser, user
authenticates against the tailnet's configured IdP (Google, GitHub,
Microsoft, Apple, Okta, OneLogin, custom OIDC). Used on laptops, phones,
any device with a human in front of it.

**2. Auth keys** (Settings → Keys → Generate auth key). Five orthogonal
axes: `reusable|one-time`, `ephemeral|durable`, `tagged|untagged`,
`preauthorized|requires-approval`, plus an expiry (max 90 days).

- **One-time** — single use, expires after first use
- **Reusable** — enrolls many devices, expires by clock
- **Ephemeral** — node auto-removed when offline (CI runners, scratch containers)
- **Pre-authorized** — bypass admin approval if device approval is enabled
- **Tagged** — automatically applies tags (`tag:server`, `tag:agent`); the
  creator must be listed in `tagOwners` for that tag

Format: `tskey-auth-xxxxxxxxxxxxxxx-yyyyyyyyyyyyyy`

For headless servers the canonical pick is **reusable + durable + tagged +
preauthorized**, expiry as long as possible, minted via OAuth client.

**3. OAuth clients** — programmatic API access for tooling that needs to
mint auth keys, manage devices, or edit ACLs. Scoped (`devices:read`,
`auth_keys`, etc.). The Tailscale Terraform provider and CI pipelines use
this path to mint short-lived ephemeral auth keys at apply time with no
long-lived secrets in state files.

**4. Tailnet lock** — cryptographic signing chain for new nodes. Designated
signing nodes must co-sign any new node before it can decrypt traffic from
existing nodes. Neutralizes the "compromised control plane inserts a
malicious node" attack. `tailscale lock init`, `tailscale lock sign <nodekey>`.

EOS headless bootstrap:

```bash
sudo tailscale up \
  --authkey=tskey-auth-xxxx \
  --hostname=os-vps \
  --advertise-tags=tag:server \
  --ssh \
  --accept-dns=true
```

## Quick Reference

### Bring interface up / down

```bash
sudo tailscale up                                          # interactive
sudo tailscale up --authkey=tskey-auth-xxxx --hostname=os-vps --advertise-tags=tag:server --ssh
sudo tailscale down                                        # disconnect, keep key
sudo tailscale logout                                      # disconnect + invalidate
sudo tailscale up --reset --ssh --hostname=os-vps          # clear sticky flags
```

### State and inspection

```bash
tailscale status                              # peers, IPs, direct/relay
tailscale status --json                       # machine-readable
tailscale status --peers=false                # self only
tailscale ip -4                               # own tailnet IPv4
tailscale ip -4 os-vps                        # peer's IPv4 by MagicDNS name
tailscale version
```

### Connectivity testing

```bash
tailscale ping os-vps                         # ICMP-like over tailnet
tailscale ping --until-direct os-vps          # keep going until direct path
tailscale ping --tsmp os-vps                  # Tailscale protocol (bypasses ICMP block)
tailscale netcheck                            # NAT type, UDP, IPv6, DERP latency
```

### SSH

```bash
tailscale ssh root@os-vps                     # uses tailnet identity, ACL-gated
sudo tailscale up --ssh                       # enable Tailscale SSH server
```

### Serve (private HTTPS, tailnet-only)

```bash
tailscale serve --bg https / http://localhost:3000
# → https://os-vps.<tailnet>.ts.net/ reaches localhost:3000
tailscale serve --bg --https=8443 --set-path=/api http://localhost:8000
tailscale serve status
tailscale serve reset
```

### Funnel (public HTTPS, Tailscale edge)

```bash
tailscale funnel 443 on                       # expose Serve publicly
tailscale funnel --bg --https=8443 http://localhost:8000
tailscale funnel status
tailscale funnel reset
# Allowed public ports: 443, 8443, 10000
```

### Exit nodes

```bash
sudo tailscale up --advertise-exit-node                  # offer this node
tailscale exit-node list                                 # see available
sudo tailscale up --exit-node=os-vps --exit-node-allow-lan-access
sudo tailscale up --exit-node=                           # stop using (empty value)
```

### Subnet routes

```bash
sudo tailscale up --advertise-routes=10.0.0.0/24,192.168.1.0/24
sudo sysctl -w net.ipv4.ip_forward=1
sudo sysctl -w net.ipv6.conf.all.forwarding=1
# Then approve in admin console → Machines → Edit route settings
# Clients accept with --accept-routes (macOS/iOS default on, Linux/Win off)
```

### File transfer (Taildrop)

```bash
tailscale file cp ./report.pdf os-vps:                   # send
tailscale file get --wait /tmp/inbox                     # receive
```

### Certs (LetsEncrypt for *.ts.net)

```bash
tailscale cert os-vps.<tailnet>.ts.net
```

### Debug

```bash
sudo journalctl -u tailscaled -f
tailscale debug daemon-logs
tailscale debug prefs
tailscale debug netmap
tailscale bugreport
```

## Conceptual Model

**Control plane vs data plane.** The Tailscale control server (SaaS at
`controlplane.tailscale.com`, or self-hosted via Headscale) distributes
public keys, identities, ACLs, and NAT-traversal rendezvous information.
It never sees plaintext traffic. Once two nodes learn about each other,
WireGuard packets flow directly peer-to-peer. When direct paths fail —
symmetric NAT, blocked UDP, hostile corporate networks — traffic falls
back to a **DERP relay** (encrypted end-to-end, relayed by Tailscale in
~30 regions). DERP sees only opaque WireGuard packets.

**Identity model.** A **tailnet** is your private network namespace. A
**node** is a device identified by a WireGuard public key and named via
MagicDNS. A **user** is a human authenticated through your IdP. A **tag**
is workload identity for non-human nodes (servers, containers, CI runners)
— ACLs reference tags rather than owners. An **auth key** is a time-bounded
credential to enroll new nodes, optionally pre-tagged.

**ACL evaluation.** The policy file is HuJSON, lives in admin console →
Access Controls, and is **default-deny**. Only listed `src → dst:port` flows
are permitted, and rules are enforced **at each node**, not at a chokepoint.
This is why there is no bottleneck, no firewall box, and no single point of
failure for the data plane.

If you internalize "control plane is the truth, data plane is direct
WireGuard," every Tailscale behavior becomes obvious:
- "MagicDNS resolves but ping fails" → ACL is denying the flow
- "Connection is slow" → data plane is DERP-relayed, not direct
- "Server drops offline after months" → node key expired, should have been disabled

## Gotchas

- **`tailscale up` resets flags by default** → running `tailscale up
  --advertise-routes=...` will silently drop `--ssh` if you don't re-pass it.
  Always re-pass every flag, or use `tailscale set` for incremental changes.
- **Key expiry kills servers at 3am** → default node key expiry is ~180 days.
  Headless servers silently drop offline when the key expires. ALWAYS
  "Disable key expiry" on tagged server nodes in admin console (Machines → ⋯).
- **`--exit-node` without `--exit-node-allow-lan-access`** → all traffic
  including LAN goes through the exit. You lose your printer, NAS, and
  router admin page. Almost nobody knows this flag exists on first use.
- **Malformed ACLs can lock you out** → the admin console rejects invalid
  JSON, but a *valid* ACL that revokes your own access is accepted. Use the
  `tests:` block to assert your own reachability on every save, and keep a
  backup auth method (admin tag on a known-good device).
- **MagicDNS + systemd-resolved fights** → on Linux with NetworkManager,
  dnsmasq, or a custom resolver, Tailscale's attempt to register via
  systemd-resolved can fail silently. Symptom: `tailscale ping device`
  works but `ssh device` fails name resolution. Check `resolvectl status`.
- **DERP mode is slower than you think** → `tailscale status` shows
  `relay "nyc"` instead of `direct` when NAT traversal fails. DERP adds a
  hop (60ms+) and throughput is capped. Run `tailscale netcheck` — if it
  shows `UDP: false`, your outbound firewall is blocking UDP 41641.
- **Auth key axes are five-dimensional** → `reusable × ephemeral × tagged ×
  preauthorized × expiry`. Picking wrong is the #1 source of "why is this
  server stuck waiting for approval" tickets.
- **`tag:*` must be in `tagOwners`** → advertising a tag you don't own
  ("tag not allowed") fails with no clear error. Add to `tagOwners` first.
- **Funnel is not a private tunnel** → Funnel terminates TLS at Tailscale's
  edge. The control plane sees source IPs, byte counts, and target node.
  Use Serve (tailnet-only) unless you need public reachability.
- **Docker sidecar requires userspace mode** → without privileged mode you
  need `--tun=userspace-networking`. Missing this silently breaks reachability.
- **Client version skew** → Ubuntu 22.04 ships older tailscale in some
  mirrors; Drive and ACL grants require 1.64+. `tailscale version` at
  provisioning time. Use `tailscale set --auto-update=true` on non-critical nodes.
- **Corporate VPN + Tailscale conflict** → corporate VPNs that install their
  own default route eat `100.x.x.x`. Symptom: Tailscale works until you
  connect corp VPN, then dies. Fix: corp VPN must be split-tunnel.

See references/best_practices.md for the full 19-section creator-level knowledge base.
