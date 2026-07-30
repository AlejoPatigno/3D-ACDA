# Phase 12 Tasks — PADA-3DACB + CDAN

All actions MUST use exactly one responsible agent from the allowed execution agents: `claude-code`, `codex`, `gemini-cli`, `opencode`, `kimi`. No action may commit or push. Production work is limited to Phase 12 CDAN only.

## Action 1: repository-and-memory-audit

Responsible agent: `opencode`

- [x] Audit repository and Engram baseline for Phase 12.
- [x] Record decisions in `specs/phase_12_cdan/decisions.md`.
- [x] Preserve evidence that Source-Only, CORAL, and MMD are protected prior methods.
- [x] Record hybrid artifact-store and no-commit/no-push constraints.

## Action 2: write-sdd-specification

Responsible agent: `claude-code`

- [x] Read `specs/phase_12_cdan/decisions.md` first.
- [x] Create/overwrite `requirements.md`, `design.md`, `tasks.md`, `acceptance.md`, and `agent_plan.yaml` under `specs/phase_12_cdan/`.
- [x] Capture Phase 12 CDAN-only scope, tensor contracts, GRL, discriminator, domain loss, objective, data/monitoring, config/hash rules, tests, commands, and exclusions.
- [x] Include independent spec review and final audit/validation actions.
- [x] Save compact completion/correction record in Engram.

## Action 3: independent-spec-review

Responsible agent: `kimi`

- [x] Read all Phase 12 SDD files.
- [x] Verify requirements are testable and limited to PADA-3DACB + CDAN.
- [x] Verify unresolved scientific values are recorded as blockers instead of invented defaults.
- [x] Verify `agent_plan.yaml` has exactly one responsible agent per action from the allowed agent set.
- [x] Verify no exclusive ownership collisions exist among concurrently-ready actions.
- [x] Output `specs/phase_12_cdan/spec_review.md` exactly.

## Action 4: implement-gradient-reversal

Responsible agent: `codex`

- [x] Reconcile or implement constant gradient reversal in `src/pada3dacb/adaptation/gradient_reversal.py` only.
- [x] Validate finite non-negative constant coefficient; reject missing, negative, NaN, infinite, or scheduled coefficients.
- [x] Add or reconcile `tests/test_gradient_reversal.py` for forward identity and `-coefficient` backward scaling.

## Action 5: implement-conditional-cdan

Responsible agent: `claude-code`

- [x] Reconcile or implement exact outer-product conditioning in `src/pada3dacb/adaptation/cdan.py`.
- [x] Ensure `z` and latent probabilities are not detached and output shape is `(B, d * 3)`.
- [x] Reconcile concatenated mean `BCEWithLogitsLoss` with internal source=0 and target=1 labels.
- [x] Add or reconcile conditional map, domain loss, and gradient tests.

## Action 6: implement-domain-discriminator

Responsible agent: `gemini-cli`

- [x] Reconcile or implement `src/pada3dacb/adaptation/domain_discriminator.py`.
- [x] Ensure it consumes flattened CDAN conditionals and returns one raw logit per sample with no sigmoid.
- [x] Validate positive input dimension, explicit hidden dimensions, valid activation, dropout in `[0, 1)`, and output dimension 1.
- [x] Add or reconcile discriminator and provenance/resume tests.

## Action 7: independent-mathematical-verification

Responsible agent: `kimi`

- [x] Independently verify the CDAN math: outer product, flattening contract, GRL gradient sign/scale, discriminator logits, and BCE domain objective.
- [x] Verify unresolved real-run hyperparameters remain blockers.
- [x] Output `specs/phase_12_cdan/mathematical_verification.md`.

## Action 8: trainer-integration

Responsible agent: `opencode`

- [x] Reconcile or implement CDAN support in `src/pada3dacb/training/uda_trainer.py` and adaptation exports only.
- [x] Preserve source-only warm-up: no target batch consumption, no conditional construction, no discriminator call/update, and zero/no CDAN diagnostics.
- [x] Full stage must use one shared model, one shared discriminator, one AdamW optimizer with explicit parameter groups, one backward pass, and one optimizer step per paired batch.
- [x] Add or reconcile warm-up, trainer, loader cycling, and target-label rejection tests.

## Action 9: experiment-and-cli-integration

Responsible agent: `codex`

- [x] Reconcile or implement CDAN experiment/config/CLI integration.
- [x] Require explicit real-run CDAN weight, GRL coefficient, discriminator architecture/dropout, and discriminator optimizer settings.
- [x] Ensure configuration/hash/checkpoint identity includes method, conditional variant, GRL, discriminator, optimizer group, and loader provenance.
- [x] Add or reconcile config, checkpoint policy, CLI, helper, and fold orchestration tests.

## Action 10: orchestration-and-regression-tests

Responsible agent: `gemini-cli`

- [x] Reconcile prediction-schema tests for `method=cdan` and `model=PADA-3DACB + CDAN`.
- [x] Run or reconcile Source-Only, CORAL, and MMD regression tests.
- [x] Report pre-existing prior-method defects separately unless Phase 12 worsens or activates them.

## Action 11: documentation

Responsible agent: `claude-code`

- [x] Update only Phase 12 CDAN documentation/report files.
- [x] Document exact CDAN variant, exclusions, explicit real-run blockers, and monitoring/checkpoint policy.
- [x] Do not claim real scientific results from validate-only or smoke tests.

## Action 12: final-scope-and-regression-audit

Responsible agent: `kimi`

- [x] Audit final diff against `requirements.md`, `design.md`, `tasks.md`, `acceptance.md`, and `agent_plan.yaml`.
- [x] Confirm no Phase 13, full/contextual encoder, identity patch, preprocessing, artifact precompute, split regeneration, pseudo-label, prototype, entropy conditioning, randomized projection, or baseline behavior was introduced.
- [x] Confirm Source-Only, CORAL, and MMD remain behaviorally protected.
- [x] Confirm unresolved real-run scientific values remain blockers.
- [x] Output `specs/phase_12_cdan/final_scope_and_regression_audit.md`.

## Action 13: final-validation

Responsible agent: `opencode`

- [x] Run focused Phase 12 tests and prior-method regression tests.
- [x] Run available static/readability checks in the local environment.
- [x] Record exact commands, exit codes, and dependency limitations.
- [x] Confirm no commits or pushes were performed.
- [x] Output `specs/phase_12_cdan/final_validation.md`.

## Review Workload Forecast

- Chained PRs recommended: Yes, based on expected Phase 12 implementation/test surface above 400 changed lines.
- 400-line budget risk: High.
- Decision needed before apply: No, because the user has explicitly approved a single-PR exception for this Phase 12 execution.
- Delivery strategy: `single-pr` with approved size exception.

## Final Commands

Local verification should use the available project test runner. Focused commands SHOULD include:

```powershell
python -m pytest tests/test_cdan_conditional_map.py tests/test_gradient_reversal.py tests/test_cdan_domain_discriminator.py tests/test_cdan_domain_loss.py tests/test_cdan_gradients.py
python -m pytest tests/test_cdan_warmup.py tests/test_cdan_trainer.py tests/test_cdan_config.py tests/test_cdan_checkpoint_policy.py tests/test_cdan_cli.py tests/test_cdan_no_target_labels.py tests/test_cdan_predictions.py tests/test_cdan_fold_orchestration.py tests/test_cdan_loader_cycling.py tests/test_cdan_resume.py
python -m pytest tests/test_source_only_coral_regression.py tests/test_mmd_cli.py tests/test_mmd_gradients.py
```

If dependencies are unavailable, the verifier MUST record exact missing dependency evidence and MUST NOT treat `--no-deps` installation as equivalent to a clean environment.
