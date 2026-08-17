# Phase 18 Scientific Resolution Ledger

## Final decision

**Scientific protocol status: `PHASE18_SCIENTIFIC_FREEZE_COMPLETE_BUT_EXTERNAL_PROVENANCE_BLOCKED`.** Selected scientific fields are frozen for pre-run planning. No target outcome, real cohort, or publication result was inspected.

## Classification contract

- `RESOLVED_CANONICAL`: protected by the active repository contract and selected implementation path.
- `RESOLVED_PRE_RUN_HUMAN`: explicitly selected by the maintainer before execution.
- `ENGINEERING_ONLY`: synthetic or operational evidence that is not a publication claim.
- `BLOCKED_EXTERNAL_PROVENANCE`: required real path, hash, identity, review, resource, or authorization evidence is absent.

Selected scientific fields are **not** generic unresolved values:

- PADA coefficients, optimizer values, epochs, checkpoint policy, and seed policy are `RESOLVED_CANONICAL` or `RESOLVED_PRE_RUN_HUMAN`.
- The seven-method parameter ledger is structured and content-hash bound.
- Missing real evidence is classified `BLOCKED_EXTERNAL_PROVENANCE`.

## Selected PADA-3DACB values

| Field | Selected value | Class | Evidence |
|---|---:|---|---|
| `lambda_proto` | `1.0` | `RESOLVED_PRE_RUN_HUMAN` | Primary non-commented path/configuration; maintainer pre-run decision. |
| Historical `lambda_proto` | `0.2` | `RESOLVED_PRE_RUN_HUMAN` (excluded discrepancy) | Historical helper/manuscript discrepancy; non-production and never target-selected. |
| `lambda_z`, `lambda_c` | `1.0`, `1.0` | `RESOLVED_CANONICAL` | Primary objective path. |
| `lambda_cons`, `lambda_cbm`, `lambda_anat`, `lambda_pl` | `0.1`, `0.5`, `0.2`, `0.1` | `RESOLVED_CANONICAL` | Primary objective/configuration path. |
| `tau_p`, `proto_margin`, `lambda_sep` | `0.95`, `1.0`, `0.1` | `RESOLVED_CANONICAL` | Prototype configuration. |
| Warm coefficients | `0.1`, `1.0`, `1.0`, `1.0`, `0.0` | `RESOLVED_CANONICAL` | Primary warm-stage equation. |
| Epochs | warm `5`, full `50` | `RESOLVED_PRE_RUN_HUMAN` | Fixed pre-run decision; early stopping is forbidden. |
| Optimizer | learning rate `1e-4`, weight decay `1e-4`, batch size `16` | `RESOLVED_PRE_RUN_HUMAN` | Maintainer pre-run decision. |

Target labels cannot enter adaptation loss, gradients, checkpoint selection, or hyperparameter selection. The no-context PADA-3DACB backbone and approved equations remain unchanged.

## Method parameter ledger

The exact structured ledger in both publication configurations contains these seven methods. Every entry has a `parameters` mapping, a resolved `value_class`, and mapping-valued `evidence`: `source_only`, `coral`, `mmd`, `cdan`, `prototype_pseudo`, `aagn`, and `faster_snn`. Its content hash is recorded in the authorization configuration.

| Method | Selected parameter identity | Class |
|---|---|---|
| Source-Only | canonical source-only contract | `RESOLVED_CANONICAL` |
| CORAL | `weight=1.0`, `representation=z` | `RESOLVED_PRE_RUN_HUMAN` |
| MMD | biased Gaussian RBF mixture; bandwidths `[8,16,32]`; `z` | `RESOLVED_PRE_RUN_HUMAN` |
| CDAN | constant GRL `1.0`; hidden dims `[1024,1024]`; dropout `.5`; LR/WD `1e-4` | `RESOLVED_PRE_RUN_HUMAN` |
| Prototype pseudo-label | `lambda_proto=1.0` | `RESOLVED_PRE_RUN_HUMAN` |
| AAGN | canonical AAGN contract | `RESOLVED_CANONICAL` |
| Faster SNN | canonical Faster SNN contract | `RESOLVED_CANONICAL` |

## Seeds, checkpoint, and ablations

- Seeds are `[42, 43, 44]`, with source split random state `42`, target partition seed `42`, predeclared selection, and posthoc selection forbidden.
- Primary checkpoint is `best_source_f1` using source-validation macro-F1 only; `last` is a non-training sensitivity projection; macro-AUC is evaluation-only.
- Primary ablations are `no_proto`, `no_pl`, `no_concept`, and `no_anat`; supplementary ablations are `no_cons` and `mean_pool`; excluded historical cells are `no_domain_adaptation`, `no_ctx_encoder`, `full`, and `identity_ctx`. These are planning classifications, not executed rows or blockers.

## Matrix identity

The generated matrix is the complete Cartesian product of seven methods, two canonical directions, five folds, and three seeds: **210 training rows plus 210 linked checkpoint projections, 420 rows total**. Every checkpoint projection has `training_invocation=false` and schedules no training.

## External blockers

The freeze remains closed because the following evidence is absent and is classified `BLOCKED_EXTERNAL_PROVENANCE` or an equivalent external gate class:

- ADNI/OASIS split manifests, source assignments, target-adaptation assignments, target-evaluation assignments, and target subject intersection verification.
- Atlas, ROI order/masks, concept normalizer/targets, Jacobian artifacts, code/environment/command identity, and canonicalization/native conformance identity.
- Approved hardware/resource observations, real feasibility, independent review, privacy/data-access evidence, native lifecycle receipt, and human real-run authorization.
- A complete authoritative manuscript source for later alignment; its absence does not unsettle selected pre-run values.

No performance, publication metric, cohort runtime, or real provenance conclusion is inferred.
