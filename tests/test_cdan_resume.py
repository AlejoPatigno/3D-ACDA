from pada3dacb.adaptation import DomainDiscriminatorConfig


def test_cdan_discriminator_provenance_is_stable_and_normalized():
    config = DomainDiscriminatorConfig(12, [8, 4], "relu", 0.1)

    assert config.resolved_dict() == {
        "input_dim": 12,
        "hidden_dims": [8, 4],
        "activation": "relu",
        "dropout": 0.1,
        "output_dim": 1,
        "initialization": "pytorch_default",
    }


def test_cdan_discriminator_provenance_changes_with_scientific_settings():
    base = DomainDiscriminatorConfig(12, (8, 4), "relu", 0.1).resolved_dict()
    wider = DomainDiscriminatorConfig(12, (16, 4), "relu", 0.1).resolved_dict()
    dropout = DomainDiscriminatorConfig(12, (8, 4), "relu", 0.2).resolved_dict()

    assert wider != base
    assert dropout != base


def test_cdan_discriminator_config_round_trips_from_checkpoint_provenance():
    saved = DomainDiscriminatorConfig(12, (8, 4), "gelu", 0.25).resolved_dict()

    restored = DomainDiscriminatorConfig(
        input_dim=saved["input_dim"],
        hidden_dims=saved["hidden_dims"],
        activation=saved["activation"],
        dropout=saved["dropout"],
        output_dim=saved["output_dim"],
        initialization=saved["initialization"],
    )

    assert restored.resolved_dict() == saved
