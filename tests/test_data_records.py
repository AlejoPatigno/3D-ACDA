
import pytest

from acda3d.data.records import CLASS_ORDER, CLASS_TO_INDEX, SubjectRecord, requirement_profile
from acda3d.exceptions import DatasetContractError


def test_class_mapping_identity_and_roundtrip(tmp_path):
    assert CLASS_ORDER == ("CN", "MCI", "AD")
    assert CLASS_TO_INDEX == {"CN": 0, "MCI": 1, "AD": 2}
    record = SubjectRecord("hash", "ADNI", "MCI", 1, (tmp_path / "x.pt").resolve(), subject_id="subject")
    record.validate()
    assert record.identity == "ADNI:hash"
    assert SubjectRecord.from_dict(record.to_dict()) == record


def test_invalid_record_and_profiles(tmp_path):
    with pytest.raises(DatasetContractError, match="mismatch"):
        SubjectRecord("hash", "ADNI", "CN", 2, (tmp_path / "x.pt").resolve()).validate()
    assert requirement_profile("classification_only").concept is False
    assert requirement_profile("source_full_artifacts").jacobian is True
    with pytest.raises(DatasetContractError, match="Unknown"):
        requirement_profile("other")
