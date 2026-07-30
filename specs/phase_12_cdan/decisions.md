# Phase 12 Decisions — PADA-3DACB + CDAN

## Repository and memory audit

- Last approved phase: Phase 11 — PADA-3DACB + MMD.
- Current authorized phase: Phase 12 — PADA-3DACB + CDAN.
- Artifact store: hybrid; repository SDD files under `specs/phase_12_cdan/` plus compact Engram records.
- Delivery strategy: single PR exception approved by the user for this Phase 12 execution despite expected review workload above 400 changed lines.
- Existing repository state: Phase 12 production and test files are already present in the worktree; the required SDD directory was absent at audit start.
- Protected prior methods: Source-Only, CORAL, and MMD must remain behaviorally unchanged and regression-protected.
- No commits or pushes are authorized in this phase execution.

## Immutable scientific decisions

- Supported cohorts remain ADNI and OASIS only.
- Supported directions remain ADNI -> OASIS and OASIS -> ADNI.
- Public model remains PADA-3DACB.
- PADA-3DACB is the former Lite/no-contextual-encoder architecture.
- Full architecture, `ContextualROIEncoder`, `ctx_enc`, and identity patch behavior are excluded.
- Class order remains CN = 0, MCI = 1, AD = 2.
- Source folds and target partitions are immutable.
- Target adaptation and target evaluation are disjoint.
- Target diagnosis labels do not enter adaptation training.
- Target evaluation remains monitoring-only.
- Source-validation macro-F1 remains the sole best-checkpoint criterion.
- Fixed epochs remain required; early stopping is prohibited.
- Concept normalizers are not refitted per fold.
- Experiment phases do not rerun preprocessing, artifact precomputation, or splits.

## Phase 12 CDAN decisions

- Public method label: `PADA-3DACB + CDAN`.
- Declared CDAN variant: exact outer-product conditioning using subject embedding `z` and latent classifier probabilities from the current forward pass.
- Conditional tensor: for `z ∈ R^(B,d)` and `p ∈ R^(B,3)`, construct `H_i = z_i p_i^T` and flatten deterministically to `h ∈ R^(B, d * 3)`.
- Default embedding dimension `d=128` implies conditional dimension 384, but implementation must infer and validate the dimension.
- Neither `z` nor latent probabilities may be detached.
- GRL uses explicit finite non-negative constant coefficient; no hidden progress schedule exists.
- Discriminator consumes flattened conditional representation and returns one logit per sample with no sigmoid final layer.
- Domain labels are generated internally: source = 0, target = 1.
- CDAN loss is concatenated `BCEWithLogitsLoss(reduction="mean")` over source and target logits and labels.
- Warm-up remains source-only and must not consume target adaptation, construct conditional features, call discriminator, or update discriminator parameters.
- Full stage uses one shared PADA-3DACB model, one shared discriminator, one AdamW optimizer with explicit model/discriminator parameter groups, one backward pass, and one optimizer step per paired source-target batch.

## Explicit exclusions

- No entropy conditioning.
- No randomized multilinear projection.
- No pseudo-labels.
- No prototype alignment.
- No baseline methods.
- No Phase 13 production files.

## Open discrepancies / limitations

- Repository audit found existing Phase 12 implementation files before the SDD directory existed. This execution must validate and reconcile those files against the approved Phase 12 specification rather than assume they are correct.
- Previous Engram evidence reported local host dependency limitations: normal dependency resolution may be blocked, while `--no-deps` is not equivalent to a clean installation.
