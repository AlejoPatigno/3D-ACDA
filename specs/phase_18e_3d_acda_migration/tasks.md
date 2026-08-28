# Phase B — 3D-ACDA Migration Task Plan

## Task status

All tasks in this file are **planning tasks**. No implementation, run, test, result, publication, or rename task is complete. Phase B owns only this documentation package.

## Ownership rules

- One owner per task; no overlapping write ownership.
- Phase B documentation owner writes only `specs/phase_18e_3d_acda_migration/`.
- Future implementation owners must not modify the frozen notebook, existing MMD source, historical records, outputs, package/repository identity, or unrelated paths without a separately approved scope.
- A downstream owner cannot bypass a blocked prerequisite.
- Reviewers produce evidence; they do not silently resolve historical discrepancies.

## Dependency graph

```text
B0 boundary inventory
  -> B1 scientific identity and taxonomy
  -> B2 binary/provenance/reporting contract
  -> B3 MMD/comparator/ablation contract
  -> B4 alias/hash/checkpoint contract
  -> B5 acceptance and review-gate consolidation
  -> B6 Phase B package review

A freeze and live-run status --------------------+
                                                   v
B6 review + reporting-only start-boundary evidence
                                                   |
                                                   v
C0 reporting-only resolver/projection implementation [CONDITIONALLY STARTABLE]
  -> C1 contract and non-interference review evidence [REQUIRED BEFORE D]
  -> C2 implementation review [REQUIRED BEFORE D]
  -> Phase 18B OASIS provenance/semantics blocker [MUST PASS]
  -> separate explicit Phase D execution authorization [MUST BE RECORDED]
  -> verified live seed attestation for 42/43/44 [MUST PASS]
  -> D0 controlled live execution [BLOCKED]
  -> D1 result freeze [BLOCKED]
  -> E0 reporting/statistics [BLOCKED until D1]
  -> F0 rename execution [SEPARATE APPROVAL; NOT EXECUTED]
```

## Phase B work items

### B0 — Record the authoritative boundary

**Owner:** Phase B documentation owner  
**Depends on:** A freeze record  
**Deliverables:** references and decision record in this package  
**Acceptance:** the user-verified source commit SHA and the separately recorded untracked-notebook SHA-256 are distinguished; the live seed family is `42/43/44` with `43/44` recorded as running by user attestation within protected boundaries and activation prerequisites; and the no-change boundary/protected historical paths are stated without claiming additional notebook facts.

- [x] Identify `docs/EXPERIMENT_FREEZE_PRE_3D_ACDA.md` as the live-family authority.
- [x] Preserve the user-verified source commit `aafe817365cb4068f167b398c776aff4c3b1f021` as the source-tree anchor, separately from the untracked notebook SHA-256.
- [x] Identify live frozen seeds `42`, `43`, and `44`; record `43` and `44` as running by user attestation within protected boundaries and activation prerequisites, without claiming completion.
- [x] State that existing MMD source and behavior are unchanged.
- [x] State that the notebook, outputs, historical specs/docs, Git metadata, and package/repository identity are outside Phase B ownership.
- [x] State that no real run, result, publication, HPO, or rename is authorized.

### B1 — Define scientific identity and taxonomy

**Owner:** Scientific specification owner  
**Depends on:** B0  
**Deliverables:** `requirements.md`, `design.md`, `decisions.md`  
**Acceptance:** public naming and contribution claims are unambiguous and MMD is not claimed as novelty.

- [x] Record `3D-ACDA` as Three-Dimensional Anatomically Constrained Domain Adaptation.
- [x] Record the 3D encoder, 102-ROI representation/tokenization, independent refinement, learned attention, concept bottleneck with MRI-derived supervision, Jacobian anatomy consistency, dual paths, and cross-cohort evaluation.
- [x] Preserve `mmd`, `source_only`, `coral`, `cdan`, `prototype_pseudo`, `aagn`, and `faster_snn` internal IDs.
- [x] Define display aliases without changing IDs or paths.
- [x] Mark prototype/pseudo comparator-only and `no_proto`/`no_pl` legacy/supplementary.

### B2 — Define binary, cohort, and reporting contracts

**Owner:** Evaluation and provenance owner  
**Depends on:** B0, B1, Phase 18B  
**Deliverables:** `requirements.md`, `design.md`, `acceptance.md`  
**Acceptance:** both directions, prospective mappings, target separation, label isolation, and subject-level aggregation are explicit without historical compliance claims; the Phase 18B OASIS provenance/semantics blocker and its evidence artifact are required before Phase D/live execution.

- [x] Record ADNI `CN` versus `MCI/AD` mapping.
- [x] Record OASIS `CDR=0` versus `CDR>0` as prospective semantics subject to the approved Phase 18B provenance/semantics blocker; missing, stale, conflicting, or failed evidence maps to `BLOCKED`.
- [x] Require `ADNI -> OASIS` and `OASIS -> ADNI`.
- [x] Require disjoint target adaptation/evaluation assignments by subject identity and hash.
- [x] Prohibit target labels in training, adaptation, model selection, and checkpoint selection.
- [x] Require subject-level aggregation.
- [x] Preserve the distinction between prospective requirements and historical proof.

### B3 — Define MMD, comparators, and ablations

**Owner:** Method-contract owner  
**Depends on:** B0, B1, Phase 17, frozen notebook  
**Deliverables:** `requirements.md`, `design.md`, `decisions.md`  
**Acceptance:** exact audited MMD behavior, primary ablations, comparator roles, and `no_mmd` distinction are explicit.

- [x] Record biased squared mixture-RBF MMD with diagonals and arithmetic bandwidth averaging.
- [x] Record float32 pairwise behavior and the prohibition on normalization, median heuristic, and final clamp.
- [x] Record frozen notebook `lambda_MMD=1` and bandwidths `[1,2,4,8,16]` without inventing other production values.
- [x] Define primary prospective ablations: `no_mmd`, `no_cons`, `no_concept`, `no_anat`, `mean_pool`.
- [x] Require `no_mmd` as a distinct `lambda_MMD=0` run, not Source-Only.
- [x] Keep CORAL, CDAN, and prototype/pseudo as explicit comparators; AAGN and FasterSNN remain independent baselines.
- [x] Retain all known package/notebook/default/sampler discrepancies.

### B4 — Define aliases, hashes, and checkpoint/resume behavior

**Owner:** Compatibility and provenance owner  
**Depends on:** B1, B3  
**Deliverables:** `design.md`, `acceptance.md`, `decisions.md`  
**Acceptance:** aliases resolve at read/report time and cannot mutate output paths, IDs, hashes, checkpoint identity, or resume semantics.

- [x] Require requested spelling and canonical ID to be preserved in report metadata.
- [x] Require canonical config hashes independent of display alias spelling.
- [x] Require alias/config-hash coverage before activation.
- [x] Require checkpoint/resume coverage for matching canonical identity, alias variation, and mismatches.
- [x] Require explicit `no_mmd` output/manifest/RNG/checkpoint/resume non-equivalence evidence.
- [x] Define a rename plan only; do not execute it.

### B5 — Consolidate acceptance and review gates

**Owner:** Phase B documentation owner  
**Depends on:** B1, B2, B3, B4  
**Deliverables:** `acceptance.md`, `agent_plan.yaml`  
**Acceptance:** every gate has an owner, prerequisite, evidence, and fail-closed result.

- [x] Define the documentation-only Phase B completion gate.
- [x] Define scientific, binary/provenance, compatibility, regression, and activation gates.
- [x] Permit only the user-authorized, reporting-only Phase C start after its frozen-boundary, import/reachability, and non-interference evidence is recorded; keep the required tests/regressions as Phase C implementation/review evidence prerequisites for Phase D, not prerequisites to starting C; and explicitly block Phase D until live runs finish, results/manifests are frozen, Phase C regressions/review pass, the Phase 18B blocker passes, and separate Phase D authorization is recorded.
- [x] Record ownership and dependency graph.
- [x] Record A–F future sequence.
- [x] Give every gate an owner, prerequisites, evidence artifact, and fail-closed `BLOCKED` result mapping in `agent_plan.yaml` and the acceptance contract.

### B6 — Review the package

**Owner:** Independent specification reviewer; final decision owner: maintainer  
**Depends on:** B5  
**Deliverables:** review outcome outside this package if separately authorized  
**Acceptance:** reviewer confirms no runtime change, no historical rewrite, no invented configuration, complete discrepancy record, complete regression plan, and correct blockers.

- [ ] Review all six artifacts for internal consistency.
- [ ] Verify technical artifacts are in English.
- [ ] Verify no historical path or existing OpenSpec artifact was modified.
- [ ] Verify Phase C is only conditionally startable under the explicit user authorization and reporting-only boundary, while Phase D remains blocked.
- [ ] Verify rename language is plan-only.
- [ ] Verify no historical completion or scientific result claim is made.

## Future Phase C tasks — conditionally authorized, not complete

**Start condition:** Phase C may start now only when the explicit user authorization already received is paired with a recorded reporting-only start-boundary record proving:

1. the frozen source commit/tag reference and frozen notebook boundary are verified, with separate notebook SHA-256 evidence;
2. the live notebook training path does not import or reach the modified reporting modules; and
3. exclusive non-interference proof covers training, model, loss, adaptation, configuration, manifest generation, run directories, output paths, checkpoint/resume identity, and historical artifacts.

The C implementation scope is limited to a pure display-name resolver and report-time projection layer. It must preserve canonical IDs, canonical configuration hashes, run directories, output paths, checkpoint/resume identity, and stored historical outputs. New projections may resolve approved display aliases; historical files must never be rewritten.

The following are **not** prerequisites to starting C. They are implementation/review evidence prerequisites for Phase D activation:

- [ ] exact MMD numerical and behavioral regressions;
- [ ] target-label isolation and disjoint target adaptation/evaluation regressions;
- [ ] legacy comparator regressions;
- [ ] explicit `no_mmd` non-equivalence regression against Source-Only;
- [ ] alias/configuration-hash coverage; and
- [ ] checkpoint/resume coverage, including mismatch rejection.

Phase C is not complete merely because it may start. No C implementation, test, regression, or review result is claimed complete by this planning package.

Until the start-boundary record is complete:

- [ ] Do not modify runtime training, model, loss, adaptation, configuration, manifests, output paths, or historical artifacts.
- [ ] Do not change MMD source or defaults.
- [ ] Do not add or activate primary ablation runs.
- [ ] Do not change package/repository names.

After the start boundary is evidenced, C may implement only the reporting-only layer and must stop on any proof of runtime reachability or non-interference failure.

## Future Phase D tasks — blocked

**Activation condition:** C implementation is complete and reviewed; all required C regressions pass; the live family finishes and results/manifests are frozen; the Phase 18B OASIS provenance/semantics blocker is recorded as passed; the live seed-status attestation is verified; and a separate, explicit Phase D execution authorization artifact is recorded. Any missing, stale, conflicting, or failed prerequisite is `BLOCKED`.

- [ ] Pass and record the Phase 18B OASIS provenance/semantics blocker before any data access or activation.
- [ ] Record and verify the separate explicit Phase D execution authorization; do not infer it from C authorization, review, user intent, or target outcomes.
- [ ] Verify the frozen live seed family `42/43/44`, including the `43/44` user-attested running status within protected boundaries and activation prerequisites.
- [ ] Freeze approved binary mappings and provenance.
- [ ] Freeze both transfer directions and subject-level assignments.
- [ ] Validate disjoint target adaptation/evaluation manifests.
- [ ] Execute only the approved complete matrix.
- [ ] Preserve target-label isolation and source-validation macro-F1 checkpoint selection.
- [ ] Emit immutable output/config/checkpoint/resume manifests.
- [ ] Freeze results before reporting or comparison.

No Phase D task may use target outcomes to resolve a configuration discrepancy or choose a method.

## Future Phase E tasks — dependent on frozen results

- [ ] Resolve display aliases only at report/read time.
- [ ] Present primary ablations separately from explicit comparators and independent baselines.
- [ ] Report both directions and subject-level aggregation.
- [ ] Include configuration, assignment, artifact, checkpoint, and alias-resolution provenance.
- [ ] Make only claims supported by frozen results and approved statistical procedures.

## Future Phase F tasks — separate approval; not executed

- [ ] Inventory imports, entry points, package metadata, config names, docs, manifests, checkpoints, and paths.
- [ ] Define a compatibility window for `pada3dacb` and historical IDs/paths.
- [ ] Migrate new public-facing names without rewriting historical identities.
- [ ] Validate import compatibility, report aliases, config hashes, checkpoint resume, and legacy readers.
- [ ] Obtain explicit rename approval.

**No F task is executed by Phase B.**
