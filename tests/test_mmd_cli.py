import json
import subprocess
import sys
from pathlib import Path

from tests.phase11_helpers import make_mmd_environment


def test_mmd_cli_dry_run_and_cdan_config_boundary(tmp_path: Path):
    config = make_mmd_environment(tmp_path)
    command = [
        sys.executable,
        "scripts/train.py",
        "--config",
        str(config),
        "--method",
        "mmd",
        "--mmd-weight",
        "1.0",
        "--mmd-bandwidths",
        "0.5",
        "1.0",
        "2.0",
        "--fold",
        "0",
        "--dry-run",
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload[0]["status"] == "PENDING"
    missing_config = subprocess.run(
        [sys.executable, "scripts/train.py", "--method", "cdan"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert missing_config.returncode != 0
    assert "--config is required for CDAN execution" in missing_config.stderr
