import unittest

from training_agent_network import (
    AgentDefinition,
    EvidenceStore,
    RuntimeCoordinator,
    RuntimePolicy,
    Task,
)


AGENTS = [
    AgentDefinition("a", "general", frozenset({"solve"})),
    AgentDefinition("b", "specialist", frozenset({"solve"})),
]


class RuntimeTests(unittest.TestCase):
    def test_experience_changes_first_action_and_is_attributable(self):
        store = EvidenceStore()
        for index in range(3):
            store.record(
                task_id=f"prior-a-{index}", task_type="research", requester_id="coordinator",
                agent_id="a", passed=False, verifier_id="v",
            )
            store.record(
                task_id=f"prior-b-{index}", task_type="research", requester_id="coordinator",
                agent_id="b", passed=True, verifier_id="v",
            )

        coordinator = RuntimeCoordinator(agents=AGENTS, policy=RuntimePolicy(), evidence=store)
        result = coordinator.run_task(
            run_id="experienced",
            task=Task("t", "research", "solve"),
            executor=lambda agent, task: {"ok": agent.agent_id == "b"},
            verifier=lambda result, task: result["ok"],
            max_calls=1,
        )

        trace = coordinator.traces[0]
        self.assertTrue(result.success)
        self.assertEqual(trace.selected_agent, "b")
        self.assertTrue(trace.history_read)
        self.assertTrue(trace.evidence_ids)

    def test_verification_failure_causes_bounded_reroute(self):
        coordinator = RuntimeCoordinator(agents=AGENTS, policy=RuntimePolicy())
        result = coordinator.run_task(
            run_id="fresh",
            task=Task("t", "research", "solve"),
            executor=lambda agent, task: {"ok": agent.agent_id == "b"},
            verifier=lambda result, task: result["ok"],
            max_calls=2,
        )
        self.assertEqual(result.attempted_agents, ("a", "b"))
        self.assertTrue(result.recovered)


if __name__ == "__main__":
    unittest.main()

