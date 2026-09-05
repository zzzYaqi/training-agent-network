"""Strict output and adjudication contract for open-source bug finding."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class BugClaim:
    repository: str
    commit: str
    file: str
    line: int
    claim: str
    reproduction: str
    expected: str
    observed: str
    severity: str
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class BugAdjudication:
    valid: bool
    distinct_key: str | None
    reason: str


class BugFindingAdapter:
    """Validate claim completeness before calling an independent adjudicator."""

    def __init__(self, adjudicator: Callable[[BugClaim], BugAdjudication]):
        self.adjudicator = adjudicator
        self.last_adjudication: BugAdjudication | None = None

    @staticmethod
    def is_complete(claim: BugClaim) -> bool:
        return bool(
            claim.repository.strip()
            and claim.commit.strip()
            and claim.file.strip()
            and claim.line > 0
            and claim.claim.strip()
            and claim.reproduction.strip()
            and claim.expected.strip()
            and claim.observed.strip()
            and claim.evidence
        )

    def verify(self, claim: BugClaim) -> bool:
        if not self.is_complete(claim):
            self.last_adjudication = BugAdjudication(False, None, "incomplete claim")
            return False
        self.last_adjudication = self.adjudicator(claim)
        return self.last_adjudication.valid

