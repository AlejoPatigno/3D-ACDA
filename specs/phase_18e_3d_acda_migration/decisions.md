# Phase B — 3D-ACDA Migration Decisions and Discrepancy Register

## Decision status

This is a prospective decision record for Phase B. It authorizes documentation of a future migration boundary only. It does not authorize runtime changes, real training/evaluation, publication analysis, HPO, output mutation, package/repository rename, or historical record rewriting.

## Accepted scientific decisions

### D-B-001 — Public/model identity

The public/model name is **3D-ACDA**, expanded as **Three-Dimensional Anatomically Constrained Domain Adaptation**.

The contribution is the complete architecture and evaluation design: 3D encoder, 102-ROI representation/tokenization, independent ROI refinement, learned attention, concept bottleneck with MRI-derived supervision, Jacobian anatomy consistency, dual latent/concept paths, and cross-cohort evaluation.

MMD is a standard latent UDA regularizer. It is not a novelty claim and must not be used as the public method's scientific differentiator.

### D-B-002 — Live provenance and no-change boundary

The live family is anchored to the user-verified source commit `aafe817365cb4068f167b398c776aff4c3b1f021` and the notebook/provenance record `docs/EXPERIMENT_FREEZE_PRE_3D_ACDA.md`.

The untracked frozen notebook's SHA-256 is a separate content anchor. Its value is not invented by this package and must be recorded and independently verified before activation; it is not interchangeable with the source commit SHA.

The frozen live family is seeds `42`, `43`, and `44`. Seeds `43` and `44` are recorded as running by user attestation within protected boundaries and activation prerequisites; this does not claim completion or results.

The existing MMD source, notebook, outputs, package, repository identity, historical paths, historical documents/specifications, Git metadata, and existing OpenSpec changes are protected. Phase B owns only the new directory `specs/phase_18e_3d_acda_migration/`.

No statement in this package proves that a live seed completed or that historical files satisfy the prospective requirements.

### D-B-003 — Taxonomy

The following presentation mapping is approved without changing internal IDs:

| Internal ID | Display | Status |
|---|---|---|
| `mmd` | `3D-ACDA` | Primary public/model display. |
| `source_only` | `3D-ACDA Source-Only` | Explicit source-only control. |
| `coral` | `3D-ACDA + CORAL` | Explicit comparator. |
| `cdan` | `3D-ACDA + CDAN` | Explicit comparator. |
| `prototype_pseudo` | `3D-ACDA + Prototype/Pseudo` | Explicit comparator; legacy/comparator-only. |
| `aagn` | Existing AAGN identity | Independent baseline. |
| `faster_snn` | Existing FasterSNN identity | Independent baseline. |

`no_proto` and `no_pl` remain legacy/supplementary. They are not primary prospective ablations. Display aliases resolve at report/read time only and must not mutate paths, IDs, manifests, hashes, checkpoints, or resume identities.

### D-B-004 — Binary reporting contract

Future reporting is expected to use:

- ADNI `CN` versus `MCI/AD`;
- OASIS `CDR=0` versus `CDR>0`;
- both `ADNI -> OASIS` and `OASIS -> ADNI`;
- disjoint target adaptation and target evaluation by subject identity and assignment hash;
- no target labels in training or model selection; and
- subject-level aggregation.

This is a prospective reporting requirement. It is not a claim that the current historical package or notebook already complies. OASIS semantics remain subject to approved Phase 18B metadata/provenance evidence.

### D-B-005 — MMD fidelity

The existing audited MMD behavior is protected exactly as observed:

- biased squared mixture-RBF MMD;
- diagonal terms included;
- arithmetic bandwidth averaging;
- float32 pairwise calculation;
- no normalization;
- no median heuristic; and
- no final clamp.

The live notebook values are `lambda_MMD=1` and bandwidths `[1,2,4,8,16]`. They are the only MMD values frozen for this live family in Phase B. No new production configuration is invented.

### D-B-006 — Primary prospective ablations

The primary prospective set is:

`no_mmd`, `no_cons`, `no_concept`, `no_anat`, `mean_pool`.

Each future candidate must be one explicit intervention. `mean_pool` is an aggregator intervention, not a contextual or Full/Lite model. Historical `no_proto` and `no_pl` remain supplementary/legacy. Existing Phase 17 dispositions for `no_domain_adaptation`, `no_ctx_encoder`, `identity_ctx`, and `full` remain unchanged.

### D-B-007 — `no_mmd` is not Source-Only

`no_mmd` must be a distinct future run with `lambda_MMD=0`. It is not runtime-equivalent to `source_only` because target forwards/loaders consume RNG and may produce different loader state, outputs, manifests, checkpoint state, and resume behavior.

Future activation requires a regression that demonstrates this non-equivalence. A zero coefficient is not proof of a source-only execution path.

### D-B-008 — Phase D authorization and OASIS blocker

Phase D/live execution requires both (1) a passed and separately recorded Phase 18B OASIS provenance/semantics blocker and (2) a separately recorded, explicit Phase D execution authorization artifact. Neither may be inferred from C authorization, review approval, user intent, a seed attestation, or target outcomes. A missing, stale, conflicting, or failed prerequisite is `BLOCKED` before data access.

### D-B-009 — User-authorized Phase C safe sequence

The user has explicitly authorized Phase C to start now, but only for a pure, non-breaking display-name resolver and report-time projection layer. Before implementation starts, the owner must record the verified frozen source commit/tag and notebook boundary, a documented import/reachability check proving that the live notebook training path does not import or reach modified reporting modules, and exclusive proof that training, model, loss, adaptation, configuration, manifest generation, run directories, output paths, checkpoint/resume identity, and historical artifacts remain unchanged.

Phase C preserves canonical IDs, canonical configuration hashes, run directories, output paths, checkpoint/resume identity, and stored historical outputs. New projections may resolve display aliases at read/report time, but historical files must never be rewritten. This authorization is not approval for a live run, Phase D, or a package/repository rename. The package records no claim that Phase C implementation, tests, or review are complete.

## Discrepancy register — unresolved by design

### X-B-001 — Package versus notebook binary protocol

The live notebook is frozen as a binary CN-vs-Impaired family, while historical package configurations/specifications include differing task and label protocols, including three-class contracts. The notebook and immutable live boundary govern the frozen family; historical package contracts are not rewritten. The migration specification is prospective and must not imply that a historical package default was silently changed.

**Disposition:** `BLOCKED_CONFLICT`; resolve only through explicit future evidence/decision and migration review.

### X-B-002 — Historical MMD and default configurations

Historical package, helper, and publication-facing defaults differ from the frozen notebook MMD contract and other training values. In particular, historical defaults must not be substituted for the live notebook values, and no target result may select between them.

**Disposition:** `BLOCKED_CONFLICT`; preserve source/provenance for every future resolved value.

### X-B-003 — Sampler behavior

The frozen notebook records deterministic `50/50` binary source batches, while historical package/configuration sampler behavior differs. The difference affects reproducibility and potentially RNG/loader semantics. Phase B records the discrepancy and does not choose a universal future sampler.

**Disposition:** `BLOCKED_CONFLICT`; require an explicit future pre-run decision and regression evidence.

### X-B-004 — Strict-TDD configuration mismatch

The repository and inherited phase records contain differing strict-TDD and validation configuration signals. Phase B does not infer which runtime test policy is authoritative, does not run tests, and does not alter configuration.

**Disposition:** `BLOCKED_CONFLICT`; the future execution owner must reconcile the policy before implementation activation and record the decision with evidence.

### X-B-005 — OASIS provenance and semantics

The prospective `CDR=0` versus `CDR>0` mapping is required by the user-approved reporting direction, but Phase 18B still requires approved metadata-generation provenance, accepted values, missing/out-of-domain policy, duplicate/conflict/longitudinal policy, and a canonical manifest before production use.

**Disposition:** `BLOCKED_EXTERNAL_PROVENANCE`; no OASIS run or historical claim is authorized by this package.

## Required future evidence before Phase D activation

The following are gates, not completed evidence. They are produced during Phase C implementation/review and are not prerequisites to starting the reporting-only Phase C scope:

1. exact MMD numerical/behavioral regressions against the existing source;
2. target-label isolation and disjoint target partition regressions;
3. legacy comparator regressions for CORAL, CDAN, and prototype/pseudo;
4. independent baseline regressions for AAGN and FasterSNN;
5. explicit `no_mmd` non-equivalence regression against Source-Only;
6. read/report-time alias coverage with no output-path or internal-ID mutation;
7. canonical configuration-hash coverage;
8. checkpoint/resume coverage, including alias handling and mismatch rejection;
9. fixed epochs, source-validation macro-F1-only selection, target-monitoring-only, and subject-level aggregation evidence; and
10. finished live runs, frozen results/manifests, and separate explicit Phase D execution authorization.

Phase C is conditionally startable only under D-B-009 and its documented boundary evidence. Phase D remains blocked until all listed regression/review evidence, finished live runs, frozen results/manifests, the Phase 18B blocker, verified seed status, and separate Phase D authorization are present. A target metric, a historical file, or a plausible numerical result cannot substitute for any gate.

## Rename plan — explicitly not executed

A future separately approved rename may inventory imports, entry points, package metadata, config names, display names, manifests, checkpoints, documentation, and repository paths; introduce compatibility readers; preserve `pada3dacb`, `mmd`, and historic paths during a compatibility window; and validate aliases, hashes, checkpoint resume, and historical reads.

This record does not execute or authorize a package rename, repository rename, path migration, ID migration, or historical rewrite.
