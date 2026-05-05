# Password Manager Adapter Roadmap v1

**Phase**: 94D.9S
**Status**: PLANNED
**Date**: 2026-05-04

---

## 1. Architecture

All secret backends implement the same interface:

```python
class SecretBackend(Protocol):
    def has_secret(self, secret_ref: SecretRef) -> bool: ...
    def get_secret_for_action(self, secret_ref: SecretRef, action_context: dict) -> tuple[SecretUseStatus, str]: ...
    def rotate_secret(self, secret_ref: SecretRef) -> SecretUseStatus: ...
    def revoke_secret(self, secret_ref: SecretRef) -> SecretUseStatus: ...
    def audit_secret_use(self, secret_ref: SecretRef, action_id: str) -> SecretUseAuditEvent: ...
```

## 2. Current Backend

### Local .env (IMPLEMENTED)
- Path: `~/.umh/secrets/.env`
- Format: standard KEY=VALUE
- Security: file permissions only
- Rotation: manual edit
- Suitable for: development, bootstrap, single-operator

## 3. Planned Backends (Priority Order)

### A. Windows Credential Manager
- **When**: After W0-001 pilot proves the flow works
- **Why**: Native Windows secret store, already present on local PC
- **How**: `cmdkey` / PowerShell `Get-StoredCredential`
- **Advantage**: No external dependencies, encrypted at rest by Windows
- **Limitation**: Windows-only, no cross-device sync

### B. 1Password CLI (`op`)
- **When**: If founder already uses 1Password
- **Why**: Industry-standard, cross-device, team-capable
- **How**: `op read "op://vault/item/field"`
- **Advantage**: Audit trail, sharing, TOTP support
- **Limitation**: Subscription required, CLI auth session

### C. Bitwarden CLI (`bw`)
- **When**: If founder prefers open-source
- **Why**: Self-hostable, cross-platform
- **How**: `bw get password <item-id>`
- **Advantage**: Self-hosted option, free tier
- **Limitation**: CLI session management, slower than native

### D. Doppler
- **When**: If multi-environment secrets needed
- **Why**: Built for application secrets, environment-aware
- **How**: `doppler secrets get KEY --plain`
- **Advantage**: Environment promotion, change log
- **Limitation**: Cloud-only, another SaaS dependency

### E. Infisical
- **When**: If self-hosted secrets management needed
- **Why**: Open-source Doppler alternative
- **How**: Infisical CLI or SDK
- **Advantage**: Self-hostable, Kubernetes-native
- **Limitation**: Infrastructure overhead

### F. HashiCorp Vault
- **When**: If enterprise-grade secrets needed
- **Why**: Industry standard for infrastructure secrets
- **How**: Vault CLI or HTTP API
- **Advantage**: Dynamic secrets, leasing, rotation
- **Limitation**: Complex setup, operational overhead

## 4. Implementation Sequence

```
Phase 1 (NOW):     Local .env — prove the abstraction works
Phase 2 (NEXT):    Windows Credential Manager — native on target PC
Phase 3 (SCALE):   1Password or Bitwarden — cross-device, team-ready
Phase 4 (INFRA):   Doppler/Infisical/Vault — multi-environment
```

## 5. Migration Path

Each backend upgrade is additive:
1. Implement new backend adapter
2. Test with existing SecretRef keys
3. Migrate secrets to new backend
4. Update DEFAULT_BACKEND config
5. Old backend remains as fallback until deprecated

## 6. Selection Criteria

| Factor | Local .env | WinCred | 1Password | Bitwarden | Doppler |
|--------|-----------|---------|-----------|-----------|---------|
| Setup complexity | Trivial | Low | Medium | Medium | Medium |
| Security at rest | File perms | DPAPI | AES-256 | AES-256 | Cloud |
| Cross-device | No | No | Yes | Yes | Yes |
| Audit trail | No | No | Yes | Yes | Yes |
| Rotation support | Manual | Manual | Manual | Manual | Auto |
| Cost | Free | Free | $3/mo | Free | Free tier |
| Team sharing | No | No | Yes | Yes | Yes |
