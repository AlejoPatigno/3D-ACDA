# Phase 15 Independent Statistical Specification Review

Final verdict: **PASS**

Reviewer role: Kimi was requested by the action plan but no Kimi runtime agent was exposed. Fresh-context `sdd-verify` reviewers performed independent read-only reviews. The runtime fallback is explicit and does not weaken the gate.

## Review history

### Round 1 — BLOCKED

The initial review identified:

1. contradictory supplied-versus-derived `subject_hash` policy;
2. inconsistent candidate exclusion reason codes;
3. ambiguous available-with-reason semantics for zero-discordance McNemar;
4. inconsistent seven-quantity/eight-row per-class terminology.

These findings were corrected across OpenSpec and repository requirements, design, acceptance, protocol, and output schema.

### Round 2 — BLOCKED

The second review confirmed the first corrections and identified:

1. contradictory CLI required/default semantics;
2. disagreement over whether planning-artifact delivery blocked synthetic apply.

These findings were corrected. `--config` is explicit and required; inspection output roots are optional and non-writing. Planning delivery is downstream and blocked by receipt #1793, not by the synthetic implementation gate.

### Final fresh review — PASS

A new reviewer context received the exact active OpenSpec change and structured action context. It found no remaining statistical, provenance, output, ownership, or scope blocker.

## Approved contracts

- The subject is the sole statistical unit.
- Source OOF predictions are unique and never fold-averaged.
- Target probabilities average folds within seed, then every predeclared seed; partial ensembles are invalid.
- `best_source_f1` is primary; `last` is separate sensitivity; target outcomes perform no selection.
- Stable `subject_hash` is supplied only by approved exports or approved companion mappings; evaluator-local derivation is prohibited.
- One closed 19-token candidate `IssueCode` taxonomy is separate from metric-unavailability reasons.
- Twelve aggregate metrics and seven distinct per-class quantities emitted as eight named rows are explicit.
- Bootstrap uses true-class-stratified subjects, PCG64, no redraw, percentile intervals, and explicit validity counts.
- McNemar is exact two-sided; zero discordance emits `status=available`, `p=1`, `reason=null`, and `note_code=no_discordant_pairs`.
- Paired bootstrap uses identical subjects/shared indices and `prototype_pseudo - comparator` orientation.
- Holm families retain six predeclared comparisons and remain separate by direction, checkpoint policy, and statistic.
- Outputs derive only from final subject-level tables and use the exact required schema-v2 tree.
- `--config` is always explicit; dry-run and validate-only are non-writing; validate-only builds in-memory ensembles and verifies pairing.
- The plan contains 13 actions, 57 exclusively owned paths, and zero collisions.
- No training, experiment-producing configuration, immutable export, concept-analysis, manuscript, or Phase 16 path is owned.

## Implementation gate

Synthetic implementation may begin only after:

1. this PASS;
2. explicit user selection of the chain strategy;
3. measurement of the first behavior-plus-test slice at no more than 400 additions plus deletions, splitting again if necessary.

D-14-001, D-14-002, complete authorized exports, and hash-bound approval continue to block real evaluation. Native receipt issue #1793 continues to block planning-artifact delivery, archive, commit, push, PR, release, and publication.

No implementation, real evaluation, concept analysis, manuscript generation, or Phase 16 work occurred during this review.
