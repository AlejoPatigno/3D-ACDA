# Phase 18 — Scientific Resolution Ledger

## Current resolution

The protocol is **not scientifically freeze-ready**. Repository evidence is recorded below; unresolved values remain blockers. No entry below authorizes a real run.

## Classification legend

`canonical_fixed` = protected/repeated repository value; `manually_selected_pre_run` = must be explicitly chosen before execution; `engineering_only` = operational or synthetic value; `unresolved_blocking` = conflicting, missing, or unauthorized.

## Fixed repository contracts

| Field | Value | Class | Evidence |
|---|---|---|---|
| Cohorts | `ADNI`, `OASIS` only | canonical_fixed | `AGENTS.md`; Phase 15–17 contracts |
| Directions | `ADNI -> OASIS`; `OASIS -> ADNI` | canonical_fixed | `AGENTS.md`; `configs/evaluation/predictive.yaml`; Phase 17 matrix |
| Class order | `CN=0`, `MCI=1`, `AD=2` | canonical_fixed | `AGENTS.md`; model/evaluation configs |
| Core methods | `source_only`, `coral`, `mmd`, `cdan`, `prototype_pseudo`, `aagn`, `faster_snn` | canonical_fixed | Phase 15 decisions/config; Phase 17 regression boundary |
| Proposed public model | `PADA-3DACB` | canonical_fixed | `docs/PADA3DACB_MODEL.md`; `configs/model/pada3dacb.yaml` |
| Contextual encoder | `false`; no contextual runtime switch | canonical_fixed | model config and architecture docs |
| Input channels/classes/ROIs | `1` / `3` / `102` | canonical_fixed | `configs/model/pada3dacb.yaml` |
| Primary warm/full epochs | `5` / `50` | canonical_fixed | primary notebook call; `prototype_pseudo.yaml`; Phase 17 contract |
| Primary LR / weight decay | `1e-4` / `1e-4` | canonical_fixed | primary notebook call and proposed-method config |
| Primary batch/workers | `16` / `2` | canonical_fixed | primary notebook call and proposed-method config |
| Early stopping | `false` | canonical_fixed | `AGENTS.md`; training configs |
| Best checkpoint | source-validation macro-F1 only | canonical_fixed | `AGENTS.md`; `docs/LOSSES_AND_TRAINING.md`; Phase 15 D-14-002 boundary |
| Training after best save | required through fixed epochs | canonical_fixed | `AGENTS.md`; training docs |
| Target monitoring label | `MONITORING ONLY — NOT A TRAINING LOSS` | canonical_fixed | training/evaluation configs |
| Seed policy evidence | `[42]` | canonical_fixed evidence; approval still required | experiment, baseline, evaluation, preprocessing, precompute configs |
| Primary evaluation policy | `best_source_f1` | canonical_fixed | `configs/evaluation/predictive.yaml`; Phase 15 protocol |
| Sensitivity policy | `last`, separate and never pooled | canonical_fixed | Phase 15 decisions/config |
| Bootstrap replicates | `10000` when/if the approved evaluation protocol is authorized | canonical_fixed | Phase 15 statistical protocol/config |

## Primary loss coefficients

The following values are inherited from the primary path and are not to be tuned in a run:

| Value | Class | Provenance |
|---|---|---|
| `lambda_z=1.0`, `lambda_c=1.0` | canonical_fixed | `training_original.ipynb` primary coefficients; Phase 17 inventory |
| `lambda_cons=0.1`, `lambda_cbm=0.5`, `lambda_anat=0.2` | canonical_fixed | same sources; `configs/experiments/ablations.yaml` |
| `lambda_pl=0.1` | canonical_fixed | same sources; proposed-method config |
| `tau_p=0.95`, `proto_margin=1.0`, `lambda_sep=0.1` | canonical_fixed | proposed-method config and Phase 17 inventory |
| `label_smoothing=0.1` | canonical_fixed | primary loss config |
| `warm_lambda_z=0.1`, `warm_lambda_c=1.0`, `warm_lambda_cbm=1.0`, `warm_lambda_anat=1.0`, `warm_lambda_cons=0.0` | canonical_fixed | active warm equation and Phase 17 inventory |

## Blocking coefficient decision

| Candidate value | Evidence | Disposition |
|---|---|---|
| `lambda_proto=1.0` | Primary non-commented path, cell 14 lines 504–524; `prototype_pseudo.yaml`; Phase 17 inventory | canonical primary evidence, but not publication-resolved |
| `lambda_proto=0.2` | Later ablation helper/class default, cell 18 lines 55–86 and cell 8 default; D-14-001 | historical helper/manuscript evidence, not equivalent |
| Publication-facing choice | No authoritative maintainer resolution | **unresolved_blocking** |

The resolver MUST reject publication-facing execution while this conflict is unresolved. Target metrics, target labels, folds, seeds, or manuscript performance MUST NOT choose the value. The matrix compiler and real-run gate MUST reject authorization until an authoritative decision record binds exactly one value and its hash.

## Checked-in adaptation parameter ledger

The seven-method inventory is not runnable merely because method IDs exist. Every method-specific parameter required by its checked-in loader/configuration MUST be present, typed, and hash-bound before authorization. The following parameters are currently absent, null, or rejected by the available validators and therefore remain `unresolved_blocking`:

| Method | Required parameter set that must be checked in and validated | Current disposition |
|---|---|---|
| `coral` | CORAL adaptation weight | `unresolved_blocking` |
| `mmd` | MMD adaptation weight; kernel type; every kernel bandwidth/scale used by the implementation | `unresolved_blocking` |
| `cdan` | CDAN adaptation weight; GRL strength/schedule; discriminator architecture, hidden size, input contract, optimizer, and discriminator learning-rate settings | `unresolved_blocking` |

A future resolved method configuration MUST enumerate these fields explicitly and include them in `resolved_config_hash`. The loader MUST reject a missing, null, malformed, or out-of-schema field. It MUST NOT invent defaults, inherit an unrelated method's value, or silently substitute a generic configuration. Until authoritative checked-in values and loader-validation evidence exist, the affected method rows and the real-run gate remain blocked.

## Method and ablation disposition

The seven core methods are the only matrix rows. Phase 17's exact candidates (`no_proto`, `no_pl`, `no_cons`, `no_concept`, `no_anat`, `mean_pool`) are `canonical_defined_not_executed` evidence for synthetic work, not automatically publication methods. Their publication inclusion is `unresolved_blocking` pending explicit human selection. Forbidden historical/contextual names and unproven source-only aliases are excluded from the runnable inventory and cannot be reintroduced by name.

## Real-data values still requiring selection or evidence

| Field | Class | Required evidence |
|---|---|---|
| Split manifests and subject assignments | unresolved_blocking | exact immutable manifests and hashes for every direction/fold/seed |
| Target adaptation/evaluation partition | unresolved_blocking | hash-verified manifest contents, disjoint subject lists, role manifests, and hashes |
| CORAL/MMD/CDAN checked-in parameters | unresolved_blocking | authoritative method configs plus loader validation; no invented defaults |
| Atlas/ROI metadata and order | unresolved_blocking until identified | Phase 5 artifact identity, atlas/mask/order hashes |
| Concept normalizer/targets/Jacobians | unresolved_blocking until identified | immutable artifact index and source hashes; no refit/regeneration |
| Data paths/privacy authorization | unresolved_blocking | configured roots, access/privacy decision, no external discovery |
| Hardware/device and budget | unresolved_blocking | observed feasibility record and approved conservative/nominal budget |
| Publication ablation subset | unresolved_blocking | explicit maintainer selection before matrix identity is frozen |
| Manuscript equations/endpoints | unresolved_blocking | authoritative source for any publication score or statistical endpoint |

## Outcome

Until the blockers above are resolved, the only valid Phase 18 state is planning/blocked. No performance, feasibility, publication, or scientific conclusion is inferred. A gate manifest with an unresolved lambda, missing method parameter, non-canonical direction identifier, failed content-level assignment intersection, or unavailable canonical-JSON conformance evidence MUST be rejected before authorization.
