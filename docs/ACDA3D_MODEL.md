# 3D-ACDA Production Model

## Decision and provenance

The scientific source is `notebooks/archive/training_original.ipynb`, chiefly
the active model definitions in cell 7 and the `identity_ctx` ablation in cell
18. The architecture formerly called Lite, `no_ctx_encoder` or `identity_ctx`
is now the only proposed model and its public name is **3D-ACDA**.

The former Full architecture is not implemented. There is no contextual ROI
encoder, Transformer ROI mixer, `ctx_enc`, identity patch, mean-pool ablation,
or Full/Lite runtime switch. Precompute and baseline notebook copies were
reviewed only as parity references; training contains the latest active
components. Their copied Full models are deliberately not production sources.

## Exact architecture

Canonical defaults are `K=84`, `C_f=256`, `C_t=128`, three classes,
`base_ch=32`, concept hidden width 64 and dropout 0.2. The repository model
configuration sets `K=102` to match the Phase 5 CerebrA ROI metadata.

1. `Encoder3D`: a 7x7x7 stride-2 stem followed by three two-block residual
   stages. Stages 1 and 2 downsample by two; stage 3 has stride one. Every
   convolutional block uses GroupNorm and ReLU. The channel path is
   `1 -> 32 -> 64 -> 128 -> 256`, and spatial output is approximately one
   eighth of the input along each axis.
2. `ROITokenizer`: receives masks already on that feature grid and already
   normalized offline. It performs the canonical weighted sum with
   `einsum("bcv,kv->bkc")`, projects `C_f -> C_t`, and adds one learned
   embedding per ROI in the supplied order.
3. Token processing is exactly `T0 = tokenizer(F)`, `T1 = token_norm(T0)`,
   `T2 = T1 + token_mlp(T1)`, `T = token_dropout(T2)`. The MLP is
   `Linear(C_t,C_t) -> GELU -> Dropout(0.2) -> Linear(C_t,C_t)`.
4. `U = T`. Here `U` is a compatibility alias for retained non-contextual
   tokens; no additional transformation or token-to-token mixing occurs.
5. `AttentionAggregator` scores each ROI with
   `v(tanh(W_a(U)))`, applies softmax over `K`, and returns weighted embedding
   `z` plus coefficients `alpha`.
6. `ClassificationHead` is the canonical single linear `C_t -> 3` layer.
   Softmax probabilities are computed by the parent model. Class order is
   fixed as `CN`, `MCI`, `AD`.
7. `ConceptBottleneck` contains a distinct MLP for each ROI:
   `Linear(C_t,64) -> GELU -> Dropout(0.2) -> Linear(64,1)`. Concatenated raw
   concepts pass through sigmoid, then a linear `K -> 3` concept classifier.

## Tensor contract

`x` is finite CPU/GPU-compatible float32 with shape `(B,1,H,W,D)`. `roi_masks`
has shape `(K,h,w,d)`, float32 or bool, is on the same device, and follows the
Phase 5 atlas label ordering shared by concept targets and Jacobian vectors.
Every mask must be non-empty. Masks are never reordered.

The canonical tokenizer did **not** resize masks. Production therefore rejects
a feature-grid mismatch instead of inventing interpolation. This differs from
general atlas preparation: the prepared atlas remains immutable, and callers
must inject the pre-normalized feature-grid pooling masks. No model module
loads an atlas, MRI, artifact, split manifest, or filesystem path.

`ACDA3DOutput` exposes `F`, `T`, `U`, `z`, `alpha`, `latent_logits`,
`latent_probabilities`, `concepts`, `concept_logits`, and
`concept_probabilities`. Aliases `logits`, `probs`, `c`, `cbm_logits`,
`logits_cbm`, and `probs_cbm` are documented compatibility views.
`to_legacy_dict()` emits the notebook's eight retained keys.

## Parameters and state

With the configured 102 ROIs, the model has 9,132,350 trainable parameters:

| Component | Parameters |
|---|---:|
| encoder | 8,187,040 |
| tokenizer | 45,952 |
| token_norm | 256 |
| token_mlp | 33,024 |
| token_dropout | 0 |
| aggregator | 16,640 |
| cls_head | 387 |
| cbm | 849,051 |

State keys use canonical retained prefixes `encoder.`, `tokenizer.`,
`token_norm.`, `token_mlp.`, `aggregator.`, `cls_head.`, and `cbm.`. Dropout has
no state. No key starts with `ctx_enc.` or `contextual_encoder.`.

## Legacy checkpoint migration

`migrate_legacy_lite_state_dict` accepts a raw state dictionary or exactly one
of `model_state_dict`, `state_dict`, or `model`. It explicitly drops only
Full-only contextual prefixes, maps documented retained rename prefixes,
checks every retained tensor shape, and reports loaded, dropped, renamed,
missing, and unexpected keys. Unknown keys and incompatible retained shapes
always fail. Missing retained keys fail by default and are reportable only via
the explicit `strict_retained=False` mode. Optimizer and scheduler state are
outside this migration.

## Parity and limitations

The CPU parity test transcribes the former Lite flow, copies all retained
weights, disables dropout with evaluation mode, and compares all eight
retained tensors. Shapes are exact; float32 tensors, softmax attention and
sigmoid concepts use `rtol=1e-6`, `atol=1e-7`. Phase 7 tests observed exact
agreement within those tolerances.

The model expects feature-grid masks to be prepared by the caller and does not
encode their label IDs in the tensor itself. Correct ordering must therefore
be established from Phase 5 metadata. Phase 7 implements no scientific loss,
trainer, optimizer, scheduler, early stopping, adaptation method, baseline,
metric, preprocessing, artifact computation, or split generation.
