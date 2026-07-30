# Datasets, Artifact Wiring and Deterministic Splits

## Scope and Canonical References

Phase 6 uses the final dataset and split definitions in
`training_original.ipynb` for domain adaptation and
`baselines_original.ipynb` for supervised classification. It consumes the
Phase 5 `artifact_index.csv` explicitly. It does not execute preprocessing,
regenerate concepts or Jacobians, refit normalizers, create models, define
losses or run training.

The fixed class order is `CN`, `MCI`, `AD`, mapped to `0`, `1`, `2`. Only ADNI
and OASIS are accepted. Subject identity is the composite
`<cohort>:<subject_hash>`, so equal strings from different cohorts are not
treated as the same person.

## Artifact Index and Subject Record

`load_artifact_index` accepts an explicit CSV and optional artifact root.
Relative derivative, concept and Jacobian paths resolve against that root;
absolute paths remain absolute. Repository relocation is permitted only with
explicit old/new prefix arguments, and every replacement is recorded. There
is no path discovery, fallback by filename, recomputation or repair.

The shared `SubjectRecord` stores subject ID/hash, cohort, class and index,
resolved paths, preprocessing/precompute/atlas hashes, artifact statuses,
original inventory row and remaining metadata. Loading rejects duplicate
composite identities, duplicate derivatives, invalid cohorts/classes,
label-index conflicts and required missing/failed artifacts.

| Profile | Label | Concept | Jacobian |
|---|---:|---:|---:|
| `classification_only` | yes | no | no |
| `source_with_concepts` | yes | yes | no |
| `source_with_anatomy` | yes | no | yes |
| `source_full_artifacts` | yes | yes | yes |
| `target_adaptation` | retained, not returned | no | no |
| `target_evaluation` | yes | no | no |

MRI tensors are finite CPU float32 `(1,H,W,D)`. Concept and Jacobian tensors
are finite CPU float32 `(K,)`. No intensity transform or CUDA initialization
occurs. Initialization validation checks all required tensors before a loader
starts.

## Dataset Batch Contracts

`LabeledSourceDataset` returns `x`, `y`, `c_target`, `g_bar`, `subject_id`,
`subject_hash`, `cohort`, and `label_name`. The `c_target` spelling preserves
the final training notebook consumer.

`TargetAdaptationDataset` returns only `x`, `subject_id`, `subject_hash`, and
`cohort`; it excludes `y`, `label_name` and supervised target artifacts. Labels
remain in records/manifests for splitting and monitoring.

`LabeledTargetDataset` returns `x`, `y`, `subject_id`, `subject_hash`, `cohort`,
and `label_name`. `SupervisedMRIDataset` returns the same classification fields
and includes `c_target`/`g_bar` only under an explicit profile. Paths are omitted
unless debug mode is enabled. Dataset factories consume existing manifests and
never call random split functions.

## Split Protocol

Source validation reproduces `StratifiedKFold(n_splits=5, shuffle=True,
random_state=42)`. Every source subject validates exactly once. A class with
fewer than five subjects is a hard error.

The notebook contains both a fixed `stratified_subject_split` with
`val_fraction=0.2` and later fold-specific target `StratifiedKFold` calls. The
fixed Phase 6 decision requires one target partition shared by every source
fold and method. Production preserves the fixed 80% target adaptation / 20%
target evaluation split, stratified with seed 42, and removes fold-specific
target regeneration. No new target-label firewall is added.

`ADNI_to_OASIS` and `OASIS_to_ADNI` are generated independently. Each contains
`source_folds.csv`, `target_split.csv`, `class_counts.csv`, `protocol.json`,
JSON/Markdown summaries and resolved YAML. Artifacts are referenced, not copied.

The protocol records input-index hash, counts, ratios, seed, mapping,
software/Git provenance, scientific configuration hash and assignment hash.
The assignment hash uses stable cohort/subject/label/fold/partition values and
excludes machine paths and timestamps.

Existing manifests are reused only when configuration, input index and stored
assignment hashes validate. Incompatibility requires `--overwrite`. Dry-run
computes assignments and hashes but writes no final split directory.

## DataLoader Defaults

Source train and target adaptation use `shuffle=True`, `drop_last=True`.
Source validation, target evaluation and supervised evaluation use
`shuffle=False`, `drop_last=False`. Builders use a seeded CPU generator and
`seed_worker`; no weighted sampler or class resampling is introduced.

## CLI

```text
python scripts/create_splits.py --config configs/splits/default.yaml \
  --artifact-index /path/artifact_index.csv \
  --artifact-root /path/cache \
  --split-root /path/splits \
  --all-directions
```

Use explicit source/target flags for one direction, `--overwrite` for explicit
replacement, and `--dry-run` for assignment-only validation. Target evaluation
identities remain fixed across methods because they come from one stored
direction manifest.

## Limitations

Splits require sufficient class support for five-fold source validation and
stratified target partitioning. Phase 6 provides no model, loss, training,
adaptation, baseline, metric or paper-reproduction behavior.
