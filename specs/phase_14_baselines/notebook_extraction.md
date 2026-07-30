# Phase 14 Canonical Baseline Notebook Extraction

This document records the executable baseline behavior extracted from `notebooks/archive/baselines_original.ipynb`. It is the canonical migration source for Phase 14 planning and MUST NOT be treated as an implementation artifact. `specs/phase_14_baselines/baseline_inventory.yaml` is the authoritative reconciled implementation-gating inventory.

## Source and execution boundary

| Item | Extraction result |
|---|---|
| Source notebook | `notebooks/archive/baselines_original.ipynb` |
| Inspected cells | Baseline suite cell containing configs, helpers, models, dataset, trainer, CV orchestration, summaries; example usage cell |
| Executed workflow marker | Later definitions in the baseline suite override earlier definitions; the final `run_all_requested_baselines` and example usage call define the workflow that actually participates in execution. |
| Example usage status | The example cell failed under papermill, but it still records the executed call shape and explicit `baseline_names` override. The notebook example uses `cohort="target"`; Phase 14 production first slice intentionally overrides that shape and MUST train only on the explicit source side of the requested direction. |
| External architecture lookup | Not performed. The notebook text is the only source for model contracts. |

## Completeness result

The requested baseline symbol list is complete for model classes that participate in the final baseline factory or final requested/default workflow:

- `CNNDesignForADBaseline`
- `DenseNetCNNBaseline`
- `ViTBaseline`
- `LongFormerBaseline`
- `JointTransformerBaseline`
- `FasterSNNBaseline`
- `ROIAwareGatingBaseline`
- `BiFPN3DViTBaseline`
- `DAViT3DBaseline`

Additional baseline-adjacent symbols were found and classified as helpers, obsolete shadow definitions, posthoc analysis, or proposed-model copies. No additional executable baseline model class was discovered in the inspected baseline workflow.

## Definition precedence

The migration MUST use the last definition that participates in the executed workflow, not merely the last textual definition in the notebook.

| Symbol | Participating definition |
|---|---|
| `BaselineTrainConfig` | Single dataclass definition in the baseline suite. |
| `BaselineModelConfig` | Single dataclass definition in the baseline suite. |
| `ClassificationOnlyLoss` | Single class definition. |
| `ClassificationOnlyTrainer` | Final subclass override of `_ClassificationOnlyTrainerBase`; base trainer methods remain inherited except `fit`. |
| `ClassificationOnlyMRIDataset` | Final dataset definition from the external-validation patch. |
| `build_baseline_model` | Final factory override that includes DA-ViT and BiFPN3DViT. |
| `train_baseline_cv_fold` | Final external-cohort version with `cohort="source"`, `external_cohort="other"`; Phase 14 production first slice constrains this to source-only training (`source_train`/`source_validation`) plus target monitoring (`target_evaluation`). |
| `run_baseline_cv_for_cohort` | Final external-cohort version. |
| `run_all_requested_baselines` | Final external-cohort version using final `REQUESTED_BASELINES` when `baseline_names is None`. |
| `summarize_baseline_cv_results` | Final summary function using pandas grouped mean/std. |

## Baseline classification

| Name | Symbol | Classification | Migration gate | Reason |
|---|---|---|---|---|
| AAGN | `ROIAwareGatingBaseline` | `active_executed` | Implement | Included in final `REQUESTED_BASELINES` and explicitly executed in the example `baseline_names` override. |
| FasterSNN | `FasterSNNBaseline` | `active_executed` | Implement | Included in final `REQUESTED_BASELINES` and explicitly executed in the example `baseline_names` override. |
| Joint-Transformer | `JointTransformerBaseline` | `active_not_executed` | Requires explicit approval before implementation | Included in final `REQUESTED_BASELINES`; commented out in example explicit override. |
| CNN_design_for_AD | `CNNDesignForADBaseline` | `active_not_executed` | Requires explicit approval before implementation | Included in final `REQUESTED_BASELINES`; commented out in example explicit override. |
| DenseNet-CNN | `DenseNetCNNBaseline` | `active_not_executed` | Requires explicit approval before implementation | Included in final `REQUESTED_BASELINES`; commented out in example explicit override. |
| ViT | `ViTBaseline` | `active_not_executed` | Requires explicit approval before implementation | Included in final `REQUESTED_BASELINES`; commented out in example explicit override. |
| DA-ViT | `DAViT3DBaseline` | `active_not_executed` | Requires explicit approval before implementation | Included in final `REQUESTED_BASELINES`; commented out in example explicit override. |
| BiFPN3DViT | `BiFPN3DViTBaseline` | `active_not_executed` | Requires explicit approval before implementation | Included in final `REQUESTED_BASELINES`; commented out in example explicit override. |
| LongFormer | `LongFormerBaseline` | `active_not_executed` | Requires explicit approval before implementation | Present in final factory, absent from final `REQUESTED_BASELINES`, and commented out in earlier defaults. |
| Supervised MRI model copy | `AlzheimerSupervisedMRIModel` | `proposed_model_copy` | Do not migrate | It subclasses the domain-adaptation model and is not part of the final baseline factory or baseline CV workflow. |
| Earlier `build_baseline_model` | first factory definition | `obsolete` | Do not migrate | Superseded by final factory override. |
| Earlier `ClassificationOnlyTrainer.fit` behavior | base fit implementation | `obsolete` except inherited non-`fit` methods | Do not migrate as canonical fit loop | Superseded by final subclass fit implementation. |
| Earlier CV functions and `REQUESTED_BASELINES` | first CV runner/default list | `obsolete` | Do not migrate | Superseded by external-cohort patch definitions. |
| Summary CSV display in example cell | `df_folds`, `df_summary`, `display`, `to_csv` | `posthoc_analysis_only` | Do not migrate into production runtime | It is notebook reporting/output convenience, not reusable production behavior. |
| Common blocks | `ConvNormAct3D`, `ResidualBlock3D`, `Small3DBackbone`, `MLP`, `TransformerBlock`, `TransformerEncoder`, `LocalTransformerEncoder`, `PatchEmbed3D`, `BiFPNLayer3D`, `DeformableMHSA3D`, `DeformableTransformerBlock3D`, ROI helpers, dense helpers, slice/spike helpers | `helper_only` | Migrate only when required by approved baselines | These symbols are not user-facing baselines. |

## Configuration defaults and executed overrides

### `BaselineTrainConfig`

| Field | Notebook default | Example override | Phase 14 production rule |
|---|---:|---:|---|
| `n_epochs` | 25 | 30 | Fixed configured epoch count MUST run; no early stopping. |
| `lr` | `1e-4` | `1e-4` | Preserve as default unless config explicitly overrides. |
| `weight_decay` | `1e-4` | `1e-4` | Preserve as default unless config explicitly overrides. |
| `batch_size` | 2 | 8 | Use explicit config override; tests MAY use smaller synthetic values. |
| `num_workers` | 0 | 0 | Preserve deterministic default. |
| `use_amp` | `True` | default | Enable only on CUDA-compatible device; CPU MUST run without AMP. |
| `grad_clip_norm` | 1.0 | default | Clip gradients after backward; preserve norm. |
| `device` | CUDA if available else CPU | CUDA if available else CPU | Device MUST be explicit and testable. |
| `log_every` | 10 | default | Notebook does not use this field in final fit; production MAY omit or expose as nonfunctional metadata only if documented. |
| `early_stopping_patience` | 10 | 6 | MUST NOT control training termination in production. Keep only as rejected notebook conflict if retained for metadata compatibility. |
| `scheduler` | `cosine` | default | `cosine` MUST map to `CosineAnnealingLR(T_max=n_epochs)`; unsupported values MUST disable scheduler or fail explicitly per design. |
| `label_smoothing` | 0.0 | default | Pass to cross entropy. |
| `seed` | 42 | default | Fold seed MUST be `seed + fold_idx`. |

### `BaselineModelConfig`

| Field | Notebook default | Example override | Executed model override behavior |
|---|---:|---:|---|
| `input_shape` | `(128, 128, 128)` | inferred from dataset | `train_baseline_cv_fold` MUST infer from the first training sample and override the model config. |
| `n_classes` | 3 | 3 | All classifiers output `[B, n_classes]` logits. |
| `base_ch` | 32 | 16 | Factory overrides: DenseNet/FasterSNN use `max(16, base_ch // 2)`; BiFPN uses `max(8, base_ch)`; AAGN and CNN use `base_ch`. |
| `embed_dim` | 128 | 128 | Shared transformer/ROI embedding dimension. |
| `n_heads` | 4 | 4 | Transformer attention heads. |
| `n_layers` | 2 | 2 | Factory overrides depth by baseline. |
| `dropout` | 0.1 | 0.1 | Used in transformer/head dropout where present. |
| `patch_size` | `(16,16,16)` | `(16,16,16)` | Used by ViT, LongFormer, DA-ViT. |
| `n_slice_tokens` | 24 | default | Used by Joint-Transformer. |
| `longformer_window` | 32 | default | Used by LongFormer only. |

## Model contracts

All baseline model `forward` methods accept MRI tensors shaped `[B, 1, D, H, W]` and MUST return a mapping containing `logits` shaped `[B, n_classes]`. Additional keys are model-specific and MUST NOT be used for checkpoint selection.

| Symbol | Constructor defaults | Factory overrides | Output keys | ROI/static inputs | Notable limitations/conflicts |
|---|---|---|---|---|---|
| `CNNDesignForADBaseline` | `n_classes=3`, `base_ch=24` | `n_classes=cfg.n_classes`, `base_ch=cfg.base_ch` | `logits`, `features` | None | Uses shared 3D CNN backbone and dropout fixed at 0.2 in head. |
| `DenseNetCNNBaseline` | `n_classes=3`, `base_ch=24`, `growth=16` | `base_ch=max(16, cfg.base_ch // 2)` | `logits`, `features` | None | Growth remains fixed unless explicitly added to config. |
| `ViTBaseline` | `input_shape=(128,128,128)`, `n_classes=3`, `embed_dim=128`, `heads=4`, `depth=4`, `patch_size=(16,16,16)`, `dropout=0.1` | `depth=max(3, cfg.n_layers + 1)` | `logits`, `features` | None | Requires patch-grid token count compatible with positional embedding size. |
| `LongFormerBaseline` | Same as ViT plus `window=32` | `depth=max(3, cfg.n_layers + 1)`, `window=cfg.longformer_window` | `logits`, `features` | None | Present in final factory but not final default list; implementation requires approval. |
| `JointTransformerBaseline` | `n_classes=3`, `embed_dim=128`, `heads=4`, `depth=2`, `n_slices=24`, `dropout=0.1` | `depth=cfg.n_layers`, `n_slices=cfg.n_slice_tokens` | `logits`, `features` | None | Uses sampled 2D slices from all three axes; axis naming in notebook is approximate. |
| `FasterSNNBaseline` | `n_classes=3`, `base_ch=24` | `base_ch=max(16, cfg.base_ch // 2)` | `logits`, `features` | None | This is a surrogate spiking-style classifier, not a full SNN runtime. |
| `ROIAwareGatingBaseline` | `roi_masks`, `n_classes=3`, `base_ch=32`, `embed_dim=128` | `roi_masks` resolved from atlas, `base_ch=cfg.base_ch`, `embed_dim=cfg.embed_dim` | `logits`, `features`, `alpha` | Requires ROI masks shaped `[K,D,H,W]` after normalization/resizing. | Must fail if ROI masks are unavailable. |
| `BiFPN3DViTBaseline` | `input_shape=(128,128,128)`, `n_classes=3`, `base_ch=24`, `embed_dim=128`, `heads=4`, `depth=2`, `dropout=0.1` | `base_ch=max(8,cfg.base_ch)`, `depth=max(1,cfg.n_layers)` | `logits`, `features`, `token_attention`, `feature_map` | None | Memory-heavy; attention token count depends on downsampled 3D shape. |
| `DAViT3DBaseline` | `input_shape=(128,128,128)`, `n_classes=3`, `embed_dim=128`, `heads=4`, `depth=4`, `patch_size=(16,16,16)`, `dropout=0.1` | `depth=max(2,cfg.n_layers + 1)` | `logits`, `features`, `patch_tokens` | None | Deformable attention is a notebook approximation using learnable spatial bias, not an external implementation. |

## Dataset and input contracts

- `ClassificationOnlyMRIDataset` MUST read an inventory DataFrame with `x_path` and either `label` or `Label`.
- Default label order MUST be `CN:0`, `MCI:1`, `AD:2` unless an explicit label map is supplied.
- Tensor loading MUST prefer keys `x`, `image`, `mri`, `tensor`, `volume` when a serialized object is a mapping.
- Input tensors MAY be `[D,H,W]` and MUST be converted to `[1,D,H,W]`.
- Multi-channel tensors MUST be reduced to the first channel only if production design approves the notebook behavior; otherwise this must be a failing validation rule.
- Samples MUST expose `x`, `y`, `subject_id`, and `label_name`.

## Training and evaluation contracts

- Loss MUST be cross entropy with configured label smoothing.
- Optimizer MUST be AdamW with configured learning rate and weight decay.
- Scheduler MUST be cosine annealing over configured fixed epochs when `scheduler == "cosine"`.
- AMP MUST be enabled only when `use_amp` is true and the device is CUDA.
- Gradient clipping MUST use `grad_clip_norm` after gradients are available and before optimizer step.
- Metrics MUST include accuracy, macro-F1, macro recall, macro precision, and macro one-vs-rest AUC when computable.
- Checkpoint selection MUST use `source_validation` macro-F1 only (`val_f1_macro`).
- Target metrics MUST be computed from `target_evaluation` for monitoring/reporting only and MUST NOT influence model selection, scheduler policy, early termination, or model state.
- Production baselines MUST never construct or consume a `target_adaptation` loader.
- Production first-slice orchestration MUST reject target-cohort training. A direction such as OASIS -> ADNI means OASIS supplies `source_train` and `source_validation`, while ADNI supplies `target_evaluation` only.
- Class weighting is not implemented in the notebook; Phase 14 MUST NOT invent class weights unless a later scientific decision explicitly approves them.
- The notebook contains early stopping, but Phase 14 production MUST enforce fixed epochs and no early stopping.

## Orchestration contracts

- `train_baseline_cv_fold` final notebook workflow defaults to `cohort="source"`, `external_cohort="other"`, `n_splits=5`, `fold_idx=0`; production first-slice orchestration MUST expose this as explicit source-only training.
- Stratified CV MUST use `StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)` on the source cohort only.
- Fold seed MUST be `train_cfg.seed + fold_idx`.
- `n_splits` MUST fail when larger than the smallest source class count.
- External cohort resolution for first-slice production MUST resolve `target_evaluation` as monitoring/export only. Notebook-compatible values MAY be parsed only when they still produce source-only training; values that request target training MUST fail or be deferred behind later scientific approval.
- Result payload MUST include baseline name, source cohort, target cohort, fold index, `source_train`/`source_validation`/`target_evaluation` counts, train/model configs, best score, final source-validation metrics, final target-evaluation metrics, and history.
- Saved artifacts, when enabled, MUST use safe stems and include weights plus metrics JSON.
- `summarize_baseline_cv_results` MUST build per-fold rows and grouped mean/std summaries for validation and external metric columns.

## Production migration gates

1. Production implementation MUST begin with only `active_executed` baselines: AAGN and FasterSNN.
2. `active_not_executed` baselines MUST NOT be implemented unless the orchestrator/user explicitly approves them for the implementation slice.
3. `obsolete`, `helper_only`, `posthoc_analysis_only`, and `proposed_model_copy` symbols MUST NOT become public production baselines.
4. Shared helpers MAY be implemented only when needed by an approved baseline or by the accepted orchestration contract.
5. No copied `AlzheimerSupervisedMRIModel` production baseline is allowed.

## Inventory reconciliation notes

`baseline_inventory.yaml` is now the reconciled authoritative inventory for implementation gating. It includes `AlzheimerSupervisedMRIModel` as `proposed_model_copy`, classifies AAGN and FasterSNN as `active_executed`, classifies active-but-not-executed baselines as blocked pending approval, and records obsolete/helper/posthoc symbols with explicit migration gates.

Additional extraction notes:

- `LongFormerBaseline` is `active_not_executed`: it is present in the final factory but omitted from the final default `REQUESTED_BASELINES` and not executed by the example override.
- The final example explicitly executes only AAGN and FasterSNN, even though the final default list contains eight baselines.
- The notebook's final `ClassificationOnlyTrainer` inherits optimizer, scheduler, AMP, gradient clipping, and evaluation behavior from the base trainer but overrides `fit`.
