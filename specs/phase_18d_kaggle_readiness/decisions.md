# Phase 18D Decisions

## Decision ledger

| ID | Decision | Status | Consequence |
|---|---|---|---|
| D18D-01 | Phase 18D is Kaggle-only readiness evidence, not execution. | Resolved | No repository-side real training/evaluation or publication work. |
| D18D-02 | Current authority remains `docs/PHASE18B_REPORT.md` with status `PHASE18B_IMPLEMENTATION_COMPLETE_EXTERNAL_BLOCKED`. | Resolved | Phase 18D cannot claim Phase 18B closure or replace its blockers. |
| D18D-03 | Intended source URL is `https://www.kaggle.com/datasets/sanjukaggling/adnidataset`; observed display name is `ADNI_dataset`. | Resolved | Source identity is recorded, but runtime path remains unresolved. |
| D18D-04 | Kaggle mount discovery is dynamic and content-based under `/kaggle/input`. | Resolved | No guessed mount path or local path is allowed. |
| D18D-05 | `ad_new_2_19_2026.csv` is a candidate only. | Resolved | Schema and exact SHA-256 verification are required before use. |
| D18D-06 | ADNI mapping is `CN -> CN=0`, `MCI -> Impaired=1`, `AD -> Impaired=1`. | Resolved | Unsupported, missing, duplicate, or conflicting labels fail closed. |
| D18D-07 | The cohort is one canonical person and one initial MRI per person. | Resolved | Longitudinal duplicates and later MRIs are excluded under the approved Phase 4 selection rule. |
| D18D-08 | Only approved Phase 4 preprocessing may be reused. | Resolved | No new fit or repository-side model-ready generation. |
| D18D-09 | Existing concept/anatomy artifacts are reused and validated read-only. | Resolved | No refitting, regeneration, or label-migration rewrite. |
| D18D-10 | OASIS structural policy is fixed: CDR `{0, 0.5, 1, 2}`, `0 -> CN`, positives -> `Impaired`, 436 visits, 416 persons, 20 duplicates, 316/100 persons, 332/84 target partition, zero intersection. | Resolved | Any mismatch emits `BLOCKED_COHORT_MISMATCH`; no repair or alternate count. |
| D18D-11 | HMAC-SHA256 may pseudonymize person identity; only key ID/version is recorded. | Resolved | The HMAC key never enters evidence, logs, notebooks, or repository. |
| D18D-12 | Three standalone notebooks are required: 00 discovery, 01 materialization, 02 verification. | Resolved | Each has a no-training boundary and declared inputs/outputs. |
| D18D-13 | Materialization is resumable with per-subject statuses and hash-verified reuse. | Resolved | Corrupt or mismatched artifacts are blocked, not overwritten or accepted. |
| D18D-14 | Feasibility probes are synthetic-only. | Resolved | No subject training or scientific performance claims. |
| D18D-15 | Readiness states are `KAGGLE_NOTEBOOKS_READY_FOR_EXECUTION` followed by `KAGGLE_READINESS_EVIDENCE_IMPORTED`. | Resolved | No `REAL_RUN_READY*` state is valid. |
| D18D-16 | Authorization flags remain false and Phase 19 is forbidden. | Resolved | No state transition grants execution, freeze, publication, or Phase 19 authority. |
| D18D-17 | OpenSpec is the durable source because Engram persistence is degraded by a `mem_doctor` sync-payload defect. | Resolved | Do not repair Engram manually; repository OpenSpec files carry the plan. |

## Explicitly unresolved external values

These values must be supplied by the intended Kaggle runtime or a separately approved authority. The package records them as decisions rather than inventing defaults:

- discovered runtime-relative path for `ADNI_dataset`;
- exact selected path and SHA-256 for `ad_new_2_19_2026.csv`;
- approved Phase 4 contract identifier/version and output hashes as bound in the runtime;
- model-ready artifact root and per-person artifact hashes generated externally in Kaggle;
- source-fold seed/identity and exact source-fold counts;
- HMAC key material, which remains secret and must never be recorded;
- independent/native OASIS approval evidence and its receipt/identity;
- final evidence-root path used by repository import.

If any unresolved value is absent, ambiguous, or inconsistent, the pipeline remains blocked. No default path, seed, count, key, hash, or authorization is invented.

## Forbidden decisions

No decision in this package authorizes real execution, predictive evaluation, publication analysis, a binary freeze, lifecycle receipt fabrication, raw-ID handling, secret persistence, Engram repair, or Phase 19.
