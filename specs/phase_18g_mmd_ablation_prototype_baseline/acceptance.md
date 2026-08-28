# Phase 18G Acceptance

**Status:** draft/planning. **Implementation:** BLOCKED pending independent review.  
**Authorization recorded:** the latest user prompt explicitly authorizes implementation after independent review; it is not review approval.

## Acceptance criteria

- [ ] Independent review approves apply ownership and protected-MMD equivalence evidence.
- [ ] `mean_pool` is the sole canonical mean-pooling key; `mean_pooling` is alias-only.
- [ ] Registry behavior is covered through `list_ablations`, `get_ablation_spec`, `registry_hash`, `alias_target`, `is_unresolved_name`, and `registry_specs`.
- [ ] Resolution behavior covers `AblationResolutionError`, `ResolvedAblationConfig`, `resolve_ablation_config`, and `validate_target_adaptation_batch`.
- [ ] Experiment identity covers `APPROVED_ABLATIONS`, `AblationExperimentConfig`, `load_ablation_config`, `build_equivalence_reference`, and `planned_run_path`.
- [ ] Mean-pool identity covers `MeanPoolAggregator`, `MeanPoolPADA3DACB`, `build_mean_pool_model`, and `mean_pool_model_variant_hash`.
- [ ] `no_da` is the framework with `lambda_MMD=0` and is demonstrably distinct from Source-Only.
- [ ] Apply changes only `src/pada3dacb/ablations/registry.py`, `src/pada3dacb/ablations/resolver.py`, `src/pada3dacb/ablations/schemas.py`, `src/pada3dacb/experiments/ablations.py`, confirmed evaluation display/report mapping if needed, and new `tests/phase_18g/test_*.py`.
- [ ] `src/pada3dacb/adaptation/mmd.py`, Phase 17 tests, and other historical tests remain immutable regression evidence.
- [ ] `python -m pytest -q` is planned as the test command; this document asserts no test execution or verification.

## Rejection criteria

Reject a candidate that treats `mean_pooling` as canonical, aliases `no_da` to Source-Only, changes protected MMD or historical tests, uses unconfirmed APIs/symbols, or changes an unowned file without review approval.
