import numpy as np
import pytest
import SimpleITK as sitk

from pada3dacb.artifacts.jacobians import (
    apply_psi,
    jacobian_determinant_from_displacement,
    normalize_regional_deformation,
)


def test_psi_and_gbar_notebook_parity():
    jacobian = np.array([0.5, 1.0, 2.0], dtype=np.float32)
    assert np.allclose(apply_psi(jacobian), -np.log(np.clip(jacobian, 1e-6, None)))
    raw = np.array([-1.0, 0.0, 2.0], dtype=np.float32)
    expected_z = (raw - raw.mean()) / (raw.std() + 1e-6)
    assert np.allclose(normalize_regional_deformation(raw), 1.0 / (1.0 + np.exp(-expected_z)))


def test_psi_validation_and_identity():
    assert np.array_equal(apply_psi(np.ones((2, 2)), "identity"), np.ones((2, 2), np.float32))
    with pytest.raises(ValueError, match="Unknown"):
        apply_psi(np.ones(1), "other")
    with pytest.raises(ValueError, match="non-finite"):
        apply_psi(np.array([np.nan]))


def test_jacobian_identity_translation_expansion_and_contraction():
    shape = (8, 8, 8)
    identity = sitk.GetImageFromArray(np.zeros((*shape, 3), dtype=np.float64), isVector=True)
    assert np.allclose(jacobian_determinant_from_displacement(identity), 1.0)

    translation_array = np.zeros((*shape, 3), dtype=np.float64)
    translation_array[..., 0] = 2.0
    translation = sitk.GetImageFromArray(translation_array, isVector=True)
    assert np.allclose(jacobian_determinant_from_displacement(translation), 1.0)

    coordinates = np.indices(shape, dtype=np.float64)
    for scale, expected in ((0.1, 1.1**3), (-0.1, 0.9**3)):
        field = np.stack(
            [scale * coordinates[2], scale * coordinates[1], scale * coordinates[0]], axis=-1
        )
        image = sitk.GetImageFromArray(field, isVector=True)
        determinant = jacobian_determinant_from_displacement(image)
        assert np.isfinite(determinant).all()
        assert np.allclose(determinant[2:-2, 2:-2, 2:-2], expected, atol=1e-5)
