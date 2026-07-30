# Architectural baselines

Phase 14 migrates only the two baseline architectures that the canonical notebook actually executes: **AAGN** and **FasterSNN**. All other discovered architectures remain blocked because they are active-but-not-executed, obsolete, helper-only, post-hoc, or a prohibited copy of PADA-3DACB.

## Supported registry

| Registry id | Display name | Class | Required input | Trainable parameters |
|---|---|---|---|---:|
| `aagn` | AAGN / ROI-aware gating | `ROIAwareGatingBaseline` | MRI `[B,1,D,H,W]` plus static ROI masks `[K,D,H,W]` | 3,866,596 with three default ROI masks |
| `faster_snn` | FasterSNN | `FasterSNNBaseline` | MRI `[B,1,D,H,W]` | 291,603 |

Registry order is deterministic. Aliases are explicit. Unknown, fuzzy, blocked, copied-model, and PADA names fail without fallback.

```python
from pada3dacb.models.baselines import build_baseline, get_baseline_spec, list_baselines

assert list_baselines() == ("aagn", "faster_snn")
model = build_baseline("faster_snn", {})
```

## Canonical provenance

The authoritative source is `notebooks/archive/baselines_original.ipynb`, participating cell 17.

| Baseline | Notebook symbol | Participating range | Resolved constructor |
|---|---|---|---|
| AAGN | `ROIAwareGatingBaseline` | lines 603–625 | `n_classes=3`, `base_ch=32`, `embed_dim=128`, `dropout=0.1` |
| FasterSNN | `FasterSNNBaseline` | lines 575–600 | `n_classes=3`, effective `base_ch=16`, `dropout=0.1` |

The FasterSNN notebook model config starts at `base_ch=32`, but the participating factory applies `max(16, base_ch // 2)`. Production therefore uses the canonical effective width 16. Explicit constructor overrides remain literal.

## Model contracts

### AAGN

AAGN uses a single-channel 3D backbone, resizes atlas masks with trilinear interpolation, normalizes each mask by voxel sum, pools features in preserved ROI order, and applies softmax ROI gates. It returns:

- `logits`: raw `[B,3]` classification logits;
- `features`: gated feature vector;
- `alpha`: ROI gate weights.

ROI masks are static model inputs. Their ordering and provenance must match the Phase 5 atlas artifacts.

### FasterSNN

FasterSNN uses four ordered stride-2 `Conv3d → InstanceNorm3d → surrogate spike` blocks, adaptive average pooling, and a linear three-class classifier. The local surrogate is:

- forward: `(x > 0).float()`;
- backward: `1 / (1 + abs(x))²`.

It returns raw `logits` and pooled `features`. Every spatial dimension must be at least 17.

## Dataset contract

`ClassificationOnlyMRIDataset` returns:

```text
x, y, subject_id, subject_hash, cohort, label_name
```

It never requires or returns `c_target` or `g_bar`. Labels always follow `CN=0`, `MCI=1`, `AD=2`. Serialized MRI mappings accept exactly one explicit key from `x`, `image`, `mri`, `tensor`, or `volume`.

Canonical preprocessing already produces one MRI channel. Production rejects multi-channel inputs rather than silently truncating to the first channel.

## Source-only comparison protocol

For `ADNI -> OASIS`:

- `ADNI/source_train` trains the baseline;
- `ADNI/source_validation` selects the best checkpoint;
- `OASIS/target_evaluation` is monitoring and prediction export only.

The reverse direction swaps those cohort roles. Baseline orchestration never constructs `target_adaptation`.

Training is fixed epoch, classification-only AdamW with optional cosine scheduling, CUDA-only AMP, gradient clipping, and label smoothing. Early stopping is prohibited. Only strict improvement in source-validation macro-F1 replaces the best checkpoint. Target metrics cannot change loss, gradients, optimizer, scheduler, epoch count, checkpoint selection, architecture, or hyperparameters.

## Execution

```bash
python scripts/train.py \
  --config configs/experiments/baselines.yaml \
  --method baseline \
  --baseline-name faster_snn \
  --source-domain ADNI \
  --target-domain OASIS \
  --fold 0 \
  --seed 42 \
  --artifact-index <resolved-classification-index.csv> \
  --output-root runs
```

Use `--all-baselines`, `--all-folds`, or `--both-directions` for explicit sequential planning. Use `--dry-run` or `--validate-only` before training. Resume/interruption requires one baseline, direction, seed, and fold.

Run directories are isolated by baseline, direction, seed, and fold:

```text
<output_root>/baselines/<baseline_id>/<source>_to_<target>/seed_<seed>/fold_<fold>/
```

Completed-fold reuse validates the content-bound experiment hash and required outputs. Checkpoints are never shared across architectures.

## Prediction and manifest boundaries

Predictions contain subject identity, cohort, fixed label, predicted class, three probabilities, split, checkpoint, and `method=baseline`. Exported splits are `source_validation` and `target_monitoring`; no target-adaptation predictions, confusion matrices, publication statistics, or concept-analysis outputs are produced.

Manifests include baseline identity/configuration/provenance, assignment hashes, parameter count, split counts, experiment hash, and `target_adaptation_loader_constructed: false`.

## Blocked inventory

The following notebook classes are `active_not_executed` and have no Phase 14 production module: `CNNDesignForADBaseline`, `DenseNetCNNBaseline`, `ViTBaseline`, `LongFormerBaseline`, `JointTransformerBaseline`, `BiFPN3DViTBaseline`, and `DAViT3DBaseline`.

`AlzheimerSupervisedMRIModel` is a prohibited proposed-model copy. Its scientific role is already represented by PADA-3DACB Source-Only.

## Computational limitations

Both supported baselines are 3D models. Validate parameter count, minimum input shape, ROI-mask compatibility, and memory before a real run. Phase 14 validation uses deterministic CPU synthetic tensors only and makes no performance claim.
