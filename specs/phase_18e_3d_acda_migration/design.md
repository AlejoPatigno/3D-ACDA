# Phase B — 3D-ACDA Migration Design

## Design decision

Use a compatibility-preserving migration boundary around the existing package contracts. The future canonical method is displayed as **3D-ACDA** while retaining internal ID `mmd` and existing package identity `pada3dacb`. The boundary must separate:

1. immutable historical/live execution;
2. prospective canonical method and ablation contracts;
3. read/report-time display aliases; and
4. a later, separately approved rename operation.

No implementation is part of Phase B. The design is an executable target for a future phase, not evidence that these components exist or have passed tests.

### Phase C safe-sequence boundary

The user has explicitly authorized Phase C to start now, but only as a non-breaking reporting-only change. Before editing, the implementation owner must record the verified frozen source commit/tag and notebook boundary, a documented import/reachability check proving that the live notebook training path does not import or reach the modified reporting modules, and exclusive non-interference proof covering training, model, loss, adaptation, configuration, manifest generation, run directories, output paths, checkpoint/resume identity, and stored historical artifacts.

Phase C owns only a pure display-name resolver and report-time projection layer. It may resolve approved aliases while reading/rendering reports, but it must preserve requested spelling, canonical internal IDs, canonical configuration hashes, run directories, output paths, checkpoint/resume identity, and historical outputs. The frozen live family runtime, including currently running seeds `43` and `44`, remains immutable. Historical files must never be rewritten. Phase C implementation, tests, and review are not complete merely because this design authorizes the safe start. This authorization is not approval for a live run, Phase D, or a rename.

The live provenance anchors are distinct: the user-verified source commit SHA `aafe817365cb4068f167b398c776aff4c3b1f021` identifies the source tree, while the untracked frozen notebook's SHA-256 identifies notebook content and must be recorded separately before activation. The frozen live family is seeds `42/43/44`; seeds `43/44` are running by user attestation within protected boundaries and activation prerequisites, not completed-result evidence.

## Protected architecture and scientific boundary

```text
3D input
  -> 3D encoder
  -> 102-ROI representation/tokenization
  -> independent ROI refinement
  -> learned attention aggregator
  -> dual paths:
       latent path -> diagnosis head + latent UDA regularizer
       concept path -> concept bottleneck + MRI-derived supervision
                    -> Jacobian anatomy consistency
```

The canonical method keeps learned attention. `mean_pool` is a single explicitly named prospective intervention, not a Full/Lite switch and not a contextual encoder. The contribution is the 3D anatomically constrained architecture and dual-path supervision; MMD remains a standard latent UDA regularizer.

The existing MMD source is outside the write boundary and must remain untouched. Any future adapter calls it through the existing contract and must not reimplement or wrap it in a way that changes mathematical behavior.

## Compatibility-preserving identity layers

```text
requested spelling
       |
       v
read/report alias resolver  ----> requested_name + canonical_id + resolution record
       |                                      |
       v                                      v
canonical internal ID  ----------------> config/hash/checkpoint identity
       |
       v
existing package/runtime boundary
```

### Identity rules

- `mmd` remains the internal ID and resolves to display `3D-ACDA`.
- `source_only` resolves to display `3D-ACDA Source-Only`.
- `coral`, `cdan`, and `prototype_pseudo` remain explicit comparator IDs.
- AAGN and FasterSNN remain independent baseline identities.
- Alias resolution occurs when reading or rendering a report, not while writing an output path or mutating stored manifests.
- A requested alias is retained as presentation metadata; canonical ID, output path, checkpoint identity, and config hash remain stable.
- Unknown, case-altered, ambiguous, or unapproved aliases fail closed.
- `prototype_pseudo` is comparator-only. `no_proto` and `no_pl` are historical/supplementary and cannot be promoted by display naming.

## Future component boundaries

Phase C implements only the read/report-time resolver and projection described above. The broader registry, configuration, adapter, ablation, data, and execution boundaries below remain prospective contracts; they are not Phase C permission to change runtime behavior, configuration, manifests, or training paths.

### 1. Canonical registry and resolver

A future registry is the sole source of canonical IDs, display labels, roles, dispositions, and approved aliases. Each entry should include:

- canonical internal ID;
- display label;
- role (`primary`, `source_only`, `comparator`, or `independent_baseline`);
- exact source provenance;
- architecture and loss contract;
- alias set and approval reference;
- configuration fields and hash inputs;
- legacy/supplementary disposition where applicable; and
- blocked reason when not runnable.

The resolver must return a structured immutable record containing requested spelling, canonical ID, display label, alias decision, role, resolved configuration hash, model identity, and evidence status. It must not infer a candidate from a nearby name.

### 2. Configuration and hash boundary

Canonical configuration is resolved before data loading or training. The future manifest must distinguish:

- requested name;
- canonical internal ID;
- display name;
- alias-resolution version;
- inherited frozen values;
- explicit intervention;
- model variant identity;
- source/target assignment hashes;
- artifact hashes; and
- resolved configuration hash.

The config hash MUST be computed from canonical identity and resolved values, not from a presentation alias. Equivalent read-time aliases therefore produce the same canonical hash and output identity. A changed canonical ID, intervention, assignment, artifact, or inherited value must produce a distinct hash and fail resume compatibility.

No production configuration beyond the frozen notebook values is selected in this design. Historical defaults remain discrepancy records until an authorized owner resolves them.

### 3. MMD adapter boundary

The future canonical `mmd` path calls the existing MMD implementation with the frozen live-family contract:

- biased squared mixture-RBF estimator;
- diagonal terms included;
- arithmetic mixture averaging;
- float32 pairwise computation;
- no normalization;
- no median heuristic; and
- no final clamp.

The live notebook records `lambda_MMD=1` and `[1,2,4,8,16]`. The adapter must preserve those values for the frozen family and must reject or clearly classify any future unresolved alternative rather than silently adopting historical package defaults.

`no_mmd` is a separate prospective composition. It changes the MMD coefficient to zero but retains the target-aware execution path where the approved future contract requires it. The adapter must record target-loader/forward/RNG and manifest semantics so Source-Only cannot be inferred from coefficient equality.

### 4. Ablation composition boundary

The future primary registry contains:

| ID | Single intervention | Status in Phase B |
|---|---|---|
| `no_mmd` | `lambda_MMD = 0` | Prospective primary; not executed. |
| `no_cons` | Disable only consistency term | Prospective primary; exact inherited coefficient still requires authorized resolution. |
| `no_concept` | Disable only concept supervision | Prospective primary; exact inherited coefficient still requires authorized resolution. |
| `no_anat` | Disable only Jacobian anatomy consistency | Prospective primary; exact inherited coefficient still requires authorized resolution. |
| `mean_pool` | Replace learned attention with approved mean aggregator | Prospective primary; architecture approval required. |

Every future candidate must preserve all non-intervened components, data assignments, optimizer/scheduler, fixed epochs, checkpoint criterion, and output identity rules. A candidate must never be implemented by copying a second trainer.

`no_proto` and `no_pl` remain legacy/supplementary. `prototype_pseudo` is an explicit comparator, not the canonical 3D-ACDA identity. Phase 17's blocked/invalid/equivalent dispositions remain in force for `no_domain_adaptation`, `no_ctx_encoder`, `identity_ctx`, and `full`.

### 5. Data and target-label firewall boundary

The future data contract has two target partitions:

```text
target cohort
  +--> target_adaptation: unlabeled, disjoint
  +--> target_evaluation: labeled, monitoring-only, disjoint
```

The adaptation batch contract allows only `x`, `subject_id`, `subject_hash`, and `cohort`. Diagnosis labels, binary labels, concept targets, Jacobian targets, diagnostic probabilities, and other supervision fields are forbidden. Rejection must happen at the boundary; fields must not be silently dropped.

Before any run, manifests are hash-verified and parsed subject identities are checked for an empty intersection. Aggregate hashes alone are insufficient. Target evaluation may be read by a separate monitoring path but cannot affect loss, gradients, optimizer, scheduler, checkpoint, resume, HPO, or candidate selection.

### 6. Evaluation and reporting boundary

Evaluation produces subject-level aggregates for both directions. Slice-level observations may be retained as diagnostics but cannot substitute for the subject-level reporting unit. The report resolver maps internal IDs to display names at read time and emits:

- requested method spelling;
- canonical internal ID;
- display label;
- role and comparator classification;
- alias resolution decision;
- configuration and artifact hashes; and
- evidence status.

No renderer may rewrite historical output paths or change an internal ID to achieve the public label.

## Regression and validation architecture

Phase C may start before the regression matrix is complete. The focused matrix below is implementation/review evidence to be produced during Phase C and is a prerequisite for Phase D/live execution, not a prerequisite to starting the reporting-only layer:

| Regression family | Required proof |
|---|---|
| Exact MMD | Reference outputs and edge cases prove biased squared mixture-RBF, diagonals, arithmetic averaging, float32 pairwise calculation, and absence of normalization/median heuristic/clamp. |
| Target isolation | Adaptation rejects forbidden fields; partitions are disjoint by subject and hash; target labels never reach training or selection. |
| Legacy comparators | `coral`, `cdan`, `prototype_pseudo`, AAGN, and FasterSNN preserve equations, IDs, paths, and checkpoint behavior. |
| `no_mmd` distinction | A zero-MMD run remains distinct from Source-Only in loaders/forwards, RNG, manifest, output, checkpoint, and resume semantics. |
| Alias behavior | Aliases resolve only at read/report time; output path, canonical ID, and stored hash remain unchanged. |
| Hash identity | Requested alias and canonical ID resolve to the same canonical config hash; any contract change invalidates the hash. |
| Resume | Matching canonical identity resumes; alias variation does not alter identity; candidate, config, assignment, artifact, or method mismatch rejects resume. |
| Training policy | Fixed epochs, source-validation macro-F1-only checkpointing, continued training, target-monitoring-only, and subject-level aggregation are enforced. |

The exact MMD tests must be regression tests against the existing behavior, not a new mathematical reference that permits drift. No result is considered passing merely because a numerical value looks plausible.

## Ownership and dependency graph

```text
A freeze/provenance owner
        |
        v
B specification writer (this package)
        |
        +--> scientific identity/taxonomy review
        +--> binary/OASIS semantics review
        +--> MMD and comparator contract review
        +--> target-isolation and artifact review
        |
        v
C migration implementer  [BLOCKED]
        |
        v
C contract/regression verification  [BLOCKED]
        |
        v
D live execution owner  [BLOCKED]
        |
        v
D result-freeze/audit owner  [BLOCKED]
        |
        v
E reporting/statistics owner
        |
        v
F compatibility-rename owner (separate approval; plan only here)
```

Dependency rules:

- C may start only after the explicit user authorization and the R-B-012 start-boundary record are satisfied: the frozen commit/tag/notebook boundary is verified, the live notebook training path is proven not to import or reach modified reporting modules, and exclusive non-interference proof limits the change to report/read-time mapping and projection.
- C implementation/review evidence must include the focused regression matrix below. Those tests are not prerequisites to starting C, but all must pass before D activation.
- D depends on completed C implementation, review, and regressions; finished live runs; frozen results/manifests; a passed, separately recorded Phase 18B OASIS provenance/semantics blocker; verified live seed-status attestation; and a separate explicit Phase D execution authorization artifact. Missing, stale, conflicting, or failed evidence is `BLOCKED` before data access.
- E depends on immutable frozen results and report-time alias resolution evidence.
- F depends on a separate rename approval and must not change the frozen family retroactively.

## Review gates

1. **Phase B content gate:** all six package artifacts exist, are internally consistent, English, prospective, and documentation-only.
2. **Scientific boundary gate:** public naming and contribution claims are separated from the standard MMD regularizer; historical discrepancies remain visible.
3. **Compatibility gate:** IDs, package name, paths, and historical outputs are preserved; aliases are read/report-time only.
4. **Binary and provenance gate:** ADNI/OASIS mapping, both directions, disjoint target partitions, no target labels, and subject aggregation are specified without claiming historical compliance.
5. **Regression gate:** exact MMD, target isolation, legacy comparators, `no_mmd` non-equivalence, alias/hash, and checkpoint/resume coverage are explicitly planned.
6. **Activation gate:** C may start only under the explicit user authorization and verified R-B-012 reporting-only boundary; C implementation/review evidence is not claimed complete. D remains blocked until the live family finishes, results/manifests are frozen, all required C regressions/review pass, the Phase 18B OASIS provenance/semantics blocker passes, verified `42/43/44` seed status is recorded, and a separate explicit execution authorization artifact is recorded; each missing prerequisite maps to `BLOCKED`.
7. **Rename gate:** any package/repository rename is separately reviewed and executed only under a future approved migration; this package performs no rename.

## Rename plan — not executed

A later migration may:

1. inventory package imports, entry points, config names, method IDs, display labels, documentation references, checkpoints, manifests, and repository paths;
2. define a compatibility layer that preserves `pada3dacb`, `mmd`, and historic paths while reports adopt 3D-ACDA labels;
3. add read-time alias resolution and dual-name diagnostics without rewriting stored IDs;
4. migrate new outputs only after hash/checkpoint/resume and legacy comparator regressions pass;
5. deprecate old public names only after an explicit compatibility window and maintainer approval; and
6. validate imports, manifests, report identity, resume identity, and historical read access.

**The package/repository rename is not executed in Phase B.**
