# Phase 18B Migration Inventory

**Status:** Planning inventory. No migration, implementation, or artifact regeneration has run.

## Compatibility policy

Phase 18B creates a new binary task identity. Historical Phase 18 three-class artifacts remain preserved, immutable evidence. They are conceptually superseded only in new artifacts with:

`SUPERSEDED_BY_PHASE18B_BINARY_LABEL_SPACE`

No historical file is edited, deleted, overwritten, or merged into a binary result.

## Inventory

| Artifact or concern | Historical state | Phase 18B disposition | Gate/evidence |
|---|---|---|---|
| Task vocabulary | Three-class `CN/MCI/AD` planning | New fixed `CN/Impaired`, IDs 0/1 | Specification review pending |
| Original diagnosis | Source provenance | Retain alongside derived binary label | Future contract test |
| ADNI mapping | Three distinct labels | `CN→CN`, `MCI→Impaired`, `AD→Impaired`; reject invalid values and exclude duplicates/conflicts pending policy | Deterministic planning contract |
| OASIS mapping | Legacy CDR evidence | Block until canonical manifest/provenance approval; reject/exclude ambiguity | Maintainer gate blocked |
| Split manifests | Historical three-class identity | Regenerate binary splits by default | `REGENERATE_BINARY_SPLITS_REQUIRED` |
| Split hashes | Historical or absent | No real binary hash yet | No real data allowed |
| Experiment matrix | Historical three-class plan | New binary-scoped matrix later | No matrix execution claimed |
| Checkpoints | Three-class heads may exist | Reject for binary; no partial load | Future compatibility test |
| Task classifier | Three logits historically planned | Two logits `(B,2)` | Future shape test |
| Concept outputs | `(B,K)` | Unchanged | Future invariant test |
| CDAN conditioning | Class-count dependent | Runtime `z_dim*n_classes`; test `(128,2)->256` and distinct configuration with gradient to `z` and `p` | Future contract test |
| Prototype/pseudo paths | Historical class assumptions | Two raw logits `(B,2)`, integer targets/prototype IDs `{0,1}`, PyTorch-style `CrossEntropyLoss`; absent-class tests; empty accepted set zero loss | Future contract test |
| CORAL/MMD | Existing approved math | Unchanged | Future regression test |
| Predictions | Three-class schema | `prob_cn`, `prob_impaired`; reject active `prob_mci` and `prob_ad` | Future schema test |
| Evaluation | Three-class confusion/metrics | Binary 2x2 and required metrics with shared tolerance/null policy | Future evaluation test |
| Identity families | Historical three-class identities | Distinct binary experiment, split, model/checkpoint, training metadata, evaluation result, and freeze identities | Collision tests required |
| CN-vs-AD sensitivity | Not a primary binary result | Specification-only filtered slice | No result allowed |
| Freeze artifacts | Historical identity | No binary freeze approved | `freeze_approved=false` |
| Phase 19 interfaces | Future consumer | Prepare interface only | `phase_19_forbidden=true` |

## Identity rules

Each future binary identity family—experiment, split, model/checkpoint, training metadata, evaluation result, and freeze—must bind task/version, fixed class order, mapping version/provenance, and relevant inputs. Each must reject collision with a historical three-class identity. Real hash values are intentionally absent.

## Checkpoint migration

There is no conversion path from a three-class checkpoint to a binary checkpoint in this specification. A loader must inspect task/cardinality metadata and classifier tensor shape before loading. Any mismatch fails closed; classifier-only omission or partial loading is prohibited.

## Operational boundary

Before both the verified OASIS semantics gate and the two substituted independent checklist reviews pass, only documentation, specification refinement, and synthetic contract-test planning are allowed. That work is not implementation. Real data execution, training, inference, evaluation, publication analysis, Phase 19 execution, lifecycle claims, receipt edits, and binary freeze artifacts remain forbidden.
