from pathlib import Path

import yaml

from tests.phase11_helpers import make_mmd_environment


def make_cdan_environment(tmp_path: Path, *, weight: float | None = 1.0) -> Path:
    source = make_mmd_environment(tmp_path)
    payload = yaml.safe_load(source.read_text(encoding="utf-8"))
    payload["experiment"].update({"name": "synthetic_cdan", "display_name": "3D-ACDA + CDAN", "method": "cdan"})
    payload["adaptation"] = {
        "name": "cdan", "feature": "z", "probability_source": "latent_probabilities",
        "conditional_mode": "exact_outer_product", "weight": weight, "active_during_warmup": False,
        "grl": {"schedule": "constant", "coefficient": 1.0},
        "domain_labels": {"source": 0, "target": 1},
        "discriminator": {"hidden_dims": [8, 4], "activation": "relu", "dropout": 0.0,
                          "output_dim": 1, "initialization": "pytorch_default",
                          "optimizer_group": {"learning_rate": 0.001, "weight_decay": 0.0}},
    }
    path = tmp_path / "cdan.yaml"
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    return path
