import pytest
import torch

from pada3dacb.adaptation import gaussian_rbf_kernel_matrix, mmd_loss
from pada3dacb.exceptions import LossContractError


def test_biased_mmd_matches_direct_kernel_means_and_includes_diagonal():
    source = torch.tensor([[0.0, 1.0], [2.0, 3.0], [1.0, 5.0]])
    target = torch.tensor([[1.0, 0.0], [3.0, 4.0]])
    bandwidths = [0.5, 1.0, 2.0]
    ss = gaussian_rbf_kernel_matrix(source, source, bandwidths)
    tt = gaussian_rbf_kernel_matrix(target, target, bandwidths)
    st = gaussian_rbf_kernel_matrix(source, target, bandwidths)
    expected = ss.mean() + tt.mean() - 2 * st.mean()
    actual = mmd_loss(source, target, bandwidths)
    torch.testing.assert_close(actual, expected)
    assert actual.ndim == 0 and torch.isfinite(actual) and actual > 0
    assert ss.diag().sum() == source.shape[0] and tt.diag().sum() == target.shape[0]


def test_mmd_identical_and_common_translation_behavior():
    source = torch.tensor([[0.0, 1.0], [2.0, 3.0], [1.0, 5.0]])
    target = torch.tensor([[1.0, 0.0], [3.0, 4.0]])
    bandwidths = [1.0, 2.0]
    assert abs(float(mmd_loss(source, source, bandwidths))) < 1e-7
    torch.testing.assert_close(
        mmd_loss(source, target, bandwidths),
        mmd_loss(source + 7, target + 7, bandwidths),
        atol=1e-6,
        rtol=1e-6,
    )


@pytest.mark.parametrize(
    ("source", "target", "bandwidths"),
    [
        (torch.ones(1, 2), torch.ones(2, 2), [1.0]),
        (torch.ones(2, 2), torch.ones(2, 3), [1.0]),
        (torch.ones(2, 2), torch.ones(2, 2), []),
        (torch.ones(2, 2), torch.ones(2, 2), [0.0]),
        (torch.ones(2, 2), torch.ones(2, 2), [float("inf")]),
        (torch.ones(2, 2), torch.ones(2, 2), [1.0, 1.0]),
        (torch.ones(2, 2, 1), torch.ones(2, 2), [1.0]),
        (torch.tensor([[float("nan"), 1.0], [2.0, 3.0]]), torch.ones(2, 2), [1.0]),
    ],
)
def test_mmd_rejects_invalid_contracts(source, target, bandwidths):
    with pytest.raises(LossContractError):
        mmd_loss(source, target, bandwidths)
