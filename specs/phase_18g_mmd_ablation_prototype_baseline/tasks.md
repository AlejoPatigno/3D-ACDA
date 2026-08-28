# Phase 18G Tasks

**Status:** draft/planning. **Implementation:** BLOCKED pending independent review.  
**Authorization recorded:** latest user prompt authorizes apply only after that review.

## Review Workload Forecast

| Field | Value |
|---|---|
| Estimated changed lines | 200–400, excluding immutable evidence |
| 400-line budget risk | Medium |
| Chained PRs recommended | No |
| Suggested split | Registry/resolver contract → experiment/model wiring → focused tests |
| Delivery strategy | pending independent review |
| Chain strategy | pending |

Decision needed before apply: Yes
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Medium

## Phase 1: Review and RED tests

- [ ] 1.1 Obtain independent approval for protected `src/pada3dacb/adaptation/mmd.py`, historical-test evidence, and the ownership map.
- [ ] 1.2 RED: add `tests/phase_18g/test_*.py` for canonical `mean_pool`, alias-only `mean_pooling`, and unresolved-name errors.
- [ ] 1.3 RED: cover `no_da` (`lambda_MMD=0`) identity, adaptation-batch validation, registry hash/provenance, and mean-pool variant hash.

## Phase 2: Registry and resolution

- [ ] 2.1 In `src/pada3dacb/ablations/registry.py` and `src/pada3dacb/ablations/schemas.py`, establish `mean_pool` as the sole canonical entry; map `mean_pooling` only through alias APIs.
- [ ] 2.2 In `src/pada3dacb/ablations/resolver.py`, use the confirmed resolver APIs and retain invalid-name failure behavior.

## Phase 3: Experiment and model wiring

- [ ] 3.1 In `src/pada3dacb/experiments/ablations.py`, wire approved config, equivalence reference, and planned-run identity using the confirmed symbols.
- [ ] 3.2 Implement mean-pool model construction only through the confirmed mean-pool symbols.
- [ ] 3.3 Update evaluation display/report mapping only if apply confirms it is necessary.

## Phase 4: Verification

- [ ] 4.1 Run `python -m pytest -q`; treat Phase 17 and historical tests as immutable regression evidence.
- [ ] 4.2 Record equivalence/isolation evidence without modifying protected MMD or historical tests.

No implementation or verification has occurred.
