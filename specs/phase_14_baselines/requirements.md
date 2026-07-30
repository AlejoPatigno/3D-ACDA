# Phase 14 Baseline Migration Requirements

Phase 14 MUST migrate only the canonical, executable architectural baseline behavior extracted from `notebooks/archive/baselines_original.ipynb` into production-ready specifications and later implementation. Implementation MUST NOT start from obsolete shadows, copied PADA-3DACB models, or invented architecture defaults.

## Scope

In scope for the first implementation slice:

- AAGN / `ROIAwareGatingBaseline`
- FasterSNN / `FasterSNNBaseline`
- Shared helpers required by those approved baselines
- Classification-only dataset, trainer, source-only CV orchestration, and summary contracts needed to run supervised cross-cohort baseline evaluation

Out of scope unless explicitly approved before implementation:

- `CNNDesignForADBaseline`
- `DenseNetCNNBaseline`
- `ViTBaseline`
- `LongFormerBaseline`
- `JointTransformerBaseline`
- `BiFPN3DViTBaseline`
- `DAViT3DBaseline`
- copied `AlzheimerSupervisedMRIModel`
- notebook-only display/CSV convenience beyond specified result persistence

## Requirements

### Requirement: Canonical Notebook Source

The system MUST treat `notebooks/archive/baselines_original.ipynb` as the historical source for Phase 14 baseline behavior, MUST use the executable workflow definitions identified in `specs/phase_14_baselines/notebook_extraction.md`, and MUST use `specs/phase_14_baselines/baseline_inventory.yaml` as the authoritative reconciled implementation-gating inventory.

#### Scenario: last participating definition wins

- GIVEN a symbol has multiple notebook definitions
- WHEN Phase 14 migrates its behavior
- THEN the migrated contract MUST use the final definition that participates in `run_all_requested_baselines`
- AND it MUST NOT use superseded shadows only because they appear earlier in the notebook.

#### Scenario: copied PADA model is not a baseline

- GIVEN `AlzheimerSupervisedMRIModel` exists in the notebook
- WHEN Phase 14 selects baseline models for migration
- THEN the system MUST classify it as `proposed_model_copy`
- AND MUST NOT expose it as a production architectural baseline.

### Requirement: Baseline Migration Gate

The system MUST implement only baselines classified as `active_executed`, unless an `active_not_executed` baseline has explicit approval recorded before implementation.

#### Scenario: first implementation slice

- GIVEN no additional approval exists
- WHEN Phase 14 implementation begins
- THEN only AAGN and FasterSNN MAY be implemented as production baselines
- AND all other discovered baseline model classes MUST remain unimplemented public baselines.

#### Scenario: active but not executed baseline approval

- GIVEN the user approves an `active_not_executed` baseline for a later slice
- WHEN tasks are updated
- THEN the approval MUST name the baseline symbol and alias
- AND the owning action MUST include tests, docs, and validation evidence for that baseline.

### Requirement: Production Invariant Conflicts

The system MUST preserve repository training invariants over conflicting notebook behavior.

#### Scenario: no early stopping

- GIVEN `BaselineTrainConfig` contains `early_stopping_patience`
- WHEN production training runs
- THEN training MUST run the configured fixed number of epochs
- AND early stopping MUST NOT terminate training.

#### Scenario: checkpoint selection

- GIVEN `source_validation` and `target_evaluation` metrics are both available
- WHEN selecting the best checkpoint
- THEN the system MUST select only by `source_validation` macro-F1 (`val_f1_macro`)
- AND MUST NOT use `target_evaluation` metrics or AUC tie-breaks for checkpoint selection.

#### Scenario: target monitoring only

- GIVEN a `target_evaluation` loader is provided
- WHEN epochs are evaluated
- THEN target metrics MAY be logged, exported, and returned
- BUT MUST NOT alter checkpoint selection, learning rate schedule, early termination, gradients, optimizer state, or model state.

#### Scenario: no target adaptation loader

- GIVEN a baseline training run is configured
- WHEN loaders are constructed
- THEN the system MUST construct `source_train`, `source_validation`, and MAY construct `target_evaluation`
- AND MUST NOT construct or consume a `target_adaptation` loader for baselines.

### Requirement: Baseline Configuration Contracts

The system MUST expose deterministic training and model configuration equivalent to the extracted notebook defaults, with documented production overrides.

#### Scenario: training defaults

- GIVEN a baseline train config is constructed without overrides
- WHEN training setup is created
- THEN it MUST default to `n_epochs=25`, `lr=1e-4`, `weight_decay=1e-4`, `batch_size=2`, `num_workers=0`, `use_amp=True`, `grad_clip_norm=1.0`, `scheduler="cosine"`, `label_smoothing=0.0`, `seed=42`
- AND device MUST default to CUDA when available and CPU otherwise.

#### Scenario: model defaults

- GIVEN a baseline model config is constructed without overrides
- WHEN a baseline model is built
- THEN it MUST default to `input_shape=(128,128,128)`, `n_classes=3`, `base_ch=32`, `embed_dim=128`, `n_heads=4`, `n_layers=2`, `dropout=0.1`, `patch_size=(16,16,16)`, `n_slice_tokens=24`, and `longformer_window=32`.

#### Scenario: inferred input shape

- GIVEN a classification dataset is available for a fold
- WHEN a model is built for that fold
- THEN `input_shape` MUST be inferred from the first dataset sample
- AND MUST override the default model config input shape.

### Requirement: Classification Dataset Contract

The system MUST provide a classification-only MRI dataset that does not depend on domain-adaptation concept targets.

#### Scenario: inventory labels

- GIVEN an inventory DataFrame with `x_path` and either `label` or `Label`
- WHEN a sample is loaded
- THEN the dataset MUST map labels using `CN=0`, `MCI=1`, `AD=2` unless an explicit label map is supplied
- AND each sample MUST include `x`, `y`, `subject_id`, and `label_name`.

#### Scenario: tensor loading

- GIVEN a serialized MRI tensor object
- WHEN the dataset loads it
- THEN it MUST accept tensors directly or mappings with keys `x`, `image`, `mri`, `tensor`, or `volume`
- AND it MUST produce a float32 contiguous tensor shaped `[1,D,H,W]`.

### Requirement: Model Forward Contract

Every production baseline model MUST accept `[B,1,D,H,W]` MRI tensors and MUST return a mapping containing `logits` shaped `[B,n_classes]`.

#### Scenario: AAGN forward

- GIVEN an AAGN model with ROI masks
- WHEN it receives a valid MRI batch
- THEN it MUST return `logits`, `features`, and `alpha`
- AND `alpha` MUST be batch-aligned ROI weights.

#### Scenario: FasterSNN forward

- GIVEN a FasterSNN model
- WHEN it receives a valid MRI batch
- THEN it MUST return `logits` and `features`
- AND it MUST use the notebook's surrogate spike activation contract rather than an external SNN dependency.

### Requirement: ROI Input Contract

The system MUST require atlas-derived ROI masks only for ROI-aware baselines.

#### Scenario: AAGN without ROI masks

- GIVEN the requested baseline is AAGN
- WHEN ROI masks cannot be resolved
- THEN model construction MUST fail explicitly
- AND MUST NOT fall back to an unmasked classifier.

#### Scenario: non-ROI baseline

- GIVEN the requested baseline is FasterSNN
- WHEN model construction runs
- THEN ROI masks MUST NOT be required.

### Requirement: Optimization and Loss Contract

The system MUST train baselines with classification-only loss and the notebook optimizer behavior.

#### Scenario: loss and optimizer setup

- GIVEN a model and train config
- WHEN a trainer is initialized
- THEN it MUST use cross entropy with configured label smoothing
- AND AdamW with configured learning rate and weight decay.

#### Scenario: AMP and gradient clipping

- GIVEN a training batch
- WHEN backward and optimizer update are performed
- THEN AMP MUST be enabled only on CUDA when configured
- AND gradients MUST be clipped with `grad_clip_norm` before optimizer step.

#### Scenario: class weights not invented

- GIVEN class imbalance exists in a cohort
- WHEN the classification loss is constructed
- THEN class weights MUST NOT be introduced unless a later explicit scientific decision approves them.

### Requirement: Source-Only Cross-Cohort CV Orchestration Contract

The system MUST reproduce the approved supervised cross-cohort evaluation shape without running real ADNI/OASIS training during implementation validation. For the first implementation slice, all baseline training MUST be source-only: train only on `source_train`, checkpoint only on `source_validation` macro-F1, and use `target_evaluation` only for monitoring/export.

#### Scenario: fold construction

- GIVEN labels for the explicit source cohort
- WHEN folds are created
- THEN the system MUST use `StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)` only on source samples
- AND MUST reject `n_splits` larger than the smallest source class count.

#### Scenario: source-only direction

- GIVEN a cross-cohort direction such as OASIS -> ADNI
- WHEN baseline CV runs
- THEN OASIS MUST provide `source_train` and `source_validation`
- AND ADNI MUST provide `target_evaluation` only.

#### Scenario: target cohort is not trainable in first slice

- GIVEN a request would train with the target side as the train cohort
- WHEN first-slice Phase 14 orchestration validates the request
- THEN the request MUST fail or be deferred behind explicit later scientific approval
- AND target labels MUST NOT influence training, validation checkpoint selection, scheduler policy, early termination, gradients, optimizer state, or model state.

#### Scenario: result payload

- GIVEN a fold completes
- WHEN the result is returned or saved
- THEN it MUST include baseline name, source cohort, target cohort, fold index, `source_train`/`source_validation`/`target_evaluation` counts, train config, model config, best score, final source-validation metrics, final target-evaluation metrics, and history.

### Requirement: Parameter Count Strategy

The system MUST report parameter counts for each constructed baseline without using parameter count as a checkpoint criterion.

#### Scenario: model metadata

- GIVEN a baseline model is constructed
- WHEN metadata is produced
- THEN total trainable parameters MUST be computable from the instantiated model
- AND the count MAY be included in reports and logs
- BUT MUST NOT affect training, checkpoint selection, or acceptance thresholds.

### Requirement: Optional Dependencies

The system MUST avoid optional external architecture dependencies for migrated notebook baselines.

#### Scenario: FasterSNN dependency

- GIVEN FasterSNN is implemented
- WHEN imports are resolved
- THEN the model MUST rely on local PyTorch modules and the notebook surrogate spike function
- AND MUST NOT require an external SNN package.

#### Scenario: DA-ViT/BiFPN later approval

- GIVEN DA-ViT or BiFPN3DViT is later approved
- WHEN implementation begins
- THEN the implementation MUST follow the notebook approximations
- AND MUST NOT download or import third-party architecture code unless separately approved.

### Requirement: File Ownership and Phase Boundaries

The system MUST keep Phase 14 planning, implementation, validation, and reporting actions isolated by file ownership.

#### Scenario: this action remains specification-only

- GIVEN the canonical-baseline-extraction or specification-remediation action runs
- WHEN it completes
- THEN only `specs/phase_14_baselines/baseline_inventory.yaml`, `notebook_extraction.md`, `requirements.md`, `design.md`, `tasks.md`, and `acceptance.md` MAY be modified
- AND production code and tests MUST remain untouched.

#### Scenario: no Phase 15 artifacts

- GIVEN Phase 14 planning is active
- WHEN tasks are generated
- THEN no Phase 15 files, docs, or tasks MUST be created.
