# Phase 18D Kaggle Readiness Acceptance

## Acceptance rule

Phase 18D is accepted only as a readiness-evidence implementation when every mandatory gate below passes and an independent reviewer records PASS. Acceptance does not authorize real training, predictive evaluation, publication analysis, a binary freeze, or Phase 19.

## Evidence gates

### A. Notebook boundary

- [ ] `00_discover_kaggle_inputs.ipynb`, `01_materialize_kaggle_readiness.ipynb`, and `02_verify_kaggle_readiness.ipynb` are standalone.
- [ ] No notebook trains, evaluates predictions, performs publication analysis, or invokes Phase 19.
- [ ] Model-ready generation, if any, is Kaggle-only and uses the approved Phase 4 contract.

### B. Discovery and provenance

- [ ] Discovery recursively inspects `/kaggle/input` by contents and records relative paths.
- [ ] No fixed or guessed mount path is present.
- [ ] `ad_new_2_19_2026.csv` is treated as a candidate until exact schema and SHA-256 verification passes.
- [ ] `source_provenance.json`, `metadata_manifest.json`, and all artifact hashes use exact bytes and lowercase 64-character SHA-256.
- [ ] Source URL and observed dataset name are recorded; unresolved external values remain blocking decisions.

### C. Privacy and canonicalization

- [ ] No raw subject IDs, raw-ID filenames, secrets, or HMAC keys occur in emitted evidence.
- [ ] HMAC-SHA256 tokens and key ID/version are recorded; the key is not.
- [ ] ADNI mapping is exactly `CN -> CN=0`, `MCI -> Impaired=1`, `AD -> Impaired=1`.
- [ ] Exactly one canonical person and one initial MRI are selected per person; ambiguity fails closed.
- [ ] Per-subject status and reason are present; reuse is hash-verified.

### D. Preprocessing, concept/anatomy, and OASIS

- [ ] Only the approved Phase 4 preprocessing identity is reused.
- [ ] Existing `c_target`, `g_bar`, normalizer, ROI ordering, atlas, masks, and Jacobian artifacts are validated read-only.
- [ ] No refit, regeneration, or label-migration rewrite occurs.
- [ ] OASIS policy matches CDR `{0, 0.5, 1, 2}`, mapping `0 -> CN` and positive values -> `Impaired`, 436 visits, 416 persons, 20 duplicates, 316/100 class counts, 332/84 target partition, and zero target intersection.
- [ ] Any OASIS mismatch emits exactly `BLOCKED_COHORT_MISMATCH` and blocks import.

### E. Splits and target firewall

- [ ] Source folds are person-level and disjoint.
- [ ] Target adaptation and target evaluation are fixed, person-level, 332/84 partitions with zero intersection.
- [ ] The manifest proves that target evaluation identities and derived data cannot enter adaptation or source-fold inputs.
- [ ] No training, checkpoint selection, or predictive evaluation is performed by this change.

### F. Repository import and states

- [ ] `scripts/import_kaggle_readiness.py` is read-only and validates an explicit evidence root.
- [ ] Focused tests use synthetic data only and cover negative paths.
- [ ] The only accepted states are `KAGGLE_NOTEBOOKS_READY_FOR_EXECUTION` and `KAGGLE_READINESS_EVIDENCE_IMPORTED`.
- [ ] No `REAL_RUN_READY*` state or equivalent is emitted.
- [ ] `authorized=false`, `real_execution_authorized=false`, `freeze_approved=false`, `publication_authorized=false`, and `phase_19_forbidden=true` remain true/false exactly as named.

## Exact validation commands

```bash
python -m pytest -q tests/phase_18d -p no:cacheprovider --basetemp=C:/p18d-focused
python scripts/import_kaggle_readiness.py --validate-only --evidence-root "%KAGGLE_READINESS_EVIDENCE_ROOT%"
python -m ruff check scripts/import_kaggle_readiness.py tests/phase_18d
git diff --check
```

Expected results: focused tests exit 0; the validator exits 0 only for a complete valid evidence bundle; Ruff exits 0; `git diff --check` exits 0. The validator must fail closed for each negative case listed in `requirements.md`.

## Independent review gate

Before implementation closure, an independent reviewer must verify this acceptance checklist against the actual diff and validation outputs. Review must specifically inspect dynamic discovery, privacy/hash evidence, OASIS mismatch behavior, person-level split firewall, read-only importer behavior, forbidden-action markers, false authorization flags, and absence of Phase 19. A review finding marked BLOCKED or FAIL prevents closure; no state edit may override it.
