# Phase 17 — Executable Acceptance Criteria

## Acceptance boundary

These criteria define the authorized synthetic-only implementation gate. The current synthetic implementation and validation evidence satisfies the criteria below. This does not authorize a real run or publication evaluation, does not claim that any ablation was trained on real data, and does not start Phase 18.

## A. Provenance and candidate classification

- [x] **A1 — Complete extraction:** `notebook_extraction.md` lists every candidate, helper, config/default, runner, flag, pooling helper, loss override, executed/commented call, shadowed definition, and historical result table with exact notebook cell and source-line provenance.
- [x] **A2 — Status honesty:** every item is classified as active/canonical, shadowed, helper-only, defined-not-executed, equivalent, invalid, obsolete, unsupported, or blocked. No commented call or stripped output is described as a completed ablation run.
- [x] **A3 — Conservative approval:** a `canonical_defined_not_executed` candidate cannot resolve or train without explicit approval. `unsupported`, `helper_only`, `obsolete`, `equivalent_to_existing_method`, and `invalid_after_architecture_revision` entries fail closed.
- [x] **A4 — No invented values:** the resolver rejects unresolved `lambda_proto=0.2` versus `1.0` rather than choosing a value; no unspecified hyperparameter is silently defaulted.

## B. Scientific contracts

- [x] **B1 — Questions and boundaries:** requirements identify the scientific questions, scope, non-goals, and the prohibition on real data/publication metrics in this phase.
- [x] **B2 — One intervention:** each runnable loss candidate changes exactly one named coefficient; `mean_pool`, if approved, changes only the retained aggregator. A multiple-override request fails.
- [x] **B3 — Objective fidelity:** warm and full equations exactly match the canonical objective; warm prototype/pseudo-label terms remain absent and logged zero; full terms use the established sources.
- [x] **B4 — Preserved behavior:** source-only, CORAL, MMD, CDAN, prototype-pseudo, AAGN, FasterSNN, Phase 15, and Phase 16 contracts remain unchanged under regression tests.
- [x] **B5 — Invariants:** class order, immutable source concept/Jacobian artifacts, finite tensors, dimensions/devices, fixed data identities, and inherited coefficients are enforced.

## C. Target-label firewall and monitoring

- [x] **C1 — Adaptation batch:** a target-adaptation batch containing exactly the four allowed fields `x`, `subject_id`, `subject_hash`, and `cohort` is accepted; a batch containing any forbidden field—including `y`, `label`, `label_name`, `true_label`, `c_target`, `g_bar`, `diagnosis`, stored diagnostic probabilities, concept targets, Jacobian targets, or another supervision/artifact field—is rejected before loss computation.
- [x] **C2 — Disjoint assignments:** target adaptation and target evaluation assignments are disjoint and carry separate assignment hashes.
- [x] **C3 — Monitoring-only:** target evaluation metrics are namespaced and labeled `MONITORING ONLY — NOT A TRAINING LOSS`; tests prove they do not affect gradients, optimizer/scheduler state, checkpoint choice, hyperparameter choice, or epoch count.

## D. Architecture and equivalence

- [x] **D1 — Explicit model boundary:** resolved configs identify only current PADA-3DACB and its retained components. No `ContextualROIEncoder`, `ctx_enc`, Full/Lite switch, or patched Full construction is importable or selectable.
- [x] **D2 — Mean-pool boundary:** an approved `mean_pool` run changes only aggregator behavior (`z=U.mean(dim=1)`, uniform `alpha=1/K`) and records a distinct model hash. If not approved, the resolver rejects it and the architecture action is recorded as NOT APPLICABLE.
- [x] **D3 — No duplicate trainer:** all candidates use one existing fixed-epoch trainer integration. There is no second ablation trainer loop.
- [x] **D4 — Equivalence map:** `no_domain_adaptation` is either proven Source-Only by loader/forward/output evidence or remains BLOCKED; `no_ctx_encoder` is recorded equivalent to current no-context behavior but invalid as a patch; `full` is invalid after architecture revision.
- [x] **D5 — Alias behavior:** long aliases are rejected unless an explicit one-to-one mapping is approved and the canonical exact source ID remains the output identity.

## E. Matrix, epochs, checkpoints, and resume

- [x] **E1 — Complete matrix:** a run cannot start without a predeclared complete direction/fold/seed matrix; the historical selective-fold `availability` shortcut is rejected.
- [x] **E2 — Fixed epochs:** warm/full epoch counts are explicit inputs, all declared epochs run, and early stopping is unavailable. The notebook's `5/50` values are not silently promoted to defaults.
- [x] **E3 — Checkpoint choice:** only source-validation macro-F1 can update `checkpoint_best_source_f1.pt`; target metrics cannot select checkpoints or hyperparameters; training continues after a best save.
- [x] **E4 — Resume identity:** resume succeeds only when candidate, approval, config, model variant, registry, direction, fold, seed, split assignments, target assignments, artifact identities, and hash algorithm match exactly.
- [x] **E5 — Atomic outputs:** checkpoint/history writes are recoverable and hash-verified; a partial or mismatched artifact fails closed without silently overwriting a different identity.

## F. Output and schema

- [x] **F1 — Directory contract:** outputs use `<candidate>/<source>_to_<target>/seed_<SEED>/fold_<NN>/` and contain checkpoint, history, prediction, config, reproducibility, and equivalence manifest artifacts.
- [x] **F2 — Checkpoint schema:** checkpoint records model/optimizer/scheduler/scaler state as applicable, epoch/global step, source-best value, history position, RNG/loader states, all identity hashes, and no MRI data.
- [x] **F3 — History schema:** every row records stage, epoch, step, learning rate, total loss, all active/raw/weighted components, diagnostics, source metrics, target monitoring metrics, and provenance.
- [x] **F4 — Prediction schema:** predictions contain subject/split/role identity, prediction outputs, checkpoint identity, and target monitoring designation; they do not contain training labels for target adaptation.
- [x] **F5 — Equivalence manifest:** every requested candidate, alias, disposition, approval, exact intervention, provenance, and blocked reason is serialized and hashed.
- [x] **F6 — Hashes:** required SHA-256 hashes are stable under canonical serialization and change when identity-bearing content changes.

## G. Tests and evidence

- [x] **G1 — Focused tests:** registry/resolver, composition/diagnostics, target firewall, output identity, and equivalence tests exist and pass.
- [x] **G2 — Regression tests:** protected methods and Phase 15/16 behavior pass without changed expectations.
- [x] **G3 — Synthetic lifecycle:** a deterministic synthetic smoke run demonstrates fixed warm/full lifecycle, source-only checkpoint selection, target monitoring labels, checkpoint output, interruption, and resume. It uses no real cohort or publication metric.
- [x] **G4 — Blocked behavior:** synthetic tests prove unsupported aliases, unapproved candidates, unresolved coefficient, incomplete matrix, target labels, `no_domain_adaptation` Source-Only claim, Full/contextual requests, and unauthorized real-run requests fail with structured reasons.
- [x] **G5 — Validation discipline:** implementation agents provide strict-TDD RED, GREEN, TRIANGULATE, and REFACTOR evidence for behavior changes; documentation-only artifact checks may use a justified artifact-validation exception.

## H. Explicit phase boundaries

- [x] **H1 — Phase 17 implementation gate:** no production implementation begins until this specification is independently reviewed and candidate approvals are recorded.
- [x] **H2 — Real-run gate:** no ADNI/OASIS data is loaded or trained until a separate authorization records the exact candidate matrix, data/artifact locations, compute budget, and approved command.
- [x] **H3 — Publication gate:** no publication metric, statistical comparison, table, leaderboard value, or scientific conclusion is generated by synthetic or blocked runs.
- [x] **H4 — Phase 18 boundary:** Phase 18 remains not started; no Phase 18 file, plan, implementation, evaluation, or artifact is created by Phase 17.
- [x] **H5 — Administrative boundary:** native incident #1793 and existing Phase 16 cleanup artifacts remain unchanged and continue to govern lifecycle operations.

## Minimum evidence bundle for future approval

A future implementation review must include:

1. resolved candidate and approval record;
2. exact matrix and all assignment hashes;
3. focused test output and strict-TDD evidence;
4. synthetic lifecycle output with no real-data identifiers;
5. protected-method regression output;
6. schema/hash validation output;
7. equivalence manifest proving or blocking Source-Only and documenting architecture dispositions;
8. a statement that no real ADNI/OASIS training, publication evaluation, or Phase 18 work occurred.
