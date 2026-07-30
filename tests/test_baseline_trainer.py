from __future__ import annotations

from pathlib import Path

import pytest
import torch
from torch import nn
from torch.utils.data import DataLoader

from pada3dacb.exceptions import TrainingRuntimeError
from pada3dacb.training.baseline_trainer import (
    BaselineTrainConfig,
    ClassificationOnlyLoss,
    ClassificationOnlyTrainer,
)


class TinyBaseline(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.classifier = nn.Linear(2, 3)

    def forward(self, x: torch.Tensor) -> dict[str, torch.Tensor]:
        return {"logits": self.classifier(x)}


def _loader(labels: tuple[int, ...] = (0, 1, 2)) -> list[dict[str, torch.Tensor]]:
    x = torch.tensor([[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]])
    y = torch.tensor(labels)
    return [{"x": x, "y": y}]


def _shuffled_loader(seed: int) -> DataLoader:
    rows = [
        {"x": torch.tensor([float(index), 1.0]), "y": torch.tensor(index % 3)}
        for index in range(6)
    ]
    return DataLoader(
        rows, batch_size=2, shuffle=True, generator=torch.Generator().manual_seed(seed)
    )


def _trainer(
    tmp_path: Path,
    *,
    epochs: int = 3,
    seed: int = 7,
    identity: dict[str, object] | None = None,
) -> ClassificationOnlyTrainer:
    torch.manual_seed(seed)
    return ClassificationOnlyTrainer(
        TinyBaseline(),
        BaselineTrainConfig(n_epochs=epochs, lr=0.01, use_amp=False, seed=seed),
        run_dir=tmp_path,
        identity=identity,
    )


def test_classification_loss_matches_cross_entropy_with_label_smoothing() -> None:
    logits = torch.tensor([[2.0, 0.0, -1.0], [0.0, 1.0, 2.0]], requires_grad=True)
    labels = torch.tensor([0, 2])

    actual = ClassificationOnlyLoss(label_smoothing=0.1)(logits, labels)
    expected = torch.nn.functional.cross_entropy(logits, labels, label_smoothing=0.1)

    torch.testing.assert_close(actual, expected, rtol=0, atol=0)
    actual.backward()
    assert logits.grad is not None and torch.isfinite(logits.grad).all()


def test_fit_runs_fixed_epochs_and_selects_only_source_macro_f1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    trainer = _trainer(tmp_path)
    source_scores = iter((0.2, 0.8, 0.7, 0.7))
    target_scores = iter((0.99, 0.01, 1.0, 1.0))

    def fake_evaluate(loader: object, prefix: str) -> dict[str, float]:
        score = next(source_scores if prefix == "source_validation" else target_scores)
        return {f"{prefix}/macro_f1": score, f"{prefix}/loss": 0.0}

    monkeypatch.setattr(trainer, "evaluate", fake_evaluate)
    result = trainer.fit(_loader(), _loader(), _loader(labels=(2, 2, 2)))

    assert len(result.history) == 3
    assert result.best_source_epoch == 2
    assert result.best_source_macro_f1 == 0.8
    assert trainer.completed_epoch == 3


def test_target_monitoring_cannot_change_training_state(tmp_path: Path) -> None:
    without_target = _trainer(tmp_path / "without")
    with_target = _trainer(tmp_path / "with")

    without_target.fit(_loader(), _loader())
    with_target.fit(_loader(), _loader(), _loader(labels=(2, 2, 2)))

    for left, right in zip(
        without_target.model.parameters(), with_target.model.parameters(), strict=True
    ):
        torch.testing.assert_close(left, right, rtol=0, atol=0)
    assert without_target.best_source_macro_f1 == with_target.best_source_macro_f1


def test_target_adaptation_loader_is_rejected(tmp_path: Path) -> None:
    trainer = _trainer(tmp_path, epochs=1)

    with pytest.raises(TrainingRuntimeError, match="target adaptation"):
        trainer.fit(_loader(), _loader(), target_adaptation_loader=_loader())


def test_interrupted_resume_matches_uninterrupted_training(tmp_path: Path) -> None:
    uninterrupted = _trainer(tmp_path / "full", epochs=4)
    uninterrupted_result = uninterrupted.fit(_loader(), _loader())

    interrupted = _trainer(tmp_path / "resume", epochs=4)
    interrupted.fit(_loader(), _loader(), interrupt_after_epoch=2)
    resumed = _trainer(tmp_path / "resume", epochs=4)
    resumed_result = resumed.fit(
        _loader(), _loader(), resume_from=tmp_path / "resume" / "last.pt"
    )

    assert len(uninterrupted_result.history) == len(resumed_result.history) == 4
    for left, right in zip(
        uninterrupted.model.parameters(), resumed.model.parameters(), strict=True
    ):
        torch.testing.assert_close(left, right, rtol=0, atol=0)
    assert uninterrupted_result.best_source_macro_f1 == resumed_result.best_source_macro_f1


def test_resume_restores_loader_generator_state_exactly(tmp_path: Path) -> None:
    uninterrupted = _trainer(tmp_path / "full-generator", epochs=4)
    uninterrupted_result = uninterrupted.fit(_shuffled_loader(19), _loader())

    interrupted = _trainer(tmp_path / "resume-generator", epochs=4)
    interrupted.fit(_shuffled_loader(19), _loader(), interrupt_after_epoch=2)
    resumed = _trainer(tmp_path / "resume-generator", epochs=4)
    resumed_result = resumed.fit(
        _shuffled_loader(19),
        _loader(),
        resume_from=tmp_path / "resume-generator" / "last.pt",
    )

    assert uninterrupted_result.history == resumed_result.history
    for left, right in zip(
        uninterrupted.model.parameters(), resumed.model.parameters(), strict=True
    ):
        torch.testing.assert_close(left, right, rtol=0, atol=0)


def test_resume_rejects_different_experiment_identity(tmp_path: Path) -> None:
    interrupted = _trainer(tmp_path, epochs=2, identity={"experiment_hash": "original"})
    interrupted.fit(_loader(), _loader(), interrupt_after_epoch=1)
    incompatible = _trainer(tmp_path, epochs=2, identity={"experiment_hash": "changed"})

    with pytest.raises(TrainingRuntimeError, match="identity mismatch"):
        incompatible.fit(_loader(), _loader(), resume_from=tmp_path / "last.pt")


def test_config_rejects_non_fixed_or_invalid_training_values() -> None:
    with pytest.raises(TrainingRuntimeError):
        BaselineTrainConfig(n_epochs=0).validate()
    with pytest.raises(TrainingRuntimeError):
        BaselineTrainConfig(lr=0).validate()
    with pytest.raises(TypeError):
        BaselineTrainConfig(early_stopping=True)  # type: ignore[call-arg]
