# Instance Context Law

UMH has two layers that must never mix:

- **Canonical** (substrate/) = universal mechanisms. Works for any user.
- **Instance** = identity loaded at runtime from BIS/env/config.

Before writing ANY string literal in substrate/ code, ask:
"Would this be different for a different UMH user?"

If yes → it's instance context. Use runtime lookup, not a literal.

Categories that are ALWAYS instance context:
- AI name → `get_ai_name()` 
- Founder/user name → BIS profile
- Company/venture/product names → BIS registry
- Infrastructure IPs/hosts → env vars
- Account identifiers → env vars
- Node identifiers → BIS node registry
- Session name prefixes → derive from `get_ai_name()` at runtime

Pre-commit hook enforces this: `scripts/check_instance_leak.py`
