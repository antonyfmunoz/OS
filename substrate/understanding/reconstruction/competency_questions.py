"""Competency questions for the Grounded Self-Model (DOMAIN_RECONSTRUCTION_SPEC §11.5).

The ten questions the reconstructed self-model MUST be able to answer from the
ledger + observations ALONE — never from prose, never from memory. Each question
carries an id, the human text, and an answer-derivation note stating which record
types answer it and what "unknown" means for that question.

This module is DATA ONLY (no I/O, no substrate imports). The builder consumes it
to produce competency answers; evaluation checks every id is represented in the
built model.json.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CompetencyQuestion:
    """One competency question with its answer-derivation contract."""

    id: str
    question: str
    derivation: str  # which record types answer it; what an unknown looks like

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "question": self.question,
            "derivation": self.derivation,
        }


# The 10 competency questions (§11.5). Order is stable and load-bearing:
# evaluation asserts all ten ids are present in model.json.
COMPETENCY_QUESTIONS: tuple[CompetencyQuestion, ...] = (
    CompetencyQuestion(
        id="CQ1",
        question="Which components are declared to exist?",
        derivation=(
            "ClaimLedgerEntry(claim_type='component_status') for each declared "
            "component. Unknown only if no declaration source was acquired."
        ),
    ),
    CompetencyQuestion(
        id="CQ2",
        question="Which components are observed running?",
        derivation=(
            "ObservationRecord with a RUNTIME facet (running/reachable/live_path/"
            "outcome_verified). Unknown/none when no runtime probe established a "
            "runtime facet — reported as thin runtime coverage, never fabricated."
        ),
    ),
    CompetencyQuestion(
        id="CQ3",
        question="Which capabilities are claimed?",
        derivation=(
            "Observations with predicate='provides_capability' (from the organism "
            "world-model extractor) + component_status claims. Unknown if no "
            "capability source acquired."
        ),
    ),
    CompetencyQuestion(
        id="CQ4",
        question="Which components are present in source?",
        derivation=(
            "ObservationRecord at facet 'source_present' from the inventory seam. "
            "Unknown if inventory produced no source_present observation."
        ),
    ),
    CompetencyQuestion(
        id="CQ5",
        question="Which components are tested, and what do those tests prove?",
        derivation=(
            "Observations at facet 'unit_tested'/'integration_tested'; the value "
            "names what the test establishes. Unknown when no test observation "
            "exists for the component."
        ),
    ),
    CompetencyQuestion(
        id="CQ6",
        question="Which components are declared canonical?",
        derivation=(
            "component_status claims whose declaration text marks a canonical "
            "runtime/owner (e.g. CONFIRMED_RUNTIME + 'canonical'). Unknown when "
            "no source declares canonical ownership."
        ),
    ),
    CompetencyQuestion(
        id="CQ7",
        question="Where do components overlap or duplicate?",
        derivation=(
            "IdentityResolution entries (verdict merge/link/remain_separate/"
            "unresolved) over duplicate-name candidates. Unknown-per-pair maps to "
            "an 'unresolved' verdict, which is a first-class answer."
        ),
    ),
    CompetencyQuestion(
        id="CQ8",
        question="Which desired states have no implementation evidence?",
        derivation=(
            "component_status claims supported ONLY by declaration-facet "
            "observations, plus WorldGap-derived recorded omissions. Unknown never "
            "needed — absence of implementation evidence is itself the answer."
        ),
    ),
    CompetencyQuestion(
        id="CQ9",
        question="What must change for the model to converge?",
        derivation=(
            "Divergence entries (the 9 classes) each naming the claim/observation "
            "gap to close. Unknown when no divergence could be computed (no "
            "claims or no observations)."
        ),
    ),
    CompetencyQuestion(
        id="CQ10",
        question="What evidence would prove convergence?",
        derivation=(
            "Per divergence entry, the missing facet/observation type that would "
            "resolve it (verification requirement). Unknown when the divergence "
            "set is empty."
        ),
    ),
)

COMPETENCY_IDS: tuple[str, ...] = tuple(q.id for q in COMPETENCY_QUESTIONS)


def as_data() -> list[dict[str, Any]]:
    """The ten questions as plain dicts (for model.json embedding)."""
    return [q.to_dict() for q in COMPETENCY_QUESTIONS]
