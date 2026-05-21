"""Stage 1: Authority check — gatekeeper for execution permission."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from umh.execution.stages import StageContext

_log = logging.getLogger(__name__)

_FAIL_CLOSED_RISK_CLASSES = frozenset({"HIGH", "CRITICAL"})


@dataclass(frozen=True)
class AuthorityCheckStage:
    name: str = "authority_check"
    description: str = "Validate execution authority — fail-closed for HIGH/CRITICAL"
    dependencies: tuple[str, ...] = ()
    can_abort: bool = True

    def run(self, context: StageContext) -> StageContext:
        try:
            from umh.environments.system_context import load_context_from_env
            from umh.runtime_engine.authority_engine import AuthorityEngine

            ctx = load_context_from_env()
            context.ctx = ctx
            ae = AuthorityEngine(ctx)
            check = ae.check_can_execute(context.authority_class)
            if not check["can_execute"] and check.get("requires_approval"):
                approval_id = ae.queue_for_approval(
                    context.authority_class,
                    {"prompt": context.message, "agent": context.agent_type},
                    context.agent_type,
                )
                context.aborted = True
                context.abort_result = (
                    f"Queued for approval — use `!approve {approval_id}` to execute."
                )
                return context
        except Exception as e:
            risk_class = "LOW"
            try:
                from umh.runtime_engine.authority_engine import AuthorityEngine as _AE

                risk_class = _AE.classify_action(None, context.authority_class)
            except Exception:
                pass
            if risk_class in _FAIL_CLOSED_RISK_CLASSES:
                _log.error(
                    "Authority check failed for %s (risk=%s), blocking: %s",
                    context.authority_class,
                    risk_class,
                    e,
                )
                context.aborted = True
                context.abort_result = (
                    f"Unable to verify authority for this {risk_class} action. "
                    f"Request blocked for safety. Error: {e}"
                )
                return context
            _log.warning(
                "Authority check failed for %s (risk=%s), proceeding: %s",
                context.authority_class,
                risk_class,
                e,
            )

        if context.ctx is None:
            try:
                from umh.environments.system_context import load_context_from_env

                context.ctx = load_context_from_env()
            except Exception as e:
                _log.error("Cannot load context: %s", e)
                context.aborted = True
                context.abort_result = f"System configuration error: {e}"

        return context
