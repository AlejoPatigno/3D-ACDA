# CN-versus-AD Sensitivity Protocol

**Status:** Specification-only secondary analysis; execution and reporting are forbidden in this phase.

## Purpose

Define a future sensitivity check that separates the primary task grouping from a narrower CN-versus-AD view. This protocol must not be used to claim that the primary `Impaired` class is diagnostically homogeneous.

## Inclusion rule

Use retained original diagnosis provenance:

- include original `CN` records;
- include original `AD` records;
- exclude original `MCI` records;
- exclude missing, unknown, ambiguous, malformed, conflicting, or unsupported diagnoses;
- exclude duplicate/conflicting subjects pending explicit duplicate/longitudinal policy;
- require subject-disjoint approved evaluation membership.

For this sensitivity slice, original `AD` is the positive class and original `CN` is the negative class. The primary binary classifier still emits `prob_impaired`; score orientation, threshold, and metric policy must be stated before any future run.

## Required definitions

Before execution, record:

- canonical manifest and provenance identity;
- subject/visit selection policy;
- exact inclusion and exclusion counts;
- positive and negative denominators;
- threshold or threshold-free metric policy;
- shared float64/float32 probability tolerance;
- lower-index CN argmax tie-break;
- missing/undefined metric policy (`null` plus reason, never coercion);
- split and checkpoint identities;
- relationship to the primary CN-versus-Impaired evaluation.

## Blocking rules

This protocol cannot run against unresolved OASIS semantics, an unapproved manifest, an invalid split, missing original diagnosis provenance, duplicate/conflicting subjects without policy, or a three-class checkpoint. It must not use target labels during adaptation. It must not emit a publication result, sensitivity number, class count, or claim in the current planning package.

## Current evidence state

No CN-versus-AD sensitivity analysis has run. No result, estimate, real data summary, or publication claim is present.
