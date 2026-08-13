# Phase 17 — Equivalence and Alias Map

## Decision rule

A name is not a method until its exact source symbol, intervention, preserved components, loader semantics, and output identity are proven. The resolver must emit one of `RUNNABLE_AFTER_APPROVAL`, `EQUIVALENT_TO_EXISTING_METHOD`, `INVALID_AFTER_ARCHITECTURE_REVISION`, `BLOCKED_NOT_PROVEN`, or `UNSUPPORTED_ALIAS`. It must never silently alias, downgrade, or select a nearby candidate.

## `no_domain_adaptation` -> Source-Only proof

**Disposition: BLOCKED_NOT_PROVEN.** The historical name is not accepted as Source-Only by the current evidence.

### Evidence for the historical definition

- Exact definition: `notebooks/archive/training_original.ipynb`, cell 19, lines 53–64.
- Intervention recorded there: `lambda_proto=0.0` and `lambda_pl=0.0`.
- The historical ablation-aware runner remains target-aware: cell 18, lines 259–261 constructs `UnlabeledTargetAdaptDataset`; lines 290–297 construct `target_train_loader`; lines 383–390 pass it to `trainer.fit`.
- The selective-fold branch at cell 18, lines 487–499 includes `no_domain_adaptation` only for `fold_idx >= 3`; this is incomplete evidence and cannot establish a full Source-Only run.
- Cell 8, lines 590–600 computes the adaptation components from target tensors in the full objective. Zeroing coefficients is not equivalent to proving that no target adaptation loader is built, forwarded, consumed, or represented in output identity.

### Required proof before Source-Only equivalence

The name may map to the protected Source-Only method only if an independently reviewed implementation proves all of the following:

1. no target adaptation loader is constructed, opened, iterated, or passed to the trainer;
2. no target tensor enters a loss, forward path used for training, gradient, optimizer step, scheduler step, or checkpoint decision;
3. the Source-Only trainer/method identity and equations are used, not the UDA trainer with zero adaptation weights;
4. target evaluation, if present, is a disjoint monitoring-only path with labels excluded from training;
5. the output/equivalence manifest records the Source-Only method identity rather than a loss-disabled UDA identity;
6. source-validation macro-F1 remains the only checkpoint criterion and fixed epochs remain unchanged;
7. a synthetic firewall/lifecycle test and protected Source-Only regression test pass.

Until all seven conditions have evidence, resolution fails with `source_only_not_proven`. The registry must not report `no_domain_adaptation` as `Source-Only`, and it must not accept an alias such as `source_only` for this historical name.

## Architecture dispositions

| Requested/extracted name | Exact evidence | Disposition | Resolver behavior |
|---|---|---|---|
| `no_ctx_encoder` | Factory cell 19, lines 39–44; `identity_ctx` patch cell 18, lines 10–12 and 37–46 | `EQUIVALENT_TO_EXISTING_METHOD` in resulting no-context behavior; invalid as a patching technique | Reject as a runnable ablation. Report that current PADA-3DACB is already the explicit no-context architecture. |
| `identity_ctx` | Helper patch cell 18, lines 10–12 and 37–46 | `HELPER_ONLY` | Reject as a method ID and as a production model switch. |
| `full` | Factory cell 19, lines 3–8; historical model includes former contextual path | `INVALID_AFTER_ARCHITECTURE_REVISION` | Reject. Do not instantiate `ContextualROIEncoder`, `ctx_enc`, or a Full/Lite switch. |
| `mean_pool` | Helper cell 18, lines 15–31 and patch lines 37–50; factory cell 19, lines 45–50 | `BLOCKED_NOT_PROVEN` / `canonical_defined_not_executed` | Runnable only after explicit architectural-candidate approval. If not approved, record NOT APPLICABLE and reject. |
| `mean_pooling` | No exact source symbol; nearest is `mean_pool` | `UNSUPPORTED_ALIAS` | Reject unless explicit one-to-one alias approval is recorded. |

The cross-check documents `docs/PADA3DACB_MODEL.md` and `docs/NOTEBOOK_MIGRATION_MAP.md` state that current PADA-3DACB has no contextual encoder, no `ctx_enc`, no mean-pool production ablation, and no Full/Lite runtime switch. They also state that the former Lite/no-context behavior must be implemented as an explicit PADA-3DACB model, not as an identity-patched Full model.

## Unsupported aliases and exact candidate aliases

| Requested name | Exact source candidate | Status | Rule |
|---|---|---|---|
| `no_prototype` | `no_proto` | `UNSUPPORTED_ALIAS` until approved | May map only to `no_proto`; never create a second registry identity. |
| `no_pseudo_label` | `no_pl` | `UNSUPPORTED_ALIAS` until approved | May map only to `no_pl`; preserve exact source provenance. |
| `no_head_consistency` | nearest is `no_cons` | `UNSUPPORTED_ALIAS` | Do not infer that a head-consistency description means `lambda_cons`; exact source symbol is absent. |
| `no_concept_supervision` | `no_concept` | `UNSUPPORTED_ALIAS` until approved | May map only to `no_concept`; no independent semantics. |
| `no_anatomical_consistency` | `no_anat` | `UNSUPPORTED_ALIAS` until approved | May map only to `no_anat`; no independent semantics. |
| `mean_pooling` | `mean_pool` | `UNSUPPORTED_ALIAS` until approved | May map only to `mean_pool`; no independent architecture name. |
| `source_only` | none proven from `no_domain_adaptation` | `UNSUPPORTED_ALIAS` | Use the protected Source-Only method identity only after its own contract resolves. |

## Coefficient equivalence

`lambda_proto=0.2` is not equivalent to the canonical primary `lambda_proto=1.0`. Evidence for `0.2` appears in the later helper at cell 18, line 70 and in the historical class default at cell 8, line 475; the primary call sets `1.0` at cell 14, line 513. The resolver must preserve the discrepancy as `UNRESOLVED_CONFIGURATION` and fail publication-facing resolution until a separate decision selects one value with provenance.

## Manifest requirements

Every future request, including rejected requests, records:

- requested name and exact spelling;
- canonical resolved ID, or `null` if blocked;
- alias mapping decision and approval reference;
- classification and disposition;
- exact source provenance;
- intervention and preserved components, or `unresolved`;
- Source-Only proof status where relevant;
- model variant disposition;
- blocked reason and required evidence;
- `equivalence_manifest_hash`.

A rejected alias must be visible in the manifest. Absence of a mapping is not permission to use the nearest candidate.
