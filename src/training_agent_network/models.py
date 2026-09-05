"""Typed records shared by the runtime and evaluation code."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Callable


@dataclass(frozen=True)
class AgentDefinition:
    """A stable identity snapshot used for one experimental run."""

    agent_id: str
    role: str
    capabilities: frozenset[str]
    version: str = "v1"
    cost_per_call: float = 1.0
    latency_per_call_ms: int = 100


@dataclass(frozen=True)
class Task:
    """A task whose external verifier returns an objective boolean outcome."""

    task_id: str
    task_type: str
    required_capability: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CandidateScore:
    agent_id: str
    capability_match: float
    trust_score: float
    total_score: float
    evidence_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["evidence_ids"] = list(self.evidence_ids)
        return value


@dataclass(frozen=True)
class DecisionTrace:
    """One observable routing decision, including its evidence provenance."""

    run_id: str
    task_id: str
    task_type: str
    decision_index: int
    policy: str
    candidates: tuple[CandidateScore, ...]
    selected_agent: str
    history_available: bool
    history_read: bool
    evidence_ids: tuple[str, ...]
    decision_reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "evidence_ids": list(self.evidence_ids),
        }


@dataclass(frozen=True)
class TaskResult:
    run_id: str
    task_id: str
    task_type: str
    policy: str
    success: bool
    attempted_agents: tuple[str, ...]
    verified_outcomes: tuple[bool, ...]
    cost: float
    latency_ms: int

    @property
    def calls(self) -> int:
        return len(self.attempted_agents)

    @property
    def recovered(self) -> bool:
        return self.success and self.calls > 1 and not self.verified_outcomes[0]

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["attempted_agents"] = list(self.attempted_agents)
        value["verified_outcomes"] = list(self.verified_outcomes)
        value["calls"] = self.calls
        value["recovered"] = self.recovered
        return value


Executor = Callable[[AgentDefinition, Task], Any]
Verifier = Callable[[Any, Task], bool]

