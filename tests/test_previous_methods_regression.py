from acda3d.adaptation import CORALAdaptationMethod, MMDAdaptationMethod


def test_prior_approved_adaptation_methods_remain_importable():
    assert CORALAdaptationMethod.name == "coral" and MMDAdaptationMethod.name == "mmd"
