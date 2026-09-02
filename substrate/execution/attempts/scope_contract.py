"""Provider-neutral attempt scope/projection contract helpers."""

from __future__ import annotations

from typing import Any

from substrate.execution.attempts.field_task_scope import ScopeResolutionError

TRUSTED_PROJECTION_PATHS = ("OBJECTIVE.md", "SHARED_CONTEXT.md")


def sealed_writable_scope(package: Any) -> list[str] | None:
    """Return the sealed writable_path_scope constraint, or None if absent."""
    for constraint in getattr(package, "governance_constraints", []) or []:
        text = str(constraint)
        if not text.startswith("writable_path_scope="):
            continue
        raw = text.split("=", 1)[1].strip()
        try:
            import ast

            parsed = ast.literal_eval(raw)
        except (ValueError, SyntaxError, TypeError, MemoryError, RecursionError) as exc:
            raise ScopeResolutionError(
                f"sealed writable_path_scope is unparseable ({raw[:60]!r}): {exc}"
            ) from exc
        if not isinstance(parsed, (list, tuple)):
            raise ScopeResolutionError(
                f"sealed writable_path_scope is not a list (got {type(parsed).__name__})"
            )
        return [str(p) for p in parsed]
    return None


__all__ = ["TRUSTED_PROJECTION_PATHS", "sealed_writable_scope"]
