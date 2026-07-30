import subprocess
import sys

from tests.phase6_helpers import make_artifact_index


def run_cli(index, root, *extra):
    return subprocess.run(
        [
            sys.executable,
            "scripts/create_splits.py",
            "--config",
            "configs/splits/default.yaml",
            "--artifact-index",
            str(index),
            "--artifact-root",
            str(index.parent),
            "--split-root",
            str(root),
            *extra,
        ],
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
    )


def test_cli_directions_all_and_dry_run(tmp_path):
    index = make_artifact_index(tmp_path)
    forward_root = tmp_path / "forward"
    forward = run_cli(index, forward_root, "--source-domain", "ADNI", "--target-domain", "OASIS")
    assert forward.returncode == 0, forward.stderr
    assert (forward_root / "ADNI_to_OASIS" / "source_folds.csv").exists()
    reverse_root = tmp_path / "reverse"
    reverse = run_cli(index, reverse_root, "--source-domain", "OASIS", "--target-domain", "ADNI")
    assert reverse.returncode == 0, reverse.stderr
    assert (reverse_root / "OASIS_to_ADNI" / "target_split.csv").exists()
    both_root = tmp_path / "both"
    both = run_cli(index, both_root, "--all-directions")
    assert both.returncode == 0, both.stderr
    assert (both_root / "ADNI_to_OASIS" / "protocol.json").exists()
    assert (both_root / "OASIS_to_ADNI" / "protocol.json").exists()
    dry_root = tmp_path / "dry"
    dry = run_cli(index, dry_root, "--all-directions", "--dry-run")
    assert dry.returncode == 0, dry.stderr
    assert not dry_root.exists()


def test_no_forbidden_phase_seven_behavior():
    from pathlib import Path

    text = "\n".join(path.read_text(encoding="utf-8") for path in Path("src/pada3dacb/data").glob("*.py"))
    for forbidden in ("Encoder3D", "CORAL", "MMD", "CDAN", "pseudo-label", "fit_concept_normalizer", "ensure_artifact_cache"):
        assert forbidden not in text
