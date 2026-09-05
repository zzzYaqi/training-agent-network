import unittest

from training_agent_network import (
    AgentDefinition,
    MessageType,
    RuntimeCoordinator,
    RuntimePolicy,
    SharedGroup,
    Task,
)
from training_agent_network.evaluation import group_mechanism_metrics


class GroupProtocolTests(unittest.TestCase):
    def test_non_member_cannot_publish(self):
        group = SharedGroup("g")
        with self.assertRaises(ValueError):
            group.emit(MessageType.TASK_POSTED, sender_id="outsider", task_id="t")

    def test_runtime_emits_complete_protocol_loop(self):
        agents = [AgentDefinition("worker", "coder", frozenset({"solve"}))]
        coordinator = RuntimeCoordinator(agents=agents, policy=RuntimePolicy())
        result = coordinator.run_task(
            run_id="r",
            task=Task("t", "code", "solve"),
            executor=lambda agent, task: {"ok": True},
            verifier=lambda result, task: result["ok"],
            max_calls=1,
        )

        task_types = {
            message.message_type for message in coordinator.group.for_task("t")
        }
        self.assertTrue(result.success)
        self.assertTrue(
            {
                MessageType.TASK_POSTED,
                MessageType.PROPOSAL,
                MessageType.COMMITMENT,
                MessageType.RESULT,
                MessageType.VERIFICATION,
            }.issubset(task_types)
        )
        metrics = group_mechanism_metrics(list(coordinator.group.messages))
        self.assertTrue(metrics["group_mechanism_activated"])


if __name__ == "__main__":
    unittest.main()

