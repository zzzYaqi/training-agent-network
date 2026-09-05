import unittest

from training_agent_network.adapters import (
    BugAdjudication,
    BugClaim,
    BugFindingAdapter,
    ProgramBenchAdapter,
    ProgramBenchScore,
    ProgramSubmission,
)


class AdapterTests(unittest.TestCase):
    def test_bug_claim_requires_evidence_and_independent_adjudication(self):
        adapter = BugFindingAdapter(
            lambda claim: BugAdjudication(True, "parser-empty-input", "reproduced")
        )
        claim = BugClaim(
            repository="owner/repo",
            commit="abc123",
            file="src/parser.py",
            line=12,
            claim="empty input crashes",
            reproduction="pytest tests/test_empty.py",
            expected="empty result",
            observed="IndexError",
            severity="medium",
            evidence=("trace.txt",),
        )
        self.assertTrue(adapter.verify(claim))
        self.assertEqual(adapter.last_adjudication.distinct_key, "parser-empty-input")

    def test_programbench_uses_strict_resolved_as_verifier_outcome(self):
        almost = ProgramBenchAdapter(lambda submission: ProgramBenchScore(95, 100))
        exact = ProgramBenchAdapter(lambda submission: ProgramBenchScore(100, 100))
        submission = ProgramSubmission("pb-1", "/workspace", "./build.sh")

        self.assertFalse(almost.verify(submission))
        self.assertTrue(almost.scores["pb-1"].almost_resolved)
        self.assertTrue(exact.verify(submission))


if __name__ == "__main__":
    unittest.main()

