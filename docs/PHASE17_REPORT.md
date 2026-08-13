# Phase 17 — Canonical Ablation Suite Closure Report

**Status: COMPLETE / closed.** The synthetic implementation and validation evidence are complete, and the final independent documentary review returned **PASS** from fallback reviewer `gentle-ai-verify` because requested `kimi` was unavailable. This report does not authorize real-run execution, publication claims, or Phase 18.

## Action graph, ownership, and actual file reconciliation

The authoritative action graph is `specs/phase_17_ablations/agent_plan.yaml`. Scientific ownership remains bound to that plan even when a named runtime profile is unavailable. The table lists the observed authored paths for each action; generated `__pycache__` files are omitted.

| Action | Depends on | Responsible agent | Actual created/modified files for the action |
|---|---|---|---|
| `phase16-closure-and-ablation-audit` | — | `opencode` | `AGENTS.md`; `specs/phase_17_ablations/decisions.md`; `specs/phase_17_ablations/ablation_inventory.yaml` |
| `canonical-ablation-extraction` | `phase16-closure-and-ablation-audit` | `claude-code` | `specs/phase_17_ablations/notebook_extraction.md`; `requirements.md`; `design.md`; `tasks.md`; `acceptance.md`; `equivalence_map.md`; `output_schema.md` |
| `independent-specification-review` | `canonical-ablation-extraction` | `kimi` | `specs/phase_17_ablations/spec_review.md` |
| `implement-ablation-registry-and-resolver` | `independent-specification-review` | `codex` | `src/pada3dacb/ablations/__init__.py`; `schemas.py`; `registry.py`; `resolver.py`; `outputs.py`; `tests/phase_17/test_registry_resolver.py` |
| `implement-loss-component-ablations` | `implement-ablation-registry-and-resolver` | `codex` | `src/pada3dacb/adaptation/prototype_pseudo.py`; `src/pada3dacb/training/uda_trainer.py`; `tests/phase_17/test_composition_diagnostics.py` |
| `implement-architectural-ablations` | `implement-ablation-registry-and-resolver` | `codex` | `src/pada3dacb/models/ablations/__init__.py`; `mean_pooling.py`; `tests/phase_17/test_architecture_ablation.py` |
| `independent-mathematical-verification` | `implement-loss-component-ablations`, `implement-architectural-ablations` | `gemini-cli` | `tests/phase_17/test_mathematical_reference.py`; `test_target_firewall.py` |
| `experiment-cli-integration` | `independent-mathematical-verification` | `opencode` | `src/pada3dacb/experiments/ablations.py`; `scripts/run_ablations.py`; `configs/experiments/ablations.yaml`; `configs/ablations/mean_pool.yaml`; `no_anat.yaml`; `no_concept.yaml`; `no_cons.yaml`; `no_pl.yaml`; `no_proto.yaml`; `src/pada3dacb/experiments/run_manifest.py`; `fold_summary.py`; `prediction_export.py` |
| `complete-integration-and-regression-tests` | `experiment-cli-integration` | `codex` | `tests/phase_17/test_synthetic_lifecycle.py`; `test_protected_methods_regression.py`; `test_cli_regression.py` |
| `documentation` | `complete-integration-and-regression-tests` | `claude-code` | `docs/ABLATION_EXPERIMENTS.md`; `docs/PHASE17_REPORT.md`; `docs/IMPLEMENTATION_AUDIT.md` (preserved; not modified in this remediation) |
| `final-audit` | `documentation` | `kimi` — fallback audit recorded because Kimi was unavailable | `specs/phase_17_ablations/final_audit.md` |
| `final-validation` | `final-audit` | `opencode` | No owned files; validation and Engram evidence only |

### Runtime profile substitution record

- **Kimi:** unavailable for the final-audit execution; the recorded fallback audit preserves the `kimi` ownership row. The independent fallback reviewer `gentle-ai-verify` returned final review **PASS**.
- **Claude-Code and OpenCode:** the supplied artifacts do not record these profiles as unavailable, so no unsupported fallback substitution is asserted for their actions. If the orchestrator substituted a runtime profile, that substitution is execution metadata only and does not change the authoritative ownership table.
- **Codex and Gemini CLI:** remain the implementation and mathematical-verification runtime labels in the authoritative plan.

The action graph above is complete for the planned actions. The separate task ledgers reconcile P17-A1 through P17-A19 as complete only for the authorized synthetic scope; the planned standalone output-identity and integration-contract filenames are addressed by the integrated-test equivalence note in those ledgers, without fabricating files.

## 1. Phase 16 closure reference

Phase 17 follows the archived and approved Phase 16 concept-validation state in `openspec/changes/archive/2026-08-08-phase-16-concept-validation/state.yaml` and its `archive-report.md`. That state records 65 completed tasks and the historical approved Phase 16 receipt provenance. `AGENTS.md` authorized Phase 17 audit, specification, and synthetic-only implementation before any real run, publication result, or Phase 18 work.

The prior incident `#1793` wording and boundary are preserved: it is an administrative delivery issue, not a scientific result. Its historical provenance and required native lifecycle validation remain relevant to lifecycle operations. No current Phase 17 native review receipt was created because the parent bootstrap timed out; no receipt is fabricated here.

## 2. SDD/OpenSpec state

The SDD source of truth is `specs/phase_17_ablations/`, including requirements, design, tasks, acceptance, decisions, inventory, equivalence map, output schema, notebook extraction, agent plan, and specification review. The hybrid OpenSpec artifacts are under `openspec/changes/phase-17-ablations/`.

The OpenSpec state is completed with `status: completed` and `current_phase: phase17-closed` after the final independent fallback review returned **PASS**. The existing approval and boundary fields remain unchanged: synthetic implementation is authorized; real execution, publication, and Phase 18 are not authorized.

## 3. Inventory and historical evidence

The canonical historical source is `notebooks/archive/training_original.ipynb`. The inventory records definitions and helpers but no retained, reproducible Phase 17 ablation result. The only non-commented historical experiment call is the primary `source_to_target`/`bidirectional_results` path; it is provenance evidence, not a current real-data run.

Historical helper runners, selective-fold branches, summary CSV/JSON shapes, and shadowed definitions are not promoted to runnable identities. `specs/phase_17_ablations/ablation_inventory.yaml` remains the inventory authority.

## 4. Six approved candidate IDs

The exact approved synthetic IDs are `no_proto`, `no_pl`, `no_cons`, `no_concept`, `no_anat`, and `mean_pool`. No second identity is created for a descriptive alias.

## 5. Exact interventions and preserved components

| ID | Exact intervention | Preserved components and rules |
|---|---|---|
| `no_proto` | `lambda_proto = 0.0` | Pseudo-label term, canonical model/data/splits, optimizer, schedule, fixed epochs, checkpoint policy, diagnostics, and artifacts remain preserved. |
| `no_pl` | `lambda_pl = 0.0` | Prototype term and all other canonical losses, model/data/splits, optimizer, schedule, epochs, checkpoint policy, diagnostics, and artifacts remain preserved. |
| `no_cons` | `lambda_cons = 0.0` | Only the full consistency term is disabled; warm behavior is numerically unchanged because `warm_lambda_cons = 0.0`. |
| `no_concept` | `lambda_cbm = 0.0` | The concept head and immutable concept artifacts remain present; only concept-supervision loss is disabled. |
| `no_anat` | `lambda_anat = 0.0` | Concept targets, Jacobian artifacts, and every other loss/model/data/training component remain preserved. |
| `mean_pool` | Retained aggregator only: `z = U.mean(dim=1)`, `alpha = 1/K` | The current PADA-3DACB architecture, trainer, losses, data, splits, epochs, and output controls remain preserved; no contextual model is introduced. |

The canonical primary `lambda_proto = 1.0` is preserved. The later helper value `lambda_proto = 0.2` remains unresolved and is not substituted.

## 6. Blocked and equivalent variants

- `no_domain_adaptation`: `BLOCKED_NOT_PROVEN`; zeroing two coefficients does not prove Source-Only loader, forward, gradient, method-identity, or output semantics.
- `no_ctx_encoder`: equivalent to the current explicit no-context PADA-3DACB behavior, but rejected as a runnable identity-patching ablation.
- `identity_ctx`: helper-only, not a production method identity.
- `full`: invalid after the architecture revision; the former contextual Full path is not a current production method.
- `mean_pooling`, long descriptive names, and `source_only`: unsupported aliases unless separately approved with exact provenance.
- `lambda_proto = 0.2`, CFS, ACS, PCS, and QIS: unresolved or blocked; no inference is allowed.

## 7. Unchanged method and phase boundaries

The protected method identities remain unchanged and regression-guarded: Source-Only, PADA-3DACB + CORAL, PADA-3DACB + MMD, CDAN, PADA-3DACB prototype-pseudo, AAGN, and FasterSNN. Phase 15 predictive evaluation and Phase 16 concept evaluation remain unchanged. Phase 17 composes around existing trainer/model boundaries and does not add a duplicate trainer, `ContextualROIEncoder`, `ctx_enc`, or a Full/Lite switch.

## 8. Target-label firewall

Target adaptation accepts exactly `x`, `subject_id`, `subject_hash`, and `cohort`. Target diagnosis labels, probabilities, concept targets, Jacobian targets, and other supervision/artifact fields are rejected before loss computation. Target evaluation is disjoint and labeled exactly **`MONITORING ONLY — NOT A TRAINING LOSS`**.

Target labels and target artifacts cannot affect adaptation loss, gradients, optimizer or scheduler state, checkpoint selection, hyperparameter selection, epoch count, resume choice, or candidate selection.

## 9. Hash and identity contract

Identity hashes use SHA-256 over canonical UTF-8 JSON with sorted keys, stable list ordering, no timestamps in hashed payloads, and `phase17.canonical-json.v1`. Identity data binds the registry, candidate, resolved configuration, model variant, source split, target-adaptation assignment, target-evaluation assignment, and immutable precomputed-artifact hashes.

## 10. Resume and artifact contract

The synthetic lifecycle records fixed-epoch position, history position, source-validation best value, RNG/loader state, identity data, empty target checkpoint-selection state, and `contains_mri_data: false`. Artifact indexes verify written hashes and roles. Resume validates the complete identity and artifact set; mismatches fail closed without overwriting another run, while matching interrupted runs continue without duplicate history rows and matching completed runs are reused read-only.

## 11. Lifecycle evidence

Executed lifecycle evidence covers **60 synthetic CLI plans**: six candidates × five folds × two directions. It also covers approved-candidate validate-only behavior; blocked `no_domain_adaptation`, `no_ctx_encoder`, and invalid requests with exit 2; one complete lifecycle pass; five target-firewall tests; the prior-method/Phase 15/Phase 16 targeted subset of 66 passed; and the registry/CLI subset of 43 passed. No real data was loaded or used.

## 12. Focused Phase 17 result

The focused recheck was:

```text
python -m pytest -q -p no:cacheprovider tests/phase_17 --basetemp=artifacts/pytest-tmp-phase17-full-recheck
```

Result: **119 passed, 0 warnings**.

## 13. Authoritative post-Phase 17 full result

The authoritative current post-Phase17 command was `python -m pytest -q`: **exit 0, 1178 passed, 7 warnings, 1012.14s (0:16:52)**. Warnings were four sklearn `UndefinedMetricWarning` instances, two preprocessing standard-deviation warnings, and the existing Windows pytest-cache permission warning.

The earlier **1059 passed** result is explicitly the **pre-Phase17 baseline**, not the current post-Phase17 result.

## 14. Installation and version evidence

`python -m pip install -e .` completed with **exit 0**. Import/version validation completed with **exit 0** and reported version **0.1.0**.

## 15. Static and whitespace evidence

`python -m ruff check .` completed with **exit 0** and all checks passed. `git diff --check` completed with **exit 0**.

## 16. Previous-method and Phase 15/16 regression status

The executed prior-method/Phase 15/Phase 16 targeted subset passed **66 tests**. The broader post-Phase17 suite passed **1178 tests** as recorded above. These results support unchanged protected-method and earlier-phase regression boundaries; they do not convert synthetic evidence into real-cohort scientific evidence.

## 17. Final audit result

`specs/phase_17_ablations/final_audit.md` records the final audit action accurately: **PASS**, returned by independent fallback reviewer `gentle-ai-verify` because the requested Kimi agent was unavailable in this session. The audit found no critical or scientific defect in the reviewed synthetic-only scope and explicitly did not authorize real execution, publication evaluation, or Phase 18. It accepted the exact current validation evidence: `python -m pytest -q` exited 0 with 1178 passed, 7 warnings, and 1012.14s (0:16:52); the focused Phase 17 recheck passed 119 tests with 0 warnings; 60 synthetic CLI plans, lifecycle/firewall/protected regression subsets, and the recorded static checks passed.

## 18. Audit limitations

The fallback audit and this closure report do not claim real ADNI/OASIS training or evaluation, performance, confidence intervals, significance tests, computational benchmarks, publication tables, leaderboard values, superiority, clinical conclusions, or publication validity. Synthetic fixtures and lifecycle outputs are contract evidence only.

## 19. Engram closure record

Engram closure record **571** was saved for project `PADA-3DACB` under the Phase 17 closure topic. It records the exact commands/results above, the owned closure artifacts, the synthetic-only and no-publication limitations, the absent current native receipt, and next action `stop-await-human-approval`. No historical evidence is reconstructed.

## 20. OpenSpec closure status

OpenSpec is **completed / phase17-closed**. The state preserves approval and boundary fields, records implementation and validation evidence as complete, and keeps `real_execution_authorized: false`, `publication_authorized: false`, and `phase_18_authorized: false`. The next action is **STOP and await explicit human approval**; Phase 18 must not start.

## 21. Real-run authorization

No real run is authorized or performed. Real ADNI/OASIS training or evaluation remains blocked until a separate authorized decision resolves the real-data gate, provenance, protocol, privacy, and lifecycle requirements. This report grants no such authorization.

## 22. Publication and output boundary

No publication metrics, statistical comparisons, manuscript tables, public artifacts, or scientific conclusions were produced. No target label entered adaptation. No Phase 17 claim is a publication result, and no publication operation is authorized by this report.

## 23. Proposed Phase 18 scope — not implemented

A future Phase 18 may be proposed only through a new SDD/OpenSpec decision with explicit scientific questions, authoritative equations, ownership, data authorization, real-run gates, provenance, and publication boundaries. This is a proposal boundary only: no Phase 18 files, plan, implementation, evaluation, or artifacts were created, and no Phase 18 work has started.

## 24. Closure assertions and next action

The following assertions are explicit and unchanged: protected methods remain unchanged; no real data was loaded, trained, or evaluated; no publication output or claim was produced; and Phase 18 was not started or authorized. Phase 17 implementation, validation, and final independent review are complete. The next action is **STOP and await explicit human approval**; do not start Phase 18 or authorize real execution.
