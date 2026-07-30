import subprocess
import sys
from pathlib import Path

from tests.phase9_helpers import make_source_only_environment


def test_source_only_cli_dry_run_and_unsupported_method(tmp_path: Path):
    config = make_source_only_environment(tmp_path)
    command = [
        sys.executable, "scripts/train.py", "--config", str(config), "--method",
        "source_only", "--fold", "0", "--dry-run",
    ]
    result = subprocess.run(command, cwd=Path(__file__).parents[1], capture_output=True, text=True)
    assert result.returncode == 0
    assert '"status": "PENDING"' in result.stdout
    assert not (tmp_path / "outputs").exists()
    unsupported = subprocess.run(
        [sys.executable, "scripts/train.py", "--config", str(config), "--method", "coral", "--dry-run"],
        cwd=Path(__file__).parents[1], capture_output=True, text=True,
    )
    assert unsupported.returncode != 0
    assert "not implemented in Phase 9" in unsupported.stderr
