# Phase 17 Ablation Experiments

Phase 17 provides a registry-backed, fail-closed ablation contract for synthetic validation and later authorization review. It does **not** authorize real ADNI/OASIS training, publication evaluation, or Phase 18. The registry is the source of candidate identity; a description, alias, notebook helper, or historical output name is not sufficient to create a runnable method.

## Quick path

1. Use an exact approved ID from the registry.
2. Use `configs/experiments/ablations.yaml`, which declares the synthetic-only boundary, both transfer directions, folds `0..4`, seed `42`, explicit epochs, and the canonical primary coefficients.
3. Run `--dry-run` to inspect plans or `--validate-only` to exercise the CPU synthetic contract without writing a run directory.

```bash
python scripts/run_ablations.py \
  --config configs/experiments/ablations.yaml \
  --ablation no_proto \
  --source-domain ADNI \
  --target-domain OASIS \
  --fold 0 \
  --seed 42 \
  --output-root runs/phase17_synthetic \
  --dry-run
```

The command is planning-only. It does not load MRI data, execute a forward pass, or create `runs/phase17_synthetic`.

## Approved registry IDs

These are the only approved Phase 17 candidate IDs. Each candidate has one intervention and inherits the rest of the canonical primary configuration.

| Exact ID | Sole intervention | Model variant |
|---|---|---|
| `no_proto` | Set `lambda_proto = 0.0` | `3D-ACDA` |
| `no_pl` | Set `lambda_pl = 0.0` | `3D-ACDA` |
| `no_cons` | Set `lambda_cons = 0.0` | `3D-ACDA` |
| `no_concept` | Set `lambda_cbm = 0.0` | `3D-ACDA` |
| `no_anat` | Set `lambda_anat = 0.0` | `3D-ACDA` |
| `mean_pool` | Replace only the retained attention aggregation with `z = U.mean(dim=1)` and uniform `alpha = 1/K` | `3D-ACDA+MeanPoolAggregator` |

`mean_pool` is an explicit aggregator composition, not a Full/Lite switch, contextual model, or patched checkpoint. Loss-only candidates preserve the base model-variant hash; `mean_pool` has a distinct model-variant hash.

## Inherited scientific settings

The five loss candidates inherit every setting not named by their intervention: the 3D-ACDA architecture, class order, source and target assignments, folds, seed, optimizer, schedule, explicit epoch inputs, thresholds, margins, smoothing, immutable concept/Jacobian artifacts, diagnostics, checkpoint rules, and output identity rules.

The canonical primary coefficient values are:

```text
lambda_z=1.0, lambda_c=1.0, lambda_cons=0.1,
lambda_cbm=0.5, lambda_anat=0.2,
lambda_proto=1.0, lambda_pl=0.1,
tau_p=0.95, proto_margin=1.0, lambda_sep=0.1,
label_smoothing=0.1,
warm_lambda_z=0.1, warm_lambda_c=1.0,
warm_lambda_cbm=1.0, warm_lambda_anat=1.0,
warm_lambda_cons=0.0
```

The warm objective is:

```text
L_warm = warm_lambda_z    * lambda_z    * L_cls_z
        + warm_lambda_c    * lambda_c    * L_cls_c
        + warm_lambda_cbm  * lambda_cbm  * L_concept
        + warm_lambda_anat * lambda_anat * L_anat
        + warm_lambda_cons * lambda_cons * L_cons
```

`L_proto` and `L_pl` are not computed during warm-up and are logged as zero. The full objective is:

```text
L_full = lambda_z     * L_cls_z
        + lambda_c     * L_cls_c
        + lambda_cons  * L_cons
        + lambda_cbm   * L_concept
        + lambda_anat  * L_anat
        + lambda_proto * L_proto
        + lambda_pl    * L_pl
```

The later helper value `lambda_proto=0.2` remains unresolved and is never selected by assumption. The canonical primary value for this contract is `lambda_proto=1.0`.

## Target four-key firewall

A target-adaptation batch must contain exactly these keys:

```text
x, subject_id, subject_hash, cohort
```

The resolver and strict UDA trainer reject missing or additional fields before forward/loss computation. Rejected supervision or artifact fields include `y`, `label`, `label_name`, `true_label`, `c_target`, `g_bar`, `diagnosis`, stored diagnostic probabilities, concept targets, Jacobian targets, and other supervision or artifact fields. Fields are rejected rather than silently dropped.

`target_adaptation` and `target_evaluation` assignments are disjoint and carry separate hashes. Target evaluation is a separate observational path labeled exactly:

```text
MONITORING ONLY — NOT A TRAINING LOSS
```

Target monitoring cannot affect gradients, optimizer or scheduler state, checkpoint selection, hyperparameter selection, epoch count, resume choice, candidate selection, or training loss fields.

## Matrix, epochs, and checkpoint policy

The checked-in synthetic configuration declares:

- directions: `ADNI_to_OASIS` and `OASIS_to_ADNI`;
- folds: `0, 1, 2, 3, 4`;
- seed: `42`;
- warm epochs: `5`;
- full epochs: `50`;
- early stopping: disabled;
- best-checkpoint criterion: source-validation macro-F1 only;
- training after a best-checkpoint save: required.

The epoch values are explicit synthetic configuration values. Historical notebook values are provenance, not implicit defaults for another run. The selective-fold `availability` helper is obsolete and is not used as evidence or as a complete matrix.

## CLI modes

### Dry-run

`--dry-run` resolves the requested exact IDs, directions, folds, seeds, output plans, firewall metadata, and blocked inventory. It performs no model forward pass and creates no output path.

```bash
python scripts/run_ablations.py \
  --config configs/experiments/ablations.yaml \
  --all-approved-ablations \
  --both-directions \
  --all-folds \
  --all-seeds \
  --dry-run
```

### Validate-only

`--validate-only` runs the deterministic CPU synthetic contract under `torch.no_grad()`. It validates model composition, finite objectives, disabled components, the target four-key firewall, and the monitoring boundary. It does not call backward, step an optimizer, load real data, or create output directories.

```bash
python scripts/run_ablations.py \
  --config configs/experiments/ablations.yaml \
  --ablation mean_pool \
  --source-domain ADNI \
  --target-domain OASIS \
  --fold 0 \
  --seed 42 \
  --validate-only \
  --device cpu
```

`--target-monitoring` and `--no-target-monitoring` select whether synthetic monitoring fields are emitted for validation. They must not change the resolved training objective.

### Synthetic lifecycle and resume

The deterministic lifecycle API is implemented in `acda3d.experiments.ablations`:

- `run_synthetic_lifecycle(...)` runs a synthetic warm/full lifecycle and writes atomic artifacts;
- `resume_synthetic_lifecycle(...)` continues only a matching interrupted identity;
- `validate_resume_identity(...)` performs read-only identity and artifact checks.

The lifecycle API is synthetic-only. A matching interrupted run resumes from its recorded history position without duplicate rows. A candidate, direction, fold, seed, matrix, configuration, assignment, artifact, or hash mismatch fails closed and does not overwrite the existing identity. A completed matching run is reused read-only.

## Output paths and artifacts

The implementation path is produced by `ablation_output_path`:

```text
<output_root>/ablations/<candidate_id>/<source>_to_<target>/seed_<SEED>/fold_<FOLD>/
```

For example:

```text
runs/phase17_synthetic/ablations/no_proto/ADNI_to_OASIS/seed_42/fold_0/
```

Synthetic lifecycle output includes the identity/configuration, checkpoints, training history, predictions, reproducibility metadata, equivalence manifest, and artifact index. The lifecycle uses these files when applicable:

```text
identity.json
config_resolved.json
checkpoint_last.pt
checkpoint_best_source_f1.pt
training_history.json
predictions.jsonl
source_validation_predictions.jsonl
target_monitoring_predictions.jsonl
reproducibility_metadata.json
equivalence_manifest.json
artifact_index.json
```

Prediction records distinguish source validation from target evaluation. No target-adaptation prediction file is produced. Synthetic and blocked records state `real_data_run: false` and `publication_metrics_present: false`.

Hashes use SHA-256 over canonical UTF-8 JSON with sorted keys, stable list ordering, no timestamps in hashed payloads, and canonicalization version `phase17.canonical-json.v1`. The identity envelope records registry, candidate, resolved configuration, model variant, source split, target-adaptation assignment, target-evaluation assignment, and immutable precomputed-artifact hashes. Written artifact hashes are checked through the artifact index.

## Blocked, equivalent, and unresolved requests

The registry keeps rejected requests visible and fail-closed:

| Request or item | Classification/disposition | Rule |
|---|---|---|
| `no_domain_adaptation` | `BLOCKED_NOT_PROVEN` | Zeroing prototype and pseudo-label terms does not prove a Source-Only loader, forward, gradient, method identity, or output contract. |
| `full` | `INVALID_AFTER_ARCHITECTURE_REVISION` | The former contextual Full architecture is not the current 3D-ACDA control. |
| `no_ctx_encoder` | Equivalent to existing no-context behavior; invalid as a patch | Current 3D-ACDA is already explicit no-context. Do not patch a Full model. |
| `identity_ctx` | `HELPER_ONLY` | Implementation helper, not a method or runtime switch. |
| `no_prototype`, `no_pseudo_label`, `no_head_consistency`, `no_concept_supervision`, `no_anatomical_consistency`, `mean_pooling`, `source_only` | `UNSUPPORTED_ALIAS` | Use the exact approved registry ID; no alias is silently accepted. |
| `lambda_proto=0.2` | `UNRESOLVED_CONFIGURATION` | The later helper value is not equivalent to the canonical primary `1.0`. |
| `CFS`, `ACS`, `PCS`, `QIS` | `BLOCKED_NOT_PROVEN` | No authoritative equation and implementation contract has been established. |
| selective-fold `availability` | `OBSOLETE` | It is not a complete direction/fold/seed design. |

Blocked requests produce a structured preflight/equivalence result, not a training artifact. They are never downgraded to the base method.

## Real-data, publication, and Phase 18 boundaries

This documentation and the Phase 17 implementation do not claim real cohort results, performance, statistical comparisons, publication metrics, clinical conclusions, or superiority. No real ADNI/OASIS data is loaded by the synthetic dry-run, validate-only path, or synthetic lifecycle. A future real run requires a separate authorization containing the exact candidate matrix, data and artifact locations, compute budget, and approved command; absent that authorization, resolution fails before data loading.

The Phase 16 approval and native receipt provenance remain administrative controls. The former native incident `#1793` was resolved administratively by the approved Phase 16 receipt (`review-79ee2a4308d2010c`); native pre-commit, pre-push, pre-PR, and release validation of the same content-bound receipt remain mandatory. Phase 18 has not started and is not authorized by Phase 17.
