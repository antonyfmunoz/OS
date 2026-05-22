"""Concrete agent cells — Researcher, Builder, AutoResearch."""

from __future__ import annotations

from services.umh.organism.agent_runtime import AgentRuntime
from services.umh.organism.protocols import CritiqueResult
from services.umh.organism.store import OrganismStore
from services.umh.organism.worker_cell import WorkerCell

RESEARCHER_SOUL = """You are the Researcher agent in the UMH organism.
Your domain: bounded research tasks across codebase, docs, web.
You spawn workers with read-only tools (read_file, grep, git_log).
You never modify files. You always self-critique your findings."""

BUILDER_SOUL = """You are the Builder agent in the UMH organism.
Your domain: code edits, implementation, file mutations.
You spawn workers with write tools (edit_file, shell).
You always verify your changes compile before delivering."""

AUTO_RESEARCH_SOUL = """You are the Auto-Research agent in the UMH organism.
Your domain: pattern extraction from agent deliverables and learning signals.
You observe the learning channel and identify recurring patterns.
You propose soul-doc updates for other agents."""


def create_researcher(store: OrganismStore, worker: WorkerCell | None = None) -> AgentRuntime:
    return AgentRuntime(
        agent_id="researcher",
        agent_name="Researcher",
        soul_doc=RESEARCHER_SOUL,
        store=store,
        worker=worker,
        max_critique_iterations=2,
        critique_threshold=7,
    )


def create_builder(store: OrganismStore, worker: WorkerCell | None = None) -> AgentRuntime:
    return AgentRuntime(
        agent_id="builder",
        agent_name="Builder",
        soul_doc=BUILDER_SOUL,
        store=store,
        worker=worker,
        max_critique_iterations=2,
        critique_threshold=7,
    )


def create_auto_research(store: OrganismStore, worker: WorkerCell | None = None) -> AgentRuntime:
    return AgentRuntime(
        agent_id="auto-research",
        agent_name="Auto-Research",
        soul_doc=AUTO_RESEARCH_SOUL,
        store=store,
        worker=worker,
        max_critique_iterations=1,
        critique_threshold=5,
    )
