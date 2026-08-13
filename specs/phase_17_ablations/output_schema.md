# Phase 17 — Output and Provenance Schemas

## 1. Serialization rules

All JSON objects use UTF-8, sorted keys, stable list order, no timestamps in hashed payloads, and the declared canonicalization version. Hashes use SHA-256 over canonical JSON bytes unless a schema explicitly says file bytes. Every artifact includes `schema_version`, `phase: 17`, `candidate_id`, `direction`, `fold`, and `seed` where applicable.

Target labels may appear only under a target-evaluation/monitoring role. They MUST NOT appear in target-adaptation batches, adaptation loss inputs, training labels, or checkpoint-selection fields.

## 2. Directory contract

```text
<output_root>/
  <candidate_id>/
    <source>_to_<target>/
      seed_<SEED>/
        fold_<NN>/
          checkpoint_last.pt
          checkpoint_best_source_f1.pt
          checkpoint_epoch_<NNN>.pt
          training_history.json
          predictions.jsonl
          equivalence_manifest.json
          config_resolved.json
          reproducibility_metadata.json
          artifact_index.json
```

`<candidate_id>` is the exact resolved registry ID, never a rejected alias. A blocked request creates only a structured preflight result outside this run directory and never creates a training artifact.

## 3. Common identity envelope

Every JSON artifact carries:

| Field | Type | Required meaning |
|---|---|---|
| `schema_version` | string | Artifact schema version. |
| `phase` | integer | Exactly `17`. |
| `candidate_id` | string | Exact resolved candidate ID. |
| `candidate_classification` | string | Inventory classification. |
| `candidate_approval_id` | string/null | Required for approved defined-not-executed candidates. |
| `requested_name` | string | Original CLI/request spelling. |
| `alias_mapping` | object/null | Explicit mapping, or null; never inferred. |
| `direction` | string | Exact transfer direction. |
| `fold` | integer | Predeclared fold index. |
| `seed` | integer | Predeclared seed identity. |
| `registry_hash` | string | SHA-256 of registry payload. |
| `candidate_hash` | string | SHA-256 of candidate/provenance/intervention payload. |
| `resolved_config_hash` | string | SHA-256 of resolved inherited and overridden configuration. |
| `model_variant_hash` | string | SHA-256 of explicit PADA-3DACB model manifest. |
| `source_split_assignment_hash` | string | SHA-256 of source assignment manifest. |
| `target_adaptation_assignment_hash` | string | SHA-256 of unlabeled target adaptation assignment manifest. |
| `target_evaluation_assignment_hash` | string | SHA-256 of labeled monitoring-only target evaluation assignment manifest. |
| `precomputed_artifacts_hash` | string | SHA-256 of immutable concept/Jacobian/artifact identities. |
| `hash_algorithm` | string | `sha256`. |
| `canonicalization_version` | string | Canonical JSON rules version. |

## 4. Resolved configuration schema (`config_resolved.json`)

```json
{
  "schema_version": "phase17.config.v1",
  "phase": 17,
  "identity": { "...common identity envelope fields...": "..." },
  "method": {
    "base_method": "PADA-3DACB",
    "model_variant": "PADA-3DACB",
    "architecture_components": ["Encoder3D", "ROITokenizer", "token_processing", "AttentionAggregator", "ClassificationHead", "ConceptBottleneck"],
    "contextual_encoder": null,
    "runtime_variant_switch": false
  },
  "intervention": {
    "kind": "loss_override | aggregator_replacement",
    "parameter": "lambda_proto | lambda_pl | lambda_cons | lambda_cbm | lambda_anat | aggregator",
    "old_value": "number or exact component identity",
    "new_value": "0.0 or approved component identity",
    "preserved_components": ["..."],
    "provenance": { "path": "...", "cell": 0, "lines": "..." }
  },
  "objective": {
    "warm_equation_id": "phase17.warm.v1",
    "full_equation_id": "phase17.full.v1",
    "coefficients": { "resolved inherited fields only": "..." },
    "warm_adaptation_components_active": false,
    "full_adaptation_components": ["..."]
  },
  "epochs": {
    "warm": "explicit approved input",
    "full": "explicit approved input",
    "early_stopping": false,
    "train_after_best_checkpoint": true,
    "checkpoint_metric": "source_validation_macro_f1"
  },
  "target_contract": {
    "target_adaptation_batch_keys": ["x", "subject_id", "subject_hash", "cohort"],
    "target_label_fields_forbidden": [
      "y",
      "label",
      "label_name",
      "true_label",
      "c_target",
      "g_bar",
      "diagnosis",
      "stored_diagnostic_probabilities",
      "concept_targets",
      "jacobian_targets",
      "other_supervision_fields",
      "other_artifact_fields"
    ],
    "target_evaluation": "monitoring_only",
    "assignments_disjoint": true
  }
}
```

The schema does not authorize new values for the epoch or coefficient fields. Missing or conflicting values fail resolution.

## 5. Checkpoint schema

Each `.pt` checkpoint is a structured mapping with at least:

| Field | Required content |
|---|---|
| `schema_version` | `phase17.checkpoint.v1`. |
| `checkpoint_kind` | `last`, `best_source_validation_macro_f1`, or `epoch`. |
| `model_state_dict` | State for current PADA-3DACB or approved mean-pool composition. |
| `optimizer_state_dict` | Current optimizer state. |
| `scheduler_state_dict` | Present only if the approved trainer has one; no scheduler may be invented. |
| `amp_scaler_state_dict` | Present when AMP is used. |
| `epoch` / `global_step` | Exact resume position. |
| `stage` | `warm` or `full`. |
| `best_source_validation_macro_f1` | Best source-validation value to date. |
| `history_append_position` | Position used to resume without duplicate rows. |
| `rng_state` | Python/NumPy/CPU/CUDA states available to the existing trainer. |
| `loader_generator_state` | Source and target-adaptation generator states as applicable. |
| `identity` | Full common identity envelope and all assignment/artifact hashes. |
| `target_checkpoint_selection_state` | Must be absent or an explicit empty object; target metrics cannot select. |
| `contains_mri_data` | Exactly `false`. |

`checkpoint_best_source_f1.pt` may be updated only when source-validation macro-F1 improves. Target monitoring fields cannot participate.

## 6. History schema (`training_history.json`)

```json
{
  "schema_version": "phase17.history.v1",
  "identity": { "...common identity envelope fields...": "..." },
  "rows": [
    {
      "stage": "warm | full",
      "epoch": 0,
      "global_step": 0,
      "learning_rate": "resolved numeric value",
      "loss": {
        "total": 0.0,
        "components": {
          "L_cls_z": { "active": true, "raw": 0.0, "weighted": 0.0 },
          "L_cls_c": { "active": true, "raw": 0.0, "weighted": 0.0 },
          "L_cons": { "active": true, "raw": 0.0, "weighted": 0.0 },
          "L_concept": { "active": true, "raw": 0.0, "weighted": 0.0 },
          "L_anat": { "active": true, "raw": 0.0, "weighted": 0.0 },
          "L_proto": { "active": false, "raw": 0.0, "weighted": 0.0 },
          "L_pl": { "active": false, "raw": 0.0, "weighted": 0.0 }
        }
      },
      "diagnostics": {
        "accepted_count": 0,
        "rejected_count": 0,
        "acceptance_rate": 0.0,
        "adaptation_active": false,
        "prototype_alignment_raw": 0.0,
        "prototype_alignment_weighted": 0.0,
        "prototype_separation_raw": 0.0,
        "prototype_separation_weighted": 0.0,
        "classes_with_source_prototypes": 0,
        "classes_with_target_prototypes": 0,
        "classes_with_both_prototypes": 0
      },
      "source_metrics": { "macro_f1": 0.0, "accuracy": 0.0 },
      "target_monitoring": {
        "enabled": false,
        "label": "MONITORING ONLY — NOT A TRAINING LOSS",
        "metrics": {}
      },
      "gradient_norm": 0.0,
      "duration_seconds": 0.0
    }
  ],
  "history_hash": "sha256"
}
```

The numeric examples above illustrate types and field presence; runtime values come from the approved trainer. In warm rows, adaptation components are inactive and zero. In a loss ablation, the intended weighted component is zero while its raw diagnostic may be retained if the existing loss computes it; the schema must distinguish `active`, `raw`, and `weighted` rather than collapsing them.

## 7. Prediction schema (`predictions.jsonl`)

Each line is one subject/split prediction record:

| Field | Type/requirement |
|---|---|
| `schema_version` | `phase17.prediction.v1`. |
| `subject_id` | Stable non-sensitive fixture/subject identity. |
| `dataset_role` | `source_train`, `source_validation`, `target_adaptation`, or `target_evaluation`. |
| `target_labels_present` | Must be `false` for `target_adaptation`; may be `true` only for monitoring-only `target_evaluation`. |
| `target_label_usage` | `forbidden`, `monitoring_only`, or `not_applicable`. |
| `split_assignment_hash` | Corresponding source/target assignment hash. |
| `checkpoint_hash` | Checkpoint used for prediction. |
| `logits_z` | Latent-head logits. |
| `logits_c` | Concept-head diagnosis logits. |
| `probabilities_z` / `probabilities_c` | Corresponding probabilities. |
| `predicted_class_z` / `predicted_class_c` | Class indices using `[CN, MCI, AD]`. |
| `target_monitoring_label` | Exact monitoring-only label when role is target evaluation. |
| `prediction_hash` | Hash of canonical prediction record. |

A target adaptation prediction record must not serialize target diagnosis labels, concept targets, Jacobian targets, or a field that could be interpreted as training supervision.

## 8. Equivalence manifest schema (`equivalence_manifest.json`)

```json
{
  "schema_version": "phase17.equivalence.v1",
  "requested_name": "no_domain_adaptation",
  "canonical_id": null,
  "alias_mapping": null,
  "classification": "canonical_defined_not_executed",
  "disposition": "BLOCKED_NOT_PROVEN",
  "exact_source": {
    "path": "notebooks/archive/training_original.ipynb",
    "cells": [{ "cell": 19, "lines": "53-64" }, { "cell": 18, "lines": "259-297" }]
  },
  "intervention": { "loss_overrides": { "lambda_proto": 0.0, "lambda_pl": 0.0 } },
  "source_only_proof": {
    "target_loader_constructed": "not_proven_false",
    "target_loader_forwarded": "not_proven_false",
    "target_loss_or_gradient": "not_proven_false",
    "source_only_method_identity": false,
    "status": "blocked"
  },
  "model_disposition": "not_applicable",
  "blocked_reason": "Historical runner still constructs and forwards target adaptation data.",
  "equivalence_manifest_hash": "sha256"
}
```

For `no_ctx_encoder`, the manifest must record `equivalent_to_existing_method` for resulting no-context behavior and `invalid_after_architecture_revision` for identity patching. For `full`, it must record `invalid_after_architecture_revision`. For aliases, it must record the exact mapping or `UNSUPPORTED_ALIAS`.

## 9. Artifact index schema

`artifact_index.json` records every file path, role, byte size, content hash, schema version, and producer identity. It must include:

- checkpoint, history, prediction, config, reproducibility, and equivalence manifest hashes;
- assignment and immutable precomputed-artifact hashes;
- `target_adaptation_loader_role: unlabeled_only`;
- `target_evaluation_loader_role: monitoring_only`;
- `target_labels_in_adaptation: false`;
- `publication_metrics_present: false` for synthetic/blocked lifecycle artifacts;
- `real_data_run: false` for this specification and synthetic validation boundary.

An index mismatch, missing required artifact, target-label violation, or hash drift fails validation and cannot be repaired by rewriting the manifest to match the bad bytes.
