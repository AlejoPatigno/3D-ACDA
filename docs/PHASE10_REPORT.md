# Phase 10 Report

## Scope and files

Phase 10 implements only `PADA-3DACB + CORAL`. It creates the typed adaptation
interface and CORAL equation under `src/pada3dacb/adaptation/`, replaces the
Phase 8 UDA refusal boundary with CORAL-only training, adds configuration and
orchestration in `src/pada3dacb/experiments/coral.py`, extends the CLI, and adds
the eleven requested Phase 10 test files plus `phase10_helpers.py`.

Shared training checkpoint hooks and prediction metadata parameters were added
with source-only defaults. Run-manifest documentation and fold numeric summaries
were generalized. `configs/experiments/coral.yaml`, `docs/CORAL_EXPERIMENT.md`,
this report and the cumulative audit were added or updated.

Created files:

- `src/pada3dacb/adaptation/{base,coral,outputs}.py`
- `src/pada3dacb/experiments/coral.py`
- `configs/experiments/coral.yaml`
- `docs/CORAL_EXPERIMENT.md` and `docs/PHASE10_REPORT.md`
- `tests/phase10_helpers.py` and the eleven requested `test_coral_*` /
  `test_source_only_regression.py` suites

Updated files include adaptation/experiment/training exports, `trainer.py`,
`uda_trainer.py`, checkpointing, source-only config composition, runner shared
primitives, prediction export, fold summary, run manifest, `scripts/train.py`
and the cumulative audit.

## Mathematical contract

For rank-2 `z` embeddings, covariance uses centered float32 values and the
unbiased denominator `n-1`. CORAL is exactly
`||C_s-C_t||_F^2 / (4 d^2)`. There is no mean alignment, kernel, class
conditioning or alternate feature switch. Tests compare against a direct
reference, verify shifted means, positivity, scalar/finite output, float32 AMP
behavior, and gradients to source, target and the shared encoder.

## Configuration and weight

The public method/model names are `PADA-3DACB + CORAL` and `PADA-3DACB`.
`contextual_encoder` and early stopping must remain false. The adaptation block
fixes method `coral`, feature `z`, warm-up activity false, unbiased covariance,
`four_d_squared` normalization and float32 compute. Missing, negative or
non-finite weights fail. Synthetic fixtures use `1.0`; no publication value was
invented and no target-guided tuning exists.

The exact floating-point weight is represented collision-free in the run path
and participates in both adaptation and full experiment hashes.

## Batch and objective contracts

Source training batches require `x`, `y`, `c_target` and `g_bar`. Target
adaptation batches require exactly `x`, `subject_id`, `subject_hash` and
`cohort`. Dataset construction and runtime assertions reject target label,
concept, anatomy and stored-class-probability fields.

Warm-up consumes source only and retains effective coefficients
`0.1/1.0/0.0/0.5/0.2`; CORAL and target consumption are zero. Full training
runs source and target through one shared model, computes supervised core loss
from source only, adds `weight * L_coral`, performs one backward, one clipping
operation and one optimizer step.

Source controls the epoch length. Target is cycled deterministically when
shorter. Both training loaders require `drop_last=True`, at least one batch and
observed batch size at least two. History records adaptation identity, raw and
weighted loss, embedding/covariance diagnostics and source/target cycle counts.

## Partitions, checkpoints and monitoring

The runner consumes immutable `source_train`, `source_validation`,
`target_adaptation` and `target_evaluation` assignments and verifies that the
target partitions are disjoint. Manifests add adaptation identity/config hash,
weight, target-adaptation/evaluation assignment hashes, counts, expected cycles,
stage activity and `target_training_labels_available: false`.

Best checkpoint selection remains source-validation macro-F1 only. CORAL loss
and target metrics cannot select a checkpoint. Target evaluation remains eval
mode, no-gradient monitoring and is not joined to adaptation data.

Checkpoints store adaptation method/config/hash, weight, all relevant split
hashes and source/target loader-generator states. Resume validates each field;
changing the method, feature, weight or assignment is incompatible. Exact
continuous-versus-resumed parameter equality is covered by CPU tests.

## Outputs and orchestration

One fold, all five folds, multiple explicit seeds and both transfer directions
run sequentially. Source-Only and CORAL paths are separate. Fold summaries add
raw/weighted CORAL results, mean full-stage CORAL, cycles, source checkpoint
metrics and clearly named target-monitoring metrics. The experiment manifest
retains the attempted explicit weight.

Source-validation and target-monitoring exports retain the Phase 9 schema with
`method=coral` and `model=PADA-3DACB + CORAL`. No target-adaptation prediction
file or confusion matrix is emitted. Dry-run performs no forward or optimizer
step; validate-only computes one combined loss without changing parameters.

## Verification status

Focused Phase 10 tests:

```text
24 passed in 108.48s
```

The focused Phase 8/9 regression initially found one historical CLI-message
discrepancy when a Source-Only config was paired with `--method coral`. The
Phase 9 rejection boundary was restored; the affected Source-Only and CORAL CLI
tests then reported `2 passed`. No scientific or Source-Only runtime behavior
changed.

## Synthetic CLI evidence

All evidence used generated tensors under `runs/`; no real ADNI/OASIS data was
read. Every CORAL command supplied `--coral-weight 1.0`.

- `--all-folds --dry-run`: folds 0-4 were PENDING; each planned 12 source
  training, 3 source validation, 12 target adaptation and 3 target evaluation
  subjects, with one source step and zero expected cycles.
- `--fold 0 --both-directions --dry-run`: `ADNI_to_OASIS` and
  `OASIS_to_ADNI` passed with distinct experiment hashes.
- `--fold 0 --validate-only`: completed without optimizer step and produced a
  finite synthetic CORAL scalar `0.0002943641156889498`.
- One two-epoch fold completed: epoch 1 was warm with CORAL `0`, adaptation
  inactive and zero target batches; epoch 2 was full with CORAL
  `0.00032081964309327304`, adaptation active and one target batch.
- The fold selected best source epoch 1, retained last epoch 2 and exported
  source-validation and target-monitoring predictions for both policies.
- A separate run stopped as INTERRUPTED after warm epoch 1, then resumed to
  COMPLETED at epoch 2 with unchanged experiment hash
  `af52f6cf9fbecf27b1c0e8f00b8e8977b893bebc0443c976f4edca7ce3587048`.
- Repeating the completed fold returned `reused: true` and preserved hash
  `d79e755c3b6765a789cf51aa3843e7016615c5ad0f9034aec1793b0fa0fd7850`.
- Source-Only dry-run remained PENDING without a target-adaptation workload.

Checkpoint inspection confirmed method, weight, separate source/target hashes
and generator states named `source_train` and `target_adaptation`. Input
validation recorded exactly `cohort`, `subject_hash`, `subject_id`, `x` for
target adaptation and `target_training_labels_available: false`.

## Final required commands

Executed on 2026-07-21:

```text
python -m pip install -e .
Successfully installed pada3dacb-0.1.0

python -c "import pada3dacb; print(pada3dacb.__version__)"
0.1.0

python -m pytest -q
172 passed, 2 warnings in 1170.22s

python -m ruff check .
All checks passed!
```

The warnings are the two pre-existing one-element standard-deviation warnings
in preprocessing parity; Phase 10 introduced no warning.

## Discrepancies encountered

The first manually generated CLI fixture used a relative root, which its YAML
correctly interpreted relative to the config file and duplicated the prefix.
Fixtures were regenerated with absolute paths, matching test and production
path semantics; all evidence then passed. No production fix was required.

The first global pytest command reached its twenty-minute command limit at 41%
without a failure. It was rerun alone under a thirty-minute limit and completed
with all 172 tests passing. The historical CLI rejection-message discrepancy
described above was also corrected before final validation.

## Explicit boundaries

- No target label entered training and no target supervised loss was computed.
- CORAL was inactive during warm-up.
- Target metrics selected neither checkpoints nor the CORAL weight.
- No early stopping or concept-normalizer refit was introduced.
- Source-Only configuration hash, loss path and target isolation remain intact.
- No MMD, CDAN, discriminator, gradient reversal, prototype, pseudo-label,
  confidence-threshold or baseline implementation was added.
- Phase 11 was not started.

## Proposed Phase 11 files

Subject to explicit approval, Phase 11 could add `adaptation/mmd.py`,
`experiments/mmd.py`, an approved MMD experiment configuration, MMD-specific
tests and documentation while reusing the Phase 10 typed adaptation and UDA
infrastructure. No such production module was created in Phase 10.
