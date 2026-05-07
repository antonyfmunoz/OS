---
type: codebase-file
path: core/environment_bridge/result_ingestion.py
module: core.environment_bridge.result_ingestion
lines: 165
size: 5823
generated: 2026-05-07
---

# core/environment_bridge/result_ingestion.py

Result ingestion for the Environment Bridge.

Validates and ingests result artifacts from local worker execution.
Checks proof completeness, governance compliance, and founder
confirmation requirements.
...

**Lines:** 165 | **Size:** 5,823 bytes

## Contains

- **class** [[core-environment_bridge-result_ingestion-py-BridgeResultStatus]] — 0 methods
- **class** [[core-environment_bridge-result_ingestion-py-BridgeResult]] — 1 methods
- **fn** [[core-environment_bridge-result_ingestion-py-build_bridge_result]]`(packet_id, work_order_id, execution_environment, outputs, proof_artifacts, governance_report, no_secret_confirmed, no_mutation_confirmed, founder_confirmation_required, founder_confirmation_status) → BridgeResult`
- **fn** [[core-environment_bridge-result_ingestion-py-validate_bridge_result]]`(result) → BridgeResult`
- **fn** [[core-environment_bridge-result_ingestion-py-result_satisfies_proof_requirements]]`(result, packet) → bool`
- **fn** [[core-environment_bridge-result_ingestion-py-result_has_governance_compliance]]`(result) → bool`
- **fn** [[core-environment_bridge-result_ingestion-py-ingest_bridge_result]]`(result) → BridgeResult`
- **fn** [[core-environment_bridge-result_ingestion-py-summarize_bridge_result]]`(result) → dict[str, Any]`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Any
from work_packet import WorkPacket
```
