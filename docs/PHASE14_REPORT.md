# Phase 14 Report — Canonical Architectural Baselines

Status: **FINAL AUDIT AND VALIDATION PASS — NATIVE RECEIPT PENDING**

Phase 14 migrates the canonical executed AAGN and FasterSNN architectures into a strict source-only cross-cohort workflow. No external architecture was added, no real cohort training ran, and no Phase 15 capability was started.

## 1. SDD files

`specs/phase_14_baselines/` contains requirements, design, tasks, acceptance, decisions, notebook extraction, authoritative inventory, agent plan, approved spec review, and independent baseline verification.

## 2. Action graph

| Action | Canonical owner | Status |
|---|---|---|
| Phase 13 closure and baseline audit | OpenCode | Complete |
| Canonical notebook extraction | Claude Code | Complete through Pi fallback |
| Independent specification review | Kimi | APPROVED through fresh Pi fallback |
| Shared baseline framework | Codex | Complete |
| AAGN implementation | Codex | Complete |
| FasterSNN implementation | Codex | Complete |
| Independent model verification | Gemini CLI | PASS through fresh Pi fallback |
| Dataset and trainer | OpenCode | Complete |
| Experiment/config/CLI | OpenCode | Complete |
| Integration tests | Codex | Complete through parent fallback after subagent tooling incident |
| Documentation | Claude Code | Complete through parent fallback after subagent tooling incident |
| Final audit | Kimi | PASS through fresh Pi fallback |
| Final validation | OpenCode | PASS |

Writes remained serial and file ownership has no declared collision. Delivery uses feature-branch-chain with 400-line work-unit boundaries.

## 3–5. Inventory and notebook traceability

| Class | Public name | Classification | Production |
|---|---|---|---|
| `ROIAwareGatingBaseline` | AAGN | `active_executed` | Migrated |
| `FasterSNNBaseline` | FasterSNN | `active_executed` | Migrated |
| `CNNDesignForADBaseline` | CNN design for AD | `active_not_executed` | Blocked |
| `DenseNetCNNBaseline` | DenseNet-CNN | `active_not_executed` | Blocked |
| `ViTBaseline` | ViT | `active_not_executed` | Blocked |
| `LongFormerBaseline` | LongFormer | `active_not_executed` | Blocked |
| `JointTransformerBaseline` | Joint-Transformer | `active_not_executed` | Blocked |
| `BiFPN3DViTBaseline` | BiFPN3DViT | `active_not_executed` | Blocked |
| `DAViT3DBaseline` | DA-ViT | `active_not_executed` | Blocked |
| `AlzheimerSupervisedMRIModel` | copied proposed model | `proposed_model_copy` | Prohibited |

Shared CNN, transformer, ROI, spike, BiFPN, and deformable blocks are `helper_only`; earlier factories/trainers/runners are `obsolete`; display/CSV conveniences are `posthoc_analysis_only`.

Canonical source: `notebooks/archive/baselines_original.ipynb`, participating cell 17. Example cell 18 executes AAGN and FasterSNN.

## 6–9. Files, registry, constructors, and tensor contracts

Production files created:

- `src/pada3dacb/models/baselines/{__init__,common,registry,roi_aware_gating,faster_snn}.py`
- `src/pada3dacb/data/baseline_dataset.py`
- `src/pada3dacb/training/baseline_trainer.py`
- `src/pada3dacb/experiments/baselines.py`
- `configs/baselines/{aagn,faster_snn}.yaml`

Stable ids are `aagn` and `faster_snn`. Registry APIs are `list_baselines`, `get_baseline_spec`, and `build_baseline`.

AAGN resolves `n_classes=3`, `base_ch=32`, `embed_dim=128`, `dropout=0.1`, and requires ordered ROI masks. FasterSNN resolves `n_classes=3`, effective `base_ch=16`, `dropout=0.1`.

Both consume finite single-channel MRI `[B,1,D,H,W]` and return raw logits `[B,3]`. AAGN additionally returns `features` and `alpha`; FasterSNN returns `features`.

## 10–11. Parameter counts and notebook parity

| Model/configuration | Trainable parameters |
|---|---:|
| AAGN default, three ROI masks | 3,866,596 |
| AAGN focused parity config | 15,586 |
| FasterSNN canonical default | 291,603 |
| FasterSNN focused parity config | 4,701 |

Copied-weight reference tests use identical synthetic tensors. AAGN `logits`, `features`, and `alpha` match exactly (`rtol=0`, `atol=0`). FasterSNN `logits` and `features` match exactly, including surrogate gradient and four-block ordering.

Independent verification initially blocked FasterSNN's default width. Strict TDD corrected registry width 32 to canonical effective 16; 39 focused tests then passed and verification became PASS.

## 12–16. Training, isolation, checkpoints, resume, predictions

The trainer preserves notebook classification behavior where compatible: cross entropy with label smoothing, AdamW, explicit learning rate/weight decay, cosine scheduler, CUDA-only AMP, gradient clipping, and fixed epochs.

Production deliberately deviates from notebook patience behavior: early stopping is disabled by invariant. Best state changes only on strict source-validation macro-F1 improvement. Macro-AUC is reported when computable but never breaks checkpoint ties.

Data flow is:

```text
source_train -> loss/gradients/optimizer/scheduler
source_validation -> best-source-F1 checkpoint selection
target_evaluation -> monitoring and predictions only
```

No `target_adaptation` loader is constructed or passed. Trainer tests prove target monitoring cannot change trained parameters or best-source score. Atomic `last.pt` contains optimizer, scheduler, scaler, history, best state, configuration, epoch, and RNG state. Interrupted/resumed synthetic training matches uninterrupted training.

Predictions use the established subject-level identity and three-probability schema for source validation and target monitoring. No confusion matrices or statistical summaries are generated.

## 17–18. Fold and direction orchestration

Source folds use `StratifiedKFold(n_splits, shuffle=True, random_state=42)`. Fold runtime seed is `seed + fold`. Source and target assignment hashes enter each experiment hash. The CLI supports one/all approved baselines, one/all configured folds, explicit config seeds, both directions, dry-run, validate-only, interruption, resume, and completed reuse. Execution is sequential.

## 19. Computational limitations

Real 3D memory consumption was not measured. Validation uses small structurally faithful CPU tensors. Real runs require explicit artifact paths, ROI masks for AAGN, and a feasibility check. No architecture width/depth is silently reduced for real execution.

## 20. Focused tests

Recorded focused evidence includes:

- shared registry/common: 24 passed;
- AAGN/reference: 27 passed;
- FasterSNN/reference: 37 passed;
- corrected FasterSNN registry/default: 39 passed;
- dataset: 17 passed;
- trainer: 6 passed; combined dataset/trainer: 23 passed;
- CV/CLI/config: 18 passed, then helper/config override suite 14 passed;
- integration: 6 passed;
- Phase 14 plus representative previous-method regressions: **111 passed, 5 warnings**.

Warnings are synthetic single-class AUC and local `.pytest_cache` permission warnings; they do not change test outcomes.

## 21–24. Final commands, regressions, and CLI evidence

Final validation passed: editable installation exit 0, version `0.1.0`, full pytest `549 passed, 7 warnings in 238.57s`, Ruff exit 0, and `git diff --check` exit 0.

Representative Source-Only, CORAL, MMD, CDAN, and prototype_pseudo regressions passed inside the full suite.

Final synthetic lifecycle evidence passed `56 tests` with five non-blocking warnings. It covers actual validate-only for both approved models, all five folds and both directions in dry-run, interruption/resume, strict completed reuse, prediction schema, prior CLI boundaries, and explicit no-target-adaptation metadata.

## 25. Engram records

Compact records exist for Phase 14 audit, extraction, spec remediation/review, agent plan, each model action, independent verification, dataset/trainer, orchestration, delivery strategy, and cumulative apply progress.

## 26. Discrepancies and blocked baselines

- D-14-001: repository `lambda_proto=1.0` versus manuscript `0.2`; Phase 13 remains unchanged.
- D-14-002: repository source macro-F1-only checkpoint selection versus manuscript macro-AUC tie-break wording; repository invariant preserved.
- D-14-003: native review/receipt inventory unavailable; must be resolved before commit/push.
- D-14-004: notebook may truncate channels; production rejects non-single-channel MRI.
- Seven active-not-executed baselines remain blocked and unimplemented.

## 27. Proposed Phase 15 scope

A future explicitly authorized phase may add predictive evaluation artifacts such as confusion matrices and statistical comparisons. Phase 14 does not implement them.

## Explicit confirmations

- No external baseline was added.
- No target-adaptation batch entered baseline training.
- No target metric selected a checkpoint or hyperparameter.
- No early stopping was introduced.
- No concept normalizer was refitted.
- PADA-3DACB was not duplicated as a baseline.
- Source-Only, CORAL, MMD, CDAN, and prototype_pseudo were not scientifically changed.
- Confusion matrices were not implemented.
- Concept evaluation was not implemented.
- Phase 15 was not started.
