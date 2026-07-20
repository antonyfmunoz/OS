"""Identity-resolution record lifecycle for the reconstruction subsystem.

Append-only log of IdentityResolution verdicts over candidate entity pairs.
Verdicts are supersedable (a later verdict links back via supersedes; the prior
verdict is never rewritten). A `merge` verdict MUST carry >=1 supporting
evidence id — merging two entities on no evidence is rejected.

Candidate MINING (proposing which entities might be the same) lives in the
builder, not here; this module owns only the record lifecycle + validation.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

from typing import Optional

from substrate.understanding.reconstruction.contracts import IdentityResolution
from substrate.understanding.reconstruction.provenance import JsonlAppender


def candidate_pair(entity_a: str, entity_b: str) -> tuple[str, ...]:
    """Order-independent candidate pair key (sorted, de-duplicated)."""
    return tuple(sorted({entity_a, entity_b}))


class IdentityResolutionLog:
    """Append-only, supersedable identity-resolution log.

    append() validates every verdict; a `merge` with zero evidence ids raises.
    current() projects the latest non-superseded verdict per candidate lineage.
    """

    def __init__(self, appender: Optional[JsonlAppender] = None) -> None:
        self._appender = appender
        self._entries: list[IdentityResolution] = []

    @staticmethod
    def _validate(res: IdentityResolution) -> None:
        if len(res.candidate_entity_ids) < 2:
            raise ValueError("an identity resolution needs >=2 candidate ids")
        if res.verdict == "merge" and len(res.supporting_evidence_ids) < 1:
            raise ValueError("a 'merge' verdict requires >=1 supporting evidence id")

    def append(self, res: IdentityResolution) -> IdentityResolution:
        self._validate(res)
        self._entries.append(res)
        if self._appender is not None:
            self._appender.append(res.to_dict())
        return res

    def supersede(
        self, prior: IdentityResolution, replacement: IdentityResolution
    ) -> IdentityResolution:
        if replacement.supersedes not in (None, prior.id):
            raise ValueError("replacement.supersedes must be None or prior.id")
        return self.append(
            IdentityResolution(
                candidate_entity_ids=replacement.candidate_entity_ids,
                verdict=replacement.verdict,
                run_id=replacement.run_id,
                supporting_evidence_ids=replacement.supporting_evidence_ids,
                support_score=replacement.support_score,
                rationale=replacement.rationale,
                recorded_at=replacement.recorded_at,
                supersedes=prior.id,
            )
        )

    @property
    def entries(self) -> list[IdentityResolution]:
        return list(self._entries)

    def current(self) -> list[IdentityResolution]:
        """Latest non-superseded verdict per candidate lineage."""
        superseded = {e.supersedes for e in self._entries if e.supersedes}
        latest: dict[str, IdentityResolution] = {}
        for e in self._entries:
            if e.id in superseded:
                continue
            latest[e.lineage_id()] = e
        return [latest[k] for k in sorted(latest)]

    def merges(self) -> list[IdentityResolution]:
        return [e for e in self.current() if e.verdict == "merge"]
