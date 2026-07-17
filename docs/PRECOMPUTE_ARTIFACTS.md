# Phase 5 Artifact Precomputation

## Canonical Source and Boundaries

The scientific source is `notebooks/archive/precompute_original.ipynb`.
Phase 5 consumes Phase 4 model-ready tensors and never preprocesses or modifies
them. It requires an explicit prepared discrete atlas; atlas discovery,
registration, conversion and resampling are not performed. Artifact generation
is separate from datasets, models and training.

## Input Contract

The input CSV must provide `cohort`, `class_label`, `derivative_path` and either
`subject_id` or `subject_hash`. Phase 4 aliases `output_path` and
`configuration_hash` are accepted. Inputs are deterministically ordered and
must be unique by subject and resolved derivative path. Every derivative must
be a finite CPU `torch.float32` tensor shaped `(1,H,W,D)`; the default spatial
shape is `(128,128,128)` and is configurable.

The prepared atlas is loaded in closest canonical orientation only. Labels must
be finite and integer-like. Nonzero labels are sorted numerically, masks are
`float32` with shape `(K,H,W,D)`, and every selected ROI must be non-empty. The
atlas grid must equal the configured MRI grid. A mismatch is an error, not a
request to resize masks. ROI ordering must remain unchanged in training and
evaluation.

## Concept Targets

For subject `n`, the foreground is `x > 0`. The canonical threshold `q_n` is the
20th percentile of all foreground intensities. For ROI `k`:

`s[n,k] = mean(x[v] <= q_n for v in ROI[k])`

The canonical normalizer is fitted independently for each supplied cohort
inventory, using every row whose `class_label` is `CN`; it is not fold-specific.
For each ROI it records population mean and population standard deviation
(`ddof=0`). Targets are:

`c[n,k] = sigmoid((s[n,k] - mu[k]) / (sigma[k] + 1e-6))`

There is no extra clipping or redesigned reference population. Zero variance is
handled only by `epsilon`. The JSON normalizer records statistics, ROI labels,
fitted count, cohort/class composition, configuration and inventory hashes, and
software version. This preserves the notebook protocol, including its use of
diagnostic `CN` labels during artifact generation.

## Jacobian Summary

SimpleITK performs histogram matching (128 levels, 10 match points), followed
by Diffeomorphic Demons with 50 iterations and standard deviation 1.0. Images
use unit voxel spacing, matching the notebook. The displacement field is
optionally smoothed with recursive Gaussian sigma 1.0. SimpleITK computes the
displacement-field Jacobian determinant `J`.

The canonical transform is `psi(J) = -log(clip(J, 1e-6, infinity))`. Its mean is
pooled in each ROI. The resulting `g` is normalized within the subject as
`sigmoid((g - mean(g)) / (std(g) + 1e-6))`. Output is a finite float32 vector
of shape `(K,)`. Displacement fields and Jacobian volumes are not saved by
default. This registration is isolated artifact computation; it neither
replaces nor overwrites preprocessing derivatives.

## Cache and Restart

Outputs use `atlas/`, `concepts/normalizers/`, `concepts/subjects/`,
`jacobians/subjects/`, and `sidecars/`, plus `artifact_index.csv`, summaries,
failures, skipped records, resolved configuration and run metadata. Vector files
are plain tensors for compatibility with the downstream notebook loader.

With `resume: true` and `overwrite: false`, each concept and Jacobian branch is
skipped independently only after loading its tensor and sidecar and validating
shape, dtype, finite values, configuration hash, atlas hash and derivative
identity. Corrupt or incompatible outputs are reported and require explicit
overwrite. Writes use temporary files followed by atomic replacement.

Dry-run validates configuration, inventory, derivative existence and atlas,
identifies the normalizer fitting population and planned paths, and writes only
planning reports. It creates no atlas cache, concept vector, normalizer,
Jacobian vector or intermediate scientific artifact.

## CLI

```text
python scripts/precompute_artifacts.py --config configs/precompute/default.yaml \
  --manifest /path/preprocessing_manifest.csv \
  --atlas /path/CerebrA_discrete_ready.nii.gz \
  --template /path/template_MRI.pt \
  --artifact-root /path/precomputed_artifacts
```

Use `--no-jacobians` for concept-only operation, `--no-concepts` for
Jacobian-only operation, and `--dry-run` for planning. Computation is one
subject at a time and one worker by default. Runtime depends on volume size,
ROI count and Demons convergence; this repository does not invent a benchmark.

## Limitations

SimpleITK is an optional dependency required for Jacobian computation. Phase 5
does not implement atlas preparation, model ROI tokenization, data loaders,
models, losses, training, baselines, evaluation or paper reproduction.
