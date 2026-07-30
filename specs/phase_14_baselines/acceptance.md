# Phase 14 Baseline Migration Acceptance Criteria

Acceptance is split into specification acceptance, implementation acceptance, and final evidence. This action satisfies only the specification-production step; implementation remains pending.

## Specification acceptance

- [ ] `specs/phase_14_baselines/notebook_extraction.md` exists and records direct inspection of `notebooks/archive/baselines_original.ipynb`.
- [ ] The baseline symbol list is verified complete for the final participating baseline workflow.
- [ ] `baseline_inventory.yaml` is the authoritative reconciled implementation-gating inventory.
- [ ] Every discovered baseline-adjacent symbol is classified as `active_executed`, `active_not_executed`, `obsolete`, `helper_only`, `proposed_model_copy`, or `posthoc_analysis_only`.
- [ ] `requirements.md` uses testable MUST/SHOULD/MAY language and blocks invented scientific baselines.
- [ ] `design.md` defines file ownership and action graph without collisions.
- [ ] `tasks.md` contains a Review Workload Forecast.
- [ ] This specification/remediation action does not modify production code, tests, or Phase 15 artifacts.

## Implementation acceptance

### Baseline gate

- [ ] Only AAGN and FasterSNN are implemented in the first production slice unless a later approval explicitly names another baseline.
- [ ] The requested production files for CNN_design_for_AD, DenseNet-CNN, ViT, LongFormer, Joint-Transformer, DA-ViT, and BiFPN3DViT remain absent because the inventory classifies them as `active_not_executed` and no explicit implementation approval was given.
- [ ] Blocked `active_not_executed` baseline names fail explicitly by default.
- [ ] No production baseline subclasses or copies `AlzheimerSupervisedMRIModel`.

### Registry and model behavior

- [ ] `list_baselines() -> tuple[str, ...]` returns approved canonical names in deterministic order.
- [ ] `get_baseline_spec(name: str) -> BaselineSpec` accepts canonical names and explicit aliases only.
- [ ] `build_baseline(name: str, config: Mapping[str, Any]) -> nn.Module` rejects unknown, blocked, fuzzy, or fallback names and validates exactly three logits.
- [ ] Reproducibility hashes include the selected canonical baseline and all resolved constructor values.
- [ ] AAGN accepts `[B,1,D,H,W]`, requires ROI masks, returns `logits`, `features`, and `alpha`.
- [ ] FasterSNN accepts `[B,1,D,H,W]`, uses local surrogate spike activation, and returns `logits` and `features`.
- [ ] All approved model outputs include `logits` shaped `[B,3]` under the default class config.
- [ ] Parameter counts are computed from instantiated model parameters and are not used for checkpointing.

### Dataset behavior

- [ ] Classification dataset accepts `x_path` plus `label` or `Label`.
- [ ] Default labels map to `CN=0`, `MCI=1`, `AD=2`.
- [ ] Tensor loading supports direct tensors and mapping keys `x`, `image`, `mri`, `tensor`, `volume`.
- [ ] Samples return `x`, `y`, `subject_id`, and `label_name`.
- [ ] Multi-channel tensor behavior is explicitly tested and documented.

### Training behavior

- [ ] Trainer uses cross entropy with label smoothing.
- [ ] Trainer uses AdamW with configured learning rate and weight decay.
- [ ] Cosine scheduler maps to fixed configured epoch count.
- [ ] AMP is enabled only when CUDA and config allow it.
- [ ] Gradient clipping is applied before optimizer step.
- [ ] Training runs exactly `n_epochs`; early stopping does not terminate training.
- [ ] Best checkpoint is selected only by strict improvement in `source_validation` `val_f1_macro`.
- [ ] `target_evaluation` metrics are monitoring/export only and cannot select checkpoints, change scheduler policy, trigger early termination, or alter model state.
- [ ] Class weights are not introduced without an explicit scientific decision.

### Orchestration behavior

- [ ] Stratified CV uses `shuffle=True` and `random_state=42` on source samples only.
- [ ] `n_splits` larger than the smallest source class count fails explicitly.
- [ ] Fold seed is `seed + fold_idx`.
- [ ] First-slice orchestration trains only on `source_train` and checkpoints only on `source_validation`.
- [ ] Target-side cohort data is loaded only as `target_evaluation` for monitoring/export.
- [ ] No baseline orchestration constructs or consumes `target_adaptation`.
- [ ] Requests that train on the target side of a configured direction fail or are deferred behind explicit later scientific approval.
- [ ] Fold payload includes baseline name, source cohort, target cohort, fold index, `source_train`/`source_validation`/`target_evaluation` counts, train/model configs, best score, final source-validation metrics, final target-evaluation metrics, and history.
- [ ] Summaries include per-fold rows and grouped mean/std for source-validation and target-evaluation metrics.

## Final validation commands

Run these after implementation, from repository root. Commands use synthetic/unit/smoke tests only; they MUST NOT run real ADNI/OASIS training.

```bash
python -m pytest -q tests/test_baseline_registry.py tests/test_baseline_common.py tests/test_baseline_roi_aware_gating.py tests/test_baseline_faster_snn.py tests/test_baseline_dataset.py tests/test_baseline_trainer.py tests/test_baseline_cv.py tests/test_baseline_cli.py tests/test_baseline_smoke.py tests/test_baseline_source_only.py
python -m pytest -q
python -m ruff check .
git diff --check
```

Specification-only validation for this action:

```bash
git diff --check -- specs/phase_14_baselines/design.md specs/phase_14_baselines/tasks.md specs/phase_14_baselines/acceptance.md specs/phase_14_baselines/agent_plan.yaml
```

## Required evidence

Final Phase 14 evidence MUST include:

- exact command text;
- exact exit code;
- exact stdout/stderr summary;
- changed file list;
- confirmation that no real ADNI/OASIS training ran;
- confirmation that no Phase 15 artifacts were created;
- confirmation that no copied `AlzheimerSupervisedMRIModel` production baseline exists;
- review/receipt status or explicit parent-level blocker if native review remains unavailable.

## Blockers to archive

Phase 14 MUST NOT be archived until:

- all accepted tasks pass final validation;
- review/receipt status is resolved or carried as an explicit non-archive blocker by the parent workflow;
- discrepancies D-14-001 and D-14-002 remain documented or are explicitly resolved;
- production docs and report match implemented behavior.
