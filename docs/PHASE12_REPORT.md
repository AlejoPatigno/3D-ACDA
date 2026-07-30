# Phase 12 Report — PADA-3DACB + CDAN

Phase 12 adds the declared `PADA-3DACB + CDAN` method only. It preserves Source-Only, CORAL, and MMD behavior while adding exact outer-product CDAN adaptation for the existing PADA-3DACB model.

## Current status

Final validation is **PASSED for Phase 12 implementation acceptance** after the CDAN CLI lifecycle remediation. Installation, import, the full suite with repository-local pytest temp directory, Ruff, whitespace, CDAN dry-run, both approved directions, validate-only, one complete synthetic fold, controlled interruption, exact resume, completed-fold reuse, unequal-batch evidence, and prior-method CLI regressions passed.

The exact `python -m pytest -q` command still fails only because this Windows environment cannot access the default pytest temp root. Real ADNI/OASIS training was not run, real-cohort performance is not claimed, and Phase 13 was not started.

## Scope summary

| Topic | Phase 12 decision / verified fact |
|---|---|
| New method | `cdan` / `PADA-3DACB + CDAN` |
| Base model | Existing PADA-3DACB Lite/no-contextual-encoder architecture |
| Dataset scope | ADNI/OASIS only, both approved directions only |
| Training policy | Fixed epochs; source-only warm-up; paired source/target full stage |
| Checkpoint policy | Source-validation macro-F1 only |
| Target policy | Monitoring-only; no training labels; no target-guided selection |
| CDAN lifecycle | Controlled interruption, exact resume, and completed-fold reuse passed with fixture-only CLI evidence |
| Real-run status | Blocked until explicit CDAN scientific hyperparameters are supplied |
| Phase 13 status | Not started |

## CDAN method contract

The declared variant is exact outer-product CDAN:

```text
H_i = z_i p_i^T
h_i = flatten(H_i)
```

where `z_i` is the subject embedding and `p_i` is the current latent classifier probability vector over `CN`, `MCI`, and `AD`. The flattened tensor has shape `(B, d * 3)`; with `d = 128`, the default discriminator input dimension is `384` by validation.

The CDAN path keeps `z` and probabilities differentiable. Focused tests revalidated gradient flow to the shared encoder path, latent classifier path, and discriminator parameters.

## GRL, discriminator, and domain labels

- GRL is constant-coefficient only: forward identity, backward scale `-coefficient`.
- The coefficient must be explicit, finite, and non-negative.
- The discriminator is a binary MLP that consumes flattened conditionals and returns one raw logit per sample.
- There is no final sigmoid; logits are consumed by `BCEWithLogitsLoss`.
- Domain labels are generated internally: source = `0`, target = `1`.
- External domain-label overrides are not part of Phase 12.

The domain objective is:

```text
domain_bce = BCEWithLogitsLoss(reduction="mean")(
    concat(source_logits, target_logits),
    concat(zeros, ones),
)
total_loss = source_objective + cdan_weight * domain_bce
```

Unequal source/target batch-size behavior passed with:

```powershell
python -m pytest -q tests/test_cdan_domain_loss.py::test_cdan_domain_loss_uses_internal_labels_and_exact_concatenated_mean_bce_for_unequal_batches --basetemp C:/Users/LOQ/Desktop/PADA-3DACB/.tmp_pytest_final_validation_refresh_unequal
```

Result: `1 passed, 1 warning in 3.37s`.

## Warm-up and full-stage objective

Warm-up remains source-only. It does not consume target-adaptation batches, construct CDAN conditionals, call the discriminator, update discriminator parameters, or report nonzero CDAN diagnostics.

The full stage uses one shared PADA-3DACB model, one discriminator, and one AdamW optimizer with explicit model and discriminator parameter groups. Each paired batch performs one combined backward pass and one optimizer step.

A synthetic one-fold warm-plus-full command completed with `status: "COMPLETED"`, `best_source_epoch: 1`, `last_epoch: 2`, finite CDAN loss, and expected checkpoints/prediction exports. This is fixture-only runtime evidence, not a real cohort result.

## Checkpoint, resume, and monitoring separation

Checkpoint selection remains source-validation macro-F1 only. The complete and resumed synthetic folds selected `best_source_epoch: 1` from source-validation macro-F1. Target-monitoring metrics were reported separately and labeled `MONITORING ONLY — NOT A TRAINING LOSS`; they were not checkpoint selectors.

CDAN lifecycle evidence now passed:

- Controlled interruption returned `status: "INTERRUPTED"`, hash `993f64a34d2e263bde38ad2e16886614d032cdb07b94479cf7fd8e59e8cb35e8`, `last_epoch: 1`.
- Exact resume returned `status: "COMPLETED"` with the same hash and `last_epoch: 2`.
- Completed-fold reuse returned `status: "COMPLETED"`, `reused: true`, hash `20017fbd1fc433c26da990c27e39575ea4d03d4368404cadcd749ee85fdcc350`.
- Checkpoint inspection confirmed `loader_generator_states` includes `source_train` and `target_adaptation`.

## Target-label isolation

Target-adaptation diagnosis labels are not consumed by the CDAN trainer. They do not contribute to loss, gradients, checkpoint selection, prediction export, or domain-label creation. Dry-run summaries reported `target_training_labels_available: false`.

## Prior-method preservation

Source-Only, CORAL, and MMD remain protected prior methods. Final validation re-ran prior-method CLI regressions successfully:

| Method | Command summary | Exit code | Hash/status |
|---|---|---:|---|
| Source-Only | synthetic fold-0 dry-run | 0 | `status: "PENDING"`, hash `4b54e09494066b383b970ffd8ad4c34cda2e822c231a9489db102e0aaf026f8a` |
| CORAL | synthetic fold-0 dry-run with `--coral-weight 1.0` | 0 | `status: "PENDING"`, hash `f58c13c8e986028c76930891e8f307dc4d491d979f17611dd01e0b231ba58358` |
| MMD | synthetic fold-0 dry-run with fixture bandwidths | 0 | `status: "PENDING"`, hash `91b7cb092d647e12c5280eb70092543d350fd26328c2d8abaf6465bb6d6d77b1` |

## Explicit exclusions

Phase 12 excludes:

- entropy conditioning;
- randomized multilinear projection;
- pseudo-labels or confidence filtering;
- prototype alignment;
- baseline methods;
- Phase 13 production work;
- `ContextualROIEncoder`, `ctx_enc`, or identity patch behavior;
- target-guided checkpoint selection;
- target diagnosis supervision in adaptation;
- preprocessing, artifact precomputation, split regeneration, or concept-normalizer refitting.

No Phase 13 behavior is declared, implemented, or claimed.

## Final validation evidence

| Check | Command | Exit code | Result |
|---|---|---:|---|
| Editable install | `python -m pip install -e .` | 0 | Installed `pada3dacb-0.1.0`. |
| Import/version | `python -c "import pada3dacb; print(pada3dacb.__version__)"` | 0 | `0.1.0`. |
| Exact full suite | `python -m pytest -q` | 1 | Environment temp-root failure: `PermissionError` on `C:\Users\LOQ\AppData\Local\Temp\pytest-of-LOQ`; `139 passed`, `173 errors`. |
| Full suite workaround | `python -m pytest -q --basetemp C:/Users/LOQ/Desktop/PADA-3DACB/.tmp_pytest_final_validation_refresh` | 0 | `312 passed, 3 warnings in 353.72s`. |
| Ruff | `python -m ruff check .` | 0 | `All checks passed!`. |
| Whitespace | `git diff --check` | 0 | No output. |
| CDAN all-folds dry-run | fixture-only CDAN CLI with explicit CDAN/GRL/discriminator overrides | 0 | Folds `0..4` pending; hash `5cbe80a2bb66c8584ef4ad6405d1f8c2e7566ffa3a52f659499bcf54a262decf`. |
| CDAN both-directions dry-run | same fixture-only CDAN CLI plus `--both-directions --all-folds` | 0 | Both approved directions pending; hashes `5cbe80a2...262decf` and `56f6c812...d47a46`. |
| CDAN validate-only | fixture-only fold 0 validate-only | 0 | `validated: true`, finite `cdan_loss: 0.7096753716468811`. |
| CDAN complete synthetic fold | fixture-only fold 0 warm-plus-full | 0 | `COMPLETED`; hash `c045ef59d5dfad1b5feed8f0f8e225253c646e344fb1900d2b3aecd9101e2bd4`; checkpoints and prediction files generated. |
| CDAN controlled interruption | fixture-only fold 1 with `--interrupt-after-epoch 1` | 0 | `INTERRUPTED`; hash `993f64a34d2e263bde38ad2e16886614d032cdb07b94479cf7fd8e59e8cb35e8`; `last_epoch: 1`. |
| CDAN exact resume | resume from interrupted fold checkpoint | 0 | `COMPLETED`; same hash `993f64a34d2e263bde38ad2e16886614d032cdb07b94479cf7fd8e59e8cb35e8`; `last_epoch: 2`. |
| CDAN completed-fold reuse | rerun completed fold without `--overwrite` | 0 | `COMPLETED`, `reused: true`; hash `20017fbd1fc433c26da990c27e39575ea4d03d4368404cadcd749ee85fdcc350`. |

## Evidence not claimed

The following are intentionally not claimed:

- no real ADNI/OASIS CDAN training result;
- no real-run fold/seed matrix result;
- no scientific performance comparison against Source-Only, CORAL, or MMD;
- no Phase 13 production work.

## Real-run blockers

Real CDAN experiments remain blocked until maintainers provide finite explicit values for CDAN weight, constant GRL coefficient, discriminator architecture/dropout, discriminator learning rate and weight decay, and the real-run seed/fold command matrix.

## Final blockers before Phase 13

No implementation acceptance blocker remains from Phase 12 final validation. Phase 13 is still not started and should remain blocked until Phase 12 receives the required explicit review/human approval and real-run scientific configuration decisions remain properly scoped.
