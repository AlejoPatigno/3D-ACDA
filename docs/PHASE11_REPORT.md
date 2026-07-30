# Phase 11 Report

## Scope and files

Phase 11 implements only `PADA-3DACB + MMD`.

Created:

- `src/pada3dacb/adaptation/mmd.py`
- `src/pada3dacb/experiments/mmd.py`
- `configs/experiments/mmd.yaml`
- `docs/MMD_EXPERIMENT.md` and this report
- `tests/phase11_helpers.py`
- fourteen requested MMD and Source-Only/CORAL regression test files

Updated adaptation and experiment exports, the shared UDA trainer, CORAL runner
hooks, fold summaries, CLI and cumulative audit. Source-Only code, model/core
loss definitions, partition generation and concept normalizers were not changed.

## Mathematical definition

Distances use the float32 matrix identity
`||x||^2 + ||y||^2 - 2xy^T`, clamping only negative roundoff in squared
distances. The sole kernel is the arithmetic mean of explicit Gaussian RBF
kernels `exp(-D/(2 sigma^2))`.

The loss is the biased estimator
`mean(K_ss) + mean(K_tt) - 2 mean(K_st)`, including both self-kernel diagonals.
The final value is not clamped. MMD operates only on subject embedding `z` and
supports unequal source/target batch sizes of at least two.

Direct-reference tests cover distances, each kernel, bandwidth averaging,
diagonal inclusion, estimator, translations, unequal counts, float32 AMP
behavior and gradients to source, target and the shared encoder.

## Configuration and governance

The public label is `PADA-3DACB + MMD`. Method `mmd`, feature `z`, kernel
`gaussian_rbf_mixture`, aggregation `mean`, estimator `biased`, diagonal true,
float32 compute and warm-up activity false are fixed. Weight and bandwidths are
required and validated; no publication value was invented. Ordered bandwidths
and exact weight affect configuration hash, experiment hash and run path.

There is no automatic bandwidth heuristic, candidate ranking or target-guided
tuning. Synthetic fixtures use weight `1.0` and bandwidths `[0.5, 1.0, 2.0]`.

## Batch, objective and history contracts

Source batches retain `x/y/c_target/g_bar`. Target-adaptation Dataset, runner
and trainer checks allow only `x/subject_id/subject_hash/cohort`. No target
label or supervised target loss enters training.

Warm-up consumes source only, does no target forward or kernel computation and
records raw/weighted MMD zero. Full training performs one source and one target
forward through the shared model, source core loss plus weighted MMD, one
backward, one clipping operation and one optimizer step.

Source controls steps and target cycles deterministically. History records MMD,
weighted MMD, kernel means, embedding diagnostics, mean distance, declared
kernel metadata, source steps, target consumption and cycles. Full matrices are
not logged.

## Checkpoints, monitoring and outputs

Checkpoints add complete MMD configuration/hash, weight, feature, estimator,
diagonal policy, kernel family, ordered bandwidths, source/target split hashes
and both loader-generator states. Resume validates all fields. Source-validation
macro-F1 remains the sole best-checkpoint criterion; MMD and target monitoring
cannot select checkpoints or hyperparameters.

Run manifests add kernel and estimator provenance, counts, cycles, stage
activity and `target_training_labels_available: false`. MMD has a separate
weight/kernel-hash directory. Prediction exports retain the Phase 9 schema with
`method=mmd` and `model=PADA-3DACB + MMD`; no target-adaptation labels or
predictions are exported.

## Verification evidence

Focused results:

```text
MMD mathematics/configuration: 25 passed
MMD trainer/orchestration/regression: 11 passed
MMD prediction/reuse: 1 passed
Source-Only and CORAL regression: 38 passed
All requested Phase 11 tests: 42 passed in 318.20s
```

One PowerShell wildcard did not expand when passed directly to pytest; rerunning
with an explicit resolved file list produced the 38 passing regression tests.
One expanded negative-contract run reached its five-minute command limit after
16 passes and no failure; the same cases subsequently passed in both the
42-test Phase 11 run and the complete repository run.

Final package validation:

```text
pip install --no-deps -e .: passed (pada3dacb 0.1.0)
public package/MMD imports: passed
python -m pytest -q: 214 passed, 2 warnings in 3023.10s
python -m ruff check .: All checks passed!
git diff --check: passed
```

The two warnings are the pre-existing single-element standard-deviation warning
in the preprocessing parity case; no Phase 11 test emitted a warning. The first
editable-install attempt stalled while resolving dependencies after the known
connection failure. It was terminated and repeated successfully with
`--no-deps`, using the dependencies already present in the bundled runtime.

Synthetic CLI evidence used only generated CPU fixtures and explicit test-only
parameters `weight=1.0` and `bandwidths=[0.5, 1.0, 2.0]`:

| Scenario | Result |
|---|---|
| Five-fold dry run | Folds 0-4 planned with immutable split counts and no target labels |
| Both directions | `ADNI_to_OASIS` and `OASIS_to_ADNI` planned successfully |
| Validate only | Passed; finite MMD `0.036449551582336426` |
| Full fold | Completed warm epoch 1 and full epoch 2; final MMD `0.03175485134124756` |
| Completed-fold rerun | Returned `reused: true` |
| Controlled interruption | Returned `INTERRUPTED` after epoch 1 |
| Exact resume | Continued from `checkpoint_last.pt` and completed epoch 2 with the same experiment hash |
| Source-Only/CORAL CLI regression | Both prior methods planned successfully |
| Unequal source/target batches | Covered by trainer-level CPU evidence and direct estimator tests |

The completed MMD run selected `best_source_f1` at epoch 1 using source
validation macro-F1 only. Target monitoring remained explicitly non-training
and did not select the checkpoint, weight or bandwidths.

## Explicit boundaries

- No target label entered training and no target supervised loss was computed.
- MMD was inactive during warm-up.
- Target metrics selected no checkpoint, weight or bandwidth.
- No early stopping or concept-normalizer refit was introduced.
- Source-Only and CORAL behavior remained unchanged.
- No CDAN, discriminator, gradient reversal, prototype, pseudo-label,
  confidence-threshold or baseline implementation was added.
- Phase 12 was not started.

## Proposed Phase 12 files

Subject to explicit approval, Phase 12 could add a declared CDAN method,
configuration, runner integration, tests and documentation while reusing the
validated UDA infrastructure. No CDAN production file was created in Phase 11.
