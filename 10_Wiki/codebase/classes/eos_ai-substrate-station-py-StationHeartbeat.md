---
type: codebase-class
file: eos_ai/substrate/station.py
line: 78
generated: 2026-04-12
---

# StationHeartbeat

**File:** [[eos_ai-substrate-station-py]] | **Line:** 78

Periodic liveness + capability advertisement from a station to EOS.

Station sends this on connect and on a regular interval (to be chosen
during daemon implementation). EOS updates NodeRegistry from it.

## Decorators

- `@dataclass`
