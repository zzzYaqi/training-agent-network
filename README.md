# Training an Agent Network

A minimal, auditable implementation for testing how agents form a shared task
group and whether verified coordination experience changes later decisions.

The first version deliberately tests a narrow claim:

> With agents, tasks, budgets, and the routing rule held fixed, does restoring
> verified experience change candidate ranking and delegation decisions, and
> does that change coordination cost or task outcome?

It does **not** yet claim topology evolution, policy learning, or end-to-end
self-evolution. The included workload adapters are integration contracts, not
completed leaderboard submissions.

## Shared group protocol

Every coordinator, verifier, and worker joins one bounded group. Work then
produces an append-only event stream:

```text
task_posted -> proposal -> commitment -> result -> verification
                                  |
                                  +-> delegation (after a rejected result)
```

The group is deliberately policy-neutral. It records membership and messages;
the Design-Time or Runtime policy still controls ranking. This separation lets
the evaluator check whether collaboration actually occurred instead of trusting
a method name such as `rac.full`.

## Experimental conditions

| Condition | Routing rule | Initial experience |
|---|---|---|
| Design-Time | Frozen agent order | Ignored |
| Runtime-Fresh | Capability + task-scoped verified trust | Empty |
| Runtime-Experienced | The same runtime rule | Restored checkpoint |

The Fresh/Experienced comparison isolates accumulated verified experience. The
runtime policy code is identical in both conditions.

## What is recorded

Every routing decision records:

- all eligible candidates and their capability/trust scores;
- the selected agent and the decision reason;
- whether history existed and was read;
- the exact verification evidence IDs consumed by the decision.

The evaluator reports three layers:

1. **Mechanism** — was history available, consumed, and decision-relevant?
2. **Coordination** — first-choice success, calls, reroutes, and recovery.
3. **Outcome** — verified task success, cost units, and latency.

The group activation check additionally requires a complete observable loop of
task, proposal, commitment, result, and verification events for every task.

## Real workload seams

- `adapters/bug_finding.py` defines a reproducible bug claim and requires an
  independent adjudicator after basic evidence-completeness checks.
- `adapters/programbench.py` accepts scores from the official ProgramBench
  evaluator. Only 100% behavioral-test completion becomes a passing verifier
  outcome; partial pass rate remains diagnostic metadata.

Neither adapter fabricates benchmark results or embeds hidden tests. The next
integration step is to connect these contracts to the team's existing
bug-finding runner and the official ProgramBench containers.

## Run the zero-API pilot

Python 3.10+ is sufficient; the package has no runtime dependencies.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -e .
python experiments/run_pilot.py
```

The complete trace and metric report is written to
`results/pilot_report.json`.

## Run tests

```bash
python -m unittest discover -s tests -v
```

## Repository layout

```text
src/training_agent_network/
  messages.py      collaboration message vocabulary
  group.py         membership and append-only shared message log
  evidence.py      verified evidence and checkpoints
  policies.py      frozen and runtime routing policies
  runtime.py       attributable coordination loop
  evaluation.py    mechanism, coordination, outcome metrics
  adapters/        Bug Finding and ProgramBench integration contracts
experiments/
  run_pilot.py     deterministic paired pilot
tests/             unit tests
```

## Evidence boundary

The included pilot is an implementation test. It demonstrates that the
measurement pipeline can attribute a changed action to consumed verified
evidence. It does not establish real-world benchmark gains. Later benchmark
adapters should preserve the same conditions, external verifier, task order,
budget, and trace schema.
