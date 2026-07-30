# Run Phase 16 concept evaluation safely

Phase 16 provides a read-only concept-evaluation package and a deterministic synthetic lifecycle. The repository CLI intentionally does **not** run real ADNI/OASIS evaluation; real cohort execution remains a separate, human-controlled Kaggle workflow.

## Quick path

1. Copy `configs/evaluation/concepts.yaml` outside the repository.
2. Set `analysis_mode: synthetic_test_only` in the copy.
3. Run dry-run, validate-only, evaluate, and reuse against temporary roots.

```bash
python scripts/evaluate_concepts.py \
  --config /tmp/concepts-synthetic.yaml \
  --runs-root /tmp/phase16/runs \
  --artifact-root /tmp/phase16/artifacts \
  --both-directions --all-pada-methods --include-sensitivity \
  --dry-run

python scripts/evaluate_concepts.py \
  --config /tmp/concepts-synthetic.yaml \
  --runs-root /tmp/phase16/runs \
  --artifact-root /tmp/phase16/artifacts \
  --both-directions --all-pada-methods --include-sensitivity \
  --validate-only

python scripts/evaluate_concepts.py \
  --config /tmp/concepts-synthetic.yaml \
  --runs-root /tmp/phase16/runs \
  --artifact-root /tmp/phase16/artifacts \
  --output-root /tmp/phase16/results \
  --both-directions --all-pada-methods --include-sensitivity \
  --bootstrap-replicates 100 --bootstrap-seed 17
```

For reuse, add the completed output path to `completed_reuse.approved_output_roots` in the copied configuration, then run the same selectors with `--reuse`. Reuse verifies the exact file set, manifest, artifact index, and hashes without changing file mtimes.

## Mode contract

| Mode | Synthetic behavior | Real behavior | Writes results |
|---|---|---|---|
| `--dry-run` | Validates configuration and selectors | Discovers the declared checkpoint/artifact matrix; missing entries fail closed | No |
| `--validate-only` | Executes deterministic metric kernels | Blocked by the real-evaluation authorization gate | No |
| Evaluate | Produces the complete fixture-only output tree atomically | Closed in Phase 16 | Yes, synthetic only |
| `--reuse` | Verifies one approved completed tree | Only approved completed trees are accepted | No |

## Scientific contract

| Area | Definition |
|---|---|
| Concept fidelity | `c_hat` versus immutable precomputed `c_target`: MAE, RMSE, bias, Pearson, and Spearman |
| Anatomical consistency | `c_hat` versus immutable precomputed `g_bar`, reported separately from fidelity |
| Head agreement | Predictive metrics per head, top-1 agreement, Jensen-Shannon divergence, and configured `L_cons` direction |
| ROI stability | Profile-specific rank correlation, standard deviation, explicit top-k Jaccard, and rank dispersion |
| Class profiles | Descriptive CN/MCI/AD means and subject-bootstrap intervals |
| Method inference | `prototype_pseudo` versus `{source_only, coral, mmd, cdan}` with paired diagnosis-stratified subject bootstrap and four-comparator Holm families |

AAGN and FasterSNN are `not_applicable_no_pada3dacb_concept_head`; they never enter concept comparisons.

## Input and provenance rules

- `c_target` and `g_bar` must be precomputed artifacts. Inference never regenerates either tensor.
- Every subject record validates fixed labels, domains, probability normalization, predictions, ROI dimensions, and lowercase SHA-256 metadata.
- Candidate validation issues exclude that candidate from inference.
- OOF source aggregation requires the complete expected subject population for every seed.
- Target aggregation is fold-first, then seed; immutable targets must agree exactly.
- Target labels are used only for posthoc evaluation and descriptive stratification. They never enter training, optimization, scheduling, or checkpoint selection.

## Output tree

Each direction and checkpoint policy contains:

- subject-level machine-readable output;
- the 11 required summary tables;
- five required PNG figures;
- detailed fidelity, anatomy, agreement, stability, profile, and paired-comparison tables.

Publication is atomic: all ordinary artifacts are staged first, `artifact_index.json` is self-excluding, and `evaluation_manifest.json` is written last.

## Explicit exclusions

- No real ADNI/OASIS data are read by the synthetic lifecycle.
- No training or checkpoint mutation occurs.
- No result is a publication claim.
- CFS, ACS, PCS, and QIS remain blocked because no authoritative equations were found. The code does not invent them.
- Phase 17 behavior is not present.
