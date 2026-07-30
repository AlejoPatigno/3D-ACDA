# Phase 14 Final Validation

Status: **PASS**

No real ADNI/OASIS cohort training was executed.

## Required command results

| Step | Command | Exit code | Result |
|---:|---|---:|---|
| 1 | `python -m pip install -e .` | 0 | Editable wheel built and `pada3dacb==0.1.0` installed successfully. No `--no-deps` fallback was used. |
| 2 | `python -c "import pada3dacb; print(pada3dacb.__version__)"` | 0 | Printed `0.1.0`. |
| 3 | `python -m pytest -q` | 0 | `549 passed, 7 warnings in 238.57s (0:03:58)`. |
| 4 | `python -m ruff check .` | 0 | `All checks passed!` |
| 5 | `git diff --check` | 0 | No output. |

## Synthetic lifecycle evidence

Command:

```text
python -m pytest -q tests/test_baseline_registry.py tests/test_baseline_smoke.py tests/test_baseline_cv.py tests/test_baseline_cli.py tests/test_baseline_trainer.py tests/test_baseline_source_only.py tests/test_all_methods_regression_phase14.py tests/test_proposed_method_cli.py --basetemp=artifacts/pytest-tmp-phase14-final-synthetic
```

Result: exit 0; `56 passed, 5 warnings in 19.17s`.

This evidence covers:

- deterministic listing of `aagn` and `faster_snn`;
- actual synthetic validate-only forward for both approved baselines;
- all five folds in dry-run;
- both cross-cohort directions in dry-run;
- one interrupted run and exact resume;
- completed-fold reuse and corrupt/incomplete-output rejection;
- no-target-adaptation assertions in plans, manifests, trainer APIs, and predictions;
- source-only prediction/manifest schema;
- previous-method CLI phase-boundary regressions.

## Warning inventory

- Four scikit-learn `UndefinedMetricWarning` messages come from deliberate single-class synthetic target-monitoring data; macro-AUC is recorded as unavailable and never affects training or checkpoint selection.
- Two historical preprocessing `std()` warnings are unchanged.
- One local `PytestCacheWarning` reports denied writes under `.pytest_cache`; test execution and results are unaffected.

## Acceptance boundary checks

- Only AAGN and FasterSNN production baseline modules exist.
- No external architecture was added.
- No `AlzheimerSupervisedMRIModel` baseline copy exists.
- No target-adaptation loader entered baseline orchestration or training.
- No target metric selects a checkpoint or hyperparameter.
- Source-validation macro-F1 remains the sole best-checkpoint criterion.
- Fixed epochs remain enforced and no early stopping was introduced.
- Source-Only, CORAL, MMD, CDAN, and prototype_pseudo regressions pass in the full suite.
- No confusion-matrix, concept-analysis, statistical-comparison, or Phase 15 production module was created.
- Agent-plan ownership validation reports 13 actions, 42 exclusive paths, and zero duplicate ownership.

## Remaining non-validation gate

Native review/receipt authority must still be resolved before archive, commit, push, PR, or publication. This does not change the PASS result for the required Phase 14 validation commands.
