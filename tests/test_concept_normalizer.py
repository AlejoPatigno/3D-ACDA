import numpy as np

from acda3d.artifacts.concepts import ConceptNormalizer, fit_concept_normalizer


def test_normalizer_parity_provenance_and_roundtrip(tmp_path):
    features = np.array([[0.0, 1.0], [2.0, 1.0], [9.0, 9.0]], dtype=np.float32)
    normalizer = fit_concept_normalizer(features, ["CN", "CN", "AD"], roi_labels=[1, 2], cohorts=["ADNI"] * 3)
    assert np.array_equal(normalizer.mu, np.array([1.0, 1.0], np.float32))
    assert np.array_equal(normalizer.sigma, np.array([1.0, 0.0], np.float32))
    expected = 1.0 / (1.0 + np.exp(-((features - normalizer.mu) / (normalizer.sigma + 1e-6))))
    assert np.allclose(normalizer.transform(features), expected.astype(np.float32))
    assert normalizer.provenance["number_of_fitted_subjects"] == 2
    path = tmp_path / "normalizer.json"
    normalizer.save(path)
    loaded = ConceptNormalizer.load(path)
    assert loaded.roi_labels == [1, 2]
    assert np.array_equal(loaded.transform(features), normalizer.transform(features))
