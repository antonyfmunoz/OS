# UMH RLS and Tenant Isolation Matrix

Phase: 14.6B-UMH | Status: DRAFT | Provenance: CODE_RESOLVED_CURRENT_TRUTH

---

## Current Architecture

UMH operates in single-user validation phase -- one org, multiple ventures. Org and venture IDs loaded from BIS at runtime.

### Database Connections

| Layer | Connection | Role | RLS Status |
|-------|-----------|------|------------|
| Substrate (Python) | substrate/state/storage/db.py get_conn() | neondb_owner | BYPASSRLS -- no isolation |
| SaaS API (TypeScript) | transports/api/http/db/client.ts | eos_app | RLS ENFORCED |

### RLS Implementation (SaaS Layer)

Location: transports/api/http/db/migrate.ts

Tables with RLS:
- All tables defined in transports/api/http/db/schema.ts (users, organizations, portfolios)
- RLS enabled + forced (applies even to table owners)
- Isolation policies: WHERE org_id = current_setting('app.current_org_id')
- Set before each request: SET LOCAL app.current_org_id = '<org_id>'

### Tenant Isolation Status

| Concern | Status | Evidence |
|---------|--------|----------|
| SaaS multi-tenant isolation | IMPLEMENTED | RLS policies on all tenant tables via eos_app role |
| Substrate data isolation | NOT IMPLEMENTED | neondb_owner bypasses RLS |
| Cross-projection isolation | NOT IMPLEMENTED | No mechanism prevents one projection from accessing another's data |
| Cockpit data access | NOT RESTRICTED | Operator can access all data (by design for single-operator) |
| Projection database isolation | BY DESIGN | Each projection has its own DATABASE_URL |
| Audit log isolation | NOT IMPLEMENTED | All audit logs in shared JSONL files |

### Projection Database Isolation

Each projection connects to its own database via environment variables:
- EOS: EOS_DATABASE_URL
- CreatorOS: CREATOROS_DATABASE_URL
- LyfeOS: LYFEOS_DATABASE_URL

This provides physical isolation at the database level. UMH's ProductConnectionManager connects to each separately.

### Gaps

1. **P0**: Substrate Python code connects as neondb_owner with BYPASSRLS -- all RLS policies are meaningless for substrate operations
2. **P1**: No RLS on projection-specific tables accessed via substrate integrations
3. **P1**: No cross-projection data access audit mechanism
4. **P2**: No multi-org isolation in substrate (currently single-org assumption)
5. **P2**: JSONL audit logs are not tenant-isolated

### Recommendations

1. Create a substrate-specific database role with RLS enforcement
2. Ensure all substrate queries set app.current_org_id before execution
3. Add projection-level RLS for cross-projection data access
4. Move audit logs to tenant-isolated storage
5. These recommendations are for FUTURE multi-tenant scaling -- current single-operator deployment has acceptable risk
