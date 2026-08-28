import torch

from acda3d.data.artifact_wiring import load_artifact_index
from acda3d.data.datasets import (
    LabeledSourceDataset,
    LabeledTargetDataset,
    SupervisedMRIDataset,
    TargetAdaptationDataset,
)
from tests.phase6_helpers import make_artifact_index


def test_dataset_role_contracts(tmp_path):
    index = make_artifact_index(tmp_path)
    records = load_artifact_index(index, artifact_root=index.parent).records
    source_record = next(record for record in records if record.cohort == "ADNI")
    target_record = next(record for record in records if record.cohort == "OASIS")
    kwargs = {"expected_spatial_shape": (2, 2, 2), "expected_num_rois": 2}

    source = LabeledSourceDataset([source_record], **kwargs)[0]
    assert set(source) == {"x", "y", "c_target", "g_bar", "subject_id", "subject_hash", "cohort", "label_name"}
    assert source["x"].shape == (1, 2, 2, 2) and source["x"].dtype == torch.float32
    assert source["y"].ndim == 0 and source["y"].dtype == torch.long
    assert source["c_target"].shape == source["g_bar"].shape == (2,)

    adaptation = TargetAdaptationDataset([target_record], **kwargs)[0]
    assert set(adaptation) == {"x", "subject_id", "subject_hash", "cohort"}
    assert "y" not in adaptation and "label_name" not in adaptation

    evaluation = LabeledTargetDataset([target_record], **kwargs)[0]
    assert set(evaluation) == {"x", "y", "subject_id", "subject_hash", "cohort", "label_name"}

    supervised = SupervisedMRIDataset([source_record], profile="classification_only", **kwargs)[0]
    assert "c_target" not in supervised and "g_bar" not in supervised
    full = SupervisedMRIDataset([source_record], profile="source_full_artifacts", **kwargs)[0]
    assert "c_target" in full and "g_bar" in full
