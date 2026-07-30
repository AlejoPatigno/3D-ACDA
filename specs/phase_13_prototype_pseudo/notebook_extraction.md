# Phase 13 Notebook Extraction

Status: COMPLETE — canonical scientific contracts are established from `notebooks/archive/training_original.ipynb`.

## Active-source rule

The authoritative executed training path is the primary domain-adaptation run in `training_original.ipynb` before the later ablation helper overrides. The loss classes are defined once and remain active. `train_domain_adaptation_fold` is later redefined for ablation support, but the executed `bidirectional_results = run_bidirectional_domain_adaptation(...)` call used the earlier primary training helpers.

## Traceability

| Notebook lines | Symbol/cell | Status | Extracted contract |
|---:|---|---|---|
| 2001-2131 | `PrototypeLoss` | Active | Batch-local source/target prototype alignment on `z`; source separation; no buffers, cache, EMA, or momentum. |
| 2036-2059 | `PrototypeLoss._class_prototypes` | Active | Per-class mean over rows whose integer label equals `c`; absent classes return zero prototype and `valid=False`; `eps=1e-8` is present in the signature but unused. |
| 2074-2104 | `PrototypeLoss.forward` | Active | Target pseudo-labels from `softmax(logits_tgt)` argmax; accepted where confidence `>= tau_p`; align only classes present in both source and accepted target batch. |
| 2105-2128 | `PrototypeLoss.forward` | Active | Source separation over valid source prototypes: mean pairwise `relu(margin - ||mu_i - mu_j||_2)^2`; `L_proto = align + lambda_sep * sep`. |
| 2135-2170 | `PseudoLabelLoss` | Active | Self-training cross-entropy on accepted target samples using the same `softmax(logits_tgt)` argmax and `conf >= tau_p`; zero scalar if none accepted. |
| 2360-2531 | `DomainAdaptiveTotalLoss` | Active | Warm and full objectives; pseudo-label and prototype losses consume concept-head target logits (`logits_c_tgt`). |
| 3058-3068 | `DomainAdaptiveTrainConfig` | Active | Defaults: warm epochs 20, full epochs 30, lr 3e-4, weight decay 1e-4, grad clip 5.0, CPU, AMP false. |
| 3116-3370 | `DomainAdaptiveMRITrainer` | Active | Warm stage uses source batches only; full stage cycles target adaptation loader and requires only target `x`; no target diagnosis labels in adaptation loss. |
| 3407-3510 | `DomainAdaptiveMRITrainer.fit` | Active | Runs all warm epochs then all full epochs; evaluation on labeled target loaders is monitoring only. |
| 3866-4128 | Primary `train_domain_adaptation_fold` | Used by executed primary run | Builds labeled source data, unlabeled target adaptation data, target eval data, PADA model, loss, trainer, and final checkpoint/history. |
| 4360-4377 | `bidirectional_results = run_bidirectional_domain_adaptation(...)` | Latest executed primary training config | `n_splits=5`, `batch_size=16`, `num_workers=2`, `n_epochs_warm=5`, `n_epochs_full=50`, `lr=1e-4`, `weight_decay=1e-4`, `random_state=42`, `save_dir=/kaggle/working/exp_da_cbm`. |
| 4593-5120 | Ablation redefinition of `train_domain_adaptation_fold` and helpers | Superseding in namespace, not primary executed training path | Adds ablation patches/overrides. Default full ablation uses `lambda_proto=0.2`, but this was not the primary executed `bidirectional_results` run. |
| precompute/baselines parity grep | Copied symbols | Reference only | Same prototype and pseudo-label symbol copies appear; not authoritative over training path. |

## Canonical extraction

### Prototype alignment

- Representation: embeddings `z_src` and `z_tgt`, shape `(B, C_t)`.
- Normalization: no explicit normalization of embeddings or prototypes.
- Source prototypes: `mu_src[c] = mean(z_src[y_src == c], dim=0)` for present classes.
- Target pseudo-labels: `probs_tgt = softmax(logits_c_tgt, dim=-1)`, `conf, pseudo = probs_tgt.max(dim=-1)`, accepted if `conf >= tau_p`.
- Target prototypes: `mu_tgt[c] = mean(z_tgt[accepted & pseudo == c], dim=0)` for present accepted classes.
- Absent classes: zero prototype with invalid mask; invalid classes do not contribute to alignment or separation.
- Alignment: if any class is valid in both source and target, `mean_c sum_j (mu_src[c,j] - mu_tgt[c,j])^2`; otherwise zero.
- Separation: valid source classes only; for each unordered valid pair, `relu(margin - ||mu_i - mu_j||_2)^2`, averaged over pairs; zero if fewer than two valid source classes.
- Combined prototype loss: `L_proto = L_proto_align + lambda_sep * L_proto_sep`.
- Defaults: class constructor defaults `tau_p=0.9`, `margin=1.0`, `lambda_sep=0.1`; executed primary config uses `tau_p=0.95`, `proto_margin=1.0`, `lambda_sep=0.1`, `lambda_proto=1.0`.
- Update mode/cache/moving averages/momentum: none. The notebook computes prototypes from the current mini-batch only.
- Detach/gradient: no detach appears in `PrototypeLoss`; gradients flow through `z_src`, `z_tgt`, and selected target logits used in the confidence/pseudo-label branch only as selected CE logits. The argmax/mask are non-differentiable selection tensors.
- Warm-up: prototype loss is not computed in warm stage and is logged as `0.0`.

### Pseudo-label adaptation

- Probability branch: concept-head target logits (`logits_c_tgt`, notebook output key `cbm_logits`) only.
- Probability equation: `p = softmax(logits_c_tgt, dim=-1)`.
- Label creation: `pseudo = argmax_c p_c`, `conf = max_c p_c`.
- Confidence: accepted if `conf >= tau_p`; no entropy rule, no class balancing, no schedule, no temperature scaling.
- Objective: `F.cross_entropy(logits_c_tgt[mask], pseudo[mask])`, default PyTorch mean reduction over accepted samples.
- No-accepted behavior: returns `logits_tgt.new_tensor(0.0), 0`.
- Detach: no explicit detach; pseudo labels and masks come from argmax/max and are non-differentiable index/target tensors. Cross-entropy gradients flow only through accepted `logits_c_tgt` rows.
- Coefficient: class default `lambda_pl=0.1`; executed primary config uses `lambda_pl=0.1`.
- Warm-up: pseudo-label loss is not computed in warm stage and is logged as `0.0`.
- Target concept/anatomy use: target adaptation loader requires only `x`; target concept/anatomy tensors are not consumed by adaptation losses. Labeled target loaders are used only for monitoring.

### Combined `L_proposed`

Warm stage:

```text
L_warm = warm_lambda_z    * lambda_z    * L_cls_z
       + warm_lambda_c    * lambda_c    * L_cls_c
       + warm_lambda_cbm  * lambda_cbm  * L_concept
       + warm_lambda_anat * lambda_anat * L_anat
       + warm_lambda_cons * lambda_cons * L_cons
```

Full stage:

```text
L_proposed = lambda_z     * L_cls_z
           + lambda_c     * L_cls_c
           + lambda_cons  * L_cons
           + lambda_cbm   * L_concept
           + lambda_anat  * L_anat
           + lambda_proto * L_proto
           + lambda_pl    * L_pl
```

Executed primary coefficients:

```text
lambda_z=1.0, lambda_c=1.0, lambda_cons=0.1,
lambda_cbm=0.5, lambda_anat=0.2,
lambda_proto=1.0, lambda_pl=0.1,
tau_p=0.95, proto_margin=1.0, lambda_sep=0.1,
label_smoothing=0.1,
warm_lambda_z=0.1, warm_lambda_c=1.0,
warm_lambda_cbm=1.0, warm_lambda_anat=1.0, warm_lambda_cons=0.0
```

### Discrepancies and obsolete notes

- Notebook prose says prototype accumulators live in the trainer and are passed as arguments; the active code has no prototype accumulators, no cache, no EMA, and no trainer-passed prototype state.
- `eps=1e-8` exists in `_class_prototypes` but is unused.
- Primary `run_bidirectional_domain_adaptation` returns only `source_to_target`; backward direction code is commented out in the primary run helper.
- Later ablation helpers redefine `train_domain_adaptation_fold`; they are namespace-active after execution but were not used by the primary executed `bidirectional_results` call.
