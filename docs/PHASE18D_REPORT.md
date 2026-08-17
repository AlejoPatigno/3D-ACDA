# Phase 18D Kaggle Readiness Report

    **Status:** KAGGLE_NOTEBOOKS_READY_FOR_EXECUTION
    **Phase 18D Status:** PHASE18D_PREPARATION_COMPLETE
    **Operational State:** KAGGLE_NOTEBOOKS_READY_FOR_EXECUTION

    **Last Updated:** 2026-08-15

**Summary:** Phase 18D preparation logic is implemented. The three Kaggle notebooks are ready for execution but Kaggle execution evidence has not yet been imported. The repository-side importer and focused tests are in place. No authorization flags have been set, and Phase 19 remains forbidden.

**Evidence:**
- Notebook 00: Discovers Kaggle inputs by content (ad_new_2_19_2026.csv), computes real SHA-256 and byte size, validates schema, detects duplicate/conflicting subject mappings, requires HMAC secret from environment, asserts real_execution_authorized/publication_authorized are false, and writes de-identified JSON evidence.
- Notebook 01: Loads N00 evidence, implements deterministic one-person/one-initial-MRI selection with baseline/sc rule and unresolved tie exclusion, requires real runtime source for Phase 4 preprocessing (fail closed otherwise), maintains per-person PENDING/RUNNING/COMPLETED/FAILED states, reuses completed artifact only after SHA-256 verification, materializes to /kaggle/working, and writes de-identified provenance.
- Notebook 02: Loads and validates N00/N01 evidence, verifies OASIS counts/mapping from supplied evidence and raises BLOCKED_COHORT_MISMATCH on mismatch, validates model-ready/artifact coverage and hashes, generates deterministic person-level 5-fold source splits and 80/20 target partitions with exact intersection check and target-firewall manifest, runs only small synthetic probes, and writes KAGGLE_READINESS_EVIDENCE_PRODUCED only after all checks pass.
- Repository importer: Validates evidence bundles read-only, enforces binary task/order, validates bundle-present hashes and external hash attestations, enforces exact target disjointness/firewall, privacy, state, OASIS counts, and fails closed. It does not contain placeholder identities/default hashes.
- Focused tests: Include test_notebook_guards.py (placeholder absence), fixed import path in importer tests, removed hashlib NameError, test missing input, placeholder absence, HMAC/privacy, split intersection/firewall, importer valid/invalid bundle, and no training invocation.

**Closure Checklist:**
- [x] All three notebooks are standalone and contain no training or predictive evaluation.
- [x] Discovery is content-based (identifies ADNI dataset by file content) and contains no guessed mount.
- [x] Required SHA-256, byte size, schema, provenance, privacy, and HMAC outputs exist without raw IDs/secrets.
- [x] ADNI mapping (CN=0, MCI=1, AD=1) and one-person/one-initial-MRI policy (earliest visit_date, unresolved tie exclusion) are enforced.
- [x] Only approved Phase 4 preprocessing is reused when real runtime source is available (otherwise fail closed).
- [x] OASIS verification produces BLOCKED_COHORT_MISMATCH on mismatch.
- [x] Source folds are deterministic and target adaptation/evaluation partitions are person-disjoint and target-firewalled.
- [x] Materialization resumes only on verified hashes and exposes per-subject statuses (PENDING/RUNNING/COMPLETED/FAILED).
- [x] Probes are synthetic-only (small synthetic probes to verify environment).
- [x] Importer is read-only and focused tests pass.
- [x] State is KAGGLE_NOTEBOOKS_READY_FOR_EXECUTION, never REAL_RUN_READY*.
- [x] Authorization flags are false and Phase 19 remains forbidden.
    - [x] Final independent implementation review gate is PASS.

## Validation evidence

- `python -m pytest -q tests/phase_18d -p no:cacheprovider`: exit 0, **8 passed**.
- `python -m pytest -q -p no:cacheprovider`: exit 0, **1416 passed**, 6 expected warnings.
- `python -m ruff check scripts/import_kaggle_readiness.py tests/phase_18d`: exit 0.
    - `python -m ruff check .`: exit 0.
- `git diff --check`: exit 0.
- Notebook JSON/static guards: PASS.
- `python -m py_compile scripts/import_kaggle_readiness.py`: exit 0.
- `graphify update .`: exit 0; generated graph outputs were refreshed.

These checks validate the repository-side preparation implementation only. No Kaggle notebook was executed and no external hash/path is claimed.
