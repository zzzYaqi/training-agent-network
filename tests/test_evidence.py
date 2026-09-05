import unittest

from training_agent_network import EvidenceStore


class EvidenceStoreTests(unittest.TestCase):
    def test_checkpoint_round_trip_preserves_scores_and_provenance(self):
        store = EvidenceStore()
        event = store.record(
            task_id="t1",
            task_type="code",
            requester_id="coordinator",
            agent_id="agent_a",
            passed=True,
            verifier_id="tests",
        )
        restored = EvidenceStore.from_checkpoint(store.checkpoint())

        self.assertEqual(restored.events, store.events)
        self.assertEqual(restored.trust_score("coordinator", "agent_a", "code"), 2 / 3)
        self.assertEqual(event.evidence_id, "ev-00001")

    def test_unseen_scope_uses_neutral_prior(self):
        self.assertEqual(EvidenceStore().trust_score("c", "a", "unknown"), 0.5)


if __name__ == "__main__":
    unittest.main()

