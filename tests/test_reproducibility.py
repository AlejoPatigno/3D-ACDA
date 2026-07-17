import random

import numpy as np
import torch

from pada3dacb.training.reproducibility import (
    collect_reproducibility_metadata,
    make_torch_generator,
    seed_everything,
)


def test_seed_everything_repeats_cpu_randomness():
    seed_everything(123)
    first = (random.random(), np.random.rand(), torch.rand(3))
    seed_everything(123)
    second = (random.random(), np.random.rand(), torch.rand(3))

    assert first[0] == second[0]
    assert first[1] == second[1]
    assert torch.equal(first[2], second[2])


def test_make_torch_generator_is_seeded():
    gen_a = make_torch_generator(7)
    gen_b = make_torch_generator(7)
    assert torch.equal(torch.rand(4, generator=gen_a), torch.rand(4, generator=gen_b))


def test_collect_reproducibility_metadata_has_expected_keys():
    metadata = collect_reproducibility_metadata()
    assert "python_version" in metadata
    assert "torch_version" in metadata
    assert "cuda_available" in metadata
