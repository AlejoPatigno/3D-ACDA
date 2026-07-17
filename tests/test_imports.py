def test_required_imports():
    import pada3dacb
    import pada3dacb.config
    import pada3dacb.paths
    import pada3dacb.training.experiment_logging
    import pada3dacb.training.reproducibility

    assert pada3dacb.__version__
