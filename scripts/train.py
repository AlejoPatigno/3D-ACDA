"""Fixed-epoch experiment entry point for approved 3D-ACDA methods."""

from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path

import torch
import yaml
from torch.utils.data import DataLoader

from acda3d.exceptions import PhaseNotImplementedError
from acda3d.experiments import (
    CDANExperimentRunner,
    CORALExperimentRunner,
    MMDExperimentRunner,
    SourceOnlyExperimentRunner,
    load_baseline_config,
    load_cdan_config,
    load_coral_config,
    load_mmd_config,
    load_source_only_config,
    run_all_requested_baselines,
    run_baseline_both_directions,
    run_both_directions,
    run_cdan_both_directions,
    run_coral_both_directions,
    run_mmd_both_directions,
    train_baseline_cv_fold,
)
from acda3d.experiments.prototype_pseudo import (
    PrototypePseudoExperimentRunner,
    load_prototype_pseudo_config,
    run_prototype_pseudo_both_directions,
)
from acda3d.losses import CoreACDA3DLoss
from acda3d.models import ACDA3D, prepare_feature_grid_roi_masks
from acda3d.models.baselines import list_baselines
from acda3d.training import FixedEpochTrainingConfig, SourceOnlyTrainer
from acda3d.training.reproducibility import seed_everything


def _loader(*, target_monitoring: bool = False) -> DataLoader:
    rows = []
    for index in range(3):
        row = {
            "x": torch.full((1, 16, 16, 16), (index + 1) / 3, dtype=torch.float32),
            "y": torch.tensor(index, dtype=torch.long),
        }
        if not target_monitoring:
            row["c_target"] = torch.tensor([0.25, 0.75], dtype=torch.float32)
            row["g_bar"] = torch.tensor([0.4, 0.6], dtype=torch.float32)
        rows.append(row)
    return DataLoader(rows, batch_size=3, shuffle=False)


def run_synthetic_smoke(args: argparse.Namespace) -> None:
    seed_everything(args.seed)
    model = ACDA3D(2, 8, 6, base_channels=4, concept_hidden_dim=4)
    atlas_masks = torch.zeros(2, 16, 16, 16)
    atlas_masks[0, :8] = 1
    atlas_masks[1, 8:] = 1
    feature_masks = prepare_feature_grid_roi_masks(atlas_masks, (2, 2, 2))
    config = FixedEpochTrainingConfig(
        warmup_epochs=args.warmup_epochs,
        full_epochs=args.full_epochs,
        checkpoint_every=1,
        target_monitoring_enabled=True,
        mixed_precision=True,
        seed=args.seed,
    )
    trainer = SourceOnlyTrainer(
        model,
        CoreACDA3DLoss(2),
        feature_masks,
        args.run_dir,
        config=config,
        split_assignment_hash="synthetic-split-v1",
        atlas_hash="synthetic-atlas-v1",
        roi_order_hash="synthetic-roi-order-v1",
    )
    history = trainer.fit(
        _loader(),
        _loader(),
        _loader(target_monitoring=True),
        resume_from=args.resume_from,
        interrupt_after_epoch=args.interrupt_after_epoch,
    )
    print(
        f"synthetic_smoke_ok epochs_completed={trainer.completed_epoch} "
        f"global_step={trainer.global_step} history_rows={len(history.rows)} "
        f"run_dir={Path(args.run_dir).resolve()}"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--synthetic-smoke", action="store_true")
    parser.add_argument("--run-dir", type=Path, default=Path("runs/synthetic_phase8"))
    parser.add_argument("--warmup-epochs", type=int, default=1)
    parser.add_argument("--full-epochs", type=int, default=1)
    parser.add_argument("--interrupt-after-epoch", type=int)
    parser.add_argument("--resume-from", type=Path)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--method")
    parser.add_argument("--baseline-name", action="append", dest="baseline_names")
    parser.add_argument("--all-baselines", action="store_true")
    parser.add_argument("--coral-weight", type=float)
    parser.add_argument("--mmd-weight", type=float)
    parser.add_argument("--cdan-weight", type=float)
    parser.add_argument("--grl-coefficient", type=float)
    parser.add_argument("--domain-hidden-dims", type=int, nargs="+")
    parser.add_argument("--domain-dropout", type=float)
    parser.add_argument("--domain-learning-rate", type=float)
    parser.add_argument("--domain-weight-decay", type=float)
    parser.add_argument("--mmd-bandwidths", type=float, nargs="+")
    parser.add_argument("--source-domain", choices=("ADNI", "OASIS"))
    parser.add_argument("--target-domain", choices=("ADNI", "OASIS"))
    parser.add_argument("--fold", type=int)
    parser.add_argument("--all-folds", action="store_true")
    parser.add_argument("--all-seeds", action="store_true")
    parser.add_argument("--both-directions", action="store_true")
    parser.add_argument("--artifact-index", type=Path)
    parser.add_argument("--artifact-root", type=Path)
    parser.add_argument("--split-root", type=Path)
    parser.add_argument("--roi-masks", type=Path)
    parser.add_argument("--atlas-metadata", type=Path)
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--device")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--validate-only", action="store_true")
    monitoring = parser.add_mutually_exclusive_group()
    monitoring.add_argument("--target-monitoring", action="store_true", dest="target_monitoring")
    monitoring.add_argument("--no-target-monitoring", action="store_false", dest="target_monitoring")
    parser.set_defaults(target_monitoring=None)
    return parser


def run_source_only(args: argparse.Namespace) -> None:
    if args.config is None:
        raise ValueError("--config is required for source-only execution.")
    method = args.method or "source_only"
    if method != "source_only":
        raise PhaseNotImplementedError(f"Method {method!r} is not implemented in Phase 9.")
    overrides = {
        "artifact_index": args.artifact_index,
        "artifact_root": args.artifact_root,
        "split_root": args.split_root,
        "roi_masks": args.roi_masks,
        "atlas_metadata": args.atlas_metadata,
        "output_root": args.output_root,
        "source_domain": args.source_domain,
        "target_domain": args.target_domain,
        "device": args.device,
        "overwrite": True if args.overwrite else None,
    }
    config = load_source_only_config(args.config, overrides=overrides)
    if args.fold is not None and args.all_folds:
        raise ValueError("Use either --fold or --all-folds, not both.")
    if args.fold is not None:
        config.folds = [args.fold]
    elif args.all_folds:
        config.folds = list(range(5))
    if not args.all_seeds:
        config.seeds = [args.seed]
    if args.target_monitoring is not None:
        config.evaluation.target_monitoring = args.target_monitoring
        config.training = FixedEpochTrainingConfig(
            **{
                **vars(config.training),
                "target_monitoring_enabled": args.target_monitoring,
            }
        )
    config.validate()
    if args.resume_from is not None and (len(config.folds) != 1 or len(config.seeds) != 1 or args.both_directions):
        raise ValueError("--resume-from requires exactly one direction, fold, and seed.")
    if args.both_directions:
        results = run_both_directions(
            config, dry_run=args.dry_run, validate_only=args.validate_only
        )
        payload = {
            direction: [result.summary_row() for result in direction_results]
            for direction, direction_results in results.items()
        }
    else:
        runner = SourceOnlyExperimentRunner(config)
        if args.interrupt_after_epoch is not None:
            if len(config.folds) != 1 or len(config.seeds) != 1:
                raise ValueError("--interrupt-after-epoch requires exactly one fold and seed.")
            results = [
                runner.run_fold(
                    config.folds[0],
                    config.seeds[0],
                    interrupt_after_epoch=args.interrupt_after_epoch,
                )
            ]
        else:
            results = runner.run(
                dry_run=args.dry_run,
                validate_only=args.validate_only,
                resume_from=args.resume_from,
            )
        payload = [result.summary_row() for result in results]
    print(json.dumps(payload, indent=2, default=str))


def run_coral(args: argparse.Namespace) -> None:
    if args.config is None:
        raise ValueError("--config is required for CORAL execution.")
    raw_config = yaml.safe_load(args.config.read_text(encoding="utf-8")) or {}
    configured_method = str(
        (raw_config.get("experiment") or {}).get("method", "source_only")
    )
    if configured_method != "coral":
        raise PhaseNotImplementedError(
            "Method 'coral' is not implemented in Phase 9 source-only configuration."
        )
    overrides = {
        "artifact_index": args.artifact_index,
        "artifact_root": args.artifact_root,
        "split_root": args.split_root,
        "roi_masks": args.roi_masks,
        "atlas_metadata": args.atlas_metadata,
        "output_root": args.output_root,
        "source_domain": args.source_domain,
        "target_domain": args.target_domain,
        "device": args.device,
        "overwrite": True if args.overwrite else None,
        "coral_weight": args.coral_weight,
    }
    config = load_coral_config(args.config, overrides=overrides)
    if args.fold is not None and args.all_folds:
        raise ValueError("Use either --fold or --all-folds, not both.")
    if args.fold is not None:
        config.folds = [args.fold]
    elif args.all_folds:
        config.folds = list(range(5))
    if not args.all_seeds:
        config.seeds = [args.seed]
    if args.target_monitoring is not None:
        config.evaluation.target_monitoring = args.target_monitoring
        config.training = FixedEpochTrainingConfig(
            **{
                **vars(config.training),
                "target_monitoring_enabled": args.target_monitoring,
            }
        )
    config.validate()
    if args.resume_from is not None and (
        len(config.folds) != 1 or len(config.seeds) != 1 or args.both_directions
    ):
        raise ValueError("--resume-from requires exactly one direction, fold, and seed.")
    if args.both_directions:
        results = run_coral_both_directions(
            config, dry_run=args.dry_run, validate_only=args.validate_only
        )
        payload = {
            direction: [result.summary_row() for result in direction_results]
            for direction, direction_results in results.items()
        }
    else:
        runner = CORALExperimentRunner(config)
        if args.interrupt_after_epoch is not None:
            if len(config.folds) != 1 or len(config.seeds) != 1:
                raise ValueError("--interrupt-after-epoch requires exactly one fold and seed.")
            results = [
                runner.run_fold(
                    config.folds[0],
                    config.seeds[0],
                    interrupt_after_epoch=args.interrupt_after_epoch,
                )
            ]
        else:
            results = runner.run(
                dry_run=args.dry_run,
                validate_only=args.validate_only,
                resume_from=args.resume_from,
            )
        payload = [result.summary_row() for result in results]
    print(json.dumps(payload, indent=2, default=str))


def run_mmd(args: argparse.Namespace) -> None:
    if args.config is None:
        raise PhaseNotImplementedError(
            "Method 'mmd' is not implemented in Phase 10 without an explicit "
            "Phase 11 MMD configuration; --config is required."
        )
    raw_config = yaml.safe_load(args.config.read_text(encoding="utf-8")) or {}
    configured_method = str(
        (raw_config.get("experiment") or {}).get("method", "source_only")
    )
    if configured_method != "mmd":
        raise PhaseNotImplementedError(
            f"Cannot reinterpret {configured_method!r} configuration as MMD."
        )
    overrides = {
        "artifact_index": args.artifact_index,
        "artifact_root": args.artifact_root,
        "split_root": args.split_root,
        "roi_masks": args.roi_masks,
        "atlas_metadata": args.atlas_metadata,
        "output_root": args.output_root,
        "source_domain": args.source_domain,
        "target_domain": args.target_domain,
        "device": args.device,
        "overwrite": True if args.overwrite else None,
        "mmd_weight": args.mmd_weight,
        "mmd_bandwidths": args.mmd_bandwidths,
    }
    config = load_mmd_config(args.config, overrides=overrides)
    if args.fold is not None and args.all_folds:
        raise ValueError("Use either --fold or --all-folds, not both.")
    if args.fold is not None:
        config.folds = [args.fold]
    elif args.all_folds:
        config.folds = list(range(5))
    if not args.all_seeds:
        config.seeds = [args.seed]
    if args.target_monitoring is not None:
        config.evaluation.target_monitoring = args.target_monitoring
        config.training = FixedEpochTrainingConfig(
            **{
                **vars(config.training),
                "target_monitoring_enabled": args.target_monitoring,
            }
        )
    config.validate()
    if args.resume_from is not None and (
        len(config.folds) != 1 or len(config.seeds) != 1 or args.both_directions
    ):
        raise ValueError("--resume-from requires exactly one direction, fold, and seed.")
    if args.both_directions:
        results = run_mmd_both_directions(
            config, dry_run=args.dry_run, validate_only=args.validate_only
        )
        payload = {
            direction: [result.summary_row() for result in direction_results]
            for direction, direction_results in results.items()
        }
    else:
        runner = MMDExperimentRunner(config)
        if args.interrupt_after_epoch is not None:
            if len(config.folds) != 1 or len(config.seeds) != 1:
                raise ValueError("--interrupt-after-epoch requires exactly one fold and seed.")
            results = [
                runner.run_fold(
                    config.folds[0],
                    config.seeds[0],
                    interrupt_after_epoch=args.interrupt_after_epoch,
                )
            ]
        else:
            results = runner.run(
                dry_run=args.dry_run,
                validate_only=args.validate_only,
                resume_from=args.resume_from,
            )
        payload = [result.summary_row() for result in results]
    print(json.dumps(payload, indent=2, default=str))


def run_cdan(args: argparse.Namespace) -> None:
    if args.config is None:
        raise ValueError("--config is required for CDAN execution.")
    raw = yaml.safe_load(args.config.read_text(encoding="utf-8")) or {}
    configured = str((raw.get("experiment") or {}).get("method", "source_only"))
    if configured != "cdan":
        raise PhaseNotImplementedError(f"Cannot reinterpret {configured!r} configuration as CDAN.")
    overrides = {"artifact_index": args.artifact_index, "artifact_root": args.artifact_root,
        "split_root": args.split_root, "roi_masks": args.roi_masks, "atlas_metadata": args.atlas_metadata,
        "output_root": args.output_root, "source_domain": args.source_domain, "target_domain": args.target_domain,
        "device": args.device, "overwrite": True if args.overwrite else None, "cdan_weight": args.cdan_weight,
        "grl_coefficient": args.grl_coefficient, "domain_hidden_dims": args.domain_hidden_dims,
        "domain_dropout": args.domain_dropout, "domain_learning_rate": args.domain_learning_rate,
        "domain_weight_decay": args.domain_weight_decay}
    config = load_cdan_config(args.config, overrides=overrides)
    if args.fold is not None and args.all_folds:
        raise ValueError("Use either --fold or --all-folds, not both.")
    if args.fold is not None:
        config.folds = [args.fold]
    elif args.all_folds:
        config.folds = list(range(5))
    if not args.all_seeds:
        config.seeds = [args.seed]
    if args.target_monitoring is not None:
        config.evaluation.target_monitoring = args.target_monitoring
        config.training = FixedEpochTrainingConfig(**{**vars(config.training), "target_monitoring_enabled": args.target_monitoring})
    config.validate()
    if args.resume_from is not None and (len(config.folds) != 1 or len(config.seeds) != 1 or args.both_directions):
        raise ValueError("--resume-from requires exactly one direction, fold, and seed.")
    if args.both_directions:
        results = run_cdan_both_directions(config, dry_run=args.dry_run, validate_only=args.validate_only)
        payload = {direction: [result.summary_row() for result in values] for direction, values in results.items()}
    else:
        runner = CDANExperimentRunner(config)
        if args.interrupt_after_epoch is not None:
            if len(config.folds) != 1 or len(config.seeds) != 1:
                raise ValueError("--interrupt-after-epoch requires exactly one fold and seed.")
            results = [
                runner.run_fold(
                    config.folds[0],
                    config.seeds[0],
                    interrupt_after_epoch=args.interrupt_after_epoch,
                )
            ]
        else:
            results = runner.run(dry_run=args.dry_run, validate_only=args.validate_only, resume_from=args.resume_from)
        payload = [result.summary_row() for result in results]
    print(json.dumps(payload, indent=2, default=str))


def run_prototype_pseudo(args: argparse.Namespace) -> None:
    if args.config is None:
        raise ValueError("--config is required for prototype-pseudo execution.")
    raw = yaml.safe_load(args.config.read_text(encoding="utf-8")) or {}
    configured = str((raw.get("experiment") or {}).get("method", "source_only"))
    if configured != "prototype_pseudo":
        raise PhaseNotImplementedError(f"Cannot reinterpret {configured!r} configuration as prototype_pseudo.")
    overrides = {
        "artifact_index": args.artifact_index,
        "artifact_root": args.artifact_root,
        "split_root": args.split_root,
        "roi_masks": args.roi_masks,
        "atlas_metadata": args.atlas_metadata,
        "output_root": args.output_root,
        "source_domain": args.source_domain,
        "target_domain": args.target_domain,
        "device": args.device,
        "overwrite": True if args.overwrite else None,
    }
    config = load_prototype_pseudo_config(args.config, overrides=overrides)
    if args.fold is not None and args.all_folds:
        raise ValueError("Use either --fold or --all-folds, not both.")
    if args.fold is not None:
        config.folds = [args.fold]
    elif args.all_folds:
        config.folds = list(range(5))
    if not args.all_seeds:
        config.seeds = [args.seed]
    if args.target_monitoring is not None:
        config.evaluation.target_monitoring = args.target_monitoring
        config.training = FixedEpochTrainingConfig(**{**vars(config.training), "target_monitoring_enabled": args.target_monitoring})
    config.validate()
    if args.resume_from is not None and (len(config.folds) != 1 or len(config.seeds) != 1 or args.both_directions):
        raise ValueError("--resume-from requires exactly one direction, fold, and seed.")
    if args.both_directions:
        results = run_prototype_pseudo_both_directions(config, dry_run=args.dry_run, validate_only=args.validate_only)
        payload = {direction: [result.summary_row() for result in values] for direction, values in results.items()}
    else:
        runner = PrototypePseudoExperimentRunner(config)
        if args.interrupt_after_epoch is not None:
            if len(config.folds) != 1 or len(config.seeds) != 1:
                raise ValueError("--interrupt-after-epoch requires exactly one fold and seed.")
            results = [runner.run_fold(config.folds[0], config.seeds[0], interrupt_after_epoch=args.interrupt_after_epoch)]
        else:
            results = runner.run(dry_run=args.dry_run, validate_only=args.validate_only, resume_from=args.resume_from)
        payload = [result.summary_row() for result in results]
    print(json.dumps(payload, indent=2, default=str))



def run_baseline(args: argparse.Namespace) -> None:
    if args.config is None:
        raise ValueError("--config is required for baseline execution.")
    config = load_baseline_config(
        args.config,
        overrides={
            "artifact_index": args.artifact_index,
            "output_root": args.output_root,
            "roi_masks": args.roi_masks,
            "source_domain": args.source_domain,
            "target_domain": args.target_domain,
            "device": args.device,
            "overwrite": True if args.overwrite else None,
            "target_monitoring": args.target_monitoring,
        },
    )
    if args.baseline_names and args.all_baselines:
        raise ValueError("Use --baseline-name or --all-baselines, not both.")
    selected = tuple(args.baseline_names or (list_baselines() if args.all_baselines else config.baseline_names))
    folds = (
        (args.fold,)
        if args.fold is not None
        else (tuple(range(config.n_splits)) if args.all_folds else config.folds)
    )
    seeds = config.seeds if args.all_seeds else (args.seed,)
    config = replace(
        config,
        baseline_names=selected,
        source_domain=args.source_domain or config.source_domain,
        target_domain=args.target_domain or config.target_domain,
        folds=folds,
        seeds=seeds,
        artifact_index=(args.artifact_index.resolve() if args.artifact_index else config.artifact_index),
        output_root=(args.output_root.resolve() if args.output_root else config.output_root),
        roi_masks=(args.roi_masks.resolve() if args.roi_masks else config.roi_masks),
        target_monitoring=(args.target_monitoring if args.target_monitoring is not None else config.target_monitoring),
        overwrite=(args.overwrite or config.overwrite),
        training=replace(config.training, device=args.device) if args.device else config.training,
    )
    config.validate()
    if args.fold is not None and args.all_folds:
        raise ValueError("Use either --fold or --all-folds, not both.")
    single_lifecycle = args.resume_from is not None or args.interrupt_after_epoch is not None
    if single_lifecycle and (
        len(selected) != 1 or len(folds) != 1 or len(seeds) != 1 or args.both_directions
    ):
        raise ValueError(
            "Baseline resume/interruption requires exactly one baseline, direction, fold, and seed."
        )
    if args.both_directions:
        results = run_baseline_both_directions(
            config,
            baseline_names=selected,
            dry_run=args.dry_run,
            validate_only=args.validate_only,
        )
        payload = {
            direction: {
                baseline: [result.summary_row() for result in values]
                for baseline, values in baseline_results.items()
            }
            for direction, baseline_results in results.items()
        }
    elif single_lifecycle:
        result = train_baseline_cv_fold(
            config,
            selected[0],
            folds[0],
            seeds[0],
            resume_from=args.resume_from,
            interrupt_after_epoch=args.interrupt_after_epoch,
        )
        payload = [result.summary_row()]
    else:
        results = run_all_requested_baselines(
            config,
            baseline_names=selected,
            dry_run=args.dry_run,
            validate_only=args.validate_only,
        )
        payload = {
            baseline: [result.summary_row() for result in values]
            for baseline, values in results.items()
        }
    print(json.dumps(payload, indent=2, default=str))

def main() -> None:
    args = build_parser().parse_args()
    if args.synthetic_smoke:
        run_synthetic_smoke(args)
        return
    method = args.method
    if method is None and args.config is not None:
        payload = yaml.safe_load(args.config.read_text(encoding="utf-8")) or {}
        method = str((payload.get("experiment") or {}).get("method", "source_only"))
    method = method or "source_only"
    if method == "source_only":
        run_source_only(args)
    elif method == "coral":
        run_coral(args)
    elif method == "mmd":
        run_mmd(args)
    elif method == "cdan":
        run_cdan(args)
    elif method == "prototype_pseudo":
        run_prototype_pseudo(args)
    elif method == "baseline":
        run_baseline(args)
    else:
        raise PhaseNotImplementedError(
            f"Method {method!r} is not implemented in Phase 14. "
            "Phase 15 evaluation remains phase-gated."
        )


if __name__ == "__main__":
    main()
