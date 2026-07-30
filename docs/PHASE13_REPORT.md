# Phase 13 Report: Canonical PADA-3DACB Prototype and Pseudo-Label Adaptation

Phase 13 is implemented and documented as a synthetic/focused validation milestone for the canonical proposed PADA-3DACB method. It adds current-batch prototype alignment and confidence-gated pseudo-label adaptation while preserving previous approved methods and avoiding unverified performance claims.

## Review path

1. Start with the SDD files and notebook extraction below.
2. Review the action graph and file ownership to confirm work-unit boundaries.
3. Verify the equations, target-label firewall, checkpoint/resume behavior, and evidence tables.
4. Read discrepancies and limitations before treating the method as ready for real experiments.

## Phase status

| Item | Status |
|---|---|
| Phase | 13 — Canonical PADA-3DACB Prototype and Pseudo-Label Adaptation |
| Implementation | Complete for synthetic/focused scope |
| Documentation | Complete in this report and proposed-method document |
| Final validation | PASS — full required command sequence passed |
| Closure status | COMPLETE for Phase 13 SDD closure; commit/publication receipt remains separate |
| Real ADNI/OASIS training | Not run |
| Performance claims | None |
| Phase 14 | Not started |

## SDD files

| File | Role |
|---|---|
| `specs/phase_13_prototype_pseudo/notebook_extraction.md` | Canonical notebook extraction and active/obsolete definition split |
| `specs/phase_13_prototype_pseudo/requirements.md` | Executable requirements and scenarios |
| `specs/phase_13_prototype_pseudo/design.md` | Tensor contracts, equations, integration boundaries, target-label firewall |
| `specs/phase_13_prototype_pseudo/acceptance.md` | Acceptance criteria and validation commands |
| `specs/phase_13_prototype_pseudo/spec_review.md` | Independent specification approval |
| `specs/phase_13_prototype_pseudo/tasks.md` | Action graph, ownership, workload forecast |

## Action graph and responsible agents

| Action | Responsible agent | Status | Depends on |
|---|---|---|---|
| `canonical-notebook-extraction` | `claude-code` | Complete | Phase 12 closure |
| `independent-specification-review` | `kimi` | Approved | notebook extraction |
| `implement-prototype-adaptation` | `codex` | Complete | spec review |
| `implement-pseudo-label-adaptation` | `codex` | Complete | spec review |
| `implement-combined-method` | `codex` | Complete | prototype + pseudo modules |
| `independent-mathematical-verification` | `gemini-cli` | Complete | combined method |
| `trainer-and-checkpoint-integration` | `opencode` | Complete | mathematical verification |
| `experiment-cli-and-config-integration` | `opencode` | Complete | trainer integration |
| `complete-integration-and-regression-tests` | `codex` | Complete | CLI/config integration |
| `documentation, final-audit, final-validation` | `claude-code` | Complete — final audit PASS and final validation PASS | implementation and regression evidence |

## Files changed per action

| Action | Files |
|---|---|
| notebook extraction | `specs/phase_13_prototype_pseudo/notebook_extraction.md`, `requirements.md`, `design.md`, `tasks.md`, `acceptance.md` |
| specification review | `specs/phase_13_prototype_pseudo/spec_review.md` |
| prototype adaptation | `src/pada3dacb/adaptation/prototype.py`, `tests/test_prototype_loss.py`, `tests/test_prototype_construction.py`, `tests/test_prototype_gradients.py` |
| pseudo-label adaptation | `src/pada3dacb/adaptation/pseudo_label.py`, `tests/test_pseudo_label_selection.py`, `tests/test_pseudo_label_loss.py`, `tests/test_pseudo_label_gradients.py` |
| combined method | `src/pada3dacb/adaptation/prototype_pseudo.py`, `tests/test_prototype_pseudo_total.py` |
| mathematical verification | `tests/test_proposed_method_reference.py`, `tests/test_proposed_method_edge_cases.py` |
| trainer/checkpoint integration | `src/pada3dacb/training/uda_trainer.py`, `src/pada3dacb/training/checkpointing.py`, `src/pada3dacb/training/history.py`, `tests/test_proposed_method_trainer.py`, `tests/test_proposed_method_warmup.py`, `tests/test_proposed_method_loader_cycling.py`, `tests/test_proposed_method_checkpoint_policy.py`, `tests/test_proposed_method_resume.py` |
| CLI/config/fold integration | `src/pada3dacb/experiments/prototype_pseudo.py`, `src/pada3dacb/experiments/runner.py`, `src/pada3dacb/experiments/run_manifest.py`, `src/pada3dacb/experiments/fold_summary.py`, `scripts/train.py`, `configs/experiments/prototype_pseudo.yaml`, `tests/test_proposed_method_config.py`, `tests/test_proposed_method_cli.py`, `tests/test_proposed_method_fold_orchestration.py` |
| integration/regression tests | `tests/phase13_helpers.py`, `tests/test_proposed_method_no_target_labels.py`, `tests/test_proposed_method_predictions.py`, `tests/test_all_previous_methods_regression.py` |
| documentation | `docs/PROPOSED_METHOD_EXPERIMENT.md`, `docs/PHASE13_REPORT.md`, `docs/IMPLEMENTATION_AUDIT.md` |

## Canonical notebook symbols and cells

| Notebook lines | Symbol/cell | Active definition |
|---:|---|---|
| 2001-2131 | `PrototypeLoss` | Current-batch prototype loss over `z` |
| 2036-2059 | `PrototypeLoss._class_prototypes` | Per-class source/target means; absent classes invalid |
| 2074-2104 | `PrototypeLoss.forward` | Target pseudo-labels from `softmax(logits_c_tgt)` and `conf >= tau_p` |
| 2105-2128 | `PrototypeLoss.forward` | Source prototype separation margin penalty |
| 2135-2170 | `PseudoLabelLoss` | Accepted target CE over concept-head logits |
| 2360-2531 | `DomainAdaptiveTotalLoss` | Warm and full objectives |
| 3058-3068 | `DomainAdaptiveTrainConfig` | Training defaults; Phase 13 uses primary executed run overrides |
| 3116-3510 | `DomainAdaptiveMRITrainer` | Warm source-only; full source-target adaptation; monitoring-only target eval |
| 3866-4128 | Primary `train_domain_adaptation_fold` | Builds proposed-method fold path |
| 4360-4377 | Executed `bidirectional_results` call | Primary proposed-method run configuration |
| 4593-5120 | Later ablation helpers | Namespace-later but not canonical Phase 13 proposed method |

## Active definitions

The active Phase 13 implementation follows the primary domain-adaptation path in `training_original.ipynb`, before later ablation helper overrides. The later ablation redefinition remains documented as non-canonical for Phase 13 proposed-method behavior.

## Prototype equations

```text
mu_src[c] = mean(z_src[i] for i where y_src[i] == c)
p_tgt = softmax(logits_c_tgt, dim=-1)
conf, pseudo = max_c p_tgt, argmax_c p_tgt
accepted = conf >= tau_p
mu_tgt[c] = mean(z_tgt[j] for j where accepted[j] and pseudo[j] == c)

L_proto_align = mean_c_in_valid_source_and_target sum_d (mu_src[c,d] - mu_tgt[c,d])^2
L_proto_sep = mean_{i<j valid source classes} relu(proto_margin - ||mu_src[i] - mu_src[j]||_2)^2
L_proto = L_proto_align + lambda_sep * L_proto_sep
```

Absent or unmatched classes contribute zero through invalid masks. No normalization, cache, EMA, memory bank, momentum, or schedule is implemented.

## Pseudo-label equations and confidence rule

```text
p_tgt = softmax(logits_c_tgt, dim=-1)
conf, pseudo = max(p_tgt), argmax(p_tgt)
mask = conf >= tau_p
L_pl = cross_entropy(logits_c_tgt[mask], pseudo[mask])
```

If no target row is accepted, `L_pl` is a scalar zero and the accepted count is zero. The confidence rule is fixed `>= tau_p`; there is no entropy filter, class balancing, threshold schedule, or temperature scaling.

## Gradient and detach behavior

The implementation preserves notebook behavior:

- prototype gradients flow through selected source and target embeddings `z_src` and `z_tgt`;
- pseudo-label CE gradients flow through accepted rows of `logits_c_tgt`;
- argmax labels and confidence masks are non-differentiable selection tensors;
- no stored target diagnosis labels are inputs to adaptation losses;
- no explicit detach is added to the adaptation tensors.

## Warm/full objective and canonical coefficients

Warm stage:

```text
L_warm = warm_lambda_z    * lambda_z    * L_cls_z
       + warm_lambda_c    * lambda_c    * L_cls_c
       + warm_lambda_cbm  * lambda_cbm  * L_concept
       + warm_lambda_anat * lambda_anat * L_anat
       + warm_lambda_cons * lambda_cons * L_cons
```

Full stage:

```text
L_proposed = lambda_z     * L_cls_z
           + lambda_c     * L_cls_c
           + lambda_cons  * L_cons
           + lambda_cbm   * L_concept
           + lambda_anat  * L_anat
           + lambda_proto * L_proto
           + lambda_pl    * L_pl
```

Canonical executed Phase 13 config:

| Field | Value |
|---|---:|
| `lambda_z` | `1.0` |
| `lambda_c` | `1.0` |
| `lambda_cons` | `0.1` |
| `lambda_cbm` | `0.5` |
| `lambda_anat` | `0.2` |
| `lambda_proto` | `1.0` |
| `lambda_pl` | `0.1` |
| `tau_p` | `0.95` |
| `proto_margin` | `1.0` |
| `lambda_sep` | `0.1` |
| `label_smoothing` | `0.1` |
| `warm_lambda_z` | `0.1` |
| `warm_lambda_c` | `1.0` |
| `warm_lambda_cbm` | `1.0` |
| `warm_lambda_anat` | `1.0` |
| `warm_lambda_cons` | `0.0` |
| warm/full epochs | `5` / `50` |
| learning rate / weight decay | `1e-4` / `1e-4` |
| batch size / workers | `16` / `2` |
| seed | `42` |

## Target-label isolation

Target adaptation batches require only `x`. The trainer rejects target adaptation fields that could leak supervision, including `y`, label aliases, diagnosis fields, `c_target`, and `g_bar`.

Target monitoring remains isolated from training. It may produce monitoring metrics and prediction rows, but it cannot influence loss, gradients, optimizer, scheduler, checkpoint selection, epoch count, or hyperparameter selection.

## Checkpoint and resume

Prototype/pseudo-label adaptation is stateless across batches and epochs. Checkpoints record method/config identity, source and target assignment hashes, and loader generator state. Resume validates the stored identity and restores source/target loader generator states. No prototype cache, moving average, pseudo-label cache, or threshold schedule exists.

## Focused test results

| Slice | Result |
|---|---|
| Prototype adaptation | `26 passed` |
| Pseudo-label adaptation | `27 passed` |
| Combined/dependency | `74 passed` |
| Mathematical verification | `81 passed` |
| Trainer focused | `8 passed` |
| Previous trainer regression | `11 passed` |
| Config/CLI focused | `24 passed` |
| Prior CLI regression | `9 passed` |
| Integration/regression focused | `27 passed` |
| Broader Phase 13 regression | `140 passed` |

These are synthetic/focused validation results, not real ADNI/OASIS performance results.

## Prior regressions protected

Phase 13 includes regression coverage for previous approved methods:

- `PADA-3DACB Source-Only`
- `PADA-3DACB + CORAL`
- `PADA-3DACB + MMD`
- `PADA-3DACB + CDAN`

The regression checks cover method identity, dry-run planning, target-label isolation metadata, method-scoped run directories, and previous trainer/CLI behavior reported by earlier action evidence.

## Discrepancies and limitations

- Notebook prose mentions trainer-side prototype accumulators, but active notebook code computes current-batch prototypes inside `PrototypeLoss.forward`; Phase 13 follows active code.
- `_class_prototypes` includes an unused `eps=1e-8` argument; Phase 13 does not invent smoothing from that unused parameter.
- The primary notebook helper returned only the forward direction in the executed primary run; Phase 13 CLI supports both approved transfer directions for reproducible production planning.
- Later ablation helpers are namespace-later but not canonical for Phase 13 proposed-method defaults.
- Real ADNI/OASIS runs were not executed.
- No publication metric, performance comparison, statistical conclusion, or clinical claim is made.
- Real-run paths and compute environment remain external inputs.

## Validation evidence

Documentation validation for this action:

```text
git diff --check -- docs/PROPOSED_METHOD_EXPERIMENT.md docs/PHASE13_REPORT.md docs/IMPLEMENTATION_AUDIT.md
exit 0; no output
```

```text
python -m ruff check docs/PROPOSED_METHOD_EXPERIMENT.md docs/PHASE13_REPORT.md docs/IMPLEMENTATION_AUDIT.md
exit 0; warning: No Python files found under the given path(s); All checks passed!
```

Ruff accepted the command but did not lint Markdown content because this repository's Ruff scope is Python-oriented.

## Final validation and closure evidence

Phase 13 final validation passed after the synthetic fixture/cache path hardening remediation and closure-ledger reconciliation:

| Command | Exit code | Result |
|---|---:|---|
| `python -m pip install -e .` | 0 | Editable install succeeded for `pada3dacb==0.1.0`. |
| `python -c "import pada3dacb; print(pada3dacb.__version__)"` | 0 | Printed `0.1.0`. |
| `python -m pytest -q` | 0 | `453 passed, 3 warnings in 479.80s (0:07:59)`. |
| `python -m ruff check .` | 0 | `All checks passed!`. |
| `git diff --check` | 0 | No output. |

`specs/phase_13_prototype_pseudo/tasks.md` has no remaining unchecked implementation task markers. `specs/phase_13_prototype_pseudo/final_audit.md` is updated to PASS / COMPLETE. This closure does not claim real ADNI/OASIS training, publication metrics, clinical conclusions, commit readiness, or a review lifecycle receipt.

## Engram records

This documentation action updates Engram with:

- merged apply progress at topic `sdd/phase-13-prototype-pseudo/apply-progress`;
- compact documentation completion record at topic `sdd/phase-13-prototype-pseudo/action/documentation`.

## Next phase boundary

No Phase 14 code, tests, configs, or documentation scope was started. A future Phase 14 should begin only after Phase 13 review/approval and should define its own SDD artifacts before implementation.
