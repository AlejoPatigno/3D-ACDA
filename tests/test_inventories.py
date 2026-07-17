import numpy as np

from pada3dacb.data.inventories import (
    choose_oasis_scan,
    discover_and_select,
    extract_adni_subject_id,
    extract_oasis_base_id,
    is_supported_file,
)


def test_supported_extensions_and_ids(tmp_path):
    assert is_supported_file("a.nii.gz", [".nii.gz"])
    assert not is_supported_file("a.txt", [".nii.gz"])
    assert extract_adni_subject_id("root/002_S_0619/file.nii.gz") == "002_S_0619"
    assert extract_oasis_base_id("OASIS1_0001_MR1.nii.gz") == "OASIS1_0001"


def test_adni_discovery_deterministic(tmp_path):
    root = tmp_path / "adni"
    cn = root / "CN"
    cn.mkdir(parents=True)
    np.save(cn / "002_S_0619_b.npy", np.ones((2, 2, 2)))
    np.save(cn / "002_S_0619_a.npy", np.ones((2, 2, 2)))
    selected = discover_and_select("ADNI", root, [".npy"])
    assert len(selected) == 1
    assert selected[0].subject_id == "002_S_0619"
    assert selected[0].selected_path.name == "002_S_0619_a.npy"


def test_oasis_discovery_and_priority(tmp_path):
    root = tmp_path / "oasis"
    root.mkdir()
    np.save(root / "OASIS1_0001_plain.npy", np.ones((2, 2, 2)))
    np.save(root / "OASIS1_0001_T1_brain.npy", np.ones((2, 2, 2)))
    metadata = root / "meta.csv"
    metadata.write_text("ID,CDR\nOASIS1_0001,0\n", encoding="utf-8")
    selected = discover_and_select("OASIS", root, [".npy"], metadata)
    assert len(selected) == 1
    assert selected[0].class_label == "CN"
    assert selected[0].selected_path.name == "OASIS1_0001_T1_brain.npy"
    assert choose_oasis_scan(selected[0].all_paths).name == "OASIS1_0001_T1_brain.npy"
