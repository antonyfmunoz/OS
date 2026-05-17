# Operator UI Auth Path

## Current Status: FUNCTIONAL (token-gated)

The Code View API server supports token-based auth via the
`CLAUDE_CODE_OAUTH_TOKEN` environment variable.

## How it works

1. Server reads `CLAUDE_CODE_OAUTH_TOKEN` from env at startup
2. If set, all `/api/code/*` requests must include `x-auth-token` header
3. If not set (dev mode), all requests are allowed without auth

## Token source

The token comes from `/opt/OS/.env.sessions`:
```
export CLAUDE_CODE_OAUTH_TOKEN=<token>
```

## Docker integration

The `os-operator` service in docker-compose.yml passes the token via:
```yaml
environment:
  - CLAUDE_CODE_OAUTH_TOKEN=${CLAUDE_CODE_OAUTH_TOKEN:-}
```

Set it in the host env or in `infra/docker/services.env`.

## Gate: ANTHROPIC_API_KEY

ANTHROPIC_API_KEY is explicitly NOT used here. The operator UI uses
the OAuth token for its own auth layer. The saas-dev-skill code engine
(which calls Claude API for AI features) would need ANTHROPIC_API_KEY,
but that path is currently blocked (401 per CLAUDE.md known gotchas).

AI-powered features in the code engine are gated until:
- Anthropic credits are restored, OR
- cc_sdk OAuth path is used (already working for other services)

The file operations (read/write/execute/list) work without any AI API key.
