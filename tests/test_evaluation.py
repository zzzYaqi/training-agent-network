import unittest

from training_agent_network.evaluation import mechanism_metrics
from training_agent_network.models import CandidateScore, DecisionTrace


def trace(run_id, selected, order, evidence=()):
    return DecisionTrace(
        run_id=run_id,
        task_id="task-1",
        task_type="research",
        decision_index=1,
        policy="runtime",
        candidates=tuple(CandidateScore(agent, 1.0, 0.5, 0.5) for agent in order),
        selected_agent=selected,
        history_available=bool(evidence),
        history_read=bool(evidence),
        evidence_ids=tuple(evidence),
        decision_reason="test",
    )


class EvaluationTests(unittest.TestCase):
    def test_activation_requires_evidence_and_changed_decision(self):
        metrics = mechanism_metrics(
            [trace("fresh", "a", ("a", "b"))],
            [trace("experienced", "b", ("b", "a"), ("ev-1",))],
        )
        self.assertTrue(metrics["mechanism_activated"])
        self.assertEqual(metrics["action_change_rate"], 1.0)


if __name__ == "__main__":
    unittest.main()

