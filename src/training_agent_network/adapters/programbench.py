"""A narrow seam to the official ProgramBench evaluator.

The package deliberately does not duplicate ProgramBench containers or hidden
tests.  Callers inject the official evaluator and retain its strict `resolved`
result as the primary verifier outcome.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class ProgramSubmission:
    task_id: str
    workspace_path: str
    build_script: str


@dataclass(frozen=True)
class ProgramBenchScore:
    passed_tests: int
    total_tests: int

    def __post_init__(self):
        if self.total_tests <= 0:
            raise ValueError("total_tests must be positive")
        if not 0 <= self.passed_tests <= self.total_tests:
            raise ValueError("passed_tests must be within the test total")

    @property
    def pass_rate(self) -> float:
        return self.passed_tests / self.total_tests

    @property
    def almost_resolved(self) -> bool:
        return self.pass_rate >= 0.95

    @property
    def resolved(self) -> bool:
        return self.passed_tests == self.total_tests


class ProgramBenchAdapter:
    """Convert official behavioral-test scores into verifier outcomes."""

    def __init__(self, evaluator: Callable[[ProgramSubmission], ProgramBenchScore]):
        self.evaluator = evaluator
        self.scores: dict[str, ProgramBenchScore] = {}

    def verify(self, submission: ProgramSubmission) -> bool:
        score = self.evaluator(submission)
        self.scores[submission.task_id] = score
        return score.resolved

