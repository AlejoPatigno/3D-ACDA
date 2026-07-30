# Phase 16 — Tasks

## Action graph

```yaml
actions:
  - id: phase15-closure-and-concept-audit
    agent: opencode
    depends_on: []
    owns:
      - AGENTS.md
      - specs/phase_16_concept_validation/decisions.md
    description: |
      Close T-15-16 and T-15-17; reconcile Phase 15 status; correct AAGN naming;
      record native receipt #1793; inventory concept outputs, artifacts and checkpoints;
      confirm no Phase 16 implementation existed before authorization.

  - id: concept-contract-extraction
    agent: claude-code
    depends_on: [phase15-closure-and-concept-audit]
    owns:
      - specs/phase_16_concept_validation/manuscript_extraction.md
      - specs/phase_16_concept_validation/requirements.md
      - specs/phase_16_concept_validation/design.md
      - specs/phase_16_concept_validation/tasks.md
      - specs/phase_16_concept_validation/acceptance.md
      - specs/phase_16_concept_validation/metric_protocol.md
      - specs/phase_16_concept_validation/output_schema.md
    description: |
      Extract exact concept/anatomy/head semantics from notebooks and manuscript;
      extract CFS/ACS/PCS/QIS when supported; specify aggregation and metrics;
      document unresolved definitions.

  - id: independent-scientific-review
    agent: kimi
    depends_on: [concept-contract-extraction]
    owns:
      - specs/phase_16_concept_validation/spec_review.md
    description: |
      Reject invented score definitions; verify target-label isolation;
      verify subject-level aggregation; verify no causal overclaiming;
      approve or block implementation.

  - id: implement-concept-discovery-and-inference
    agent: codex
    depends_on: [independent-scientific-review]
    owns:
      - src/pada3dacb/evaluation/concepts/__init__.py
      - src/pada3dacb/evaluation/concepts/schemas.py
      - src/pada3dacb/evaluation/concepts/dataset.py
      - src/pada3dacb/evaluation/concepts/discovery.py
      - src/pada3dacb/evaluation/concepts/provenance.py
      - src/pada3dacb/evaluation/concepts/inference.py
      - tests/test_concept_schemas.py
      - tests/test_concept_dataset.py
      - tests/test_concept_discovery.py
      - tests/test_concept_provenance.py
      - tests/test_concept_inference.py
    description: |
      Implement read-only artifact/checkpoint discovery;
      implement evaluation dataset; implement no-grad subject inference;
      validate K, ROI order and hashes.

  - id: implement-concept-aggregation-and-fidelity
    agent: codex
    depends_on: [implement-concept-discovery-and-inference]
    owns:
      - src/pada3dacb/evaluation/concepts/aggregation.py
      - src/pada3dacb/evaluation/concepts/fidelity.py
      - src/pada3dacb/evaluation/concepts/anatomy.py
      - tests/test_concept_aggregation.py
      - tests/test_concept_fidelity.py
      - tests/test_concept_anatomy.py
    description: |
      Implement OOF and fold/seed aggregation;
      implement concept fidelity; implement anatomical consistency;
      implement unavailable-state handling.

  - id: implement-agreement-stability-profiles
    agent: codex
    depends_on: [implement-concept-aggregation-and-fidelity]
    owns:
      - src/pada3dacb/evaluation/concepts/agreement.py
      - src/pada3dacb/evaluation/concepts/stability.py
      - src/pada3dacb/evaluation/concepts/class_profiles.py
      - tests/test_concept_agreement.py
      - tests/test_concept_stability.py
      - tests/test_concept_class_profiles.py
    description: |
      Implement head agreement; implement ROI stability;
      implement descriptive class profiles; avoid causal terminology.

  - id: implement-statistics-figures-tables
    agent: codex
    depends_on: [implement-agreement-stability-profiles]
    owns:
      - src/pada3dacb/evaluation/concepts/statistics.py
      - src/pada3dacb/evaluation/concepts/figures.py
      - src/pada3dacb/evaluation/concepts/tables.py
      - tests/test_concept_statistics.py
      - tests/test_concept_figures.py
      - tests/test_concept_tables.py
    description: |
      Reuse subject bootstrap; implement paired method comparisons;
      implement Holm correction; generate complete non-cherry-picked tables and figures.

  - id: independent-mathematical-verification
    agent: gemini-cli
    depends_on: [implement-statistics-figures-tables]
    owns:
      - tests/test_concept_metrics_reference.py
      - tests/test_concept_statistics_reference.py
      - tests/test_concept_edge_cases.py
    description: |
      Verify metric equations; verify constant-ROI behavior;
      verify aggregation; verify bootstrap unit; verify method pairing;
      verify no target adaptation or gradients.

  - id: report-cli-integration
    agent: opencode
    depends_on: [independent-mathematical-verification]
    owns:
      - src/pada3dacb/evaluation/concepts/report.py
      - scripts/evaluate_concepts.py
      - configs/evaluation/concepts.yaml
      - tests/test_concept_report.py
      - tests/test_concept_cli.py
      - tests/test_concept_output_schema.py
      - tests/test_concept_reuse.py
    description: |
      Implement CLI; implement real gate; implement dry-run and validate-only;
      implement manifests, output directories and reuse.

  - id: complete-integration-and-regression-tests
    agent: codex
    depends_on: [report-cli-integration]
    owns:
      - tests/concept_phase16_fixtures.py
      - tests/test_concept_integration.py
      - tests/test_concept_modes.py
      - tests/test_concept_boundaries.py
      - tests/test_concept_regressions.py
      - tests/test_all_methods_regression_phase15.py
      - tests/test_phase15_predictive_evaluation_regression.py
    description: |
      Test all PADA methods; test both directions; test folds/seeds/checkpoints;
      protect Phase 15 and all training behavior.

  - id: documentation
    agent: claude-code
    depends_on: [complete-integration-and-regression-tests]
    owns:
      - docs/CONCEPT_EVALUATION.md
      - docs/PHASE16_REPORT.md
      - docs/IMPLEMENTATION_AUDIT.md
    description: |
      Document implemented equations; distinguish observational validation
      from causal interpretation; document unavailable scores and real-run blockers;
      avoid performance and clinical claims.

  - id: final-audit
    agent: kimi
    depends_on: [documentation]
    owns:
      - specs/phase_16_concept_validation/final_audit.md
    description: |
      Audit scientific validity; audit ROI and concept provenance;
      audit target-label firewall; audit previous-phase regressions;
      verify no Phase 17 work.

  - id: final-validation
    agent: opencode
    depends_on: [final-audit]
    owns: []
    description: |
      Run complete tests and linting; run synthetic concept-evaluation lifecycle;
      write final Engram summary; stop before Phase 17.
```

## Task details

### T-16-01: Phase 15 closure and concept audit
- Close T-15-16 (final-validation) and T-15-17 (OpenSpec mirrors)
- Reconcile Phase 15 status: final_audit.md PASS, agent_plan.yaml ownership 14/60/0
- Correct A-A-GAN → AAGN in all docs
- Record native receipt #1793 as administrative blocker
- Inventory: concept outputs, c_target, g_bar, alpha, checkpoints, artifacts
- Confirm no Phase 16 production files existed pre-authorization

### T-16-02: Manuscript extraction
- Read `notebooks/archive/training_original.ipynb` for concept/anatomy/head semantics
- Read `notebooks/archive/precompute_original.ipynb` for concept targets and normalizer
- Read `docs/PROPOSED_METHOD_EXPERIMENT.md` for manuscript methodology
- Search for CFS, ACS, PCS, QIS definitions
- Record exact equations or mark BLOCKED
- Output: `manuscript_extraction.md`

### T-16-03: Requirements and design
- Complete `requirements.md` with all FR/NFR
- Complete `design.md` with tensor contracts, metric equations, config
- Output: `requirements.md`, `design.md`

### T-16-04: Tasks, acceptance, metric protocol, output schema
- Complete `tasks.md` (this file)
- Complete `acceptance.md` with executable criteria
- Complete `metric_protocol.md` with exact equations
- Complete `output_schema.md` with table/figure specs
- Complete `agent_plan.yaml` with action graph

### T-16-05: Independent scientific review
- Reviewer: kimi
- Reject invented score definitions
- Verify target-label isolation
- Verify subject-level aggregation
- Verify no causal overclaiming
- Output: `spec_review.md` with PASS/BLOCKED

### T-16-06: Concept discovery and inference
- `schemas.py`: Concept-specific dataclasses, enums, validation
- `dataset.py`: Read-only concept-evaluation dataset
- `discovery.py`: Checkpoint/artifact discovery with provenance
- `provenance.py`: Hash validation, artifact assignment
- `inference.py`: No-grad forward pass, tensor extraction
- Focused tests for each module

### T-16-07: Aggregation and fidelity
- `aggregation.py`: OOF, fold-ensemble, seed aggregation
- `fidelity.py`: Concept fidelity metrics (MAE, RMSE, bias, correlations)
- `anatomy.py`: Anatomical consistency metrics (weighted/unweighted)
- Focused tests with synthetic fixtures

### T-16-08: Agreement, stability, profiles
- `agreement.py`: Head agreement (predictive, top-1, JS, consistency direction)
- `stability.py`: ROI stability (Spearman rank, Jaccard, dispersion)
- `class_profiles.py`: Class-conditional descriptive profiles
- Focused tests

### T-16-09: Statistics, figures, tables
- `statistics.py`: Subject bootstrap, paired comparisons, Holm correction
- `figures.py`: Heatmaps, matrices, profiles (matplotlib/seaborn)
- `tables.py`: CSV generation for all required tables
- Focused tests

### T-16-10: Independent mathematical verification
- Reference tests for metric equations
- Constant-ROI behavior
- Aggregation correctness
- Bootstrap unit (subject-level, not ROI)
- Method pairing (ROI)
- No target adaptation/gradients

### T-16-11: Report, CLI, integration
- `report.py`: Manifest, output tree, atomic write, reuse
- `scripts/evaluate_concepts.py`: CLI with all flags
- `configs/evaluation/concepts.yaml`: Configuration
- Dry-run, validate-only, real gate
- Integration tests: all PADA methods, both directions, folds/seeds/checkpoints
- Regression tests: Phase 15, all prior methods

### T-16-12: Documentation
- `docs/CONCEPT_EVALUATION.md`: User-facing guide
- `docs/PHASE16_REPORT.md`: Complete report with evidence
- `docs/IMPLEMENTATION_AUDIT.md`: Technical audit

### T-16-13: Final audit
- Scientific validity audit
- ROI and concept provenance audit
- Target-label firewall audit
- Previous-phase regression audit
- No Phase 17 work verification
- Output: `final_audit.md`

### T-16-14: Final validation
- `pip install -e .`
- Import check
- Full pytest (focused + regression)
- Ruff check
- `git diff --check`
- Synthetic lifecycle: dry-run, validate-only, evaluate, reuse
- Engram summary
- Stop before Phase 17

## File ownership summary

| Module | Owner |
|--------|-------|
| `concepts/schemas.py` | codex |
| `concepts/dataset.py` | codex |
| `concepts/discovery.py` | codex |
| `concepts/provenance.py` | codex |
| `concepts/inference.py` | codex |
| `concepts/aggregation.py` | codex |
| `concepts/fidelity.py` | codex |
| `concepts/anatomy.py` | codex |
| `concepts/agreement.py` | codex |
| `concepts/stability.py` | codex |
| `concepts/class_profiles.py` | codex |
| `concepts/statistics.py` | codex |
| `concepts/figures.py` | codex |
| `concepts/tables.py` | codex |
| `concepts/report.py` | opencode |
| `scripts/evaluate_concepts.py` | opencode |
| `configs/evaluation/concepts.yaml` | opencode |
| `docs/CONCEPT_EVALUATION.md` | claude-code |
| `docs/PHASE16_REPORT.md` | claude-code |
| `docs/IMPLEMENTATION_AUDIT.md` | claude-code |
| Tests | codex (implementation), gemini-cli (reference) |

## Dependencies

```
phase15-closure-and-concept-audit
    → concept-contract-extraction
        → independent-scientific-review
            → implement-concept-discovery-and-inference
                → implement-concept-aggregation-and-fidelity
                    → implement-agreement-stability-profiles
                        → implement-statistics-figures-tables
                            → independent-mathematical-verification
                                → report-cli-integration
                                    → complete-integration-and-regression-tests
                                        → documentation
                                            → final-audit
                                                → final-validation
```

## Milestones

| Milestone | Tasks | Gate |
|-----------|-------|------|
| M1: Spec complete | T-16-01 through T-16-04 | Independent review PASS |
| M2: Core implementation | T-16-06 through T-16-09 | Mathematical verification PASS |
| M3: Integration | T-16-10 through T-16-11 | All tests PASS |
| M4: Documentation | T-16-12 | Final audit PASS |
| M5: Final validation | T-16-13 through T-16-14 | All checks PASS |

## Notes

- Every action writes compact Engram record
- No two active actions own the same file
- Codex owns all production implementation and focused tests
- Gemini-cli owns independent reference/edge-case tests
- Kimi owns independent scientific/statistical review
- Opencode owns orchestration, CLI, config, final commands
- Phase 15 utilities reused, not duplicated
- No training modules modified
- No Phase 17 files created