# Proposal: Phase 18B Binary Publication Label Space

## Intent

Phase 18B will replace the planned three-class publication task with a binary classification task: **CN vs Impaired**, using the fixed class order `CN = 0` and `Impaired = 1`. This is a task-level grouping for publication experiments, not a claim that MCI and AD are diagnostically equivalent.

The proposal permits only documentation/specification maintenance and synthetic contract-test planning before the gates pass. It does not authorize production implementation, real ADNI/OASIS execution, publication analysis, publication results, native lifecycle claims, receipt mutation, or Phase 19 execution.

## Problem statement

Phase 18 currently plans publication experiments around the historical three-class label space (`CN`, `MCI`, `AD`). The intended publication task is now binary, so the existing planning identity, experiment matrix, and hashes no longer describe the intended scientific task. Continuing from those artifacts without an explicit migration contract could mix incompatible labels, splits, checkpoints, and experiment identities while presenting the result as one coherent protocol.

OASIS creates an additional hard blocker. The repository does not currently identify an actual canonical OASIS root or metadata file, and the legacy loader collapses every nonzero numeric CDR value to historical `AD`. That behavior is evidence of prior implementation only; it is not an approved binary-label scientific contract.

## Users and scientific context

The primary users are the researchers and reviewers who must prepare, execute, audit, and reproduce the PADA-3DACB publication experiments across ADNI and OASIS. They need one explicit binary task identity that:

- preserves subject-level diagnostic provenance;
- prevents target labels from entering adaptation decisions;
- makes label grouping reviewable rather than implicit;
- rejects incompatible checkpoints and split identities;
- distinguishes documentation/specification planning status from authorization to run real cohorts or publish results.

## Product and scientific outcome

After Phase 18B documentation/specification planning:

- the primary publication task is represented consistently as `CN` versus `Impaired`;
- the class order is fixed as `CN = 0`, `Impaired = 1` and is never derived alphabetically;
- ADNI records retain their original diagnosis while mapping `CN -> CN`, `MCI -> Impaired`, and `AD -> Impaired`;
- OASIS records can enter the binary task only after canonical metadata and metadata-generation provenance establish approved semantics;
- binary experiment identities, matrices, splits, hashes, and checkpoints are distinguishable from historical three-class artifacts;
- protected training, adaptation, anatomical, concept, and provenance invariants remain unchanged except for classifier cardinality.

## Current-state gap

| Area | Current state | Required Phase 18B state |
| --- | --- | --- |
| Publication task | Phase 18 planning uses three classes | Binary `CN` vs `Impaired` |
| ADNI grouping | Historical labels are distinct | Preserve original label and derive the approved binary task label |
| OASIS configuration | `configs/data/oasis.yaml` has `root: null` and `metadata_csv: null` | Actual approved canonical manifest and provenance are required before production semantics |
| OASIS legacy loader | Requires an ID/Subject ID field and `CDR`; skips missing CDR; maps `CDR == 0` to `CN` and every nonzero numeric CDR to historical `AD` | Treat as evidence only; approve binary semantics from actual canonical metadata before any post-gate production implementation |
| Split evidence | No real manifests or hashes are available | `REGENERATE_BINARY_SPLITS_REQUIRED` unless prior assignments are proven binary-valid |
| Checkpoint compatibility | Existing checkpoints may have three-class classifier tensors | Reject old three-class checkpoints; never silently partially load them |
| Historical identity | Phase 18 matrix/hash represents the three-class task | Preserve it as historical evidence and mark it superseded in later Phase 18B artifacts |

## Business and scientific rules

### Binary label contract

1. The primary publication task is binary: `CN` versus `Impaired`.
2. The class order is fixed: `CN = 0`, `Impaired = 1`.
3. ADNI task grouping is fixed:
   - original `CN` maps to task label `CN`;
   - original `MCI` maps to task label `Impaired`;
   - original `AD` maps to task label `Impaired`.
4. Grouping MCI and AD under `Impaired` defines the publication task only. It must not be described as diagnostic equivalence.
5. Every derived task label must retain the original cohort label and sufficient provenance to audit the mapping.
6. Ambiguous, unsupported, or missing diagnoses are excluded rather than guessed. No OASIS MCI category may be invented.

### OASIS hard precondition

**Status: blocked pending canonical OASIS manifest and metadata-generation provenance.**

Production OASIS binary semantics must not be implemented or approved until the actual canonical metadata is available and reviewed. The review must establish at least the authoritative subject identifier, source diagnosis/CDR fields, missing-value policy, accepted numeric/category domain, duplicate or longitudinal-record policy, derivation provenance, and unambiguous mapping into `CN` or `Impaired`.

The current `load_oasis_label_map` behavior—skip missing CDR, map `CDR == 0` to `CN`, and map every nonzero numeric CDR to historical `AD`—is legacy evidence only. It cannot be adopted as final binary semantics without validation against the approved manifest and its generation provenance.

### Migration and compatibility invariants

The migration must preserve:

- original label provenance alongside the derived binary label;
- the target-label firewall and disjoint `target_adaptation`/`target_evaluation` partitions;
- fixed epoch counts and continued training after best-checkpoint saves;
- source-validation macro-F1 as the only best-checkpoint selection criterion;
- concept and anatomical artifacts, including atlas/artifact identity and Phase 5 ROI order;
- the approved concept normalizer;
- approved CORAL and MMD mathematics;
- the PADA-3DACB architecture except for binary classifier cardinality;
- protected output/provenance behavior, updated only where binary task identity must be explicit.

Old three-class checkpoints are incompatible with the binary classifier and must fail closed. Silent partial loading, classifier-key omission, or other compatibility bypasses are prohibited.

Any future task classifier must use PyTorch-style `CrossEntropyLoss` with two raw logits shaped `(B,2)` and integer class targets `{0,1}`. This is not `BCEWithLogitsLoss`, does not apply sigmoid, and is not one-logit BCE.

### Split and identity rules

- The current split disposition is `REGENERATE_BINARY_SPLITS_REQUIRED`.
- Existing subject assignments may be reused only if evidence proves that they are valid for the binary cohort, stratification, leakage, and target-partition contracts.
- No such real manifests or hashes currently exist, so this proposal invents none.
- Binary split generation must produce new binary-scoped provenance and identities after cohort semantics are approved.
- Phase 18's three-class planning identity, matrix, and hash are conceptually superseded by Phase 18B. They remain preserved historical artifacts and must be marked superseded by later Phase 18B artifacts; they are not deleted or rewritten by this proposal.

## Scope and affected areas

Phase 18B may document the contracts for, and only after both gates pass may production implementation address, the minimum changes needed to represent and enforce the binary task across:

- canonical label vocabulary, mappings, and provenance schemas;
- cohort inventory and manifest validation;
- split generation and split identity;
- classifier output cardinality and checkpoint compatibility checks;
- experiment matrix, configuration, and canonical hashing;
- evaluation schemas and macro-F1 computation for the fixed binary order;
- CLI validation and fail-closed errors;
- documentation and synthetic contract-test planning required to define these contracts; no production code or test implementation before both gates pass;
- documented Phase 19 interface design only; Phase 19 execution remains forbidden.

The bounded user exception permits Phase 18, Phase 18B, and Phase 19 documentation/specification planning only before the gates pass. Production implementation is permitted only after OASIS semantics approval and both substituted independent fallback reviews pass the complete checklist. It does not authorize real cohort execution or weaken any acceptance boundary below.

## First-slice boundaries

The first product slice will:

1. specify the binary vocabulary, ADNI grouping, provenance, incompatibility, split-regeneration, and supersession contracts;
2. specify the fail-closed OASIS precondition and validation evidence required to unblock its semantics;
3. document binary contracts; no production code path may be implemented before both gates pass;
4. plan synthetic contract tests only; no test implementation or execution is authorized before both gates pass;
5. document Phase 19 interface design only; Phase 19 execution remains forbidden.

The first slice must remain documentation/specification-only before both gates pass. Production implementation is permitted only after BOTH OASIS semantics approval AND both substituted independent fallback reviews pass the complete checklist. Phase 19 interface design may be documented only; Phase 19 execution remains forbidden.

## Edge cases

- Missing, nonnumeric, malformed, or out-of-domain OASIS CDR values are excluded or rejected according to the later approved manifest contract; they are never coerced into `Impaired` by default.
- Conflicting diagnoses for one subject, duplicate metadata rows, or longitudinal diagnosis changes require an explicit approved subject/visit policy before inclusion.
- Unknown source labels and already-derived labels without original provenance fail closed.
- A binary dataset with only one represented class is invalid for training, stratification, or macro-F1 acceptance.
- Empty cohort partitions, insufficient subjects for required folds, or impossible stratification block split generation rather than changing fold policy silently.
- Prior split assignments that introduce leakage or violate binary stratification are regenerated even if subject IDs overlap.
- A three-class checkpoint presented to a binary model is rejected with an explicit compatibility error.
- Partial checkpoint loading must not conceal classifier cardinality mismatch.
- Target diagnoses remain unavailable to adaptation training even when binary labels simplify the task.
- Historical three-class outputs remain identifiable as historical and must not be merged with binary results.

## Non-goals

This proposal does not:

- claim that MCI and AD are diagnostically equivalent;
- invent OASIS MCI labels or infer ambiguous OASIS diagnoses;
- approve the legacy OASIS CDR mapping as final semantics;
- obtain, search for, download, inspect, or execute real ADNI/OASIS data;
- create real manifests, split assignments, artifact hashes, experiment results, or publication metrics;
- run training, evaluation, publication analysis, or Phase 19;
- change fixed epochs, checkpoint-selection policy, target isolation, ROI order, concept normalizer, CORAL/MMD mathematics, or architecture beyond classifier cardinality;
- delete or rewrite Phase 18 historical artifacts;
- edit native lifecycle state, `.git/gentle-ai`, receipts, or the approved receipt `review-1d63ad8511d6bbf5`;
- claim a native lifecycle gate, receipt, publication authorization, or real-run authorization.

## Implications and impact

- **Scientific interpretation:** Publication language and schemas must consistently describe a task grouping, not diagnostic equivalence.
- **Data governance:** Original labels and metadata provenance become mandatory audit fields for derived binary labels.
- **Reproducibility:** New binary identities, matrices, splits, and hashes prevent accidental comparison or resumption across incompatible task definitions.
- **Model compatibility:** The classifier head changes cardinality; three-class checkpoints become intentionally incompatible.
- **Operations:** OASIS implementation remains blocked until maintainers provide and approve the canonical manifest and generation provenance.
- **Support and review:** Errors must explain whether failure comes from unresolved cohort semantics, excluded diagnoses, invalid splits, or incompatible checkpoints.
- **Downstream planning:** Phase 19 interface design may be documented against the binary contract but cannot be executed under this proposal.

## Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Binary grouping is misreported as diagnostic equivalence | Require task-grouping language and retain original diagnoses |
| Legacy OASIS behavior becomes an accidental scientific rule | Keep OASIS semantics hard-blocked pending actual canonical metadata and provenance |
| Ambiguous OASIS cases are forced into a class | Exclude ambiguity; prohibit invented MCI and default nonzero-CDR assumptions |
| Historical and binary experiment identities are mixed | Generate binary-scoped identities and mark historical Phase 18 artifacts superseded without deleting them |
| Old checkpoints load with an invalid classifier | Enforce cardinality/task compatibility and prohibit silent partial loading |
| Reused splits distort class balance or leak subjects | Default to `REGENERATE_BINARY_SPLITS_REQUIRED`; allow reuse only with explicit proof |
| Target labels influence adaptation after migration | Preserve and test the target-label firewall and partition separation |
| Scope exception is mistaken for execution authorization | Repeat the explicit no-real-run, no-publication, no-lifecycle-claim boundary in phase artifacts |

## Rollback

This Phase 18B planning package changes only newly owned proposal, specification, design, task, state, and Engram artifacts under the Phase 18B scope. It can be rolled back by removing or reverting those owned artifacts as a coherent package. Any post-gate production implementation must provide path-scoped rollback for binary-specific code and configuration while preserving historical three-class evidence. Rollback must not mutate unrelated dirty workspace changes, native lifecycle state, receipts, or real data.

## Unresolved decisions

The following decisions remain intentionally unresolved and must not be guessed:

1. Which actual OASIS manifest and metadata-generation record are canonical and approved.
2. Which OASIS source fields and values define an unambiguous binary mapping, including the treatment of nonzero CDR values, missing values, duplicates, and longitudinal changes.
3. Which deterministic binary split-generation parameters and resulting identities apply after both cohort mappings are approved.
4. The exact versioned schema/hash migration details needed to distinguish binary artifacts from preserved three-class artifacts.

Items 1 and 2 are hard preconditions for production OASIS semantics. Planning may define validation contracts, but implementation must not encode final OASIS mapping behavior until those decisions are resolved from actual approved metadata.

## Proposal question round

An interactive question round was not available during this delegated phase. The fixed decisions supplied for Phase 18B are treated as approved proposal inputs. Before OASIS semantics can be finalized, maintainers should answer these product/scientific questions from the canonical evidence:

1. What exact OASIS manifest and metadata-generation provenance are approved for publication use?
2. Which source values unambiguously mean `CN` or `Impaired`, and which values must be excluded as ambiguous?
3. What subject/visit rule governs duplicate or longitudinal OASIS records with changing or conflicting values?
4. What evidence would be sufficient to prove an old subject assignment is binary-valid instead of regenerating it?

Current assumption: none of these answers may be inferred from the null configuration or the legacy loader. Until reviewed answers exist, OASIS production semantics remain blocked and binary splits remain marked for regeneration.

## Success criteria

The proposal is successful when subsequent specification and design artifacts:

- define one fixed binary task and class order;
- preserve original-label provenance and the target-label firewall;
- encode the fixed ADNI grouping without implying diagnostic equivalence;
- keep OASIS semantics explicitly blocked pending approved canonical evidence;
- require regenerated binary splits unless reuse is proven valid;
- reject old three-class checkpoints without silent partial loading;
- preserve all listed training, concept, anatomical, adaptation, and architecture invariants;
- preserve and later mark Phase 18 three-class artifacts as superseded rather than deleting them;
- keep real execution, publication claims, native lifecycle claims, receipt edits, and Phase 19 execution outside the authorized boundary.

## Acceptance boundary

Acceptance of this proposal authorizes only the next SDD planning phases and documentation/specification maintenance plus synthetic contract-test planning before the gates. It does **not** authorize production implementation and does not authorize:

- real ADNI or OASIS execution;
- use of unapproved OASIS semantics;
- real split/hash creation from cohort data;
- publication analysis, results, or claims;
- Phase 19 execution (only documented interface design is permitted);
- native lifecycle gate or receipt claims;
- edits to `.git/gentle-ai`, any receipt, or approved receipt `review-1d63ad8511d6bbf5`.

Production OASIS semantics remain **BLOCKED PENDING CANONICAL MANIFEST AND METADATA-GENERATION PROVENANCE**.

## Next recommended phase

Proceed to **SDD specification (`sdd-spec`)** for `phase-18b-binary-label-space`. The specification should convert these decisions into testable requirements while retaining the OASIS hard blocker, the requirement for both substituted independent fallback reviews, and all execution/authorization boundaries.
