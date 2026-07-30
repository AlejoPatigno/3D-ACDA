# Phase 12 Acceptance — PADA-3DACB + CDAN

## SDD Artifact Acceptance

1. The repository contains the Phase 12 SDD files required for this planning action:
   - `specs/phase_12_cdan/requirements.md`
   - `specs/phase_12_cdan/design.md`
   - `specs/phase_12_cdan/tasks.md`
   - `specs/phase_12_cdan/acceptance.md`
   - `specs/phase_12_cdan/agent_plan.yaml`
2. The requirements define only Phase 12 `PADA-3DACB + CDAN` behavior and explicitly preserve Source-Only, CORAL, and MMD.
3. The spec covers functional/scientific requirements, tensor contracts, GRL contract, discriminator contract, domain loss, training objective, data/monitoring, config validation/hash rules, production-file scope, tests, final commands, and forbidden later-phase behavior.
4. Unresolved real-run scientific values are blockers and no real-run hyperparameters are invented.
5. `agent_plan.yaml` uses only these execution agent names: `claude-code`, `codex`, `gemini-cli`, `opencode`, `kimi`.
6. `agent_plan.yaml` includes `repository-and-memory-audit` as the first completed action owned by `opencode`, with exclusive ownership of `specs/phase_12_cdan/decisions.md` and an Engram baseline deliverable.
7. `agent_plan.yaml` includes `independent-spec-review` owned by `kimi`, outputting and exclusively owning `specs/phase_12_cdan/spec_review.md` exactly.
8. `agent_plan.yaml` includes the required Phase 12 action graph: `implement-gradient-reversal`, `implement-conditional-cdan`, `implement-domain-discriminator`, `independent-mathematical-verification`, `trainer-integration`, `experiment-and-cli-integration`, `orchestration-and-regression-tests`, `documentation`, `final-scope-and-regression-audit`, and `final-validation`.
9. Every action has exactly one responsible agent, dependencies, and exclusive file ownership.
10. No two concurrently-ready actions own the same exclusive file path or glob.
11. No production file is modified by this specification correction action.
12. A compact corrective Engram record is saved with topic key `sdd/phase-12-cdan/action/write-sdd-specification` or a revision thereof.

## Behavioral Acceptance for Phase 12 Implementation

### Scientific and Functional

- CDAN supports only ADNI/OASIS and the two approved directions.
- Public display identity is `PADA-3DACB + CDAN`.
- PADA-3DACB remains the former Lite/no-contextual-encoder architecture.
- Class order remains CN=0, MCI=1, AD=2.
- Source folds and target partitions remain immutable.
- Target adaptation and target evaluation remain disjoint.
- Target diagnosis labels do not enter adaptation training.
- Source-validation macro-F1 remains the sole best-checkpoint criterion.
- Fixed epochs are used; early stopping is forbidden.
- Experiment phases do not rerun preprocessing, artifact precomputation, split generation, or concept normalizer fitting.

### Tensor, GRL, Discriminator, and Loss

- Conditional features are exact outer products of `z` and current latent probabilities.
- Conditional shape is `(B, d * 3)` and `d=128` implies 384 by validation, not hardcoded assumption.
- Neither `z` nor probabilities are detached.
- GRL coefficient is explicit, finite, non-negative, and constant.
- Discriminator consumes flattened conditionals and returns one raw logit per sample with no final sigmoid.
- Domain labels are internal: source=0, target=1.
- CDAN loss is concatenated mean `BCEWithLogitsLoss` over source and target logits/labels.
- Full-stage objective uses weighted domain BCE plus the approved source objective.

### Training, Data, Monitoring, and Provenance

- Warm-up is source-only and has no CDAN/discriminator side effects.
- Full stage uses one shared model, one shared discriminator, one AdamW optimizer with explicit parameter groups, one backward pass, and one optimizer step per paired batch.
- Prediction export includes source-validation and target-monitoring records only, with `method=cdan` and `model=PADA-3DACB + CDAN`.
- Target-adaptation predictions and domain labels are not exported.
- CDAN configuration and checkpoint identities include method, conditional variant, GRL, discriminator, optimizer group, and loader provenance.

## Forbidden Later-Phase Behavior

The final scope and regression audit MUST fail if Phase 12 introduces any of the following:

- entropy conditioning;
- randomized multilinear projection;
- pseudo-labels;
- prototype alignment;
- baseline methods;
- Phase 13 production files;
- `ContextualROIEncoder` or `ctx_enc`;
- identity patch behavior;
- target-guided checkpoint selection;
- target diagnosis supervision in adaptation;
- preprocessing, split generation, artifact precomputation, or per-fold normalizer refitting.

## Required Verification Commands

The verifier SHOULD run focused tests first:

```powershell
python -m pytest tests/test_cdan_conditional_map.py tests/test_gradient_reversal.py tests/test_cdan_domain_discriminator.py tests/test_cdan_domain_loss.py tests/test_cdan_gradients.py
python -m pytest tests/test_cdan_warmup.py tests/test_cdan_trainer.py tests/test_cdan_config.py tests/test_cdan_checkpoint_policy.py tests/test_cdan_cli.py tests/test_cdan_no_target_labels.py tests/test_cdan_predictions.py tests/test_cdan_fold_orchestration.py tests/test_cdan_loader_cycling.py tests/test_cdan_resume.py
python -m pytest tests/test_source_only_coral_regression.py tests/test_mmd_cli.py tests/test_mmd_gradients.py
```

If a normal dependency-resolved environment is unavailable, the verifier MUST record the exact limitation and treat verification as blocked or partial rather than silently weakening acceptance.

## Local Acceptance Checks Performed by This Spec Correction

This correction checks only SDD artifact health, not implementation correctness:

- file existence and readability for updated `agent_plan.yaml`, `tasks.md`, and `acceptance.md`;
- allowed-agent-name validation by inspection;
- simple ownership-collision validation by graph design: the only concurrently-ready implementation actions after `independent-spec-review` own disjoint files;
- Engram save attempt for corrective completion record.
