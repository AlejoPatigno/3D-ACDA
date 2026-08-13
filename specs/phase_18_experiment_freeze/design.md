# Phase 18 — Scientific Freeze Design

## Technical approach

Treat Phase 18 as a read-only protocol compiler, not an experiment runner. The artifacts define one immutable scientific contract, one deterministic matrix identity, one provenance/hash envelope, one synthetic-only feasibility procedure, and one fail-closed authorization manifest. Runtime implementation remains a later action and cannot consume an unresolved freeze.

```text
canonical docs/configs/notebook audit
              |
              v
 scientific resolution ---> matrix/schema ---> feasibility + budget
              |                 |                    |
              +----------> real-run gate <-----------+
                              |
                 authorized command only (future)
```

## Architecture decisions

| Decision | Choice | Rationale / rejected alternative |
|---|---|---|
| Scientific authority | Primary repository path plus explicit Phase 15–17 contracts | Avoids promoting later notebook helpers or manuscript names over active evidence. |
| Matrix | Seven protected methods × parser IDs `adni_to_oasis`/`oasis_to_adni` × folds 0–4 × seed 42; 70 training rows plus 70 linked `last` projections | Preserves complete coverage, exact parser identity, one training invocation per cell, and prevents selective-fold or duplicate-training shortcuts. |
| `lambda_proto` | Keep unresolved until an external decision binds one value | `1.0` is the primary path; `0.2` is a later helper/manuscript discrepancy. The matrix and gate reject authorization while unresolved; target metrics cannot arbitrate. |
| Ablations | Keep Phase 17 candidates as inventory evidence; publication subset unresolved | Synthetic approval is not publication approval. This prevents an unauthorized subset from becoming a claim. |
| Checkpointing | Fixed epochs; source-validation macro-F1 only; target monitoring isolated | Matches the protected training contract and rejects manuscript tie-break drift. |
| Provenance | SHA-256 over versioned `phase18.canonical-json.v1` and exact file bytes, with content-level manifest intersections | Makes assignments, artifacts, code, environment, and commands auditable and resume-safe; aggregate hashes alone cannot prove disjointness. |
| Feasibility | Synthetic faithful shapes/contracts only; synthetic timing and resource observations remain engineering-only | Provides contract evidence without loading real MRI, claiming real throughput, or resolving real timing/resource fields. |

## Data and state flow

1. Read canonical evidence and assign every value one of the four required classes.
2. Resolve method, direction, fold, seed, checkpoint, assignment, and artifact identities without reading target outcomes.
3. Emit one `row_kind: training` row per method/direction/fold/seed and one linked `row_kind: checkpoint_projection` row; require exactly one training invocation per cell and never emit `COMPLETED` during this phase.
4. Validate synthetic shapes/contracts, target firewall, fixed-stage equations, provenance schema, canonicalization vectors, content-level manifest intersections, and failure transitions.
5. Require all authorization hashes and human approvals before any future real-data loader is opened.

## Current file changes

This action creates only the explicitly owned Phase 18 specification files and matching OpenSpec artifacts. No `src/`, `configs/`, `scripts/`, `tests/`, `docs/`, `.git/`, or runtime output path is modified.

## Contracts

The freeze schema binds method identity, exact intervention/configuration, direction, fold, seed, checkpoint policy, split/assignment hashes, immutable artifact hashes, code/environment identity, command hash, authorization state, and output state. Target adaptation contains no diagnosis labels; target evaluation is monitoring-only. Resume is permitted only for an identical identity; hash drift, missing provenance, or partial matrix coverage fails closed.

## Verification and rollout

This phase uses artifact inspection only; no test command or feasibility probe is run. An independent specification review must approve the documents before implementation planning can transition. A later implementation may add focused schema/firewall/lifecycle tests, then run synthetic feasibility, then request a separate human real-run authorization. No publication analysis or Phase 19 follows automatically.

## Open questions

- Which authoritative decision resolves `lambda_proto=0.2` versus `1.0`?
- Which human-approved publication ablation subset, if any, is included?
- What are the real split/artifact hashes, privacy-approved paths, hardware observations, resource budget, and final command hash?
- Are manuscript checkpoint tie-breaking and publication score equations supplied by an authoritative source?
