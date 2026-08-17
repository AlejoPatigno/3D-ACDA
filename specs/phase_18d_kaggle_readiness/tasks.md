# Phase 18D Kaggle Readiness Tasks

## Ownership rule

Every action has one owner. Owners may read declared dependencies but may not modify another owner's files. A task is complete only when its outputs and focused evidence are available to the next dependent task.

| ID | Action | Sole owner | Dependencies | Output |
|---|---|---|---|---|
| 18D-01 | Freeze scope, authority, forbidden actions, and false authorization flags | `planning-owner` | Phase 18B report | Requirements/design/decision traceability |
| 18D-02 | Define notebook contracts and dynamic content-based discovery | `kaggle-discovery` | 18D-01 | Notebook 00 contract and discovery schemas |
| 18D-03 | Implement resumable materialization and exact hash/privacy manifests in Kaggle | `kaggle-materialization` | 18D-02; approved Phase 4 contract | Notebook 01 contract; source, subject, cohort, and privacy evidence |
| 18D-04 | Implement canonical ADNI mapping and one-person/one-initial-MRI selection | `kaggle-materialization` | 18D-02 | Mapping and selection evidence |
| 18D-05 | Verify OASIS mapping, counts, person policy, HMAC policy, and mismatch behavior | `kaggle-verification` | 18D-03 | Notebook 02 verification evidence; `BLOCKED_COHORT_MISMATCH` on mismatch |
| 18D-06 | Verify source folds, fixed target partitions, person disjointness, and target firewall | `kaggle-verification` | 18D-03; 18D-05 | Splits manifest and firewall proof |
| 18D-07 | Validate approved Phase 4 preprocessing and concept/anatomy reuse without refit/regeneration | `kaggle-verification` | 18D-03 | Reuse manifest and validation result |
| 18D-08 | Define and implement the read-only repository importer | `repository-import` | 18D-03 through 18D-07 | `scripts/import_kaggle_readiness.py` |
| 18D-09 | Add synthetic-only focused tests, including negative and forbidden-action cases | `repository-tests` | 18D-08 | `tests/phase_18d/` |
| 18D-10 | Run exact validation commands and preserve outputs | `validation-owner` | 18D-08, 18D-09 | Focused test, validator, lint, and diff-check evidence |
| 18D-11 | Perform independent review gate | `independent-reviewer` | 18D-10 and complete implementation diff | Review PASS or blocking findings |
| 18D-12 | Close implementation only after review PASS and state checks | `transaction-controller` | 18D-11 | Closure decision; no authorization change |

## Detailed work packages

### WP-A: Kaggle notebooks

- Keep notebooks standalone and explicitly named `00`, `01`, and `02`.
- Make every external path a discovered runtime value; do not hardcode a mount.
- Record source URL, observed dataset name, candidate metadata path, file hashes, schema fingerprint, and candidate disposition.
- Keep notebook code free of training, real predictive evaluation, publication analysis, and Phase 19 calls.
- Keep model-ready generation, if performed, inside Kaggle and under the approved Phase 4 contract; repository work imports evidence only.

### WP-B: Materialization and privacy

- Process one canonical person and one initial MRI per person.
- Emit per-subject statuses and reason codes.
- Reuse only exact hash-verified artifacts; never overwrite a mismatch.
- Use HMAC-SHA256 subject tokens and record only key ID/version.
- Scan output paths, text, metadata, notebook cells, and manifests for raw IDs and secrets.

### WP-C: Verification

- Recompute ADNI mapping and reject unsupported/conflicting labels.
- Verify OASIS CDR mapping and exact approved arithmetic.
- Emit `BLOCKED_COHORT_MISMATCH` for any OASIS mismatch; no repair or alternative count.
- Verify source folds and fixed target adaptation/evaluation sets at person level.
- Prove target adaptation/evaluation intersection is empty and enforce the target firewall.
- Verify Phase 4 and concept/anatomy identities without fitting or regenerating artifacts.

### WP-D: Repository import and tests

- Make `scripts/import_kaggle_readiness.py` read-only and explicit-input only.
- Recompute every declared SHA-256 from bytes.
- Validate canonical schemas, privacy, status, mappings, splits, reuse, and false authorization flags.
- Add synthetic-only tests for pass and fail paths, especially hash reuse, OASIS mismatch, overlap, leakage, privacy, and forbidden actions.

## Required validation commands

Run from the repository root after implementation. `KAGGLE_READINESS_EVIDENCE_ROOT` must be supplied by the operator; its value is not committed or invented by this change.

```bash
python -m pytest -q tests/phase_18d -p no:cacheprovider --basetemp=C:/p18d-focused
python scripts/import_kaggle_readiness.py --validate-only --evidence-root "%KAGGLE_READINESS_EVIDENCE_ROOT%"
python -m ruff check scripts/import_kaggle_readiness.py tests/phase_18d
git diff --check
```

The validator command must exit non-zero for a missing, ambiguous, privacy-violating, hash-mismatched, OASIS-mismatched, overlapping, target-firewall-violating, regenerated, unauthorized, or forbidden-action bundle. No command in this package trains, evaluates, publishes, or executes Phase 19.

## Closure checklist

- [x] All three notebooks are standalone and no-training.
- [x] Discovery is content-based and contains no guessed mount.
- [x] Required SHA-256, provenance, privacy, and HMAC outputs exist without raw IDs/secrets.
- [x] ADNI mapping and one-person/one-initial-MRI policy are enforced.
- [x] Only approved Phase 4 preprocessing is reused when its Kaggle runtime binding is supplied.
- [x] OASIS verification produces `BLOCKED_COHORT_MISMATCH` on mismatch.
- [x] Source folds and fixed target partitions are deterministic, person-disjoint where required, and target-firewalled.
- [x] Materialization resumes only on verified hashes and exposes per-subject statuses.
- [x] Probes are synthetic-only.
- [x] Importer is read-only and focused tests pass.
- [x] State is `KAGGLE_NOTEBOOKS_READY_FOR_EXECUTION` or `KAGGLE_READINESS_EVIDENCE_IMPORTED`, never `REAL_RUN_READY*`.
- [x] Authorization flags are false and Phase 19 remains forbidden.
- [ ] Independent review gate is PASS; final follow-up remains pending.
