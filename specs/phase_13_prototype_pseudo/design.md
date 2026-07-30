# Phase 13 Design

Status: COMPLETE — design is bounded to canonical notebook behavior.

## Architecture boundary

Phase 13 introduces the proposed prototype + pseudo-label adaptation method as a production method alongside previously approved Source-Only, CORAL, MMD, and CDAN behavior. The adaptation losses should live behind method-specific modules and trainer integration so previous methods are not altered.

## Tensor contracts

| Name | Shape | Source | Role |
|---|---:|---|---|
| `logits_z_src` | `(B_S, C)` | source model classifier head | source diagnosis CE |
| `logits_c_src` | `(B_S, C)` | source concept/CBM head | source diagnosis CE and consistency |
| `labels_src` | `(B_S,)` | source dataset | source diagnosis labels only |
| `c_src` | `(B_S, K)` | source concept head | concept/anatomy losses |
| `c_target_src` | `(B_S, K)` | source artifacts | concept supervision |
| `g_bar_src` | `(B_S, K)` | source artifacts | anatomical consistency |
| `z_src` | `(B_S, C_t)` | source model embedding | source prototypes |
| `z_tgt` | `(B_T, C_t)` | target model embedding | target prototypes |
| `logits_c_tgt` | `(B_T, C)` | target concept/CBM head | pseudo-label creation and CE |

Target adaptation batches must require only `x`. Target `y`, `c_target`, and `g_bar` may exist only in monitoring/evaluation loaders and must not enter the adaptation objective.

## Equations

### Prototype construction

For class `c`:

```text
mu_src[c] = mean(z_src[i] for i where labels_src[i] == c)
valid_src[c] = any(labels_src == c)

p_tgt = softmax(logits_c_tgt, dim=-1)
conf[j], pseudo[j] = max_c p_tgt[j,c], argmax_c p_tgt[j,c]
accepted[j] = conf[j] >= tau_p

mu_tgt[c] = mean(z_tgt[j] for j where accepted[j] and pseudo[j] == c)
valid_tgt[c] = any(accepted and pseudo == c)
```

Absent classes produce a zero prototype and `valid=False` but must not contribute to alignment/separation.

### Prototype loss

```text
both = valid_src & valid_tgt
L_proto_align = mean_c_in_both sum_d (mu_src[c,d] - mu_tgt[c,d])^2
              = 0 if no class is valid in both

L_proto_sep = mean_{i<j, i,j in valid_src} relu(proto_margin - ||mu_src[i] - mu_src[j]||_2)^2
            = 0 if fewer than two source classes are valid

L_proto = L_proto_align + lambda_sep * L_proto_sep
```

No L2 normalization, cosine distance, squared norm normalization, EMA, moving average, cache, memory bank, or momentum is part of the canonical behavior.

### Pseudo-label loss

```text
p_tgt = softmax(logits_c_tgt, dim=-1)
conf, pseudo = max(p_tgt), argmax(p_tgt)
mask = conf >= tau_p

L_pl = cross_entropy(logits_c_tgt[mask], pseudo[mask])
     = 0 if mask is empty
```

There is no temperature scaling, entropy threshold, class balancing, per-class quota, confidence schedule, or target concept/anatomy input.

### Combined objective

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

Canonical executed coefficients:

| Field | Value |
|---|---:|
| `lambda_z` | `1.0` |
| `lambda_c` | `1.0` |
| `lambda_cons` | `0.1` |
| `lambda_cbm` | `0.5` |
| `lambda_anat` | `0.2` |
| `lambda_proto` | `1.0` |
| `lambda_pl` | `0.1` |
| `tau_p` | `0.95` |
| `proto_margin` | `1.0` |
| `lambda_sep` | `0.1` |
| `label_smoothing` | `0.1` |
| `warm_lambda_z` | `0.1` |
| `warm_lambda_c` | `1.0` |
| `warm_lambda_cbm` | `1.0` |
| `warm_lambda_anat` | `1.0` |
| `warm_lambda_cons` | `0.0` |

## Integration boundaries

- Adaptation loss modules should be stateless and deterministic for fixed tensors.
- Trainer integration should pair each source batch with a cycled target adaptation batch in full stage.
- Warm stage must not call prototype or pseudo-label losses.
- Full stage must call model once for source and once for target using the shared PADA-3DACB model.
- Checkpoint/resume does not need adaptation-specific state because no cache, EMA, memory bank, or schedule exists.
- Configuration hashes must include all Phase 13 scientific coefficients.
- Real-run validation must fail if required coefficients remain `null` placeholders.

## Target-label firewall

Adaptation functions must be callable without target labels. Tests should use sentinels or objects that fail if target label keys are accessed. Target evaluation metrics may be computed for monitoring only and must not influence loss, optimizer, scheduler, checkpoint selection, epoch count, or hyperparameter selection.

## Discrepancies handled by design

- The notebook comment about trainer-side prototype accumulators is treated as obsolete because active code constructs prototypes inside `PrototypeLoss.forward`.
- The unused `eps=1e-8` argument in `_class_prototypes` is not a numerical operation and should not be turned into invented smoothing.
- The later ablation helper's `lambda_proto=0.2` base is not used for the primary executed proposed-method run; it may inform ablation reproduction only, not Phase 13 canonical proposed method.
