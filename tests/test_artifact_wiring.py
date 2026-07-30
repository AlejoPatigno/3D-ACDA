from pathlib import Path

import pandas as pd
import pytest

from pada3dacb.data.artifact_wiring import load_artifact_index
from pada3dacb.exceptions import DatasetContractError
from tests.phase6_helpers import make_artifact_index


def test_relative_paths_order_and_coverage(tmp_path):
    index = make_artifact_index(tmp_path)
    result = load_artifact_index(index, artifact_root=index.parent, profile="source_full_artifacts")
    assert result.report.valid
    assert len(result.records) == 30
    assert result.records == sorted(result.records, key=lambda record: (record.cohort, record.subject_hash))
    assert all(record.derivative_path.is_absolute() for record in result.records)


def test_absolute_path_and_prefix_remapping(tmp_path):
    index = make_artifact_index(tmp_path)
    frame = pd.read_csv(index)
    old = Path("C:/old/cache")
    for column in ("derivative_path", "concept_path", "jacobian_path"):
        frame[column] = frame[column].map(lambda value: str(old / value))
    frame.to_csv(index, index=False)
    result = load_artifact_index(index, artifact_root=index.parent, profile="source_full_artifacts", old_prefix=old, new_prefix=index.parent)
    assert len(result.report.remappings) == len(frame) * 3


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda frame: frame.__setitem__("cohort", ["OTHER"] + frame.cohort.tolist()[1:]), "Unsupported cohort"),
        (lambda frame: frame.__setitem__("class_label", ["OTHER"] + frame.class_label.tolist()[1:]), "Unsupported diagnostic"),
        (lambda frame: frame.__setitem__("label_index", [2] + frame.label_index.tolist()[1:]), "mismatch"),
        (lambda frame: frame.__setitem__("subject_hash", [frame.subject_hash.iloc[1]] + frame.subject_hash.tolist()[1:]), "Duplicate subject"),
        (lambda frame: frame.__setitem__("derivative_path", [frame.derivative_path.iloc[1]] + frame.derivative_path.tolist()[1:]), "Duplicate derivative"),
        (lambda frame: frame.__setitem__("concept_status", ["FAILED"] + frame.concept_status.tolist()[1:]), "invalid concept status"),
    ],
)
def test_invalid_index_contracts(tmp_path, mutation, message):
    index = make_artifact_index(tmp_path)
    frame = pd.read_csv(index)
    mutation(frame)
    frame.to_csv(index, index=False)
    with pytest.raises(DatasetContractError, match=message):
        load_artifact_index(index, artifact_root=index.parent, profile="source_full_artifacts")


def test_missing_files_required_by_profile(tmp_path):
    index = make_artifact_index(tmp_path)
    frame = pd.read_csv(index)
    (index.parent / frame.loc[0, "concept_path"]).unlink()
    load_artifact_index(index, artifact_root=index.parent, profile="classification_only")
    with pytest.raises(DatasetContractError, match="concept file does not exist"):
        load_artifact_index(index, artifact_root=index.parent, profile="source_full_artifacts")
