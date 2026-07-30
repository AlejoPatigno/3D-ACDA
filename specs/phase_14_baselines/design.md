# Phase 14 Baseline Migration Design

This design defines the production shape required to migrate the approved canonical baselines without duplicating PADA-3DACB or inventing non-notebook behavior. It is specification-level only; no implementation begins in this action.

## Design principles

1. **Notebook extraction is historical, not production shape.** Production modules MUST be small, typed, testable, and independent of Kaggle paths.
2. **Baselines are classification-only.** They MUST NOT depend on concept targets, domain adaptation losses, pseudo-labeling, or prototype logic.
3. **Gate first, implement second.** Only `active_executed` baselines are in the first slice unless an `active_not_executed` baseline is explicitly approved.
4. **Repository invariants override notebook conflicts.** No early stopping; fixed epochs; `source_validation` macro-F1 checkpoint selection; `target_evaluation` monitoring/export only.
5. **No external architecture discovery.** The notebook text defines the model approximations.

## Proposed production modules

| Path | Responsibility | Public surface |
|---|---|---|
| `src/pada3dacb/models/baselines/__init__.py` | Export approved registry APIs and model classes. | Approved baseline symbols only. |
| `src/pada3dacb/models/baselines/common.py` | Shared helpers and baseline specification/config types required by approved baselines. | Helper and metadata types only. |
| `src/pada3dacb/models/baselines/roi_aware_gating.py` | AAGN / ROI-aware gating classifier. | `ROIAwareGatingBaseline`. |
| `src/pada3dacb/models/baselines/faster_snn.py` | FasterSNN surrogate classifier. | `FasterSNNBaseline`. |
| `src/pada3dacb/models/baselines/registry.py` | Strict approved registry, explicit aliases, construction, and parameter-count metadata. | `list_baselines`, `get_baseline_spec`, `build_baseline`. |
| `src/pada3dacb/data/baseline_dataset.py` | Classification-only MRI dataset over precomputed inventories. | `ClassificationOnlyMRIDataset`, dataset builders. |
| `src/pada3dacb/training/baseline_trainer.py` | Classification loss, trainer, fixed-epoch fit loop, metrics, checkpoint rule. | `BaselineTrainConfig`, `ClassificationOnlyLoss`, `ClassificationOnlyTrainer`. |
| `src/pada3dacb/experiments/baselines.py` | Source-only cross-cohort CV orchestration and summaries. | `train_baseline_cv_fold`, `run_baseline_cv_for_cohort`, `run_all_requested_baselines`, `summarize_baseline_cv_results`. |
| `scripts/train.py` | Existing training entry point integration for approved baseline runs. | Explicit baseline dispatch only. |
| `configs/experiments/baselines.yaml` | Experiment-level baseline selection and reproducible run defaults. | Approved canonical names only. |
| `configs/baselines/aagn.yaml` | AAGN constructor defaults. | AAGN-specific values. |
| `configs/baselines/faster_snn.yaml` | FasterSNN constructor defaults. | FasterSNN-specific values. |
| `docs/BASELINES.md` | Human-facing baseline contract and migration gate. | Supported baselines and scientific caveats. |
| `docs/PHASE14_REPORT.md` | Phase evidence report after implementation/verification. | Commands, evidence, remaining limitations. |
| `docs/IMPLEMENTATION_AUDIT.md` | Implementation-scope and invariant audit. | Approved/omitted files and verification evidence. |
| `tests/phase14_helpers.py` and `tests/test_baseline*.py` | Shared synthetic fixtures and focused flat-layout tests. | No real cohort training. |

Configuration ownership updates the existing experiment configuration and the two baseline-specific configuration files. A generic `configs/baselines/phase14_baselines.yaml` MUST NOT be created.

## Canonical baseline registry

The production registry MUST distinguish available notebook definitions from approved production baselines. Its public API is strict:

- `list_baselines() -> tuple[str, ...]` MUST return canonical approved names in deterministic order.
- `get_baseline_spec(name: str) -> BaselineSpec` MUST resolve canonical names and explicitly declared aliases only.
- `build_baseline(name: str, config: Mapping[str, Any]) -> nn.Module` MUST use the resolved approved specification and validate exactly three output logits under the default class contract.
- Unknown, blocked, misspelled, or approximately matching names MUST fail explicitly; fuzzy matching and fallback construction are prohibited.
- Reproducibility hashes MUST include the selected canonical baseline and all resolved constructor values.

| Baseline | Symbol | Initial production status | Aliases |
|---|---|---|---|
| AAGN | `ROIAwareGatingBaseline` | approved | `aagn`, `roiawaregating`, `aagnstyle`, `roi-aware-gating`, `roi_gating` |
| FasterSNN | `FasterSNNBaseline` | approved | `fastersnn`, `faster_snn`, `faster-snn` |
| CNN_design_for_AD | `CNNDesignForADBaseline` | blocked pending approval | `cnn_design_for_ad`, `cnndesignforad`, `cnn_design_for_adbaseline` |
| DenseNet-CNN | `DenseNetCNNBaseline` | blocked pending approval | `densenet-cnn`, `densenet_cnn`, `densenetcnn` |
| ViT | `ViTBaseline` | blocked pending approval | `vit`, `visiontransformer`, `vision-transformer` |
| LongFormer | `LongFormerBaseline` | blocked pending approval | `longformer`, `long_former` |
| Joint-Transformer | `JointTransformerBaseline` | blocked pending approval | `joint-transformer`, `joint_transformer`, `jointtransformer` |
| DA-ViT | `DAViT3DBaseline` | blocked pending approval | `da-vit`, `davit`, `deformable-vit`, `deformable_vit`, `deformablemhsa-vit` |
| BiFPN3DViT | `BiFPN3DViTBaseline` | blocked pending approval | `bifpn3dvit`, `bifpn-3d-vit`, `bifpn_3d_vit`, `bifpn3dvitbaseline` |

`get_baseline_spec` and `build_baseline` MUST fail for blocked baselines by default. A later implementation slice MAY enable an approved subset by changing the registry and tests in the same work unit.

The requested production files for CNN_design_for_AD, DenseNet-CNN, ViT, LongFormer, Joint-Transformer, DA-ViT, and BiFPN3DViT are intentionally omitted: the authoritative inventory classifies them as `active_not_executed`, and no explicit implementation approval was given. They MUST NOT receive production modules, importable placeholders, or file ownership in this phase.

## Configuration design

### `BaselineTrainConfig`

Production config MUST include these fields unless implementation finds an existing equivalent config mechanism and maps it one-to-one:

- `n_epochs: int = 25`
- `lr: float = 1e-4`
- `weight_decay: float = 1e-4`
- `batch_size: int = 2`
- `num_workers: int = 0`
- `use_amp: bool = True`
- `grad_clip_norm: float = 1.0`
- `device: str | None = None` where `None` resolves to CUDA if available else CPU
- `scheduler: str = "cosine"`
- `label_smoothing: float = 0.0`
- `seed: int = 42`

`early_stopping_patience` MUST NOT be a functional production field. If compatibility requires parsing it from legacy notebook configs, it MUST be ignored with a documented warning or stored as rejected metadata.

### `BaselineModelConfig`

Production config MUST include:

- `input_shape: tuple[int, int, int] = (128, 128, 128)`
- `n_classes: int = 3`
- `base_ch: int = 32`
- `embed_dim: int = 128`
- `n_heads: int = 4`
- `n_layers: int = 2`
- `dropout: float = 0.1`
- `patch_size: tuple[int, int, int] = (16, 16, 16)`
- `n_slice_tokens: int = 24`
- `longformer_window: int = 32`

The fold runner MUST infer `input_shape` from the dataset and pass an updated config to model construction.

## Model design contracts

### AAGN / `ROIAwareGatingBaseline`

- MUST use a single-channel `Small3DBackbone` with `out_ch=embed_dim`.
- MUST store ROI masks as static tensor state and move them to the feature device in `forward`.
- MUST resize ROI masks to feature spatial shape using trilinear interpolation and normalize each mask by voxel sum.
- MUST pool features by weighted ROI mask einsum.
- MUST compute ROI gates with an MLP ending in one logit per ROI and softmax over ROIs.
- MUST return `logits`, `features`, and `alpha`.
- MUST fail construction when ROI masks are missing.

### FasterSNN / `FasterSNNBaseline`

- MUST use local PyTorch layers only.
- MUST use surrogate spike activation where forward is `(x > 0).float()` and backward uses `1 / (1 + abs(x))^2`.
- MUST apply four stride-2 3D convolution blocks with instance norm and spike activation.
- MUST use adaptive average pooling and a linear classifier.
- MUST return `logits` and `features`.

### Blocked models

Blocked `active_not_executed` models MUST NOT have production modules or importable placeholders in Phase 14. Their names MAY appear only as rejection metadata so `get_baseline_spec` and `build_baseline` can fail with an explicit approval error.

## Dataset design

`ClassificationOnlyMRIDataset` MUST be independent of concept and domain-adaptation tensors.

- Inputs: inventory table or DataFrame-like object with `x_path` and `label`/`Label`.
- Optional: `subject_id`.
- Label map default: `CN -> 0`, `MCI -> 1`, `AD -> 2`.
- Tensor loading: use existing repository tensor loader if available; otherwise use safe local torch loading consistent with repository conventions.
- Shape normalization: `[D,H,W]` becomes `[1,D,H,W]`; invalid ndim fails.
- Multi-channel behavior MUST be decided during implementation review: either preserve notebook first-channel truncation with tests and docs or fail fast. It MUST NOT be silent without tests.

## Training design

`ClassificationOnlyTrainer` MUST separate reusable methods from fit policy.

- `evaluate(loader, prefix)` returns prefixed metrics and loss.
- `train_epoch(loader)` performs one optimizer/scheduler epoch.
- `fit(train_loader, train_eval_loader, val_loader, external_loader=None)` runs exactly `n_epochs` epochs.
- Best checkpoint state is copied on strict improvement of finite `source_validation` `val_f1_macro` only.
- After fixed epochs, the trainer loads the best state if available and evaluates final `source_validation` and optional `target_evaluation` metrics.
- History contains one row per epoch; in production this MUST equal configured fixed epochs unless training fails.

## Metrics design

Metrics MUST include:

- accuracy
- macro-F1 with `zero_division=0`
- macro recall with `zero_division=0`
- macro precision with `zero_division=0`
- macro one-vs-rest AUC when computable, otherwise NaN
- mean loss per evaluated loader

Metric computation MUST handle AUC failures without failing the run, matching the notebook.

## Cross-cohort CV design

Production first-slice orchestration MUST be source-only. A direction such as OASIS -> ADNI means OASIS is the explicit source side and supplies `source_train` plus `source_validation`; ADNI supplies `target_evaluation` for monitoring/export only. The reverse direction is allowed only when explicitly requested as ADNI -> OASIS, where ADNI becomes the source side and OASIS becomes `target_evaluation`.

`train_baseline_cv_fold` MUST:

1. Resolve seed as `train_cfg.seed + fold_idx`.
2. Load precomputed artifacts through existing project artifact loaders.
3. Build a classification-only dataset for the explicit source cohort only.
4. Split source samples into `source_train` and `source_validation`.
5. Infer input shape from a source training sample.
6. Validate `n_splits` against source class counts.
7. Build stratified source train/validation indices with `random_state=42`.
8. Build `source_train`, `source_train_eval`, `source_validation`, and optional `target_evaluation` loaders.
9. Never build or consume a `target_adaptation` loader for baselines.
10. Reject first-slice requests that train on the target side of the configured direction instead of the explicit source side.
11. Resolve ROI masks only for AAGN.
12. Build the approved baseline model.
13. Train with fixed epochs using source data only.
14. Return the specified payload and optionally save weights/metrics.

`run_baseline_cv_for_cohort` MUST call the fold runner for every fold index in order for the explicit source cohort only.

`run_all_requested_baselines` MUST default to the approved production registry, not the full notebook default list, unless later approvals extend it.

`summarize_baseline_cv_results` MUST return per-fold and grouped summary tables, with grouped mean/std over source-validation and target-evaluation metric columns.

## Checkpoint and persistence design

- Checkpoint selection: highest `source_validation` `val_f1_macro` only.
- Tie behavior: no replacement on equal score; only strict greater-than replaces best state.
- Saved weights: one state dict per baseline/source cohort/target-evaluation cohort/fold when `save_dir` is configured.
- Metrics JSON: one payload per saved fold.
- Summary JSON/CSV MAY be generated by experiment/reporting code, but notebook `display` behavior MUST NOT be production runtime behavior.

## Parameter count design

Model construction SHOULD produce metadata with total parameters and trainable parameters. Parameter counts MUST be computed directly from instantiated model parameters and MUST NOT be hard-coded from the notebook.

## Optional dependency design

Phase 14 production code MUST use existing project dependencies plus PyTorch/sklearn/pandas already required by the project where applicable. It MUST NOT download architectures or add third-party model packages for FasterSNN, DA-ViT, BiFPN, LongFormer, ViT, DenseNet, or CNN baselines.

## Action graph and file ownership

```text
phase13-closure-and-baseline-audit
  -> canonical-baseline-extraction
  -> independent-specification-review
  -> implement-shared-baseline-framework
      owns: __init__.py, common.py, registry.py, test_baseline_registry.py, test_baseline_common.py
  -> implement-baseline-group-a
      owns: roi_aware_gating.py, test_baseline_roi_aware_gating.py
  -> implement-baseline-group-b
      owns: faster_snn.py, test_baseline_faster_snn.py
  -> independent-baseline-verification
  -> trainer-integration
      owns: baseline_dataset.py, baseline_trainer.py, test_baseline_dataset.py, test_baseline_trainer.py
  -> experiment-config-cli-integration
      owns: experiments/baselines.py, experiments/__init__.py, scripts/train.py,
            configs/experiments/baselines.yaml, configs/baselines/aagn.yaml,
            configs/baselines/faster_snn.yaml, tests/phase14_helpers.py,
            test_baseline_cv.py, test_baseline_cli.py
  -> complete-baseline-integration-tests
      owns: test_baseline_smoke.py, test_baseline_source_only.py
  -> documentation
      owns: docs/BASELINES.md, docs/PHASE14_REPORT.md, docs/IMPLEMENTATION_AUDIT.md
  -> final-audit
  -> final-validation
```

The canonical full path-to-action mapping is `agent_plan.yaml`; this graph is a readable projection of that collision-free ownership table.

Collision rule: if an action needs a file outside its ownership list, the orchestrator MUST update ownership before work starts. No action may create Phase 15 artifacts.

## Review strategy

The implementation is expected to touch executable training/model/config code and tests. It is not docs-only. A bounded post-apply implementation review is required when native review/receipt capability is restored or replaced by the parent workflow. This specification action does not run review lifecycle commands.
