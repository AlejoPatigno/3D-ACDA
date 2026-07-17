# Preprocessing

Phase 4 modularizes the preprocessing implementation from
`notebooks/archive/preprocess_original.ipynb`.

The implementation preserves the notebook operation order:

1. discover cohort-specific input files;
2. select one scan per subject;
3. load MRI-like data on CPU;
4. convert to channel-first 3D tensor `(1, H, W, D)`;
5. replace NaN and infinity with zero during tensor conversion;
6. robust intensity normalization over positive voxels;
7. trilinear resize with `align_corners=False`;
8. center crop or zero padding;
9. save a model-ready CPU `.pt` tensor.

No new registration, skull stripping, bias correction, atlas resampling,
histogram matching, harmonization, augmentation, denoising or tissue
segmentation is performed.

## Supported Inputs

Supported input formats follow the canonical notebook:

- NIfTI-like files: `.nii`, `.nii.gz`, `.img`, `.hdr`, `.mgz`, `.mgh`
- PyTorch: `.pt`, `.pth`
- NumPy: `.npy`, `.npz`
- DICOM files or series directories when SimpleITK is available

NIfTI inputs are read with nibabel and converted with
`nib.as_closest_canonical`, matching the notebook. The final `.pt` tensor does
not preserve a NIfTI physical-space header. Source physical metadata are
recorded in the sidecar when available.

## Cohort Discovery

ADNI discovery expects class-label directories named `CN`, `MCI` or `AD` under
the configured root. Subject IDs are extracted with the notebook pattern
`\d{3}_S_\d{4}` when present, otherwise from the filename.

OASIS discovery requires a metadata CSV with an ID-like column and `CDR`.
Subject IDs are extracted from OASIS-style names. Scan selection preserves the
notebook scoring rule: filenames containing `mpr`, `t1`, `brain`, `struc`,
`processed`, `masked` or `talairach` are prioritized; ties use path order.

No implicit Kaggle path search is performed.

## Normalization

Robust normalization is:

```text
vals = x[x > 0]
lo = quantile(vals, 0.01)
hi = quantile(vals, 0.99)
x = clamp(x, lo, hi)
x = (x - mean(vals)) / max(std(vals), 1e-6)
```

If there are no positive voxels, the tensor is returned unchanged.

## Resize, Crop and Padding

Resize uses PyTorch 3D interpolation with:

- mode: `trilinear`
- `align_corners=False`
- axis permutation from `(1,H,W,D)` to `(1,1,D,H,W)` and back

Center crop/padding creates a zero-filled target tensor and copies the centered
crop using integer floor offsets, preserving the notebook behavior for odd
differences.

## Output Contract

Each processed subject produces a plain CPU tensor:

```text
(1, target_H, target_W, target_D)
dtype=torch.float32
```

The tensor is saved atomically to:

```text
<output_root>/<class_label>/<subject_id>_MRI.pt
```

Each tensor may have a sidecar:

```text
<output_file>.pt.json
```

The sidecar records source path, selected scan, original/final shape and dtype,
operation order, configuration hash, source metadata and status.

## Manifests

The output root receives:

- `preprocessing_manifest.csv`
- `preprocessing_summary.json`
- `preprocessing_summary.md`
- `failures.csv`
- `skipped.csv`
- `configuration_resolved.yaml`
- `preprocessing_metadata.json`

Failed rows are retained in the manifest.

## Restart and Dry Run

With `resume: true` and `overwrite: false`, existing outputs are skipped only
when they can be loaded, match the target shape, contain finite values and have
a compatible sidecar configuration hash when present.

Dry-run mode discovers and plans outputs but writes no model-ready `.pt`
tensors. It writes reports only to the configured output root.

## CLI

ADNI:

```bash
python scripts/preprocess.py \
  --config configs/preprocessing/default.yaml \
  --cohort ADNI \
  --input-root /path/to/adni \
  --output-root /path/to/model_ready_data/adni
```

OASIS:

```bash
python scripts/preprocess.py \
  --config configs/preprocessing/default.yaml \
  --cohort OASIS \
  --input-root /path/to/oasis \
  --metadata-csv /path/to/oasis_metadata.csv \
  --output-root /path/to/model_ready_data/oasis
```

Atlas compatibility is evaluated separately by Phase 3 derivative verification.
