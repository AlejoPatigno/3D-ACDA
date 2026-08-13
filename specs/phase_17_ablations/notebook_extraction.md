# Phase 17 — Canonical Ablation Notebook Extraction

## Decision first

The archived notebook provides **definitions and helper paths, not an executed ablation study**. The only non-commented experiment call is the primary `source -> target` bidirectional wrapper in cell 15. Every ablation candidate below is therefore evidence for a future contract, not evidence of a completed run. A `canonical_defined_not_executed` candidate requires explicit maintainer approval before implementation or execution.

The primary scientific source is `notebooks/archive/training_original.ipynb`. Cell and line numbers below are one-based and refer to the notebook cell's source list, not to a rendered export. Notebook outputs and execution counts are stripped.

## Provenance and precedence

1. Active source text and the non-commented primary call are authoritative for what the notebook defines and calls.
2. Existing repository contracts are authoritative for production architecture, label firewall, checkpointing, resume, and protected methods.
3. Commented calls, later shadowing definitions, helper defaults, prose, and historical output paths are audit evidence only.
4. Names are not semantics. A requested long alias is not accepted unless it maps to an exact source symbol and the mapping is recorded.

Cross-checks: `docs/PROPOSED_METHOD_EXPERIMENT.md`, `docs/PHASE13_REPORT.md`, `specs/phase_13_prototype_pseudo/notebook_extraction.md`, `docs/NOTEBOOK_MIGRATION_MAP.md`, `docs/PADA3DACB_MODEL.md`, `docs/LOSSES_AND_TRAINING.md`, `specs/phase_16_concept_validation/manuscript_extraction.md`, and `specs/phase_16_concept_validation/decisions.md`.

## Executed-path evidence

| Item | Exact provenance | Status | Consequence |
|---|---|---|---|
| Primary call | Cell 15, lines 11–26: `bidirectional_results = run_bidirectional_domain_adaptation(...)` | `canonical_executed` path evidence | One forward `source_to_target` result is returned. This is not a claim that a reproducible real-data run occurred in the current workspace. |
| Primary arguments | Cell 15, lines 17–24: `n_splits=5`, `batch_size=16`, `num_workers=2`, `n_epochs_warm=5`, `n_epochs_full=50`, `lr=1e-4`, `weight_decay=1e-4`, `random_state=42` | Active call configuration | These are provenance values only; no Phase 17 value may be invented from them. |
| Primary runner | Cell 14, lines 621–676: `run_domain_adaptation_experiment` | Active earlier definition for the primary path | Iterates all folds and calls the primary fold runner. |
| Primary fold runner | Cell 14, lines 330–619: `train_domain_adaptation_fold` | Active earlier definition for the primary path | Builds source labels/artifacts, unlabeled target adaptation data, separate target evaluation data, model, loss, trainer, history, and historical files. |
| Primary model builder | Cell 14, lines 303–328: `build_patched_model` | Active historical builder | Builds the former notebook model and replaces its concept bottleneck; it is not the post-revision production model boundary. |
| Primary direction wrapper | Cell 14, lines 678–735 | Forward call active; backward call commented | Lines 694–711 call `source -> target`; lines 713–730 comment `target -> source`; lines 732–735 return only `source_to_target`. |
| Commented backward call | Cell 14, lines 713–730 | Shadowed/commented | Not an executed direction and not evidence for a bidirectional result table. |

### Primary data and output provenance

The primary fold runner creates source labeled datasets at cell 14, lines 400–414; an unlabeled target adaptation dataset at lines 416–418; labeled target train-evaluation data at lines 420–426; and labeled target validation data at lines 428–434. Loader construction is at lines 438–490. The target adaptation loader is distinct from target evaluation loaders, but the historical ablation runner must not be treated as a complete source-only implementation.

The primary loss is constructed at cell 14, lines 504–524. The trainer is constructed at lines 539–545 and called at lines 552–559. The payload is assembled at lines 561–575. Historical output paths are saved at lines 577–617:

- `<save_dir>/<source>_to_<target>/fold_<NN>/domain_adaptive_mri_cbm.pt`
- `<save_dir>/<source>_to_<target>/fold_<NN>/history_domain_adaptive.json`
- architecture metadata returned by `save_model_architecture`

These paths are provenance, not the approved Phase 17 output contract.

## Objective and coefficient extraction

### Active warm/full loss

The active `DomainAdaptiveTotalLoss` is at cell 8, lines 442–625. Its constructor fields and defaults are at lines 469–488; the primary executed coefficients override them at cell 14, lines 504–524.

Warm, cell 8, lines 526–563:

```text
L_warm = warm_lambda_z    * lambda_z    * L_cls_z
        + warm_lambda_c    * lambda_c    * L_cls_c
        + warm_lambda_cbm  * lambda_cbm  * L_concept
        + warm_lambda_anat * lambda_anat * L_anat
        + warm_lambda_cons * lambda_cons * L_cons
```

`L_proto` and `L_pl` are not computed in warm and are logged as `0.0` at lines 557–561. Full, cell 8, lines 568–625:

```text
L_full = lambda_z     * L_cls_z
        + lambda_c     * L_cls_c
        + lambda_cons  * L_cons
        + lambda_cbm   * L_concept
        + lambda_anat  * L_anat
        + lambda_proto * L_proto
        + lambda_pl    * L_pl
```

The full path obtains target adaptation probabilities from target concept-head logits at lines 590–600. No target diagnosis labels are part of this loss contract.

### Coefficient table

| Field | Primary call, cell 14 lines 504–524 | Historical class/helper evidence | Disposition |
|---|---:|---:|---|
| `lambda_z` | `1.0` | Cell 8, lines 469, 493 | Preserve. |
| `lambda_c` | `1.0` | Cell 8, lines 470, 494 | Preserve. |
| `lambda_cons` | `0.1` | Cell 8, lines 471, 495 | Preserve unless exact `no_cons` intervention is approved. |
| `lambda_cbm` | `0.5` | Cell 8, lines 472, 496 | Preserve unless exact `no_concept` intervention is approved. |
| `lambda_anat` | `0.2` | Cell 8, lines 473, 497 | Preserve unless exact `no_anat` intervention is approved. |
| `lambda_proto` | `1.0` | Cell 8 default lines 475, 498; cell 14 lines 513 | Canonical primary value. |
| `lambda_proto` later helper default | Not a primary-call value | Cell 18, lines 61–81, specifically line 70: `0.2`; class default also cell 8, line 475 | `unsupported` unresolved discrepancy; do not select. |
| `lambda_pl` | `0.1` | Cell 8, lines 476, 499 | Preserve unless exact `no_pl` intervention is approved. |
| `tau_p` | `0.95` | Cell 14 line 515; cell 18 line 72 | Preserve; do not substitute the class default `0.9` at cell 8 line 478. |
| `proto_margin` | `1.0` | Cell 14 line 516; cell 18 line 73 | Preserve. |
| `lambda_sep` | `0.1` | Cell 14 line 517; cell 18 line 74 | Preserve. |
| `label_smoothing` | `0.1` | Cell 14 line 518; cell 18 line 75 | Preserve. |
| `warm_lambda_z` | `0.1` | Cell 14 line 519; cell 18 line 76 | Preserve. |
| `warm_lambda_c` | `1.0` | Cell 14 line 520; cell 18 line 77 | Preserve. |
| `warm_lambda_cbm` | `1.0` | Cell 14 line 521; cell 18 line 78 | Preserve. |
| `warm_lambda_anat` | `1.0` | Cell 14 line 522; cell 18 line 79 | Preserve. |
| `warm_lambda_cons` | `0.0` | Cell 14 line 523; cell 18 line 80 | Preserve; `no_cons` has no effective warm change. |

The notebook also contains a commented `SupervisedTotalLoss` draft in cell 8, lines 345–431. It is not the active domain-adaptive loss and must not be mixed into an ablation contract.

## Ablation definitions and exact interventions

The factory is cell 19, lines 1–66. The exact source names and dictionaries are:

| Exact source name | Cell 19 lines | Exact intervention | Classification | Execution status |
|---|---:|---|---|---|
| `full` | 3–8 | Empty `loss_overrides`, `model_patch=None`; historical former Full model | `invalid_after_architecture_revision` | Defined, not called |
| `no_proto` | 9–14 | `loss_overrides: {"lambda_proto": 0.0}` | `canonical_defined_not_executed` | No non-commented call |
| `no_pl` | 15–20 | `loss_overrides: {"lambda_pl": 0.0}` | `canonical_defined_not_executed` | No non-commented call |
| `no_cons` | 21–26 | `loss_overrides: {"lambda_cons": 0.0}` | `canonical_defined_not_executed` | No non-commented call |
| `no_concept` | 27–32 | `loss_overrides: {"lambda_cbm": 0.0}` | `canonical_defined_not_executed` | No non-commented call |
| `no_anat` | 33–38 | `loss_overrides: {"lambda_anat": 0.0}` | `canonical_defined_not_executed` | No non-commented call |
| `no_ctx_encoder` | 39–44 | `model_patch: "identity_ctx"` | `equivalent_to_existing_method` and invalid as implementation technique | Defined, not called |
| `mean_pool` | 45–50 | `model_patch: "mean_pool"` | `canonical_defined_not_executed` | No non-commented call |
| `no_domain_adaptation` | 53–64, conditional `include_no_da=True` | `lambda_proto=0.0` and `lambda_pl=0.0` | `canonical_defined_not_executed`, semantically blocked as Source-Only | Optional definition only; call commented |

No exact symbols named `no_prototype`, `no_pseudo_label`, `no_head_consistency`, `no_concept_supervision`, `no_anatomical_consistency`, or `mean_pooling` occur in the factory. Requested names may be aliases only after explicit mapping in `equivalence_map.md`; they are not independent candidates.

## Model and pooling helpers

| Helper/flag | Exact provenance | Status and limitation |
|---|---|---|
| `IdentityContextualEncoder` | Cell 18, lines 10–12; returns `T` unchanged | `helper_only`; implementation detail for the former Full patch, not a production model. |
| `MeanPoolAggregator` | Cell 18, lines 15–31; `alpha=1/K`, `z=U.mean(dim=1)` | `helper_only`; a defined alternative pooling intervention, not executed. |
| `apply_model_ablation` | Cell 18, lines 37–52 | `helper_only`; deep-copies the former model and accepts only `None`, `identity_ctx`, or `mean_pool`; unknown patches raise. |
| `model_patch` | Cell 18, lines 39–50 and cell 19 lines 6–7, 12–13, etc. | Historical patch flag. Phase 17 must not expose a Full/contextual runtime switch. |
| `loss_overrides` | Cell 18, lines 55–86 | Historical arbitrary dictionary update. Phase 17 must whitelist exactly one approved coefficient change and reject all other changes. |
| `include_no_da` | Cell 19, lines 1, 53–64 | Factory flag only; `True` appends `no_domain_adaptation`. It does not establish source-only loader semantics. |
| `availability` | Cell 18, lines 487–501 | `obsolete` selective-fold shortcut. It runs only fold 4 for `no_ctx_encoder` and `no_pl`, folds 4–5 for `no_concept` and `no_domain_adaptation`; never use as evidence. |

The architecture cross-check is explicit: `docs/PADA3DACB_MODEL.md` and `docs/NOTEBOOK_MIGRATION_MAP.md` state that PADA-3DACB is the no-context architecture and that contextual `Full`, `ctx_enc`, identity patching, mean-pool production behavior, and a Full/Lite switch are excluded from production.

## Ablation-aware runner and tables

### Shadowed runner definitions

`train_domain_adaptation_fold` is defined first at cell 14, lines 330–619 and again at cell 18, lines 163–458. `run_domain_adaptation_experiment` is defined first at cell 14, lines 621–676 and again at cell 18, lines 460–531. The later definitions shadow the earlier names if the notebook is executed top-to-bottom, but the primary cell-15 call is documented by the Phase 13 extraction as the earlier primary path. This namespace ambiguity is `obsolete` audit evidence, not permission to infer an ablation run.

`DomainAdaptiveTotalLoss` is active at cell 8, lines 442–625; the commented supervised draft at lines 345–431 is not an active duplicate. `apply_model_ablation` has one definition at cell 18, lines 37–52.

### Ablation-aware fold runner

Cell 18, lines 163–458:

- default spec is `full` at lines 185–190;
- source and target splits are created at lines 225–238;
- target adaptation uses `UnlabeledTargetAdaptDataset` at lines 259–261;
- target train/validation evaluation uses labeled datasets at lines 263–277;
- model patching and loss override application occur at lines 341–355;
- one historical `DomainAdaptiveMRITrainer` is constructed at lines 370–376;
- the runner calls the trainer at lines 383–390;
- payload fields are added at lines 392–408;
- ablation output paths are at lines 410–456.

The historical ablation path is evidence of separation between adaptation input and monitoring data, but it does not establish Phase 17's complete target firewall, fixed checkpoint selection, resume identity, or source-only semantics.

### Selective-fold experiment runner

Cell 18, lines 460–531 redefines the experiment runner. The `availability` conditions at lines 487–499 are incomplete by construction. They cannot support a complete fold/seed matrix or a scientific comparison.

### Summary runner and result tables

`run_ablation_study` is cell 18, lines 533–642. Its defaults at lines 541–548 are `n_splits=3`, `batch_size=2`, `num_workers=0`, `n_epochs_warm=5`, `n_epochs_full=10`, `lr=1e-4`, `weight_decay=1e-4`, and `random_state=42`; its docstring lines 552–556 explicitly recommends screening and later repeating only selected ablations. This is not an approved Phase 17 design.

The helper table `extract_fold_terminal_metrics` is cell 18, lines 96–147. It selects the last full row, or last warm row if no full rows exist, via `_get_last_epoch_info` at lines 88–93. It reports:

- identity: `ablation`, `fold_idx`, `source_domain`, `target_domain`;
- losses: `L_total`, `L_cls_z`, `L_cls_c`, `L_cons`, `L_concept`, `L_anat`, `L_proto`, `L_pl`;
- prototype diagnostics: `proto_align`, `proto_sep`, `n_confident_T`;
- source train, target train, source validation, and target validation metrics.

` summarize_ablation_results` is cell 18, lines 149–161. It groups by ablation and computes `nanmean`/`nanstd`; it provides no inferential protocol, uncertainty model, or publication gate.

The historical output tables are written in cell 18, lines 621–636:

- `ablation_folds.csv`;
- `ablation_summary.csv`;
- `ablation_runs.json`.

They are `canonical_defined_not_executed` output shapes only. Target metrics from these helpers remain monitoring-only in Phase 17.

## Commented setup and call

Cell 19, line 68 contains `# ABLATIONS_FAST = get_default_ablation_specs(True)`. Cell 19, lines 70–88 contain a fully commented `# ablation_results = run_ablation_study(...)` with `n_splits=5`, `batch_size=16`, `num_workers=2`, `n_epochs_warm=5`, `n_epochs_full=50`, `lr=1e-4`, `weight_decay=1e-4`, `random_state=42`, and a Kaggle save path. Both are `canonical_defined_not_executed`; neither supplies output, checkpoint, or real-data evidence.

## Unresolved limitations that remain BLOCKED

- The notebook does not contain a non-commented ablation call, outputs, execution counts, or reproducible ablation result table.
- `lambda_proto=0.2` in the later helper conflicts with the primary `lambda_proto=1.0`; the discrepancy recorded as `D-14-001` remains unresolved.
- `no_domain_adaptation` zeroes two losses but the historical runner still creates and forwards a target adaptation loader; it is not proven Source-Only.
- `full` and `no_ctx_encoder` refer to the former contextual architecture and cannot define a current production model variant.
- `mean_pool` is defined but not executed and is excluded from the final proposed architecture.
- Long aliases are not exact source names and must not be silently accepted.
- Selective availability is not a complete fold/seed design.
- Historical summary tables use terminal rows and `nanmean`/`nanstd`, not a publication statistical protocol.
- Real ADNI/OASIS training, target-supervised adaptation, publication metrics, and Phase 18 are outside this action.
