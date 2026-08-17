# Phase 18 — Scientific Experiment Freeze Requirements

## Decision boundary

This phase defines the publication-experiment protocol, provenance contract, feasibility procedure, and real-run authorization gate. It is planning-only. The freeze is **not approved**: `phase_18_authorized=true`, `real_execution_authorized=false`, `publication_authorized=false`, and Phase 19 is forbidden.

No ADNI/OASIS data, runtime implementation, CLI implementation, configuration change, test, feasibility probe, publication analysis, or result artifact is produced by this specification action.

## Evidence and value classes

Every scientific or operational value in the freeze uses exactly one class:

- `RESOLVED_CANONICAL`: explicitly repeated or protected by repository configuration/specification.
- `RESOLVED_PRE_RUN_HUMAN`: selected and recorded before a real run; it cannot be selected from target outcomes.
- `ENGINEERING_ONLY`: implementation, synthetic-fixture, or operational value that is not a publication claim.
- `BLOCKED_EXTERNAL_PROVENANCE`: missing real path/hash/identity evidence.
- `BLOCKED_CONFLICT`: conflicting evidence retained without silent override.

Repository evidence is authoritative in this order: active package/configuration contracts, the primary non-commented path in `notebooks/archive/training_original.ipynb`, approved Phase 15–17 specifications, then historical helper/prose evidence. No target metric may resolve a conflict.

## Normative requirements

### R18-001 — Authorization and scope

1. The OpenSpec state MUST retain `phase_18_authorized: true`.
2. It MUST retain `real_execution_authorized: false`, `publication_authorized: false`, and `phase_19_forbidden: true` until a separate human approval changes them.
3. Any real-data load, training, evaluation, publication statistic, manuscript table, or Phase 19 action MUST fail closed before input access.
4. `.git/gentle-ai`, the approved native receipt, unrelated dirty files, and all non-owned paths MUST remain untouched.

### R18-002 — Cohorts, labels, and directions

The only cohorts are `ADNI` and `OASIS`. The only transfer directions are `ADNI -> OASIS` and `OASIS -> ADNI`, represented in parser-bound canonical lowercase IDs `adni_to_oasis` and `oasis_to_adni` where the current parser requires identifiers. Display labels and legacy/uppercase aliases MUST be rejected, not silently remapped. Diagnostic order is fixed: `CN=0`, `MCI=1`, `AD=2` (`canonical_fixed`). No cohort, direction, or class order may be inferred from available files.

### R18-003 — Frozen runnable method inventory

The core inventory contains exactly these repository-approved IDs, in deterministic order:

1. `source_only` — `PADA-3DACB Source-Only`.
2. `coral` — `PADA-3DACB + CORAL`.
3. `mmd` — `PADA-3DACB + MMD`.
4. `cdan` — `PADA-3DACB + CDAN`.
5. `prototype_pseudo` — `PADA-3DACB`.
6. `aagn` — `AAGN / ROI-aware gating`.
7. `faster_snn` — `FasterSNN`.

This list is `RESOLVED_CANONICAL` as an inventory boundary, not evidence that a real run has completed. Historical or forbidden names are not rows in the runnable matrix. The publication ablation classification is a separate `RESOLVED_PRE_RUN_HUMAN` planning decision: primary `[no_proto,no_pl,no_concept,no_anat]`, supplementary `[no_cons,mean_pool]`, excluded `[no_domain_adaptation,no_ctx_encoder,full,identity_ctx]`. It does not authorize execution or metrics.

### R18-004 — Objective and coefficient fidelity

The PADA-3DACB primary objective MUST preserve the recorded warm/full equations. The repository-supported coefficients are:

```text
lambda_z=1.0, lambda_c=1.0, lambda_cons=0.1,
lambda_cbm=0.5, lambda_anat=0.2, lambda_pl=0.1,
tau_p=0.95, proto_margin=1.0, lambda_sep=0.1,
label_smoothing=0.1,
warm_lambda_z=0.1, warm_lambda_c=1.0,
warm_lambda_cbm=1.0, warm_lambda_anat=1.0,
warm_lambda_cons=0.0
```

These are `RESOLVED_CANONICAL` inherited primary-path values. `lambda_proto=1.0` is `RESOLVED_PRE_RUN_HUMAN` for production, bound before any run. The later helper/manuscript `0.2` is retained as a `BLOCKED_CONFLICT` non-production discrepancy; it cannot be selected using target performance. The real-run gate still rejects authorization until external provenance, resources, and approval are complete.

Warm-up MUST not compute or weight prototype/pseudo-label adaptation and MUST log those components as zero. Full-stage adaptation MUST use the existing source-label and target-concept-logit contracts without target diagnosis labels.

### R18-005 — Fixed epochs and checkpoint selection

Fixed epochs are mandatory; early stopping is prohibited. For the primary PADA-3DACB path, the repository-supported notebook/config values are `5` warm epochs and `50` full epochs (`canonical_fixed`). The generic training config's `20/30` values are not silently substituted for this publication matrix. A method-specific checked-in configuration is required for each baseline. CORAL adaptation weight, MMD adaptation weight/kernel/bandwidth fields, and CDAN adaptation weight/GRL/discriminator settings are mandatory fields and currently `unresolved_blocking`. A loader MUST validate their presence, type, and schema; missing or null values and invented, inherited, or generic defaults are forbidden.

The sole best-checkpoint criterion is source-validation macro-F1. Training MUST continue through all declared epochs after a best checkpoint is saved. Target monitoring MUST NOT affect loss, gradients, optimizer, scheduler, checkpoint, epoch count, resume, hyperparameter, method, or candidate selection. The separate `last` checkpoint is a predeclared sensitivity projection only.

### R18-006 — Complete matrix and seed policy

The matrix MUST be the complete Cartesian product of the approved method inventory, both directions, folds `0..4`, and the pre-run seed policy `[42,43,44]`. The seed set, source split random state `42`, and target partition seed `42` are `RESOLVED_PRE_RUN_HUMAN`, predeclared, and not posthoc-selectable. Missing real assignment manifests remain `BLOCKED_EXTERNAL_PROVENANCE`.

The obsolete selective-fold availability shortcut MUST NOT be used. Every expected cell MUST be represented with an explicit state; no matrix row in this phase may be `COMPLETED`. The matrix MUST separate `row_kind: training` from `row_kind: checkpoint_projection`, link each projection with `parent_training_id`, and require exactly one training invocation per method/direction/fold/seed cell.

### R18-007 — Target isolation

`target_adaptation` and `target_evaluation` MUST be disjoint by subject identity and assignment hash. Exact manifest bytes MUST be hash-verified before parsing, and a content-level intersection over the parsed subject identities MUST be empty; aggregate assignment hashes alone are insufficient. Target-adaptation batches MUST contain exactly `x`, `subject_id`, `subject_hash`, and `cohort`; diagnosis labels, probabilities, concept targets, Jacobian targets, and other supervision/artifact fields are forbidden. Target evaluation is labeled exactly `MONITORING ONLY — NOT A TRAINING LOSS` and is read-only.

### R18-008 — Immutable artifacts and provenance

Before any real run, the protocol MUST identify and hash the source/target split manifests, source assignments, target adaptation/evaluation assignments, atlas metadata, ROI order/masks, concept normalizer, concept targets, Jacobian artifacts, model/configuration identities, code/environment identity, and approved command. Structured records MUST use the exact versioned `phase18.canonical-json.v1` profile with deterministic numeric, negative-zero, Unicode, and separator rules. Authoritative conformance vectors and implementation identity are required; if unavailable, canonicalization remains `unresolved_blocking`. Missing, conflicting, regenerated, or silently remapped artifacts MUST fail closed. No concept normalizer, concept target, Jacobian, atlas, split, or preprocessing artifact may be regenerated in the experiment phase.

### R18-009 — Feasibility

Feasibility MAY use only deterministic synthetic data with faithful tensor ranks, channels, class count, ROI count, loader contracts, and artifact schemas. It MUST NOT use ADNI/OASIS files or claim real throughput. Synthetic feasibility may validate shapes/contracts and record synthetic diagnostics only; it MUST NEVER resolve real wall-time, memory, storage, worker, concurrency, or retry fields. The feasibility protocol MUST record observations under an explicitly synthetic namespace; absent real hardware observations remain unresolved, not zero.

### R18-010 — Resource budget

The budget MUST distinguish conservative and nominal scenarios. Hardware, VRAM/RAM, wall time, storage, and concurrency values without repository or observed hardware evidence MUST remain `unresolved_blocking` placeholders. Cell counts and formulas MAY be recorded as `engineering_only`; they are not measured runtime.

### R18-011 — Fail-closed CLI contract

Future implementation MUST expose planning/validation modes that do not access real data, plus an explicit real-run mode that requires the authorization manifest and all resolved hashes. It MUST support exact method, direction, fold, seed, config, artifact-index, output-root, dry-run, validate-only, and resume selectors. Missing approval, unresolved coefficient, incomplete matrix, missing artifacts, target-label leakage, invalid provenance, or hash mismatch MUST stop before training.

### R18-012 — Manuscript alignment

The alignment audit MUST classify each comparison as `MATCH`, `MANUSCRIPT_OUTDATED`, `REPOSITORY_OUTDATED`, or `UNRESOLVED`. Because no complete manuscript PDF is present, no discrepancy may be silently resolved and the manuscript MUST NOT be rewritten by this phase. Lambda production use, checkpoint criterion, and ablation classification are recorded as pre-run decisions; manuscript-only wording, scores, and endpoints remain `UNRESOLVED`.

## Non-goals

This phase does not implement runtime code, CLI code, configs, tests, data discovery, preprocessing, artifact generation, training, evaluation, statistical analysis, publication reporting, manuscript edits, or Phase 19. It does not convert Phase 17 synthetic evidence into real-cohort evidence or freeze a publication claim.
