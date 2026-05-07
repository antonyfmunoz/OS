---
type: codebase-function
file: core/environment_bridge/w0_packet_builder.py
line: 183
generated: 2026-05-07
---

# build_w0_001_packet

**File:** [[core-environment_bridge-w0_packet_builder-py]] | **Line:** 183
**Signature:** `build_w0_001_packet() → dict[str, Any]`

Build a complete W0-001 packet with all required routing fields.

## Calls

- [[core-coherence-spine_lineage_contracts-py-CoherenceEnvelope-to_dict]]
- [[core-coherence-spine_lineage_contracts-py-CoherenceValidationResult-to_dict]]
- [[core-coherence-spine_lineage_contracts-py-SpineLineage-to_dict]]
- [[core-coherence-spine_lineage_contracts-py-SpineStageArtifact-to_dict]]
- [[core-environment_bridge-w0_packet_builder-py-_build_w0_001_coherence_envelope]]

## Called By

- [[scripts-validate_w0_coherence_dry-py-run_dry_validation]]
