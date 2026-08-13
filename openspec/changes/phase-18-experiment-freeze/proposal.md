# Proposal: Phase 18 Scientific Experiment Freeze

## Problem statement

The repository has completed the Phase 18 preflight audit but does not yet have a single, reviewable protocol that binds the publication experiment matrix, scientific values, provenance, feasibility evidence, resource budget, and real-run authorization boundary. The existing evidence contains a material `lambda_proto=1.0` versus `0.2` discrepancy, no complete real split/artifact identity, no hardware budget observation, and no complete manuscript protocol.

Without an explicit freeze, a later implementation could silently select a coefficient, reuse selective folds, include unauthorized ablations, let target outcomes influence decisions, or report synthetic/blocked evidence as a real publication result.

## Outcome

Create a documentation-only Phase 18 freeze package that:

- preserves the seven protected methods, both transfer directions, folds `0..4`, and the repository seed policy;
- preserves fixed epochs and source-validation macro-F1-only checkpoint selection;
- records the unresolved lambda discrepancy and rejects matrix/gate authorization until authoritative resolution;
- enumerates unresolved checked-in CORAL/MMD/CDAN parameters and forbids invented defaults;
- keeps publication ablation selection unresolved until human approval;
- defines parser-bound direction IDs, separate training/projection rows, content-level manifest intersection checks, versioned canonical JSON, synthetic-only contract feasibility, and deterministic matrix, state, provenance, hash, target-isolation, failure/retry, resource, CLI, manuscript-alignment, and authorization contracts;
- leaves real execution, publication, and Phase 19 fail-closed.

## Scope

The change creates the owned Phase 18 specification files under `specs/phase_18_experiment_freeze/` and matching OpenSpec proposal, design, task, state, and contract files under this change directory.

## Non-goals

This proposal does not implement runtime code, CLI code, configuration, tests, data loading, preprocessing, artifact generation, training, evaluation, publication analysis, manuscript edits, or Phase 19. It does not modify `.git/gentle-ai`, native receipts, or unrelated dirty workspace changes.

## Safety and rollback

The change is documentation-only. Rollback is a path-scoped revert of the owned specification/OpenSpec artifacts; no runtime or data artifact is mutated. If any scientific value remains unresolved, the state remains blocked rather than guessing or partially authorizing execution.

## Approval boundary

`phase_18_authorized: true` means protocol-freeze planning is permitted. It does not mean the scientific freeze is approved. `real_execution_authorized: false`, `publication_authorized: false`, and `phase_19_forbidden: true` remain explicit until separate human and independent-review decisions resolve all blockers.
