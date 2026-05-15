# observability/

System health, status monitoring, and operational visibility.

## Subdirectories

| Path | Purpose |
|------|---------|
| `health/` | Health check endpoints and monitoring |
| `status/` | System status reporting |

## §24 Reference

Canonical module tree §24: `observability/` — tracing, logging,
health, metrics.

## Boundary

Observability reads and reports. It does NOT modify system state or
make decisions. It provides visibility into what other layers are doing.
