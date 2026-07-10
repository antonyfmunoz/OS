---
name: shannon
description: "Use when running AI-powered penetration testing, security audits, or vulnerability scanning against web applications and APIs with source code access."
allowed-tools: "Read, Bash"
version: 1.0
source_url: "https://github.com/KeygraphHQ/shannon"
last_researched: "2026-06-10"
instantiated_from: templates/tools/_template/
cli_version: "1.5.0"
speed_category: "slow"
trigger: both
effort: high
context: fork
---

# Tool: Shannon (AI Penetration Testing)

## What This Tool Does

Shannon is an autonomous, white-box AI pentester by KeygraphHQ. It analyzes
application source code, identifies attack vectors, and executes real exploits
in ephemeral Docker containers to produce proof-by-exploitation reports.

Core capabilities:
- **Source code analysis** — reads repo to understand architecture, entry points, data flows
- **Vulnerability discovery** — AI-driven identification of OWASP Top 10 and beyond
- **Proof-by-exploitation** — executes actual attacks in isolated Docker containers
- **Resumable scans** — named workspaces allow pause/resume without re-running phases
- **Markdown reports** — validated findings with reproducible exploitation steps

Coverage: SQL injection, XSS, SSRF, broken auth, broken authz, IDOR, command injection, template injection.

## Installation (Already Done on VPS)

```bash
npm install -g @keygraph/shannon
```

- Requires: Node.js 18+, Docker
- Runs as non-root user (ubuntu) — refuses to run as root
- Config at: /home/ubuntu/.shannon/config.toml
- API key injected from 1Password: `op://${UMH_OP_VAULT}/AI-Anthropic/api_key`

## UMH Integration

Adapter: `adapters/shannon/shannon_connector.py`

```python
from adapters.shannon.shannon_connector import ShannonConnector
sc = ShannonConnector()

# Check status
status = sc.status()

# Start a scan
result = sc.start_scan(
    url="https://target-app.com",
    repo_path="/path/to/source",
    workspace="q2-audit",
    output_dir="/opt/OS/data/shannon_reports",
)

# Get logs
logs = sc.get_logs("q2-audit")

# Stop all containers
sc.stop(clean=True)
```

## CLI Reference (run as ubuntu user)

```bash
# Setup / config
su - ubuntu -c "shannon setup"

# Start a scan
su - ubuntu -c "shannon start -u https://app.com -r /path/to/repo -w my-scan"

# With config file and output directory
su - ubuntu -c "shannon start -u https://app.com -r /repo -c config.yaml -o /output -w audit-q2"

# Check status
su - ubuntu -c "shannon status"

# List workspaces
su - ubuntu -c "shannon workspaces"

# Tail logs
su - ubuntu -c "shannon logs my-scan"

# Stop containers
su - ubuntu -c "shannon stop --clean"

# Monitor UI
# http://localhost:8233 (while scan is running)
```

## Configuration

Config file: `/home/ubuntu/.shannon/config.toml`

```toml
[provider]
type = "anthropic"       # anthropic | bedrock | vertex | custom
api_key = "sk-ant-..."   # injected from 1Password

# Optional overrides
# [provider]
# type = "bedrock"
# region = "us-east-1"
```

Environment variable overrides (take precedence over config.toml):
- `ANTHROPIC_API_KEY` — direct key
- `CLAUDE_CODE_USE_BEDROCK=1` — use AWS Bedrock
- `CLAUDE_CODE_USE_VERTEX=1` — use Google Vertex AI
- `ANTHROPIC_BASE_URL` — custom endpoint (e.g., LiteLLM proxy)

## Scan Lifecycle

1. **Pre-recon** — analyzes source code structure
2. **Reconnaissance** — maps attack surface from code + live target
3. **Vulnerability analysis** — AI identifies attack vectors
4. **Exploitation** — executes real exploits in ephemeral Docker containers
5. **Reporting** — generates proof-by-exploitation markdown report

Typical scan: 1-1.5 hours. Cost varies by app complexity (LLM API usage).

## Gotchas

- **Root user blocked** — Shannon refuses to run as root. Always run as `ubuntu` user via `su -`.
- **Docker required** — exploits run in ephemeral containers. Docker daemon must be running.
- **ubuntu must be in docker group** — `usermod -aG docker ubuntu` (already done on VPS).
- **LLM cost** — scans consume Anthropic API credits. A full scan can use significant tokens.
- **Long-running** — scans take 1-1.5 hours. Use named workspaces (`-w`) so scans resume on interruption.
- **Only Claude models** — non-Claude providers are experimental/unstable.
- **Config precedence** — env vars override config.toml values.
- **Port 8233** — Temporal UI for monitoring. Only available during active scan.
- **AGPL-3.0 license** — copyleft. Fine for internal use; review before distributing modified versions.
- **Defensive use only** — only scan applications you own or have explicit authorization to test.

## Verification

```bash
# Verify installation
su - ubuntu -c "shannon status"

# Verify config
su - ubuntu -c "cat ~/.shannon/config.toml | head -2"

# Verify Docker access
su - ubuntu -c "docker ps"

# Test against a known vulnerable app (OWASP Juice Shop)
# docker run -p 3000:3000 bkimminich/juice-shop
# su - ubuntu -c "shannon start -u http://localhost:3000 -r /path/to/juice-shop -w test-run"
```
