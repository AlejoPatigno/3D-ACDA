# Phase 7 Report: Explicit PADA-3DACB Model

## Scope completed

Phase 7 extracted the active `ResBlock3D`, `Encoder3D`, `ROITokenizer`,
`AttentionAggregator`, `ClassificationHead`, and per-ROI MLP
`ConceptBottleneck` from `training_original.ipynb`. The duplicated precompute
and baseline definitions were compared as parity references. Training was
selected because it contains the latest active concept bottleneck and the
executed `identity_ctx` evidence for the former Lite path.

The new `PADA3DACB` directly constructs only retained modules. Its exact path
is:

`x -> encoder -> tokenizer -> LayerNorm -> residual token MLP -> token dropout -> U=T -> attention -> latent head + concept bottleneck`

Excluded: Full architecture, contextual ROI encoder, Transformer ROI mixing,
identity patching, mean pooling and architecture mode switches.

## Contracts and configuration

- Constructor notebook defaults: `K=84`, `C_f=256`, `C_t=128`, classes 3,
  `base_ch=32`, concept hidden 64, dropout 0.2.
- Production YAML: public name `PADA-3DACB`, `contextual_encoder=false`, and
  `K=102` from Phase 5 metadata.
- Encoder: GroupNorm/ReLU residual CNN, one-eighth spatial grid, 256 channels.
- Tokenizer: pre-normalized exact-feature-grid weighted pooling, linear
  projection, learned ROI embeddings; no interpolation or reordering.
- Token processing: normalize, add MLP residual, then dropout.
- Attention: tanh score, ROI-axis softmax, weighted sum.
- Latent head: linear 128-to-3, class order CN/MCI/AD.
- Concepts: one `128 -> 64 -> 1` GELU/dropout MLP per ROI, sigmoid, linear
  concept classifier.
- Output: typed `F/T/U/z/alpha`, latent logits/probabilities, concepts and
  concept logits/probabilities, with documented legacy aliases.

The model receives MRI and mask tensors explicitly and performs no file I/O.
Input validation covers dimensions, one channel, float32 MRI values,
finiteness, device agreement, ROI count, feature-grid shape and non-empty
masks. `U` is the non-contextual processed token tensor.

## Parameters and checkpoints

Configured `K=102` parameter counts are: total/trainable 9,132,350;
encoder 8,187,040; tokenizer 45,952; token norm 256; token MLP 33,024;
aggregator 16,640; latent head 387; concept bottleneck 849,051. There are no
non-trainable parameters and no contextual state keys.

Legacy migration explicitly locates model state, drops `ctx_enc.*` and
`contextual_encoder.*`, maps only the audited prefix table, validates shapes,
and reports loaded/dropped/renamed/missing/unexpected keys. Strict retained
loading is the default. Optimizer and scheduler checkpoints are not migrated.

## Parity and integration

The reference test transcribes notebook cells 7 and 18, copies retained
weights, evaluates identical float32 MRI/masks with dropout disabled, and
compares encoder features, tokens, `U`, embedding, attention, latent logits,
concepts and concept logits. Tolerance is `rtol=1e-6`, `atol=1e-7`; all
comparisons passed. Shape checks are exact.

The Phase 6 integration test creates a `LabeledSourceDataset` item and verifies
that `batch["x"]` passes through the model and that model ROI dimensions match
both `batch["c_target"]` and `batch["g_bar"]`, without calculating a loss.

## Required validation results

Commands used the bundled Python runtime at
`C:\Users\LOQ\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`.

```text
python -m pip install -e .
Successfully built pada3dacb
Successfully installed pada3dacb-0.1.0

python -c "import pada3dacb; print(pada3dacb.__version__)"
0.1.0

python -m pytest -q
113 passed, 2 warnings in 605.08s (0:10:05)

python -m ruff check .
All checks passed!
```

The two warnings predate Phase 7 and come from the one-element standard
deviation edge case in `test_normalization_parity_cases` and its canonical
preprocessing implementation.

Synthetic inspection command:

```text
python -c "import json, torch; from pada3dacb.models import PADA3DACB; from pada3dacb.models.model_summary import summarize_model; m=PADA3DACB(num_rois=102).cpu(); masks=torch.ones(102,2,2,2,dtype=torch.float32)/8; s=summarize_model(m,(1,1,16,16,16),masks); s['ctx_state_keys']=[k for k in m.state_dict() if k.startswith(('ctx_enc.','contextual_encoder.'))]; print(json.dumps(s,indent=2))"
```

Observed summary: total/trainable/non-trainable parameters
`9,132,350 / 9,132,350 / 0`; input `(1,1,16,16,16)`; `F`
`(1,256,2,2,2)`; `T` and `U` `(1,102,128)`; `z` `(1,128)`;
`alpha` and concepts `(1,102)`; both logit/probability branches `(1,3)`;
`ctx_state_keys=[]`. Component counts match the table in
`PADA3DACB_MODEL.md`.

The first sandboxed editable-install attempt could not reach the build index.
The same required command was rerun with approved network access and completed
successfully; this was an environment restriction, not a package discrepancy.

## Files

Created eight production model modules, eight requested test files,
`docs/PADA3DACB_MODEL.md`, and this report. Updated model exports,
configuration schema/YAML, package exceptions, and the cumulative audit.

## Boundaries and limitations

The canonical tokenizer requires already normalized masks at feature-grid
resolution, so production rejects grid mismatch and does not resize. ROI
ordering remains a caller-visible Phase 5 metadata contract. Validation is
synthetic and CPU-only; no cohort MRI, preprocessing, artifact recomputation,
split regeneration, normalizer fitting, or training was run.

No contextual encoder, Full model, identity patch, scientific loss, training
loop, optimizer, scheduler, early stopping, source-only training, CORAL, MMD,
CDAN, prototype/pseudo-label behavior, baseline, or evaluation metric was
implemented. Phase 8 was not started.

## Proposed Phase 8 files

Subject to explicit approval, Phase 8 may introduce focused scientific loss
modules under `src/pada3dacb/losses/` and their synthetic contract/parity tests.
No Phase 8 file has been created in this phase.
