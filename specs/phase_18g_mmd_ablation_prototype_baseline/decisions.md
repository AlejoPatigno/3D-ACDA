# Phase 18G Decisions

**Status:** draft/planning. **Implementation:** BLOCKED pending independent review.

## Recorded authorization

The latest user prompt is explicit implementation authorization for this Phase 18G plan. It applies only after independent review; it does not grant approval, verify any behavior, or permit work outside the planned ownership boundary.

## Decisions

| Decision | Constraint |
|---|---|
| Public framework name | Use `3DACDA`; keep `pada3dacb`, repository/path names, and historical compatibility surfaces. |
| MMD | Keep it primary and protected; `src/pada3dacb/adaptation/mmd.py` is read-only evidence. |
| Mean-pooling identity | Use `mean_pool` as canonical; allow `mean_pooling` only as an alias. |
| Registry contract | Use `list_ablations`, `get_ablation_spec`, `registry_hash`, `alias_target`, `is_unresolved_name`, and `registry_specs`. |
| Resolver contract | Use `AblationResolutionError`, `ResolvedAblationConfig`, `resolve_ablation_config`, and `validate_target_adaptation_batch`. |
| Experiment contract | Use `APPROVED_ABLATIONS`, `AblationExperimentConfig`, `load_ablation_config`, `build_equivalence_reference`, and `planned_run_path`. |
| Mean-pool contract | Use `MeanPoolAggregator`, `MeanPoolPADA3DACB`, `build_mean_pool_model`, and `mean_pool_model_variant_hash`. |
| `no_da` | The framework with `lambda_MMD=0`, distinct from Source-Only. |
| Apply ownership | `src/pada3dacb/ablations/registry.py`, `src/pada3dacb/ablations/resolver.py`, `src/pada3dacb/ablations/schemas.py`, `src/pada3dacb/experiments/ablations.py`, conditional evaluation display/report mapping, and new `tests/phase_18g/test_*.py`. |
| Test evidence | Plan `python -m pytest -q`; Phase 17 and historical tests remain immutable regression evidence. |

## Independent-review gate

Implementation remains blocked until independent review confirms the ownership map, protected-MMD equivalence, canonical/alias semantics, and compatibility assumptions. This planning artifact makes no implementation or verification claim.
