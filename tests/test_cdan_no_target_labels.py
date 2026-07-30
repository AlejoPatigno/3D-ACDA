import pytest

from pada3dacb.exceptions import TrainingRuntimeError
from pada3dacb.training import UDATrainer


def test_cdan_target_batch_rejects_diagnostic_label_keys():
    with pytest.raises(TrainingRuntimeError):
        UDATrainer._validate_target_batch({"x": __import__("torch").ones(2, 1), "subject_id": ["a", "b"], "subject_hash": ["a", "b"], "cohort": ["OASIS", "OASIS"], "true_label": ["CN", "AD"]})


@pytest.mark.parametrize("label_key", ["diagnosis", "diagnosis_label"])
def test_cdan_target_batch_rejects_diagnosis_label_tensor_aliases(label_key):
    torch = __import__("torch")

    with pytest.raises(TrainingRuntimeError, match="forbidden label fields"):
        UDATrainer._validate_target_batch({
            "x": torch.ones(2, 1),
            "subject_id": ["a", "b"],
            "subject_hash": ["hash-a", "hash-b"],
            "cohort": ["OASIS", "OASIS"],
            label_key: torch.tensor([0, 2]),
        })
