# Phase 18 — Experiment Freeze and Preflight Decisions

## Decision status

**Preflight record created; Phase 18 is not scientifically freeze-ready.** This file records the authorized protocol-freeze scope, inherited Phase 17 evidence, canonical-source inventory, and unresolved blockers. It does not authorize a real run, publication analysis, or Phase 19.

## Explicit human authorization record

The current user explicitly authorized **Phase 18: Publication Experiment Freeze, Real-Run Authorization, and Computational Feasibility**.

Authorized scope:

- protocol and experiment-freeze decisions;
- preflight and computational-feasibility inventory;
- recording unresolved scientific decisions and stopping affected actions.

Not authorized:

- `real_execution_authorized=false` — do not train or evaluate on real ADNI/OASIS data;
- `publication_authorized=false` — do not produce publication analysis, metrics, tables, claims, or conclusions;
- Phase 19 — forbidden and not started;
- changes to `.git/gentle-ai` or the approved native receipt;
- Phase 18 runtime implementation, experiment outputs, or real-data artifacts.

The only Phase 18 owned artifacts created by this action are `AGENTS.md` and this decisions file. No implementation was added under `src/`, `configs/`, `scripts/`, `tests/`, or `docs/`.

## Phase 17 closure reference

Authoritative closure artifacts:

- `openspec/changes/phase-17-ablations/state.yaml`
  - `status: completed`;
  - `current_phase: phase17-closed`;
  - synthetic implementation and validation complete;
  - `real_execution_authorized: false`;
  - `publication_authorized: false`;
  - `phase_18_authorized: false` in the pre-authorization state.
- `specs/phase_17_ablations/final_audit.md`
  - final verdict: **PASS**;
  - fallback audit by `gentle-ai-verify` because requested `kimi` was unavailable;
  - explicitly does not authorize real execution, publication evaluation, or Phase 18.
- `docs/PHASE17_REPORT.md`
  - Phase 17 closure report and exact post-Phase 17 validation record;
  - explicitly states that no real-data result, publication output, or Phase 18 work was produced.
- `specs/phase_17_ablations/decisions.md`
  - canonical ablation boundary and unresolved coefficient record.

The approved native receipt evidence was inspected but not changed:

- `.git/gentle-ai/review-transactions/v2/review-1d63ad8511d6bbf5/review-receipt.json`
  - `terminal_state: approved`;
  - lineage: `review-1d63ad8511d6bbf5`.

No native review lifecycle command was run by this action. The receipt and all `.git/gentle-ai` content remain untouched.

## Recorded Phase 17 evidence (not rerun)

The following is confirmed from the closure artifacts above. It is historical recorded evidence, not a rerun in this action.

| Check | Recorded result | Evidence path |
|---|---|---|
| Full regression suite | `python -m pytest -q` — exit 0; **1178 passed, 7 warnings**; `1012.14s (0:16:52)` | `openspec/changes/phase-17-ablations/state.yaml`; `specs/phase_17_ablations/final_audit.md`; `docs/PHASE17_REPORT.md` |
| Editable install | `python -m pip install -e .` — passed, exit 0 | `openspec/changes/phase-17-ablations/state.yaml`; `specs/phase_17_ablations/final_audit.md` |
| Import/version | `python -c "import pada3dacb; print(pada3dacb.__version__)"` — passed; `0.1.0` | `openspec/changes/phase-17-ablations/state.yaml`; `specs/phase_17_ablations/final_audit.md` |
| Ruff | `python -m ruff check .` — exit 0; all checks passed | `openspec/changes/phase-17-ablations/state.yaml`; `specs/phase_17_ablations/final_audit.md` |
| Whitespace | `git diff --check` — exit 0 | `openspec/changes/phase-17-ablations/state.yaml`; `specs/phase_17_ablations/final_audit.md` |

The focused Phase 17 recheck was also recorded as `119 passed, 0 warnings`; it was not rerun here. No claim in this record treats the historical `1059 passed` result as the post-Phase 17 result; that number is preserved only as the pre-Phase 17 baseline.

## Pre-authorization runtime audit

Before this authorization, no Phase 18 runtime implementation was found under:

- `src/`;
- `configs/`;
- `scripts/`;
- `tests/`;
- `docs/`.

The audit found no Phase 18-named implementation files in those directories and no Phase 18 implementation markers in `src/`, `configs/`, `scripts/`, or `tests/`. Existing documentation mentions Phase 18 only to preserve a boundary or state that it had not started; those references are not implementation. The Phase 17 synthetic configuration remains explicitly `synthetic_only: true`, `real_data_authorized: false`, and `publication_metrics: false` in `configs/experiments/ablations.yaml`.

## Canonical inventory and unresolved scientific decisions

The inventory below records repository evidence without selecting values that are not resolved by authoritative sources.

| Decision area | Repository evidence | Phase 18 disposition |
|---|---|---|
| Primary method and architecture | `docs/PADA3DACB_MODEL.md`; `docs/PROPOSED_METHOD_EXPERIMENT.md`; `notebooks/archive/training_original.ipynb` | Preserve public method `PADA-3DACB` and the no-context architecture. Do not introduce Full/Lite switches, `ContextualROIEncoder`, `ctx_enc`, or identity patching. |
| Candidate set | `specs/phase_17_ablations/ablation_inventory.yaml`; `specs/phase_17_ablations/decisions.md` | The six exact Phase 17 synthetic candidates are evidence only: `no_proto`, `no_pl`, `no_cons`, `no_concept`, `no_anat`, `mean_pool`. A publication matrix still requires a separate Phase 18 decision. |
| `lambda_proto` | Primary path and current Phase 17 config use `lambda_proto=1.0`; later notebook helper/default uses `lambda_proto=0.2`. Evidence: `notebooks/archive/training_original.ipynb`, `specs/phase_17_ablations/ablation_inventory.yaml`, `docs/PROPOSED_METHOD_EXPERIMENT.md`. | **Unresolved blocking decision.** Do not choose `0.2` or `1.0` for a publication-facing matrix unless authoritative repository evidence or an explicit maintainer decision resolves the discrepancy. The matrix compiler and real-run gate MUST reject authorization while this field is unresolved; target outcomes MUST NOT resolve it. |
| Objective equations | `docs/LOSSES_AND_TRAINING.md`; `docs/PROPOSED_METHOD_EXPERIMENT.md`; Phase 17 decisions/spec | Preserve the recorded warm/full equations. Warm prototype and pseudo-label terms remain absent/logged zero; no alternate equation may be inferred. |
| Checkpoint criterion | `docs/LOSSES_AND_TRAINING.md`; Phase 17 specification | **Invariant:** fixed epoch counts; source-validation macro-F1 is the only best-checkpoint criterion; training continues after a best save; target monitoring cannot affect loss, gradients, optimizer, scheduler, checkpoint, hyperparameter, epoch, or resume decisions. |
| Cohort and transfer matrix | `AGENTS.md`; Phase 17 synthetic matrix; notebook primary call | Cohorts remain only `ADNI` and `OASIS`, with directions `ADNI -> OASIS` and `OASIS -> ADNI`. The complete real direction/fold/seed matrix, assignment identities, and any exclusions are not yet authorized or frozen. |
| Splits and subject assignments | `docs/PROPOSED_METHOD_EXPERIMENT.md`; Phase 17 output/identity contracts; notebook split helpers | Real split manifests, subject-level disjointness, target adaptation/evaluation assignments, and immutable assignment hashes remain unresolved inputs. Do not regenerate or infer them. |
| Immutable artifacts | `specs/phase_16_concept_validation/manuscript_extraction.md`; `docs/LOSSES_AND_TRAINING.md`; `AGENTS.md` | Atlas/ROI ordering, concept normalizer, concept targets, Jacobian artifacts, and hashes must be identified and verified before any real run. No regeneration or refitting is authorized here. |
| Preprocessing and provenance | `AGENTS.md`; `notebooks/archive/preprocess_original.ipynb`; Phase 16 extraction | Canonical preprocessing and artifact provenance must be mapped to the real environment. No new preprocessing, harmonization, external data search, or path invention is authorized. |
| Compute feasibility | `docs/PROPOSED_METHOD_EXPERIMENT.md` and Phase 17 closure | Required real hardware, wall-clock budget, storage, workers, memory, retry policy, and approved command are not recorded as a Phase 18 authorization. Computational feasibility remains unresolved. |
| Publication protocol | `specs/phase_16_concept_validation/manuscript_extraction.md`; `docs/PHASE17_REPORT.md` | No complete manuscript PDF is present. CFS, ACS, PCS, and QIS have no verified authoritative equations and remain blocked. Statistical comparisons, confidence intervals, reporting tables, and publication endpoints are not frozen. |
| Target-label isolation | `AGENTS.md`; `docs/PROPOSED_METHOD_EXPERIMENT.md`; Phase 17 specification | Preserve disjoint `target_adaptation`/`target_evaluation`; target diagnosis labels are monitoring-only and never training supervision or selection criteria. |

## Blocking items before scientific freeze

The following must be resolved by explicit authoritative evidence or a new human decision before Phase 18 can declare a publication experiment freeze or authorize any real execution:

1. Resolve the `lambda_proto=0.2` versus `lambda_proto=1.0` discrepancy; this is currently **`unresolved_blocking`**.
2. Approve the exact real candidate/method matrix and all inherited coefficients, epochs, seeds, directions, and fold policy without using the historical selective-fold shortcut.
3. Identify and hash the real split manifests, subject assignments, target adaptation/evaluation separation, atlas/ROI metadata, concept normalizer, concept targets, and Jacobian artifacts.
4. Record real-data provenance, access/privacy constraints, configured paths, and a fail-closed preflight command; no external data may be searched for or downloaded by this action.
5. Establish compute feasibility from actual available resources: device/runtime, memory, storage, expected duration, retry/resume policy, and approved resource budget.
6. Define the publication evaluation/statistical protocol from authoritative sources. CFS, ACS, PCS, and QIS remain blocked until their equations are verified; no manuscript score is invented from a name.
7. Define the exact output, provenance, failure, and publication boundary records required for any later authorized run.

## Current decision

Phase 18 protocol-freeze work is authorized, but the scientific freeze is **not approved**. Real execution and publication remain false, and Phase 19 remains forbidden. The next action is to resolve the blocking decisions above through explicit human/authoritative evidence; until then, stop the affected action and do not run ADNI/OASIS experiments.
