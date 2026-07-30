# Phase 15 Predictive Evaluation

## Safety first

Phase 15 evaluates approved prediction exports. It does **not** train models, select checkpoints from target labels, regenerate splits, or create concept/Jacobian artifacts. The checked-in real-evaluation gate is closed. No real evaluation is authorized until all four gate hashes in `configs/evaluation/predictive.yaml` are independently resolved and bound.

Start with inspection modes. They validate configured inputs and never create `--output-root`:

```bash
python scripts/evaluate.py \
  --config configs/evaluation/predictive.yaml \
  --runs-root runs \
  --both-directions \
  --all-methods \
  --dry-run

python scripts/evaluate.py \
  --config configs/evaluation/predictive.yaml \
  --runs-root runs \
  --both-directions \
  --all-methods \
  --validate-only
```

The default mode is evaluation. It requires `--output-root` and an explicit `--bootstrap-seed`. With the current real configuration it fails closed at the authorization gate; that is expected behavior, not permission to bypass the gate.

## Selectors and policies

Exactly one direction selector is required: `--direction {adni_to_oasis,oasis_to_adni}` or `--both-directions`. Exactly one method selector form is required: repeat `--method` or use `--all-methods`.

Approved methods are:

- `source_only`
- `coral`
- `mmd`
- `cdan`
- `prototype_pseudo` (the PADA-3DACB method)
- `aagn`
- `faster_snn`

The primary policy is `best_source_f1`, selected only from source-validation macro-F1. `--include-sensitivity` adds the separate `last` policy. Policies and directions are never pooled. Target-derived selection is prohibited.

## Input contract

The evaluator accepts the two configured schema families:

- shared exports for Source-Only, CORAL, MMD, CDAN, and PADA-3DACB;
- combined baseline exports for AAGN and Faster-SNN.

Every included candidate must prove method, direction, cohorts, seed, fold, logical checkpoint, checkpoint epoch, experiment/model/training hashes, split and partition hashes, atlas/ROI ordering when applicable, and fixed class order `(CN,MCI,AD)=(0,1,2)`. Missing or conflicting provenance excludes the affected candidate. Source-Only must prove target-evaluation membership.

Canonical subject rows require a stable, approved, supplied `subject_hash`. Phase 15 never invents or derives hashes. Raw subject identifiers are forbidden in outputs, logs, metadata, and errors.

Target ensembles average folds within each configured seed and then average all configured seeds. Every subject must have every required fold and seed. Source validation remains out-of-fold and unique per subject. Incomplete ensembles, duplicate rows, incompatible labels, invalid probabilities, and policy mismatches fail closed.

## Statistical contract

The statistical unit is the subject. Computation uses NumPy `float64` and fixed labels `[0,1,2]`. The evaluator emits 12 aggregate metrics and eight named per-class rows (seven distinct quantities because recall and sensitivity are aliases).

Uncertainty uses deterministic class-stratified subject bootstrap with `PCG64`; default `B=10000`, explicit seed, no redraw of invalid replicates, and a 95% successful-replicate threshold. Pairwise comparisons use PADA-3DACB as the predeclared reference, exact two-sided McNemar, paired stratified bootstrap differences oriented `prototype_pseudo-comparator`, and separate six-slot Holm families. Undefined values are explicit nulls with stable reasons, never zero-filled.

See `specs/phase_15_predictive_evaluation/statistical_protocol.md` for normative equations.

## Output and reuse

Evaluation writes directly to the exact `--output-root`; no identity directory is inserted. Required root files include the completion manifest, resolved configuration, provenance report, method status, computational summary, and sanitized log. Each selected direction/policy tree contains inclusion, canonical subject predictions, metrics, confidence intervals, paired comparisons, four confusion artifacts per method, and a publication table.

Writes use a same-filesystem staging tree and publish the completion manifest last. Existing output fails unless `--overwrite` or `--reuse` is selected. Overwrite refuses unknown paths and never modifies inputs. Reuse is read-only and succeeds only when identity, configuration, authorization, versions, inputs, required files, and hashes match exactly.

The authoritative layout and columns are in `specs/phase_15_predictive_evaluation/output_schema.md`.

## Current limitations

- The real-evaluation gate is closed; no real outputs or performance estimates exist.
- Required ADNI/OASIS exports and gate-resolution hashes were not supplied during Phase 15 implementation.
- Computational values absent from source records remain `not_recorded` nulls.
- Target evaluation is monitoring/reporting only and cannot affect training or model selection.
- Concept evaluation, manuscript generation, Phase 16 work, publication, and delivery are outside this task.

