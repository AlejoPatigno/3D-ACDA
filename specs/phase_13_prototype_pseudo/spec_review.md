# Phase 13 Independent Specification Review

Verdict: APPROVED

Implementation may proceed for Phase 13 only, subject to the existing action dependencies and file ownership in `agent_plan.yaml`.

## Review scope

Authoritative source reviewed: `notebooks/archive/training_original.ipynb`.

Specification artifacts reviewed:

- `specs/phase_13_prototype_pseudo/notebook_extraction.md`
- `specs/phase_13_prototype_pseudo/requirements.md`
- `specs/phase_13_prototype_pseudo/design.md`
- `specs/phase_13_prototype_pseudo/tasks.md`
- `specs/phase_13_prototype_pseudo/acceptance.md`
- `specs/phase_13_prototype_pseudo/agent_plan.yaml`
- `specs/phase_13_prototype_pseudo/decisions.md`

## Findings

| Check | Result | Evidence |
|---|---:|---|
| Source traceability | PASS | `PrototypeLoss`, `PseudoLabelLoss`, `DomainAdaptiveTotalLoss`, `DomainAdaptiveTrainConfig`, `DomainAdaptiveMRITrainer`, primary `train_domain_adaptation_fold`, and executed `bidirectional_results = run_bidirectional_domain_adaptation(...)` were checked against the notebook. |
| Prototype equation | PASS | Notebook computes current-batch source and target prototypes from `z_src`/`z_tgt`, aligns only mutually valid classes with mean squared Euclidean distance, and adds source separation as `lambda_sep * mean(relu(margin - L2)^2)`. |
| Pseudo-label equation | PASS | Notebook computes `softmax(logits_c_tgt)`, uses argmax and `conf >= tau_p`, and applies `F.cross_entropy(logits_c_tgt[mask], pseudo[mask])`; empty mask returns zero loss and count zero. |
| Coefficients | PASS | Primary executed fold construction sets `lambda_z=1.0`, `lambda_c=1.0`, `lambda_cons=0.1`, `lambda_cbm=0.5`, `lambda_anat=0.2`, `lambda_proto=1.0`, `lambda_pl=0.1`, `tau_p=0.95`, `proto_margin=1.0`, `lambda_sep=0.1`, `label_smoothing=0.1`, warm multipliers `0.1/1.0/1.0/1.0/0.0`, and run values `n_epochs_warm=5`, `n_epochs_full=50`, `batch_size=16`, `num_workers=2`, `lr=1e-4`, `weight_decay=1e-4`, `random_state=42`. |
| No invented behavior | PASS | The specs explicitly reject placeholder values, cache/EMA/momentum, normalization, entropy/temperature/class-balancing schedules, and target concept/anatomy inputs for adaptation. |
| Active vs. obsolete definitions | PASS | The specs correctly treat later ablation redefinitions as namespace-later but not the primary executed proposed-method path. The ablation `lambda_proto=0.2` is not used as the Phase 13 canonical proposed-method coefficient. |
| Target-label isolation | PASS | Full adaptation training requires source keys `x`, `y`, `c_target`, `g_bar` and target key `x` only; target labels/concepts/anatomy are used only by labeled monitoring/evaluation loaders. |
| Phase boundaries | PASS | The reviewed specs do not include baseline implementation, evaluation publication statistics, Phase 14, real-cohort execution, concept intervention, or confusion-matrix scope. |
| File ownership | PASS | `agent_plan.yaml` has no duplicate owned-file collisions; `spec_review.md` is owned only by `independent-specification-review`. |

## Notes for implementation

- Keep the Phase 13 implementation stateless for prototype and pseudo-label adaptation.
- Do not use target diagnosis labels, target concept targets, or target anatomical tensors in adaptation losses.
- Do not implement the later ablation helper behavior as the primary proposed method.
- Keep implementation split by `agent_plan.yaml` action boundaries because the review workload forecast recommends chained PR slices.

## Validation performed

- Read and inspected required specification artifacts.
- Inspected relevant notebook sections around the active loss definitions, trainer behavior, primary executed run call, and later ablation redefinition.
- Ran a YAML ownership-collision check for `agent_plan.yaml`: no collisions found.

No production tests were run because this was a specification-only review and no production code was modified.

## Verdict

APPROVED — implementation may begin for the first Phase 13 implementation action only, within the declared ownership and dependency boundaries.
