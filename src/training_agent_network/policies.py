"""Frozen design-time and evidence-conditioned runtime routing policies."""

from __future__ import annotations

from abc import ABC, abstractmethod

from .evidence import EvidenceStore
from .models import AgentDefinition, CandidateScore, Task


class RoutingPolicy(ABC):
    name: str

    @abstractmethod
    def rank(
        self,
        *,
        requester_id: str,
        task: Task,
        agents: tuple[AgentDefinition, ...],
        excluded: frozenset[str],
        evidence: EvidenceStore,
    ) -> tuple[tuple[CandidateScore, ...], bool, str]:
        """Return candidates, whether history was read, and a reason."""


class DesignTimePolicy(RoutingPolicy):
    """A deployment-time route that remains frozen throughout execution."""

    name = "design_time"

    def __init__(self, fixed_order: tuple[str, ...]):
        self.fixed_order = fixed_order

    def rank(self, *, requester_id, task, agents, excluded, evidence):
        by_id = {agent.agent_id: agent for agent in agents}
        ranked = []
        for position, agent_id in enumerate(self.fixed_order):
            agent = by_id.get(agent_id)
            if agent is None or agent_id in excluded:
                continue
            match = float(task.required_capability in agent.capabilities)
            if not match:
                continue
            ranked.append(CandidateScore(agent_id, match, 0.5, -float(position)))
        return tuple(ranked), False, "frozen deployment-time order"


class RuntimePolicy(RoutingPolicy):
    """Same fixed policy rule in every run; only its evidence state differs."""

    name = "runtime"

    def rank(self, *, requester_id, task, agents, excluded, evidence):
        ranked = []
        history_read = False
        for stable_index, agent in enumerate(agents):
            if agent.agent_id in excluded:
                continue
            match = float(task.required_capability in agent.capabilities)
            if not match:
                continue
            events = evidence.evidence_for(requester_id, agent.agent_id, task.task_type)
            ids = tuple(event.evidence_id for event in events)
            history_read = history_read or bool(ids)
            trust = evidence.trust_score(requester_id, agent.agent_id, task.task_type)
            # Stable index is only a deterministic tie-breaker; it cannot
            # outweigh even a small difference in verified task-scoped trust.
            score = match * trust
            ranked.append((CandidateScore(agent.agent_id, match, trust, score, ids), stable_index))
        ranked.sort(key=lambda item: (-item[0].total_score, item[1]))
        reason = "capability-filtered, task-scoped verified trust ranking"
        return tuple(item[0] for item in ranked), history_read, reason

