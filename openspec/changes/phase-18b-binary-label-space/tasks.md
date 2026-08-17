# Phase 18B Binary Label Space Tasks

**Current status:** `PHASE18B_IMPLEMENTATION_COMPLETE_EXTERNAL_BLOCKED`

Implementation and repository validation evidence is complete. Phase 18B remains open and is not scientifically approved, frozen, natively closed, authorized for real execution, or authorized for publication. The intended ADNI source identity is now known, but the mounted path, metadata verification, external model-ready artifacts, provenance, and lifecycle gates remain deferred or blocked.

## Current maintainer decision

- Intended source: `https://www.kaggle.com/datasets/sanjukaggling/adnidataset` (`ADNI_dataset` on the Kaggle page).
- Mounted filesystem path: resolve inside Kaggle; do not invent a local path.
- `ad_new_2_19_2026.csv`: metadata candidate only; verify schema and hash before treating it as a canonical manifest.
- `ADNI_MODEL_READY_ROOT`: intentionally deferred while model-ready artifacts are generated externally in Kaggle.

## Specification package

- [x] Maintain the normative binary label-space specification at `openspec/changes/phase-18b-binary-label-space/specs/label-space/spec.md`.
- [x] Maintain fixed binary vocabulary and deterministic canonical ADNI mapping: `CN -> CN`, `MCI -> Impaired`, `AD -> Impaired`.
- [x] Maintain provenance, rejection, duplicate/conflict exclusion, and target-label-firewall contracts.
- [x] Maintain the OASIS structural evidence contract and explicit pending-approval policy.
- [x] Maintain tensor, CDAN-gradient, prototype/pseudo, checkpoint, prediction, evaluation, identity, sensitivity, migration, and freeze-impact contracts.
- [x] Maintain authorization and historical immutability boundaries.

## Implemented engineering scope

- [x] Implement the binary data spine, person-level OASIS policy, target firewall, and checkpoint identity boundary.
- [x] Implement the five core method surfaces: source-only, CORAL, MMD, CDAN, and prototype-pseudo.
- [x] Implement binary AAGN and FasterSNN task-scoped surfaces.
- [x] Implement all six approved ablations with behaviorally effective loss-component interventions; excluded variants remain rejected.
- [x] Implement binary prediction/evaluation contracts, including fixed class order, 2x2 confusion, nullable undefined metrics, and source-validation macro-F1 selection.
- [x] Implement Phase 16 concept routing/reuse compatibility and three-class rejection.
- [x] Keep the publication/runtime boundary task-scoped and validate-only for this work package.
- [x] Preserve historical three-class artifacts and reject historical identity collisions or partial checkpoint loads.

## Validation evidence

- [x] Focused Phase 18B suite: **83 passed**.
- [x] Full repository suite: **1408 passed**.
- [x] Packaging/import/version validation, Ruff, and `git diff --check` passed.
- [x] Both binary validate-only CLIs passed.
- [x] Real-run authorization checker failed closed as required.
- [x] Final independent mathematical review passed, including mathematical contracts and empty-kappa null policy.

## External authority and closure work — incomplete

- [ ] In Kaggle, resolve the mounted path for `ADNI_dataset`; no local mount path may be invented. `configs/data/adni.yaml` remains unbound.
- [ ] Bind `ad_new_2_19_2026.csv` in the intended runtime and verify its schema and hash; it is not yet an approved canonical manifest.
- [ ] Generate or bind model-ready artifacts externally in Kaggle and record authoritative per-person hashes and provenance. `ADNI_MODEL_READY_ROOT` remains deferred; absent or fabricated artifacts must not be hashed.
- [ ] Obtain cryptographically/native-authority-bound approval of the supplied OASIS metadata, mapping, person policy, and preprocessing provenance.
- [ ] Complete an independent scientific/provenance review after the missing inputs are supplied. The current scientific/provenance review is **BLOCKED**.
- [ ] Resolve the OASIS gate; structural mapping is verified, but `semantics_approved=false` remains correct.
- [ ] Prove binary cohort manifest and split reuse valid against approved inputs or regenerate binary manifests/splits and record exact person-level identities/hashes.
- [ ] Obtain a native Phase 18B lifecycle result. No Phase 18B receipt exists; the previous status attempt timed out with `mutation_outcome=not_started`; do not retry or fabricate a receipt.
- [ ] Create and separately approve a binary freeze identity without changing historical Phase 18 files or receipt state.
- [ ] Explicitly authorize any later real execution or publication work; this task does not grant that authorization.

## Prohibited activities

- [x] Do not run real ADNI/OASIS training or evaluation, preprocessing, concept/anatomy regeneration, or publication analysis.
- [x] Do not create real manifests, real split hashes, real result claims, per-person model-ready hashes for absent/fabricated artifacts, or binary freeze artifacts.
- [x] Do not invent the Kaggle-mounted filesystem path or treat the metadata candidate as canonical before schema/hash verification.
- [x] Do not execute Phase 19.
- [x] Do not edit receipts, native lifecycle state, historical Phase 18 authorization/freeze, or unrelated dirty workspace; do not retry the prior native lifecycle timeout.
- [x] Do not claim Phase 18B complete, a binary freeze hash, native lifecycle PASS, `REAL_RUN_READY`, scientific approval, publication authorization, or real execution.

## Next maintainer action

In Kaggle, resolve the mounted `ADNI_dataset` path, verify `ad_new_2_19_2026.csv` by schema and hash, generate the model-ready artifacts, and return authoritative per-person provenance/hashes. Do not perform real training, predictive evaluation, preprocessing, concept/anatomy regeneration, Phase 19, or publication analysis during this handoff.

## Explicit closure state

`[ ] Phase 18B closed` — intentionally unchecked. The truthful current state is implementation-complete but externally blocked: `PHASE18B_IMPLEMENTATION_COMPLETE_EXTERNAL_BLOCKED`.
