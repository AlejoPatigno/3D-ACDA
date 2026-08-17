# Phase 18 Report — Scientific Freeze Synchronization

## Current status

**Phase 18B remains `PHASE18B_IMPLEMENTATION_COMPLETE_EXTERNAL_BLOCKED`. Phase 18C readiness is not closed.** `docs/PHASE18B_REPORT.md` is the current implementation authority. The latest maintainer decision identifies the intended ADNI source as `https://www.kaggle.com/datasets/sanjukaggling/adnidataset` (`ADNI_dataset` on the Kaggle page), while deferring mounted-path resolution and model-ready artifact generation to Kaggle.

The following remain false: `authorized`, `freeze_approved`, `real_execution_authorized`, and `publication_authorized`. `phase_19_forbidden` remains true. No real training, predictive evaluation, preprocessing, concept/anatomy regeneration, publication analysis, or Phase 19 execution occurred. The prior native lifecycle attempt timed out with `mutation_outcome=not_started`; it was not retried and no receipt is fabricated.

## Resolved decisions and deferred external input

- `ad_new_2_19_2026.csv` is a metadata candidate, not an approved canonical ADNI manifest; its schema and hash must be verified in the intended Kaggle runtime.
- `ADNI_MODEL_READY_ROOT` is intentionally deferred while model-ready artifacts are generated externally in Kaggle. No fabricated or absent artifact is treated as model-ready or hashed.
- The canonical ADNI manifest, per-person model-ready hashes, binary cohort manifests/splits, binary freeze hash, and Phase 18C readiness remain unresolved external inputs.
- The retained scientific planning freeze below is not a binary freeze and does not authorize a real run.

## Retained Phase 18 planning status (not binary readiness)

**`PHASE18_SCIENTIFIC_FREEZE_COMPLETE_BUT_EXTERNAL_PROVENANCE_BLOCKED`**

The pre-run scientific protocol is frozen, but the real-run gate remains closed. No target outcome, real cohort, publication result, or Phase 19 action was inspected or executed.

| Control | Value |
|---|---|
| `scientific_freeze_complete` | `true` |
| `real_run_ready` | `false` |
| `freeze_approved` | `false` |
| `real_execution_authorized` | `false` |
| `publication_authorized` | `false` |
| `phase_19_forbidden` | `true` |
| `authorized` | `false` |

## Scientific resolution

Selected scientific fields are explicitly `RESOLVED_CANONICAL` or `RESOLVED_PRE_RUN_HUMAN`; no generic unresolved classification is used for selected decisions. Production `lambda_proto=1.0` is pre-run bound. Historical `lambda_proto=0.2` is an excluded non-production discrepancy, never target-selected. CORAL, MMD, CDAN, checkpoint, coefficient, epoch, optimizer, and seed decisions are likewise recorded before execution.

Both configurations contain the exact structured seven-method ledger. Each entry has a parameter mapping, value class, and mapping-valued evidence. Selected scientific decisions, the ledger, the seed policy, matrix content, and canonical freeze payload are content-hash bound.

## Matrix and ablations

- Methods: `source_only`, `coral`, `mmd`, `cdan`, `prototype_pseudo`, `aagn`, `faster_snn`.
- Directions: `adni_to_oasis`, `oasis_to_adni`; folds: `0..4`; seeds: `[42,43,44]`.
- Matrix: **210 training rows + 210 linked checkpoint projections = 420 rows**.
- Every checkpoint projection has `training_invocation=false` and schedules no training.
- Ablations are separate planning arithmetic under three seeds: **120 primary**, **60 supplementary**, and **120 excluded** cells. No ablation row was executed.

## Remaining blockers

1. In Kaggle, resolve the mounted path for `ADNI_dataset`, bind `ad_new_2_19_2026.csv`, and hash- and schema-verify it; the candidate is not yet a canonical manifest.
2. Generate the model-ready artifacts externally in Kaggle and return authoritative per-person hashes and provenance. `ADNI_MODEL_READY_ROOT` remains deferred.
3. Bind approved binary cohort manifests/splits, identities, target intersection evidence, and all required artifact/provenance hashes.
4. Resolve independent scientific review, privacy/data access, approved resources/real feasibility, and native lifecycle closure. The prior native lifecycle attempt timed out with `mutation_outcome=not_started`; it was not retried.
5. Obtain a separately approved binary freeze and explicit human authorization before any real execution or publication work. Phase 18C readiness remains unresolved.

No fake external hash was created. The binary freeze hash and unresolved provenance, feasibility, resource-budget, independent-review, and human-authorization hashes remain unresolved. Native lifecycle commands were not retried and no receipt was fabricated.

## Prohibited actions and next maintainer action

Do not run real training or predictive evaluation, preprocessing, concept/anatomy regeneration, Phase 19, publication analysis, or publication work. Do not create a binary freeze artifact, hash fabricated or absent model-ready artifacts, invent a local Kaggle mount, edit authorization or receipt state, or claim Phase 18B closure, a binary freeze hash, native lifecycle PASS, or `REAL_RUN_READY`.

The next maintainer action is external: complete the Kaggle path resolution, metadata verification, and model-ready artifact generation, then return the evidence for the still-open cohort, review, split, and lifecycle gates.

## Validation evidence

- Full regression with the final source/test candidate: `python -m pytest -q -p no:cacheprovider --basetemp=C:/Users/LOQ/AppData/Local/Temp/pada3dacb-full-suite-final` — exit 0, **1325 passed**, 6 warnings, 1213.18s (0:20:13). The cache plugin was disabled only to avoid the known Windows `.pytest_cache` access-denied interference; test behavior was unchanged.
- `python -m pytest -q tests/phase_18/ -p no:cacheprovider --basetemp=C:/Users/LOQ/AppData/Local/Temp/pada3dacb-phase18-final` — exit 0, **147 passed**, 22.76s.
- `python -m ruff check .` — exit 0, all checks passed.
- `git diff --check` — exit 0.
- Repeated canonical hash check — exit 0 for both configs. Matrix: `4856bff8fd631f10c6473194064365d8bb55bb72ce5e5b68e4ca3209f3bf82ea`; scientific resolution: `3421e7d764986496a58eb5a83506ed2e68c8b478f8ae45dbaf5676120de27fb0`; ledger: `dff9e3917728889737fe1582aaa6f9cecc21fb2d63ec11dfbed5654dffd7f979`; seed policy: `9a7d5c7c8130c8b434709a1240398f5d5ee5d487760268a6b4f1aa48a82dbb71`; historical/planning canonical freeze payload (not a binary freeze hash): `153e6baeb16211dd4aae9d226dbf1be1a8930831b956ee2780af90a7f3b4adb6`.
- `python scripts/check_real_run_authorization.py --config configs/publication/real_run_authorization.yaml` — exit 1 as required; printed `REAL RUN NOT AUTHORIZED` and `PASS — FAIL-CLOSED AUTHORIZATION VERIFIED`.

No real data, training, evaluation, publication analysis, publication metric, or Phase 19 artifact was created.
