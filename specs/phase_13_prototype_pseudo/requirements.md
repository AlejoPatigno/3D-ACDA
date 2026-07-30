# Phase 13 Requirements

Status: COMPLETE — implementation may proceed only after independent specification review approves these requirements.

## Requirement: Notebook-derived method identity

The system MUST implement the canonical PADA-3DACB prototype and pseudo-label adaptation behavior extracted from `notebooks/archive/training_original.ipynb`, not the pre-existing placeholder configuration fields and not later ablation-only overrides.

### Scenario: Reject placeholder behavior

- GIVEN configuration fields named for prototype or pseudo-label behavior contain `null` or placeholder values
- WHEN a real Phase 13 run is validated
- THEN the system MUST require the explicit canonical values from this specification
- AND MUST NOT silently treat placeholders as approved implementation.

## Requirement: Prototype loss contract

The system MUST compute `L_proto = L_proto_align + lambda_sep * L_proto_sep` from current mini-batch embeddings `z_src` and `z_tgt` without prototype cache, EMA, momentum, or normalization.

### Scenario: Align only mutually present classes

- GIVEN source labels and accepted target pseudo-labels contain only a subset of classes
- WHEN prototype alignment is computed
- THEN source and target prototypes MUST be per-class means over current-batch `z`
- AND alignment MUST average squared Euclidean distances only over classes valid in both source and accepted target batches
- AND absent classes MUST contribute zero to the loss.

### Scenario: Source separation

- GIVEN at least two source classes are present in the current source batch
- WHEN source separation is computed
- THEN the system MUST average `relu(proto_margin - ||mu_i - mu_j||_2)^2` over unordered present-class pairs
- AND multiply it inside `L_proto` by `lambda_sep`.

## Requirement: Pseudo-label selection and loss

The system MUST create target pseudo-labels from concept-head target logits using `softmax`, argmax confidence, and a fixed threshold `tau_p`.

### Scenario: Confident target rows

- GIVEN target concept-head logits `logits_c_tgt` with shape `(B_T, C)`
- WHEN pseudo-label loss is computed
- THEN probabilities MUST be `softmax(logits_c_tgt, dim=-1)`
- AND pseudo labels MUST be `argmax` classes
- AND rows MUST be accepted where `max probability >= tau_p`
- AND the loss MUST be PyTorch cross-entropy mean over accepted rows.

### Scenario: No target row accepted

- GIVEN no target row has confidence `>= tau_p`
- WHEN pseudo-label loss is computed
- THEN the system MUST return a scalar zero tensor on the logits device and dtype-compatible with the computation
- AND MUST report zero accepted target rows.

## Requirement: Combined objective and stage behavior

The system MUST use source-only warm-up followed by full source-target adaptation with the exact coefficient structure extracted from the notebook.

### Scenario: Warm stage

- GIVEN training is in warm stage
- WHEN the total loss is computed
- THEN the system MUST compute only source losses: `L_cls_z`, `L_cls_c`, `L_concept`, `L_anat`, and `L_cons`
- AND MUST apply warm multipliers: `warm_lambda_z=0.1`, `warm_lambda_c=1.0`, `warm_lambda_cbm=1.0`, `warm_lambda_anat=1.0`, `warm_lambda_cons=0.0` for the canonical executed config
- AND MUST report `L_proto=0`, `L_pl=0`, and `n_confident_T=0`.

### Scenario: Full stage

- GIVEN source and target adaptation batches
- WHEN full loss is computed
- THEN the system MUST compute source core losses plus `lambda_proto * L_proto` and `lambda_pl * L_pl`
- AND MUST use canonical executed coefficients `lambda_proto=1.0`, `lambda_pl=0.1`, `tau_p=0.95`, `proto_margin=1.0`, `lambda_sep=0.1` unless a test-only override is explicitly marked as synthetic.

## Requirement: Target-label firewall

The system MUST NOT consume target diagnosis labels, target concept targets, or target anatomical tensors in adaptation loss computation.

### Scenario: Adaptation batch contains only target images

- GIVEN a target adaptation batch with only key `x`
- WHEN full adaptation training runs
- THEN prototype and pseudo-label adaptation MUST use model outputs from target `x`
- AND MUST NOT require or read target `y`, `c_target`, or `g_bar`.

## Requirement: Tensor contracts and gradients

The system MUST validate tensor shapes and preserve notebook gradient behavior.

### Scenario: Tensor shapes

- GIVEN source logits `(B_S, C)`, target concept logits `(B_T, C)`, source embeddings `(B_S, C_t)`, target embeddings `(B_T, C_t)`, source labels `(B_S,)`, source concepts `(B_S, K)`, source concept targets `(B_S, K)`, and source anatomy `(B_S, K)`
- WHEN the Phase 13 objective is computed
- THEN the system MUST reject incompatible shapes, non-floating logits/embeddings/concepts, invalid source labels, and non-finite tensors.

### Scenario: Gradient firewall

- GIVEN accepted target pseudo-label rows
- WHEN backpropagation runs
- THEN gradients MUST flow through accepted target concept logits for `L_pl` and through selected source/target embeddings for `L_proto`
- AND MUST NOT flow through stored target labels because they are not inputs.

## Requirement: Checkpoint and resume implications

The system MUST treat prototype and pseudo-label adaptation as stateless across batches and epochs.

### Scenario: Resume state

- GIVEN a checkpoint is created during or after Phase 13 training
- WHEN adaptation state is serialized
- THEN no prototype cache, moving average, pseudo-label cache, or threshold schedule state MUST be required
- AND existing trainer/model/optimizer/scaler/history checkpoint policy MUST remain responsible for ordinary resume behavior.
