# Phase 18G Design

**Status:** draft/planning. **Implementation:** BLOCKED pending independent review.  
**Authorization recorded:** the latest user prompt authorizes implementation only after independent review.

## Technical approach

Plan a registry-backed, isolated ablation surface around the protected MMD baseline. The canonical identifier is `mean_pool`; `mean_pooling` is alias-only. `no_da` is the existing framework with `lambda_MMD=0`, not Source-Only. No implementation is performed by this plan.

## Architecture decisions

| Decision | Choice | Rationale |
|---|---|---|
| Canonical key | `mean_pool` | Prevent duplicate registry identities; preserve `mean_pooling` solely as an alias. |
| Registry boundary | `list_ablations`, `get_ablation_spec`, `registry_hash`, `alias_target`, `is_unresolved_name`, `registry_specs` | Defines one inspectable source of keys, aliases, and provenance. |
| Resolver boundary | `AblationResolutionError`, `ResolvedAblationConfig`, `resolve_ablation_config`, `validate_target_adaptation_batch` | Keeps invalid-name and adaptation validation behavior explicit. |
| Experiment boundary | `APPROVED_ABLATIONS`, `AblationExperimentConfig`, `load_ablation_config`, `build_equivalence_reference`, `planned_run_path` | Preserves approved-run identity and equivalence planning. |
| Mean-pool boundary | `MeanPoolAggregator`, `MeanPoolPADA3DACB`, `build_mean_pool_model`, `mean_pool_model_variant_hash` | Makes the comparator identity and model construction testable. |

## Planned data flow

`requested name → registry alias lookup → resolver → resolved config → experiment config/run path → model variant hash`

Unknown names raise `AblationResolutionError`; aliases must resolve to the sole canonical identity. Target adaptation batches are validated before use.

## Apply ownership

| File/surface | Planned action |
|---|---|
| `src/pada3dacb/ablations/registry.py`, `src/pada3dacb/ablations/resolver.py`, `src/pada3dacb/ablations/schemas.py`, `src/pada3dacb/experiments/ablations.py` | Review-gated candidate implementation only. |
| Evaluation display/report mapping | Change only if apply confirms a required mapping. |
| `src/pada3dacb/adaptation/mmd.py`, historical tests, Phase 17 tests | Read-only; Phase 17 tests are immutable regression evidence. |
| `tests/phase_18g/test_*.py` | New focused tests only, after review approval. |

## Testing strategy

Write RED tests first for canonical/alias behavior, unresolved names, `no_da` identity, resolver validation, experiment provenance, and mean-pool hashes; then make the smallest GREEN change. Planned command: `python -m pytest -q`. No tests have been added or run.

## Threat matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file classification, or process-integration boundary is planned.

## Gate

Independent review must confirm this ownership map, protected-MMD equivalence, and compatibility assumptions before apply begins.
