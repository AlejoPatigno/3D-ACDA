# Phase 18 — Manuscript Alignment Audit

## Audit boundary

No complete manuscript PDF is present in the repository. The audit therefore compares repository documents/configurations and the available manuscript extraction, but it does not invent missing manuscript text and does not rewrite the manuscript. Statuses are:

- `MATCH`: authoritative sources agree.
- `MANUSCRIPT_OUTDATED`: authoritative manuscript text conflicts with a newer approved repository contract.
- `REPOSITORY_OUTDATED`: authoritative manuscript text is newer and the repository has not adopted it.
- `UNRESOLVED`: source/equation/ownership is incomplete or conflicting; no side may be changed by inference.

The last two “outdated” statuses are vocabulary, not a license to assign them without a complete authoritative manuscript and maintainer decision.

## Alignment table

| Topic | Repository evidence | Manuscript evidence | Status | Freeze action |
|---|---|---|---|---|
| Public method name | `PADA-3DACB` in model and proposed-method docs | No complete PDF; extraction names the proposed method | MATCH for available repository sources; manuscript completeness remains limited | Preserve name; do not infer publication claim. |
| Class order | `CN=0`, `MCI=1`, `AD=2` across AGENTS/configs/evaluation | Extraction records same order | MATCH | Keep fixed order. |
| Cohorts/directions | ADNI/OASIS and both directions | Partial method extraction only | UNRESOLVED | Require authoritative protocol confirmation. |
| Architecture | Explicit no-context model; contextual path excluded | Historical notebook contains former contextual path and identity helper | UNRESOLVED | Keep current repository architecture; do not revive historical variant. |
| `lambda_proto` | Primary path/config `1.0`; later helper `0.2` | D-14-001 records manuscript discrepancy | UNRESOLVED | Do not choose; require explicit decision and hash. |
| Epoch policy | Primary DA path `5` warm/`50` full; fixed epochs | Available extraction records `5/50`; generic config has `20/30` | UNRESOLVED until publication protocol binds the method-specific config | Preserve fixed epochs; no early stopping. |
| Best checkpoint | Source-validation macro-F1 only | D-14-002 records manuscript macro-AUC tie-break wording | UNRESOLVED | Repository invariant controls engineering; publication use waits for decision. |
| Core method inventory | Seven protected methods in Phase 15 config | No complete manuscript inventory | UNRESOLVED | Do not add or remove methods by name inference. |
| Publication ablation subset | Six Phase 17 synthetic candidates; no publication selection | No complete manuscript subset | UNRESOLVED | Keep subset outside active matrix. |
| CFS/ACS/PCS/QIS | No verified equations; blocked in Phase 16/17 | Names/descriptions only in extraction | UNRESOLVED | Do not implement or report scores. |
| Statistical endpoints | Phase 15 protocol defines predictive metrics/bootstrap/Holm for its approved scope | No complete manuscript statistical protocol | UNRESOLVED | Require protocol approval before publication analysis. |
| Preprocessing/artifact provenance | Canonical notebooks and immutable-artifact rules | Partial extraction, no complete manuscript methods | UNRESOLVED | Require exact hashes and approved provenance. |
| Forbidden historical variants | Repository explicitly excludes them from runnable inventory | Manuscript evidence unavailable | UNRESOLVED | Do not add rows or rewrite manuscript. |

## Outdated-status handling

A future complete manuscript review MAY assign `MANUSCRIPT_OUTDATED` or `REPOSITORY_OUTDATED` only with exact quoted source, version/date, maintainer authority, and a migration decision. This phase assigns neither status to a scientific value because the complete manuscript is absent. The unresolved lambda and checkpoint discrepancies remain blockers.

## Required alignment evidence before publication

Provide the complete manuscript/methods source, exact equations for all named endpoints, method/ablation list, checkpoint wording, seed/fold policy, and versioned maintainer disposition. Bind the decision record hash to the real-run and publication gates. Until then, this audit is a blocking planning artifact, not a publication approval.
