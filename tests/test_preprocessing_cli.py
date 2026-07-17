import subprocess
import sys

import numpy as np
import pandas as pd
import torch


def test_cli_smoke_adni_and_oasis(tmp_path):
    adni = tmp_path / "adni"
    (adni / "CN").mkdir(parents=True)
    np.save(adni / "CN" / "002_S_0619_scan.npy", np.ones((3, 3, 3), dtype=np.float32))
    adni_out = tmp_path / "adni_out"
    cmd = [
        sys.executable,
        "scripts/preprocess.py",
        "--config",
        "configs/preprocessing/default.yaml",
        "--cohort",
        "ADNI",
        "--input-root",
        str(adni),
        "--output-root",
        str(adni_out),
        "--target-shape",
        "4",
        "4",
        "4",
        "--overwrite",
    ]
    completed = subprocess.run(cmd, cwd=".", text=True, capture_output=True, check=False)
    assert completed.returncode == 0, completed.stderr
    tensor = torch.load(adni_out / "CN" / "002_S_0619_MRI.pt", map_location="cpu", weights_only=True)
    assert tuple(tensor.shape) == (1, 4, 4, 4)
    assert (adni_out / "preprocessing_manifest.csv").exists()

    oasis = tmp_path / "oasis"
    oasis.mkdir()
    np.save(oasis / "OASIS1_0001_T1_brain.npy", np.ones((3, 3, 3), dtype=np.float32))
    meta = oasis / "meta.csv"
    pd.DataFrame([{"ID": "OASIS1_0001", "CDR": 0}]).to_csv(meta, index=False)
    oasis_out = tmp_path / "oasis_out"
    cmd = [
        sys.executable,
        "scripts/preprocess.py",
        "--config",
        "configs/preprocessing/default.yaml",
        "--cohort",
        "OASIS",
        "--input-root",
        str(oasis),
        "--metadata-csv",
        str(meta),
        "--output-root",
        str(oasis_out),
        "--target-shape",
        "4",
        "4",
        "4",
        "--overwrite",
    ]
    completed = subprocess.run(cmd, cwd=".", text=True, capture_output=True, check=False)
    assert completed.returncode == 0, completed.stderr
    assert (oasis_out / "CN" / "OASIS1_0001_MRI.pt").exists()


def test_failure_isolation(tmp_path):
    root = tmp_path / "adni"
    (root / "CN").mkdir(parents=True)
    np.save(root / "CN" / "002_S_0619_ok.npy", np.ones((3, 3, 3), dtype=np.float32))
    (root / "CN" / "003_S_0001_bad.npy").write_text("corrupt", encoding="utf-8")
    out = tmp_path / "out"
    cmd = [
        sys.executable,
        "scripts/preprocess.py",
        "--config",
        "configs/preprocessing/default.yaml",
        "--cohort",
        "ADNI",
        "--input-root",
        str(root),
        "--output-root",
        str(out),
        "--target-shape",
        "4",
        "4",
        "4",
        "--overwrite",
        "--continue-on-error",
    ]
    completed = subprocess.run(cmd, cwd=".", text=True, capture_output=True, check=False)
    assert completed.returncode == 0
    assert (out / "CN" / "002_S_0619_MRI.pt").exists()
    failures = (out / "failures.csv").read_text(encoding="utf-8")
    assert "003_S_0001" in failures
