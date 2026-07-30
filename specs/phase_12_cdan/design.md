# Phase 12 Design — PADA-3DACB + CDAN

## Purpose

Phase 12 adds one classical unsupervised domain-adaptation method, `PADA-3DACB + CDAN`, on top of the existing PADA-3DACB UDA workflow. The design is constrained to exact outer-product CDAN with a constant gradient reversal layer and a binary domain discriminator.

## Authorized Architecture

- Base model: existing PADA-3DACB subject-level architecture only.
- Method: `cdan` with display name `PADA-3DACB + CDAN`.
- Cohorts/directions: ADNI/OASIS only; `ADNI -> OASIS` and `OASIS -> ADNI` only.
- Training stages: source-only warm-up followed by full paired source-target adaptation.
- Checkpoint criterion: source-validation macro-F1 only.
- Target evaluation: monitoring-only, read-only, not model selection.

## CDAN Data Flow

1. Source batch enters the shared PADA-3DACB model with diagnosis labels.
2. Target-adaptation batch enters the same shared model without diagnosis labels.
3. The current forward pass produces subject embedding `z` and latent logits/probabilities for source and target samples.
4. CDAN builds conditional features from `z` and latent probabilities without detaching either tensor.
5. Source and target conditional features pass through one shared binary discriminator through a constant-coefficient GRL path.
6. Source domain labels are generated internally as `0`; target domain labels are generated internally as `1`.
7. Concatenated source/target logits and labels feed `BCEWithLogitsLoss(reduction="mean")`.
8. The full objective combines the existing source objective plus `cdan_weight * domain_bce`.

## Tensor Contracts

- `z`: rank-2 tensor, shape `(B, d)`, differentiable.
- latent probabilities `p`: rank-2 tensor, shape `(B, 3)`, differentiable, derived from current latent classifier output.
- conditional matrix per sample: `H_i = z_i p_i^T`.
- flattened conditional tensor: rank-2 tensor, shape `(B, d * 3)`, deterministic flatten order.
- default `d=128` implies discriminator input dimension `384`, but runtime must infer and validate the dimension.
- discriminator output: one raw logit per sample; no sigmoid final layer.

## GRL Contract

- GRL coefficient is explicit, finite, non-negative, and constant.
- No hidden schedule or progress-dependent coefficient may exist.
- Forward values must be unchanged by GRL.
- Backward gradients must be multiplied by `-coefficient`.
- Invalid coefficients must fail validation before training.

## Discriminator Contract

- The discriminator is a binary MLP used only by CDAN.
- It consumes flattened CDAN conditional features.
- It returns one raw logit per sample.
- It must validate positive input dimension, explicit non-empty hidden dimensions, valid activation, dropout in `[0, 1)`, and output dimension equal to 1.
- It must be optimized through the shared full-stage AdamW optimizer with its own explicit parameter group.

## Training Objective

### Warm-up

Warm-up remains source-only:

- no target-adaptation loader consumption;
- no conditional tensor construction;
- no discriminator call;
- no discriminator parameter update;
- zero/no CDAN loss diagnostics.

### Full stage

Each paired source-target batch uses:

- one shared PADA-3DACB model;
- one shared discriminator;
- one AdamW optimizer with explicit model and discriminator parameter groups;
- one combined loss;
- one backward pass;
- one optimizer step.

The weighted objective is:

```text
total_loss = source_objective + cdan_weight * BCEWithLogitsLoss(concat(source_logits, target_logits), concat(zeros, ones))
```

## Configuration and Hash Design

CDAN configuration must include and validate:

- method/display identity;
- conditional variant: exact outer product of `z` and latent probabilities;
- finite non-negative CDAN weight;
- finite non-negative constant GRL coefficient;
- discriminator architecture and dropout;
- discriminator optimizer group;
- internal domain labels source=0 and target=1.

Run identity, manifests, and checkpoints should hash normalized resolved configuration data including method, conditional variant, CDAN weight, GRL coefficient, discriminator configuration, discriminator optimizer settings, and loader generator provenance. A change in these scientific settings should alter identity.

## Data and Monitoring Design

- Target-adaptation labels are not read for training.
- Target-evaluation labels are monitoring-only.
- Source-validation and target-monitoring predictions use the shared subject-level schema.
- Exported predictions include `method=cdan` and `model=PADA-3DACB + CDAN`.
- Target-adaptation predictions and domain labels are not exported.
- Monitoring must restore model mode/gradient state and must not update optimizer state.

## Production File Scope

Approved implementation areas for Phase 12 are limited to:

- CDAN adaptation/loss utilities;
- constant gradient reversal support;
- CDAN domain discriminator support;
- UDA trainer CDAN integration;
- CDAN experiment configuration/orchestration;
- train CLI method routing and explicit CDAN flags;
- CDAN experiment config fixture;
- Phase 12 docs/report;
- Phase 12 tests and test fixtures.

Forbidden production areas:

- preprocessing, artifact cache generation, and split generation;
- full/contextual model architecture and identity patch behavior;
- Phase 13 production files;
- unrelated baseline methods;
- pseudo-label/prototype/entropy/randomized CDAN behavior.

## Testability Design

The specification is testable through focused unit, configuration, CLI, orchestration, and regression tests:

- conditional tensor shape, determinism, and gradient flow;
- GRL forward/backward and coefficient validation;
- discriminator output/logit and configuration validation;
- domain BCE loss labels/reduction/diagnostics;
- warm-up absence of target/discriminator side effects;
- full-stage gradient reachability and optimizer parameter grouping;
- config validation and hash/provenance changes;
- prediction export policy;
- target label rejection;
- Source-Only/CORAL/MMD regression protection;
- scope/audit checks for forbidden later-phase behavior.

## Unresolved Scientific Values

Real-run hyperparameters remain unresolved blockers and must be supplied explicitly. This design intentionally does not invent real-run values for CDAN weight, GRL coefficient, discriminator architecture/dropout, discriminator optimizer settings, or final real-run seed/fold matrix.
