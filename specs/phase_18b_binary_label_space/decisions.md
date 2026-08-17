# Phase 18B Binary Label Space Decisions

**Record status:** Implementation in progress under explicit maintainer instruction. Scientific closure and independent review pass are not yet claimed.

## Resolved decisions

| Decision | Resolution | Consequence |
|---|---|---|
| Primary task | `CN` versus `Impaired` | Use one binary task identity. |
| Class order | `CN=0`, `Impaired=1` | Never infer order alphabetically or from data. |
| ADNI vocabulary | Exact canonical `CN`, `MCI`, `AD` only | Map deterministically; reject missing, unknown, malformed, unsupported, and out-of-domain values. |
| ADNI grouping | `CN→CN`, `MCI→Impaired`, `AD→Impaired` | Preserve original diagnosis; grouping is not diagnostic equivalence. |
| ADNI duplicates/conflicts | Exclude duplicate subjects and conflicting diagnoses | No precedence, recency, majority vote, or guessing. |
| OASIS source | Supplied `oasis_cross-sectional (1).csv` with `ID` and `CDR`, paired with `preprocess-adni-oasis.ipynb` | Exact CSV/notebook hashes are bound in de-identified provenance artifacts. |
| OASIS mapping | Closed observed CDR domain `{0.0, 0.5, 1.0, 2.0}`; `0.0→CN`; positive allowed values→`Impaired`; missing/malformed/nonfinite/negative/out-of-domain→excluded | No OASIS MCI class; source CDR value and visit/person provenance are retained without raw IDs. |
| OASIS longitudinal policy | Person identity removes terminal `_MR<number>`; select lowest numeric visit (MR1 when present); count additional same-label visits as `longitudinal_duplicate`; conflicting person values exclude all visits | Splits operate on person hashes, not visit hashes. Supplied input yields 436 visits, 416 canonical persons, 20 longitudinal duplicates. |
| OASIS approval boundary | Structural evidence is verified; scientific approval remains subject to independent review and explicit closure update | Runtime admission requires structured exact-hash evidence with `evidence_verified=true` and `semantics_approved=true`; caller booleans are rejected. |
| Split disposition | `REGENERATE_BINARY_SPLITS_REQUIRED` | Binary source folds and target partitions are deterministic and person-disjoint; historical splits remain preserved. |
| Checkpoint policy | Three-class checkpoints fail closed | No partial load or classifier omission; binary metadata/hash binding is mandatory. |
| Classifier shape | `(B,2)` task logits | CE consumes two logits and IDs `{0,1}`. |
| Concept shape | `(B,K)` unchanged | Concept artifacts, ROI order, and normalizer remain unchanged. |
| CDAN | Runtime `z_dim*n_classes`; `(128,2)=256` and a distinct configuration are required contract cases | No hard-coded three-class width or detach. |
| Prototype/pseudo | Two raw logits shaped `(B,2)`, integer targets and prototype IDs `{0,1}`, with PyTorch-style `CrossEntropyLoss` | Test absent class 0 and class 1; empty accepted set returns zero loss; reject `BCEWithLogitsLoss`, sigmoid, and one-logit BCE. |
| Probability policy | float64 sum tolerance `1e-6`; float32 `1e-5` | Same policy in prediction, evaluation, and acceptance; ties choose lower index CN. |
| Undefined metrics | `null` plus reason when support/denominator is zero | Never silently coerce undefined values. |
| Legacy prediction fields | `prob_mci` and `prob_ad` rejected when active | Original diagnosis fields may remain only as provenance. |
| Identity | Six binary-bound identity families | Experiment, split, model/checkpoint, training metadata, evaluation result, and freeze reject historical three-class collisions. |
| Adaptation | Target-label free | Target adaptation cannot receive target diagnosis or binary labels. |
| Metrics | Binary accuracy, balanced accuracy, macro/weighted F1, sensitivity, specificity, MCC, Cohen kappa, ROC-AUC, PR-AUC, log loss, Brier score | Fixed confusion order; source-validation macro-F1 selects checkpoints. |
| Sensitivity | CN-versus-AD specification only | Filter original labels; no result is produced now. |
| Authorization | All freeze/execution/publication flags false; Phase 19 forbidden | Implementation and synthetic validate-only work are authorized; real execution and publication are not. |

## Implementation authorization

The maintainer explicitly instructed implementation and closure of Phase 18B after supplying the OASIS notebook and CSV. This authorizes task-scoped binary production code, de-identified metadata provenance, deterministic binary split artifacts, and synthetic/validate-only tests. It does not authorize real model training, real predictive evaluation, publication analysis, human real-run authorization, receipt edits, or Phase 19.

## Review substitution record

Kimi and Gemini CLI are unavailable. Fresh independent fallback contexts are substituted. The first post-implementation mathematical and scientific review attempts were **BLOCKED** by stale planning state, visit-level leakage, open-ended CDR acceptance, and missing `semantics_approved` enforcement. Those findings are being remediated; no independent review pass is currently claimed.

## Repository evidence

- `preprocess-adni-oasis.ipynb` contains executable OASIS ID/CDR handling, numeric coercion, invalid-value exclusion, and explicit CDR mapping.
- `oasis_cross-sectional (1).csv` contains 436 visits, 416 person stems, and observed CDR values `0`, `0.5`, `1`, `2`.
- `specs/phase_18b_binary_label_space/oasis_binary_provenance.json` and `oasis_target_partition.json` contain de-identified records, exact input hashes, mapping policy, and person-level identities only.
- No real model training, real predictive evaluation, publication metrics, or Phase 19 execution occurred.

## Remaining decisions/gates

1. Rerun independent mathematical and scientific reviews after the person-level OASIS remediation.
2. Resolve any surviving review findings.
3. Update OpenSpec state/tasks/report to the verified implementation status only after tests and reviews pass.
4. Rebuild the separate binary Phase 18 freeze identity; it must not mutate or authorize the historical Phase 18 freeze.

## Prohibited activities remain

Real ADNI/OASIS training, real predictive evaluation, publication analysis, human authorization, native receipt edits, and Phase 19 execution remain forbidden in Phase 18B.

## Final implementation and closure evidence

The implementation and validation work is complete under explicit maintainer instruction, but scientific closure is not. The final state is `PHASE18B_IMPLEMENTATION_COMPLETE_EXTERNAL_BLOCKED`.

### OASIS evidence

The supplied external inputs are bound by these hashes:

- CSV SHA256: `b223c39f83d811356675e8711e9906b1cba95ea1a110f3117a61923a72d1d1f1`
- Notebook SHA256: `588bc2a6c214fd99e2900dd45357ec2fa235cbe1670a1ab99c87c5bf2726e41b`

The structural evidence contains 436 visits, 416 canonical persons, and 20 longitudinal duplicates. The observed CDR domain is `{0, 0.5, 1, 2}`. Canonical person counts are 316 CN and 100 Impaired. The planning partition is 332 adaptation persons and 84 evaluation persons with zero person intersection. The HMAC key ID/version is metadata only; the key is never persisted.

The person-level policy and structural mapping are verified. `semantics_approved=false` remains the correct value because independent/native scientific approval is absent.

### ADNI blocker

The implemented mapping remains `CN -> CN`, `MCI -> Impaired`, and `AD -> Impaired`. The actual ADNI canonical manifest/source assignments are unavailable; `configs/data/adni.yaml` has null root/metadata paths and no repository ADNI manifest exists. No ADNI counts or hashes are inferred or claimed.

### Binary implementation evidence

The implementation covers the data spine/firewall/checkpoint boundary, five core methods, AAGN/FasterSNN, six effective loss interventions, binary prediction/evaluation, concept routing/reuse, three-class rejection, and the task-scoped runtime boundary. Binary contracts include `(B,2)` logits, CE with target IDs `{0,1}`, CDAN dimensions/gradients, prototype absent-class and empty-set behavior, probability tolerances, deterministic ties, nullable undefined metrics, and active legacy-field rejection.

Final validation is 83 focused tests and 1408 full-suite tests passing. Packaging/import/version, Ruff, `git diff --check`, and both validate-only CLIs passed. The real-run authorization checker failed closed. The final mathematical review passed, including mathematical contracts and empty-kappa null handling. The final scientific/provenance review is blocked by the missing ADNI manifest/source assignments and missing cryptographically/native-authority-bound OASIS approval.

### Remaining blockers and decisions

1. Obtain the authoritative ADNI canonical manifest/source assignments, provenance, and hashes.
2. Obtain cryptographically/native-authority-bound OASIS approval of metadata, mapping, person policy, and preprocessing provenance.
3. Complete the independent scientific/provenance review after those inputs exist.
4. Prove binary split reuse valid or regenerate person-disjoint binary splits and record exact identities/hashes.
5. Obtain native lifecycle closure; no Phase 18B receipt exists and the previous status attempt timed out with `mutation_outcome=not_started`.
6. Create and separately approve a binary freeze identity without modifying historical Phase 18 files, authorization, or receipt.

The implementation status is complete, but `oasis_gate_pass=false`, `independent_review_pass=false`, `binary_freeze=false`, `real_execution_authorized=false`, `publication_authorized=false`, and `phase_19_forbidden=true` remain in force. Phase 18B is not closed.
