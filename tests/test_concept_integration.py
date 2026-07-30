"""Synthetic matrix integration test for Phase 16."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import yaml

from scripts.evaluate_concepts import ExitCode, main


def test_complete_synthetic_method_direction_policy_matrix(tmp_path) -> None:
    config = yaml.safe_load(Path("configs/evaluation/concepts.yaml").read_text(encoding="utf-8"))
    config["analysis_mode"] = "synthetic_test_only"
    config["top_k"] = [1, 2]
    config_path = tmp_path / "synthetic.yaml"
    config_path.write_text(yaml.safe_dump(config, sort_keys=True), encoding="utf-8")
    runs = tmp_path / "runs"
    artifacts = tmp_path / "artifacts"
    output = tmp_path / "results"
    runs.mkdir()
    artifacts.mkdir()

    code = main(
        [
            "--config", str(config_path),
            "--runs-root", str(runs),
            "--artifact-root", str(artifacts),
            "--output-root", str(output),
            "--both-directions",
            "--all-pada-methods",
            "--include-sensitivity",
            "--bootstrap-replicates", "100",
            "--bootstrap-seed", "17",
        ]
    )

    assert code == ExitCode.SUCCESS
    manifest = json.loads((output / "evaluation_manifest.json").read_text(encoding="utf-8"))
    assert manifest["methods"] == [
        "source_only", "coral", "mmd", "cdan", "prototype_pseudo"
    ]
    assert manifest["directions"] == ["adni_to_oasis", "oasis_to_adni"]
    assert manifest["checkpoint_policies"] == ["best_source_f1", "last"]
    assert manifest["analysis_mode"] == "synthetic_test_only"

    with (output / "method_status.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    included = [row for row in rows if row["status"] == "included"]
    not_applicable = [
        row for row in rows
        if row["status"] == "not_applicable_no_pada3dacb_concept_head"
    ]
    assert len(included) == 5 * 2 * 2
    assert len(not_applicable) == 2 * 2 * 2
    assert {row["method"] for row in not_applicable} == {"aagn", "faster_snn"}
