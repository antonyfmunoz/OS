---
type: codebase-function
file: core/environment_bridge/packet_validator.py
line: 153
generated: 2026-05-07
---

# validate_w0_packet_dict

**File:** [[core-environment_bridge-packet_validator-py]] | **Line:** 153
**Signature:** `validate_w0_packet_dict(packet) → PacketValidationResult`

Validate a W0 packet dict including execution_binding and coherence.

This validates the dict form produced by build_w0_001_packet()
rather than the WorkPacket dataclass. Checks execution_binding,
coherence_envelope, and their contents.

## Calls

- [[core-coherence-spine_coherence_validator-py-validate_coherence_envelope_dict]]

## Called By

- [[scripts-validate_w0_coherence_dry-py-run_dry_validation]]
