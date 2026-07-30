import json
import subprocess
import sys
from pathlib import Path

from tests.phase10_helpers import make_coral_environment


def test_coral_cli_dry_run_and_phase_gate(tmp_path: Path):
    config = make_coral_environment(tmp_path)
    command = [
        sys.executable,
        "scripts/train.py",
        "--config",
        str(config),
        "--method",
        "coral",
        "--coral-weight",
        "1.0",
        "--fold",
        "0",
        "--dry-run",
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload[0]["status"] == "PENDING"
    forbidden = subprocess.run(
        [sys.executable, "scripts/train.py", "--method", "mmd"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert forbidden.returncode != 0 and "not implemented in Phase 10" in forbidden.stderr
