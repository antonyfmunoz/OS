"""UMH Context — layered context composition with fault isolation.

Public API:
    from umh.context import ContextBuilder, ContextResult, ContextSection

    builder = ContextBuilder()
    builder.add_section(ContextSection(
        name="identity",
        content="You are a helpful assistant.",
        priority=ContextPriority.CRITICAL,
    ))
    result = builder.build()
    print(result.system_prompt)
"""

from umh.context.builder import ContextBuilder
from umh.context.budget import TokenBudget
from umh.context.types import ContextPriority, ContextResult, ContextSection

__all__ = [
    "ContextBuilder",
    "ContextPriority",
    "ContextResult",
    "ContextSection",
    "TokenBudget",
]
