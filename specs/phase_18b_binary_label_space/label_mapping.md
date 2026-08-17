# Binary Label Mapping Contract

**Status:** ADNI semantics are deterministic for planning; OASIS mapping is blocked. No implementation or gate pass is claimed.

## Fixed vocabulary

| ID | Name | Meaning in this task |
|---:|---|---|
| 0 | `CN` | Cognitively normal task class |
| 1 | `Impaired` | Task grouping for approved non-CN source diagnoses |

`Impaired` is a publication-task label. It does not assert diagnostic equivalence between MCI and AD.

## ADNI mapping

Only these canonical source labels are supported:

| Original label | Derived name | Derived ID | Provenance requirement |
|---|---|---:|---|
| `CN` | `CN` | 0 | retain original `CN` |
| `MCI` | `Impaired` | 1 | retain original `MCI` |
| `AD` | `Impaired` | 1 | retain original `AD` |

The source label is never overwritten. The minimum derived record is:

```yaml
original_label_name: CN | MCI | AD
binary_label_name: CN | Impaired
binary_label: 0 | 1
mapping_contract: phase-18b-binary-v1
```

Implementations, if later authorized, must also retain cohort, subject ID, source-row/visit identity, and derivation provenance. A derived label without original provenance is invalid.

## Deterministic exclusion policy

Missing, unknown, malformed, unsupported, and out-of-domain source labels are rejected. Duplicate subject records are excluded from the approved cohort pending an explicit duplicate/longitudinal policy. If a subject has conflicting diagnoses, all records for that subject are excluded pending explicit policy. No precedence, recency, majority vote, filename, class order, or other guess is allowed.

## OASIS boundary

No final OASIS mapping is specified. Current repository evidence says the configuration has null root and metadata paths. The legacy loader requires an ID/Subject ID-compatible field and CDR, skips missing CDR, maps CDR zero to CN, and maps every other numeric CDR to historical AD. That is evidence only and cannot be adopted as binary semantics.

An approved OASIS mapping must identify canonical metadata, source value domain, missing/out-of-domain treatment, duplicate/conflict/longitudinal policy, and derivation provenance. Until approved, ambiguous, unknown, missing, malformed, conflicting, and out-of-domain records are rejected or excluded. No OASIS MCI category may be invented and no record defaults to `Impaired`.

## Invariants

- Class order is explicit `[CN, Impaired]`.
- Original diagnosis remains available for audit and CN-versus-AD sensitivity specification.
- Target adaptation does not receive target labels.
- Historical three-class mappings remain historical and are not silently recoded in place.
- New artifacts use `SUPERSEDED_BY_PHASE18B_BINARY_LABEL_SPACE` when describing Phase 18 supersession.
