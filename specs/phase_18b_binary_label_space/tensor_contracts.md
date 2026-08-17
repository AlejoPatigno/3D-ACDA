# Binary Tensor and Loss Contracts

**Status:** Planning contract; no runtime validation has passed.

## Shape table

| Tensor/artifact | Required shape | Contract |
|---|---|---|
| Task classifier logits | `(B,2)` raw logits | Columns are fixed IDs `CN=0`, `Impaired=1`; consumed by PyTorch-style `CrossEntropyLoss`. |
| Binary target labels | `(B,)` | Integer IDs exactly in `{0,1}`. |
| Concept predictions/artifacts | `(B, K)` | `K`, ROI order, atlas identity, and artifact semantics unchanged. |
| CDAN conditioning | `z_dim * n_classes` | Runtime computation; `(128,2)->256` and `(64,2)->128` required contract cases. |
| Confusion matrix | `(2, 2)` | Rows true `[CN, Impaired]`; columns predicted `[CN, Impaired]`. |
| Prototype class IDs | binary `{0,1}` | No historical three-class IDs are accepted. |
| Prototype/pseudo logits | `(B,2)` raw logits | Integer targets `{0,1}` use PyTorch-style `CrossEntropyLoss`. |

`B` is batch size. Empty batches, non-finite values, wrong rank, and out-of-domain target IDs must fail closed according to existing project error conventions.

## Classification and prototype/pseudo losses

The task classifier and prototype/pseudo paths use PyTorch-style `CrossEntropyLoss` over exactly two raw logits shaped `(B,2)` and integer target IDs `{0,1}`. This is **not** `BCEWithLogitsLoss`, does not apply sigmoid, and is not one-logit BCE. Contract tests must cover an absent class 0 and an absent class 1 independently. If no pseudo rows are accepted, the loss is exactly zero with the existing scalar/dtype contract. Target diagnosis and target binary labels must not enter adaptation or pseudo-label decisions.

The implementation must not use a three-class default, inferred class count, or label remapping that changes fixed IDs.

## Domain adaptation

CDAN conditioning width is computed at runtime as `z_dim*n_classes`, not copied from a historical three-class constant. Required contract-only examples are:

- `(z_dim,n_classes)=(128,2) -> 256`;
- `(z_dim,n_classes)=(64,2) -> 128` (a distinct configuration).

The backward-gradient contract must show nonzero gradient reaches both feature representation `z` and class-probability input `p`. No detach operation may be introduced to bypass gradient flow.

Target adaptation remains label-free. CORAL and MMD equations, feature contracts, and weighting semantics are unchanged.

## Preserved concept/anatomical contracts

The binary migration does not alter concept output cardinality `(B,K)`, concept target artifacts or approved normalizer, atlas identity and Phase 5 ROI ordering, anatomical feature encoding, tokenizer, preprocessing, or attention contracts.

## Checkpoint tensor compatibility

Before loading any weights, the loader validates task identity and classifier output cardinality. A tensor with a classifier dimension other than two is incompatible. It must raise an explicit error and reject the complete checkpoint. Partial loading, skipped classifier keys, and shape-based truncation are prohibited.

## Numeric and identity binding

Future prediction/evaluation validators share float64 probability-sum tolerance `1e-6`, float32 tolerance `1e-5`, and lower-index CN tie-break. Undefined metrics return `null` plus a reason.

Future experiment, split, model/checkpoint, training metadata, evaluation result, and freeze identities bind binary task/version and class order and reject collision with historical three-class identities. No real hashes are created or claimed by this planning artifact.
