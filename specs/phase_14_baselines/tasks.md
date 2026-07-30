# Phase 14 Baseline Migration Tasks

Implementation remains gated to `ROIAwareGatingBaseline` (AAGN) and `FasterSNNBaseline`. Execution is serial, single-writer, and delivered as a feature-branch chain whose child PRs remain at or below 400 authored changed lines.

## Dependency graph

```text
T0 approved specification
  -> T1 shared registry/framework
  -> T2 ROI-aware gating
  -> T3 FasterSNN
  -> T4 independent model verification
  -> T5 dataset/trainer integration
  -> T6 experiment/config/CLI integration
  -> T7 integration evidence and documentation
  -> T8 final audit/validation
```

Exactly one action and responsible agent owns every task and path; no production action may start concurrently with another production writer.

## Tasks

### T0 — Approved specification

Owner: `independent-specification-review` (`kimi`)  
Status: completed

- [x] Confirm only AAGN and FasterSNN are approved.
- [x] Confirm source-only training, source-validation checkpointing, and monitoring-only target evaluation.

### T1 — Shared baseline registry/framework

Owner: `implement-shared-baseline-framework` (`codex`)  
Depends on: T0

Files:

- `src/pada3dacb/models/baselines/__init__.py`
- `src/pada3dacb/models/baselines/common.py`
- `src/pada3dacb/models/baselines/registry.py`
- `tests/test_baseline_registry.py`
- `tests/test_baseline_common.py`

- [x] Implement `list_baselines() -> tuple[str, ...]` with deterministic canonical ordering.
- [x] Implement `get_baseline_spec(name: str) -> BaselineSpec` with explicit aliases only.
- [x] Implement `build_baseline(name: str, config: Mapping[str, Any]) -> nn.Module`.
- [x] Reject unknown, blocked, misspelled, and fuzzy names without fallback.
- [x] Validate the three-logit output contract.
- [x] Include the selected canonical baseline and all resolved constructor values in reproducibility hashes.
- [x] Test aliases, ordering, blocked names, three-logit validation, and parameter metadata.

### T2 — ROI-aware gating baseline

Owner: `implement-baseline-group-a` (`codex`)  
Depends on: T1

Files:

- `src/pada3dacb/models/baselines/roi_aware_gating.py`
- `tests/test_baseline_roi_aware_gating.py`

- [x] Implement `ROIAwareGatingBaseline` with required ROI masks, resizing, normalized masked pooling, gates, and `logits`/`features`/`alpha` outputs.
- [x] Test missing masks, shapes, and exactly three logits.

### T3 — FasterSNN baseline

Owner: `implement-baseline-group-b` (`codex`)  
Depends on: T2

Files:

- `src/pada3dacb/models/baselines/faster_snn.py`
- `tests/test_baseline_faster_snn.py`

- [x] Implement the local surrogate spike and four stride-2 3D convolution blocks.
- [x] Test spike behavior, output keys, shapes, and exactly three logits.

### T4 — Independent model verification

Owner: `independent-baseline-verification` (`gemini-cli`)  
Depends on: T3

File: `specs/phase_14_baselines/baseline_verification.md`

- [x] Verify registry strictness, approved scope, model contracts, and absence of blocked model files.

### T5 — Classification dataset and trainer

Owner: `trainer-integration` (`opencode`)  
Depends on: T4

Files:

- `src/pada3dacb/data/baseline_dataset.py`
- `src/pada3dacb/training/baseline_trainer.py`
- `tests/test_baseline_dataset.py`
- `tests/test_baseline_trainer.py`

- [x] Implement classification-only data loading and explicit multi-channel behavior.
- [x] Implement fixed-epoch AdamW training without functional early stopping.
- [x] Select checkpoints only on strict source-validation macro-F1 improvement.
- [x] Prove target-evaluation metrics cannot alter state, scheduling, checkpointing, or duration.

### T6 — Experiment, configuration, and CLI integration

Owner: `experiment-config-cli-integration` (`opencode`)  
Depends on: T5

Files:

- `src/pada3dacb/experiments/baselines.py`
- `src/pada3dacb/experiments/__init__.py`
- `scripts/train.py`
- `configs/experiments/baselines.yaml`
- `configs/baselines/aagn.yaml`
- `configs/baselines/faster_snn.yaml`
- `tests/phase14_helpers.py`
- `tests/test_baseline_cv.py`
- `tests/test_baseline_cli.py`

- [x] Integrate source-only stratified CV, fold seeds, summaries, and optional persistence.
- [x] Update existing experiment configuration and baseline-specific configs; do not create `configs/baselines/phase14_baselines.yaml`.
- [x] Integrate explicit approved-baseline dispatch into `scripts/train.py`.
- [x] Use synthetic flat-layout tests and never run real ADNI/OASIS training.

### T7 — Integration evidence and documentation

Owner sequence: `complete-baseline-integration-tests` (`codex`), then `documentation` (`claude-code`)  
Depends on: T6

Integration-test owner files:

- `tests/test_baseline_smoke.py`
- `tests/test_baseline_source_only.py`

Documentation owner files:

- `docs/BASELINES.md`
- `docs/PHASE14_REPORT.md`
- `docs/IMPLEMENTATION_AUDIT.md`

- [x] Prove synthetic end-to-end and source-only behavior.
- [x] Document supported baselines, scientific caveats, omitted blocked files, exact commands, and evidence.

### T8 — Final audit and validation

Owners in order: `final-audit` (`kimi`), then `final-validation` (`opencode`)  
Depends on: T7

Files:

- `specs/phase_14_baselines/final_audit.md`
- `specs/phase_14_baselines/final_validation.md`
- `specs/phase_14_baselines/archive_report.md`

- [x] Run acceptance commands and confirm no Phase 15 artifacts, copied prohibited model, blocked baseline production files, or ownership collisions.
- [ ] Resolve review/receipt status before archive.

## Explicitly omitted production files

Production files requested for CNN_design_for_AD, DenseNet-CNN, ViT, LongFormer, Joint-Transformer, DA-ViT, and BiFPN3DViT are intentionally absent. The inventory classifies these baselines as `active_not_executed`, and no explicit implementation approval was given. No action owns or may create those files.

## Feature-branch-chain work units

The tracker PR is draft/no-merge. Child PR 1 targets the tracker branch; each later child targets the immediate prior child branch. Every child MUST stay within 400 authored changed lines, include its tests/docs, focused command evidence, runtime-harness evidence or explicit N/A, and a precise rollback boundary.

1. Shared registry/framework (T1).
2. ROI-aware gating (T2).
3. FasterSNN plus independent model verification (T3–T4).
4. Classification dataset/trainer (T5).
5. Experiment/config/CLI integration (T6).
6. Integration evidence, docs, and final validation (T7–T8).

## Review Workload Forecast

| Forecast item | Result |
|---|---|
| Chained PRs recommended | Yes |
| 400-line budget risk | High overall; hard limit per child |
| Estimated authored changed lines | >400 across the full chain |
| Execution | Serial single writer |
| Ownership collisions | Zero required |
| Decision needed before apply | No; feature-branch-chain is selected |
| Approved production baselines | AAGN and FasterSNN only |

## Guardrails

- Do not implement blocked `active_not_executed` baselines or create their production files.
- Do not migrate `AlzheimerSupervisedMRIModel`, obsolete definitions, or external architecture packages.
- Do not construct or consume `target_adaptation`.
- Do not run real ADNI/OASIS training in tests.
- Do not create Phase 15 artifacts.
- Do not commit or push until the parent workflow resolves review/receipt status.
