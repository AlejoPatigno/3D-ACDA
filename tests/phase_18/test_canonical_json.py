from __future__ import annotations

import math

import pytest

from pada3dacb.publication.canonical_json import (
    CANONICALIZATION_PROFILE,
    canonical_json_bytes,
    identity_sha256,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ({"b": 1, "a": 2}, b'{"a":2,"b":1}'),
        ({"x": -0.0}, b'{"x":0}'),
        ({"x": "e\u0301"}, '{"x":"é"}'.encode()),
        ({"x": "é"}, '{"x":"é"}'.encode()),
        ([1, 2, 3], b"[1,2,3]"),
        ({"x": 1e6}, b'{"x":1000000}'),
        ({"x": 1.25, "y": 2}, b'{"x":1.25,"y":2}'),
        ({"bool": True, "null": None}, b'{"bool":true,"null":null}'),
    ],
)
def test_normative_conformance_vectors(value: object, expected: bytes) -> None:
    assert canonical_json_bytes(value) == expected


def test_nested_mapping_and_list_order_are_canonical() -> None:
    value = {"z": [{"b": "two", "a": "one"}, 3], "a": {"d": 4, "c": 5}}
    assert canonical_json_bytes(value) == b'{"a":{"c":5,"d":4},"z":[{"a":"one","b":"two"},3]}'


def test_unicode_keys_are_nfc_normalized_and_collisions_rejected() -> None:
    assert canonical_json_bytes({"e\u0301": "value"}) == '{"é":"value"}'.encode()
    with pytest.raises(ValueError, match="normalization collision"):
        canonical_json_bytes({"é": 1, "e\u0301": 2})


def test_controls_are_escaped_with_uppercase_hex_and_unicode_is_utf8() -> None:
    assert canonical_json_bytes({"x": "\x00\x01\x1a\n\t\\\"é"}) == (
        b'{"x":"\\u0000\\u0001\\u001A\\n\\t\\\\\\\"'
        + "é".encode()
        + b'"}'
    )


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_non_finite_numbers_are_rejected(value: float) -> None:
    with pytest.raises(ValueError, match="finite"):
        canonical_json_bytes({"value": value})


def test_identity_hash_is_sha256_of_exact_canonical_bytes() -> None:
    payload = {"b": [True, None], "a": "value"}
    # The assertion below derives the digest from the public byte contract.
    import hashlib

    assert identity_sha256(payload) == hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
    assert CANONICALIZATION_PROFILE == "phase18.canonical-json.v1"


def test_float_exponents_are_short_and_have_no_plus_or_leading_zero() -> None:
    assert canonical_json_bytes({"small": 1e-7, "negative": -1.25e-7}) == (
        b'{"negative":-1.25e-7,"small":1e-7}'
    )


def test_unsupported_identity_values_and_surrogates_are_rejected() -> None:
    from datetime import datetime

    with pytest.raises(TypeError, match="unsupported"):
        canonical_json_bytes({"value": {1, 2}})
    with pytest.raises(TypeError, match="unsupported"):
        canonical_json_bytes(datetime(2024, 1, 1))
    with pytest.raises(TypeError, match="keys must be strings"):
        canonical_json_bytes({1: "not a JSON object key"})
    with pytest.raises(ValueError, match="surrogate"):
        canonical_json_bytes("bad\ud800")


def test_reserializing_unchanged_value_is_byte_identical() -> None:
    value = {"nested": [1, {"é": "e\u0301"}], "zero": -0.0}
    first = canonical_json_bytes(value)
    second = canonical_json_bytes(value)
    assert first == second
    assert first.endswith(b"}") and not first.endswith(b"\n")
