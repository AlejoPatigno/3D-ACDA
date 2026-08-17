# Phase 18D Tasks

## Completed Tasks

- [x] **T-18D-01 — Implement Notebook 00: Discover Kaggle Inputs**
  - Dynamically enumerate `/kaggle/input`, identify ADNI dataset by content, compute real SHA-256/byte size/schema/row count, validate required fields, detect duplicate/conflicting subject mappings, require HMAC secret from environment, assert real_execution_authorized/publication_authorized are false, write de-identified JSON evidence.
  - No placeholder literals.

- [x] **T-18D-02 — Implement Notebook 01: Materialize Kaggle Readiness**
  - Load N00 evidence, implement deterministic one-person/one-initial-MRI selection with baseline/sc rule and unresolved tie exclusion, require real runtime source for Phase 4 preprocessing (fail closed otherwise), maintain per-person PENDING/RUNNING/COMPLETED/FAILED states, reuse completed artifact only after SHA-256 verification, materialize to `/kaggle/working`, write de-identified provenance.
  - No placeholder artifacts.

- [x] **T-18D-03 — Implement Notebook 02: Verify Kaggle Readiness**
  - Load and validate N00/N01 evidence, verify OASIS counts/mapping from supplied evidence and raise BLOCKED_COHORT_MISMATCH on mismatch, validate model-ready/artifact coverage and hashes, generate deterministic person-level 5-fold source splits and 80/20 target partitions with exact intersection check and target-firewall manifest, run only small synthetic probes, write `KAGGLE_READINESS_EVIDENCE_PRODUCED` only after all checks pass.
  - No unconditional readiness.

- [x] **T-18D-04 — Implement Importer Script**
  - Make importer importable from tests, expose robust helpers, validate bundle-present hashes and external hash attestations, enforce binary task/order, manifests, exact target disjointness/firewall, privacy, state, OASIS counts, fail closed.
  - No placeholder identities/default hashes.

- [x] **T-18D-05 — Update Focused Tests**
  - Add `test_notebook_guards.py`, fix import path in importer tests, remove `hashlib` NameError, test missing input, placeholder absence, HMAC/privacy, split intersection/firewall, importer valid/invalid bundle, and no training invocation.

- [x] **T-18D-06 — Update Documentation**
  - Update `docs/PHASE18D_REPORT.md` to truthfully say preparation logic is implemented and Kaggle execution evidence is not yet imported; status remains `KAGGLE_NOTEBOOKS_READY_FOR_EXECUTION`.

- [x] **T-18D-07 — Update OpenSpec Tasks Artifact**
  - Create/update this tasks.md to reflect completed work.

## Verification

- [x] Run focused tests (importer and notebook guards) and verify they pass.
- [x] Run full test suite, Ruff, git diff --check, and notebook JSON/static checks.
