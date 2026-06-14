"""Executor implementations for the UMH Executor Runtime.

Each executor implements the canonical ExecutorContract (6 methods):
validate → prepare → execute → monitor → cancel → cleanup.

Available executors:
  - WorkstationExecutor: real machine operations (commands, files, worktrees)
  - AgentExecutor: governed cognitive worker (Claude Code CLI via gated subprocess)
"""
