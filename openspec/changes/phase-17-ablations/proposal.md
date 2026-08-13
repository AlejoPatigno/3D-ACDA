# Phase 17 — Auditable Synthetic Ablation Contracts

Phase 17 will turn the audited notebook ablation surface into a single, provenance-rich, fail-closed contract. This artifact synchronization records the implementation boundary; it does not execute an ablation, load real data, produce publication metrics, or start Phase 18.

## Problem

The archived notebook defines ablation factories and helpers, but its ablation study call is commented, outputs are stripped, later runners shadow earlier definitions, and one helper uses `lambda_proto=0.2` while the canonical primary call uses `lambda_proto=1.0`. Candidate names therefore cannot be treated as executed methods or resolved by name alone. The historical contextual `Full`/`ctx_enc` path also conflicts with the current explicit no-context PADA-3DACB architecture.

Phase 17 needs one implementation contract that preserves exact source provenance, makes only one approved intervention at a time, protects target-label isolation, enforces complete matrices and fixed epochs, and makes every synthetic artifact resumable and hash-identifiable.

## Objective

Create a deterministic synthetic/test implementation boundary for canonical PADA-3DACB ablations that:

1. resolves only exact, explicitly approved candidate identities;
2. preserves the canonical primary objective and all inherited settings;
3. composes one loss coefficient override or one approved pooling replacement around the existing trainer;
4. rejects contextual, ambiguous, incomplete, target-supervised, unresolved, and real-run requests;
5. emits provenance, output, checkpoint, resume, and equivalence contracts suitable for later authorization review.

No result from this specification is a real-data result or a publication claim.

## Scope

### Approved synthetic-contract candidates

The following six exact IDs are approved for synthetic implementation only:

| ID | Sole intervention |
|---|---|
| `no_proto` | `lambda_proto = 0.0` |
| `no_pl` | `lambda_pl = 0.0` |
| `no_cons` | `lambda_cons = 0.0` |
| `no_concept` | `lambda_cbm = 0.0` |
| `no_anat` | `lambda_anat = 0.0` |
| `mean_pool` | Replace attention aggregation with the exact notebook-defined uniform mean operation: `z = U.mean(dim=1)` and uniform `alpha = 1/K`. |

Each loss candidate inherits every other canonical primary coefficient, model component, split, seed, optimizer, schedule, epoch input, artifact, and output rule. `mean_pool` changes only the retained aggregator and remains an explicit PADA-3DACB composition, not a Full/Lite or contextual variant.

The implementation contract also records blocked and equivalent dispositions so rejection is explainable. It includes registry/resolver composition, target firewall, complete matrix validation, SHA-256 identity, fixed-epoch checkpointing, atomic outputs, interruption/resume, synthetic lifecycle evidence, and protected-method regressions.

## Non-goals

- Real ADNI/OASIS loading, training, evaluation, or publication analysis.
- Publication metrics, statistical comparisons, leaderboard values, superiority claims, or clinical conclusions.
- Phase 18 planning, implementation, evaluation, or artifacts.
- Target diagnosis labels, concept targets, Jacobian targets, or other supervision in adaptation.
- Any new contextual model, `ContextualROIEncoder`, `ctx_enc`, Full/Lite runtime switch, or identity-patched Full model.
- A duplicate trainer, a selective-fold shortcut, early stopping, target-guided checkpoint selection, or silently invented defaults.
- Silent acceptance of aliases or a choice between `lambda_proto=0.2` and `lambda_proto=1.0`.
- Changes to protected Source-Only, CORAL, MMD, CDAN, prototype-pseudo, AAGN, FasterSNN, Phase 15, Phase 16, or native lifecycle behavior.

## Scientific boundaries

The questions are limited to whether one defined loss term or the retained aggregator changes synthetic behavior under a fixed contract, whether component diagnostics isolate that intervention, and whether target monitoring remains independent of training and selection. The historical `no_domain_adaptation` name remains blocked as Source-Only until loader, forward, gradient, method identity, and output proof exists. `full` is invalid after the architecture revision; `no_ctx_encoder` is equivalent to the existing no-context behavior but invalid as a patch; `identity_ctx` is helper-only.

The canonical warm objective remains:

```text
L_warm = warm_lambda_z    * lambda_z    * L_cls_z
        + warm_lambda_c    * lambda_c    * L_cls_c
        + warm_lambda_cbm  * lambda_cbm  * L_concept
        + warm_lambda_anat * lambda_anat * L_anat
        + warm_lambda_cons * lambda_cons * L_cons
```

Warm prototype and pseudo-label terms are absent and logged as zero. The full objective remains:

```text
L_full = lambda_z     * L_cls_z
        + lambda_c     * L_cls_c
        + lambda_cons  * L_cons
        + lambda_cbm   * L_concept
        + lambda_anat  * L_anat
        + lambda_proto * L_proto
        + lambda_pl    * L_pl
```

The primary inherited value is `lambda_proto=1.0`; the later helper value `lambda_proto=0.2` remains unresolved and is not selected here.

## Administrative and safety boundaries

This proposal is downstream of the PASS independent review in `specs/phase_17_ablations/spec_review.md`. Synthetic implementation may begin only through the collision-free, dependency-ordered ownership graph. Each action owns only its listed files. No Phase 16 cleanup artifact, native receipt provenance, or unrelated worktree change may be rewritten.

A real-run request must fail before data loading unless a separate authorization records the exact candidate matrix, data and artifact locations, compute budget, and approved command. Every synthetic or blocked artifact must state `real_data_run: false` and `publication_metrics_present: false`. Any interruption or hash mismatch fails closed; rollback means discard only the incomplete synthetic run identity, never overwrite a different candidate or resume identity.

## Rollback and safety

- Resolve and validate the candidate, approval, matrix, assignments, architecture, and immutable artifacts before training or output creation.
- Write checkpoints, history, predictions, and manifests atomically; verify hashes after writing.
- Resume only when all candidate, approval, configuration, model, registry, direction, fold, seed, assignment, artifact, and hash identities match.
- Reject malformed, partial, target-supervised, real-run, publication, contextual, alias, unresolved-coefficient, or incomplete-matrix requests with structured reasons.
- Preserve the prior protected-method behavior and stop at the Phase 17 synthetic boundary; never promote synthetic output to real-data or publication evidence.
