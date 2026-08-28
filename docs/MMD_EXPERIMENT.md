# 3D-ACDA + MMD

## Scientific role

`3D-ACDA + MMD` is the second classical unsupervised domain-adaptation
comparison. It is newly added and was not extracted from the notebooks. The
architecture, immutable partitions, source core losses, warm-up, fixed epochs,
optimizer, clipping, source checkpoint criterion, monitoring and prediction
schema remain identical to Source-Only and CORAL.

MMD aligns distributions of the shared subject embedding `z`; it does not align
class labels and is not applied to MRI voxels, feature maps, ROI tokens,
attention, concepts, logits or probabilities.

## Distances and kernel

Pairwise squared Euclidean distances are evaluated in float32 with autocast
disabled locally:

```text
D(x,y) = ||x||^2 + ||y||^2 - 2 x y^T
```

Only small negative distances caused by floating-point roundoff are clamped to
zero. Embeddings are not normalized.

For each explicit positive finite bandwidth `sigma`:

```text
k_sigma(x,y) = exp(-D(x,y) / (2 sigma^2))
```

The production kernel is the arithmetic mean of all configured Gaussian RBF
kernels. Empty, duplicate, non-positive or non-finite bandwidths fail. There is
no median heuristic, learned bandwidth, target-guided selection, alternate
kernel family or class conditioning.

## Biased estimator

The exact squared MMD estimator is:

```text
L_mmd = mean(K_ss) + mean(K_tt) - 2 mean(K_st)
```

It is the biased empirical estimator and includes diagonal self-kernel entries.
The final loss is not clamped. Source and target may have unequal batch sizes,
but each batch must contain at least two examples. Gradients remain connected
to both forwards through the same 3D-ACDA model.

## Objective and warm-up

Warm-up consumes source only and retains:

```text
L_warm = 0.1 L_cls_z + 1.0 L_cls_c + 0.0 L_cons
       + 0.5 L_concept + 0.2 L_anat
```

No target-adaptation batch, target forward, distance matrix, kernel or MMD loss
is used during warm-up. Raw and weighted MMD are recorded as zero.

During the full stage:

```text
L_total = L_core_source + adaptation.weight * L_mmd
```

Target adaptation contributes only through MMD. Classification, concept,
anatomical and consistency losses use source examples exclusively.

## Hyperparameter governance

Production configuration declares both `adaptation.weight` and
`adaptation.kernel.bandwidths` as null. Every execution, including dry-run,
must provide an explicit finite non-negative weight and a non-empty list of
unique positive finite bandwidths. The fixture values `1.0` and
`[0.5, 1.0, 2.0]` are engineering values, not publication recommendations.

The ordered bandwidth list and exact floating-point weight participate in the
adaptation and experiment hashes. The kernel directory uses a hash of family,
ordered bandwidths, aggregation, estimator and diagonal policy. No automatic
tuning or ranking exists, and target monitoring may not select weight or
bandwidths.

## Data and iteration

The immutable roles are `source_train`, `source_validation`,
`target_adaptation` and `target_evaluation`. The target partitions are verified
as disjoint. `TargetAdaptationDataset` exposes exactly `x`, `subject_id`,
`subject_hash` and `cohort`; labels and supervised artifacts never enter the
training batch.

Source controls the number of steps. Target batches cycle deterministically
when shorter. Both training loaders use `drop_last=True`, must be non-empty and
must produce batches of at least two. Valid unequal batch sizes are supported.

## Checkpoints and monitoring

Best checkpoint selection uses source-validation macro-F1 only and training
always completes all fixed epochs. MMD, kernel diagnostics and target metrics
do not influence selection. Target evaluation remains no-gradient,
monitoring-only and cannot select weight or bandwidths.

Checkpoints record method, complete adaptation configuration/hash, weight,
feature, estimator, diagonal policy, kernel family, ordered bandwidths, split
hashes and both training-loader generator states. Resume rejects any mismatch
and cannot reinterpret Source-Only or CORAL runtime state as MMD.

## Outputs and CLI

Runs use:

```text
<output_root>/mmd/<source>_to_<target>/seed_<seed>/
  weight_<exact_float_label>/kernel_<hash>/fold_<fold>/
```

Each completed fold contains resolved configuration, validation and run
manifests, epoch/best/last checkpoints, history, runtime metadata, fold metrics,
logs and separate source-validation and target-monitoring predictions. No
labeled target-adaptation prediction or confusion matrix is generated.

```powershell
python scripts/train.py `
  --config configs/experiments/mmd.yaml `
  --method mmd `
  --mmd-weight 1.0 `
  --mmd-bandwidths 0.5 1.0 2.0 `
  --source-domain ADNI `
  --target-domain OASIS `
  --fold 0 `
  --seed 42
```

All folds, seeds, both directions, path overrides, monitoring switches, resume,
overwrite, dry-run and validate-only are supported. Dry-run performs no model
forward. Validate-only computes source core plus one finite MMD objective without
backward, optimizer step or parameter modification.

## Limitations

No real ADNI/OASIS experiment or performance claim is included. There is no
automatic kernel selection, CDAN, discriminator, gradient reversal, prototype
alignment, pseudo-labeling, confidence threshold, baseline architecture,
confusion matrix or publication-level statistical analysis. Source-Only and
CORAL remain unchanged.
