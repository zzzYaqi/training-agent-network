"""Verified experience and reproducible checkpoint support."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class VerificationEvidence:
    evidence_id: str
    sequence: int
    task_id: str
    task_type: str
    requester_id: str
    agent_id: str
    passed: bool
    verifier_id: str


class EvidenceStore:
    """Task-scoped Beta trust derived only from verifier-labelled outcomes."""

    def __init__(self, events: list[VerificationEvidence] | None = None):
        self._events = list(events or [])

    @property
    def events(self) -> tuple[VerificationEvidence, ...]:
        return tuple(self._events)

    def record(
        self,
        *,
        task_id: str,
        task_type: str,
        requester_id: str,
        agent_id: str,
        passed: bool,
        verifier_id: str,
    ) -> VerificationEvidence:
        sequence = len(self._events) + 1
        event = VerificationEvidence(
            evidence_id=f"ev-{sequence:05d}",
            sequence=sequence,
            task_id=task_id,
            task_type=task_type,
            requester_id=requester_id,
            agent_id=agent_id,
            passed=bool(passed),
            verifier_id=verifier_id,
        )
        self._events.append(event)
        return event

    def evidence_for(
        self, requester_id: str, agent_id: str, task_type: str
    ) -> tuple[VerificationEvidence, ...]:
        return tuple(
            event
            for event in self._events
            if event.requester_id == requester_id
            and event.agent_id == agent_id
            and event.task_type == task_type
        )

    def trust_score(self, requester_id: str, agent_id: str, task_type: str) -> float:
        events = self.evidence_for(requester_id, agent_id, task_type)
        successes = sum(event.passed for event in events)
        # Beta(1, 1) prior avoids treating a single outcome as certainty.
        return (1 + successes) / (2 + len(events))

    def checkpoint(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "events": [asdict(event) for event in self._events],
        }

    @classmethod
    def from_checkpoint(cls, value: dict[str, Any]) -> "EvidenceStore":
        if value.get("schema_version") != 1:
            raise ValueError("unsupported evidence checkpoint schema")
        return cls([VerificationEvidence(**event) for event in value.get("events", [])])

