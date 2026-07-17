# Derivative Verification

Phase 3 implements Option A: verify existing MRI derivatives and the prepared
atlas from local files and metadata.

The verifier is read-only. It does not perform registration, resampling,
interpolation, skull stripping, intensity normalization, crop/padding, tissue
segmentation, derivative repair or generation of new model-ready files.

## Supported Inputs

Derivative inspection supports:

- `.nii`
- `.nii.gz`
- `.mnc` when readable by the configured imaging stack
- `.pt`
- `.npy`
- `.npz`

NIfTI-like files provide array and physical metadata when available: shape,
affine, spacing, orientation, dtype, numerical summaries and world-space
bounding boxes. Plain `.pt` tensors provide tensor shape, dtype and numerical
summaries, but usually do not provide affine, spacing, orientation or
physical-coordinate information.

## Verification Dimensions

Reports keep separate statuses for:

- `tensor_contract_status`
- `numerical_status`
- `atlas_integrity_status`
- `physical_geometry_status`
- `array_grid_status`
- `overlay_status`
- `overall_status`

Statuses are:

- `PASSED`
- `WARNING`
- `FAILED`
- `INSUFFICIENT_METADATA`
- `NOT_APPLICABLE`

Shape equality can verify array-grid compatibility, but it does not prove
anatomical registration. Physical-space compatibility requires affine, spacing,
orientation and bounding-box metadata.

## Atlas Integrity

Atlas validation checks that the atlas:

- can be read;
- has three spatial dimensions;
- contains finite values;
- has integer-like labels;
- contains non-background labels;
- has non-empty discovered ROIs;
- has a valid affine when available;
- optionally matches the configured expected ROI count.

The expected ROI count is configurable and is treated as an explicit check, not
as a hard-coded generic assumption.

## Geometry Checks

When both derivative and atlas expose physical metadata, the verifier compares:

- affine matrices;
- voxel spacing;
- orientation codes;
- determinant sign;
- world-space bounding boxes;
- spatial dimensions.

When metadata are absent, physical geometry is reported as
`INSUFFICIENT_METADATA`. Plain `.pt` tensors can pass array-grid checks while
remaining physically unverifiable.

## Numerical Checks

Numerical integrity includes:

- finite voxel fraction;
- NaN and infinity detection;
- min, max, mean and standard deviation;
- nonzero voxel fraction;
- constant-volume detection;
- configurable extreme-value warnings.

The verifier never normalizes or changes image values.

## Overlays

Overlays are generated only when the derivative and atlas arrays have compatible
grids. No resampling is performed to create an overlay.

For `.pt` tensors with matching atlas grids but no affine metadata, overlays are
labeled:

`ARRAY-GRID OVERLAY ONLY - PHYSICAL GEOMETRY UNVERIFIED`

Overlays are visual quality-control aids, not proof of pathological validity.

## Configuration

Default configuration:

```text
configs/verification/derivatives.yaml
```

Important fields include:

- expected spatial shape;
- expected ROI count;
- supported tensor keys for `.pt` dictionaries;
- affine, spacing and bounding-box tolerances;
- finite and nonzero fraction thresholds;
- overlay sampling size and seed;
- output overwrite policy.

The configuration rejects options that enable registration, resampling,
interpolation, skull stripping or normalization.

## CLI Usage

```bash
python scripts/verify_derivatives.py \
  --config configs/verification/derivatives.yaml \
  --inventory /path/to/inventory.csv \
  --atlas /path/to/prepared_atlas.nii.gz \
  --output-dir /path/to/verification_output
```

Optional overrides:

- `--sample-size`
- `--seed`
- `--strict-physical-geometry`
- `--subjects`
- `--overwrite`
- `--no-overlays`

## Inventory

The inventory must include `derivative_path`. Optional columns include:

- `subject_id`
- `cohort`
- `class_label`
- `source_image_path`
- `split`

The verifier does not recursively search arbitrary directories by default.

## Outputs

The output directory contains:

- `subjects.csv`
- `summary.json`
- `summary.md`
- `failures.csv`
- `warnings.csv`
- `insufficient_metadata.csv`
- `atlas_report.json`
- `overlay_sample.csv`
- `configuration_resolved.yaml`
- `verification_metadata.json`
- `overlays/*.png`

## Interpretation

Allowed restrained conclusions include:

- array-grid compatibility was verified for a specific number of subjects;
- physical-space compatibility could not be established for plain tensors;
- available metadata showed compatible affine, spacing and orientation within
  configured tolerances.

Do not conclude that images are registered to MNI unless metadata directly
support that statement and the report contains the evidence.
