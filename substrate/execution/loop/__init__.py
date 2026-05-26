"""Persistent execution loops — config-driven autonomous cycles for UMH.

Import stages to register built-in stage functions on first use.
"""

from substrate.execution.loop.persistent_loop import (  # noqa: F401
    CycleReport,
    LoopDefinition,
    LoopRegistry,
    LoopState,
    PersistentLoop,
    STAGE_REGISTRY,
    get_registry,
    register_stage,
)

import substrate.execution.loop.stages  # noqa: F401 — registers built-in stages
