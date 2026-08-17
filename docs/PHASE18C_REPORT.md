# Phase 18C Audit Report — Binary Real-Run Readiness

> Historical snapshot: the original Phase 18C audit is preserved below. It records an earlier repository state and must not be read as the current Phase 18B implementation state. Current authority is `docs/PHASE18B_REPORT.md`.

## Current status

**Phase 18C readiness remains `REAL_RUN_BLOCKED_EXTERNAL_REQUIREMENTS`; it is not closed and is not `REAL_RUN_READY`.** Current Phase 18B authority remains `PHASE18B_IMPLEMENTATION_COMPLETE_EXTERNAL_BLOCKED`.

The maintainer has resolved the intended ADNI source identity to `https://www.kaggle.com/datasets/sanjukaggling/adnidataset`, exposed as `ADNI_dataset` on the Kaggle page. The mounted path must be resolved inside Kaggle and must not be invented locally. `ad_new_2_19_2026.csv` is a metadata candidate, not an approved canonical manifest; it requires schema and hash verification in the intended runtime. `ADNI_MODEL_READY_ROOT` is intentionally deferred while model-ready artifacts are generated externally in Kaggle.

`authorized=false`, `freeze_approved=false`, `real_execution_authorized=false`, `publication_authorized=false`, and `phase_19_forbidden=true` remain in force. No canonical ADNI manifest, per-person model-ready hashes, binary cohort manifests/splits, binary freeze hash, or Phase 18C readiness closure is claimed.

## Resolved decisions and evidence

- The source identity is known, but the external mounted path, candidate metadata verification, model-ready artifacts, and provenance remain deferred.
- The retained three-class freeze hash in the historical snapshot is historical/planning evidence only; it is not a binary freeze hash and does not authorize execution.
- The prior native lifecycle attempt timed out with `mutation_outcome=not_started`; it was not retried, and no receipt was fabricated or edited.
- No real training, predictive evaluation, preprocessing, concept/anatomy regeneration, publication analysis, Phase 19 execution, or publication work occurred.

## Deferred external input and remaining blockers

1. In Kaggle, resolve the mounted `ADNI_dataset` path, verify `ad_new_2_19_2026.csv` by schema and hash, and bind it only if it satisfies the canonical-manifest contract.
2. Generate model-ready artifacts externally in Kaggle and return authoritative per-person hashes/provenance; `ADNI_MODEL_READY_ROOT` remains deferred until then.
3. Resolve OASIS scientific/native approval, independent scientific/provenance review, binary cohort manifests/splits and identity-level intersection evidence, required artifact hashes, and native lifecycle closure.
4. Separately approve any binary freeze and obtain explicit real-run/publication authorization. Phase 19 remains forbidden.

## Prohibited actions and next maintainer action

Do not run real training or predictive evaluation, preprocessing, concept/anatomy regeneration, Phase 19, publication analysis, or publication work. Do not create a binary freeze artifact, hash fabricated or absent model-ready artifacts, invent a local Kaggle mount, edit receipts or authorization state, retry the prior native lifecycle attempt, or claim Phase 18B closure, binary freeze hash, native lifecycle PASS, or `REAL_RUN_READY`.

The next maintainer action is external Kaggle work only: resolve the mount, verify the candidate metadata, generate model-ready artifacts, and return their authoritative provenance/hashes. The remaining gates must then be independently and natively resolved before any authorization decision.

## Historical snapshot (preserved)

## Historical snapshot decision

**BLOCKED.** This audit cannot conclude READY. Phase 18B is still `planning` / `not_started`, its OASIS semantics gate is blocked, both required fallback reviews remain pending and non-authorizing, and the active production runtime still exposes the historical three-class task (`CN`, `MCI`, `AD`). Phase 18C therefore records no binary authorization and no scientific result.

```yaml
phase_18c_status: BLOCKED
real_run_state: REAL_RUN_BLOCKED_EXTERNAL_REQUIREMENTS
freeze_hash: 153e6baeb16211dd4aae9d226dbf1be1a8930831b956ee2780af90a7f3b4adb6
authorized: false
real_execution_authorized: false
publication_authorized: false
phase_19_forbidden: true
```

## 1. Phase 18B closure evidence

The historical snapshot's source state recorded `status: planning` and `implementation_status: not_started` at the time of that audit. Its then-current evidence also recorded a blocked OASIS gate because the canonical OASIS manifest and metadata-generation provenance were not approved/present, with both fallback reviews pending and non-authorizing. Do not use those historical values as the current Phase 18B state; the current state is maintained separately in `openspec/changes/phase-18b-binary-label-space/state.yaml` and `docs/PHASE18B_REPORT.md`.

The normative acceptance package says acceptance is **Not accepted** and no criterion is claimed passed (`specs/phase_18b_binary_label_space/acceptance.md:3`). It permits only documentation, specification maintenance, and synthetic contract-test planning before both gates pass, and explicitly prohibits calling that work implementation (`:7-14`).

**Explicit block:** production implementation, OASIS mapping, real splits, real execution, publication analysis, native lifecycle claims, receipt edits, and Phase 19 remain forbidden (`specs/phase_18b_binary_label_space/requirements.md:7-17`; `state.yaml:151-179`).

## 2. Binary task identity required versus observed

| Item | Required by Phase 18B | Observed in repository |
|---|---|---|
| Task | Exactly `CN` versus `Impaired` | Planning contract only; no binary runtime implementation (`state.yaml:60-67`). |
| IDs/order | `CN=0`, `Impaired=1` | Specified, not runtime-enforced by the active model. |
| ADNI mapping | `CN -> CN`; `MCI -> Impaired`; `AD -> Impaired`, retaining original diagnosis provenance | Specified in `requirements.md:35-45` and `label_mapping.md`; no production implementation is authorized. |
| OASIS mapping | Approved canonical metadata/provenance; no guessing | Blocked: `configs/data/oasis.yaml:1-4` has `root: null` and `metadata_csv: null`; no approved real manifest is present (`requirements.md:51-61`). No OASIS MCI may be invented. |
| Active runtime | Binary head and binary identity | **Three-class.** `src/pada3dacb/data/records.py:11-12` defines `CLASS_ORDER = ("CN", "MCI", "AD")`; `src/pada3dacb/models/pada3dacb.py:20,107,115-116` retains the same fixed three-class contract. |

The observed runtime is therefore not the required binary task. Historical three-class records and identities must remain preserved rather than silently recoded (`requirements.md:101-103`).

## 3. ADNI/OASIS mappings and class-count/split evidence

ADNI semantics are a **planning contract**, not a real cohort observation: `CN` maps to `CN`, while `MCI` and `AD` map to `Impaired`, with original labels retained (`specs/phase_18b_binary_label_space/label_mapping.md`; `requirements.md:35-45`).

OASIS semantics are **NOT VERIFIED/BLOCKED**. The configured root and metadata CSV are null (`configs/data/oasis.yaml:1-4`), the canonical manifest and generation provenance are absent, and the legacy loader's historical `CDR==0 -> CN` / other numeric CDR -> historical `AD` behavior is evidence only (`requirements.md:51-61`). No OASIS MCI category is invented.

Real class counts, real ADNI/OASIS manifests, and approved split manifests are **NOT VERIFIED/BLOCKED**. The Phase 18 authorization manifest explicitly leaves `split_manifest_hashes.ADNI` and `.OASIS` unresolved (`configs/publication/real_run_authorization.yaml:61-63`) and the acceptance contract states that no real split manifest or class count is claimed (`requirements.md:65`).

## 4. Binary split hashes and target-assignment intersection

**NOT VERIFIED/BLOCKED.** Binary split regeneration is required by default: `REGENERATE_BINARY_SPLITS_REQUIRED` (`state.yaml:89-95`; `requirements.md:65`). `configs/publication/real_run_authorization.yaml:61-72` leaves source, target-adaptation, and target-evaluation assignment hashes unresolved and contains empty subject-hash lists. Consequently, no content-level target-adaptation/target-evaluation intersection has been computed from approved identities. Aggregate hashes alone would be insufficient; the required identity-level intersection remains missing.

## 5. Artifact identities

All production artifact identities are **UNRESOLVED/MISSING** for this audit:

- MRI tensors and approved derivative/input manifests: **NOT VERIFIED/BLOCKED**; no approved real-data manifest or tensor identity is bound.
- Atlas, ROI order, and ROI masks: unresolved (`configs/publication/real_run_authorization.yaml:73-80`).
- Concept normalizer and concept targets: unresolved (`:73-80`).
- Jacobians/anatomical artifacts: unresolved (`:73-80`).
- Supporting provenance, configuration, environment, command, and target identities: unresolved (`:83-95`).

The Phase 18 report independently records these external provenance blockers (`docs/PHASE18_REPORT.md:35-37`). Synthetic or historical artifacts do not close the binary real-run identity gate.

## 6. Model two-logit/CDAN verification

The required binary contract is two raw task logits shaped `(B,2)`, integer targets `{0,1}`, PyTorch-style `CrossEntropyLoss`, runtime CDAN width `z_dim * n_classes`, and gradient flow to both `z` and `p` without detach (`specs/phase_18b_binary_label_space/requirements.md:71-75`; `acceptance.md:53-60`).

That contract is **not satisfied by the active runtime**. `src/pada3dacb/models/pada3dacb.py:107,115-116` defaults to and enforces three classes. `src/pada3dacb/experiments/cdan.py:202-208` computes CDAN width from the configured class count, whose default is `3` at `:205`; the binary `(128,2)->256` and distinct `(64,2)->128` verification has not been implemented or passed. No binary checkpoint or two-logit runtime identity is authorized.

## 7. Prediction, Phase 15 evaluation, and Phase 16 concept-evaluation contracts

The required Phase 18B prediction contract activates only `prob_cn` and `prob_impaired`, rejects active `prob_mci` and `prob_ad`, and uses a 2x2 confusion matrix (`requirements.md:89-93`; `acceptance.md:66-72`).

Observed current contracts remain three-class:

- Phase 15 requirements still declare fixed `CN=0,MCI=1,AD=2` (`specs/phase_15_predictive_evaluation/requirements.md:3`). Its output schema includes `prob_cn`, `prob_mci`, and `prob_ad` (`output_schema.md`, subject-prediction schema section).
- The active serializer emits `prob_cn`, `prob_mci`, and `prob_ad` from a three-element probability tuple (`src/pada3dacb/evaluation/tables.py:56-59,204-209`).
- Phase 16 output and subject contracts likewise describe `true_label` and latent/concept probabilities for `0/1/2` and `CN/MCI/AD` (`specs/phase_16_concept_validation/output_schema.md`, subject-output section).

No binary prediction export, binary Phase 15 evaluation, or binary Phase 16 concept evaluation is present or verified. Historical three-class evaluation contracts cannot authorize a Phase 18C binary run.

## 8. Scientific freeze values and freeze identity

The exact inherited pre-run canonical freeze hash is:

`153e6baeb16211dd4aae9d226dbf1be1a8930831b956ee2780af90a7f3b4adb6`

The freeze binds **pre-run planning values**, not a binary freeze. Repository evidence records methods `source_only`, `coral`, `mmd`, `cdan`, `prototype_pseudo`, `aagn`, and `faster_snn`; directions `adni_to_oasis` and `oasis_to_adni`; folds `0..4`; and seeds `[42,43,44]` (`docs/PHASE18_REPORT.md:21-23,28-31`). It also records pre-run values such as `lambda_proto=1.0`, fixed epochs, optimizer values, and adaptation settings in the planning authorization manifest (`configs/publication/real_run_authorization.yaml:120-316`).

This is not binary authorization: the authorization manifest remains `freeze_approved: false`, `real_execution_authorized: false`, `publication_authorized: false`, and `authorized: false` (`:3-6`), while its binary-relevant split, assignment, artifact, identity, review, and human-authorization fields remain unresolved. `binary_freeze_claimed: false` is explicit (`openspec/changes/phase-18b-binary-label-space/state.yaml:89-95`).

## 9. Ablations and matrix arithmetic

The planning arithmetic is recorded as follows:

| Planning bucket | Count | Status |
|---|---:|---|
| Core | 210 | Planning only |
| Primary ablations | 120 | Planning only |
| Supplementary ablations | 60 | Planning only |
| **Count used for this audit** | **390** | `210 + 120 + 60` |

Checkpoint projections are **not counted** in the 390. The inherited core matrix separately contains 210 training rows plus 210 non-training checkpoint projections (`docs/PHASE18_REPORT.md:28-31`; `specs/phase_18_experiment_freeze/experiment_matrix.md:20-24`). Excluded ablation cells are not included in the requested 390 arithmetic. No ablation row was executed (`docs/PHASE18_REPORT.md:31`; `resource_budget.md:21`).

## 10. Resource readiness

The audit host record is: **Windows AMD64**, **Python 3.11.9**, **torch 2.13.0+cpu**, **CUDA unavailable to PyTorch**, approximately **25.46 GB RAM**, and approximately **64.15 GB free storage**.

These facts are observational only. This is not an approved intended GPU environment, does not provide GPU/VRAM or approved wall-time evidence, and cannot close readiness. The Phase 18 resource contract explicitly says real resources are externally blocked and no hardware observation or real run was performed (`specs/phase_18_experiment_freeze/resource_budget.md:3-5,23-27`). No real feasibility probe was run for Phase 18C.

## 11. Privacy/access record

**ABSENT / NOT VERIFIED.** `privacy_data_access_record_hash` remains unresolved (`configs/publication/real_run_authorization.yaml:91-93`), and the authorization checker reported missing privacy/data-access evidence. No approved privacy, access, or data-use record is available to authorize real ADNI/OASIS access.

## 12. Native lifecycle

The exact native status operation was attempted:

```text
gentle-ai review status --cwd C:/Users/LOQ/Desktop/PADA-3DACB --contract gentle-ai.review-integration/v1 --next-transition
```

It **timed out**. The recorded outcome is `mutation_outcome: not_started`; there was no receipt transition. No native lifecycle claim is made. The existing receipt lineage `review-1d63ad8511d6bbf5` is not a Phase 18C authorization and cannot substitute for binary runtime, OASIS, provenance, or human authorization evidence. Phase 18B itself forbids receipt edits (`state.yaml:10-17`; `acceptance.md:14`).

## 13. Independent audit

Kimi was unavailable. The Phase 18B plan records fresh fallback substitutions for Kimi and Gemini CLI, but both fallback reviews remain pending and non-authorizing (`specs/phase_18b_binary_label_space/agent_plan.yaml:5-21`; `state.yaml:27-41`). Independent verification contexts also recorded Phase 18/runtime/provenance blockers, including incomplete closure evidence, unresolved real resources, absent real-data provenance, and no authorizing final review (`specs/phase_18_experiment_freeze/agent_plan.yaml:73-79,107-112`).

Therefore: **no authorizing independent review exists**. A fallback context finding blockers is not an authorization pass.

## 14. Validation evidence

Validation executed for this audit:

- `python -m pip install -e .` — **exit 0**, editable install succeeded; dependencies were already satisfied.
- `python -c "import pada3dacb; print(pada3dacb.__version__)"` — **exit 0**, version `0.1.0`.
- `python -m pytest -q tests/phase_18 -p no:cacheprovider --basetemp=/tmp/pada3dacb-phase18c-focused` — **exit 0**, **147 passed**, 0 warnings, 50.09 seconds.
- `python -m pytest -q` — **exit 0**, **1325 passed**, **7 warnings**, 1287.46 seconds (21:27). Warnings: four single-class ROC-AUC warnings, two degrees-of-freedom warnings, and one Windows pytest-cache permission warning.
- `python -m ruff check .` — **exit 0**, `All checks passed!`.
- `git diff --check` — **exit 0**.
- `python scripts/check_real_run_authorization.py --config configs/publication/real_run_authorization.yaml` — **exit 1**, printed `REAL RUN NOT AUTHORIZED`, listed unresolved external blockers, and printed `PASS — FAIL-CLOSED AUTHORIZATION VERIFIED`.

These passing tests validate the current repository contracts; they do not verify Phase 18B implementation, binary runtime readiness, real artifact provenance, or Phase 18C authorization.

## 15. Remaining authorization blockers

The following blockers remain open:

1. Phase 18B closure is still planning/not_started.
2. Canonical OASIS manifest, metadata-generation provenance, and approved OASIS policy are absent.
3. Both independent fallback reviews are pending and non-authorizing.
4. Active runtime and serializers remain three-class.
5. Binary ADNI/OASIS class counts and approved real manifests are unavailable.
6. Binary split hashes and identity-level target assignment intersection are missing.
7. MRI tensors, input/manifests, atlas, ROI order/masks, concept normalizer/targets, and Jacobians are not identity-bound.
8. Binary two-logit model, CDAN `(z,2)` verification, checkpoint compatibility, prediction, Phase 15, and Phase 16 contracts are not satisfied.
9. Privacy/data-access, resource approval, and real feasibility evidence are absent.
10. Native receipt transition and Phase 18C authorization are absent.
11. Human real-run authorization, statistical review, and publication authorization are absent.

## 16. Exact final state

`REAL_RUN_BLOCKED_EXTERNAL_REQUIREMENTS`

## 17. Explicit confirmations

- No target result selected any scientific decision.
- No real ADNI/OASIS data was loaded.
- No real training or predictive evaluation was run.
- No preprocessing was rerun.
- No concept or anatomical artifact was regenerated.
- Real execution is false.
- Publication is false.
- Phase 19 was not started and remains forbidden.
- No authorization flag, native receipt, historical Phase 18 artifact, split, manifest, or runtime implementation was changed by this audit.

This report is documentation-only and does not authorize any subsequent production implementation or real execution.
