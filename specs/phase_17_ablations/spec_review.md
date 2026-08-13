# Phase 17 — Independent Specification Review (Final Refresh)

**Reviewer:** Kimi  
**Action:** `independent-specification-review`  
**Status:** **PASS**

## Executive decision

**PASS — no CRITICAL blocker remains for the already authorized synthetic-only implementation.** The target-firewall declarations and strict runtime enforcement are now aligned. This review approves neither real-data execution nor publication or Phase 18 work.

The six explicitly approved candidates remain bounded to one intervention each:

- `no_proto` — `lambda_proto = 0.0`;
- `no_pl` — `lambda_pl = 0.0`;
- `no_cons` — `lambda_cons = 0.0`;
- `no_concept` — `lambda_cbm = 0.0`;
- `no_anat` — `lambda_anat = 0.0`;
- `mean_pool` — replace only the retained aggregator with `z = U.mean(dim=1)` and uniform `alpha = 1/K`.

## Target-firewall audit

The exact target-adaptation contract is:

```text
[x, subject_id, subject_hash, cohort]
```

Verified:

- `specs/phase_17_ablations/ablation_inventory.yaml` and `output_schema.md` use the exact four keys and the complete forbidden-field list: `y`, `label`, `label_name`, `true_label`, `c_target`, `g_bar`, `diagnosis`, `stored_diagnostic_probabilities`, `concept_targets`, `jacobian_targets`, `other_supervision_fields`, and `other_artifact_fields`.
- Repository requirements/design/tasks and OpenSpec specification/design/tasks use the same four-key contract.
- `schemas.py` requires the exact four-key set; `resolver.py` rejects missing or extra keys before resolution and reports `target_label_firewall_violation`.
- `uda_trainer.py` strict mode requires exact equality with the four-key set, rejects forbidden fields, and rejects every missing or extra field before forward/loss computation. Non-ablation compatibility remains x-only only when strict mode is disabled.
- Target adaptation and target evaluation remain disjoint. Target evaluation retains the exact label `MONITORING ONLY — NOT A TRAINING LOSS` and cannot affect loss, gradients, optimizer/scheduler state, checkpoint selection, hyperparameter choice, epoch count, resume choice, or candidate selection.

## Scientific and administrative boundaries

- The registry preserves all six approvals, exact interventions, one-intervention fairness, and the explicit mean-pool model variant.
- `no_domain_adaptation` remains blocked as `source_only_not_proven`; zeroing adaptation losses does not authorize a Source-Only claim.
- `full`, `no_ctx_encoder`, `identity_ctx`, unsupported aliases, `lambda_proto = 0.2`, CFS, ACS, PCS, and QIS remain blocked or unresolved as recorded.
- The current PADA-3DACB architecture, protected methods, fixed-epoch policy, source-validation-only checkpoint selection, immutable artifacts, assignment hashes, resume identities, and native Phase 16 receipt boundaries remain intact.
- Real ADNI/OASIS execution, publication metrics or claims, and Phase 18 remain unauthorized and out of scope.

## Focused validation

Observed in the current tree:

- `python -m pytest -q tests/phase_17/test_registry_resolver.py` — **22 passed**; one pre-existing pytest cache-permission warning.
- `python -m pytest -q tests/phase_17/test_composition_diagnostics.py` — **26 passed**; one pre-existing pytest cache-permission warning.
- `python -m ruff check .` — **passed**.
- `git diff --check` — **passed**.
- Read-only contract probe — exact valid strict batch accepted; missing, extra, and forbidden strict batches rejected.

## Implementation-status note

This is a specification approval, not an implementation-completion claim. Dedicated future firewall, output-identity, synthetic-lifecycle, protected-regression, CLI, and integration tests remain implementation work and are not claimed complete. Their absence is non-critical for this specification gate and must be resolved before claiming the full Phase 17 implementation complete.

**Final boundary:** PASS for the authorized synthetic-only implementation scope. Do not use this review to approve real data, publication, or Phase 18.
