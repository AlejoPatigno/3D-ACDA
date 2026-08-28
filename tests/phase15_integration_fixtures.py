from __future__ import annotations

import json
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType
from typing import Any

import yaml

from acda3d.evaluation.schemas import Direction, MethodId
from tests.phase15_discovery_fixtures import (
    add_identity_population_controls,
    write_baseline_candidate,
    write_shared_candidate,
)

ROOT = Path(__file__).parents[1]
CANONICAL_CONFIG = ROOT / "configs/evaluation/predictive.yaml"
SHARED_METHODS = (
    MethodId.SOURCE_ONLY, MethodId.CORAL, MethodId.MMD,
    MethodId.CDAN, MethodId.PROTOTYPE_PSEUDO,
)


def cli_module() -> ModuleType:
    name = "phase15_integration_cli"
    spec = spec_from_file_location(name, ROOT / "scripts/evaluate.py")
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _manifest_payload(
    path: Path, *, method: MethodId, direction: Direction, checkpoint: str
) -> str:
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload.update(
        method_id=method.value, direction=direction.value, seed=17, fold=2,
        logical_checkpoint=checkpoint,
    )
    return json.dumps(payload, sort_keys=True)


def write_matrix(
    root: Path,
    *,
    methods: tuple[MethodId, ...] = tuple(MethodId),
    include_sensitivity: bool = False,
) -> tuple[Path, dict[str, Any]]:
    runs = root / "runs"
    policies = ("best_source_f1", "last") if include_sensitivity else ("best_source_f1",)
    for method in methods:
        for direction in Direction:
            if method in SHARED_METHODS:
                for checkpoint in policies:
                    base = write_shared_candidate(
                        runs, method=method.value, direction=direction.value,
                        seed=17, fold=2, checkpoint=checkpoint,
                    )
                    manifest = base / "run_manifest.json"
                    (base / f"{checkpoint}_run_manifest.json").write_text(
                        _manifest_payload(
                            manifest, method=method, direction=direction, checkpoint=checkpoint
                        ),
                        encoding="utf-8",
                    )
            else:
                base = write_baseline_candidate(
                    runs, method=method.value, direction=direction.value, seed=17, fold=2
                )
                manifest = base / "run_manifest.json"
                manifest.write_text(
                    _manifest_payload(
                        manifest, method=method, direction=direction,
                        checkpoint="best_source_f1",
                    ),
                    encoding="utf-8",
                )

    config: dict[str, Any] = yaml.safe_load(CANONICAL_CONFIG.read_text(encoding="utf-8"))
    config.update(
        analysis_mode="synthetic_test_only", expected_folds=[2], expected_seeds=[17]
    )
    add_identity_population_controls(config, runs)
    config["shared_method"]["companion_patterns"] = [
        "shared/{method}/{direction}/seed_{seed}/fold_{fold}/{logical_checkpoint}_run_manifest.json"
    ]
    config_path = root / "predictive.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    config["_config_path"] = str(config_path)
    return runs, config


def matrix_argv(
    config: dict[str, Any],
    runs: Path,
    mode: str,
    *,
    methods: tuple[MethodId, ...] = tuple(MethodId),
    output: Path | None = None,
) -> list[str]:
    argv = ["--config", config["_config_path"], "--runs-root", str(runs), "--both-directions"]
    if methods == tuple(MethodId):
        argv.append("--all-methods")
    else:
        for method in methods:
            argv.extend(("--method", method.value))
    argv.append(mode)
    if output is not None:
        argv.extend(("--output-root", str(output)))
    return argv
