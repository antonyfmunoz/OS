"""UMH — Universal Meta Harness.

Domain-independent intelligence substrate.

Public API:
    from umh import run
    result = run("What should I focus on today?")
    print(result.response)
"""

from umh.run import RunResult, RunTrace, run

__all__ = ["run", "RunResult", "RunTrace"]
