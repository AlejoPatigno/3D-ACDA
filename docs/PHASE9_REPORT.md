# Phase 9 Report

## Warm-up discrepancy resolution

The executed training and baseline definitions apply warm multipliers
`0.1/1.0/0.0/1.0/1.0` to base coefficients
`1.0/1.0/0.1/0.5/0.2`. The effective coefficients multiplying raw warm losses
are therefore `0.1/1.0/0.0/0.5/0.2`. `CoreLossWeights.effective()` now exposes
this distinction, configuration and both Phase 8 documents agree, and the new
exact test asserts it. Before Phase 9 implementation, focused Phase 8 tests
reported `22 passed`; the complete precondition suite reported
`135 passed, 2 warnings`.

## Implementation

Created:

- `src/pada3dacb/experiments/{__init__,source_only,runner,run_manifest,prediction_export,fold_summary}.py`
- eight requested `tests/test_source_only_*.py` suites and `phase9_helpers.py`
- `docs/SOURCE_ONLY_EXPERIMENT.md` and this report

Updated source-only/training configuration, `scripts/train.py`,
`SourceOnlyTrainer`, exceptions, Phase 8 loss documentation/tests and the
cumulative audit.

The config loader composes approved model and training YAMLs, validates the
public label `PADA-3DACB Source-Only`, rejects contextual/early-stopping or
unsupported methods, and validates effective warm coefficients. The runner
loads immutable artifacts and manifests, builds source train/validation plus
optional target evaluation only, prepares feature masks, runs fixed epochs,
evaluates both predeclared checkpoint policies, exports predictions and writes
fold/experiment summaries.

No target-adaptation loader is imported, constructed or passed to training.
Target evaluation appears only in no-gradient monitoring. Source macro-F1 is
the sole best-checkpoint criterion.

## Manifests and predictions

Run manifests atomically track PENDING/RUNNING/INTERRUPTED/COMPLETED/FAILED,
source/target assignment hashes, artifact/atlas/ROI hashes, model/training and
experiment hashes, environment, timing, parameter count and checkpoint paths.
Resume preserves manifest identity. Completed folds are reused only when the
experiment hash and required outputs match.

Prediction CSVs use the stable 19-column schema documented in
`SOURCE_ONLY_EXPERIMENT.md`, fixed class order CN/MCI/AD, unique subject rows
and probabilities summing to one. Best-source and last policies remain
separate even when they reference the same epoch.

## Modes and orchestration

One/subset/all five folds, one/multiple seeds and one/both directions execute
sequentially. Failed folds remain in summaries; `fail_fast` controls whether
the next fold is attempted. Dry-run performs input/workload validation without
training or checkpoints. Validate-only adds model/mask/loader construction and
one no-gradient forward without optimizer step.

Focused Phase 9 validation:

```text
13 passed
```

## Synthetic CLI evidence

The CLI was exercised only with generated fixtures under `runs/`; no ADNI or
OASIS image was read. The evidence covered:

- `--all-folds --dry-run`: folds 0-4 were validated as PENDING with 12 source
  train, 3 source validation and 3 target-evaluation records per fold.
- `--fold 0 --both-directions --dry-run`: both `ADNI_to_OASIS` and
  `OASIS_to_ADNI` validated with distinct immutable assignment hashes.
- `--fold 0 --validate-only`: model, masks and loaders were built and one
  no-gradient forward completed with feature grid `[2, 2, 2]`.
- `--fold 0 --seed 42`: the two-epoch synthetic fold completed and emitted
  best-source/last checkpoints, histories, manifests, summaries and separate
  source-validation/target-monitoring predictions.
- Repeating the completed command reused its outputs and preserved the
  experiment hash.
- A separate run interrupted after epoch 1 entered INTERRUPTED; resuming from
  `checkpoint_last.pt` completed epoch 2 while preserving the run hash.

## Final validation

The required commands completed on 2026-07-20:

```text
python -m pip install -e .
Successfully installed pada3dacb-0.1.0

python -c "import pada3dacb; print(pada3dacb.__version__)"
0.1.0

python -m pytest -q
148 passed, 2 warnings in 890.57s

python -m ruff check .
All checks passed!
```

Both warnings are the previously known one-element standard-deviation warning
in the preprocessing parity case; Phase 9 introduced no new warning.

## Boundaries

No real cohort training, preprocessing, precompute, split regeneration,
concept-normalizer refit, early stopping, target training, CORAL, MMD, CDAN,
prototype/pseudo-label method, domain discriminator, gradient reversal,
baseline or publication evaluation was implemented. Phase 10 was not started.

Subject to explicit approval, Phase 10 may introduce the first approved domain
adaptation method and its method-specific losses/configuration without changing
the source-only reference.
