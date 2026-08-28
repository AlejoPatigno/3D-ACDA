import torch

from acda3d.adaptation import (
    gaussian_rbf_kernel_matrix,
    pairwise_squared_distances,
)


def test_pairwise_distances_match_direct_reference_and_support_unequal_counts():
    x = torch.tensor([[1.0, 2.0], [3.0, 5.0], [2.0, 4.0]], dtype=torch.float64)
    y = torch.tensor([[2.0, 1.0], [4.0, 7.0]])
    expected = (x.float()[:, None, :] - y.float()[None, :, :]).square().sum(-1)
    actual = pairwise_squared_distances(x, y)
    torch.testing.assert_close(actual, expected)
    assert actual.shape == (3, 2) and actual.dtype == torch.float32
    self_distances = pairwise_squared_distances(x, x)
    torch.testing.assert_close(self_distances, self_distances.T)
    torch.testing.assert_close(self_distances.diag(), torch.zeros(3))
    assert (actual >= 0).all()


def test_gaussian_mixture_is_exact_mean_and_order_invariant():
    x = torch.tensor([[0.0, 1.0], [2.0, 3.0], [1.0, 4.0]])
    bandwidths = [0.5, 1.0, 2.0]
    distances = (x[:, None, :] - x[None, :, :]).square().sum(-1)
    expected = torch.stack(
        [torch.exp(-distances / (2 * sigma**2)) for sigma in bandwidths]
    ).mean(0)
    actual = gaussian_rbf_kernel_matrix(x, x, bandwidths)
    torch.testing.assert_close(actual, expected)
    torch.testing.assert_close(actual, gaussian_rbf_kernel_matrix(x, x, bandwidths[::-1]))
    torch.testing.assert_close(actual.diag(), torch.ones(3))
    assert torch.isfinite(actual).all() and (actual > 0).all() and (actual <= 1).all()
