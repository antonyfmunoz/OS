# Global Awareness — Discovery Report

**Date:** 2026-05-18
**Session:** E — Native Global Awareness / Tier 5

## Environment Discovery

| Check | Result |
|-------|--------|
| Platform | Linux (VPS) |
| Python | 3.12 |
| Working directory | /opt/OS (UMH substrate) |
| Network access | Full — all APIs reachable |
| Existing jarvis dir | None (created fresh) |
| Windows path | N/A — VPS environment |

## Dependency State

| Package | Pre-existing | Installed | Version |
|---------|-------------|-----------|---------|
| requests | Yes | — | 2.32.5 |
| feedparser | No | Yes | 6.0.12 |
| yfinance | No | Yes | 1.3.0 |
| xml.etree (stdlib) | Yes | — | stdlib |

## API Access Verification

| API | Endpoint | Status | Auth Required |
|-----|----------|--------|---------------|
| CoinGecko | api.coingecko.com/api/v3 | Reachable (200) | No |
| NOAA Weather | api.weather.gov | Reachable (200) | No |
| RSS (NYT) | rss.nytimes.com | Reachable (200) | No |
| RSS (BBC) | feeds.bbci.co.uk | Reachable (200) | No |
| RSS (Reddit) | reddit.com/.rss | Reachable (200) | No |
| Yahoo Finance | Via yfinance SDK | Working | No |

## Location Chosen

**Backend module:** `/opt/OS/services/jarvis/awareness/world/`

Rationale:
- VPS has full network access and all Python deps
- `services/jarvis/` is the natural home for a service-level awareness module
- Package named `world` (not `global`) because `global` is a Python keyword
- No port/service conflicts — this is a library, not a server

## Package Name Decision

`global` → `world` rename was required because `global` is a Python reserved
keyword. Any `from ...global.schema import ...` triggers `SyntaxError`.
