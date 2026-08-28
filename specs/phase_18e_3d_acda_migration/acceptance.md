# Phase B — 3D-ACDA Migration Acceptance Contract

## Acceptance status

This is a prospective acceptance contract. It defines what must be demonstrated later; it does not claim any implementation, test, run, result, or review gate has passed.

## Phase B completion gate

Phase B is complete only when all six files exist in this directory, are English, mutually consistent, and describe planning only:

- [ ] `requirements.md`
- [ ] `design.md`
- [ ] `tasks.md`
- [ ] `acceptance.md`
- [ ] `agent_plan.yaml`
- [ ] `decisions.md`

The package must also satisfy:

- [ ] no source, configuration, test, notebook, output, historical document/specification, Git metadata, or existing OpenSpec change is modified;
- [ ] the user-verified source commit SHA `aafe817365cb4068f167b398c776aff4c3b1f021` and no-change boundary are preserved;
- [ ] the untracked frozen notebook has a separately recorded and verified SHA-256; it is not conflated with the source commit SHA;
- [ ] the live frozen family is seeds `42`, `43`, and `44`, with seeds `43` and `44` recorded as running by user attestation within protected boundaries and activation prerequisites;
- [ ] no production value is invented beyond frozen notebook values;
- [ ] no real execution, publication, HPO, completion, or superiority claim is made;
- [ ] Phase C is explicitly limited to the user-authorized, reporting-only start boundary and is not claimed complete; Phase D remains explicitly blocked;
- [ ] the A–F future sequence is explicit;
- [ ] the rename is a plan only and is not executed.

## Scientific identity gate

- [ ] The public/model name is exactly `3D-ACDA — Three-Dimensional Anatomically Constrained Domain Adaptation`.
- [ ] The architecture contribution is described as the 3D encoder, 102-ROI representation/tokenization, independent refinement, learned attention, concept bottleneck with MRI-derived supervision, Jacobian anatomy consistency, dual latent/concept paths, and cross-cohort evaluation.
- [ ] MMD is identified as a standard latent UDA regularizer, not a novelty claim.
- [ ] The distinction between historical live-family evidence and future prospective requirements is explicit.

## Taxonomy and compatibility gate

- [ ] `mmd` displays as `3D-ACDA`.
- [ ] `source_only` displays as `3D-ACDA Source-Only`.
- [ ] `coral`, `cdan`, and `prototype_pseudo` remain explicit comparators.
- [ ] AAGN and FasterSNN remain independent baselines.
- [ ] Internal IDs, package `pada3dacb`, repository identity, historic paths, and stored output identities remain unchanged in Phase B.
- [ ] `prototype_pseudo` is comparator-only.
- [ ] `no_proto` and `no_pl` are legacy/supplementary, not primary.
- [ ] Aliases resolve only at read/report time.
- [ ] Alias resolution preserves requested spelling, canonical ID, output path, checkpoint identity, and stored manifests.
- [ ] Unknown, ambiguous, unapproved, and case-altered aliases fail closed.

## Binary and evaluation gate

Future execution must prove, without claiming that historical artifacts already do so:

- [ ] ADNI mapping is `CN -> CN` and `MCI/AD -> Impaired`.
- [ ] OASIS mapping is `CDR=0 -> CN` and `CDR>0 -> Impaired`, only after the Phase 18B OASIS provenance/semantics blocker passes with approved metadata and provenance semantics;
- [ ] the Phase 18B OASIS blocker evidence is separately recorded and a missing, stale, conflicting, or failed result maps to `BLOCKED`;
- [ ] Both `ADNI -> OASIS` and `OASIS -> ADNI` are represented.
- [ ] Target adaptation and target evaluation are disjoint by subject identity and assignment hash.
- [ ] No target labels enter training, adaptation, checkpoint selection, HPO, or candidate selection.
- [ ] Reporting aggregates at subject level.
- [ ] Undefined metrics and mapping/provenance failures are explicit and fail closed rather than inferred.

## Exact MMD regression gate — required for Phase C review and before Phase D activation

The future test evidence must be regression evidence against the existing implementation, not a replacement implementation. It must demonstrate:

- [ ] biased squared mixture-RBF estimator;
- [ ] diagonal terms included in within-domain terms;
- [ ] arithmetic averaging across the mixture bandwidths;
- [ ] float32 pairwise calculation;
- [ ] no embedding normalization;
- [ ] no median bandwidth heuristic;
- [ ] no final clamp;
- [ ] frozen live values `lambda_MMD=1` and `[1,2,4,8,16]` preserved where the live family is exercised;
- [ ] no source, equation, or behavior drift.

## Primary ablation and non-equivalence gate

These are Phase C implementation/review evidence prerequisites for Phase D activation, not prerequisites to starting the reporting-only Phase C layer:

- [ ] the primary prospective set is exactly `no_mmd`, `no_cons`, `no_concept`, `no_anat`, `mean_pool`;
- [ ] each candidate has exactly one intervention and an immutable resolved contract;
- [ ] `no_mmd` is explicitly `lambda_MMD=0`;
- [ ] `no_mmd` is not aliased to Source-Only;
- [ ] `no_mmd` non-equivalence is tested through target-loader/forward consumption, RNG/loader state, output and manifest identity, checkpoint identity, and resume behavior;
- [ ] learned attention remains canonical and `mean_pool` is a separate intervention;
- [ ] historical `no_proto` and `no_pl` are not silently promoted;
- [ ] Phase 17 blocked/invalid/equivalent dispositions remain enforced.

## Target-label and legacy comparator regression gate

- [ ] adaptation batches reject diagnosis labels and all forbidden supervision/artifact fields;
- [ ] target partitions are content-checked for subject intersection, not only aggregate hash equality;
- [ ] target evaluation is monitoring-only and cannot influence optimization or selection;
- [ ] CORAL behavior and identity regressions pass;
- [ ] CDAN behavior and identity regressions pass;
- [ ] prototype/pseudo behavior and identity regressions pass as an explicit comparator;
- [ ] AAGN behavior and identity regressions pass as an independent baseline;
- [ ] FasterSNN behavior and identity regressions pass as an independent baseline;
- [ ] no historical output path or ID is rewritten.

## Alias, configuration-hash, and checkpoint/resume gate

- [ ] A report can accept an approved display alias without changing the canonical internal ID.
- [ ] Alias and canonical requests produce the same canonical configuration hash.
- [ ] Requested spelling is retained as report metadata.
- [ ] Any changed intervention, canonical ID, inherited field, assignment, artifact, or model identity changes the canonical hash.
- [ ] A matching canonical identity resumes successfully in the future implementation.
- [ ] Alias spelling alone does not invalidate a matching checkpoint.
- [ ] A different candidate, method, config, assignment, artifact, or incompatible policy rejects resume before loading unsafe state.
- [ ] `no_mmd` and Source-Only checkpoint/resume identities are demonstrably distinct.

## Training and reporting gate

- [ ] Fixed epoch counts are declared before training.
- [ ] Training continues after a best checkpoint save.
- [ ] Source-validation macro-F1 is the only best-checkpoint criterion.
- [ ] Target monitoring is namespaced and cannot affect loss, gradients, optimizer, scheduler, checkpoint, HPO, resume, or candidate selection.
- [ ] Both transfer directions are reported.
- [ ] Subject-level aggregation is reported.
- [ ] Every result resolves to canonical ID, display label, alias decision, config hash, assignment hashes, artifact hashes, and checkpoint/resume identity.

## Activation and phase gates

### Gate C — reporting-only implementation start and review

**Status:** conditionally startable; no Phase C implementation, test, or review result is claimed complete in this package.

C may start only after the explicit user authorization already received is paired with a recorded start-boundary evidence record proving:

- [ ] the frozen source commit/tag reference and frozen notebook boundary are verified, with separate notebook SHA-256 evidence;
- [ ] the live notebook training path does not import or reach the modified reporting modules; and
- [ ] exclusive non-interference proof covers training, model, loss, adaptation, configuration, manifest generation, run directories, output paths, checkpoint/resume identity, and historical artifacts.

C implementation is limited to a pure display-name resolver and report-time projection layer. It must preserve canonical IDs, canonical configuration hashes, run directories, output paths, checkpoint/resume identity, and stored historical outputs; historical files must never be rewritten.

The exact MMD, target-isolation, comparator, `no_mmd`, configuration-hash, and checkpoint/resume evidence listed above is produced during C implementation/review and is required before D activation. It is not required to start C.

### Gate D — controlled execution and result freeze

**Status:** blocked in Phase B.

D/live execution may start only after C is implemented, reviewed, and all required C regressions pass; the live family finishes and results/manifests are frozen; the Phase 18B OASIS provenance/semantics blocker is explicitly recorded as passed; and a separate, explicit execution authorization artifact is recorded for Phase D. The authorization must not be inferred from C authorization, a review result, user intent, or a target outcome. D must stop before data access when any provenance, mapping, assignment, target firewall, configuration, Phase 18B, seed-attestation, or authorization check fails; every such failure is `BLOCKED`.

### Gate E — reporting

**Status:** blocked until D result freeze.

E may read only immutable, frozen results and must use report-time aliases without mutation.

### Gate evidence and ownership contract

Every gate has one owner, explicit prerequisites, a named evidence artifact, and a fail-closed result. The canonical machine-readable form is `agent_plan.yaml`; the acceptance mapping is:

| Gate | Owner | Prerequisites | Evidence artifact | Fail-closed result |
|---|---|---|---|---|
| Phase B content | Phase B documentation owner | six files present; documentation-only boundary | package manifest and content review record | missing, non-documentation, or inconsistent package -> `BLOCKED` |
| Scientific identity | scientific specification owner | Phase B content | identity/taxonomy review record | unsupported identity or novelty claim -> `BLOCKED` |
| Compatibility | compatibility and provenance owner | identity/taxonomy contract | alias/ID/path compatibility evidence | mutation or unresolved alias -> `BLOCKED` |
| Binary and provenance | evaluation and provenance owner | Phase 18 and Phase 18B authority records | binary mapping, partition, and provenance evidence | missing or conflicting mapping/provenance -> `BLOCKED` |
| Phase 18B OASIS provenance/semantics | Phase 18B authority and future execution owner | approved Phase 18B metadata/provenance inputs | Phase 18B approval/manifest evidence | missing, stale, conflicting, or failed evidence -> `BLOCKED` |
| Regression | future implementation owner | Phase 17, frozen notebook, and required test contracts | regression evidence bundle | any missing or failed regression -> `BLOCKED` |
| Phase C start/review | future implementation owner | explicit user authorization; verified frozen commit/tag/notebook boundary; import/reachability check; exclusive non-interference proof | Phase C start-boundary record; later C implementation/review evidence | missing boundary proof or scope drift -> `BLOCKED` |
| Phase D activation/live execution | future execution owner | C implementation/review and required regressions; live runs/results/manifests freeze; Phase 18B blocker; seed attestation; separate explicit D execution authorization | D execution authorization, Phase 18B evidence, seed-status record, regression bundle, and preflight manifest | any failed preflight or missing authorization -> `BLOCKED` |
| Phase E reporting | future reporting owner | D result freeze | immutable result-freeze and report provenance manifest | mutable/unfrozen input -> `BLOCKED` |
| Phase F rename | future compatibility owner | E evidence and separate rename approval | compatibility approval and migration review record | inferred or missing approval -> `BLOCKED` |

### Gate F — rename

**Status:** plan only.

F requires a separate approval and compatibility review. It cannot be inferred from the public name decision and is not executed by this package.

## Failure policy

Any unmet criterion is `BLOCKED`, not `PASS WITH ASSUMPTION`. The owner must record the missing evidence and stop the affected transition. Target outcomes cannot resolve configuration conflicts, upgrade historical records, or substitute for regression evidence.
