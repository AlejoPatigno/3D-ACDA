# Phase 14 Independent Baseline Verification

Project: `pada-3dacb`
Change: `phase-14-baselines`
Action: `independent-baseline-verification`

## Verdict

**PASS**

The approved first-slice models and registry match the participating notebook behavior. The two original blockers were corrected and independently re-evaluated: FasterSNN now uses the canonical effective default width, and the cumulative apply-progress record contains the required structured Strict TDD evidence.

This verdict covers T1-T4 only. Trainer, orchestration, integration, documentation, final audit, final validation, and native review/receipt work remain pending.

## Runtime fallback

The canonical `agent_plan.yaml` assigns this action to `gemini-cli`. No `gemini-cli` subagent was exposed in the active Pi runtime, so a fresh-context independent verifier performed the action. Repeated resumed verifier runtimes became read-only; the parent persisted the verifier's final PASS result without changing production behavior.

## Verified scope

- Registry order is deterministic: `("aagn", "faster_snn")`.
- Explicit aliases resolve exactly; unknown, blocked, fuzzy, copied-model, and PADA names fail without fallback.
- No production modules exist for the seven `active_not_executed` baselines.
- No `AlzheimerSupervisedMRIModel` or PADA-3DACB copy exists in the baseline registry.
- AAGN copied-state parity is exact (`rtol=0`, `atol=0`) for `logits`, `features`, and `alpha`.
- AAGN ROI resize, normalized masked pooling, ROI ordering, and gating match the participating notebook path.
- FasterSNN copied-state parity is exact (`rtol=0`, `atol=0`) for `logits` and `features`.
- FasterSNN surrogate forward/backward and four Conv3d → InstanceNorm3d → spike blocks match the notebook path.
- Both models return finite raw logits shaped `(B, 3)` and support CPU construction.
- Model imports perform no network access, data-file discovery, or CUDA initialization.
- Model-layer code contains no target adaptation or training behavior.

## Corrected FasterSNN default

The canonical notebook declares `BaselineModelConfig.base_ch=32`, then the final participating factory constructs FasterSNN with:

```text
base_ch=max(16, cfg.base_ch // 2)
```

The effective default is therefore `base_ch=16`. The registry now preserves that effective constructor default while keeping explicit overrides literal.

| Construction | Trainable parameters |
|---|---:|
| FasterSNN canonical default (`base_ch=16`) | 291,603 |
| FasterSNN explicit test override (`base_ch=2`) | 4,701 |
| AAGN tested configuration (`base_ch=2`, `embed_dim=8`) | 15,586 |
| AAGN default with three ROI masks | 3,866,596 |

## Strict TDD correction evidence

The cumulative Engram apply-progress observation `115` contains an explicit TDD Cycle Evidence table.

| Stage | Evidence |
|---|---|
| Safety Net | Registry + FasterSNN suite: exit 0, 31 passed, 1 warning. |
| RED | New canonical-default and explicit-override tests: exit 1, 1 failed and 1 passed; failure proved registry default `32 != 16`. |
| GREEN | FasterSNN registry default changed from 32 to 16 only. |
| TRIANGULATE | Registry + FasterSNN + common: exit 0, 39 passed, 1 warning; parameter counts 291,603 and 4,701 confirmed. |
| REFACTOR | Focused Ruff exit 0; `git diff --check` exit 0. |

## Original verification commands

- `python -m pytest -q tests/test_baseline_common.py tests/test_baseline_registry.py tests/test_baseline_roi_aware_gating.py tests/test_baseline_faster_snn.py --basetemp=.pytest-baseline-verification` — exit 0; `46 passed, 1 warning in 7.62s`.
- Focused Ruff over all baseline model and test files — exit 0; `All checks passed!`.
- Focused `git diff --check` — exit 0; no output.
- Independent parameter/order/spike probe — exit 0.
- Independent alias/rejection probe — exit 0.
- Blocked-file, prohibited-symbol, and `target_adaptation` absence probe — exit 0.

## Limitations and boundaries

- No real ADNI/OASIS cohort training ran.
- No target-adaptation loader was constructed.
- No commit, push, PR, or publication operation occurred.
- This PASS does not resolve the separate native review/receipt authority blocker.
- Phase 14 is not archive-ready; T5 and later actions remain pending.

## Next action

Proceed to `trainer-integration` under its exclusive ownership. Keep all later actions dependency-blocked until their predecessors complete.
