# Phase 18B Binary Label Space Report

## Executive status

Phase 18B task-scoped binary implementation and repository validation are complete. Phase 18B is **not closed**, is not scientifically authorized, and must not be treated as a real-run or publication authorization. The remaining blockers are external cohort authority/provenance, independent scientific review, native lifecycle closure, and a separately approved binary freeze.

The implemented task is `cn_vs_impaired`, with fixed class order `CN=0` and `Impaired=1`. All real training, real predictive evaluation, preprocessing rerun, concept/anatomical regeneration, publication analysis, and Phase 19 execution remain absent.

```yaml
phase18b_status: PHASE18B_IMPLEMENTATION_COMPLETE_EXTERNAL_BLOCKED
binary_task: cn_vs_impaired
focused_tests: 83
full_tests: 1408
real_training: false
real_evaluation: false
authorized: false
freeze_approved: false
real_execution_authorized: false
publication_authorized: false
phase_19_forbidden: true
```

## Resolved maintainer decisions

- The intended ADNI source identity is `https://www.kaggle.com/datasets/sanjukaggling/adnidataset`.
- The Kaggle page exposes the dataset as `ADNI_dataset`. The mounted filesystem path is intentionally unresolved and must be discovered inside the intended Kaggle runtime; no local path is invented.
- `ad_new_2_19_2026.csv` is the metadata candidate. It is not an approved canonical manifest and must be hash- and schema-verified when bound in the intended runtime.
- `ADNI_MODEL_READY_ROOT` is intentionally deferred while model-ready artifacts are generated externally in Kaggle. No absent or fabricated artifact is treated as model-ready, and no such artifact is hashed here.

## Evidence and deferred external input

The implementation and repository validation evidence below remain valid. They establish task-scoped implementation only. The Kaggle-bound metadata, model-ready artifacts, per-person hashes, binary cohort manifests/splits, and their provenance are external/deferred inputs and are not present as approved Phase 18B evidence in this repository.

## OASIS evidence, mapping, counts, and person policy

The supplied OASIS inputs are external, untracked inputs and are not outputs to commit:

- CSV SHA256: `b223c39f83d811356675e8711e9906b1cba95ea1a110f3117a61923a72d1d1f1`
- Notebook SHA256: `588bc2a6c214fd99e2900dd45357ec2fa235cbe1670a1ab99c87c5bf2726e41b`
- 436 visits
- 416 canonical persons
- 20 longitudinal duplicate visits
- Observed CDR domain: `{0, 0.5, 1, 2}`
- Canonical person counts: 316 CN and 100 Impaired
- Target planning partition: 332 adaptation persons and 84 evaluation persons
- Person intersection between adaptation and evaluation: 0
- HMAC key identifier/version may be recorded; the HMAC key is never recorded or exposed

The structural mapping contract is closed over the observed domain: `0 -> CN`, and positive observed values `0.5`, `1`, and `2` -> `Impaired`. The person policy canonicalizes longitudinal visit stems, retains the selected canonical visit, excludes longitudinal duplicates, and rejects conflicting person-level values. Splits are person-level, not visit-level.

Structural evidence and de-identified artifacts are present. This does **not** constitute scientific approval: `semantics_approved=false` remains correct because the required independent/native OASIS approval is absent.

## ADNI mapping and deferred model-ready/provenance blocker

The intended ADNI source identity is resolved to the maintainer-supplied Kaggle dataset:

- Source URL: `https://www.kaggle.com/datasets/sanjukaggling/adnidataset`
- Kaggle dataset name exposed by the page: `ADNI_dataset`
- Mounted filesystem path: **must be resolved inside Kaggle; not observed locally and not invented**
- Metadata candidate: `ad_new_2_19_2026.csv`

The implemented ADNI mapping contract is:

- `CN -> CN`
- `MCI -> Impaired`
- `AD -> Impaired`

The canonical ADNI vocabulary is restricted to `CN`, `MCI`, and `AD`; unknown, malformed, missing, unsupported, duplicate, or conflicting assignments must fail closed or be excluded under the recorded policy. The candidate CSV is not yet an approved canonical manifest. Its schema and hash must be verified when it is bound in the intended Kaggle runtime.

`ADNI_MODEL_READY_ROOT` remains intentionally deferred while model-ready artifacts are generated externally in Kaggle. The canonical ADNI manifest, per-person model-ready hashes, binary cohort manifests/splits, and their provenance therefore remain unavailable as approved evidence. `configs/data/adni.yaml` still has `root` and `metadata_csv` set to null; no local mounted path, ADNI counts, hashes, real split identities, or real cohort claims are asserted here.

## Binary contracts, models, losses, methods, and ablations

The task-scoped implementation covers the binary data spine, target-label firewall, checkpoint identity/checkpoint loading boundary, prediction/evaluation schemas, concept routing/reuse, three-class rejection, and task-scoped runtime boundary.

Contracts include `(B,2)` raw classifier logits, target IDs `{0,1}`, PyTorch-style `CrossEntropyLoss`, fixed probability tolerances, lower-index CN tie-breaking, nullable undefined metrics with reasons, active rejection of legacy `prob_mci`/`prob_ad`, and no target diagnosis in adaptation inputs. CDAN uses `z_dim * n_classes` (including `(128,2) -> 256`) with gradients to both feature and prediction paths. Prototype/pseudo handling covers absent class 0, absent class 1, and zero loss for an empty accepted pseudo-set. Three-class checkpoints and partial loads fail closed.

The five core method surfaces are source-only, CORAL, MMD, CDAN, and prototype-pseudo. AAGN and FasterSNN are covered as binary task-scoped surfaces. Six approved ablations have effective loss-component interventions; excluded variants remain rejected. `mean_pool` changes architecture identity without silently changing loss components.

## Splits, target firewall, prediction, Phase 15, and Phase 16

Target adaptation is label-free. Target evaluation is disjoint from adaptation, with the recorded planning arithmetic of 332 adaptation persons, 84 evaluation persons, and zero person intersection. Real binary split manifests and hashes are not available; the disposition remains `REGENERATE_BINARY_SPLITS_REQUIRED` unless exact binary validity is later proven against approved cohort inputs.

Binary prediction export and evaluation use fixed CN/Impaired order, a 2x2 confusion matrix, nullable undefined metrics, and source-validation macro-F1 checkpoint selection. The Phase 15 compatibility boundary is preserved without producing real evaluation results.

The Phase 16 concept-evaluation boundary reuses the existing `c_target`, `g_bar`, normalizer, ROI ordering, atlas, masks, and Jacobian identities. No concept or anatomical artifacts were regenerated and no publication analysis was run.

## Artifact compatibility

Only de-identified Phase 18B artifacts are eligible outputs. The supplied raw CSV and notebook remain external/untracked inputs and must not be committed. Historical three-class Phase 18 files and compatibility surfaces are preserved and are not rewritten. Binary runtime APIs reject historical three-class checkpoints, identities, and active legacy prediction fields rather than partially loading or silently reinterpreting them.

## Identities and supersession

Binary-bound identities are distinct for experiment, split, model/checkpoint, training metadata, evaluation result, and freeze families. Historical three-class identity collisions are rejected. New binary artifacts are marked as superseding the historical label-space contract where applicable; supersession does not mutate, approve, or replace the historical Phase 18 freeze.

## Matrix 390 planning arithmetic

The Phase 18B matrix total is **390 planned cells**. This is planning arithmetic only: it is not a count of executed runs, trained models, evaluations, publication results, or approved artifacts. Executed real cells remain zero because real execution is unauthorized and the ADNI manifest is unavailable.

## Reviews

- Final independent mathematical review: **PASS**. The 83 focused tests passed, mathematical contracts were checked, and the empty-kappa null policy was verified.
- Final independent scientific/provenance review: **BLOCKED**. The ADNI canonical manifest, verified metadata, model-ready provenance, and per-person hashes remain deferred, and no cryptographically/native-authority-bound OASIS approval is present.
- OASIS structural mapping is verified, but `semantics_approved=false` remains the truthful state.
- No review result authorizes real execution, publication, or Phase 19.

## Validation commands and results

- `python -m pytest -q tests/phase_18b -p no:cacheprovider --basetemp=C:/p18b-focused-final5`: exit 0, **83 passed**, one environmental cache warning, 79.97s.
- `python -m pytest -q -p no:cacheprovider --basetemp=C:/p18b-full-final5`: exit 0, **1408 passed**, six warnings, 509.35s (8:29). Warnings were four sklearn single-class ROC-AUC warnings and two PyTorch degrees-of-freedom warnings.
- `python -m pip install -e .`: exit 0.
- Import/version validation: exit 0; version `0.1.0`.
- `python -m ruff check .`: exit 0, `All checks passed!`.
- `git diff --check`: exit 0.
- `python scripts/evaluate_binary.py --validate-only`: exit 0.
- `python scripts/evaluate_binary_concepts.py --validate-only`: exit 0.
- The real-run authorization checker exited 1 and failed closed, as required.

These results establish implementation and validation evidence only. They do not establish cohort approval or scientific authorization.

## Authorization and native lifecycle

The following remain false: `freeze_approved`, `real_execution_authorized`, and `publication_authorized`. `phase_19_forbidden` remains true. No real training, real predictive evaluation, preprocessing rerun, concept/anatomical regeneration, publication analysis, or Phase 19 occurred.

There is no Phase 18B native lifecycle receipt. The previous lifecycle status attempt timed out with `mutation_outcome=not_started`. No receipt is fabricated or edited; historical receipt/state files remain preserved.

## Remaining blockers

1. In Kaggle, resolve the mounted path for `ADNI_dataset`, bind `ad_new_2_19_2026.csv`, and hash- and schema-verify it as the intended-runtime metadata candidate; it is not yet a canonical manifest.
2. Generate or bind the model-ready artifacts externally in Kaggle, then record per-person model-ready hashes and authoritative provenance. `ADNI_MODEL_READY_ROOT` remains deferred until that external work is complete.
3. Obtain cryptographically/native-authority-bound approval of the supplied OASIS metadata, mapping, person policy, and preprocessing provenance.
4. Complete the independent scientific/provenance review after those inputs exist; mathematical PASS alone is insufficient.
5. Regenerate or prove binary cohort manifest and split validity against the approved inputs and record exact identities/hashes.
6. Obtain native lifecycle closure and create a separately approved binary freeze identity without changing historical Phase 18 artifacts. The prior lifecycle attempt timed out with `mutation_outcome=not_started`; it was not retried.
7. Explicitly authorize any later real execution and publication work; none is authorized by this report.

## Explicit non-actions

This closure pass did not run real training or evaluation, rerun preprocessing, regenerate concepts or anatomy, produce publication analysis, execute Phase 19, invent ADNI counts or hashes, commit supplied raw inputs, edit historical Phase 18 authorization/freeze, edit receipts, or claim Phase 18B complete.

## Prohibited actions and next maintainer action

Do not run real training or predictive evaluation, preprocessing, concept/anatomy regeneration, Phase 19, publication analysis, or publication work. Do not create a binary freeze artifact, hash fabricated or absent model-ready artifacts, invent a local Kaggle mount, edit authorization or receipt state, retry the prior native lifecycle attempt, or claim Phase 18B closure, a binary freeze hash, native lifecycle PASS, or `REAL_RUN_READY`.

The next maintainer action is external: in Kaggle, resolve the mounted `ADNI_dataset` path, verify `ad_new_2_19_2026.csv` by schema and hash, generate the model-ready artifacts, and return their authoritative per-person provenance/hashes. Only after those inputs and the still-open OASIS, review, split, and native lifecycle gates are resolved may the project consider a separately approved binary freeze. Until then, the state is `PHASE18B_IMPLEMENTATION_COMPLETE_EXTERNAL_BLOCKED`.
