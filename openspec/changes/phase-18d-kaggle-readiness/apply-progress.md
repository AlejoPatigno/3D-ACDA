# Phase 18D Apply Progress

## Current state

`KAGGLE_NOTEBOOKS_READY_FOR_EXECUTION`

Repository-side preparation logic is implemented. Kaggle execution, evidence import, independent scientific closure, binary freeze, real training/evaluation, publication analysis, and Phase 19 remain unstarted.

## Completed implementation work

- Created the required standalone notebooks:
  - `notebooks/kaggle/00_kaggle_input_binding.ipynb`
  - `notebooks/kaggle/01_kaggle_binary_artifact_preparation.ipynb`
  - `notebooks/kaggle/02_kaggle_real_run_readiness.ipynb`
- Implemented dynamic `/kaggle/input` discovery, exact metadata hashing/schema validation, HMAC privacy boundary, fail-closed authorization checks, and de-identified binding outputs.
- Implemented one-person/one-initial-MRI selection, unresolved-tie failure, resumable per-person statuses, hash-verified reuse, and the approved Phase 4 `run_preprocessing` call boundary.
- Implemented OASIS exact-count/mapping verification, concept/anatomy reuse validation, deterministic source folds, fixed target partitions, target disjointness, target firewall, and synthetic-only probe logic.
- Implemented `scripts/import_kaggle_readiness.py` as an explicit-input read-only validator. It recomputes hashes only for files present in the bundle and treats absent external source hashes as attestations.
- Added CPU-only focused tests under `tests/phase_18d/`.
- Updated `docs/PHASE18D_REPORT.md` and OpenSpec state/tasks.

## Validation evidence

- Focused Phase 18D tests: exit 0, 8 passed.
- Full repository tests: exit 0, 1416 passed, 6 expected warnings.
- Scoped Ruff for Phase 18D Python: exit 0.
- Notebook JSON/static guards: exit 0.
- Python compile check for importer: exit 0.
- `git diff --check`: exit 0.
- `graphify update .`: exit 0.
- Full `python -m ruff check .`: exit 1 because of the pre-existing unrelated untracked `run_checks.py`; that file was not modified.

## Open tasks

- [ ] Run the notebooks in Kaggle and return the de-identified readiness bundle.
- [ ] Validate/import the returned bundle with the repository importer.
- [ ] Obtain final independent scientific/provenance review and native lifecycle closure.
- [ ] Create the binary freeze only after imported evidence and closure gates pass.
- [ ] Obtain explicit human authorization before any real execution or publication.

## Safety boundary

`authorized=false`, `real_execution_authorized=false`, `freeze_approved=false`, `publication_authorized=false`, and `phase_19_forbidden=true` remain unchanged. No Kaggle path, external hash, subject identifier, secret, predictive result, or publication claim is asserted by this artifact.
