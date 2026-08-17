# Phase 18B Apply Progress

Status: implementation in progress; Phase 18B is not closed and no independent review pass is claimed.

## Scope boundary

- Primary task: `cn_vs_impaired` (`CN=0`, `Impaired=1`).
- Real ADNI/OASIS training and predictive evaluation were not run.
- No Phase 19 work was started.
- `freeze_approved`, `real_execution_authorized`, and `publication_authorized` remain false.
- Historical three-class artifacts/configurations remain compatibility surfaces and are not silently rewritten by binary runtime APIs.

## Focused batch 1: OASIS evidence and provenance repair

### RED

`pytest -q tests/phase_18b/test_binary_contracts.py`: **5 failed, 14 passed**. Failures covered missing accepted CDR counts/row-content hashes, phrase-only mapping acceptance, duplicate canonical-row behavior, and exclusion reasons.

### GREEN

`pytest -q tests/phase_18b/test_binary_contracts.py`: **19 passed** after code-cell structural notebook validation, complete-row hashing, duplicate/conflict handling, and de-identified evidence changes.

### Triangulate

Supplied inputs validated as metadata-only: **436 visits**, CDR values `0.0, 0.5, 1.0, 2.0`, counts `0=336`, `0.5=70`, `1=28`, `2=2`, source field `CDR`, exact CSV/notebook hashes recorded, no raw identifiers emitted. Independent scientific approval was still pending at this batch.

## Focused batch 2: binary data spine, firewall, and checkpoint identity

### RED

`pytest -q tests/phase_18b/test_binary_spine_batch2.py`: collection failed because the task-scoped binary dataset adapter was missing.

### GREEN

`pytest -q tests/phase_18b/test_binary_spine_batch2.py`: **6 passed**.

### Triangulate

`pytest -q tests/phase_18b`: **25 passed**. Historical compatibility subset: **52 passed**. Binary adapters preserve original ADNI labels, enforce exact target-adaptation keys, produce deterministic seed-42 split identities, and reject missing/tampered/historical/partial checkpoint metadata.

## Focused batch 3: five core method validate-only runtime

### RED

Focused collection initially failed because the task-scoped binary runtime module was missing.

### GREEN

`pytest -q tests/phase_18b/test_binary_core_runtime.py`: **7 passed**.

### Triangulate

`pytest -q tests/phase_18b`: **32 passed**. Core validate-only runtime covers source-only, CORAL, MMD, CDAN, and prototype-pseudo; PADA logits are `(B,2)`, concepts/alpha remain `(B,K)`, CDAN dimensions/gradients are checked, and historical configs are rejected.

## Focused batch 4: binary baselines and ablations

### RED

Focused collection initially failed because binary baseline/ablation entry points were missing.

### GREEN

`pytest -q tests/phase_18b/test_binary_baselines_ablations.py`: **7 passed**.

### Triangulate

`pytest -q tests/phase_18b`: **39 passed**. Historical baseline/ablation compatibility subset: **76 passed**. AAGN, FasterSNN, and all six approved ablations are task-scoped binary validate-only surfaces; excluded variants remain blocked.

## Focused batch 5: binary prediction export and Phase 15 evaluation

### RED

Focused collection initially failed because the binary aggregation entry point was missing.

### GREEN

`pytest -q tests/phase_18b/test_binary_evaluation_pipeline.py`: **7 passed**.

### Triangulate

`pytest -q tests/phase_18b`: **46 passed**. Historical Phase 15 compatibility subset: **45 passed**. Binary export/evaluation uses fixed CN/Impaired order, 2x2 confusion, nullable undefined metrics, and source-validation macro-F1 checkpoint selection. `python scripts/evaluate_binary.py --validate-only` completed deterministically without opening real data.

## Focused batch 6: binary Phase 16 concept evaluation

### RED

Focused collection initially failed because the binary concept aggregation entry point was missing.

### GREEN

`pytest -q tests/phase_18b/test_binary_concept_evaluation.py`: **7 passed**.

### Triangulate

`pytest -q tests/phase_18b`: **53 passed**. Historical evaluation compatibility subset: **45 passed**. Binary class profiles expose only CN/Impaired and reuse c_target, g_bar, normalizer, ROI ordering, atlas, masks, and Jacobian identities without regeneration.

## Focused batch 7: critical prediction/checkpoint/provenance repairs

### RED

`pytest -q tests/phase_18b/test_binary_batch7_repairs.py`: **7 failed**. Failures reproduced undefined schema fields, collector/metrics schema mismatch, duplicate evaluator behavior, metadata-free checkpoint acceptance, OASIS caller-boolean admission, wildcard exports, and unenforced `--validate-only`.

### GREEN

`pytest -q tests/phase_18b/test_binary_batch7_repairs.py`: **7 passed**.

### Triangulate

`pytest -q tests/phase_18b`: **60 passed**. Historical data/firewall/checkpoint subset: **52 passed**. Historical evaluation subset: **45 passed**. Metadata-free binary checkpoints now fail closed; prediction export and evaluation frames are separated; the concept CLI requires explicit `--validate-only`.

## Focused batch 8: deterministic OASIS person-level policy

### RED

`pytest -q tests/phase_18b/test_binary_batch8_oasis_policy.py`: **5 failed**. Failures reproduced visit-level grouping, missing person-level conflict handling, open-ended CDR acceptance, missing original metadata provenance, and missing artifact counts.

### GREEN

`pytest -q tests/phase_18b/test_binary_batch8_oasis_policy.py`: **6 passed**.

### Triangulate

`pytest -q tests/phase_18b`: **66 passed**. The supplied metadata validates to **436 visits**, **416 canonical persons**, and **20 longitudinal duplicate exclusions**. Person-level split identities are disjoint. The accepted CDR domain is closed to the observed canonical values `{0.0, 0.5, 1.0, 2.0}`; malformed, missing, negative, nonfinite, and out-of-domain values are rejected. OASIS admission requires structured evidence with `evidence_verified=true`, `semantics_approved=true`, exact CSV/notebook hashes, and matching de-identified subject provenance. No raw identifiers were emitted. Independent scientific and mathematical review are still required before closure.

## Current gate

Phase 18B remains open. Required next actions are: rerun independent scientific and mathematical reviews against the person-level policy; repair any surviving findings; update truthful OpenSpec/state/report artifacts; run the full post-migration repository validation; obtain the native lifecycle result if available; and only then close with `PHASE18B_COMPLETE_BINARY_MIGRATION_APPROVED` if every acceptance criterion passes. Otherwise record an explicit blocked state.

## Focused batch 9: security-bound OASIS admission, split integrity, and safe checkpoint loads

### RED

`python -m pytest -q tests/phase_18b`: **53 passed, 18 failed**. Failures reproduced missing explicit 32-byte synthetic OASIS keys, the incomplete records adapter call after the attestation signature change, unsafe `weights_only=False` binary checkpoint loading, and pending duplicate/approved-universe split validation.

### GREEN

`python -m pytest -q tests/phase_18b`: **71 passed**. Synthetic fixtures use only `b"phase18b-test-subject-hmac-key!!"`; production OASIS admission remains fail-closed without an external key. `binary_record_from_subject_record` now requires an exact `OasisEvidence` plus validator-bound `OasisApprovalAttestation`, binary checkpoint paths load with `weights_only=True` and `map_location="cpu"`, and duplicate target/source lists plus approved target person-universe binding are enforced.

### Triangulate

`python -m pytest -q tests/phase_18b/test_binary_batch7_repairs.py tests/phase_18b/test_binary_batch9_security.py`: **12 passed**. Negative coverage confirms absent or mapping-based OASIS evidence, caller booleans, duplicate person hashes, incomplete approved universes, metadata-free checkpoints, and non-weights-only checkpoint loads are rejected. HMAC key ID/version remain artifact metadata only; the key itself is not persisted or exposed.

## Focused batch 10: behaviorally effective binary ablation interventions

### RED

`python -m pytest -q tests/phase_18b/test_binary_batch10_ablation_effects.py`: collection failed because the task-scoped binary ablation plan and effective loss-component API were missing from `pada3dacb.binary`.

### GREEN

`python -m pytest -q tests/phase_18b/test_binary_batch10_ablation_effects.py`: **9 passed** after adding the explicit six-candidate binary intervention plan, pure loss-component masking, validate-only effective-component reporting, architecture identity reporting for `mean_pool`, and task-scoped UDA consumption.

### Triangulate

`python -m pytest -q tests/phase_18b`: **80 passed**. Differential coverage confirms `no_proto`, `no_pl`, `no_cons`, `no_concept`, and `no_anat` zero only their approved effective components (with `no_concept` disabling both concept supervision and classifier-concept contributions), unrelated components remain unchanged, `mean_pool` preserves losses while changing architecture identity, excluded variants remain rejected, and every approved candidate remains a binary two-logit path. The existing pytest cache warning (`WinError 5`, access denied) is environmental and did not affect results.

## Focused fixture and artifact repair after batch 9 hardening

### RED

`python -m pytest -q tests/phase_18b`: **76 passed, 4 failed**. The failures were successful approval fixtures still using pending scientific review status and missing person-level artifact provenance fields.

### GREEN

`python -m pytest -q tests/phase_18b`: **80 passed** after updating successful fixtures to use `scientific_review_status="PASS"` with `semantics_approved=True`, forwarding validator-bound approvals for the exact approved `OasisEvidence`, and adding `canonical_accepted_persons=416` plus `person_intersection_count=0` to the person-level partition provenance.

### Triangulate

`python -m pytest -q tests/phase_18b/test_binary_batch7_repairs.py tests/phase_18b/test_binary_batch8_oasis_policy.py tests/phase_18b/test_binary_batch9_security.py`: **18 passed**. Negative coverage remains active for pending/mapping-based evidence, missing or unvalidated attestations, caller boolean admission, duplicate person hashes, incomplete approved universes, and unsafe checkpoint loads. Synthetic OASIS fixtures continue to use the explicit 32-byte test HMAC key; only the HMAC key ID/version remain in artifacts.

## Mechanical Ruff cleanup and focused validation

- `python -m ruff check .`: **All checks passed!**
- `python -m pytest -q tests/phase_18b`: **80 passed, 1 warning in 11.44s**.
  - Warning: `PytestCacheWarning: could not create cache path C:\\Users\\LOQ\\Desktop\\PADA-3DACB\\.pytest_cache\\v\\cache\\nodeids: [WinError 5] Acceso denegado`.

## Publication runtime boundary relocation

### RED

`python -m pytest -q tests/phase_18b/test_binary_runtime_boundary.py`: **1 failed, 1 passed**. The dependency-boundary assertion observed forbidden runtime imports in `src/pada3dacb/publication/binary_runtime.py`.

### GREEN

`python -m pytest -q tests/phase_18b/test_binary_runtime_boundary.py`: **2 passed, 1 warning in 7.81s**. The historical `pada3dacb.publication.binary_runtime` import path remains available through a lazy facade, while the implementation is located at `pada3dacb.tasks.binary_runtime`.

### Triangulate

- `python -m pytest -q tests/phase_18b`: **82 passed, 1 warning in 43.22s**.
- `python -m pytest -q tests/phase_18/test_integration.py::test_publication_package_and_clis_have_no_real_runtime_import_boundary`: **1 passed, 1 warning in 0.40s**.
- `python -m ruff check .`: **All checks passed!**
- The warnings were existing Windows `PytestCacheWarning` failures while creating `.pytest_cache`; they did not affect test results.

## Final implementation and closure batch: external-blocked state

### Scope and implementation result

The task-scoped binary implementation is complete under explicit maintainer instruction. Evidence covers the data spine/firewall/checkpoint boundary, five core methods, AAGN/FasterSNN, six behaviorally effective ablations, prediction/evaluation, concept routing/reuse, three-class rejection, and the task-scoped runtime boundary. This does not close Phase 18B or authorize real execution.

The supplied OASIS evidence is recorded as 436 visits, 416 canonical persons, 20 longitudinal duplicates, canonical person counts of 316 CN and 100 Impaired, CDR domain `{0, 0.5, 1, 2}`, target planning counts of 332 adaptation and 84 evaluation persons, and person intersection zero. CSV SHA256 is `b223c39f83d811356675e8711e9906b1cba95ea1a110f3117a61923a72d1d1f1`; notebook SHA256 is `588bc2a6c214fd99e2900dd45357ec2fa235cbe1670a1ab99c87c5bf2726e41b`. The HMAC key ID may be retained, but the key is never persisted.

The ADNI mapping contract remains `CN->CN`, `MCI->Impaired`, and `AD->Impaired`. The actual ADNI canonical manifest/source assignments are unavailable: `configs/data/adni.yaml` has null root/metadata paths and no repository ADNI manifest exists. No ADNI counts or hashes are claimed.

### Final validation evidence

- `python -m pytest -q tests/phase_18b -p no:cacheprovider --basetemp=C:/p18b-focused-final5`: exit 0, **83 passed**, one environmental cache warning, 79.97s.
- `python -m pytest -q -p no:cacheprovider --basetemp=C:/p18b-full-final5`: exit 0, **1408 passed**, six warnings, 509.35s (8:29). Warnings were four sklearn single-class ROC-AUC warnings and two PyTorch degrees-of-freedom warnings.
- `python -m pip install -e .`: exit 0; import/version validation exit 0; version `0.1.0`.
- `python -m ruff check .`: exit 0, `All checks passed!`.
- `git diff --check`: exit 0.
- `python scripts/evaluate_binary.py --validate-only`: exit 0.
- `python scripts/evaluate_binary_concepts.py --validate-only`: exit 0.
- The real-run authorization checker exited 1 and failed closed.

### Final review and authorization state

The final independent mathematical review passed, including the mathematical contracts and empty-kappa null policy. The final independent scientific/provenance review is **BLOCKED** because the ADNI canonical manifest/source assignments are absent and no cryptographically/native-authority-bound OASIS approval exists. OASIS structural mapping is verified, but `semantics_approved=false` remains correct.

`freeze_approved=false`, `real_execution_authorized=false`, `publication_authorized=false`, and `phase_19_forbidden=true` remain unchanged. No real training, real predictive evaluation, preprocessing rerun, concept/anatomical regeneration, publication analysis, or Phase 19 occurred. Supplied raw CSV/notebook inputs remain external/untracked and must not be committed; only de-identified artifacts are Phase 18B outputs.

### Native lifecycle evidence

No Phase 18B native receipt exists. The previous lifecycle status attempt timed out with `mutation_outcome=not_started`. No receipt is fabricated, edited, or claimed.

### Closure disposition

The truthful closure state is `PHASE18B_IMPLEMENTATION_COMPLETE_EXTERNAL_BLOCKED`. Phase 18B is not closed. Remaining work requires the authoritative ADNI manifest/source assignments, cryptographically/native-authority-bound OASIS approval, independent scientific/provenance review, binary split validation or regeneration, native lifecycle closure, and separate binary freeze approval.
