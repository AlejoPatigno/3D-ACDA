# Phase 14 Independent Specification Review

Project: `pada-3dacb`
Change: `phase-14-baselines`
Action: `independent-specification-review`
Reviewer responsibility: repository action assigned this review to `kimi`; active Pi subagent runtime did not expose a `kimi` subagent, so this review was performed by a fresh-context independent verifier as the fallback for the `kimi` responsibility.

## Verdict

APPROVED.

The three blockers from the initial independent review are resolved. The Phase 14 specifications are coherent enough to authorize the first implementation slice, subject to the explicit delivery-workload decision already required by `tasks.md`.

Approval is limited to AAGN / `ROIAwareGatingBaseline`, FasterSNN / `FasterSNNBaseline`, and the shared dataset, trainer, source-only orchestration, tests, configuration, and documentation required for those two baselines. It does not authorize any `active_not_executed` baseline, Phase 15 work, copied PADA-3DACB model, target adaptation, or real cohort training during implementation validation.

## Evidence inspected

Re-read after remediation:

- `specs/phase_14_baselines/baseline_inventory.yaml`
- `specs/phase_14_baselines/notebook_extraction.md`
- `specs/phase_14_baselines/requirements.md`
- `specs/phase_14_baselines/design.md`
- `specs/phase_14_baselines/tasks.md`
- `specs/phase_14_baselines/acceptance.md`

The earlier direct notebook inspection remains authoritative evidence for:

- cell 7: `AlzheimerSupervisedMRIModel` subclasses `AlzheimerDomainAdaptationModel` and is not part of the final baseline factory or CV workflow;
- cell 17: final baseline model/factory inventory, superseded definitions, trainer checkpoint behavior, early-stopping conflict, and final CV workflow;
- cell 18: explicit example execution of AAGN and FasterSNN, with other baseline candidates commented out.

## Prior blocker resolution

### B-14-SPEC-001 — RESOLVED: source-only cross-cohort protocol

The updated artifacts now consistently require:

- `source_train` as the only training split;
- `source_validation` macro-F1 (`val_f1_macro`) as the only checkpoint-selection criterion;
- `target_evaluation` as monitoring/export only;
- no `target_adaptation` loader;
- rejection or deferral of requests that train on the target side of the configured direction.

Exact evidence:

- `baseline_inventory.yaml` contains a structured `source_only_protocol` with `target_adaptation: prohibited` and `target_as_train_cohort: prohibited_for_first_slice`.
- `requirements.md` defines executable scenarios for source-only direction, target-monitoring-only behavior, target-training rejection, and absence of target adaptation.
- `design.md` requires source-only fold construction and names the permitted loaders.
- `tasks.md` assigns implementation tests proving target metrics cannot select checkpoints or alter model state and proving no target-adaptation loader is constructed or consumed.
- `acceptance.md` repeats these conditions as implementation acceptance gates.

Repository invariants also remain explicit: fixed epochs, no early stopping, strict-improvement checkpointing by source-validation macro-F1 only, and no target-guided scheduler, termination, optimizer, gradient, or model-state changes.

### B-14-SPEC-002 — RESOLVED: authoritative baseline inventory

`baseline_inventory.yaml` is now marked `reconciled_authoritative_baseline_inventory` and `authoritative_for_implementation_gate: true`.

Exact evidence:

- AAGN and FasterSNN are `active_executed` with `implement_first_slice` gates.
- CNN, DenseNet, ViT, LongFormer, Joint-Transformer, DA-ViT, and BiFPN3DViT are `active_not_executed` and blocked pending explicit later approval.
- `AlzheimerSupervisedMRIModel` is present at notebook cell 7 lines 473-480, classified `proposed_model_copy`, and gated `do_not_migrate`.
- Obsolete factory/trainer/CV shadows, helper-only symbols, and posthoc reporting are classified with explicit migration gates.
- `notebook_extraction.md`, `requirements.md`, and `acceptance.md` consistently identify the YAML inventory as authoritative for implementation gating.

No invented or external baseline model is permitted. Optional architecture downloads or third-party model implementations remain prohibited unless separately approved.

### B-14-SPEC-003 — RESOLVED: review artifact ownership

The action graph and T0 task now consistently assign the independent review artifact to:

`specs/phase_14_baselines/spec_review.md`

No reviewed remediation artifact references `review_report.md`. The action graph gives each implementation action distinct owned paths and retains the collision rule for any future ownership change.

## Remaining verification findings

- The first implementation slice is unambiguously limited to AAGN and FasterSNN.
- `AlzheimerSupervisedMRIModel` cannot become a production baseline.
- Acceptance criteria are executable through focused synthetic/unit/smoke tests and full repository validation commands.
- Phase 15 artifacts are explicitly prohibited. Concept/domain-adaptation inputs are excluded from baseline design, and confusion-matrix or broader concept-analysis work is not authorized by this approval.
- The Review Workload Forecast is present: chained PRs are recommended, the 400-line risk is High, estimated authored changes exceed 400 lines, and a delivery decision is required before apply.
- File ownership has no collision in the documented action graph.

## Blockers

None for specification approval.

## Limitations and downstream gates

- This is specification approval only; implementation behavior and tests have not been verified.
- No real training was run.
- Graphify was not required because direct notebook inspection and artifact consistency checks were sufficient.
- Before apply, the parent/orchestrator must resolve the Review Workload Forecast through chained/sliced delivery or an explicit size exception.
- Native review/receipt status remains a separate commit/push/PR/release gate as documented in the Phase 14 planning artifacts.
- Archive readiness is not implied; implementation tasks and final acceptance remain incomplete.

## Next action

Proceed to the first approved implementation slice only after resolving the required delivery-workload decision. Keep AAGN and FasterSNN within the assigned work-unit boundaries and preserve the source-only protocol throughout implementation.

## Final planning-conformance addendum

Verdict retained: **APPROVED**.

A narrow recheck of the mechanically corrected `design.md`, `tasks.md`, `acceptance.md`, and mandatory `agent_plan.yaml` found no scope drift or scientific-protocol regression:

- The plan contains 13 serial actions and 40 exclusively owned paths with zero duplicate ownership.
- Production ownership remains limited to AAGN / `ROIAwareGatingBaseline`, FasterSNN / `FasterSNNBaseline`, and their required shared integration surface. Blocked `active_not_executed` baselines have no production-file ownership.
- The corrected filenames are `roi_aware_gating.py`, `faster_snn.py`, and `registry.py`; tests follow the flat `tests/test_baseline*.py` convention.
- Registry APIs remain strict: `list_baselines`, `get_baseline_spec`, and `build_baseline`; blocked, unknown, fuzzy, or fallback construction remains prohibited.
- Configuration ownership uses `configs/experiments/baselines.yaml`, `configs/baselines/aagn.yaml`, and `configs/baselines/faster_snn.yaml`; the rejected generic Phase 14 config path is not planned.
- Source-only training, source-validation-only checkpoint selection, monitoring/export-only target evaluation, fixed epochs, and prohibition of `target_adaptation` remain intact.
- The feature-branch-chain delivery decision is now recorded with serial single-writer enforcement and a 400-authored-line limit per child PR. This addendum supersedes the earlier statement that the delivery-workload decision was still pending.

No new specification blocker was found. Approval remains specification-only and does not imply implementation, review-receipt, or archive readiness.
