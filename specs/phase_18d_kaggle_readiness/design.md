# Phase 18D Kaggle Readiness Design

## Design summary

The design is a one-way evidence pipeline:

`Kaggle discovery -> resumable materialization -> privacy/provenance manifests -> OASIS and split verification -> read-only repository import -> independent review`

It never crosses into training, predictive evaluation, publication analysis, or Phase 19. Kaggle notebooks are the only place where external input discovery and model-ready generation may occur. Repository code consumes only a de-identified evidence bundle and validates it without mutation.

## Components and ownership

| Component | Location | Sole owner | Responsibility | Depends on |
|---|---|---|---|---|
| Discovery notebook | Kaggle notebook `00_discover_kaggle_inputs.ipynb` | `kaggle-discovery` | Enumerate `/kaggle/input` by contents; select and hash candidates; emit source/privacy evidence | Kaggle runtime, source URL |
| Materialization notebook | Kaggle notebook `01_materialize_kaggle_readiness.ipynb` | `kaggle-materialization` | Resume/reuse artifacts, apply canonical person/initial-MRI policy, reuse Phase 4 preprocessing, write manifests | Discovery evidence, approved Phase 4 contract |
| Verification notebook | Kaggle notebook `02_verify_kaggle_readiness.ipynb` | `kaggle-verification` | Verify OASIS, mappings, folds, target firewall, concept/anatomy reuse, privacy, and state | Materialization evidence |
| Repository validator | `scripts/import_kaggle_readiness.py` | `repository-import` | Read-only validation/import of a complete evidence bundle; no generation or authorization | Evidence bundle, schemas |
| Focused tests | `tests/phase_18d/` | `repository-tests` | Synthetic contract and negative-case protection | Validator interfaces, synthetic fixtures |
| Independent review | Review artifact outside implementation ownership | `independent-reviewer` | Verify scope, evidence, security/privacy, state, and no prohibited actions | All implementation artifacts and validation output |

No action has two owners. Owners may consume another component's outputs but may not rewrite them.

## Evidence layout

The Kaggle notebooks write an externally retained bundle with this logical layout:

```text
<evidence-root>/
  source_provenance.json
  metadata_manifest.json
  subject_artifacts.jsonl
  cohort_manifest.json
  splits_manifest.json
  privacy_report.json
  concept_anatomy_reuse.json
  readiness_state.json
  notebooks/
    00_discover_kaggle_inputs.ipynb
    01_materialize_kaggle_readiness.ipynb
    02_verify_kaggle_readiness.ipynb
  artifacts/
    <opaque-subject-token>/...
```

The evidence-root is an external value. It is never guessed or committed as a machine-specific path. Repository import accepts an explicitly supplied path and reads it only.

## Discovery algorithm

1. Enumerate files recursively below `/kaggle/input`.
2. For each file, capture relative path, byte size, content signature, and lowercase SHA-256.
3. Identify candidate `ad_new_2_19_2026.csv` files by basename and schema, not by a fixed directory.
4. Check that the selected source metadata is consistent with the intended URL and observed dataset name `ADNI_dataset`.
5. If zero or multiple candidates remain, emit a blocking reason instead of selecting by path order.
6. Emit `source_provenance.json`, `metadata_manifest.json`, and `privacy_report.json` before materialization.

No discovery function accepts a configured mount path. A test must prove that the same content succeeds under different synthetic mount layouts.

## Canonicalization and materialization

The materializer processes canonical persons, not visits. It applies the closed ADNI mapping (`CN=0`, `MCI=1`, `AD=1`) and rejects unsupported or conflicting metadata. It selects exactly one initial MRI per person according to the approved Phase 4 metadata rule and records the decision. No later visit or MRI is silently substituted.

Each materialization unit is an opaque HMAC-SHA256 subject token. The external HMAC key is injected into the Kaggle runtime, identified only by key ID/version, and is never placed in notebooks, logs, JSON, environment dumps, or repository files. Artifact reuse requires all of:

- expected opaque token and relative path;
- exact artifact SHA-256 and byte size;
- approved preprocessing contract identity;
- privacy scan pass;
- prior status `materialized` or `reused_hash_verified`.

A mismatch changes the subject status to `blocked` or `failed` with a reason and does not overwrite the artifact.

## OASIS verification

The verifier independently recomputes person canonicalization and compares the supplied evidence with the approved values from Phase 18B. It checks the CDR mapping, 436/416/20 arithmetic, 316/100 class counts, 332/84 target partition, zero target intersection, conflict rejection, and HMAC policy. Any difference is a hard `BLOCKED_COHORT_MISMATCH`; there is no repair mode.

The OASIS evidence is an input to verification, not a new source of labels for ADNI. It cannot alter ADNI mapping or authorize execution.

## Splits and firewall

Source folds are generated from opaque person tokens using a recorded deterministic split identity. Target adaptation and target evaluation are fixed partitions with 332 and 84 persons and zero overlap. The manifest includes sorted token sets, per-set SHA-256, and an explicit intersection proof.

The target firewall is represented as a validator rule: target-evaluation tokens and any target-evaluation-derived data must not appear in adaptation, source folds, preprocessing-fit inputs, or checkpoint-selection inputs. A violation is blocking. Phase 18D only constructs and verifies manifests; it does not fit preprocessing, train, select checkpoints, or evaluate.

## Preprocessing and concept/anatomy reuse

The manifest records the approved Phase 4 preprocessing contract identity and output hashes. The repository validator checks that the contract is known and that required output identities match. It rejects a bundle that contains a new fit, a regenerated label-migrated concept/anatomy artifact, or an unexplained identity change.

Concept/anatomy validation is read-only and checks `c_target`, `g_bar`, normalizer, ROI ordering, atlas, masks, and Jacobian identities, shapes, and hashes. Reuse is evidence-only; no refitting, regeneration, or label migration is performed by this change.

## State machine

```text
KAGGLE_NOTEBOOKS_READY_FOR_EXECUTION
  -> KAGGLE_READINESS_EVIDENCE_IMPORTED
```

The transition requires all manifest hashes, privacy checks, mappings, OASIS checks, split/firewall checks, and independent review evidence to pass. Any failure remains blocking and cannot advance the state. `REAL_RUN_READY*` is not a valid state in this state machine. Authorization flags remain false on every state.

## Repository validator behavior

`import_kaggle_readiness.py` is read-only with respect to the evidence root and repository source. It:

1. accepts an explicit evidence-root argument;
2. loads only the canonical evidence files;
3. validates JSON/JSONL schema and recomputes byte hashes;
4. scans for raw IDs, secrets, HMAC keys, guessed mount claims, training/evaluation/publication/Phase 19 markers;
5. verifies ADNI/OASIS mappings, person cardinality, partitions, and target firewall;
6. validates Phase 4 and concept/anatomy reuse identities;
7. validates state transition and false authorization flags;
8. emits a deterministic pass/fail report and never creates model-ready artifacts, training results, or authorization.

The validator must not overwrite an existing evidence bundle or silently normalize invalid data.

## Failure taxonomy

| Failure | Required disposition |
|---|---|
| No or ambiguous Kaggle candidate | blocked discovery |
| Hash/schema mismatch | blocked provenance |
| Raw ID or secret found | blocked privacy |
| Unsupported/conflicting ADNI assignment | blocked mapping |
| OASIS mapping/count/person mismatch | `BLOCKED_COHORT_MISMATCH` |
| Subject artifact hash mismatch | blocked materialization |
| Person overlap or target-firewall violation | blocked splits |
| New/refit/regenerated concept/anatomy artifact | blocked reuse |
| Training, predictive evaluation, publication, or Phase 19 marker | forbidden-action failure |
| Invalid state or true authorization flag | blocked state |

## Review gate

An independent reviewer must inspect the final diff, requirements/design traceability, validator behavior, focused negative tests, exact validation output, and state/authorization fields. The implementation cannot be declared closed until the reviewer records PASS. The reviewer may not change evidence, state, source, or authorization flags.
