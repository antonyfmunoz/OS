"""Stage 3: Context assembly — extract system prompt from unified context."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from umh.execution.stages import StageContext

_log = logging.getLogger(__name__)


@dataclass(frozen=True)
class ContextAssemblyStage:
    name: str = "context_assembly"
    description: str = "Extract system prompt from caller-provided unified context"
    dependencies: tuple[str, ...] = ("authority_check",)
    can_abort: bool = False

    def run(self, context: StageContext) -> StageContext:
        try:
            context.system_prompt = context.unified_context.to_system_prompt()
        except Exception as e:
            _log.warning("Context assembly failed: %s", e)
            context.system_prompt = ""
        return context
