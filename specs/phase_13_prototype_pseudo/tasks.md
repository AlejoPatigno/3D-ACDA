# Phase 13 Tasks

Status: READY FOR INDEPENDENT SPECIFICATION REVIEW.

## Dependencies

- [x] `phase12-closure-and-repository-audit` completed.
- [x] `canonical-notebook-extraction` artifacts created.
- [x] `independent-specification-review` must approve before implementation.

## Action plan

### canonical-notebook-extraction — claude-code

Owned files:

- `specs/phase_13_prototype_pseudo/notebook_extraction.md`
- `specs/phase_13_prototype_pseudo/requirements.md`
- `specs/phase_13_prototype_pseudo/design.md`
- `specs/phase_13_prototype_pseudo/tasks.md`
- `specs/phase_13_prototype_pseudo/acceptance.md`

Tasks:

- [x] Read `AGENTS.md`, `agent_plan.yaml`, and `decisions.md`.
- [x] Inspect active `PrototypeLoss`, `PseudoLabelLoss`, `DomainAdaptiveTotalLoss`, `DomainAdaptiveTrainConfig`, and `DomainAdaptiveMRITrainer` definitions in `training_original.ipynb`.
- [x] Identify later duplicated or superseded definitions and separate primary executed behavior from ablation-only behavior.
- [x] Inspect `precompute_original.ipynb` and `baselines_original.ipynb` only for parity references where symbols were copied.
- [x] Document prototype behavior, pseudo-label behavior, combined objective, tensor contracts, target-label firewall, checkpoint/resume implications, and discrepancies.
- [x] Write compact Engram completion record.

### independent-specification-review — kimi

Completed with APPROVED verdict in `spec_review.md`.

Owned file:

- `specs/phase_13_prototype_pseudo/spec_review.md`

Tasks:

- [x] Verify every scientific coefficient and equation against `notebooks/archive/training_original.ipynb`.
- [x] Confirm no behavior was invented from placeholder config fields.
- [x] Confirm the later ablation `train_domain_adaptation_fold` redefinition is not treated as the primary executed proposed-method run.
- [x] Confirm target diagnosis labels and target concept/anatomy artifacts are excluded from adaptation loss.
- [x] Approve or block implementation.

### implement-prototype-adaptation — codex

Completed after `spec_review.md` approval.

Owned files:

- `src/pada3dacb/adaptation/prototype.py`
- `tests/test_prototype_loss.py`
- `tests/test_prototype_construction.py`
- `tests/test_prototype_gradients.py`

Tasks:

- [x] Add failing tests for per-class current-batch prototypes, absent classes, alignment reduction, source separation, no normalization, no cache/EMA/momentum, and gradient flow.
- [x] Implement stateless prototype construction and loss.
- [x] Verify empty target acceptance and fewer-than-two-source-class behavior.

### implement-pseudo-label-adaptation — codex

Completed after `spec_review.md` approval.

Owned files:

- `src/pada3dacb/adaptation/pseudo_label.py`
- `tests/test_pseudo_label_selection.py`
- `tests/test_pseudo_label_loss.py`
- `tests/test_pseudo_label_gradients.py`

Tasks:

- [x] Add failing tests for softmax argmax confidence, `>= tau_p`, no temperature, no schedule, no balancing, empty selection, and concept-head logits.
- [x] Implement pseudo-label selection and CE loss.
- [x] Prove stored target labels are not consumed.

### implement-combined-method — codex

Completed after prototype and pseudo-label modules passed focused validation.

Owned files:

- `src/pada3dacb/adaptation/prototype_pseudo.py`
- `tests/test_prototype_pseudo_total.py`

Tasks:

- [x] Add failing reference tests for warm and full objectives.
- [x] Compose source core losses, `L_proto`, and `L_pl` without hidden weighting.
- [x] Return typed loss components and diagnostics matching notebook names where practical.

### independent-mathematical-verification — gemini-cli

Completed after combined method passed focused validation.

Owned files:

- `tests/test_proposed_method_reference.py`
- `tests/test_proposed_method_edge_cases.py`

Tasks:

- [x] Independently verify equations and reductions.
- [x] Verify absent-class, confidence-boundary, and gradient-flow edge cases.
- [x] Verify no target diagnosis supervision.

### trainer-and-checkpoint-integration — opencode

Completed after mathematical verification passed.

Owned files:

- `src/pada3dacb/training/uda_trainer.py`
- `src/pada3dacb/training/checkpointing.py`
- `src/pada3dacb/training/history.py`
- `tests/test_proposed_method_trainer.py`
- `tests/test_proposed_method_warmup.py`
- `tests/test_proposed_method_loader_cycling.py`
- `tests/test_proposed_method_checkpoint_policy.py`
- `tests/test_proposed_method_resume.py`

Tasks:

- [x] Add focused failing trainer/checkpoint/resume tests for the proposed method.
- [x] Integrate warm/full stage behavior.
- [x] Cycle target adaptation loader during full stage.
- [x] Preserve source-validation checkpoint selection and previous method behavior.
- [x] Confirm no adaptation-specific state is required for resume.

### experiment-cli-and-config-integration — opencode

Completed after trainer integration passed.

Owned files:

- `src/pada3dacb/experiments/prototype_pseudo.py`
- `src/pada3dacb/experiments/runner.py`
- `src/pada3dacb/experiments/run_manifest.py`
- `src/pada3dacb/experiments/fold_summary.py`
- `scripts/train.py`
- `configs/experiments/prototype_pseudo.yaml`
- `tests/test_proposed_method_config.py`
- `tests/test_proposed_method_cli.py`
- `tests/test_proposed_method_fold_orchestration.py`

Tasks:

- [x] Add focused failing config/CLI/fold orchestration tests.
- [x] Add explicit canonical configuration for all Phase 13 coefficients.
- [x] Fail real runs on unresolved placeholders.
- [x] Preserve configuration hashing and dry-run/validate-only behavior.

### complete-integration-and-regression-tests — codex

Completed after CLI/config integration passed.

Owned files: as listed in `agent_plan.yaml`.

Tasks:

- [x] Test both transfer directions and all folds with synthetic fixtures.
- [x] Protect Source-Only, CORAL, MMD, and CDAN regressions.
- [x] Verify target-label firewall, warm-up behavior, loader cycling, checkpoint policy, resume, predictions, fold orchestration, and CLI.

### documentation, final-audit, final-validation

Documentation, final audit, and final validation completed after implementation and regression tests passed.

- [x] Document equations and behavior without unverified performance claims.
- [x] Audit traceability and Phase 13 boundaries.
- [x] Run required validation commands.

## Review Workload Forecast

- Estimated implementation footprint: high; expected to exceed 400 changed lines across adaptation, trainer, config, CLI, and tests.
- 400-line budget risk: High.
- Chained PRs recommended: Yes.
- Decision needed before apply: Yes — split implementation by `agent_plan.yaml` action boundaries after spec review.
