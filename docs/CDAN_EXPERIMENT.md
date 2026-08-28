# Phase 12 CDAN Experiment Contract

Phase 12 declares exactly one new method: `3D-ACDA + CDAN`. It reuses the existing 3D-ACDA subject-level model and the established UDA experiment flow for ADNI/OASIS only. The implementation is intended for synthetic/focused wiring validation until the unresolved real-run hyperparameters are supplied explicitly.

## Declared variant

| Area | Contract |
|---|---|
| Method id | `cdan` |
| Display name | `3D-ACDA + CDAN` |
| Base model | Existing 3D-ACDA Lite/no-contextual-encoder architecture |
| Cohorts | ADNI and OASIS only |
| Directions | `ADNI -> OASIS` and `OASIS -> ADNI` only |
| Conditioning | Exact outer product of subject embedding and current latent class probabilities |
| GRL | Explicit finite non-negative constant coefficient |
| Discriminator | Binary MLP, one raw logit per sample, no final sigmoid |
| Domain labels | Generated internally: source = `0`, target = `1` |
| Checkpoint selection | Source-validation macro-F1 only |
| Target metrics | Monitoring-only, never model selection |

## Equations and tensor contracts

For each source or target sample, CDAN uses the current forward pass:

```text
z_i in R^d
p_i = softmax(latent_logits_i) in R^3
H_i = z_i p_i^T in R^(d x 3)
h_i = flatten(H_i) in R^(d * 3)
```

Batch contract:

```text
z: (B, d)
p: (B, 3)
h: (B, d * 3)
```

With the default embedding dimension `d = 128`, the discriminator input dimension is `384`. The implementation must infer and validate `d * 3`; it must not silently accept a mismatched discriminator input dimension. Neither `z` nor `p` may be detached before CDAN loss construction, so the full-stage adversarial loss can reach the encoder path, latent classifier path, and discriminator parameters.

## GRL, discriminator, and domain objective

The gradient reversal layer is an identity function in the forward pass and scales the incoming feature gradient by `-grl_coefficient` in the backward pass. The coefficient is constant for the run; missing, negative, NaN, infinite, or scheduled coefficients are invalid.

The discriminator consumes flattened CDAN conditionals and returns raw logits compatible with `BCEWithLogitsLoss`; it does not include a final sigmoid. CDAN constructs domain labels internally and computes one concatenated sample mean:

```text
source_domain = zeros_like(source_logits)
target_domain = ones_like(target_logits)
domain_bce = BCEWithLogitsLoss(reduction="mean")(
    concat(source_logits, target_logits),
    concat(source_domain, target_domain),
)
cdan_loss = cdan_weight * domain_bce
```

## Training stages

### Warm-up

Warm-up remains source-only. It must not consume target-adaptation batches, construct CDAN conditionals, call the discriminator, update discriminator parameters, or report a nonzero CDAN loss.

### Full stage

Each paired source/target step uses one shared 3D-ACDA model, one shared discriminator, one AdamW optimizer with explicit model and discriminator parameter groups, one combined loss, one backward pass, and one optimizer step:

```text
total_loss = source_objective + cdan_weight * domain_bce
```

## Data isolation and exports

Target-adaptation diagnosis labels are isolated from training. They must not contribute to loss, gradients, checkpoint selection, prediction export, or domain-label creation. Target monitoring runs read-only and must restore model mode/gradient state.

Prediction exports may include source-validation and target-monitoring records with:

```text
method = cdan
model = 3D-ACDA + CDAN
```

Target-adaptation predictions and internal domain labels are not exported.

## Checkpoint, resume, and provenance

CDAN run identity, manifests, and checkpoints must include the method label, conditional variant, CDAN weight, GRL coefficient, discriminator configuration, discriminator optimizer group, and relevant loader generator states. Resume must restore the shared model, discriminator, optimizer groups, checkpoint metadata, and loader provenance consistently.

## Explicit exclusions

Phase 12 does not include entropy conditioning, randomized multilinear projection, pseudo-labels, confidence filtering, prototype alignment, target diagnosis supervision, target-guided checkpoint selection, early stopping, baseline methods, Phase 13 work, `ContextualROIEncoder`, `ctx_enc`, identity patch behavior, preprocessing reruns, artifact precomputation reruns, split regeneration, or per-fold concept-normalizer refitting.

## Real-run blockers

Real ADNI/OASIS CDAN training remains blocked until these scientific values are supplied explicitly:

- CDAN adaptation weight for real experiments.
- Constant GRL coefficient for real experiments.
- Discriminator hidden dimensions and dropout for real experiments.
- Discriminator optimizer learning rate and weight decay for real experiments.
- Real-run seed/fold command matrix beyond smoke or validate-only commands.

Do not replace these with invented defaults.

## Current evidence status

Current evidence is synthetic/focused only. The mathematical verification reported `47 passed, 1 warning` for focused CDAN/GRL/discriminator/loss/resume tests and manual tensor probes. No real ADNI/OASIS training result is claimed here.

Final full regression and real-run evidence remain placeholders for the final validation action.
