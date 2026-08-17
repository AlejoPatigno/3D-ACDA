# Phase 18D Kaggle Readiness

## Summary

Create a Kaggle-only readiness-evidence path for the deferred ADNI inputs. The path discovers inputs by observed contents, materializes privacy-preserving hash evidence, verifies the closed ADNI/OASIS policies and person-level partitions, validates reuse of approved Phase 4 and concept/anatomy artifacts, and provides a read-only repository importer with synthetic focused tests.

## Authority and status

`docs/PHASE18B_REPORT.md` remains authoritative and its status remains `PHASE18B_IMPLEMENTATION_COMPLETE_EXTERNAL_BLOCKED`. This change does not close Phase 18B, approve a binary freeze, or change any authorization flag.

## In scope

- Three standalone Kaggle notebooks: `00` discovery, `01` materialization, `02` verification.
- Dynamic discovery below `/kaggle/input` by contents; no guessed mount path.
- Intended source URL `https://www.kaggle.com/datasets/sanjukaggling/adnidataset` and observed dataset name `ADNI_dataset`.
- Candidate metadata `ad_new_2_19_2026.csv`, requiring runtime schema and exact SHA-256 verification.
- Exact source, metadata, subject, cohort, split, privacy, and readiness outputs with no raw IDs or secrets.
- ADNI binary mapping, one-person/one-initial-MRI policy, approved Phase 4 reuse, OASIS verification, `BLOCKED_COHORT_MISMATCH`, and concept/anatomy validation without refit/regeneration.
- Source folds, fixed target adaptation/evaluation partitions, person-level disjointness, and target firewall evidence.
- Resumable per-subject materialization and hash-verified reuse.
- Synthetic-only probes and a repository-side read-only `scripts/import_kaggle_readiness.py` validator with focused tests.
- States `KAGGLE_NOTEBOOKS_READY_FOR_EXECUTION` and `KAGGLE_READINESS_EVIDENCE_IMPORTED` only.

## Out of scope

Real training, real predictive evaluation, publication analysis, repository-side model-ready generation, raw identifiers, secrets, authorization, freeze approval, lifecycle repair, and Phase 19 are forbidden.

## Durable artifact note

OpenSpec is the durable source for this change because Engram persistence is degraded by the reported `mem_doctor` sync-payload defect. Engram was not repaired. A best-effort planning decision was saved when available.
