# Phase 13 Proposed Method Experiment

Phase 13 implements the canonical 3D-ACDA proposed method: current-batch prototype alignment plus confidence-gated pseudo-label adaptation. This document gives reviewers the quickest path to verify method identity, equations, runtime contracts, and remaining real-run blockers without relying on unverified performance claims.

## Review path

1. Confirm the scientific source in `specs/phase_13_prototype_pseudo/notebook_extraction.md`.
2. Verify the implementation contracts in `src/acda3d/adaptation/prototype.py`, `pseudo_label.py`, and `prototype_pseudo.py`.
3. Verify trainer and CLI wiring in `src/acda3d/training/uda_trainer.py`, `src/acda3d/experiments/prototype_pseudo.py`, `configs/experiments/prototype_pseudo.yaml`, and `scripts/train.py`.
4. Read the evidence and limitations before interpreting any experiment output.

## Method identity

| Field | Phase 13 value |
|---|---|
| Public model/method display | `3D-ACDA` |
| CLI/config method id | `prototype_pseudo` |
| Canonical source | `notebooks/archive/training_original.ipynb`, primary domain-adaptation path |
| Probability source for pseudo labels | Target concept-head logits (`concept_logits`) |
| Prototype representation | Source and target embeddings `z` |
| Adaptation state | Stateless current mini-batch only |
| Previous methods protected | Source-Only, CORAL, MMD, and CDAN |

Phase 13 does not implement the later notebook ablation helper as the canonical proposed method. In particular, the ablation-only `lambda_proto=0.2` path is not the Phase 13 default.

## Notebook-derived equations

### Prototype construction

For source class `c`:

```text
mu_src[c] = mean(z_src[i] for i where y_src[i] == c)
valid_src[c] = any(y_src == c)
```

For target rows:

```text
p_tgt[j] = softmax(logits_c_tgt[j], dim=-1)
conf[j], pseudo[j] = max_c p_tgt[j,c], argmax_c p_tgt[j,c]
accepted[j] = conf[j] >= tau_p
mu_tgt[c] = mean(z_tgt[j] for j where accepted[j] and pseudo[j] == c)
valid_tgt[c] = any(accepted and pseudo == c)
```

Absent classes produce zero prototype tensors and `valid=False`; invalid classes do not contribute to alignment or separation.

### Prototype loss

```text
both = valid_src & valid_tgt
L_proto_align = mean_c_in_both sum_d (mu_src[c,d] - mu_tgt[c,d])^2
              = 0 if no class is valid in both

L_proto_sep = mean_{i<j, i,j in valid_src} relu(proto_margin - ||mu_src[i] - mu_src[j]||_2)^2
            = 0 if fewer than two source classes are valid

L_proto = L_proto_align + lambda_sep * L_proto_sep
```

There is no prototype normalization, cache, EMA, memory bank, momentum, or schedule.

### Pseudo-label loss

```text
p_tgt = softmax(logits_c_tgt, dim=-1)
conf, pseudo = max(p_tgt), argmax(p_tgt)
mask = conf >= tau_p

L_pl = cross_entropy(logits_c_tgt[mask], pseudo[mask])
     = 0 if mask is empty
```

There is no temperature scaling, entropy threshold, class balancing, per-class quota, confidence schedule, target concept target, or target anatomical input.

### Warm and full objective

Warm stage is source-only:

```text
L_warm = warm_lambda_z    * lambda_z    * L_cls_z
       + warm_lambda_c    * lambda_c    * L_cls_c
       + warm_lambda_cbm  * lambda_cbm  * L_concept
       + warm_lambda_anat * lambda_anat * L_anat
       + warm_lambda_cons * lambda_cons * L_cons
```

Full stage adds the Phase 13 adaptation losses:

```text
L_proposed = lambda_z     * L_cls_z
           + lambda_c     * L_cls_c
           + lambda_cons  * L_cons
           + lambda_cbm   * L_concept
           + lambda_anat  * L_anat
           + lambda_proto * L_proto
           + lambda_pl    * L_pl
```

## Tensor contracts

| Tensor | Shape | Required source | Purpose |
|---|---:|---|---|
| `z_src` | `(B_S, C_t)` | source model output | source prototypes |
| `z_tgt` | `(B_T, C_t)` | target model output | target prototypes |
| `y_src` | `(B_S,)` | source dataset | source class membership |
| `logits_c_tgt` | `(B_T, C)` | target concept-head logits | pseudo-labels and pseudo-label CE |
| `logits_z_src`, `logits_c_src` | `(B_S, C)` | source model output | source diagnosis losses |
| `c_src`, `c_target_src`, `g_bar_src` | `(B_S, K)` | source outputs/artifacts | source concept/anatomy losses |
| target adaptation batch | key `x` required | target adaptation dataset | unlabeled adaptation input |

The implementation validates rank, compatible dimensions, class counts, integer source labels, floating-point logits/features, finite values, and shared devices for adaptation tensors.

## Canonical configuration

`configs/experiments/prototype_pseudo.yaml` declares the Phase 13 canonical values:

| Field | Value |
|---|---:|
| `n_epochs_warm` | `5` |
| `n_epochs_full` | `50` |
| `lr` | `0.0001` |
| `weight_decay` | `0.0001` |
| `batch_size` | `16` |
| `lambda_proto` | `1.0` |
| `lambda_pl` | `0.1` |
| `tau_p` | `0.95` |
| `proto_margin` | `1.0` |
| `lambda_sep` | `0.1` |
| `probability_source` | `concept_logits` |

Real-run validation fails when required scientific values are missing or incompatible. Test-only overrides must remain explicit synthetic fixtures and must not become publication defaults.

## Target-label firewall

Target adaptation is label-free. `TargetAdaptationDataset` returns only base target MRI metadata and `x`; `UDATrainer._validate_target_batch()` rejects label-like and artifact-like fields including `y`, `label`, `diagnosis`, `c_target`, and `g_bar`.

Target evaluation remains monitoring-only. Target diagnosis labels may appear in target evaluation loaders for metrics, but they must not affect loss, gradients, optimizer steps, scheduler behavior, checkpoint selection, epoch count, or hyperparameter selection.

## Checkpoint and resume behavior

Prototype and pseudo-label adaptation has no serialized adaptation state. Checkpoints record ordinary trainer/model/optimizer/scaler/history state plus method identity and hashes:

- `adaptation_method = prototype_pseudo`
- resolved adaptation configuration and hash
- source split assignment hash
- target adaptation/evaluation assignment hashes
- `prototype_pseudo_weight = 1.0`
- `prototype_pseudo_stateful_adaptation = none`
- source and target adaptation loader generator states

Resume validates these identity fields and restores loader generator state. There is no prototype cache, moving average, pseudo-label cache, or threshold schedule to restore.

## CLI usage

Dry-run planning without training:

```bash
python scripts/train.py --config configs/experiments/prototype_pseudo.yaml --method prototype_pseudo --fold 0 --dry-run
```

Validate-only finite-loss smoke path without optimizer updates:

```bash
python scripts/train.py --config configs/experiments/prototype_pseudo.yaml --method prototype_pseudo --fold 0 --validate-only
```

Plan all folds and both directions:

```bash
python scripts/train.py --config configs/experiments/prototype_pseudo.yaml --method prototype_pseudo --all-folds --both-directions --dry-run
```

Resume is scoped to exactly one direction, one seed, and one fold:

```bash
python scripts/train.py --config configs/experiments/prototype_pseudo.yaml --method prototype_pseudo --fold 0 --resume-from <checkpoint-path>
```

Real runs additionally require explicit configured artifact, split, atlas, ROI-mask, and output paths.

## Real-run blockers

Phase 13 validation used synthetic/focused fixtures only. Real ADNI/OASIS training remains blocked until the real data/artifact environment is provided and the approved command matrix is run:

- artifact index path;
- artifact root;
- split root;
- atlas metadata path;
- ROI masks path;
- output root;
- available compute budget for five folds, both directions, and approved seed matrix.

No real-cohort performance, publication metric, leaderboard result, or statistical conclusion is claimed here.

## Out of scope

Phase 13 does not add baseline models, Phase 14 evaluation, concept intervention, confusion-matrix reporting, real-cohort execution, target-supervised adaptation, target-guided checkpointing, early stopping, architecture changes, contextual encoders, preprocessing reruns, artifact precomputation reruns, split regeneration, concept normalizer refitting, prototype memory banks, or pseudo-label schedules.

Phase 14 has not been started.
