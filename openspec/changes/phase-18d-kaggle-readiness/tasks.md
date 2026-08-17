# Phase 18D Tasks

- [x] 18D-01 Freeze scope, preserve Phase 18B authority/status, and keep all authorization flags false. Owner: `planning-owner`. Depends on: none.
- [x] 18D-02 Define and implement notebook 00 content-based Kaggle discovery and provenance/privacy outputs. Owner: `kaggle-discovery`. Depends on: 18D-01.
- [x] 18D-02.5 Define and implement approved Phase 4 preprocessing-contract binding/verification action. Owner: `kaggle-materialization`. Depends on: 18D-02.
- [x] 18D-03 Define and implement notebook 01 resumable per-subject materialization and hash-verified reuse. Owner: `kaggle-materialization`. Depends on: 18D-02.5.
- [x] 18D-04 Enforce canonical ADNI mapping and one-person/one-initial-MRI policy in notebook 01. Owner: `kaggle-materialization`. Depends on: 18D-02.5.
- [x] 18D-05 Define and implement notebook 02 OASIS verification, including exact `BLOCKED_COHORT_MISMATCH`. Owner: `kaggle-verification`. Depends on: 18D-03 and 18D-04.
- [x] 18D-06 Verify source folds, fixed target adaptation/evaluation partitions, person disjointness, and target firewall. Owner: `kaggle-verification`. Depends on: 18D-05.
- [x] 18D-07 Verify approved Phase 4 and concept/anatomy reuse without refit or regeneration. Owner: `kaggle-verification`. Depends on: 18D-03.
- [x] 18D-08 Implement read-only `scripts/import_kaggle_readiness.py`. Owner: `repository-import`. Depends on: 18D-05, 18D-06, 18D-07.
- [x] 18D-09 Add synthetic-only focused tests for positive, negative, privacy, mismatch, overlap, leakage, reuse, and forbidden-action paths. Owner: `repository-tests`. Depends on: 18D-08.
- [ ] 18D-10 Run required validation commands and preserve output. Owner: `validation-owner`. Depends on: 18D-08 and 18D-09. Scoped validation passes; full Ruff remains blocked by unrelated `run_checks.py`.
- [ ] 18D-11 Conduct independent review gate. Owner: `independent-reviewer`. Depends on: 18D-10.
- [ ] 18D-12 Close only after review PASS; do not alter authorization or permit Phase 19. Owner: `transaction-controller`. Depends on: 18D-11.

## Exact validation commands

```bash
python -m pytest -q tests/phase_18d -p no:cacheprovider --basetemp=C:/p18d-focused
python scripts/import_kaggle_readiness.py --validate-only --evidence-root "%KAGGLE_READINESS_EVIDENCE_ROOT%"
python -m ruff check scripts/import_kaggle_readiness.py tests/phase_18d
git diff --check
```

`KAGGLE_READINESS_EVIDENCE_ROOT` is an explicit operator-supplied external value and must not be invented or committed. No task may run real training, real predictive evaluation, publication analysis, repository-side model-ready generation, or Phase 19.