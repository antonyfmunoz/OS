"""Persistence protocols — contracts for goal and strategy state persistence."""

from __future__ import annotations

from umh.goals.interfaces import GoalPersistence
from umh.strategy.interfaces import StrategyPersistence

__all__ = ["GoalPersistence", "StrategyPersistence"]
