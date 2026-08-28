def test_required_imports():
    import acda3d
    import acda3d.config
    import acda3d.paths
    import acda3d.training.experiment_logging
    import acda3d.training.reproducibility

    assert acda3d.__version__
