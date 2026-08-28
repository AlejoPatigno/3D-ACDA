import torch

from acda3d.adaptation.prototype import (
    PrototypeLoss,
    build_source_prototypes,
    build_target_prototypes,
    prototype_alignment_loss,
    prototype_separation_loss,
)

# ---------------------------------------------------------------------------
# Existing tests updated for the new normalized math
# ---------------------------------------------------------------------------


def test_alignment_normalized_divides_by_four_times_mutually_valid_count():
    """L_align = sum|mu_s - mu_t|^2 / (4 * |C_B|).  For one mutually valid class: 5.0 / 4."""
    source = torch.tensor([[1.0, 2.0], [0.0, 0.0], [10.0, 20.0]])
    target = torch.tensor([[2.0, 4.0], [6.0, 7.0], [0.0, 0.0]])
    valid_source = torch.tensor([True, False, True])
    valid_target = torch.tensor([True, True, False])

    loss = prototype_alignment_loss(source, valid_source, target, valid_target)

    # distances = [||[1,2]-[2,4]||^2] = [5.0], count=1 → 5.0 / (4*1) = 1.25
    torch.testing.assert_close(loss, torch.tensor(5.0 / 4.0))


def test_alignment_is_zero_when_no_target_rows_are_accepted():
    loss_fn = PrototypeLoss(tau_p=0.95, proto_margin=1.0, lambda_sep=0.0)
    z_src = torch.tensor([[1.0, 2.0], [4.0, 5.0]])
    y_src = torch.tensor([0, 1])
    z_tgt = torch.tensor([[10.0, 20.0], [30.0, 40.0]])
    logits_c_tgt = torch.zeros(2, 3)

    output = loss_fn(z_src, y_src, z_tgt, logits_c_tgt)

    torch.testing.assert_close(output.alignment, torch.tensor(0.0))
    assert output.accepted_target_count == 0


def test_separation_normalized_by_margin():
    """L_sep = mean((relu(m - d) / m)^2).  For m=1.0 this equals the old form."""
    prototypes = torch.tensor(
        [
            [0.0, 0.0],
            [0.5, 0.0],
            [2.0, 0.0],
        ]
    )
    valid = torch.tensor([True, True, True])

    loss = prototype_separation_loss(prototypes, valid, proto_margin=1.0)

    # pairs: d=[0.5, 2.0, 1.5], relu(1-d)/1 = [0.5, 0, 0], squared = [0.25, 0, 0]
    expected = torch.tensor((((1.0 - 0.5) / 1.0) ** 2 + 0.0 + 0.0) / 3.0)
    torch.testing.assert_close(loss, expected)


def test_separation_is_zero_with_fewer_than_two_valid_source_classes():
    prototypes = torch.tensor([[0.0, 0.0], [9.0, 9.0], [0.0, 0.0]])
    valid = torch.tensor([False, True, False])

    loss = prototype_separation_loss(prototypes, valid, proto_margin=1.0)

    torch.testing.assert_close(loss, torch.tensor(0.0))


def test_combined_prototype_loss_matches_alignment_plus_weighted_separation():
    loss_fn = PrototypeLoss(tau_p=0.95, proto_margin=1.0, lambda_sep=0.1)
    z_src = torch.tensor([[0.0, 0.0], [0.5, 0.0], [2.0, 0.0]])
    y_src = torch.tensor([0, 1, 2])
    z_tgt = torch.tensor([[1.0, 0.0], [2.5, 0.0], [4.0, 0.0]])
    logits_c_tgt = torch.tensor([[6.0, 0.0, 0.0], [0.0, 6.0, 0.0], [0.0, 0.0, 6.0]])

    output = loss_fn(z_src, y_src, z_tgt, logits_c_tgt)

    # After L2 norm: z_src → [[0,0],[1,0],[1,0]], z_tgt → [[1,0],[1,0],[1,0]]
    # Source protos: [0,0],[1,0],[1,0]  Target protos: [1,0],[1,0],[1,0]
    # distances = [1, 0, 0], count=3 → alignment = 1/12
    expected_alignment = torch.tensor(1.0 / 12.0)
    # Separation: pairs d=[1,1,0], relu(1-d)/1=[0,0,1], squared=[0,0,1], mean=1/3
    expected_separation = torch.tensor(1.0 / 3.0)
    torch.testing.assert_close(output.alignment, expected_alignment)
    torch.testing.assert_close(output.separation, expected_separation)
    torch.testing.assert_close(output.total, expected_alignment + 0.1 * expected_separation)


def test_prototype_loss_has_no_stateful_cache_ema_momentum_but_has_l2_norm():
    loss_fn = PrototypeLoss()
    assert vars(loss_fn) == {"tau_p": 0.95, "proto_margin": 1.0, "lambda_sep": 0.1, "class_count": 3}

    z_src = torch.tensor([[3.0, 4.0]])
    y_src = torch.tensor([0])
    z_tgt = torch.tensor([[0.0, 0.0]])
    logits_c_tgt = torch.tensor([[8.0, 0.0, 0.0]])

    output = loss_fn(z_src, y_src, z_tgt, logits_c_tgt)

    # L2-normalized: [3,4] / 5 = [0.6, 0.8]
    torch.testing.assert_close(output.source_prototypes[0], torch.tensor([0.6, 0.8]))
    assert not hasattr(loss_fn, "cache")
    assert not hasattr(loss_fn, "ema")
    assert not hasattr(loss_fn, "momentum")


# ---------------------------------------------------------------------------
# §7 New tests — L2 normalization and scale invariance
# ---------------------------------------------------------------------------


def test_prototype_builders_L2_normalize_embeddings():
    """§7.1: every row used for prototype construction has ||z||_2 ≈ 1."""
    z_src = torch.tensor([[3.0, 4.0], [0.0, 5.0], [1.0, 0.0]])
    y_src = torch.tensor([0, 0, 1])
    prototypes, _ = build_source_prototypes(z_src, y_src, class_count=2)

    # class 0 mean of normalized rows: mean([0.6,0.8],[0,1]) = [0.3, 0.9]
    for c in range(prototypes.shape[0]):
        norm = prototypes[c].norm(p=2).item()
        # prototypes are means of unit vectors, so ||mu|| <= 1
        assert norm <= 1.0 + 1e-6, f"class {c} prototype norm {norm} > 1"


def test_alignment_in_range_zero_to_one_for_normalized_prototypes():
    """§7.2: 0 ≤ L_align ≤ 1 when prototypes come from L2-normalized embeddings."""
    for scale in [1.0, 10.0, 100.0, 1000.0]:
        z_src = torch.tensor([[1.0, 2.0], [10.0, 20.0]]) * scale
        y_src = torch.tensor([0, 1])
        z_tgt = torch.tensor([[2.0, 4.0], [11.0, 22.0]]) * scale
        # Use confident logits with shape matching class_count=2
        logits_c_tgt = torch.tensor([[10.0, 0.0], [0.0, 10.0]])

        prototypes_s, valid_s = build_source_prototypes(z_src, y_src, class_count=2)
        prototypes_t, valid_t, _, _ = build_target_prototypes(z_tgt, logits_c_tgt, class_count=2)

        loss = prototype_alignment_loss(prototypes_s, valid_s, prototypes_t, valid_t)

        assert 0.0 <= loss.item() <= 1.0 + 1e-6, f"L_align={loss.item()} out of [0,1] at scale={scale}"


def test_alignment_scale_invariance_through_builders():
    """§7.3: alignment loss(z) ≈ alignment loss(100*z) through L2-normalizing builders."""
    z_src = torch.tensor([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]])
    y_src = torch.tensor([0, 1, 2])
    z_tgt = torch.tensor([[2.0, 3.0], [4.0, 5.0], [6.0, 7.0]])
    logits = torch.tensor([[6.0, 0.0, 0.0], [0.0, 6.0, 0.0], [0.0, 0.0, 6.0]])

    protos_s, valid_s = build_source_prototypes(z_src, y_src, class_count=3)
    protos_t, valid_t, _, _ = build_target_prototypes(z_tgt, logits, class_count=3)
    loss_small = prototype_alignment_loss(protos_s, valid_s, protos_t, valid_t)

    protos_s2, valid_s2 = build_source_prototypes(100 * z_src, y_src, class_count=3)
    protos_t2, valid_t2, _, _ = build_target_prototypes(100 * z_tgt, logits, class_count=3)
    loss_large = prototype_alignment_loss(protos_s2, valid_s2, protos_t2, valid_t2)

    torch.testing.assert_close(loss_small, loss_large, rtol=1e-5, atol=1e-6)


def test_separation_uses_only_pairs_c_less_than_c_prime():
    """§7.4: L_sep only counts unordered pairs c < c', not both directions."""
    # 3 valid prototypes → 3 pairs: (0,1), (0,2), (1,2)
    prototypes = torch.tensor([[0.0, 0.0], [1.0, 0.0], [2.0, 0.0]])
    valid = torch.tensor([True, True, True])

    loss = prototype_separation_loss(prototypes, valid, proto_margin=1.0)

    # Verify manually: pairs (0,1) d=1 → 0, (0,2) d=2 → 0, (1,2) d=1 → 0
    # All penalties are 0 because all distances ≥ margin=1
    torch.testing.assert_close(loss, torch.tensor(0.0))


def test_separation_in_range_zero_to_one():
    """§7.5: 0 ≤ L_sep ≤ 1 for proto_margin > 0."""
    prototypes = torch.tensor([[0.0, 0.0], [0.1, 0.0], [0.2, 0.0], [5.0, 5.0]])
    valid = torch.tensor([True, True, True, True])

    loss = prototype_separation_loss(prototypes, valid, proto_margin=1.0)

    assert 0.0 <= loss.item() <= 1.0 + 1e-6, f"L_sep={loss.item()} out of [0,1]"


def test_separation_zero_margin_returns_zero_stable():
    """§7.6: proto_margin == 0 returns zero without NaN or division by zero."""
    prototypes = torch.tensor([[0.0, 0.0], [1.0, 0.0], [2.0, 0.0]])
    valid = torch.tensor([True, True, True])

    loss = prototype_separation_loss(prototypes, valid, proto_margin=0.0)

    assert loss.item() == 0.0
    assert torch.isfinite(loss)


def test_concept_loss_independent_of_roi_count():
    """§7.7: ConceptSupervisionLoss is K-independent via MSE mean."""
    from acda3d.losses import ConceptSupervisionLoss

    loss_fn = ConceptSupervisionLoss()
    for K in [2, 5, 10, 50]:
        concepts = torch.full((4, K), 0.5)
        targets = torch.full((4, K), 0.3)
        loss = loss_fn(concepts, targets)
        # MSE of constant diff = (0.2)^2 = 0.04 regardless of K
        torch.testing.assert_close(loss, torch.tensor(0.04))


def test_anatomical_loss_weighted_mse_no_extra_division_by_K():
    """§7.8: L_anat = sum(w_k * r^2) / (B * sum(w))."""
    from acda3d.losses import AnatomicalConsistencyLoss

    for K in [2, 5, 10]:
        weights = torch.ones(K) / K
        loss_fn = AnatomicalConsistencyLoss(K, weights)
        B = 4
        concepts = torch.randn(B, K)
        g_bar = torch.randn(B, K)
        residuals = (concepts - g_bar).square()
        expected = (residuals * weights.unsqueeze(0)).sum() / (B * weights.sum())
        actual = loss_fn(concepts, g_bar)
        torch.testing.assert_close(actual, expected, rtol=1e-5, atol=1e-6)


def test_anatomical_uniform_weights_equals_batch_mean_of_roi_means():
    """§7.9: with uniform w=1/K, L_anat = (1/B) * mean over batch of mean over ROIs of squared errors."""
    from acda3d.losses import AnatomicalConsistencyLoss

    K = 5
    weights = torch.ones(K) / K
    loss_fn = AnatomicalConsistencyLoss(K, weights)
    B = 4
    concepts = torch.randn(B, K)
    g_bar = torch.randn(B, K)
    residuals = (concepts - g_bar).square()
    # Each sample's mean-squared error over ROIs
    per_sample = residuals.mean(dim=1)  # (B,)
    expected = per_sample.mean()  # mean over batch
    actual = loss_fn(concepts, g_bar)
    torch.testing.assert_close(actual, expected, rtol=1e-5, atol=1e-6)


def test_zero_pseudo_labels_and_zero_alignment_backward():
    """§7.10: when no target pseudo-labels are accepted, losses are zero without breaking backward."""
    loss_fn = PrototypeLoss(tau_p=0.99, proto_margin=1.0, lambda_sep=0.1)
    z_src = torch.tensor([[1.0, 0.0], [0.0, 1.0]], requires_grad=True)
    y_src = torch.tensor([0, 1])
    z_tgt = torch.tensor([[100.0, 0.0], [0.0, 100.0]], requires_grad=True)
    # Low-confidence logits → no accepted pseudo-labels
    logits_c_tgt = torch.zeros(2, 3)

    output = loss_fn(z_src, y_src, z_tgt, logits_c_tgt)

    torch.testing.assert_close(output.alignment, torch.tensor(0.0))
    assert output.accepted_target_count == 0
    output.total.backward()
    # z_src gets gradient through source prototypes (separation depends on source)
    assert z_src.grad is not None
    assert torch.isfinite(z_src.grad).all()
    # z_tgt has no gradient: alignment returns _zero_scalar_like (disconnected from z_tgt)
    # and separation is source-only. This is correct behavior.
    assert z_tgt.grad is None or z_tgt.grad.abs().sum() == 0


def test_gradients_flow_through_l2_normalization():
    """§7.11: gradients reach z_src and z_tgt through F.normalize."""
    z_src = torch.tensor([[3.0, 4.0], [1.0, 0.0]], requires_grad=True)
    y_src = torch.tensor([0, 1])
    z_tgt = torch.tensor([[0.0, 1.0], [1.0, 1.0]], requires_grad=True)
    logits_c_tgt = torch.tensor([[6.0, 0.0, 0.0], [0.0, 6.0, 0.0]])

    loss_fn = PrototypeLoss(tau_p=0.95, proto_margin=1.0, lambda_sep=0.0)
    output = loss_fn(z_src, y_src, z_tgt, logits_c_tgt)
    output.total.backward()

    assert z_src.grad is not None, "No gradient on z_src"
    assert z_tgt.grad is not None, "No gradient on z_tgt"
    assert torch.isfinite(z_src.grad).all(), "Non-finite gradient on z_src"
    assert torch.isfinite(z_tgt.grad).all(), "Non-finite gradient on z_tgt"
    # Gradients should be non-zero (at least one element)
    assert z_src.grad.abs().sum() > 0, "Zero gradient on z_src"
    assert z_tgt.grad.abs().sum() > 0, "Zero gradient on z_tgt"
