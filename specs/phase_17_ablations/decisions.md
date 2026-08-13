# Phase 17 — Ablation Closure and Canonical Inventory Decisions

## Decision summary

This action closes the Phase 16 dependency check and audits the historical ablation surface before any Phase 17 production implementation. The audit is documentation-only. No ablation runner, configuration, model variant, loss path, real-data run, or publication evaluation was added.

The canonical conclusion is conservative: the notebook contains ablation definitions and helpers, but no ablation study call is executed in the archived source. Only the primary domain-adaptation call is a non-commented call. Every ablation candidate remains classified as `canonical_defined_not_executed`, `equivalent_to_existing_method`, `invalid_after_architecture_revision`, `helper_only`, `obsolete`, or `unsupported` as recorded in `ablation_inventory.yaml`. The human maintainer has now explicitly approved six exact candidates for Phase 17 implementation: `no_proto`, `no_pl`, `no_cons`, `no_concept`, `no_anat`, and `mean_pool`. This approval authorizes synthetic/test implementation only; it does not authorize real ADNI/OASIS execution, publication evaluation, or Phase 18.

## Explicit Phase 17 candidate approval

Recorded from the maintainer decision in the orchestration session:

| Approved ID | Exact intervention | Approval boundary |
|---|---|---|
| `no_proto` | `lambda_proto = 0.0` | Synthetic validation and production-contract implementation; inherit every other primary setting. |
| `no_pl` | `lambda_pl = 0.0` | Synthetic validation and production-contract implementation; inherit every other primary setting. |
| `no_cons` | `lambda_cons = 0.0` | Synthetic validation and production-contract implementation; warm remains numerically unchanged. |
| `no_concept` | `lambda_cbm = 0.0` | Synthetic validation and production-contract implementation; preserve concept head and all other terms. |
| `no_anat` | `lambda_anat = 0.0` | Synthetic validation and production-contract implementation; preserve concept targets and head. |
| `mean_pool` | Replace attention aggregation with the exact uniform mean operation from the notebook. | Synthetic validation and production-contract implementation as a separate explicit model variant; no production model switch. |

The approval does not resolve `lambda_proto=0.2` versus `1.0`, does not approve `no_domain_adaptation` as Source-Only, does not approve aliases, and does not authorize real data or publication claims. All rejected/unsupported/obsolete/contextual candidates remain fail-closed.

## Phase 16 closure and authorization gate

Repository artifacts and the parent-provided current Engram context agree that Phase 16 is archived and approved:

- `openspec/changes/archive/2026-08-08-phase-16-concept-validation/state.yaml` is the current hybrid artifact state: `status: archived`, 65 tasks complete, native lineage `review-79ee2a4308d2010c`, `state: approved`, and post-apply `result: allow`.
- `openspec/changes/archive/2026-08-08-phase-16-concept-validation/archive-report.md` records the same approved receipt and explicitly states that Phase 17 production work remains forbidden until separately authorized.
- `AGENTS.md:640-658` records the current Phase 17 authorization, the approved Phase 16 receipt, and the boundary that real ADNI/OASIS ablations, publication results, and Phase 18 work are not started by default.
- Older blocked verification mirrors remain in the workspace as superseded historical evidence. They are not rewritten by this action; the current archived `state.yaml` and archive report are authoritative for closure.

The following Phase 16 gates remain unchanged and are carried forward:

- Real evaluation and real ADNI/OASIS training remain authorization-gated and were not run.
- CFS, ACS, PCS, and QIS remain `BLOCKED` because no complete authoritative equations were verified. Names are not sufficient evidence for an equation.
- The former native incident #1793 was resolved as an administrative delivery issue by the approved Phase 16 receipt. Its receipt provenance and native pre-commit/pre-push/pre-PR/release validation gates remain mandatory; it is not a scientific result and does not authorize changes to earlier phases.
- No Phase 17 production path existed before Phase 17 authorization. The historical notebook helpers are not production implementation.

## Canonical source and precedence rules

The source of truth for this audit is the source text of `notebooks/archive/training_original.ipynb`, inspected deterministically by cell and source line. The following repository documents were used as cross-checks:

- `docs/PROPOSED_METHOD_EXPERIMENT.md`
- `docs/PHASE13_REPORT.md`
- `specs/phase_13_prototype_pseudo/notebook_extraction.md`
- `docs/NOTEBOOK_MIGRATION_MAP.md`
- `docs/PADA3DACB_MODEL.md`
- `docs/LOSSES_AND_TRAINING.md`
- `specs/phase_16_concept_validation/manuscript_extraction.md`
- `specs/phase_16_concept_validation/decisions.md`
- `openspec/changes/archive/2026-08-08-phase-16-concept-validation/archive-report.md`

Precedence is:

1. Active source code and the non-commented primary call in the archived training notebook.
2. The explicit production architecture and training contracts already recorded in repository specifications and docs.
3. Commented examples, later helper definitions, notebook prose, and historical copies, which are evidence only and never silently become canonical behavior.

A separate complete manuscript PDF was not present in the repository; the Phase 16 manuscript extraction records that limitation. Therefore no ablation meaning is inferred from manuscript names.

## Canonical executed control

`training_original.ipynb` cell 15, lines 11-26, contains the non-commented call:

```python
bidirectional_results = run_bidirectional_domain_adaptation(...)
```

Its arguments are `n_splits=5`, `batch_size=16`, `num_workers=2`, `n_epochs_warm=5`, `n_epochs_full=50`, `lr=1e-4`, `weight_decay=1e-4`, and `random_state=42`. The active cell-14 runner constructs the original model/loss/trainer path and passes the primary loss coefficients, including `lambda_proto=1.0` at cell 14, lines 504-524. The backward call is commented out at cell 14, lines 713-730; the returned result contains only `source_to_target` at lines 732-735.

This is classified as `canonical_executed` in the inventory because it is the only non-commented training call and is identified as the primary executed path by the Phase 13 extraction/audit. The notebook has stripped outputs and no execution counts, so this classification means "canonical non-commented executed-path evidence," not a new claim of a reproducible real-data run in this workspace.

## Architecture decision

The production model is the explicit no-context PADA-3DACB architecture documented in `docs/PADA3DACB_MODEL.md`: ROI tokenization, token normalization/MLP/dropout, attention aggregation, classification head, and concept bottleneck, with no `ContextualROIEncoder`, no `ctx_enc`, and no Full/Lite runtime switch.

Consequences:

- `no_ctx_encoder` / `identity_ctx` is not a new production ablation. It is an identity patch over the former Full notebook model and is behaviorally equivalent to the already approved no-context PADA-3DACB architecture, while remaining an invalid implementation technique after the architecture revision.
- `full` in the later helper means the former contextual Full model, not the current production PADA-3DACB control. It is therefore `invalid_after_architecture_revision`.
- `mean_pool` is a real alternative pooling intervention over the retained attention aggregator. It is defined but not executed and is not part of the final proposed architecture. It remains blocked as an unexecuted candidate until a Phase 17 runtime contract explicitly preserves all other components and output identities.

## Ablation semantics

The exact source names and interventions are:

| Source name | Exact intervention | Preserved components | Warm objective | Full objective | Status |
|---|---|---|---|---|---|
| `no_proto` | `lambda_proto=0.0` | Model, source losses, concept supervision, anatomy, head consistency, pseudo-label component | Unchanged; prototype is already absent from warm | Removes `lambda_proto * L_proto` only | Defined, not executed |
| `no_pl` | `lambda_pl=0.0` | Model, source losses, concept supervision, anatomy, head consistency, prototype component | Unchanged; pseudo-label is already absent from warm | Removes `lambda_pl * L_pl` only | Defined, not executed |
| `no_cons` | `lambda_cons=0.0` | Model and all other loss terms | Removes the consistency contribution because warm multiplier is already zero | Removes `lambda_cons * L_cons` | Defined, not executed; `no_head_consistency` is not an exact source symbol |
| `no_concept` | `lambda_cbm=0.0` | Model, diagnosis heads, anatomy, prototype, pseudo-label, head consistency | Removes `lambda_cbm * L_concept` | Removes `lambda_cbm * L_concept` | Defined, not executed |
| `no_anat` | `lambda_anat=0.0` | Model, diagnosis heads, concept supervision, head consistency, prototype, pseudo-label | Removes `lambda_anat * L_anat` | Removes `lambda_anat * L_anat` | Defined, not executed |
| `no_domain_adaptation` | `lambda_proto=0.0` and `lambda_pl=0.0` | All supervised terms and model architecture | Unchanged supervised warm objective | Removes prototype and pseudo-label terms, but the historical runner still builds/forwards a target adaptation loader; it is not automatically a true source-only control | Defined, not executed and semantically blocked |
| `mean_pool` | Replace attention aggregator with uniform `U.mean(dim=1)` and uniform `alpha` | Encoder/tokenizer/token processing, heads, and losses | Unchanged | Unchanged | Defined, not executed and blocked pending explicit Phase 17 contract |
| `no_ctx_encoder` | Patch `ctx_enc` with `IdentityContextualEncoder` | Former Full model's remaining components and losses | Unchanged | Unchanged | Equivalent to existing method but invalid as a post-revision implementation |

No target-label contract is changed by any candidate. A valid future implementation must accept target-adaptation batches with exactly the four allowed fields `x`, `subject_id`, `subject_hash`, and `cohort`; forbidden fields include `y`, `label`, `label_name`, `true_label`, `c_target`, `g_bar`, `diagnosis`, stored diagnostic probabilities, concept targets, Jacobian targets, and other supervision/artifact fields. `target_adaptation` must remain disjoint from `target_evaluation`, which is a separate monitoring-only path. The historical notebook's target train/eval loaders must not be treated as permission to feed target labels into adaptation losses.

## Warm/full objective contract

The active `DomainAdaptiveTotalLoss` is defined in cell 8, lines 442-625. Its warm objective is established at cell-local lines 526-563:

```text
L_warm = warm_lambda_z    * lambda_z    * L_cls_z
       + warm_lambda_c    * lambda_c    * L_cls_c
       + warm_lambda_cbm  * lambda_cbm  * L_concept
       + warm_lambda_anat * lambda_anat * L_anat
       + warm_lambda_cons * lambda_cons * L_cons
```

The executed primary coefficients are recorded at cell 14, lines 504-524 and in `specs/phase_13_prototype_pseudo/notebook_extraction.md`:

```text
lambda_z=1.0, lambda_c=1.0, lambda_cons=0.1,
lambda_cbm=0.5, lambda_anat=0.2,
lambda_proto=1.0, lambda_pl=0.1,
tau_p=0.95, proto_margin=1.0, lambda_sep=0.1,
label_smoothing=0.1,
warm_lambda_z=0.1, warm_lambda_c=1.0,
warm_lambda_cbm=1.0, warm_lambda_anat=1.0,
warm_lambda_cons=0.0
```

The later ablation helper at cell 18, lines 55-86, changes the default `lambda_proto` to `0.2`; this is not the primary executed configuration. It is recorded separately as an unresolved/unsupported configuration candidate because repository engineering behavior uses `lambda_proto=1.0` while prior documentation records a manuscript discrepancy (`D-14-001`). No value is chosen here.

The full objective is established at cell 8, lines 568-625:

```text
L_full = lambda_z     * L_cls_z
       + lambda_c     * L_cls_c
       + lambda_cons  * L_cons
       + lambda_cbm   * L_concept
       + lambda_anat  * L_anat
       + lambda_proto * L_proto
       + lambda_pl    * L_pl
```

`L_proto` uses source/target embeddings and target concept-head logits; `L_pl` uses target concept-head logits. Warm logs set both adaptation components to zero at cell 8, lines 550-562. No candidate may invent a warm-stage adaptation effect.

## Checkpoint and output policy

The historical notebook output locations are observed, not approved publication defaults:

- Primary cell 14, lines 577-619: `<save_dir>/<source>_to_<target>/fold_<NN>/domain_adaptive_mri_cbm.pt`, `history_domain_adaptive.json`, and architecture metadata.
- Ablation-aware cell 18, lines 410-458: `<save_dir>/<ablation>/<source>_to_<target>/fold_<NN>/domain_adaptive_mri_cbm.pt`, `history_domain_adaptive.json`, and architecture metadata.
- Ablation summary helper cell 18, lines 621-642: `ablation_folds.csv`, `ablation_summary.csv`, and `ablation_runs.json`.
- The row/table helper cell 18, lines 96-161, reports terminal loss components and source/target train/validation metrics; it does not establish a publication statistical protocol.

For any future production Phase 17 implementation, the existing fixed-epoch contract remains binding: source-validation macro-F1 is the only best-checkpoint criterion, training continues for all configured epochs, target metrics do not select checkpoints or hyperparameters, and outputs must carry method/config/split/checkpoint provenance. The notebook's final checkpoint save alone does not override that production policy.

## Validation and bugfix boundary

The parent supplied the following closure evidence for the current tree:

- `python -m pip install -e .` — passed.
- `python -c "import pada3dacb; print(pada3dacb.__version__)"` — passed; printed `0.1.0`.
- `python -m pytest -q --basetemp=artifacts/pytest-tmp-phase17-final` — passed; `1059 passed, 7 warnings`, exit 0.
- Focused Windows cleanup regression tests — `30 passed`.
- `python -m ruff check .` — passed.
- `git diff --check` — passed.

The only bugfix associated with this closure was the existing Phase 16 Windows lock-cleanup change in `src/pada3dacb/evaluation/concepts/report.py` with its focused regression coverage in `tests/test_concept_report.py`. Those paths are parent-owned and were not modified by this action. The bugfix changes no Phase 17 ablation behavior, and no Phase 17 production code was created.

## Remaining blockers and next action

- Do not execute real ADNI/OASIS ablations or publication evaluation in this action.
- Do not promote ambiguous aliases (`no_head_consistency`, `no_concept_supervision`, `no_anatomical_consistency`) without tying them to exact source symbols and contracts; the inventory records their exact-source status.
- Resolve the `lambda_proto=0.2` versus `1.0` discrepancy before any publication-facing ablation matrix is frozen.
- Replace the historical selective-fold `availability` shortcut with a complete, predeclared fold/seed matrix before implementation; it is not valid evidence for a full ablation.
- Preserve the native incident #1793 receipt provenance and lifecycle boundary; do not alter its artifacts.
- Phase 18 remains explicitly not started.

The next action is an independently reviewed Phase 17 specification/implementation decision, not a real run. This closure action itself made no production changes.
