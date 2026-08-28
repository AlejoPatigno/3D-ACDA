"""Complete synthetic selector regression for all Phase 16 methods."""

from __future__ import annotations

import csv
import io
import json

from acda3d.evaluation.concepts.report import build_synthetic_fixture_bundle
from acda3d.evaluation.schemas import CheckpointPolicy, Direction, MethodId

ACDA_METHODS = (
    MethodId.SOURCE_ONLY,
    MethodId.CORAL,
    MethodId.MMD,
    MethodId.CDAN,
    MethodId.PROTOTYPE_PSEUDO,
)


def test_all_methods_directions_and_policies_have_complete_fixture_outputs() -> None:
    plan, artifacts = build_synthetic_fixture_bundle(
        evaluation_identity="e" * 64,
        methods=ACDA_METHODS,
        directions=(Direction.ADNI_TO_OASIS, Direction.OASIS_TO_ADNI),
        checkpoint_policies=(
            CheckpointPolicy.PRIMARY_BEST_SOURCE_F1,
            CheckpointPolicy.SENSITIVITY_LAST,
        ),
        metrics={
            "concept_mae": 0.05,
            "concept_rmse": 0.05,
            "anatomy_mae": 0.10,
            "anatomy_rmse": 0.10,
            "top1_agreement_rate": 1.0,
            "mean_js_divergence": 0.0,
        },
        resolved_config={"analysis_mode": "synthetic_test_only"},
        identity_inputs={
            "configuration_sha256": "a" * 64,
            "authorization_sha256": "0" * 64,
            "ordered_input_sha256s": [],
        },
        library_versions={"python": "test"},
        bootstrap_replicates=100,
        bootstrap_seed=17,
    )

    assert set(plan.intended_relative_paths) == set(artifacts)
    manifest = json.loads(artifacts["evaluation_manifest.json"])
    assert manifest["methods"] == [method.value for method in ACDA_METHODS]
    rows = list(csv.DictReader(io.StringIO(artifacts["method_status.csv"].decode())))
    assert sum(row["status"] == "included" for row in rows) == 20
    assert sum(row["status"].startswith("not_applicable") for row in rows) == 8
    assert all(b"fixture_only" in payload for path, payload in artifacts.items() if path.endswith(".csv") and "method_status" in path)
