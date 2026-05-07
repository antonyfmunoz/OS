---
type: codebase-file
path: core/environment_bridge/chrome_visible_launch.py
module: core.environment_bridge.chrome_visible_launch
lines: 247
size: 8946
generated: 2026-05-07
---

# core/environment_bridge/chrome_visible_launch.py

Chrome visible launch gate for the Environment Bridge.

Evaluates Chrome launch attempts for W0-001 CU execution. Process
existence and window metadata (MainWindowHandle, MainWindowTitle) are
recorded as evidence but are NOT sufficient proof of visible GUI.
...

**Lines:** 247 | **Size:** 8,946 bytes

## Contains

- **class** [[core-environment_bridge-chrome_visible_launch-py-ChromeLaunchMethod]] — 0 methods
- **class** [[core-environment_bridge-chrome_visible_launch-py-MetadataEvidence]] — 0 methods
- **class** [[core-environment_bridge-chrome_visible_launch-py-ChromeVisibleLaunchStatus]] — 0 methods
- **class** [[core-environment_bridge-chrome_visible_launch-py-ChromeProcessSnapshot]] — 0 methods
- **class** [[core-environment_bridge-chrome_visible_launch-py-ChromeVisibleLaunchProof]] — 1 methods
- **fn** [[core-environment_bridge-chrome_visible_launch-py-required_chrome_executable_paths]]`() → list[str]`
- **fn** [[core-environment_bridge-chrome_visible_launch-py-is_allowed_chrome_launch_method]]`(method, executable_path) → bool`
- **fn** [[core-environment_bridge-chrome_visible_launch-py-build_chrome_launch_command]]`(url, executable_path) → str`
- **fn** [[core-environment_bridge-chrome_visible_launch-py-parse_chrome_process_snapshot]]`(snapshot) → ChromeProcessSnapshot`
- **fn** [[core-environment_bridge-chrome_visible_launch-py-classify_metadata_evidence]]`(processes) → MetadataEvidence`
- **fn** [[core-environment_bridge-chrome_visible_launch-py-evaluate_visible_chrome_launch]]`(launch_method, executable_path, requested_url, processes) → ChromeVisibleLaunchProof`
- **fn** [[core-environment_bridge-chrome_visible_launch-py-apply_founder_visual_confirmation]]`(proof, confirmed, notes) → ChromeVisibleLaunchProof`
- **fn** [[core-environment_bridge-chrome_visible_launch-py-parse_founder_visual_confirmation]]`(data) → tuple[bool, bool, str]`
- **fn** [[core-environment_bridge-chrome_visible_launch-py-visible_launch_proof_allows_next_gate]]`(proof) → bool`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Any
```
