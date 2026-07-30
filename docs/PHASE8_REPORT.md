# Phase 8 Report

## Delivered scope

Phase 8 implements the external feature-grid mask bridge, four retained core
losses, typed total-loss composition, fixed-epoch training, source validation,
isolated target monitoring, atomic checkpoints, exact resume, durable history
and a synthetic-only CLI. Phase 9 was not started.

Created production files:

- `src/pada3dacb/models/roi_mask_preparation.py`
- `src/pada3dacb/losses/{classification,concept,anatomical,consistency,core_total,outputs}.py`
- `src/pada3dacb/training/{trainer,source_only_trainer,uda_trainer,checkpointing,history,monitoring,runtime}.py`
- `configs/training/default.yaml`
- `docs/LOSSES_AND_TRAINING.md` and `docs/PHASE8_REPORT.md`
- The twelve requested `tests/test_*` Phase 8 suites and `tests/phase8_helpers.py`

Updated exports, exceptions, typed configuration defaults, synthetic
`scripts/train.py`, and `docs/IMPLEMENTATION_AUDIT.md`.

Canonical symbols migrated from training are `AtlasROIManager._resize_masks`,
`_normalize_masks`, `get_masks`, `ClassificationLoss`,
`ConceptSupervisionLoss`, `AnatomicalConsistencyLoss`,
`PredictionConsistencyLoss`, the supervised terms and weights of
`DomainAdaptiveTotalLoss`, `DomainAdaptiveTrainConfig` and generic behavior of
`DomainAdaptiveMRITrainer`. The baseline active `SupervisedTotalLoss` confirms
the concept-first warm stage. Precompute/baseline copies were parity references
only.

## Scientific contracts

Mask preparation is nearest interpolation without `align_corners` or
threshold, followed by per-ROI sum normalization with epsilon `1e-8`. Empty
post-resize ROIs fail. Ordering and source tensors are preserved; no atlas is
written. Exact parity tests compare directly against the notebook operations.

Full core coefficients are `1.0` latent CE, `1.0` concept CE, `0.1` asymmetric
KL consistency, `0.5` concept MSE and `0.2` weighted anatomical MSE. Both CEs
use label smoothing `0.1`. Warm multipliers are respectively `0.1`, `1.0`,
`0.0`, `1.0`, `1.0`; these are multipliers, not final weights. Combined with
the base weights, the effective warm coefficients are
`0.1/1.0/0.0/0.5/0.2`. Every component is returned and logged independently.
Gradients reach the encoder and both classification branches; no prediction or
concept tensor is detached.

## Runtime behavior

The fixed schedule defaults to 20 warm plus 30 full source-supervised epochs.
AdamW uses `lr=3e-4`, `weight_decay=1e-4`; the canonical notebook has no
scheduler. Gradients are zeroed with `set_to_none=True`, backpropagated once,
then norm-clipped to 5.0. AMP is CUDA-only and safely disabled on CPU.

The reusable future-UDA iterator takes one step per source batch and cycles
target batches, matching the notebook. Phase 8's UDA trainer refuses execution
because no adaptation plugin is approved.

Source validation computes core loss when artifacts exist, accuracy and
macro-F1. Only source macro-F1 selects the best checkpoint, without stopping.
Target metrics are namespaced and labeled
`MONITORING ONLY — NOT A TRAINING LOSS`; they cannot alter gradients,
optimizer, scheduler, checkpoints or epoch count.

Checkpoints atomically save complete model/runtime/RNG/provenance state.
Resume validates configuration, model dimensions, split, atlas and ROI order,
then restores model, optimizer, optional scheduler/scaler, epoch, step, best
source F1, RNG, loader generator and history position. A shuffled synthetic
interrupted/resumed test matched uninterrupted parameters exactly with
`rtol=0`, `atol=0`.

## Focused parity and integration

The Phase 8 focused suite contains 21 CPU tests. Equations are compared to
direct PyTorch transcriptions at `rtol=0`, `atol=0`; the integrated model
forward/backward and resume compare finite gradients and exact parameters.
The Phase 6/7/8 smoke builds a `LabeledSourceDataset` item, prepares Phase 5
grid masks, runs explicit PADA-3DACB, computes every core loss and backpropagates.

Focused result before global validation:

```text
21 passed in 78.36s
All checks passed!
```

Required final commands and results:

```text
python -m pip install -e .
exit 0
Successfully built pada3dacb
Successfully installed pada3dacb-0.1.0

python -c "import pada3dacb; print(pada3dacb.__version__)"
exit 0
0.1.0

python -m pytest -q
exit 0
134 passed, 2 warnings in 556.53s (0:09:16)

python -m ruff check .
exit 0
All checks passed!
```

Both warnings are the pre-existing one-element standard-deviation warning in
the preprocessing parity case and its reference calculation. Phase 8 added no
warning.

## Synthetic command evidence

Fixed run:

```text
python scripts/train.py --synthetic-smoke --run-dir runs\phase8_fixed_smoke --warmup-epochs 1 --full-epochs 1
exit 0
synthetic_smoke_ok epochs_completed=2 global_step=2 history_rows=2
```

Interrupted and resumed run:

```text
python scripts/train.py --synthetic-smoke --run-dir runs\phase8_resume_smoke --warmup-epochs 1 --full-epochs 1 --interrupt-after-epoch 1
exit 0
synthetic_smoke_ok epochs_completed=1 global_step=1 history_rows=1

python scripts/train.py --synthetic-smoke --run-dir runs\phase8_resume_smoke --warmup-epochs 1 --full-epochs 1 --resume-from runs\phase8_resume_smoke\checkpoint_last.pt
exit 0
synthetic_smoke_ok epochs_completed=2 global_step=2 history_rows=2
```

Generated files are `checkpoint_best_source_f1.pt`, periodic epoch 001/002,
`checkpoint_last.pt`, `training_history.csv`, `runtime.json`,
`config_resolved.yaml`, and `reproducibility_metadata.json`. Inspection found
two target-monitoring rows with the required label, best source F1
`0.16666666666666666`, and zero target-monitoring checkpoint-selection keys.

The first attempted fixed smoke under `C:\tmp` exited 1 before training because
Windows denied directory creation. Repeating inside Git-ignored `runs/` exited
0. This was an environment path-permission discrepancy, not scientific or
runtime behavior.

## Boundaries

No contextual encoder, Full model, identity patch, early stopping, target loss,
concept refit, CORAL, MMD, CDAN, prototype alignment, pseudo-label adaptation,
baseline architecture, confusion matrix or real-cohort execution was added.

Subject to approval, Phase 9 may add the final source-only experiment runner,
its configuration, CLI and experiment-level validation without introducing
domain adaptation.
