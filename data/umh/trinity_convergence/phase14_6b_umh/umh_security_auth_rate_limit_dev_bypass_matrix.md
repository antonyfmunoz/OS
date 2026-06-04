# UMH Security, Auth, Rate Limiting, and Dev Bypass Matrix

Phase: 14.6B-UMH | Status: DRAFT | Provenance: CODE_RESOLVED_CURRENT_TRUTH

---

## Authentication Mechanisms

### Cockpit API (transports/api/cockpit.py)

| Mechanism | Header | Validation | Status |
|-----------|--------|------------|--------|
| API Key | X-API-Key | hmac.compare_digest against UMH_OPERATOR_API_KEY | IMPLEMENTED |
| Operator Token | X-Operator-Token | hmac.compare_digest against UMH_OPERATOR_TOKEN | IMPLEMENTED |
| Dev Bypass | (none) | UMH_DEV_BYPASS=true + private IP check | IMPLEMENTED |
| WebSocket | Sec-WebSocket-Protocol: bearer.<token> | Token matches UMH_OPERATOR_API_KEY | IMPLEMENTED |

### Dev Bypass Details

- Enabled: UMH_DEV_BYPASS=true env var
- Private IPs accepted: RFC 1918 (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16) + Tailscale CGNAT (100.64.0.0/10)
- Real IP detection: Reads X-Forwarded-For only from trusted proxies (localhost, Docker bridge)
- Risk: Allows unauthenticated access from any private IP. Acceptable for single-operator VPS, NOT acceptable for multi-user deployment.

### SaaS HTTP Layer (transports/api/http/middleware/)

| Mechanism | Header | Validation | Status |
|-----------|--------|------------|--------|
| API Key | X-API-Key | env-based validation | IMPLEMENTED (TypeScript) |
| Operator Role | X-Operator-Token | env-based validation | IMPLEMENTED (TypeScript) |

### Discord Bot

- Discord bot token in services/.env
- No per-user auth beyond Discord's own user identification
- Guild/channel/user wildcards allow all

## Rate Limiting

### Cockpit API (in-memory)

| Action | Window | Status |
|--------|--------|--------|
| promote | 60 seconds | IMPLEMENTED |
| execute | 30 seconds | IMPLEMENTED |
| approve | 30 seconds | IMPLEMENTED |

Limitation: In-memory -- resets on container restart. No persistence.

### Agent Runtime (adapters/models/agent_runtime.py)

| Limit | Value | Status |
|-------|-------|--------|
| Per minute | 30 calls | IMPLEMENTED |
| Per hour | 500 calls | IMPLEMENTED |

## Database Security

### Neon PostgreSQL

| Feature | Status | Detail |
|---------|--------|--------|
| RLS enabled | YES (SaaS layer) | ROW LEVEL SECURITY enabled + forced on all tenant tables |
| RLS policies | YES | *_isolation policies per table |
| Application role | YES | eos_app role for RLS-enforced access |
| Substrate bypass | CONCERN | Python substrate connects as neondb_owner which has BYPASSRLS |
| SSL | LIKELY | Neon defaults to SSL, but not explicitly verified in connection code |

### SECURITY CONCERN

The Python substrate (substrate/state/storage/db.py) connects as neondb_owner. This role has BYPASSRLS, meaning ALL Row Level Security policies are bypassed. The RLS policies only apply to the eos_app role used by the TypeScript SaaS API.

This means: substrate code can read/write ANY org's data without RLS enforcement.

## Secret Management

| Category | Location | Status |
|----------|----------|--------|
| Bot tokens | services/.env | Plaintext, gitignored |
| API keys | services/.env | Plaintext, gitignored |
| Database URLs | infra/docker/umh.env | Plaintext, gitignored |
| Instagram creds | services/.env | Plaintext, gitignored |
| OAuth tokens | Runtime (proc/environ) | In-memory only |

No encryption at rest. No secret rotation. No vault integration.

## API Authorization

### Endpoint Auth Requirements

| Endpoint Category | API Key | Operator Token | Rate Limited |
|-------------------|---------|----------------|-------------|
| Read endpoints (GET) | YES | NO | NO |
| Mutation endpoints (POST/PATCH/DELETE) | YES | YES | Some |
| WebSocket | Token or dev bypass | NO | NO |
| Approval actions | YES | YES | YES (30s) |
| Execution control | YES | YES | NO (stubs) |

### Instance Context Leak

/api/umh/profile endpoint returns hardcoded:

- name: "Antony F. Munoz"
- org: "Munoz Conglomerate"
- ventures: ["Lyfe Institute", "Empyrean Studio", "Lyfe Spectrum"]

This violates Instance Context Law. Should load from BIS at runtime.

## Gaps and Recommendations

### P0 -- Before Cockpit Governs Implementation

1. RLS bypass by substrate: neondb_owner with BYPASSRLS is a security hole
2. Dev bypass: Acceptable for single-operator but must be disabled for any multi-user scenario
3. No HTTPS enforcement in Docker config (relies on external proxy/Tailscale)
4. Execution control endpoints are stubs -- no real pause/stop capability

### P1 -- Before Trinity Feature Build

1. Rate limiting is in-memory -- needs persistence (Redis or similar)
2. No secret rotation mechanism
3. No audit of who accessed what data (beyond trace recording)
4. Discord bot has wildcard permissions (all guilds, channels, users)
5. Instagram credentials in plaintext env file

### P2 -- Before Production Scale

1. No WAF or DDoS protection
2. No CORS configuration on cockpit API (relies on dev bypass)
3. No OWASP security headers
4. No penetration testing evidence
5. No security incident response plan
6. No data classification policy enforcement
