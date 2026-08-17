# Phase 18 Manuscript Alignment Audit

## Final alignment decision

No complete manuscript PDF or authoritative methods source is present. Repository-selected pre-run values remain frozen; manuscript-only claims remain `UNRESOLVED` until the complete source is available. No manuscript text, score, endpoint, or publication result was invented.

## Deterministic alignment rows

| Topic | Repository evidence | Manuscript evidence | Status | Freeze action |
|---|---|---|---|---|
| `lambda_proto` | Production value `1.0`; historical `0.2` is explicitly excluded from production. | Complete authoritative manuscript absent. | `UNRESOLVED` | Treat historical `0.2` as an excluded non-production discrepancy, **not `BLOCKED_CONFLICT`**; never target-tune. |
| Checkpoint criterion | `best_source_f1`, source-validation macro-F1 only; `last` is sensitivity. | Complete source absent. | `UNRESOLVED` | Preserve the selected pre-run policy; macro-AUC remains evaluation-only. |
| CORAL/MMD/CDAN | Structured selected parameters and equations are frozen in the repository ledger. | Complete parameter source absent. | `UNRESOLVED` | Preserve selected pre-run configuration; require later authoritative comparison. |
| Seeds and matrix | `[42,43,44]`; 210 training plus 210 projections. | Complete matrix source absent. | `UNRESOLVED` | Keep parser-bound directions and deterministic matrix identity. |
| Ablations | Primary, supplementary, and excluded classifications are selected pre-run and planning-only. | Complete ablation table absent. | `UNRESOLVED` | Keep later manuscript comparison in a correction ledger; do not report outcomes. |
| Architecture/endpoints/statistics | Production PADA-3DACB and approved implementation paths are preserved. | Complete source absent. | `UNRESOLVED` | Do not revive historical variants or make endpoint/publication claims. |

## Later correction ledger

When a complete manuscript becomes available, reconcile each `UNRESOLVED` row with dated source references and a maintainer disposition. The ledger must record the manuscript location, repository field, exact discrepancy, whether the repository or manuscript is authoritative, and the resulting freeze/configuration update. The historical `lambda_proto=0.2` entry remains an excluded non-production discrepancy unless a separate pre-run maintainer decision changes it.

All selected decisions were made before execution, and target outcomes were not inspected.
