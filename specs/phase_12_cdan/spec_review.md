# Phase 12 Independent Spec Review — PADA-3DACB + CDAN

## Verdict

APPROVED for implementation/reconciliation.

This review covers only the Phase 12 SDD specification artifacts. It does not verify implementation correctness or runtime behavior.

## Inputs Reviewed

- `specs/phase_12_cdan/decisions.md`
- `specs/phase_12_cdan/requirements.md`
- `specs/phase_12_cdan/design.md`
- `specs/phase_12_cdan/tasks.md`
- `specs/phase_12_cdan/acceptance.md`
- `specs/phase_12_cdan/agent_plan.yaml`

## Scope and Scientific Contract Evidence

The specification is complete enough to proceed because it explicitly covers:

- Approved cohorts and directions only: ADNI/OASIS and `ADNI -> OASIS` / `OASIS -> ADNI`.
- Public identity: method `cdan`, display name `PADA-3DACB + CDAN`, public model PADA-3DACB, with Full/contextual encoder and identity patch behavior excluded.
- Immutable scientific invariants: CN=0, MCI=1, AD=2; immutable source folds and target partitions; target adaptation/evaluation disjointness; no target diagnosis labels in adaptation; source-validation macro-F1 as the sole checkpoint selector; fixed epochs; no preprocessing/artifact/split/normalizer refitting.
- Exact CDAN variant: outer-product conditioning `H_i = z_i p_i^T`, deterministic flattening to `(B, d * 3)`, no detaching of `z` or probabilities, and discriminator dimension validation.
- GRL: explicit finite non-negative constant coefficient, forward identity, backward `-coefficient` scaling, and rejection of invalid/scheduled coefficients.
- Discriminator: binary MLP consuming flattened conditional features and returning one raw logit per sample with no sigmoid.
- Domain loss: internal source=0 and target=1 labels, concatenated logits/labels, `BCEWithLogitsLoss(reduction="mean")`, and weighted contribution `cdan_weight * domain_bce`.
- Training objective: source-only warm-up with no target/CDAN/discriminator side effects; full stage with one shared model, one discriminator, one AdamW optimizer with explicit parameter groups, one backward pass, and one optimizer step per paired batch.
- Data and monitoring: target monitoring remains read-only; exports are source-validation and target-monitoring only; no target-adaptation predictions or domain labels are exported.
- Configuration/hash/provenance: real-run CDAN weight, GRL coefficient, discriminator architecture/dropout, discriminator optimizer settings, and seed/fold matrix remain unresolved blockers rather than invented defaults.
- Required tests/final commands: focused CDAN tensor/GRL/discriminator/loss/trainer/config/CLI/export tests plus Source-Only, CORAL, and MMD regression commands are listed.
- Phase 13 and later-phase exclusions: entropy conditioning, randomized multilinear projection, pseudo-labels, prototype alignment, baseline methods, contextual/full model files, identity patch behavior, preprocessing, artifact precomputation, split regeneration, and per-fold normalizer refit are forbidden.

## Testability Assessment

APPROVED. Requirements are written as testable MUST/SHOULD contracts with scenarios. The acceptance and task files name focused tests for tensor shape/order, gradient reachability, GRL validation, discriminator logits, domain loss, warm-up side effects, full-stage optimizer behavior, config validation/hash identity, prediction export policy, target-label rejection, prior-method regressions, and forbidden-scope auditing.

## Agent Plan Review

APPROVED.

Validation performed by inspection and a local YAML parse:

- `agent_plan.yaml` contains 13 actions.
- Every action has exactly one `responsible_agent`.
- All responsible agents are from the allowed set: `claude-code`, `codex`, `gemini-cli`, `opencode`, `kimi`.
- All dependencies reference known earlier actions; no unknown or forward dependency was found.
- Every action declares exclusive file ownership.
- The concurrently-ready implementation group after `independent-spec-review` has no shared exclusive paths/globs:
  - `implement-gradient-reversal`
  - `implement-conditional-cdan`
  - `implement-domain-discriminator`
- No unsupported agent names were found.
- No concurrent exclusive file ownership collision was found in the declared ready group.

## Non-blocking Limitations

- This is a specification audit only. It does not prove that the existing Phase 12 worktree files satisfy the specification.
- Final runtime verification remains dependent on the local Python dependency environment. The spec correctly requires exact dependency limitation evidence if normal dependency resolution is unavailable.
- The approved single-PR size exception is recorded, but implementation should still keep work units reviewable and avoid scope creep.

## Blockers

None.
