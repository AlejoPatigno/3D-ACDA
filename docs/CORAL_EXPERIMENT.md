# 3D-ACDA + CORAL

## Scientific role

`3D-ACDA + CORAL` is the first classical unsupervised domain-adaptation
comparison in this repository. It preserves the Phase 9 model, source folds,
target split, source core objective, optimizer, fixed epochs, gradient clipping,
checkpoint policy and prediction schema. CORAL is new engineering work and was
not present in the canonical notebooks.

The adaptation partition is unlabeled at the Dataset and batch boundaries.
Target labels from the immutable manifest remain available only for split audit;
they are not loaded by `TargetAdaptationDataset`. The fixed, disjoint
`target_evaluation` partition remains monitoring-only.

## Representation and equation

CORAL operates only on the shared 3D-ACDA subject embedding `z` with shape
`(batch, token_dim)`. It does not operate on MRI voxels, feature maps, ROI
tokens, attention, concepts, logits or probabilities.

For centered source and target embeddings, the unbiased covariances are

```text
C_s = (Z_s - mean(Z_s))^T (Z_s - mean(Z_s)) / (n_s - 1)
C_t = (Z_t - mean(Z_t))^T (Z_t - mean(Z_t)) / (n_t - 1)
```

and the exact loss is

```text
L_coral = ||C_s - C_t||_F^2 / (4 d^2)
```

Covariance is computed in float32 with autocast disabled locally. Both batches
must contain at least two samples, have the same feature dimension and device,
and contain finite floating-point values. Neither branch is detached, so the
same model receives gradients through source and target forwards. CORAL aligns
covariance only; there is no mean, kernel or class-conditional term.

## Objective and loaders

Warm-up uses source batches only and retains the effective Phase 8 objective:

```text
L_warm = 0.1 L_cls_z + 1.0 L_cls_c + 0.0 L_cons
       + 0.5 L_concept + 0.2 L_anat
```

CORAL is zero and no target-adaptation batch is consumed or forwarded during
warm-up. During the full stage:

```text
L_total = L_core_source + adaptation.weight * L_coral
```

Only source examples contribute to classification, concept, consistency and
anatomical losses. Target examples contribute only to `L_coral`.

The source loader controls steps per epoch. The target-adaptation loader is
cycled when shorter. Both use the configured training batch size with
`drop_last_train: true`; zero-batch loaders and any observed batch below two
samples fail rather than changing batch size silently.

## Weight governance

Production configuration intentionally declares `adaptation.weight: null`.
Every execution, including dry-run, must supply a finite non-negative value in
configuration or through `--coral-weight`. The value is not inherited from a
notebook and this phase does not choose or tune it. A publication value must be
declared before real execution and may not be selected using target monitoring.

Each weight changes the complete experiment hash and uses a collision-free
directory label derived from its exact IEEE-754 representation. Phase 10 accepts
one explicit weight per run and performs no automatic candidate selection.

## Partitions and monitoring

The immutable Phase 6 roles are:

- `source_train`: source core objective and CORAL source embedding.
- `source_validation`: checkpoint selection by macro-F1 only.
- `target_adaptation`: unlabeled CORAL target embedding only.
- `target_evaluation`: optional no-gradient monitoring only.

Target adaptation and target evaluation are validated as disjoint. Target
monitoring never affects backward, optimizer, scheduler, checkpoint selection
or weight selection. No concept normalizer is refitted.

## Outputs and resume

Runs use:

```text
<output_root>/coral/<source>_to_<target>/seed_<seed>/
  weight_<exact_float_label>/fold_<fold>/
```

Each fold contains resolved configuration, input validation, atomic run
manifest, epoch/best/last checkpoints, training history, runtime and
reproducibility metadata, fold metrics, logs, source-validation predictions and
target-monitoring predictions. No labeled target-adaptation predictions are
exported.

Checkpoints include the method, complete adaptation configuration and hash,
CORAL weight, source and target split hashes, and generator states for both
training loaders. Resume rejects source-only checkpoints, changed weights,
changed features or changed split assignments. Completed folds are reused only
when their experiment identity and required outputs validate.

History records raw and weighted CORAL loss, embedding mean norms, covariance
Frobenius norms, covariance difference, source steps, target batches consumed
and target cycle count. Full covariance matrices are never logged.

## CLI

```powershell
python scripts/train.py `
  --config configs/experiments/coral.yaml `
  --method coral `
  --coral-weight 1.0 `
  --source-domain ADNI `
  --target-domain OASIS `
  --fold 0 `
  --seed 42
```

`--all-folds`, `--all-seeds`, `--both-directions`, path overrides, device,
resume, overwrite and target-monitoring switches are supported. `--dry-run`
validates partitions, label absence, loaders, cycling, hash and intended path
without model forward. `--validate-only` additionally builds the model and
masks, runs one source and target forward, and computes core plus CORAL without
backward or optimizer step.

## Limitations

No real ADNI/OASIS experiment or performance claim is included. There is no
target-guided tuning, early stopping, MMD, CDAN, discriminator, gradient
reversal, prototype alignment, pseudo-labeling, confidence thresholding,
architectural baseline, confusion matrix or publication-level inference.
Source-Only remains the unchanged reference experiment.
