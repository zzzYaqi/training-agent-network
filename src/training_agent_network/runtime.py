"""A small coordinator whose decisions are fully attributable."""

from __future__ import annotations

from .evidence import EvidenceStore
from .group import SharedGroup
from .messages import MessageType
from .models import AgentDefinition, DecisionTrace, Executor, Task, TaskResult, Verifier
from .policies import RoutingPolicy


class RuntimeCoordinator:
    def __init__(
        self,
        *,
        agents: list[AgentDefinition],
        policy: RoutingPolicy,
        evidence: EvidenceStore | None = None,
        requester_id: str = "coordinator",
        verifier_id: str = "external-verifier-v1",
        group: SharedGroup | None = None,
    ):
        if not agents:
            raise ValueError("at least one agent is required")
        self.agents = tuple(agents)
        self.policy = policy
        self.evidence = evidence or EvidenceStore()
        self.requester_id = requester_id
        self.verifier_id = verifier_id
        self.traces: list[DecisionTrace] = []
        self.group = group or SharedGroup("runtime-group")
        self.group.join(requester_id, role="coordinator", capabilities=["coordinate"])
        self.group.join(verifier_id, role="verifier", capabilities=["verify"])
        for agent in self.agents:
            self.group.join(
                agent.agent_id,
                role=agent.role,
                capabilities=list(agent.capabilities),
            )

    def run_task(
        self,
        *,
        run_id: str,
        task: Task,
        executor: Executor,
        verifier: Verifier,
        max_calls: int = 2,
    ) -> TaskResult:
        if max_calls < 1:
            raise ValueError("max_calls must be positive")

        self.group.emit(
            MessageType.TASK_POSTED,
            sender_id=self.requester_id,
            task_id=task.task_id,
            payload={
                "task_type": task.task_type,
                "required_capability": task.required_capability,
            },
        )

        attempted: list[str] = []
        outcomes: list[bool] = []
        total_cost = 0.0
        total_latency = 0
        by_id = {agent.agent_id: agent for agent in self.agents}

        for decision_index in range(1, max_calls + 1):
            history_available = bool(self.evidence.events)
            candidates, history_read, reason = self.policy.rank(
                requester_id=self.requester_id,
                task=task,
                agents=self.agents,
                excluded=frozenset(attempted),
                evidence=self.evidence,
            )
            if not candidates:
                break

            for candidate in candidates:
                candidate_agent = by_id[candidate.agent_id]
                self.group.emit(
                    MessageType.PROPOSAL,
                    sender_id=candidate.agent_id,
                    task_id=task.task_id,
                    recipient_id=self.requester_id,
                    payload={
                        "role": candidate_agent.role,
                        "capability_score": candidate.capability_match,
                        "trust_score": candidate.trust_score,
                        "total_score": candidate.total_score,
                        "evidence_ids": list(candidate.evidence_ids),
                    },
                )

            selected = candidates[0]
            consumed_ids = tuple(
                evidence_id
                for candidate in candidates
                for evidence_id in candidate.evidence_ids
            )
            self.traces.append(
                DecisionTrace(
                    run_id=run_id,
                    task_id=task.task_id,
                    task_type=task.task_type,
                    decision_index=decision_index,
                    policy=self.policy.name,
                    candidates=candidates,
                    selected_agent=selected.agent_id,
                    history_available=history_available,
                    history_read=history_read,
                    evidence_ids=consumed_ids,
                    decision_reason=reason,
                )
            )

            if attempted:
                self.group.emit(
                    MessageType.DELEGATION,
                    sender_id=attempted[-1],
                    recipient_id=selected.agent_id,
                    task_id=task.task_id,
                    payload={"reason": "previous result failed external verification"},
                )
            self.group.emit(
                MessageType.COMMITMENT,
                sender_id=selected.agent_id,
                recipient_id=self.requester_id,
                task_id=task.task_id,
                payload={"decision_index": decision_index, "status": "accepted"},
            )

            agent = by_id[selected.agent_id]
            raw_result = executor(agent, task)
            self.group.emit(
                MessageType.RESULT,
                sender_id=agent.agent_id,
                recipient_id=self.verifier_id,
                task_id=task.task_id,
                payload={"result_type": type(raw_result).__name__},
            )
            passed = bool(verifier(raw_result, task))
            self.group.emit(
                MessageType.VERIFICATION,
                sender_id=self.verifier_id,
                recipient_id=agent.agent_id,
                task_id=task.task_id,
                payload={"passed": passed, "verifier_id": self.verifier_id},
            )
            attempted.append(agent.agent_id)
            outcomes.append(passed)
            total_cost += agent.cost_per_call
            total_latency += agent.latency_per_call_ms

            self.evidence.record(
                task_id=task.task_id,
                task_type=task.task_type,
                requester_id=self.requester_id,
                agent_id=agent.agent_id,
                passed=passed,
                verifier_id=self.verifier_id,
            )
            if passed:
                break

        return TaskResult(
            run_id=run_id,
            task_id=task.task_id,
            task_type=task.task_type,
            policy=self.policy.name,
            success=bool(outcomes and outcomes[-1]),
            attempted_agents=tuple(attempted),
            verified_outcomes=tuple(outcomes),
            cost=total_cost,
            latency_ms=total_latency,
        )
