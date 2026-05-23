# governance/

Policy enforcement, quality gates, validation, and accountability.
Every action passes through governance before execution.

## Subdirectories

| Path | Purpose |
|------|---------|
| `accountability/` | Accountability tracking |
| `policies/` | Policy definitions |
| `policy/` | Policy engine (authority_engine) |
| `principles/` | System principles enforcement |
| `quality/` | Quality gates |
| `validation/` | Validation rules |

## §24 Reference

Canonical module tree §24: `governance/` — policies, authority,
accountability, quality, validation.

## Boundary

Governance authorizes or blocks. It does NOT execute, retrieve state
directly, or call external systems. It receives requests from the
control plane and returns authorize/deny decisions.
