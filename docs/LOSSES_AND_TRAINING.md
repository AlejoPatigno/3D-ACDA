# Core Losses and Fixed-Epoch Training

## Scientific provenance

The canonical source is `notebooks/archive/training_original.ipynb`: atlas
cell 3, model cell 7, loss cell 8 and trainer cell 12. Precompute contains
older copied component losses. Baselines contains the latest active
`SupervisedTotalLoss`, which confirms the same core full objective and the
concept-first warm-up. Adaptation-only `PrototypeLoss` and `PseudoLabelLoss`
were reviewed but are intentionally not migrated in Phase 8.

## Feature-grid ROI masks

Phase 5 masks `(K,H,W,D)` are converted externally to the encoder grid
`(K,h,w,d)` by the exact `AtlasROIManager.get_masks` procedure:

1. Cast masks to float32 and add a singleton channel dimension.
2. Call `torch.nn.functional.interpolate` with `mode="nearest"` and the exact
   feature shape. No `align_corners` argument and no threshold are used.
3. Flatten each ROI and compute `denom_k = sum(mask_k)`.
4. Reject any ROI that became empty.
5. Normalize after interpolation as `mask_k / clamp_min(denom_k, 1e-8)`.
6. Preserve input ROI order and return on the requested device/dtype.

This is feature-grid pooling preparation, not anatomical registration. The
source tensor is not mutated and no Phase 5 atlas file is overwritten. A
deterministic cache key combines atlas hash, feature shape and preparation
configuration hash; persistence is left to the experiment layer and must use
a separate cache with provenance.

## Core equations

For source labels `y`, latent logits `l_z`, concept logits `l_c`, predicted
concepts `c`, Phase 5 targets `c_target`, and precomputed Jacobian summaries
`g_bar`:

- Latent classification: `L_cls_z = CE(l_z, y, label_smoothing=0.1)`.
- Concept classification: `L_cls_c = CE(l_c, y, label_smoothing=0.1)`.
- Concept supervision: `L_concept = mean((c - c_target)^2)` over batch and ROI.
- Anatomical consistency: `L_anat = mean(omega_k * (c - g_bar)^2)`. Default
  `omega_k=1/K`. The final `mean()` is retained exactly from the notebook.
- Prediction consistency:
  `L_cons = KLDiv(log_softmax(l_z), softmax(l_c), reduction="batchmean")`.
  Neither branch is detached, so gradients reach both classifiers.

The full core objective is:

`L = 1.0 L_cls_z + 1.0 L_cls_c + 0.1 L_cons + 0.5 L_concept + 0.2 L_anat`.

Warm-up is concept-first. The executed notebook's warm multipliers are
`0.1/1.0/0.0/1.0/1.0`, applied to the base coefficients above. Therefore the
effective warm coefficients, which are the values multiplying each raw loss,
are `0.1/1.0/0.0/0.5/0.2`:

`L_warm = 0.1 L_cls_z + 1.0 L_cls_c + 0.5 L_concept + 0.2 L_anat`.

Its effective consistency coefficient is exactly zero. `CoreLossOutput` returns every
component separately; it contains no hidden adaptation field. Loss inputs must
have exact dimensions, batch/ROI agreement, finite values and compatible
devices. Missing `c_target` or `g_bar` fails before backward. Concept
normalizers are never refitted.

## Training runtime

`BaseFixedEpochTrainer` owns the generic loop and `SourceOnlyTrainer` exposes
the labeled-source specialization. `UDATrainer` is only an extension boundary
and raises `PhaseNotImplementedError`; no adaptation method exists in Phase 8.

Canonical defaults are 20 warm-up epochs plus 30 full epochs, AdamW with
learning rate `3e-4` and weight decay `1e-4`, no scheduler, no accumulation,
`zero_grad(set_to_none=True)`, one backward per batch and L2 gradient norm
clipping at `5.0`. AMP is enabled only when requested on CUDA; CPU falls back
to regular float32. Non-finite total loss fails before backward.

The later UDA loader helper preserves the notebook policy: source controls the
number of steps and target is cycled. Both loaders are validated as non-empty.
The Phase 8 source trainer consumes no target adaptation loader.

There is no early stopping. The configured epoch count is fixed. An explicit
`interrupt_after_epoch` exists only to simulate a recoverable interruption and
test resume; it is unrelated to metrics. Source validation uses eval mode and
no gradients, reporting loss, accuracy and macro-F1. Improved source macro-F1
may update `checkpoint_best_source_f1.pt`, but training continues.

Labeled target evaluation is a separate monitoring call. Its metrics use the
`target_monitoring/` namespace and carry the exact label
`MONITORING ONLY — NOT A TRAINING LOSS`. They never contribute to loss,
backward, optimizer, scheduler, checkpoint selection, hyperparameters or epoch
count.

## Checkpoint and resume contract

Atomic files are `checkpoint_last.pt`, `checkpoint_best_source_f1.pt`, and
`checkpoint_epoch_NNN.pt`. They contain model, optimizer, optional scheduler
and AMP scaler state; epoch, global step, best source macro-F1 and stage;
resolved config and hash; split, atlas and ROI-order hashes; seed; Python,
NumPy, CPU and available CUDA RNG states; DataLoader generator state; history
append position; package version and available Git commit. They contain no MRI
data and no target checkpoint-selection state.

Resume validates config/model dimensions through the configuration hash plus
split, atlas, ROI ordering and strict state-dictionary shapes. It restores all
runtime states before the next epoch. Incompatible checkpoints fail clearly.

After every epoch, `training_history.csv` and `runtime.json` are flushed.
Rows contain stage, global step, learning rate, all train loss components,
gradient norm, source metrics, optional target-monitoring metrics, timings and
available CUDA peak memory. `config_resolved.yaml` and
`reproducibility_metadata.json` preserve run provenance.

## Synthetic CLI

Only synthetic smoke execution is available:

```powershell
python scripts/train.py --synthetic-smoke --run-dir runs/phase8_smoke \
  --warmup-epochs 1 --full-epochs 1
```

The same command supports `--interrupt-after-epoch` and `--resume-from` for
checkpoint auditing. Running without `--synthetic-smoke` fails because real
source-only and adaptation experiments belong to later phases.

## Limitations

Phase 8 does not run ADNI/OASIS, refit concepts, recompute Jacobians, generate
splits, implement early stopping, or provide source-only experiment
orchestration, CORAL, MMD, CDAN, prototypes, pseudo-labeling, baselines or
publication evaluation.
