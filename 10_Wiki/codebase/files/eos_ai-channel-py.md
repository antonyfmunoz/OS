---
type: codebase-file
path: eos_ai/channel.py
module: eos_ai.channel
lines: 453
size: 13376
generated: 2026-05-07
---

# eos_ai/channel.py

EOS Channel System
==================
Adapted from OpenClaw's channel adapter pattern.

Channels are two-way execution surfaces, not notification sinks.
...

**Lines:** 453 | **Size:** 13,376 bytes

## Contains

- **class** [[eos_ai-channel-py-ChannelType]] — 0 methods
- **class** [[eos_ai-channel-py-Message]] — 0 methods
- **class** [[eos_ai-channel-py-ChannelConfig]] — 0 methods
- **class** [[eos_ai-channel-py-Channel]] — 4 methods
- **class** [[eos_ai-channel-py-DiscordChannel]] — 5 methods
- **class** [[eos_ai-channel-py-TelegramChannel]] — 5 methods
- **class** [[eos_ai-channel-py-WebhookChannel]] — 4 methods
- **class** [[eos_ai-channel-py-ConsoleChannel]] — 3 methods
- **class** [[eos_ai-channel-py-ChannelRouter]] — 6 methods
- **fn** [[eos_ai-channel-py-get_channel_router]]`() → ChannelRouter`

## Import Statements

```python
import json
import logging
import os
import urllib.request
import urllib.parse
from abc import ABC
from abc import abstractmethod
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Optional
```
