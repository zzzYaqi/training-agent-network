"""Run a deterministic, zero-API Fresh-vs-Experienced pilot."""

from __future__ import annotations

import json
from pathlib import Path

from training_agent_network import (
    AgentDefinition,
    DesignTimePolicy,
    EvidenceStore,
    RuntimeCoordinator,
    RuntimePolicy,
    Task,
    evaluate_experiment,
)


AGENTS = [
    AgentDefinition("agent_a", "direct coder", frozenset({"solve"}), cost_per_call=1.0, latency_per_call_ms=80),
    AgentDefinition("agent_b", "research specialist", frozenset({"solve"}), cost_per_call=1.2, latency_per_call_ms=110),
    AgentDefinition("agent_c", "data specialist", frozenset({"solve"}), cost_per_call=1.4, latency_per_call_ms=130),
]

SPECIALIST = {"code": "agent_a", "research": "agent_b", "data": "agent_c"}


def executor(agent: AgentDefinition, task: Task) -> dict:
    # Deterministic fixtures make policy comparisons paired and reproducible.
    success = agent.agent_id == SPECIALIST[task.task_type]
    return {"agent_id": agent.agent_id, "answer": task.payload.get("answer"), "ok": success}


def external_verifier(result: dict, task: Task) -> bool:
    return result["ok"] is True


def experience_checkpoint() -> dict:
    store = EvidenceStore()
    for task_type, specialist in SPECIALIST.items():
        for round_index in range(3):
            for agent in AGENTS:
                task = Task(f"experience-{task_type}-{round_index}-{agent.agent_id}", task_type, "solve")
                result = executor(agent, task)
                store.record(
                    task_id=task.task_id,
                    task_type=task.task_type,
                    requester_id="coordinator",
                    agent_id=agent.agent_id,
                    passed=external_verifier(result, task),
                    verifier_id="external-verifier-v1",
                )
    return store.checkpoint()


def evaluation_tasks() -> list[Task]:
    order = ["research", "data", "code", "data", "research", "code"] * 2
    return [Task(f"eval-{index:02d}", task_type, "solve") for index, task_type in enumerate(order, 1)]


def run_condition(name: str, coordinator: RuntimeCoordinator, tasks: list[Task]):
    results = [
        coordinator.run_task(
            run_id=name,
            task=task,
            executor=executor,
            verifier=external_verifier,
            max_calls=2,
        )
        for task in tasks
    ]
    return results, list(coordinator.traces)


def main() -> None:
    tasks = evaluation_tasks()
    checkpoint = experience_checkpoint()
    coordinators = {
        "design_time": RuntimeCoordinator(
            agents=AGENTS,
            policy=DesignTimePolicy(("agent_a", "agent_b", "agent_c")),
        ),
        "runtime_fresh": RuntimeCoordinator(agents=AGENTS, policy=RuntimePolicy()),
        "runtime_experienced": RuntimeCoordinator(
            agents=AGENTS,
            policy=RuntimePolicy(),
            evidence=EvidenceStore.from_checkpoint(checkpoint),
        ),
    }

    results_by_condition = {}
    traces_by_condition = {}
    messages_by_condition = {}
    for name, coordinator in coordinators.items():
        results, traces = run_condition(name, coordinator, tasks)
        results_by_condition[name] = results
        traces_by_condition[name] = traces
        messages_by_condition[name] = list(coordinator.group.messages)

    report = evaluate_experiment(
        traces_by_condition=traces_by_condition,
        results_by_condition=results_by_condition,
        messages_by_condition=messages_by_condition,
    )
    report["conditions"] = {
        name: {
            "results": [result.to_dict() for result in results_by_condition[name]],
            "traces": [trace.to_dict() for trace in traces_by_condition[name]],
            "messages": [message.to_dict() for message in messages_by_condition[name]],
        }
        for name in coordinators
    }
    report["experience_checkpoint"] = checkpoint

    output = Path(__file__).resolve().parents[1] / "results" / "pilot_report.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("Training Agent Network — deterministic pilot")
    print(f"mechanism activated: {report['mechanism']['mechanism_activated']}")
    print(f"action change rate: {report['mechanism']['action_change_rate']:.1%}")
    print(
        "group closed-loop rate: "
        f"{report['group_mechanism']['runtime_experienced']['closed_loop_rate']:.1%}"
    )
    for name in coordinators:
        coordination = report["coordination"][name]
        outcome = report["outcome"][name]
        print(
            f"{name:20} success={outcome['task_success_rate']:.1%} "
            f"first-choice={coordination['first_choice_success_rate']:.1%} "
            f"calls={coordination['average_calls']:.2f} "
            f"cost={outcome['total_cost_units']:.1f}"
        )
    print(f"report: {output}")


if __name__ == "__main__":
    main()
