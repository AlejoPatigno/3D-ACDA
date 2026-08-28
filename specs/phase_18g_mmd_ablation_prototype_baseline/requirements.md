# Phase 18G Requirements

**Status:** draft/planning. **Implementation:** BLOCKED pending independent review.  
**Authorization recorded:** the latest user prompt explicitly authorizes implementation after the independent-review gate; authorization does not bypass that gate.

## Requirements

1. The public display name MUST be `3DACDA`; the `pada3dacb` namespace, repository/path names, historical IDs, outputs/hashes, Source-Only, CORAL, CDAN, and prototype/pseudo surfaces MUST remain compatible.
2. MMD MUST remain the protected primary adaptation mechanism. `src/pada3dacb/adaptation/mmd.py` is read-only evidence; equations, estimator, bandwidths, embedding policy, and trainer behavior MUST NOT change.
3. The canonical mean-pooling registry key MUST be `mean_pool`. `mean_pooling` MAY resolve only as an alias, never as a second canonical key.
4. The registry contract MUST use only the confirmed APIs: `list_ablations`, `get_ablation_spec`, `registry_hash`, `alias_target`, `is_unresolved_name`, and `registry_specs`.
5. Resolution MUST use `AblationResolutionError`, `ResolvedAblationConfig`, `resolve_ablation_config`, and `validate_target_adaptation_batch` for invalid names, aliases, resolved configurations, and adaptation-batch validation.
6. Experiment planning MUST use `APPROVED_ABLATIONS`, `AblationExperimentConfig`, `load_ablation_config`, `build_equivalence_reference`, and `planned_run_path`.
7. Mean-pool planning MUST use `MeanPoolAggregator`, `MeanPoolPADA3DACB`, `build_mean_pool_model`, and `mean_pool_model_variant_hash`.
8. `no_da` MUST mean the existing framework with `lambda_MMD=0`, retain a distinct identity from Source-Only, and not alias Source-Only.
9. Apply ownership is limited to `src/pada3dacb/ablations/registry.py`, `src/pada3dacb/ablations/resolver.py`, `src/pada3dacb/ablations/schemas.py`, and `src/pada3dacb/experiments/ablations.py`; evaluation display/report mapping MAY change only if confirmed during apply. Existing historical tests, Phase 17 tests, and protected MMD are read-only; Phase 17 tests are immutable regression evidence. New focused tests, if approved, belong only in `tests/phase_18g/test_*.py`.

## Scenarios

### Scenario: canonical mean-pool resolution
- GIVEN `mean_pool` and `mean_pooling` are submitted
- WHEN the registry and resolver are queried
- THEN `mean_pool` is canonical and `mean_pooling` resolves only to that key.

### Scenario: no-da identity
- GIVEN `no_da` is resolved
- WHEN its MMD weight is set to zero
- THEN it remains the framework configuration and is distinct from Source-Only.

### Scenario: protected evidence
- GIVEN apply has not passed independent review
- WHEN implementation is requested
- THEN no production or test file is changed and planning remains blocked.

## Validation plan

Planned command: `python -m pytest -q`. Phase 17 tests are immutable regression evidence only. This artifact reports no implementation or verification result.
