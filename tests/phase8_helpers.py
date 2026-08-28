from pathlib import Path

import torch
from torch import nn
from torch.utils.data import DataLoader

from acda3d.losses import CoreACDA3DLoss
from acda3d.models import ACDA3DOutput
from acda3d.training import FixedEpochTrainingConfig, SourceOnlyTrainer


class TinyACDA3D(nn.Module):
    public_name = "3D-ACDA"

    def __init__(self, num_rois: int = 2):
        super().__init__()
        self.num_rois = num_rois
        self.num_classes = 3
        self.encoder = nn.Linear(1, 4)
        self.latent = nn.Linear(4, 3)
        self.concept_predictor = nn.Linear(4, num_rois)
        self.concept_classifier = nn.Linear(num_rois, 3)

    def forward(self, x, roi_masks):
        hidden = torch.tanh(self.encoder(x.mean(dim=(1, 2, 3, 4), keepdim=False).unsqueeze(1)))
        concepts = torch.sigmoid(self.concept_predictor(hidden))
        latent_logits = self.latent(hidden)
        concept_logits = self.concept_classifier(concepts)
        tokens = hidden.unsqueeze(1).expand(-1, self.num_rois, -1)
        attention = torch.full(
            (x.shape[0], self.num_rois), 1 / self.num_rois, device=x.device
        )
        return ACDA3DOutput(
            F=x,
            T=tokens,
            U=tokens,
            z=hidden,
            alpha=attention,
            latent_logits=latent_logits,
            latent_probabilities=torch.softmax(latent_logits, -1),
            concepts=concepts,
            concept_logits=concept_logits,
            concept_probabilities=torch.softmax(concept_logits, -1),
        )


def make_loader(*, shuffle: bool = False, seed: int = 7, target_only: bool = False):
    rows = []
    for index in range(6):
        row = {
            "x": torch.full((1, 2, 2, 2), float(index + 1) / 6),
            "y": torch.tensor(index % 3, dtype=torch.long),
        }
        if not target_only:
            row["c_target"] = torch.tensor([0.25, 0.75])
            row["g_bar"] = torch.tensor([0.4, 0.6])
        rows.append(row)
    generator = torch.Generator().manual_seed(seed)
    return DataLoader(rows, batch_size=2, shuffle=shuffle, generator=generator)


def make_trainer(
    run_dir: Path,
    *,
    warmup_epochs: int = 1,
    full_epochs: int = 1,
    seed: int = 11,
):
    torch.manual_seed(seed)
    model = TinyACDA3D()
    config = FixedEpochTrainingConfig(
        warmup_epochs=warmup_epochs,
        full_epochs=full_epochs,
        learning_rate=1e-2,
        weight_decay=1e-4,
        checkpoint_every=1,
        mixed_precision=True,
        seed=seed,
    )
    return SourceOnlyTrainer(
        model,
        CoreACDA3DLoss(2),
        torch.ones(2, 1, 1, 1),
        run_dir,
        config=config,
        split_assignment_hash="split",
        atlas_hash="atlas",
        roi_order_hash="roi-order",
    )
