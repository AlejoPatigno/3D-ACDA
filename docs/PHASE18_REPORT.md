# Phase 18 Report — Implementation Closure

## Executive decision

**Final closure status: `PHASE18_COMPLETE_BUT_BLOCKED_FOR_REAL_EXECUTION`**.

Phase 18 implementation is complete and focused-verified. The corrected specification package is approved for planning/specification purposes only. Scientific freeze is not approved, the real-run and publication gates remain closed, native lifecycle approval is pending, and final repository-wide validation is incomplete because the full test suite timed out.

| Control | Current value | Meaning |
|---|---:|---|
| `phase_18_authorized` | `true` | Phase 18 protocol and implementation work is authorized |
| `freeze_approved` | `false` | Scientific freeze is not approved |
| `real_execution_authorized` | `false` | Real ADNI/OASIS execution is forbidden |
| `publication_authorized` | `false` | Publication analysis and claims are forbidden |
| `phase_19_forbidden` | `true` | Phase 19 cannot begin |
| Real-run gate | `blocked` | Scientific, data, resource, identity, review, and authorization blockers remain |
| Publication gate | `blocked` | Separate publication authorization is absent |
| OpenSpec state | `blocked_for_real_execution` | Implementation complete; real transition blocked |

## Status boundaries

| Area | Closure statement |
|---|---|
| Specification approval | The corrected planning/specification package received bounded approval; this is not scientific freeze or real-run approval. |
| Implementation completion | WU1-WU5 and bounded corrections are complete and verified by the focused Phase 18 suite. |
| Scientific freeze | Not approved. Unresolved scientific values remain blocking. |
| Real-run authorization | Not granted. No real data path was opened. |
| Publication authorization | Not granted. No publication analysis or result claim was produced. |
| Final repository closure | Incomplete: the full suite timed out, Kimi was unavailable, and no native lifecycle receipt/approval was run. |

## Agents and independent review

- **Codex** implemented the Phase 18 work units and bounded corrections.
- **`review-risk`** and **`review-resilience`** provided the implementation review lenses and drove bounded corrections.
- The **Gemini-mapped fallback** was executed through `gentle-ai-explore`/`gentle-ai-verify` because the mapped reviewer path was unavailable.
- **Kimi was unavailable.** `gentle-ai-verify` performed the fresh independent final verification instead. Its acceptance remained partial because the full suite timed out and closure artifacts were stale before this consolidation; it did not silently resolve scientific blockers.
- No native review lifecycle command was run for this documentation/state consolidation. No receipt or approval is fabricated.

## Implementation delivered

The implementation package contains the following bounded work units and corrections:

1. Canonical `phase18.canonical-json.v1` serialization, typed schema primitives, freeze identity, and strict authorization booleans.
2. Deterministic matrix and exact-byte provenance validation, including content-level target assignment disjointness.
3. Synthetic-only feasibility contracts and machine-readable resource-budget boundaries.
4. Fail-closed freeze/authorization validation and read-only planning CLIs.
5. Phase 18 integration and CLI regression coverage.
6. Bounded corrections for authority/evidence binding, identity, seed/matrix integrity, feasibility evidence, aggregate provenance, and target-isolation firewall behavior.

The static publication package and CLI paths have no trainer, optimizer, or MRI-loader imports. No real training, evaluation, data loading, artifact regeneration, publication analysis, or Phase 19 work occurred.

## Scientific resolution ledger

The implementation preserves the scientific boundary; it does not infer values from target outcomes.

- No target-guided values were selected. Target data cannot choose hyperparameters, methods, checkpoints, folds, seeds, or publication subsets.
- `lambda_proto` remains **`BLOCKED`** between `0.2` and `1.0`; neither value is authorized.
- CORAL, MMD, and CDAN parameters remain unresolved, including CORAL weight; MMD weight/kernel/bandwidth or scale; and CDAN weight, GRL schedule/strength, discriminator architecture, and optimization settings.
- The publication ablation subset and ablation decisions remain unresolved and require explicit human selection.
- Seed planning is exactly **`[42]`**; no additional seed is invented.
- Checkpoint policy is `best_source_f1` for the primary path and `last` for the separate sensitivity projection; projection rows do not retrain.
- The planned matrix contains **70 training rows** and **70 checkpoint-projection rows** (`7 × 2 × 5 × 1` for seed `[42]`). These are planning rows, not completed real results.
- The target firewall separates adaptation from evaluation: adaptation accepts only `x`, `subject_id`, `subject_hash`, and `cohort`; evaluation is monitoring-only and cannot affect loss, gradients, optimizer/scheduler state, checkpoint selection, or candidate selection.

## Identity, provenance, and artifact limits

The implementation includes the canonical JSON profile, exact-byte SHA-256 helpers, schema identity, matrix/projection identity, provenance validation, target firewall, and implementation-level tests. It does **not** provide real-data closure.

Still unresolved or unavailable are:

- real split and assignment manifests and their hashes;
- verified content-level intersection for real target-adaptation/evaluation assignments;
- immutable atlas, ROI, concept-normalizer, target, and Jacobian artifacts and hashes;
- canonicalization implementation identity and native approval of its conformance evidence;
- real data-access/privacy records, configured paths, command identity, and human authorization;
- observed hardware, VRAM/RAM, storage, worker/concurrency, retry, wall-time, and conservative/nominal resource approval;
- real feasibility observations and real provenance hashes;
- authoritative manuscript equations, endpoints, statistical definitions, and any remaining checkpoint tie-breaking decisions.

Synthetic feasibility is engineering-only. It cannot establish real throughput, memory fit, storage capacity, statistical validity, publication readiness, or real resource closure.

## Validation evidence

| Check | Observed result |
|---|---|
| Focused Phase 18 suite | `python -m pytest -q tests/phase_18/` — exit 0, **139 passed**, 1 `PytestCacheWarning`, 6.91s |
| Editable install | `python -m pip install -e .` — exit 0 |
| Import/version | Import and version check — exit 0; version **0.1.0** |
| Ruff | `python -m ruff check .` — exit 0 |
| Scoped whitespace check | Phase 18 scoped `git diff --check` — exit 0 |
| Global whitespace check | `git diff --check` — exit 2 only for pre-existing `AGENTS.md:928` trailing whitespace; it was not modified |
| Full regression | `python -m pytest -q` attempted with a 1200-second timeout; timed out around 27%; **no pass claim** |
| Publication preparation CLI | `prepare_publication_run.py` print-matrix, print-blockers, feasibility-only, and validate-only modes fail closed and print blockers; no real data or training |
| Real-run checker | `check_real_run_authorization.py` exits 1 and prints `PASS — FAIL-CLOSED AUTHORIZATION VERIFIED` (Windows console rendered the em dash incorrectly); authorization remains false |
| Import boundary | Static publication package/CLIs contain no trainer, optimizer, or MRI-loader imports |

The full suite timeout is the reason final repository-wide validation remains incomplete. The focused suite is the implementation evidence; it is not a full-regression pass.

## OpenSpec, Engram, and native lifecycle state

OpenSpec state is recorded in `openspec/changes/phase-18-experiment-freeze/state.yaml` as:

- `status: blocked_for_real_execution`;
- `current_phase: implementation_complete`;
- `execution_mode: implementation_only`;
- `real_run_gate: blocked`;
- `publication_gate: blocked`;
- `freeze_approved: false`;
- native lifecycle receipt and approval: pending and not run.

The original planning prerequisites remain preserved in `tasks.md`, with a separate implementation closure graph assigning one owner per action. Documentation and both progress artifacts now contain the consolidated closure evidence. A compact Engram completion record was saved under the project-scoped Phase 18 implementation-closure topic; OpenSpec remains the file-based source of truth.

## Remaining blockers and required next transition

Before any real-run request, the maintainer must resolve every applicable blocker and obtain separate native lifecycle approval. In particular, the maintainer must resolve the scientific ledger, method parameters, ablations, real manifests and artifact hashes, target assignment disjointness, canonicalization identity, privacy/data access, observed resource budget, manuscript definitions, independent review, and human authorization.

The native lifecycle receipt must be created and validated by the authorized lifecycle process; it was not created or modified here. Real execution does not imply publication authorization, and Phase 19 remains forbidden.

## Explicit no-runtime/no-real-execution statement

This closure changed documentation and state artifacts only. No runtime source, tests, configs, scripts, native receipts, `.git/gentle-ai`, or real-data artifacts were edited by this action. No real ADNI/OASIS data, training, evaluation, provenance inspection, feasibility run, publication analysis, native review lifecycle command, publication authorization, or Phase 19 work was performed.
