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

## Metric and aggregation contract

The evaluator applies these equations after subject-level aggregation:

- Concept fidelity and anatomy consistency use `MAE = mean(abs(x - y))`, `RMSE = sqrt(mean((x - y)^2))`, and `bias = mean(x - y)` globally, per subject, and per ROI. Pearson and Spearman are emitted per ROI only when defined.
- Anatomical consistency compares `c_hat` with immutable `g_bar`; it is reported separately from concept fidelity. A canonical weighted anatomy score is `sum_k(w_k * MAE_k)` only when canonical weights are available.
- Head agreement reports predictive metrics separately from fidelity, top-1 agreement/disagreement, mean Jensen-Shannon divergence, the configured consistency-loss direction, and per-class disagreement counts. `JS(p,q) = 0.5*KL(p||m) + 0.5*KL(q||m)` where `m = (p + q) / 2`.
- Source outputs are out-of-fold and unique by subject. Target outputs are averaged fold-first, then seed; repeated folds are never independent subjects and transfer directions are never pooled.
- ROI stability keeps fidelity, anatomy, predicted-concept, and attention profiles separate. It reports pairwise rank correlation, per-ROI dispersion, explicit top-k Jaccard overlap, and rank dispersion.
- Class profiles are descriptive CN/MCI/AD summaries with subject-level bootstrap hooks, not unrestricted ROI-by-ROI inference.

Undefined correlations remain unavailable with an explicit reason: `constant_roi`, `insufficient_samples`, or `numerical_error`. Missing or conflicting provenance excludes a candidate rather than producing a fabricated value. Bootstrap counts retain requested, successful, invalid, and unavailable replicates.

## Validation evidence and limits

The WU-09 focused integration/regression command was run against the current workspace:

```text
python -m pytest tests/test_concept_integration.py tests/test_concept_modes.py tests/test_concept_boundaries.py tests/test_concept_regressions.py tests/test_all_methods_regression_phase16.py tests/test_proposed_method_cli.py -q --basetemp=artifacts/pytest-tmp-phase16
23 passed; one Windows pytest cache-permission warning.
```

A full `python -m pytest -q --basetemp=artifacts/pytest-tmp-phase16-full` run exceeded the 180-second execution window and is not represented as passing evidence. `python -m ruff check .` and `git diff --check` passed. These results validate the synthetic/documented boundary only; they are not scientific results from ADNI/OASIS data.

## Explicit exclusions

- No real ADNI/OASIS data are read by the synthetic lifecycle.
- No training, adaptation, optimizer, checkpoint, or target-artifact mutation occurs.
- Target labels are posthoc-only and never enter adaptation, checkpoint selection, or method selection.
- No result is a publication claim; causal importance, biomarkers, and disease mechanisms are not inferred.
- CFS, ACS, PCS, and QIS remain `BLOCKED` because no authoritative equations were found. The code does not invent them.
- Phase 17 behavior is not present or started.
- Native receipt #1793 remains an administrative delivery blocker for review lifecycle, commit, push, PR, archive, release, and publication actions.
