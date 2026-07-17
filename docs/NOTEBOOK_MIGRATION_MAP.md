# Notebook Migration Map

Phase 1 audit date: 2026-07-15.

This document maps the four canonical research notebooks to the planned
modular repository. It is an implementation map only. It does not introduce
new methods, cohorts, baselines, preprocessing operations, or scientific
claims.

## Archived Notebooks

| Canonical source notebook | Archived copy | Cells inspected | Outputs stripped |
|---|---|---:|---|
| `preprocess-alzheimer (2).ipynb` | `notebooks/archive/preprocess_original.ipynb` | 7 | Yes |
| `precompute-artifacts-alzheimer.ipynb` | `notebooks/archive/precompute_original.ipynb` | 17 | Yes |
| `train-domain-adaptation-alzheimer (1).ipynb` | `notebooks/archive/training_original.ipynb` | 20 | Yes |
| `baselines-m-m (1).ipynb` | `notebooks/archive/baselines_original.ipynb` | 20 | Yes |

## PADA-3DACB Architecture Decision

Training is the canonical source for the latest model components. The
precompute and baselines notebooks are parity references for copied or
downstream variants; they must not override the training notebook for model
extraction.

The training notebook model class `AlzheimerDomainAdaptationModel`
instantiates the following former Full architecture path:

`Encoder3D -> ROITokenizer -> token_norm/token_mlp/token_dropout -> ContextualROIEncoder -> AttentionAggregator -> ClassificationHead + ConceptBottleneck`

The previous Lite behavior appears in the training notebook as ablation
`no_ctx_encoder`, implemented by replacing `model.ctx_enc` with
`IdentityContextualEncoder`. The final package must not implement Lite as a
patched Full model. The planned production model is an explicit `PADA-3DACB`
class with:

- `Encoder3D`
- `ROITokenizer`
- ROI token projection and learned ROI embeddings
- token normalization, MLP and dropout when preserved from the notebook
- `AttentionAggregator`
- `ClassificationHead`
- `ConceptBottleneck`
- anatomical consistency losses
- prototype alignment losses
- confidence-controlled pseudo-label losses

Excluded from production code:

- `ContextualROIEncoder`
- transformer contextual ROI encoder instantiated as `ctx_enc`
- the `full` ablation variant
- token mixer or contextual ROI Transformer equivalents
- construction by creating Full and replacing modules with identity

The `mean_pool` ablation is not part of the final proposed architecture.

### Full-to-Lite Computational Transformation

Former Full token flow:

1. Input `x`: `(B, 1, H, W, D)`.
2. `Encoder3D(x)` produces feature map `F`: `(B, C_f, h, w, d)`.
3. `ROITokenizer(F, roi_masks)` pools each ROI mask over `F`, projects
   `(B, K, C_f)` to tokens `T`: `(B, K, C_t)`, and adds learned ROI embeddings.
4. `token_norm/token_mlp/token_dropout` preserve token shape `(B, K, C_t)`.
5. Full-only `ContextualROIEncoder(T)` applies a Transformer encoder and
   returns contextual tokens `U`: `(B, K, C_t)`.
6. `AttentionAggregator(U)` receives contextual tokens and returns subject
   embedding `z`: `(B, C_t)` plus attention `alpha`: `(B, K)`.
7. `ClassificationHead(z)` returns latent logits/probabilities over classes.
8. `ConceptBottleneck(U)` receives contextual tokens and returns concepts
   `c`: `(B, K)` plus concept-head logits/probabilities.

Former Lite/PADA-3DACB token flow:

1. Steps 1-4 are unchanged.
2. The contextual transformation is removed: `U = T` after token projection,
   normalization, MLP and dropout. No `TransformerEncoderLayer`, token mixer or
   `ctx_enc` module is instantiated.
3. `AttentionAggregator` receives non-contextual ROI tokens with shape
   `(B, K, C_t)`, preserving output `z`: `(B, C_t)` and `alpha`: `(B, K)`.
4. `ConceptBottleneck` receives the same non-contextual ROI tokens and
   preserves concepts `c`: `(B, K)` and concept logits.
5. The output dictionary structure should remain behavior-compatible for
   retained keys: `F`, `T`, `U`, `z`, `alpha`, latent logits/probabilities,
   concepts and concept logits/probabilities. In production, `U` may be an
   alias for retained tokens to preserve downstream loss/trainer contracts.

State dictionary implication:

- Former Full checkpoints contain `ctx_enc.*` parameters. Final PADA-3DACB
  checkpoints must not contain or require `ctx_enc.*`.
- Loading former Lite-ablation checkpoints derived from patched Full runs must
  ignore or explicitly reject unexpected `ctx_enc.*` keys rather than silently
  reintroducing a contextual encoder.
- Shared keys for `encoder`, `tokenizer`, `token_norm`, `token_mlp`,
  `token_dropout`, `aggregator`, `cls_head` and `cbm` are candidates for
  controlled partial loading, subject to explicit migration tooling.

### Definition Comparisons

| Symbol | Precompute notebook | Training notebook | Baselines notebook | Phase decision |
|---|---|---|---|---|
| `AlzheimerDomainAdaptationModel` | Full model copy with `ContextualROIEncoder`; used during artifact/training wiring examples. | Latest proposed-model reference; still Full by default, with Lite behavior documented later via `identity_ctx` ablation. | Full model copy plus `AlzheimerSupervisedMRIModel` subclass for supervised workflows. | Extract components from training, but implement a new explicit `PADA-3DACB` class without `ctx_enc`. Use baselines only for supervised parity. |
| `ConceptBottleneck` | Present as copied model component; includes commented linear per-ROI version and active per-ROI MLP version. | Canonical active version for proposed model: per-ROI MLPs followed by sigmoid concepts and linear concept classifier. | Copied version for supervised/baseline workflows. | Use training active version; document any checkpoint mismatch if old linear concept weights appear. |
| `AnatomicalConsistencyLoss` | Component-level loss copy used by `TotalLoss`. | Canonical DA loss component inside `DomainAdaptiveTotalLoss`. | Copied for supervised/posthoc workflows. | Use training for adaptation behavior; use precompute/baselines for parity checks only. Preserve coefficients and tensor contracts until specific loss phase review. |

## Migration Table

| Original notebook | Original symbol or cell | Responsibility | Destination module | Duplicate definitions | Selected canonical version | Required behavior-preservation tests |
|---|---|---|---|---|---|---|
| `preprocess_original.ipynb` | Cell 4 globals: `K_REGIONS`, `TARGET_SHAPE`, `CLASS_NAMES`, `CLASS_TO_IDX`, dataset paths | early preprocessing configuration and Kaggle path assumptions | `configs/data/*.yaml`, `configs/model/pada3dacb.yaml` | Later preprocessing cell redefines `TARGET_SHAPE` and path discovery | Cell 5 for implementation; cell 4 only as historical config evidence | config validation rejects absolute local/Kaggle defaults under `src/` |
| `preprocess_original.ipynb` | `resolve_dataset_root`, `extract_oasis_base_id`, `load_mri_tensor`, `try_extract_tensor_shape`, `inventory_source_domain`, `get_oasis_label_dict`, `process_target_domain` | initial inventory and tensor loading | `src/pada3dacb/data/inventories.py`, `src/pada3dacb/data/datasets.py` | More robust variants in cell 5 | Cell 5 variants where overlapping | synthetic inventory resolves source and target records |
| `preprocess_original.ipynb` | Cell 5 utility functions: `lower_name`, `is_supported_file`, `strip_medical_suffix`, `sanitize_id`, `make_unique_path`, `print_tree_hint` | file discovery and safe naming | `src/pada3dacb/data/inventories.py` | Similar source path utilities appear in training and baselines notebooks | Keep preprocess notebook as canonical for preprocessing utilities | unit tests for ID sanitization and supported extension detection |
| `preprocess_original.ipynb` | `safe_torch_load`, `extract_tensor_from_object`, `to_channel_first_3d`, `load_nifti_tensor`, `load_numpy_tensor`, `load_pt_tensor`, `load_dicom_series_tensor`, `load_mri_tensor` | load MRI-like inputs into tensors | `src/pada3dacb/data/preprocessing.py` | `load_tensor_like` appears in training/baselines wiring | Preserve preprocess implementation for raw preprocessing; use wiring loaders only for artifact cache resolution | tensor shape/channel tests for `.pt`, NumPy and NIfTI where dependencies are available |
| `preprocess_original.ipynb` | `robust_intensity_normalization`, `resize_3d_tensor`, `center_crop_or_pad_3d`, `mri_transforms` | end-to-end model-ready preprocessing transforms | `src/pada3dacb/data/preprocessing.py` | `PreprocessConfig` functions duplicated in precompute/training/baselines are downstream NIfTI helper utilities, not assumed identical | Preprocess notebook is canonical for ADNI/OASIS discovery, scan selection, intensity normalization, resizing, crop/padding and model-ready `.pt` generation | output shape, finite values, intensity normalization tests |
| `preprocess_original.ipynb` | `extract_adni_subject_id`, `iter_adni_files_by_label`, `find_adni_mprage_series_dirs`, `preprocess_adni_to_pt` | source cohort preprocessing | `src/pada3dacb/data/preprocessing.py`, `scripts/preprocess.py` | Path mapping code duplicated in wired training cells | Preprocess notebook canonical | dry-run manifest test with synthetic file tree |
| `preprocess_original.ipynb` | `find_oasis_clinical_csv`, `choose_oasis_scan`, `process_oasis_domain` | target cohort preprocessing | `src/pada3dacb/data/preprocessing.py`, `src/pada3dacb/data/inventories.py` | OASIS ID extraction appears in cell 4 | Cell 5 selected | OASIS ID parsing and one-scan selection tests |
| `precompute_original.ipynb` | `to_plain_tensor`, `save_plain_mri_pt` | serialization helpers | `src/pada3dacb/artifacts/cache.py` | Same cell appears in training and baselines | Precompute notebook canonical for artifact preparation | round-trip tensor save/load test |
| `precompute_original.ipynb` | `AtlasConfig`, `AtlasROIManager`, `load_label_atlas`, `infer_label_values` | atlas loading and ROI masks | `src/pada3dacb/artifacts/atlas.py` | Same definitions in training/baselines | Precompute notebook canonical | atlas shape, label integrity, ROI mask normalization tests |
| `precompute_original.ipynb` | `ConceptTargetConfig`, `ConceptNormalizer`, `extract_tissue_loss_proxy`, `fit_concept_normalizer`, `build_subject_concept_target`, `precompute_concept_targets_from_dataframe` | concept target computation | `src/pada3dacb/artifacts/concepts.py` | Same definitions in training/baselines | Precompute notebook canonical; do not redesign normalization | synthetic concept vector shape and normalizer serialization tests |
| `precompute_original.ipynb` | `JacobianConfig`, `estimate_displacement_field`, `jacobian_determinant_from_displacement`, `apply_psi`, `pool_roi_deformation`, `compute_g_bar_from_template_and_subject`, `precompute_jacobians_from_dataframe` | anatomical deformation summaries | `src/pada3dacb/artifacts/jacobians.py`, `src/pada3dacb/artifacts/regional_features.py` | Same definitions in training/baselines | Precompute notebook canonical | synthetic displacement/Jacobian finite output tests |
| `precompute_original.ipynb` | `SourceDomainDataset`, `TargetDomainDataset`, `get_domain_adaptation_dataloaders` | early DA datasets | `src/pada3dacb/data/datasets.py` | More complete wired versions in cells 13-14 and training cell 7 | Training notebook for training datasets; precompute for artifact-cache assumptions | source/target batch key contract tests |
| `training_original.ipynb` | `ResBlock3D`, `Encoder3D`, `ROITokenizer`, `AttentionAggregator`, `ClassificationHead`, `ConceptBottleneck` | model components retained in PADA-3DACB | `src/pada3dacb/models/*.py` | Same classes in precompute and baselines | Training notebook cell 8 is canonical for latest model components; baselines and precompute are parity references only | forward shape tests and no contextual encoder test |
| `training_original.ipynb` | `ContextualROIEncoder`, `AlzheimerDomainAdaptationModel` with `ctx_enc` | Full-only contextual model path | Archived only | Same in precompute/baselines | Excluded from production; training remains source of comparison for partial checkpoint migration | test package has no activatable contextual encoder |
| `precompute_original.ipynb` | `ClassificationLoss`, `PrototypeLoss`, `PseudoLabelLoss`, `ConceptSupervisionLoss`, `AnatomicalConsistencyLoss`, `TotalLoss` | losses used by precompute-era model | `src/pada3dacb/losses/*.py` | `DomainAdaptiveTotalLoss` in training supersedes `TotalLoss` | Training notebook for DA loss; precompute for component-level loss behavior | loss component tests on synthetic tensors |
| `precompute_original.ipynb`, `training_original.ipynb`, `baselines_original.ipynb` | `PreprocessConfig`, `load_nifti_canonical`, `make_brain_mask`, `robust_clip_inside_mask`, `zscore_inside_mask`, `resize_volume_torch`, `preprocess_volume_array`, `preprocess_nifti`, `validate_tensor_contract` | duplicated downstream NIfTI helper suite | `src/pada3dacb/data/preprocessing.py` after parity review, or `src/pada3dacb/data/derivative_verification.py` for verification-only helpers | Appears in all three downstream notebooks and must be compared explicitly against dedicated preprocessing notebook behavior | No automatic canonical assumption; preprocess notebook remains canonical for end-to-end preprocessing, while this suite requires parity mapping before extraction | parity tests comparing shape, mask, clipping, z-score, resize and contract behavior on synthetic arrays |
| `precompute_original.ipynb` | `read_image_any_nib`, `image_info_nib`, `unique_summary_nib`, `prepare_cerebra_discrete_atlas_nib`, `compare_geometry_nib`, `resample_label_atlas_to_reference_nib` | atlas preparation and geometry inspection | `src/pada3dacb/data/derivative_verification.py`, `src/pada3dacb/artifacts/atlas.py` | Same in training/baselines | Use only verification parts for Option A; avoid automatic new registration | geometry compatibility and invalid affine tests |
| `precompute_original.ipynb`, `training_original.ipynb`, `baselines_original.ipynb` | `SourceDomainDatasetWired`, `TargetDomainDatasetWired`, `SupervisedMRIDatasetWired`, path resolution, cache validation, `ensure_artifact_cache`, `load_precomputed_artifacts` | workflow-specific loader behavior and artifact validation | `src/pada3dacb/data/datasets.py`, `src/pada3dacb/data/inventories.py`, `src/pada3dacb/artifacts/cache.py` | Repeated with workflow-specific changes | Training, baselines and precompute are behavioral references for their own loader workflows; common loading, path resolution and artifact validation must be consolidated into shared modules | missing artifact, remapped path, source/target/supervised batch contract tests |
| `precompute_original.ipynb` | `build_all_precomputed_artifacts` | artifact precomputation CLI behavior | `src/pada3dacb/artifacts/cache.py`, `scripts/precompute_artifacts.py` | Same in baselines | Precompute notebook canonical | synthetic dataframe precompute smoke test |
| `training_original.ipynb` | `PredictionConsistencyLoss`, `ClassificationLoss`, `PrototypeLoss`, `PseudoLabelLoss`, `ConceptSupervisionLoss`, `AnatomicalConsistencyLoss`, `DomainAdaptiveTotalLoss` | proposed training losses | `src/pada3dacb/losses/*.py`, `src/pada3dacb/adaptation/prototype_pseudo.py` | Older `TotalLoss` in precompute; supervised-only loss in baselines | Training notebook canonical | controlled synthetic loss parity, empty confident pseudo-label set |
| `training_original.ipynb` | `DomainAdaptiveTrainConfig`, `DomainAdaptiveMRITrainer`, `_classification_metrics_from_outputs` | fixed-stage DA training/evaluation | `src/pada3dacb/training/uda_trainer.py`, `src/pada3dacb/evaluation/predictive_metrics.py` | supervised trainer in baselines | Training notebook canonical for DA | fixed epoch loop, metrics logging, target monitoring label tests |
| `training_original.ipynb` | `LabeledMRIDatasetWired`, `UnlabeledTargetAdaptDataset`, `stratified_subject_split`, `_make_stratified_splits` | DA datasets and folds | `src/pada3dacb/data/datasets.py`, `src/pada3dacb/data/splits.py` | baseline supervised datasets overlap | Training notebook canonical for DA splits | deterministic stratified split tests |
| `training_original.ipynb` | `build_patched_model`, `train_domain_adaptation_fold`, `run_domain_adaptation_experiment`, `run_bidirectional_domain_adaptation` | experiment orchestration | `scripts/train.py`, `src/pada3dacb/training/trainer.py` | Similar functions in precompute/baselines | Training notebook canonical, except model must become explicit PADA-3DACB | smoke training config test |
| `training_original.ipynb` | `IdentityContextualEncoder`, `apply_model_ablation` with `identity_ctx`, `get_default_ablation_specs` | evidence for previous Lite behavior and ablations | Documentation only; no production module for contextual ablation | Unique to training notebook | `identity_ctx` documents retained PADA-3DACB behavior; Full and other ablations excluded unless requested | no `PADA-3DACB-Lite` string in final package/docs except archive/migration notes |
| `baselines_original.ipynb` | `AlzheimerSupervisedMRIModel`, `SupervisedTotalLoss`, `SupervisedMRITrainer` | supervised proposed-model training used in baseline workflow | `src/pada3dacb/training/source_only_trainer.py`, `src/pada3dacb/losses/*.py` where compatible | DA versions in training notebook | Training notebook for proposed DA; baselines notebook for supervised workflow | source-only training loss behavior tests |
| `baselines_original.ipynb` | `AnalysisConfig`, `AnalysisAwareSupervisedMRITrainer`, `run_roi_probes`, `run_roi_ablation`, `run_full_posthoc_analysis` | posthoc concept/ROI analyses | `src/pada3dacb/evaluation/concept_metrics.py`, `concept_interventions.py`, `roi_stability.py` | Training notebook has ablation summary utilities | Baselines notebook canonical for posthoc analysis code | saved-prediction analysis tests without retraining |
| `baselines_original.ipynb` | `BaselineTrainConfig`, `BaselineModelConfig` | baseline configuration | `src/pada3dacb/models/baselines/registry.py`, `configs/experiments/baselines.yaml` | None | Baselines notebook canonical | baseline registry schema test |
| `baselines_original.ipynb` | `ConvNormAct3D`, `ResidualBlock3D`, `Small3DBackbone`, `MLP`, `TransformerBlock`, `TransformerEncoder`, `LocalTransformerEncoder`, `BaseBaseline` | shared baseline blocks | `src/pada3dacb/models/baselines/common.py` | Some concepts overlap with proposed encoder but are baseline-specific | Baselines notebook canonical | synthetic shape tests for shared blocks |
| `baselines_original.ipynb` | `CNNDesignForADBaseline` | existing notebook baseline | `src/pada3dacb/models/baselines/cnn_design_for_ad.py` | None | Baselines notebook canonical | instantiate and forward test |
| `baselines_original.ipynb` | `DenseNetCNNBaseline`, `_DenseLayer3D`, `_DenseBlock3D`, `_Transition3D` | existing notebook baseline | `src/pada3dacb/models/baselines/densenet_cnn.py` | None | Baselines notebook canonical | instantiate and forward test |
| `baselines_original.ipynb` | `PatchEmbed3D`, `ViTBaseline` | existing notebook baseline | `src/pada3dacb/models/baselines/vit.py` | None | Baselines notebook canonical | instantiate and forward test |
| `baselines_original.ipynb` | `LongFormerBaseline` | existing notebook baseline | `src/pada3dacb/models/baselines/longformer.py` | None | Baselines notebook canonical | instantiate and forward test |
| `baselines_original.ipynb` | `_SliceEncoder2D`, `JointTransformerBaseline` | existing notebook baseline | `src/pada3dacb/models/baselines/joint_transformer.py` | None | Baselines notebook canonical | instantiate and forward test |
| `baselines_original.ipynb` | `SurrogateSpikeFn`, `SpikeAct`, `FasterSNNBaseline` | existing notebook baseline | `src/pada3dacb/models/baselines/faster_snn.py` | None | Baselines notebook canonical | instantiate and forward test |
| `baselines_original.ipynb` | `ROIAwareGatingBaseline`, `resize_roi_masks`, `masked_roi_pool` | ROI-aware baseline | `src/pada3dacb/models/baselines/roi_aware_gating.py` | ROI pooling overlaps with proposed tokenizer | Keep separate baseline implementation to preserve behavior | ROI mask resize and forward tests |
| `baselines_original.ipynb` | `BiFPNLayer3D`, `BiFPN3DViTBaseline` | existing notebook baseline | `src/pada3dacb/models/baselines/bifpn_3d_vit.py` | None | Baselines notebook canonical | instantiate and forward test |
| `baselines_original.ipynb` | `DeformableMHSA3D`, `DeformableTransformerBlock3D`, `DAViT3DBaseline` | existing notebook baseline | `src/pada3dacb/models/baselines/davit3d.py` | None | Baselines notebook canonical | instantiate and forward test |
| `baselines_original.ipynb` | `ClassificationOnlyLoss`, `ClassificationOnlyTrainer`, `ClassificationOnlyMRIDataset`, `train_baseline_cv_fold`, `run_baseline_cv_for_cohort`, `run_all_requested_baselines`, `summarize_baseline_cv_results` | baseline training/evaluation orchestration | `src/pada3dacb/training/source_only_trainer.py`, `src/pada3dacb/evaluation/reporting.py`, `scripts/train.py` | Function names redefined within same cell | Last definitions in baseline cell selected after manual parity review | classification-only trainer smoke test and registry execution test |

## Duplicate Implementations

- `AtlasConfig`, `AtlasROIManager`, `load_label_atlas`, and `infer_label_values`
  appear in precompute, training and baselines notebooks. Use precompute as the
  canonical artifact implementation.
- Concept target utilities appear in precompute, training and baselines. Use
  precompute as canonical and preserve the existing normalization protocol.
- Jacobian utilities appear in precompute, training and baselines. Use
  precompute as canonical.
- `preprocess_original.ipynb` is canonical for the end-to-end ADNI/OASIS
  preprocessing pipeline: cohort discovery, scan selection, subject ID
  handling, intensity normalization, resizing, crop/padding and model-ready
  `.pt` generation.
- `PreprocessConfig` and the duplicated NIfTI helper suite in precompute,
  training and baselines are downstream helper utilities. They require a
  parity map against the dedicated preprocessing pipeline before extraction;
  do not assume they are identical.
- Dataset and artifact-cache wiring functions are repeated and revised across
  precompute, training and baselines. Use each notebook as behavioral reference
  for its workflow only: precompute for cache creation, training for
  domain-adaptation loaders, and baselines for supervised/baseline loaders.
  Common dataset loading, source/target path resolution and artifact validation
  must be consolidated into shared production modules.
- `AlzheimerDomainAdaptationModel` is repeated in precompute, training and
  baselines. Production must not copy the Full version directly because it
  instantiates `ContextualROIEncoder`.
- `build_patched_model` appears in precompute, training and baselines and
  hard-codes notebook path assumptions. Replace with config-driven builders in
  later phases.
- `ClassificationOnlyTrainer` is defined twice in the baseline cell. Select the
  last in-cell definition after parity review because it shadows the earlier
  one during notebook execution.
- `build_baseline_model`, `train_baseline_cv_fold`,
  `run_baseline_cv_for_cohort`, and `run_all_requested_baselines` are redefined
  in the baseline cell. Select the later definitions after manual behavior
  comparison.

## Shadowed Definition Inventory

| Symbol family | Locations observed | Shadowing pattern | Migration decision |
|---|---|---|---|
| `train_domain_adaptation_fold` | training notebook cells around original DA run and ablation run | Redefined after ablation utilities are introduced; later definition adds `ablation_spec` handling and changes orchestration context. | Keep both as audit references. Production trainer must expose method-specific config rather than hidden shadowing. |
| `run_domain_adaptation_experiment` | training notebook original DA section and ablation section | Redefined for ablation loop handling and fold skip logic. | Extract a single config-driven runner with explicit optional ablation support disabled for final PADA-3DACB unless later approved. |
| `SupervisedTrainConfig` | baselines notebook two class definitions in supervised trainer section | Later class shadows earlier definition during notebook execution. | Compare fields before extraction; use final executed definition for supervised parity tests. |
| `build_all_precomputed_artifacts` | precompute and baselines notebooks; also imported from notebook-local module in execution cells | Function appears both as imported module API and inline notebook copy. | Extract one package API in `artifacts/cache.py`; CLI calls it explicitly. |
| `build_inventory_dataframes` | precompute, training and baselines, with repeated later wired versions | Workflow-specific path handling differs. | Consolidate common inventory schema and path validation, then keep workflow adapters thin. |
| `ensure_artifact_cache` | precompute, training and baselines | Repeated with cache-dir defaults, coverage checks and optional recomputation differences. | Shared artifact cache validator plus explicit precompute command; no hidden recompute in loaders unless configured. |
| `load_precomputed_artifacts` | training, precompute later wired section, baselines later wired section | Repeated remapping of artifact dataframe paths and cache indexes. | Shared loader returns validated cache object used by DA and baseline datasets. |
| `resolve_source_x_path`, `resolve_target_x_path`, `build_source_path_map`, `resolve_single_path`, `discover_project_file`, `load_tensor_like` | precompute, training and baselines | Resolver signatures and base-dir assumptions vary, including map-based vs direct base-dir resolution. | Implement shared path resolver accepting configured roots and inventory rows; workflow modules must not hard-code Kaggle mounts. |

## Hard-Coded Paths Found

The notebooks contain the following hard-coded roots, paths and glob patterns.
Each must become a configuration field or command-line override. No path under
`src/` may contain these values in later phases.

| Notebook path or pattern | Current use | Future configuration field |
|---|---|---|
| `/kaggle/input` | generic dataset mount and search root | `paths.input_root` |
| `/kaggle/working` | generic output root | `paths.output_root` |
| `/kaggle/temp` | transient Kaggle storage note | `paths.temp_root` |
| `/kaggle/input/*{slug_hint}*` | dataset discovery by slug | `data.discovery.slug_globs` |
| `/kaggle/input/**/*.pt` | recursive source tensor search | `data.discovery.tensor_globs` |
| `/kaggle/input/**/*aal*.nii*` | atlas candidate search | `atlas.discovery_globs` |
| `/kaggle/input/**/*atlas*.nii*` | atlas candidate search | `atlas.discovery_globs` |
| `/kaggle/input/**/*harvard*oxford*.nii*` | atlas candidate search | `atlas.discovery_globs` |
| `/kaggle/input/**/*label*.nii*` | atlas candidate search | `atlas.discovery_globs` |
| `/kaggle/working/**/*atlas*.nii*` | generated atlas candidate search | `atlas.generated_discovery_globs` |
| `/kaggle/input/notebooks/alejopatio/preprocess-alzheimer/model_ready_data` | preprocessed model-ready ADNI/OASIS tensors | `paths.model_ready_data` |
| `/kaggle/input/notebooks/alejopatio/precompute-artifacts-alzheimer` | mounted precompute notebook outputs/module root | `paths.precompute_bundle_root` |
| `/kaggle/input/notebooks/alejopatio/precompute-artifacts-alzheimer/cerebra_prepared/CerebrA_discrete_ready.nii.gz` | prepared CerebrA atlas | `atlas.prepared_path` |
| `/kaggle/input/notebooks/alejopatio/precompute-artifacts-alzheimer/precomputed_artifacts_cerebra` | mounted precomputed artifact cache | `paths.precomputed_artifacts` |
| `/kaggle/input/datasets/sanjukaggling/adnidataset/ADNI_dataset` | ADNI data root | `data.adni.root` |
| `/kaggle/input/datasets/sanjukaggling/adnidataset/ADNI_dataset/ad_new_2_19_2026.csv` | ADNI metadata CSV | `data.adni.metadata_csv` |
| `/kaggle/input/datasets/ninadaithal/oasis-1-shinohara` | OASIS data root | `data.oasis.root` |
| `/kaggle/input/datasets/alejopatio/cerebra/mni_icbm152_CerebrA_tal_nlin_sym_09c.mnc` | raw CerebrA atlas | `atlas.raw_path` |
| `/kaggle/working/model_ready_data` | preprocessing output root | `paths.model_ready_output` |
| `/kaggle/working/cerebra_prepared` | prepared atlas output directory | `atlas.output_dir` |
| `/kaggle/working/cerebra_prepared/CerebrA_discrete_ready.nii.gz` | prepared discrete atlas | `atlas.prepared_path` |
| `/kaggle/working/cerebra_prepared/CerebrA_discrete_resampled_to_reference.nii.gz` | resampled atlas artifact from notebooks | `atlas.resampled_path` for legacy compatibility only; Phase 3 must not create new registration |
| `/kaggle/working/precomputed_artifacts` | generic artifact output cache | `paths.precomputed_artifacts` |
| `/kaggle/working/precomputed_artifacts_cerebra` | CerebrA artifact output cache | `paths.precomputed_artifacts` |
| `/kaggle/working/mri_da_missing` | missing-file report output | `paths.missing_report_dir` |
| `/kaggle/working/mri_da_precompute` | precompute run output | `paths.precompute_run_dir` |
| `/kaggle/working/exp_da_cbm` | domain-adaptation experiment output | `paths.runs_root` or `experiment.output_dir` |
| `/kaggle/working/baseline_runs_external` | baseline experiment output | `paths.baseline_runs_root` |
| `/kaggle/working/analysis_cbm` | posthoc analysis output | `paths.analysis_root` |
| `/kaggle/working/ablation_da_cbm` | ablation output root | archived/reference only; no Phase 2 public config unless ablations are later approved |

The raw regex extraction also encountered format-string fragments such as
`l:\n{e}` and `o:\n{path}` inside error messages. These are not filesystem
roots and should not become configuration fields.

## Dependencies Observed

- Python standard library: `os`, `glob`, `re`, `json`, `math`, `random`,
  `warnings`, `hashlib`, `copy`, `pathlib`, `dataclasses`, `typing`,
  `itertools`, `sys`, `shutil`
- Numeric/data: `numpy`, `pandas`
- Deep learning: `torch`, `torch.nn`, `torch.nn.functional`,
  `torch.utils.data`
- Medical imaging: `nibabel`, `nibabel.processing`, `SimpleITK`, `monai`
- Machine learning metrics/splits: `sklearn.metrics`,
  `sklearn.model_selection`
- Notebook-local modules referenced by import or path manipulation:
  `atlas_utils`, `concept_targets`, `jacobian_utils`, `losses`, `model`,
  `trainer`, `build_precomputed_artifacts`. These are local project modules
  and must become package modules under `src/pada3dacb`; they are not external
  requirements.

## Discrepancies and Risks

- The scientific instruction says the previous Lite architecture is now the
  only proposed architecture, but the canonical model class in notebooks is a
  Full model with `ContextualROIEncoder`; Lite is represented as an ablation
  patch. This requires careful extraction into a new explicit class.
- Some notebook cells are shell/Kaggle setup cells and are not valid Python AST.
  They were inspected as execution/environment cells, not importable code.
- The notebooks mix preprocessing, artifact generation, training, evaluation,
  plotting and execution cells. Migration must separate behavior from run
  orchestration.
- Several functions shadow earlier definitions in the same notebook. Later
  definitions likely reflect executed notebook state, but behavior parity tests
  are required before extraction.
- The notebooks include target metrics during training. Later logs must label
  these as monitoring-only metrics.
- Atlas preparation cells include resampling helpers. Phase 3 must implement
  Option A verification only and must not silently perform new registration or
  preprocessing.
- The exact default loss coefficients and confidence threshold values need
  extraction during the relevant loss/adaptation phases from the selected
  training cells.
- Baseline provenance is implementation-level only. Do not claim official or
  external implementation status without author review.

## Proposed Phase 2 Files

Phase 2 should create only package skeleton and configuration scaffolding:

- `pyproject.toml`
- `requirements.txt`
- `environment.yml`
- `.gitignore`
- `src/pada3dacb/__init__.py`
- `src/pada3dacb/config.py`
- `src/pada3dacb/training/reproducibility.py`
- `src/pada3dacb/training/logging.py`
- `configs/data/paths.example.yaml`
- `configs/data/adni.yaml`
- `configs/data/oasis.yaml`
- `configs/model/pada3dacb.yaml`
- `configs/experiments/source_only.yaml`
- `configs/experiments/pada3dacb.yaml`
- `configs/experiments/coral.yaml`
- `configs/experiments/mmd.yaml`
- `configs/experiments/cdan.yaml`
- `configs/experiments/baselines.yaml`
- placeholder executable scripts under `scripts/` that import package entry
  points but do not yet implement model behavior

Phase 2 configuration validation must enforce:

- `model.name` is exactly `PADA-3DACB` for the proposed model.
- `model.contextual_encoder` is present and `false`; `true` must raise a
  configuration error.
- `training.early_stopping` is present and `false`; `true` must raise a
  configuration error.

Production model, preprocessing, derivative verification, artifact computation,
baselines, adaptation methods and evaluation behavior should wait for their
later phases.
