import torch

from pada3dacb.data.artifact_wiring import load_artifact_index
from pada3dacb.data.datasets import LabeledSourceDataset, TargetAdaptationDataset
from pada3dacb.data.loaders import (
    DataLoaderConfig,
    build_source_train_loader,
    build_source_validation_loader,
    build_target_adaptation_loader,
)
from tests.phase6_helpers import make_artifact_index


def _order(loader):
    return [subject for batch in loader for subject in batch["subject_hash"]]


def test_dataloader_defaults_and_determinism(tmp_path):
    index = make_artifact_index(tmp_path)
    records = load_artifact_index(index, artifact_root=index.parent).records
    source_records = [record for record in records if record.cohort == "ADNI"]
    target_records = [record for record in records if record.cohort == "OASIS"]
    kwargs = {"expected_spatial_shape": (2, 2, 2), "expected_num_rois": 2}
    source = LabeledSourceDataset(source_records, **kwargs)
    target = TargetAdaptationDataset(target_records, **kwargs)
    config = DataLoaderConfig(batch_size=4, num_workers=0, pin_memory=False)
    first = _order(build_source_train_loader(source, config, seed=7))
    second = _order(build_source_train_loader(source, config, seed=7))
    assert first == second
    assert len(first) == 12
    validation = _order(build_source_validation_loader(source, config, seed=7))
    assert validation == [record.subject_hash for record in source_records]
    target_batch = next(iter(build_target_adaptation_loader(target, config, seed=7)))
    assert set(target_batch) == {"x", "subject_id", "subject_hash", "cohort"}
    assert target_batch["x"].shape == (4, 1, 2, 2, 2)
    assert target_batch["x"].dtype == torch.float32
