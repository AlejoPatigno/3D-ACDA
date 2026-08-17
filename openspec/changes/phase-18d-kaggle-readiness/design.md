# Phase 18D Design

## Pipeline

```text
Kaggle /kaggle/input
  -> 00_discover_kaggle_inputs.ipynb
  -> [Phase 4 preprocessing-contract binding/verification]
  -> 01_materialize_kaggle_readiness.ipynb
  -> 02_verify_kaggle_readiness.ipynb
  -> external evidence bundle
  -> scripts/import_kaggle_readiness.py (read-only)
  -> focused tests + independent review
```

The pipeline stops at readiness evidence. It never trains, evaluates predictions, performs publication analysis, or runs Phase 19.

## Notebook contracts

| Notebook | Sole owner | Inputs | Outputs | Hard boundary |
|---|---|---|---|---|
| `00_discover_kaggle_inputs.ipynb` | `kaggle-discovery` | Kaggle runtime and source identity | `source_provenance.json`, `metadata_manifest.json`, `privacy_report.json` | No training/evaluation |
| `01_materialize_kaggle_readiness.ipynb` | `kaggle-materialization` | Notebook 00 evidence and verified Phase 4 contract | `subject_artifacts.jsonl`, `cohort_manifest.json` | Model-ready generation only in Kaggle; no training/evaluation |
| `02_verify_kaggle_readiness.ipynb` | `kaggle-verification` | Materialization evidence | `splits_manifest.json`, `concept_anatomy_reuse.json`, `readiness_state.json` (state: KAGGLE_READINESS_EVIDENCE_PRODUCED) | No training/evaluation/publication/Phase 19 |

Discovery enumerates contents recursively below `/kaggle/input`, finds candidates by observed basename/schema/signature, and records relative paths. It must fail closed on zero or multiple unresolved matches. A mount such as `/kaggle/input/ADNI_dataset` is not assumed.

## Canonical evidence

The bundle contains:

- `source_provenance.json` with source URL, observed dataset name, relative paths, byte sizes, exact lowercase SHA-256 values, notebook hash, and status;
- `metadata_manifest.json` with candidate path, exact SHA-256, schema fingerprint, required-column result, row count, and disposition;
- `subject_artifacts.jsonl` with opaque HMAC-SHA256 person tokens, key ID/version only, relative paths, sizes, hashes, selection rule, and status;
- `cohort_manifest.json` with binary labels, role, opaque person tokens, artifact hashes, and manifest hash;
- `splits_manifest.json` with source folds, target adaptation/evaluation sets, intersection proof, and target-firewall result;
- `privacy_report.json` with raw-ID/secret scan results and explicit false emissions;
- `concept_anatomy_reuse.json` with read-only identities, shapes, hashes, and approved Phase 4 contract identity;
- `readiness_state.json` with state, prerequisite statuses, evidence hashes, blocking reasons, and false authorization flags.

SHA-256 is computed over exact bytes and serialized as lowercase 64-character hexadecimal. Raw IDs and secrets never appear; HMAC keys are never recorded.

## Policy verification

ADNI accepts only `CN`, `MCI`, and `AD`, mapping to `CN=0`, `Impaired=1`, and `Impaired=1`. Canonicalization retains one person and one initial MRI under the approved Phase 4 selection rule; missing or ambiguous selection data blocks.

OASIS verification requires CDR `{0, 0.5, 1, 2}`, mapping `0 -> CN` and positive values to `Impaired`, 436 visits, 416 persons, 20 longitudinal duplicates, 316/100 canonical class counts, 332/84 target partitions, zero target intersection, and rejection of conflicting person-level values. Any mismatch emits `BLOCKED_COHORT_MISMATCH`.

Source folds and target partitions are person-level. Target adaptation and evaluation are fixed at 332 and 84 people with zero intersection. Target-evaluation people/data cannot enter adaptation, source folds, preprocessing fitting, or checkpoint selection. Phase 18D performs none of those operations; it verifies the firewall only.

Only approved Phase 4 preprocessing is reused. Existing `c_target`, `g_bar`, normalizer, ROI ordering, atlas, masks, and Jacobian artifacts are validated read-only. Label migration cannot refit or regenerate concept/anatomy outputs.

## Importer and state machine

The repository importer accepts an explicit evidence-root argument, reads canonical files, recomputes hashes, validates schemas/privacy/policies/reuse/firewall, and emits a deterministic report without writing evidence or generating artifacts. Synthetic tests cover pass and failure paths.

```text
KAGGLE_NOTEBOOKS_READY_FOR_EXECUTION
  -> KAGGLE_READINESS_EVIDENCE_PRODUCED   (after notebook 02)
  -> KAGGLE_READINESS_EVIDENCE_IMPORTED   (after importer validation)
```

No `REAL_RUN_READY*` state is valid. `authorized`, `real_execution_authorized`, `freeze_approved`, and `publication_authorized` remain false; `phase_19_forbidden` remains true.

## Ownership and closure

`kaggle-discovery`, `kaggle-materialization`, `kaggle-verification`, `repository-import`, `repository-tests`, `validation-owner`, and `independent-reviewer` each own distinct actions/files. Implementation closure requires focused tests, read-only validator validation, Ruff, `git diff --check`, and an independent review PASS. The reviewer cannot change state or authorization.