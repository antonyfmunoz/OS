# Tailscale — Creator-Level Best Practices
Source: https://tailscale.com/kb, apenwarr.ca "How NAT traversal works", crawshaw.io
API Version: tailscale 1.80.x (client + tailscaled), control plane API v2
SDK Version: tsnet (Go, in-tree), Tailscale Terraform provider, Kubernetes Operator
Last Researched: 2026-04-06

---

# Tier 1 — Technical Mastery

## Authentication

Tailscale separates three credential types: **user identities**, **node
keys**, and **auth keys**. Understanding which one is failing is most of
debugging.

**User identities** come from the tailnet's configured identity provider:
Google, Microsoft, GitHub, Apple, Okta, OneLogin, or custom OIDC.
Configured at tailnet creation (Settings → General → User management).
Every human action — logging into a device, editing ACLs, minting auth
keys — authenticates against this IdP. There is no Tailscale-local
password. If the IdP is down, new logins break; existing tailnet
connectivity is unaffected because the data plane is peer-to-peer.

**Node keys** are WireGuard public/private keypairs generated locally by
`tailscaled` on first `tailscale up`. The private key never leaves the
device. The public key is uploaded to the control plane, stapled to a
user or tag, and distributed to peers. Node keys rotate automatically
every ~180 days on most tailnets. For servers, **disable key expiry** in
admin console (Machines → ⋯ → Disable key expiry) so they never drop
offline mid-operation.

**Auth keys** are pre-issued credentials for headless enrollment. Five
orthogonal axes:

| Axis | Values | Meaning |
|---|---|---|
| Reuse | `reusable | one-time` | Many devices vs single-use |
| Lifetime | `ephemeral | durable` | Auto-remove on disconnect vs persist |
| Tag | `tagged | untagged` | Pre-applies ACL tags vs needs user ownership |
| Approval | `preauthorized | requires-approval` | Skip admin approval queue |
| Expiry | up to 90 days | Hard upper bound |

Format: `tskey-auth-<id>-<secret>`. Max lifetime 90 days. Created via
admin console (Settings → Keys) or programmatically via OAuth client.

**OAuth clients** (Settings → OAuth clients) are the recommended path
for automation. Scopes include `devices:read`, `devices:write`,
`auth_keys`, `acl`, `dns`, `logs:read`. The Terraform provider, CI
pipelines, and infrastructure scripts use OAuth clients to mint
short-lived auth keys at provisioning time, so long-lived secrets never
sit in AMIs or state files.

**Tailnet lock** is an optional cryptographic signing layer. When
enabled, designated signing nodes must co-sign new node keys before
those nodes can decrypt traffic from existing peers. This neutralizes
"compromised control plane inserts a malicious node" — the highest-trust
attack Tailscale's threat model contemplates. Initialize with
`tailscale lock init`, then sign new nodes with `tailscale lock sign
<nodekey>` from a signing node.

**EOS auth pattern:** personal GitHub SSO for human login, OAuth client
for programmatic auth key minting, tagged preauthorized durable keys for
the VPS, ephemeral tagged keys for agent containers. Key expiry disabled
on the VPS. Tailnet lock not yet enabled (single-user phase) but
laptop+VPS will become signing nodes when tagged production fleet grows.

## Core Operations with Exact Signatures

### `tailscale up` — bring interface online

```
tailscale up [flags]

--authkey=<key>                    non-interactive enrollment (tskey-auth-...)
--hostname=<name>                  device name in admin console
--advertise-routes=<cidr,cidr>     act as subnet router for these CIDRs
--advertise-exit-node              offer this node as an exit node
--advertise-tags=<tag,tag>         apply ACL tags (must be in tagOwners)
--accept-routes                    accept subnet routes from other nodes
--accept-dns=<true|false>          use tailnet MagicDNS resolver
--ssh                              enable Tailscale SSH server on this node
--reset                            clear flags not specified on this invocation
--operator=<user>                  allow non-root user to run tailscale CLI
--shields-up                       block all incoming except explicit ACL
--login-server=<url>               custom control plane (Headscale)
--force-reauth                     re-prompt login even if authed
--auto-update                      enable client auto-updates (1.50+)
--exit-node=<ip-or-name>           route egress through this node
--exit-node-allow-lan-access       keep LAN reachable while exit-noding
--snat-subnet-routes=false         preserve client source IPs over subnet router
--netfilter-mode=<off|nodivert|on> control iptables management
--timeout=<duration>               wait this long for control plane
```

### `tailscale set` — change one flag without resetting others (preferred over `up --reset`)

```
tailscale set --ssh=true
tailscale set --advertise-exit-node=true
tailscale set --auto-update=true
```

### State / inspection

```
tailscale status [--json] [--peers=false] [--self=false] [--active]
tailscale ip [-4|-6] [hostname]
tailscale version
tailscale whois <ip>                            # who owns this tailnet IP
```

### Connectivity testing

```
tailscale ping <target>
  --until-direct                   keep pinging until direct path established
  --tsmp                           use Tailscale's own protocol (bypass ICMP)
  --c=<N>                          count
tailscale netcheck                 NAT type, UDP, IPv6, DERP latency
```

### SSH

```
tailscale ssh <user>@<host>        wrapper that prefers Tailscale SSH
tailscale up --ssh                 enable server on this node
```

### Serve / Funnel

```
tailscale serve [--bg] [--https=443] [--set-path=/api] <target>
tailscale serve status
tailscale serve reset

tailscale funnel <port> on|off
tailscale funnel status
tailscale funnel reset
```

Allowed Funnel public ports: **443, 8443, 10000** (hardcoded).

### File transfer

```
tailscale file cp <file> <host>:
tailscale file get [--wait] [--conflict=skip|overwrite|rename] <dir>
```

### Drive (1.64+)

```
tailscale drive share <name> <path>
tailscale drive list
tailscale drive unshare <name>
```

### Certs

```
tailscale cert <hostname.tailnet.ts.net>
```

Only valid for `*.ts.net` MagicDNS names. Uses LetsEncrypt DNS-01. Cert
+ key written to current working directory.

### Tailnet lock

```
tailscale lock init [--gen-disablement-for=<file>]
tailscale lock sign <nodekey> [<rotation-key>]
tailscale lock status
tailscale lock log
```

### Exit nodes

```
tailscale exit-node list
tailscale up --exit-node=<ip-or-name>
tailscale up --exit-node=                       # stop using (empty value)
```

### Debug

```
tailscale debug daemon-logs                     # stream tailscaled logs
tailscale debug prefs                           # current persisted prefs
tailscale debug netmap                          # current peer map
tailscale debug derp-map                        # configured DERP regions
tailscale debug component-logs                  # toggle subsystem verbosity
tailscale bugreport                             # produce ID for support
```

## Pagination Patterns

The `tailscale` CLI has no pagination — everything returns in one shot,
including `tailscale status` across a 500-node tailnet. At CLI scale,
this is fine. The REST API v2 does paginate for endpoints that list many
resources (devices, keys, logs). The pattern is cursor-based with a
`next` field in the response; clients follow the cursor until `next` is
empty. For scripts, prefer parsing `tailscale status --json` over
scraping human-readable output.

## Rate Limits

**Control plane API:** Tailscale's REST API v2 enforces per-OAuth-client
rate limits. Exact numbers are not published; empirically they are
generous enough that normal automation (Terraform applies, CI
enrollment) never hits them. Burst protection exists for auth-key
minting to prevent automation errors from creating thousands of keys.

**DERP relays:** DERP is intentionally rate-capped so it cannot be used
as a free backbone. Typical per-connection throughput is 100–500 Mbps
and heavy usage can be throttled. If sustained throughput matters, you
need a direct path.

**Funnel bandwidth:** Funnel is metered. On free plans the quota sits in
the tens-of-GB-per-month range (informal, subject to change). Check
admin console → Settings → Funnel for current usage.

**Client `tailscale up` retries:** If the control plane is unreachable,
tailscaled backs off exponentially up to ~1 minute between retries. It
does not give up.

## Error Codes and Recovery

| Symptom | Likely cause | Fix |
|---|---|---|
| `Logged out.` | Key expired or `tailscale logout` ran | `tailscale up` (interactive) or new authkey |
| `not logged in` in `tailscale status` | tailscaled running but not authed | `tailscale up` |
| `key expired` after ~180 days | Node key expiry enabled | Disable key expiry in admin console for servers |
| `tailnet lock is enabled — node key needs signature` | Tailnet lock requires signing new node | `tailscale lock sign <nodekey>` from signing node |
| `control plane unreachable` | Outbound 443 blocked or DNS broken | Check `curl https://controlplane.tailscale.com` |
| `derp: unreachable` | UDP+TCP both blocked outbound | Open 443/tcp; verify proxy doesn't MITM |
| MagicDNS resolves but ping fails | ACL deny | Check admin console → Logs for `denied` |
| `Too many open files` in tailscaled | ulimit too low | Add `LimitNOFILE=65535` to systemd unit override |
| `tailscaled exited unexpectedly` | OOM or crash | `journalctl -u tailscaled`, check `dmesg` |
| Can ping but SSH refused | Tailscale SSH not enabled OR ACL ssh rule missing | `tailscale up --ssh`, add ACL rule |
| Services unreachable after reboot | Bound to tailnet IP before tailscale0 came up | Add `After=tailscaled.service` and `Requires=` |
| `tag not allowed` when minting key | Caller not in `tagOwners` for that tag | Add user/group to tagOwners in policy |
| `exit node not approved` | Node advertises exit but admin hasn't approved | Approve in admin console or use `autoApprovers.exitNode` |
| `UDP: false` in netcheck | Outbound UDP 41641 blocked | Open firewall; otherwise all traffic goes DERP-relayed |

**Recovery principles:**
1. `tailscale status` first — tells you authed state and direct vs relay per peer
2. `tailscale netcheck` second — tells you NAT type, UDP reachability, DERP latency
3. `sudo journalctl -u tailscaled -f` for daemon-level errors
4. Admin console → Logs for ACL denies (reached ingress but deny-listed)

## SDK Idioms

Tailscale ships first-class support for:

**tsnet (Go)** — in-process Tailscale. A Go program imports `tailscale.com/tsnet`,
creates a `tsnet.Server`, calls `.Listen("tcp", ":443")` and its listener is
now on the tailnet with its own node identity. No separate tailscaled
process, no TUN device, no kernel capabilities required. Perfect for a
microservice that should only be reachable on the tailnet. Each tsnet
binary is its own node, consuming one device slot.

```go
import "tailscale.com/tsnet"

s := &tsnet.Server{Hostname: "my-svc", AuthKey: os.Getenv("TS_AUTHKEY")}
defer s.Close()
ln, _ := s.Listen("tcp", ":443")
http.Serve(ln, handler)
```

**Python** — no official SDK. Community wrappers exist but the canonical
idiom is to (a) run tailscaled as a sidecar / system service and (b)
call the REST API directly with `requests` for control-plane operations:

```python
import requests, os
r = requests.get(
    f"https://api.tailscale.com/api/v2/tailnet/-/devices",
    headers={"Authorization": f"Bearer {os.getenv('TS_API_KEY')}"})
```

**Terraform** — `tailscale/tailscale` provider. Canonical use is to
declare ACL policy as HCL, mint auth keys on the fly for new servers,
and manage DNS/tagOwners as code.

**Kubernetes Operator** (2024+) — install the operator, annotate a
`Service` with `tailscale.com/expose: "true"`, and it becomes reachable
on the tailnet. Supports ingress mode (external traffic → tailnet) and
egress mode (tailnet → K8s service).

**Docker** — `tailscale/tailscale` image. Canonical sidecar pattern:
run the tailscale container with `TS_AUTHKEY`, then your app container
uses `network_mode: "service:tailscale"` to share its netns. Inside
unprivileged containers, set `TS_USERSPACE=true` (userspace networking).

## Anti-Patterns

**1. Using `tailscale up` for incremental changes.** `tailscale up`
resets flags by default, silently dropping `--ssh` or `--advertise-tags`
if not re-passed. Use `tailscale set` for single-flag changes.

**2. Leaving node key expiry enabled on servers.** Headless servers
silently drop offline at 3am ~180 days after enrollment. Disable key
expiry per-node in admin console for anything tagged `tag:server`.

**3. Binding services to `0.0.0.0` and relying on a firewall.** EOS
binds to the `tailscale0` IP directly (`uvicorn --host $(tailscale ip
-4)`). This is defense in depth — even if UFW is misconfigured, the
service never listens on the public interface.

**4. Hardcoding auth keys in AMIs or Dockerfiles.** Use OAuth clients to
mint ephemeral keys at provision time. Long-lived auth keys in images
are a credential leak waiting to happen.

**5. Using subnet routes for things you could install Tailscale on.**
Subnet routes enforce ACLs per-subnet, not per-device. A subnet router
is a trust boundary. Install Tailscale directly on every reachable
device for per-device ACLs and direct WireGuard performance.

**6. `tailscale funnel` as a production reverse proxy.** Funnel is for
demos, webhooks, and OAuth callbacks. It terminates TLS at Tailscale's
edge, metadata is visible to the control plane, and bandwidth is
metered. For production public traffic, use Caddy/Traefik on the node.

**7. Running two mesh VPNs at once.** Tailscale + ZeroTier + corporate
VPN will fight over the routing table. Pick one or accept that you must
manually manage default routes.

**8. Ignoring `tailscale status` direct vs relay.** If every peer shows
`relay "<region>"` instead of `direct`, you are silently paying DERP
latency and throughput caps for everything. `tailscale netcheck` will
tell you why (usually UDP blocked).

**9. Editing ACLs in the admin console without using `tests:`.** The
`tests:` block is the one thing standing between you and locking
yourself out of your own tailnet. Use it.

**10. Using Tailscale SSH without the ACL `ssh:` rules.** Enabling
`tailscale up --ssh` without writing `ssh:` rules results in SSH being
either wide open (autogroup:member allowed) or unusable (nobody allowed).
Write explicit rules.

## Data Model

```
tailnet
├── users (authenticated via IdP)
│   └── email, role (owner/admin/member/auditor), mfa status
├── nodes (devices)
│   ├── node_key (WireGuard public key)
│   ├── tailnet_ip (100.x.y.z)
│   ├── magic_dns_name (hostname.tailnet.ts.net)
│   ├── owner (user email OR tag)
│   ├── advertised_routes[]
│   ├── advertised_exit_node (bool)
│   ├── key_expiry (timestamp, disable-able)
│   └── tags[] (if tagged node)
├── groups (logical user sets, defined in ACL)
│   └── members[] — user emails or autogroup:*
├── tags (workload identities)
│   └── owners[] (who may assign this tag)
├── acls[] (rules: src, dst, proto, ports)
├── ssh[] (ssh rules: action accept|check, src, dst, users, checkPeriod)
├── nodeAttrs[] (per-target feature flags: funnel, etc.)
├── hosts{} (stable name → IP map for ACL references)
├── autoApprovers (routes, exitNode)
└── tests[] (assertions on acl evaluation)
```

**Autogroups** (predefined groups):
- `autogroup:admin` — tailnet admins
- `autogroup:member` — any authenticated user
- `autogroup:owner` — tailnet owner
- `autogroup:tagged` — any node with a tag
- `autogroup:self` — reflexive (user accessing their own devices)
- `autogroup:internet` — the public internet (used with exit nodes)

**Example policy excerpt (EOS-shaped):**

```jsonc
{
  "tagOwners": {
    "tag:server": ["autogroup:admin"],
    "tag:agent":  ["autogroup:admin"]
  },
  "groups": {
    "group:founders": ["antony@munoz.example"]
  },
  "hosts": {
    "vps-prod": "100.77.233.50"
  },
  "acls": [
    { "action": "accept", "src": ["group:founders"], "dst": ["*:*"] },
    { "action": "accept", "src": ["tag:agent"],      "dst": ["vps-prod:443,8000"] }
  ],
  "ssh": [
    { "action": "accept", "src": ["group:founders"], "dst": ["tag:server"],
      "users":  ["root","ubuntu","afm"] }
  ],
  "nodeAttrs": [
    { "target": ["tag:server"], "attr": ["funnel"] }
  ],
  "autoApprovers": {
    "routes":   { "10.0.0.0/24": ["tag:server"] },
    "exitNode": ["tag:server"]
  },
  "tests": [
    { "src": "antony@munoz.example", "accept": ["vps-prod:22"] }
  ]
}
```

## Webhooks and Events

Tailscale supports tailnet webhooks (Settings → Webhooks) for
control-plane events: `nodeCreated`, `nodeDeleted`, `nodeKeyExpired`,
`policyUpdate`, `userApproved`, `userSuspended`, and similar. Delivered
as HTTP POST with an HMAC-SHA256 signature header for verification.
Endpoints must be publicly reachable (including via Funnel). Events
are retried on non-2xx responses.

Use cases:
- Audit trail: stream all tailnet changes to SIEM
- Discord alerting: post a message when `nodeCreated` fires with an
  unexpected tag
- Automation: rotate dependent secrets when `nodeDeleted` fires for a
  server that owned them

EOS does not currently consume Tailscale webhooks. Candidate future use:
Discord alert when a new node enrolls with `tag:server` that wasn't
expected, or when `nodeKeyExpired` fires for any device.

## Limits

**Free (Personal) plan:**
- 100 devices
- 3 users
- Unlimited subnet routes
- Funnel allowed
- Tailscale SSH allowed
- MagicDNS allowed

**Personal Plus** (~$5/mo): 200 devices, 6 users.

**Team / Premium / Enterprise:** per-user pricing, higher device caps,
audit logs, SCIM provisioning, advanced SSO, session recording for SSH,
ACL tests in CI.

**Hard / soft limits:**
- ACL rule count: no published hard cap, soft limit ~10,000 rules
- Subnet routes per node: no hard cap
- Tags per node: no hard cap
- Auth key max expiry: 90 days
- Node key default expiry: ~180 days (configurable, disable-able per node)
- Funnel public ports: 443, 8443, 10000 only
- DERP regions: ~30 globally
- MTU default: 1280 (conservative, raisable to 1420 for LANs)

**EOS is well inside the free tier:** ~5 devices, 1 user. No plan
upgrade pressure until either (a) a co-founder joins (second user) or
(b) ephemeral CI enrollment starts churning the device count.

## Cost Model

Tailscale pricing is per-user, not per-device (changed from per-device in
2024, controversial for homelabbers but friendlier for businesses).

| Plan | Price | Users | Devices | Notable features |
|---|---|---|---|---|
| Personal | Free | 3 | 100 | Everything needed for solo founder |
| Personal Plus | ~$5/mo flat | 6 | 200 | Same features, more headroom |
| Starter | per-user | — | — | Team features start here |
| Premium | per-user | — | — | SSO, audit logs, session recording |
| Enterprise | per-user | — | — | SCIM, dedicated support, compliance |

**EOS current cost:** $0/mo. Stays $0/mo until co-founder joins, at
which point Personal Plus ($5/mo) covers 6 users. Beyond that, Starter
per-user pricing applies.

**Hidden costs:**
- Funnel bandwidth is metered; quota consumption beyond free tier
  triggers a plan upgrade
- Mullvad exit nodes (if used) are an addon subscription
- No cost for control plane API calls; OAuth clients are free

## Version Pinning

Tailscale has **no LTS**. Continuous release, roughly every 2–4 weeks.
Client and daemon ship in the same binary — always the same version.

Verify:
```bash
tailscale version
apt-cache policy tailscale
```

Release notes: https://tailscale.com/changelog

**Capability floors by version:**
- 1.40+ — basic Serve, Tailscale SSH GA
- 1.50+ — `tailscale set --auto-update=true`
- 1.52+ — Funnel GA
- 1.64+ — Tailscale Drive (WebDAV shares)
- 1.70+ — ACL grants (newer grammar alternative to acls+ssh+nodeAttrs)
- 1.80+ — current stable line as of 2026-04

**Auto-update**: `tailscale set --auto-update=true` is safe for most
nodes. For the VPS and anything that hosts production traffic, pin
manually and update during maintenance windows. The client/daemon share
a binary so updating requires a daemon restart; connections briefly
drop.

**EOS version strategy:** auto-update on laptops and phones (zero-risk),
manual update on VPS during the nightly maintenance window, ephemeral
agent containers always pull the latest image at spawn time.

---

# Tier 2 — Creator Intelligence

## Design Intent and Tradeoffs

Tailscale was founded in 2019 by **Avery Pennarun** (apenwarr — sshuttle,
bup), **David Crawshaw** (Go team, runtime engineer), **Brad Fitzpatrick**
(memcached, LiveJournal, Go net stack), and **David Carney**. That
lineage matters: these are systems people who personally suffered
through every form of NAT, every corporate VPN, and every "just works"
network promise of the last two decades. Tailscale is the network they
wished existed at 2am debugging sessions.

The founding insight, stated bluntly in Crawshaw's writing and
Pennarun's canonical "How NAT traversal works" essay (apenwarr.ca, 2020):

**WireGuard solved the cryptography. It did not solve the networking.**

WireGuard ships a tiny, auditable, fast crypto tunnel. But to use it
across a real fleet, you need four additional hard things WireGuard
punts on:

1. **Key distribution** — every node needs every other node's key,
   rotation is a config-management nightmare
2. **NAT traversal** — most devices live behind CGNAT, corporate
   firewalls, or hotel wifi; "just open a port" has been wrong since 2010
3. **Identity** — who is allowed on the network, and how do humans
   authenticate without LDAP
4. **Discovery / naming** — IPs churn, DHCP shuffles things, and
   `192.168.1.47` is not a useful contact address

Tailscale's bet: **centralize the coordination plane, decentralize the
data plane.** A control server (Tailscale's SaaS, or self-hosted via
Headscale) handles identity, key exchange, ACL distribution, and
NAT-traversal rendezvous. Once two nodes know about each other,
WireGuard packets flow directly peer-to-peer. When they cannot
(symmetric NAT, hostile firewalls), traffic falls back to a **DERP
relay** — an encrypted end-to-end TCP relay Tailscale runs in ~30
regions. DERP never sees plaintext; it is a packet shuttle, not a
man-in-the-middle.

**Versus alternatives:**

- **OpenVPN / IPsec gateway VPN:** hub-and-spoke, all traffic through
  one box, terrible latency, SPOF, bottleneck
- **ZeroTier, Nebula:** closer architecturally, but Tailscale's polish
  on identity (SSO out of the box) and UX (`tailscale up` and you're
  done) is the moat
- **Cloudflare Zero Trust / Access:** reverse proxy at Cloudflare's
  edge, every request hairpins through a Cloudflare POP — great for
  HTTP, awkward for arbitrary TCP/UDP, and gives Cloudflare visibility

**What Tailscale deliberately is not:**

- **Not a privacy VPN.** The control plane sees metadata: which IPs you
  log in from, when nodes come online, who is in your tailnet. Tailscale
  is honest about this. For privacy from the network operator, run
  Headscale.
- **Not a gateway firewall.** ACLs are enforced *at each node*, not at
  a chokepoint. No traffic inspection, no DPI, no logging proxy.
- **Not zero-knowledge.** The control plane could in principle
  introduce a malicious node — which is exactly what **tailnet lock**
  was built to prevent.
- **Not a replacement for application auth.** Tailscale gives you a
  network-level identity layer; your app should still know who its users
  are.

The deepest tradeoff: **Tailscale chose ergonomics over ideological
purity.** Self-hosted absolutists hate that the default control plane is
SaaS. Everyone else gets a working mesh in five minutes. Crawshaw has
been explicit on his blog that this was a deliberate, eyes-open call: the
marginal user does not want to operate a coordination server, and the
security model survives that choice.

## Problem-Solution Map and Hidden Capabilities

Most users discover `tailscale up` and MagicDNS and stop there. The
interesting surface area is downstream:

**Tailscale SSH** — the killer feature nobody talks about loudly enough.
Delete `~/.ssh/authorized_keys` from your servers, set `--ssh` on
tailscaled, write an ACL rule:
```json
"ssh": [{"action": "accept", "src": ["autogroup:member"],
         "dst": ["tag:prod"], "users": ["root","ubuntu"]}]
```
SSH now uses tailnet identity. No key distribution. No "which laptop did
I authorize." Revocation is one ACL change. This is categorically
different from OpenSSH key management.

**Tailscale Serve** — `tailscale serve https / http://localhost:3000`
and your local dev server is at `https://laptop.tailnet.ts.net` with a
real LetsEncrypt cert, only to your tailnet. Replaces ngrok for internal
sharing with zero config and no public exposure.

**Tailscale Funnel** — the rare-knowledge feature. `tailscale funnel 443
on` exposes a Serve endpoint to the public internet, terminating TLS at
Tailscale's edge and tunneling to your node. Cloudflare Tunnel's
competitor. Most Tailscale users have no idea it exists. Caveat: control
plane sees metadata; TLS terminates at Tailscale's edge. Use for
webhooks, public demos, and "I need a real URL for this OAuth callback."

**Taildrop / Tailscale Drive** — file transfer with no shared cloud.
Drive (1.64+) adds persistent WebDAV shares.

**Tailnet lock** — cryptographic co-signing of new nodes. Neutralizes
the "compromised control plane inserts a node" attack. Almost nobody
enables it, and almost everybody running prod tagged servers should
consider it.

**ACL tests** — inside the policy JSON you can declare assertions:
"user X SHOULD be able to reach tag:prod on port 22," "user Y SHOULD
NOT." The admin console runs them on every save. Unit tests for your
network policy. Underused.

**autoApprovers** — declare in policy that a given user/tag is
pre-approved to advertise specific subnet routes or exit-node status, so
you don't click "approve" in admin console every time a server reboots.

**Ephemeral nodes** — auth keys marked ephemeral. Node disappears from
the tailnet on disconnect. Perfect for CI runners and scratch containers.

**Tagged devices** — servers don't have a human owner. Tag them
(`tag:prod`) and ACLs reference the tag. Foundation of "workload
identity."

**OAuth clients** — programmatic auth-key creation. Terraform, CI, IaC
pipelines mint short-lived ephemeral auth keys without storing long-lived
secrets.

**Split DNS** — route `*.internal.example.com` through one node's
resolver, everything else through normal DNS. Critical for hybrid cloud.

**nodeAttrs** — attach arbitrary attributes to nodes/users in the policy
file. Used to gate Funnel, Serve, exit-node permission. Feature flags at
the network identity layer.

**Userspace networking mode** (`TS_USERSPACE=true` or
`--tun=userspace-networking`) — runs Tailscale entirely in userspace
with no kernel TUN device. Essential for containers and unprivileged
pods.

**Subnet routing** — `--advertise-routes=10.0.0.0/24` and the LAN
behind you is reachable from the tailnet. Poor-man's site-to-site VPN,
except it actually works.

**`tailscale cert`** — fetches a real LetsEncrypt cert for
`device.tailnet.ts.net`. Real HTTPS on a private network without any
DNS-01 plumbing of your own.

## Operational Behavior and Edge Cases

**Direct vs DERP matters more than you think.** Direct WireGuard is
line-speed and ~RTT latency. DERP adds a hop to the nearest relay
(could be 60ms) and throughput is capped. `tailscale status` shows
which mode each peer is in. If you see `relay "nyc"` instead of
`direct`, investigate — usually symmetric NAT or a firewall stripping
UDP 41641.

**CGNAT and carrier networks.** Mobile carriers often run symmetric
CGNAT, defeating UDP hole-punching. Tailscale's PMP/PCP/UPnP + STUN +
DERP fallback handles it gracefully, but expect DERP-mode performance
on cellular uplinks.

**The 180-day key expiry gotcha.** Default node key expiry is ~180
days. When a server's key expires, it silently stops being reachable
from the tailnet, and re-authing a headless server is annoying. Always
disable key expiry on tagged server nodes. This has bitten everyone.

**MagicDNS vs systemd-resolved.** On Linux with NetworkManager,
dnsmasq, or a custom resolver, expect a fight. Symptom: `tailscale ping
device` works but `ssh device` doesn't resolve. Check
`resolvectl status` for the `tailscale0` link.

**`tailscale up` is a full reset of flags by default.** Run `tailscale
up --advertise-routes=...` and you lose `--ssh`. Use `tailscale set` or
re-pass every flag every time.

**Policy JSON is strict and you can lock yourself out.** A malformed
ACL is rejected by the admin console; a valid ACL that revokes your own
access is accepted. Use `tests:` block to assert your own access, keep
a backup auth method.

**DERP region rotation.** Long-lived TCP connections through DERP can
move regions if Tailscale rotates. Most apps reconnect fine. Apps that
hold persistent TCP and don't reconnect (some Postgres clients) can
hiccup.

**Sleep/resume.** Tailscale reconnects in 1–3 seconds on laptop wake.
iOS is more conservative to save battery — first few seconds after
wake may route through DERP before direct path is re-established.

**Double-NAT and IPv6.** If you have both, Tailscale strongly prefers
IPv6 direct connections — often better performance than IPv4 on the
same network. Leave IPv6 enabled.

**Funnel privacy caveat.** Funnel terminates TLS at Tailscale's edge.
The control plane sees connection metadata (source IPs, byte counts,
target node). Not equivalent to a self-hosted reverse proxy.

**Auth key types are 5-dimensional.** `reusable | one-time`,
`ephemeral | durable`, `tagged | untagged`, `preauthorized |
requires-approval`, expiry. Wrong combination is the #1 source of "why
is this server stuck waiting for approval" tickets.

**`--exit-node-allow-lan-access`** — by default, setting an exit node
routes *all* traffic through it, including LAN. You lose printer, NAS,
router admin page. This flag re-enables LAN access. Almost nobody knows
it exists on first use.

## Ecosystem Position and Composition

**Versus alternatives:**

- **Raw WireGuard:** faster to set up than people think, but you own
  key distribution, NAT traversal, and identity. Fine for two static
  servers, nightmare for a fleet with laptops and phones.
- **OpenVPN / IPsec:** legacy. Hub-and-spoke. Use only when forced.
- **ZeroTier:** closest peer architecturally. Tailscale wins on
  identity (SSO out of the box), polish, and SSH/Serve/Funnel features.
  ZeroTier has a more permissive license.
- **Nebula (Slack):** self-hosted from day one, certificate-based,
  no SaaS option. Better for ideological refusal of SaaS. Less ergonomic.
- **Twingate:** app-layer ZTNA, closer to Cloudflare Access. Resource-
  based access, not network-based.
- **Cloudflare Zero Trust:** closest commercial competitor. Bigger
  edge, generous free tier, but every request hairpins through
  Cloudflare and the model is HTTP-first. Tailscale is protocol-agnostic
  and direct.
- **Headscale:** open-source reimplementation of the control plane.
  Feature-incomplete (limited Funnel, limited SSH historically), but
  fully self-hostable. Tailscale tolerates it; the community maintains it.
- **NetBird:** BSL-licensed, Kubernetes-native OSS challenger gaining
  mindshare.

**Composition patterns:**

- **Tailscale + Docker:** sidecar container with shared netns. Userspace
  mode inside unprivileged containers.
- **Tailscale + Kubernetes:** Tailscale Operator (2024+) annotates
  Services with `tailscale.com/expose: "true"` for tailnet-only exposure.
  Cleanest way to do "private services" in K8s without NetworkPolicy maze.
- **Tailscale + systemd:** `tailscaled.service` + `tailscale up` in
  cloud-init. Standard.
- **Tailscale + SSH:** replaces `~/.ssh/authorized_keys` entirely.
  Combined with `ufw deny 22 && ufw allow in on tailscale0`, public SSH
  is deleted.
- **Tailscale + Caddy/Traefik:** Caddy has a native Tailscale plugin
  (`tailscale_auth`). Traefik binds to tailnet IP.
- **Tailscale + homelab:** subnet router pattern lets one always-on box
  bridge the entire LAN. Every tailnet device reaches `192.168.1.x`
  without installing Tailscale on every device.
- **Tailscale + cloud VPCs:** subnet routing as poor-man's VPC peering.
  One Tailscale node per VPC advertising the CIDR.
- **Tailscale + solo dev (the EOS pattern):** laptop, VPS, phone, iPad
  all on one tailnet. SSH to VPS via tailnet name. Code-server reachable
  only from tailnet. Zero public ports.

**What composes badly:**

- Corporate VPNs running alongside Tailscale fight over the routing
  table. `100.x.x.x` becomes unreachable when corp VPN connects. Fix:
  split-tunnel the corp VPN.
- Aggressive EDR/antivirus sometimes blocks WireGuard or flags TUN as
  suspicious.
- Multiple default-route sources (Tailscale exit + WireGuard + corp VPN)
  — pick one.

## Trajectory and Evolution

Verified milestones (through May 2025):

- **2019** — Tailscale founded
- **2020** — Brad Fitzpatrick joins. Pennarun's NAT traversal essay.
- **2021** — Series A. MagicDNS GA. iOS/Android polished.
- **2022** — Tailscale SSH GA. ACL tests. Series B.
- **2023** — Funnel GA. Mullvad exit nodes partnership. Tailnet lock preview.
- **2024** — Tailscale Drive. Kubernetes Operator matures. Per-user
  pricing (controversial — hurt some homelabbers, helped many businesses).
  SSH session recording for enterprise.
- **Through May 2025** — continued investment in operator, ACL
  ergonomics, enterprise features (SCIM, advanced SSO).

**Projected trajectory (not verified):**

- Continued push toward "network identity layer" framing — Tailscale
  wants to own workload identity the way Okta owns user identity
- More enterprise zero-trust: posture checks, device attestation,
  deeper SSO/SCIM
- ACL DSL improvements (the JSON syntax is widely complained about; a
  schema or Terraform-style DSL would not be a surprise)
- Funnel matures as a Cloudflare Tunnel alternative for OAuth callbacks
  and webhooks
- Kubernetes Operator becomes the default way to expose private K8s
  services
- Acquisition risk: well-funded, strong revenue growth. Could IPO, get
  acquired (Cloudflare is the obvious fit but has competing product), or
  stay independent. Founder personalities suggest independence.
- Competition: NetBird (OSS) and Cloudflare Zero Trust (commercial) are
  the most credible challengers.

## Conceptual Model and Solution Recipes

**Mental model:** Every device on your tailnet has a stable, unique,
globally-routable-to-you `100.x.y.z` IP and a memorable
`device.tailnet-name.ts.net` hostname. Authentication happens *once*,
at the network layer, against your identity provider. After that, every
protocol — SSH, HTTP, Postgres, Redis, anything — just works as if you
were on the same LAN. You stop thinking about "is this port exposed" and
start thinking about "is this node tagged correctly and does my ACL
allow it."

**The primitives:**
- **Tailnet** — your private network namespace
- **Node** — a device, identified by a key, named via MagicDNS, optionally tagged
- **User** — a human authenticated via IdP
- **Tag** — workload identity for non-human nodes
- **ACL rule** — declarative `src → dst:port` permission
- **Auth key** — time-bounded credential to enroll nodes, optionally pre-tagged

**Recipe A — Solo founder setup (the EOS pattern)**

1. Sign up for Tailscale with GitHub SSO.
2. Install on VPS:
   ```bash
   curl -fsSL https://tailscale.com/install.sh | sh
   sudo tailscale up --ssh --hostname=os-vps
   ```
3. Install on laptop, phone, iPad. Log in with same GitHub account.
4. Enable MagicDNS in admin console.
5. `ssh root@os-vps` from the laptop — Tailscale SSH, no key needed.
6. `sudo ufw allow in on tailscale0 && sudo ufw deny 22` — public SSH gone.
7. Admin console → disable key expiry on the VPS node.
8. Optional: enable tailnet lock with the laptop as a signing node.

**Recipe B — Tagged server fleet with ACL lockdown**

```jsonc
{
  "tagOwners": {
    "tag:prod": ["autogroup:admin"],
    "tag:ci":   ["autogroup:admin"]
  },
  "acls": [
    { "action": "accept", "src": ["autogroup:member"], "dst": ["tag:prod:22"] },
    { "action": "accept", "src": ["tag:ci"],           "dst": ["tag:prod:443"] }
  ],
  "ssh": [
    { "action": "accept", "src": ["autogroup:member"],
      "dst": ["tag:prod"], "users": ["root","ubuntu"] }
  ],
  "tests": [
    { "src": "alice@example.com", "accept": ["tag:prod:22"] },
    { "src": "tag:ci",            "deny":   ["tag:prod:22"] }
  ]
}
```
CI nodes mint ephemeral auth keys via OAuth client, run jobs, vanish.

**Recipe C — Expose a dev service via Funnel**

```bash
tailscale serve --bg https / http://localhost:3000
tailscale funnel 443 on
# Now reachable at https://laptop.<tailnet>.ts.net from the public internet
# LetsEncrypt cert, only while you have it on. Turn off when done.
```

**Recipe D — Internal dashboard behind tailnet**

- Grafana, Prometheus, Postgres bound to `100.x.y.z` only, not `0.0.0.0`
- `tailscale cert` for LetsEncrypt certs on `*.ts.net` names
- Access from any tailnet device. No reverse proxy. No public exposure.

**Recipe E — Headless server bootstrap with OAuth**

```bash
# In provisioning script:
KEY=$(curl -s -u "$OAUTH_CLIENT:$OAUTH_SECRET" \
  -X POST https://api.tailscale.com/api/v2/tailnet/-/keys \
  -d '{"capabilities":{"devices":{"create":{
    "reusable":true,"ephemeral":false,"preauthorized":true,
    "tags":["tag:prod"]}}}}' | jq -r .key)

sudo tailscale up --authkey=$KEY --advertise-tags=tag:prod --ssh --hostname=$NAME
```
No long-lived secrets in the AMI.

**Recipe F — Subnet router for a remote LAN**

```bash
sudo tailscale up --advertise-routes=192.168.1.0/24 --accept-routes
sudo sysctl -w net.ipv4.ip_forward=1
# Approve in admin console or use autoApprovers.routes
```

**Recipe G — Kill public SSH permanently**

```bash
sudo tailscale up --ssh
sudo ufw allow in on tailscale0 to any port 22
sudo ufw deny 22
```
Delete `~/.ssh/authorized_keys`. Port 22 scanners see nothing. Access is
governed by your ACL, not `authorized_keys`.

## Industry Expert and Cutting-Edge Usage

The frontier in 2024–2026:

**No-public-endpoint SaaS backends.** Founders running entire production
stacks where the only public-internet thing is the marketing site and a
Funnel-exposed webhook receiver. App servers, database, Redis,
observability — all tailnet-only. Attack surface collapses to "did
someone steal a tailnet identity," governed by IdP MFA. This is the EOS
pattern and it is becoming common among solo and small-team founders.

**AI agents over Tailscale.** Local LLMs (Ollama, llama.cpp) on a beefy
home box, exposed to a laptop via `tailscale serve`. Claude Code or
other agentic tools on a VPS, developer attaching from anywhere via
Tailscale SSH. The "my AI workspace follows me" pattern. EOS is an
example: Discord bot + agent stack on a VPS, accessed from
laptop/phone/iPad over Tailscale, no public exposure beyond the Discord
webhook.

**Homelab renaissance.** NAS, Plex, Home Assistant, pi-hole, Frigate NVR
on tailnet. The self-hosted-everything movement leans hard on Tailscale
because it makes "access my stuff from outside my house" trivial without
exposing anything.

**Tailscale as identity plane.** Tag a node → tag becomes workload
identity → ACL rules govern what that workload can reach → audit logs
show every connection. Zero trust actually delivered, not just sold.

**Infrastructure as Code with OAuth clients.** Tailscale Terraform
provider mints ephemeral auth keys at apply time, enrolls new servers
before the first userdata script finishes. No secrets in state files.

**37signals "Leaving the cloud" pattern.** Bare-metal-on-Hetzner
movement relies on a mesh VPN to make dedicated servers feel like a
cohesive private network. Tailscale is the default choice. Combined
with Kamal (37signals' deploy tool), a serious cloud alternative.

**Funnel replacing Cloudflare Tunnel** for specific workflows.
Cloudflare Tunnel is HTTP-shaped and tied to Cloudflare DNS. Funnel is
more general and integrates with the identity layer you already use.
Practitioners mix: Funnel for OAuth callbacks and webhooks, Cloudflare
for the public marketing site.

**Ephemeral CI runners.** GitHub Actions self-hosted runners enrolled
with ephemeral Tailscale auth keys. Runner appears, runs a job needing
private infrastructure access, disconnects, vanishes. Way cleaner than
punching holes for GitHub's IP ranges.

**Containerized app + Tailscale sidecar** as canonical Docker pattern.
Tailscale container handles networking, app container shares netns,
app code doesn't know Tailscale exists.

**AI pair programming over the tailnet.** Developer in Portland, agent
on a VPS elsewhere, attached over Tailscale, editing files in real time.
No exposed ports. No bastion host. The tailnet *is* the bastion.

**Quotable practitioners:**
- **Avery Pennarun / apenwarr** — "How NAT traversal works" is the
  foundation essay
- **David Crawshaw** — crawshaw.io essays on design rationale
- **Xe Iaso** — Tailscale staff blog + personal blog, excellent for
  cutting-edge usage and homelab integration
- **DHH / 37signals** — public posts on leaving the cloud reference
  Tailscale explicitly

---

## EOS Usage Patterns

**Devices on tailnet:** VPS (`os-vps`, 100.77.233.50), Windows dev box,
iPhone (Termius), iPad (Safari code-server), laptop.

**Tags:** `tag:server` for VPS, `tag:agent` for ephemeral containers
(planned). Both owned by `autogroup:admin` (single-user tailnet).

**Key expiry:** Disabled on VPS. Default (~180 days) on personal devices.

**Tailscale SSH:** Enabled on VPS. `~/.ssh/authorized_keys` still exists
as a fallback during the transition but should be removed once ACL ssh
rules are written and tested.

**Serve usage:**
- `code-server` → `https://os-vps.<tailnet>.ts.net` for iPad development
- `os-monitor` dashboard bound to tailnet IP only

**Funnel usage:** none currently. Candidate future use: Discord OAuth
callback during bot dev.

**Firewall pattern (VPS):**
```bash
sudo ufw default deny incoming
sudo ufw allow in on tailscale0
sudo ufw allow 22/tcp     # transitional
sudo ufw allow 443/tcp    # Discord webhook + marketing
sudo ufw enable
```

**Service bind pattern:** every EOS service binds to `$(tailscale ip
-4)`, never `0.0.0.0`. The `os-discord`, `os-bot`, `os-monitor`, and
`os-webhook` containers follow this rule. Webhook is the only one that
additionally listens on the public interface (needed by Discord).

**Diagnostic routine when "the VPS feels slow":**
1. `tailscale status` — check for `relay` instead of `direct`
2. `tailscale netcheck` — check UDP reachability and DERP latency
3. `tailscale ping --until-direct vps-prod` — force direct path attempt
4. `sudo journalctl -u tailscaled -n 200` — daemon-level errors

**Pending improvements:**
- Enable tailnet lock with laptop + VPS as signing nodes
- Write ACL `tests:` block to assert founder SSH access
- Remove public port 22 rule once Tailscale SSH is fully trusted
- Add Discord webhook consumer for `nodeCreated` / `nodeKeyExpired`
- Move ephemeral agent containers to OAuth-minted ephemeral auth keys

## Gotchas

### `tailscale up` resets flags silently
Running `tailscale up --advertise-routes=...` drops `--ssh` if you don't
re-pass it. Use `tailscale set` for incremental changes, or always pass
every flag. `--reset` makes the reset behavior explicit rather than
implicit. This has caused EOS-adjacent outages in other projects —
"SSH stopped working after I added a subnet route" is the classic symptom.

### Node key expiry drops servers at 3am
Default ~180-day node key expiry means a headless server silently stops
being reachable from the tailnet one night, six months after enrollment.
The fix is "Disable key expiry" per-node in admin console (Machines →
⋯). Do this the moment you tag a node `tag:server`.

### `--exit-node` without `--exit-node-allow-lan-access`
Routes all traffic, including LAN, through the exit node. You lose
printer, NAS, router admin page. Almost nobody knows the flag exists on
first use. Add it to any exit-node command in EOS scripts.

### Locking yourself out of your own tailnet
Admin console rejects malformed ACLs but accepts valid ACLs that revoke
your access. Always include a `tests:` assertion for your own reachability:
```json
"tests": [{"src": "antony@munoz.example", "accept": ["vps-prod:22"]}]
```

### MagicDNS fights with systemd-resolved
On Linux with NetworkManager, dnsmasq, or custom resolvers, `tailscale
ping device` works but `ssh device` fails name resolution. Check
`resolvectl status` for a `tailscale0` link. If missing, use
`--accept-dns=false` and resolve manually, or fix systemd-resolved.

### `UDP: false` in `tailscale netcheck` means DERP-only
Outbound UDP 41641 is blocked. All tailnet traffic is DERP-relayed,
which is encrypted but slow and capped. Open UDP outbound on firewall.

### `tag:*` must be in `tagOwners` before advertising
Minting a tagged auth key for a tag that isn't in `tagOwners` fails
with "tag not allowed" and no clear fix. Always add the tag to
`tagOwners` in policy first.

### Docker sidecar without userspace mode
Inside unprivileged containers, omitting `TS_USERSPACE=true` (or
`--tun=userspace-networking`) breaks reachability silently. The daemon
starts but the TUN device can't be created.

### Funnel is not zero-knowledge
Funnel terminates TLS at Tailscale's edge. The control plane sees
source IPs, byte counts, and target node. Use Serve (tailnet-only)
unless public reachability is required.

### Corporate VPN eats `100.x.x.x`
Corporate VPNs installing their own default route make the tailnet
unreachable. Split-tunnel the corp VPN or accept the exclusive choice.

### `crontab`-style surprise: `tailscale up --authkey=...` is idempotent but flags reset
Re-running `tailscale up` with a new authkey is fine; re-running it
without all your previous flags silently drops them. This is the same
footgun as `tailscale up` resetting flags, but worth calling out
separately because automation scripts hit it constantly.

### IPv6 sometimes preferred when you didn't expect
If both IPv4 and IPv6 are available, Tailscale prefers v6 for direct
connections, even when the v4 path would work. This is usually good
(often better perf) but surprising when debugging.

### Ephemeral nodes disappear faster than you think
Ephemeral key disconnect grace period is short (minutes). A CI runner
that pauses for a long step can lose its tailnet identity mid-job. For
CI runners that run longer than ~15 minutes, use durable + tagged keys
with a short expiry instead of ephemeral.

### `tailscale serve` state persists across reboots
`tailscale serve --bg` config is persisted and re-applied on reboot.
This is usually desired but can surprise you if you forgot a serve
config from a previous experiment. `tailscale serve reset` clears it.

### Mixing `--netfilter-mode=off` with UFW double-writes rules
If you set `--netfilter-mode=off` to manage iptables manually but still
run UFW, you get two systems fighting over the same chains. Pick one:
either let Tailscale manage its chains (default) and use UFW for
everything else, or go fully manual.
