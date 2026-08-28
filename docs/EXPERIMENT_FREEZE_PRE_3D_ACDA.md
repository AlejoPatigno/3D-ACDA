# Prospective Experiment Freeze: Pre-3D ACDA

> **This is a documentation-only prospective freeze record. It changes no scientific or runtime behavior.**

## Scope and non-goals

This record freezes the provenance and runtime contract for the live binary CN-vs-Impaired experiment family before the 3D ACDA migration. It is an audit boundary for the live family, not an implementation change.

Out of scope:

- changing the notebook, package, MMD source, training behavior, or experiment outputs;
- reconciling historical package configurations or publication documents;
- asserting that any currently running seed has completed; and
- executing or planning an immediate package or repository rename.

## Immutable commit/tag/notebook provenance

| Item | Frozen fact |
|---|---|
| Live commit | `aafe817365cb4068f167b398c776aff4c3b1f021` |
| Local references at audit time | `HEAD`, `main`, and `origin/main` resolve to the live commit |
| Existing annotated tag | `exp-binary-mmd-publication-freeze-v1` resolves to the live commit; it is not recreated by this record |
| Migration branch | `refactor/3d-acda-mmd` |
| Source notebook | `train-pada3dacb-baselines-ablation (2).ipynb` |
| Notebook status | Untracked; it remains unchanged |
| Notebook SHA-256 | `a06f825a9de647f1c2483e59009c55650ca650a0b91e1fda93c7ecc3ac6c909c` |

The commit and notebook hash are provenance anchors supplied and verified for this freeze. This document does not claim any additional filesystem or notebook-cell fact.

## Live protocol

The notebook runtime is authoritative for this live family:

- task: binary CN-vs-Impaired execution;
- architecture: 102 ROIs, `feature_dim=256`, `token_dim=128`, `base_channels=32`, and `concept_hidden_dim=64`;
- both dropouts: `0.20`;
- warmup/full schedule: `10/50`;
- batch size: `16`;
- learning rate and weight decay: `1e-4` / `1e-4`;
- gradient clipping: `5`;
- AMP: enabled when CUDA is available;
- source sampler: deterministic `50/50` binary source batches;
- core weights: the values stated by the user for this live protocol;
- MMD weight: `1`; and
- MMD bandwidths: `[1, 2, 4, 8, 16]`.

The notebook imports the existing package builders and adaptation/loss classes from the clone at the immutable commit. Seeds `42`, `43`, and `44` are one frozen family by user attestation; seeds `43` and `44` are running. The stored notebook has the `43`/`44` launches commented out, so their live provenance is an attestation, not an observable cell configuration.

## Runtime invariants

- **Target-label isolation:** the target adaptation batch firewall contains only `x`, `subject_id`, `subject_hash`, and `cohort`. Target labels are not part of that adaptation batch contract.
- **Checkpoint selection:** source-validation macro-F1 only.
- **Checkpoint resume/reuse:** use the notebook's explicit no-overwrite/reuse semantics. This record does not claim that a resume or reuse occurred.
- **Run root:** `pada3dacb_binary_training_runs_diagnostic_v2`.
- **Outputs:** live outputs belong under that run root and remain governed by the notebook's explicit no-overwrite/reuse behavior. This record does not enumerate or claim completion of output files.

## Method IDs/package/repository compatibility

The descriptive method identity for this freeze is the binary CN-vs-Impaired MMD adaptation family. No new method ID is introduced here. Compatibility is pinned to the existing package builders and adaptation/loss classes imported by the notebook from the clone at `aafe817365cb4068f167b398c776aff4c3b1f021`.

The MMD source is untouched. Its audited behavior remains the existing biased squared mixture-RBF estimator, including diagonals, arithmetic kernel averaging, and float32 pairwise computation, without embedding normalization, a median heuristic, or a final clamp. Nothing in this record modifies or reinterprets that implementation.

## Explicit discrepancies and authority boundary

Checked-in historical package configurations and publication documents materially differ from the live notebook contract, notably in three-class versus binary task definition, the unbalanced package loader, and alternative training/MMD defaults. These discrepancies are deliberately not resolved here.

For this live family only, the notebook runtime together with the immutable commit is authoritative. Historical documents remain historical and are not silently updated to match it. The discrepancies must be handled in a later prospective migration specification.

## Protected paths

This record protects the live and historical boundary. No change is made to:

- `train-pada3dacb-baselines-ablation (2).ipynb`;
- `runs/`, `results/`, or `artifacts/`;
- historical documentation or specifications;
- `.git/gentle-ai`; or
- any other file outside this record.

## Migration branch/separation

The record is created on `refactor/3d-acda-mmd` as a prospective separation marker. It does not backport the live notebook contract into the existing package, alter historical artifacts, or make the 3D ACDA migration appear to be part of the frozen live experiment.

## Validation/status

Validation for this record is documentation review against the supplied provenance and protocol binding. No tests, installs, experiment runs, or runtime mutations are performed. The live family status remains: seed `42` is part of the frozen family by attestation, while seeds `43` and `44` are running; no completion claim is made.

## Future rename plan (plan only)

A later, separately scoped migration specification may define the package and repository rename. That specification should first map the frozen method IDs, runtime entry points, imports, configuration names, documentation references, and compatibility boundaries, then define staged changes and validation without rewriting this provenance record.

**Package/repository rename: not executed.**
