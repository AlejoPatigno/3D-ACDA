# Phase B — 3D-ACDA Migration Specification

## Status and decision boundary

This package is a **prospective, documentation-only scientific specification**. It defines the boundary for a future migration from the frozen live binary MMD family to the public/model name **3D-ACDA**. It does not implement, configure, run, evaluate, publish, rename, or rewrite anything.

- Phase B is the only active scope.
- The live family remains anchored to commit `aafe817365cb4068f167b398c776aff4c3b1f021` and to the notebook freeze record.
- Existing MMD source and behavior remain unchanged.
- `pada3dacb`, repository paths, internal IDs, historical records, outputs, and compatibility paths remain unchanged now.
- No production configuration is selected beyond frozen notebook values.
- No real training, evaluation, publication claim, hyperparameter optimization, package rename, or repository rename is authorized.

This package must never be read as evidence that a future run completed or that the historical implementation already satisfies the prospective contracts below.

## Authoritative sources and precedence

1. `docs/EXPERIMENT_FREEZE_PRE_3D_ACDA.md` is authoritative for the live family and its no-change boundary.
2. The frozen, untracked notebook content is authoritative for the live binary protocol; its SHA-256 MUST be recorded as a distinct content anchor before any live activation.
3. The user-verified source commit SHA is a separate provenance anchor for the source tree and MUST NOT be treated as the notebook SHA-256.
4. Phase 18 and Phase 18B contracts remain authoritative for authorization, binary labels, target isolation, provenance, and fail-closed behavior. The Phase 18B OASIS provenance/semantics blocker MUST pass before any Phase D/live-execution activation.
5. Phase 17 contracts remain authoritative for ablation dispositions, legacy equivalence handling, fixed epochs, checkpoint selection, and protected behavior.
6. This package defines prospective migration planning only; it cannot supersede those records.

Conflicting historical package defaults, notebook/helper defaults, and publication wording remain recorded discrepancies. They are not resolved by target outcomes or by this package.

### Provenance anchors and frozen live family

The frozen live family is seeds `42`, `43`, and `44`. Seeds `43` and `44` are recorded as **running by user attestation** within the protected boundaries and activation prerequisites; this is not a completion or result claim. Seed status MUST be verified before any dependent gate is evaluated.

The two required provenance anchors are recorded separately:

- **Untracked notebook SHA-256:** the content hash of the frozen notebook; the value remains to be recorded/verified before activation and is not supplied by this documentation package.
- **User-verified source commit SHA:** `aafe817365cb4068f167b398c776aff4c3b1f021`, verified as the source-tree anchor.

No live execution may proceed if either anchor is missing, mismatched, or not independently evidenced.

## Scientific identity

The public/model name is:

> **3D-ACDA — Three-Dimensional Anatomically Constrained Domain Adaptation**

The scientific contribution is the composition of:

- a 3D encoder;
- 102-ROI representation and tokenization;
- independent ROI refinement;
- learned attention aggregation;
- a concept bottleneck with MRI-derived supervision;
- Jacobian anatomy consistency;
- dual latent and concept paths; and
- cross-cohort evaluation.

MMD is a standard latent unsupervised domain-adaptation regularizer. It is not a novelty claim and must not be presented as the defining architectural contribution.

## Normative requirements

### R-B-001 — Prospective-only scope and protected boundary

The package MUST contain planning and verification contracts only. A future implementation MUST be separately authorized and MUST NOT modify the frozen notebook, existing MMD source, historical specifications, historical outputs, `.git/gentle-ai`, or unrelated paths as part of this package.

Historical records MUST remain historical. No result, completion, superiority, clinical, or publication claim may be inferred from this specification.

### R-B-002 — Binary task and evaluation protocol

Future reporting MUST define the binary task as:

- ADNI: `CN -> CN`, `MCI -> Impaired`, `AD -> Impaired`;
- OASIS: `CDR = 0 -> CN`, `CDR > 0 -> Impaired`, subject to the approved OASIS provenance and semantics gate;
- both transfer directions: `ADNI -> OASIS` and `OASIS -> ADNI`;
- target adaptation and target evaluation MUST be disjoint by subject identity and assignment hash;
- target labels MUST NOT enter training, adaptation, checkpoint selection, hyperparameter selection, or candidate selection;
- aggregation MUST be subject-level, not an unqualified slice-level claim.

These are prospective reporting requirements. They are not proof that historical files already satisfy them. OASIS mapping remains dependent on the Phase 18B semantics gate and approved provenance.

### R-B-003 — Method taxonomy and display aliases

The canonical internal IDs remain unchanged:

| Internal ID | Required display name | Role |
|---|---|---|
| `mmd` | `3D-ACDA` | Primary migrated method identity; MMD remains a standard latent UDA regularizer. |
| `source_only` | `3D-ACDA Source-Only` | Explicit source-only control. |
| `coral` | `3D-ACDA + CORAL` | Explicit comparator. |
| `cdan` | `3D-ACDA + CDAN` | Explicit comparator. |
| `prototype_pseudo` | `3D-ACDA + Prototype/Pseudo` | Explicit legacy/comparator path only. |
| `aagn` | Existing AAGN display identity | Independent baseline. |
| `faster_snn` | Existing FasterSNN display identity | Independent baseline. |

`prototype_pseudo` MUST never become canonical. Historical `no_proto` and `no_pl` MUST remain legacy/supplementary and MUST NOT become primary method rows.

Aliases MUST resolve at read/report time only. Alias resolution MUST NOT mutate output paths, internal IDs, checkpoint names, historical manifests, hashes, or stored source records. A report MUST preserve both the requested spelling and the canonical resolved ID, with an explicit alias-resolution record.

### R-B-004 — Live MMD fidelity

The existing MMD implementation MUST remain mathematically and behaviorally unchanged. Regression evidence MUST preserve the audited contract:

- biased squared mixture-RBF MMD;
- diagonal terms included;
- arithmetic averaging across the mixture kernels;
- float32 pairwise calculation;
- no embedding normalization;
- no median heuristic;
- no final clamp.

The frozen live notebook values are `lambda_MMD = 1` and bandwidths `[1, 2, 4, 8, 16]`. These are live-family provenance, not permission to invent a new production configuration. Any future migration configuration MUST record its source and remain blocked while conflicting values are unresolved.

### R-B-005 — Distinct `no_mmd` semantics

`no_mmd` MUST be a distinct future run with `lambda_MMD = 0`. It MUST NOT be represented as an alias of Source-Only and MUST NOT be treated as runtime-equivalent to `source_only`.

The distinction MUST be retained because target forwards/loaders consume RNG and can change output, manifest, loader-state, and checkpoint/resume semantics even when the MMD coefficient is zero. Future evidence MUST cover:

- target-loader/forward consumption behavior;
- RNG state and loader-state identity;
- output and manifest identity;
- checkpoint and resume behavior; and
- explicit non-equivalence against Source-Only.

### R-B-006 — Primary prospective ablations

The primary future ablation set is exactly:

`no_mmd`, `no_cons`, `no_concept`, `no_anat`, `mean_pool`.

Each candidate MUST be one explicit intervention over an approved base contract. `no_mmd` changes only `lambda_MMD` to `0`; `no_cons` changes only the consistency coefficient; `no_concept` changes only concept supervision; `no_anat` changes only anatomy consistency; and `mean_pool` replaces learned attention aggregation with the explicitly approved mean-pooling intervention.

Historical `no_proto` and `no_pl` remain legacy/supplementary comparators and MUST NOT be silently promoted into the primary list. `no_domain_adaptation`, `no_ctx_encoder`, `identity_ctx`, and `full` retain their Phase 17 dispositions and MUST not be revived by this package.

### R-B-007 — Architecture and data contracts

A future implementation MUST preserve the approved architecture boundary and identify every changed component before activation. It MUST preserve the 102-ROI representation, tokenization, independent refinement, learned attention in the canonical method, concept bottleneck, MRI-derived supervision, Jacobian anatomy consistency, and dual latent/concept paths.

Future cross-cohort evaluation MUST preserve subject-level assignments and the target-label firewall. Target adaptation batches MUST contain no diagnosis labels or target supervision fields. Target evaluation MUST be separate, read-only, and marked monitoring-only.

### R-B-008 — Frozen training and checkpoint behavior

Before activation, the future migration MUST state the complete inherited training contract and prove that no unresolved historical default has been selected by assumption. The frozen notebook values that may be cited as live-family provenance include:

- 102 ROIs, `feature_dim=256`, `token_dim=128`, `base_channels=32`, `concept_hidden_dim=64`;
- both dropouts `0.20`;
- warmup/full schedule `10/50`;
- batch size `16`;
- learning rate and weight decay `1e-4` / `1e-4`;
- gradient clipping `5`;
- AMP enabled when CUDA is available;
- deterministic `50/50` binary source batches;
- MMD weight `1`; and
- bandwidths `[1, 2, 4, 8, 16]`.

No additional production value may be invented in Phase B. Source-validation macro-F1 MUST remain the sole checkpoint-selection criterion, fixed epochs MUST be used, training MUST continue after a best save, and target labels MUST not affect training or selection.

### R-B-009 — Phase C review and Phase D regression evidence

Phase C may begin with the reporting-only scope described in R-B-012; the following evidence is not a prerequisite to starting that scope. It MUST be produced during Phase C implementation/review and MUST be complete before any Phase D/live-execution activation:

1. exact MMD numerical and behavioral regressions, including diagonal terms, arithmetic bandwidth averaging, float32 pairwise behavior, and no normalization/median heuristic/clamp;
2. target-label isolation and disjoint target adaptation/evaluation regressions;
3. legacy comparator regressions for `coral`, `cdan`, `prototype_pseudo`, AAGN, and FasterSNN, with their existing behavior and identities preserved;
4. explicit `no_mmd` non-equivalence regression against Source-Only;
5. read/report-time alias resolution coverage proving no output-path or internal-ID mutation;
6. configuration-hash coverage over canonical IDs, aliases, resolved values, and provenance;
7. checkpoint/resume coverage for canonical IDs, aliases, and mismatched identity rejection; and
8. fixed-epoch, source-validation macro-F1, target-monitoring-only, and subject-level aggregation checks.

A missing test is a blocker for Phase D activation, not an invitation to infer equivalence or to expand Phase C scope.

### R-B-010 — Activation gates

No future runtime activation, live run, or publication evaluation may proceed until all applicable gates pass:

- scientific identity and taxonomy gate;
- binary/OASIS semantics and provenance gate, including the Phase 18B OASIS provenance/semantics blocker;
- target-label isolation and disjoint-assignment gate;
- exact MMD regression gate;
- legacy comparator regression gate;
- `no_mmd` non-equivalence gate;
- alias/config-hash/checkpoint-resume gate;
- frozen configuration and artifact-provenance gate;
- full matrix and subject-level aggregation gate;
- tests and regression evidence gate; and
- the applicable authorization gate.

The user has explicitly authorized the safe, reporting-only Phase C scope described in R-B-012. That authorization is limited to Phase C implementation and is not approval for Phase D/live execution, a rename, or any runtime behavior change. Phase D/live execution additionally requires a separately recorded, explicit execution authorization artifact; maintainer intent, Phase C authorization, a passed C review, or a target outcome cannot substitute for it. Missing, stale, mismatched, or unverified authorization is `BLOCKED`.

Phase C is conditionally startable only after its reporting-only start boundary is evidenced. Phase D/live execution remains blocked until the live family finishes, results/manifests are frozen, all Phase C implementation/review regressions pass, the Phase 18B OASIS provenance/semantics blocker passes, and the separate Phase D authorization is recorded. No target metric may be used to resolve any historical discrepancy.

### R-B-011 — Phase 18B OASIS provenance/semantics blocker

Before any Phase D/live-execution activation, the future owner MUST obtain and preserve the approved Phase 18B evidence for OASIS metadata-generation provenance, accepted values, missing/out-of-domain policy, duplicate/conflict/longitudinal policy, and canonical manifest semantics. The result MUST be recorded as `PASS` by the Phase 18B authority. Missing, unresolved, stale, or conflicting evidence MUST map to `BLOCKED`; no OASIS run, mapping assumption, or target result may bypass this blocker.

### R-B-012 — Phase C reporting-only start boundary

Phase C MAY start now only under the explicit user authorization already received for this safe sequence and only after a start-boundary record verifies all of the following:

1. the frozen source commit/tag reference and frozen notebook boundary are verified, with the notebook content SHA-256 recorded separately from the source commit SHA;
2. a documented import/reachability check proves that the live notebook training path does not import or reach the modified reporting modules; and
3. exclusive non-interference proof shows that the change is limited to a pure report/read-time display-name resolver and report-time projection layer, with no change to training, model, loss, adaptation, configuration, manifest generation, run directories, output paths, checkpoint/resume identity, or historical artifacts.

Phase C MUST preserve canonical IDs, canonical configuration hashes, run directories, output paths, checkpoint/resume identity, and stored historical outputs. The frozen live family runtime, including the currently running seeds `43` and `44`, remains immutable. New report projections MAY resolve approved display aliases while retaining requested spelling, canonical ID, and an alias-resolution record. Historical files MUST never be rewritten.

This start boundary does not claim that Phase C implementation, tests, or review are complete. It authorizes no new run, evaluation, model/configuration change, ablation activation, publication claim, Phase D execution, or package/repository rename.

## Known discrepancies — retain, do not resolve

The package MUST record, rather than silently repair, these discrepancies:

1. **Package versus notebook binary protocol:** historical package contracts and the live notebook differ in task/binary protocol; the notebook is authoritative for the frozen live family, while migration compliance is prospective.
2. **Historical MMD/default configurations:** historical package/publication/helper values differ from the frozen notebook MMD weight/bandwidth contract; no value is selected here beyond the frozen notebook values.
3. **Sampler:** historical package and notebook sampler behavior differ, including the frozen notebook's deterministic `50/50` binary source batches; the discrepancy remains unresolved for future migration activation.
4. **Strict-TDD configuration mismatch:** repository/phase records contain differing strict-TDD or validation configuration signals; no runtime or test-policy value is inferred here. The future execution owner must reconcile this explicitly before activation.

## Future A–F plan

The following sequence is prospective. The user authorization recorded for Phase C is limited to the reporting-only start boundary below; this package does not authorize Phase D, Phase E claims, or Phase F.

- **A — Freeze and identity boundary:** preserve the live commit/notebook family, binary task, provenance, protected MMD behavior, and historical records.
- **B — Scientific specification package:** create this documentation-only requirements, design, task, acceptance, plan, and decision package.
- **C — Reporting-only migration implementation:** under the explicit user authorization and R-B-012 start boundary, implement only the non-breaking display-name resolver and report-time projection layer. Preserve canonical IDs, hashes, run directories, output paths, checkpoint/resume identity, and stored historical outputs; never rewrite historical files. Phase C implementation and review evidence are not claimed complete here.
- **D — Controlled live execution and result freeze:** execute only the approved cross-cohort matrix, enforce target-label isolation and subject-level aggregation, and freeze outputs/manifests/results. **Blocked until the live family finishes, results/manifests are frozen, all Phase C regressions/review pass, the Phase 18B blocker passes, and separate Phase D authorization is recorded.**
- **E — Reporting and scientific comparison:** resolve display aliases at read/report time, compare primary and explicit comparator rows, preserve provenance, and make no claim beyond frozen evidence and approved statistics.
- **F — Separate compatibility rename execution:** if separately approved, execute the rename plan with staged compatibility and migration validation. This package records the plan only; no package or repository rename is executed now.

## Non-goals

This Phase B package does not itself authorize source, configuration, test, notebook, output, data, training, evaluation, HPO, publication, manuscript, rename, or historical-record changes. The separately user-authorized Phase C scope is the narrow reporting-only exception defined in R-B-012; it still forbids runtime behavior changes and historical rewrites.
