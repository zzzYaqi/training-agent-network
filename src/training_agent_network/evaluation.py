"""Three-layer evaluation: mechanism, coordination, and outcome."""

from __future__ import annotations

from statistics import mean
from typing import Any

from .messages import GroupMessage, MessageType
from .models import DecisionTrace, TaskResult


def _rate(values: list[bool]) -> float:
    return mean(values) if values else 0.0


def mechanism_metrics(
    fresh: list[DecisionTrace], experienced: list[DecisionTrace]
) -> dict[str, Any]:
    experienced_first = {
        trace.task_id: trace for trace in experienced if trace.decision_index == 1
    }
    fresh_first = {trace.task_id: trace for trace in fresh if trace.decision_index == 1}
    shared_ids = sorted(set(fresh_first) & set(experienced_first))

    ranking_changed = []
    action_changed = []
    for task_id in shared_ids:
        before = fresh_first[task_id]
        after = experienced_first[task_id]
        ranking_changed.append(
            [item.agent_id for item in before.candidates]
            != [item.agent_id for item in after.candidates]
        )
        action_changed.append(before.selected_agent != after.selected_agent)

    return {
        "paired_tasks": len(shared_ids),
        "history_available_rate": _rate(
            [trace.history_available for trace in experienced_first.values()]
        ),
        "history_read_rate": _rate(
            [trace.history_read for trace in experienced_first.values()]
        ),
        "evidence_consumption_rate": _rate(
            [bool(trace.evidence_ids) for trace in experienced_first.values()]
        ),
        "ranking_change_rate": _rate(ranking_changed),
        "action_change_rate": _rate(action_changed),
        "mechanism_activated": bool(
            experienced_first
            and any(trace.evidence_ids for trace in experienced_first.values())
            and (any(ranking_changed) or any(action_changed))
        ),
    }


def coordination_metrics(results: list[TaskResult]) -> dict[str, float]:
    first_failed = [result for result in results if result.verified_outcomes and not result.verified_outcomes[0]]
    return {
        "first_choice_success_rate": _rate(
            [bool(result.verified_outcomes and result.verified_outcomes[0]) for result in results]
        ),
        "average_calls": mean([result.calls for result in results]) if results else 0.0,
        "reroute_rate": _rate([result.calls > 1 for result in results]),
        "recovery_rate": (
            _rate([result.recovered for result in first_failed]) if first_failed else 1.0
        ),
    }


def outcome_metrics(results: list[TaskResult]) -> dict[str, float]:
    return {
        "task_success_rate": _rate([result.success for result in results]),
        "total_cost_units": sum(result.cost for result in results),
        "average_cost_units": mean([result.cost for result in results]) if results else 0.0,
        "total_latency_ms": sum(result.latency_ms for result in results),
        "average_latency_ms": mean([result.latency_ms for result in results]) if results else 0.0,
    }


def group_mechanism_metrics(messages: list[GroupMessage]) -> dict[str, Any]:
    """Measure actual protocol events, rather than trusting a method label."""

    task_ids = sorted(
        {
            message.task_id
            for message in messages
            if message.message_type is MessageType.TASK_POSTED and message.task_id
        }
    )
    closed_loops = []
    proposal_counts = []
    for task_id in task_ids:
        task_messages = [message for message in messages if message.task_id == task_id]
        types = {message.message_type for message in task_messages}
        closed_loops.append(
            {
                MessageType.TASK_POSTED,
                MessageType.PROPOSAL,
                MessageType.COMMITMENT,
                MessageType.RESULT,
                MessageType.VERIFICATION,
            }.issubset(types)
        )
        proposal_counts.append(
            sum(message.message_type is MessageType.PROPOSAL for message in task_messages)
        )
    return {
        "tasks_observed": len(task_ids),
        "closed_loop_rate": _rate(closed_loops),
        "average_proposals_per_task": mean(proposal_counts) if proposal_counts else 0.0,
        "delegation_events": sum(
            message.message_type is MessageType.DELEGATION for message in messages
        ),
        "total_messages": len(messages),
        "group_mechanism_activated": bool(task_ids and all(closed_loops)),
    }


def evaluate_experiment(
    *,
    traces_by_condition: dict[str, list[DecisionTrace]],
    results_by_condition: dict[str, list[TaskResult]],
    messages_by_condition: dict[str, list[GroupMessage]] | None = None,
) -> dict[str, Any]:
    if "runtime_fresh" not in traces_by_condition or "runtime_experienced" not in traces_by_condition:
        raise ValueError("fresh and experienced traces are required")
    report = {
        "schema_version": 1,
        "mechanism": mechanism_metrics(
            traces_by_condition["runtime_fresh"],
            traces_by_condition["runtime_experienced"],
        ),
        "coordination": {
            name: coordination_metrics(results)
            for name, results in results_by_condition.items()
        },
        "outcome": {
            name: outcome_metrics(results)
            for name, results in results_by_condition.items()
        },
    }
    if messages_by_condition is not None:
        report["group_mechanism"] = {
            name: group_mechanism_metrics(messages)
            for name, messages in messages_by_condition.items()
        }
    return report
