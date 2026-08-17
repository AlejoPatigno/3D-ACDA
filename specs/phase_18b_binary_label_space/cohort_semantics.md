# Cohort Semantics and OASIS Gate

**Status:** ADNI semantics are deterministic for planning; OASIS semantics are **BLOCKED**. No implementation or gate pass is claimed.

## ADNI canonical policy

The approved planning vocabulary is exact and closed:

```text
CN  -> CN (0)
MCI -> Impaired (1)
AD  -> Impaired (1)
```

Only canonical, well-formed source diagnosis tokens are accepted. Missing, unknown, malformed, unsupported, or out-of-domain labels are rejected. A diagnosis is never inferred from filenames, class order, visits, or another incidental field.

Original diagnoses remain distinct in provenance. Every included record must retain the original label, cohort, subject identity, source-row/visit identity, and mapping contract/version. A derived label without that provenance is invalid.

Every duplicate subject record is excluded from the approved cohort pending an explicit duplicate/longitudinal policy. If a subject has conflicting diagnoses, all records for that subject are excluded pending explicit policy. No precedence, recency, majority vote, or other guess resolves the conflict.

## OASIS repository evidence

The repository configuration currently contains:

```yaml
data:
  oasis:
    root: null
    metadata_csv: null
```

No approved real OASIS manifest is present for this package. CodeGraph inspection identified legacy `load_oasis_label_map` behavior:

1. Read a metadata CSV.
2. Require a column matching `ID`, `Subject ID`, `subject_id`, or `subject`, plus `CDR`.
3. Skip rows whose subject identifier cannot be extracted.
4. Skip rows with missing CDR.
5. Map numeric `CDR == 0` to historical `CN`.
6. Map every other numeric CDR to historical `AD`.

This behavior is legacy evidence only. It is not an approved OASIS binary contract and must not be used to claim scientific semantics, real cohort counts, or a publication-ready mapping.

## OASIS approval precondition

Before any production OASIS mapping or real OASIS split, maintainers must approve:

- canonical manifest path/identity and metadata-generation provenance;
- authoritative subject identifier;
- source diagnosis/CDR fields and accepted values;
- missing and out-of-domain policy;
- duplicate, conflicting, and longitudinal-record policy;
- conflict resolution or exclusion policy;
- unambiguous mapping into `CN` or `Impaired`;
- provenance fields and version/hash identity.

Until that policy is approved, missing, ambiguous, unknown, malformed, conflicting, unsupported, and out-of-domain records are rejected or excluded. No OASIS MCI category may be invented, and no value defaults to `Impaired`.

## Split implications

Because OASIS semantics are unresolved and no approved real manifests or hashes are available, split disposition is exactly `REGENERATE_BINARY_SPLITS_REQUIRED`. Reuse can be considered only after exact binary validity, provenance, leakage protection, stratification, and identity compatibility are proven.

## Current claims boundary

No OASIS mapping, real split, real hash, real class count, training/evaluation result, publication analysis, or binary freeze is claimed. Synthetic contract-test planning, if later added, must not be presented as OASIS evidence. New Phase 18B artifacts use `SUPERSEDED_BY_PHASE18B_BINARY_LABEL_SPACE` when discussing historical Phase 18 supersession; historical files remain untouched.
