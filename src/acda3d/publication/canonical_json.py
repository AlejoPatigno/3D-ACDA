"""Deterministic canonical JSON for Phase 18 identity payloads.

This module deliberately has no I/O or experiment knowledge. It turns a strict
JSON-compatible value into the exact UTF-8 byte sequence used for identity.
"""

from __future__ import annotations

import dataclasses
import hashlib
import math
import re
import unicodedata
from collections.abc import Mapping
from enum import Enum
from typing import Any

CANONICALIZATION_PROFILE = "phase18.canonical-json.v1"
_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
_NAMED_ESCAPES = {8: r"\b", 9: r"\t", 10: r"\n", 12: r"\f", 13: r"\r"}


def canonical_json_bytes(value: Any) -> bytes:
    """Serialize *value* using ``phase18.canonical-json.v1``.

    The result has no trailing newline. Values outside the JSON identity type
    boundary are rejected instead of being stringified or silently coerced.
    """

    return _serialize(value).encode("utf-8")


def canonical_json(value: Any) -> str:
    """Return the canonical JSON text corresponding to :func:`canonical_json_bytes`."""

    return _serialize(value)


def identity_sha256(value: Any) -> str:
    """Return the SHA-256 digest of the exact canonical identity bytes."""

    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def canonical_sha256(value: Any) -> str:
    """Compatibility spelling for the Phase 18 identity digest helper."""

    return identity_sha256(value)


sha256_identity = identity_sha256


def _serialize(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return _quote(_normalize_string(value, "string"))
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return _serialize_float(value)
    if isinstance(value, Enum):
        return _serialize(value.value)
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return _serialize({field.name: getattr(value, field.name) for field in dataclasses.fields(value)})
    if isinstance(value, Mapping):
        return _serialize_mapping(value)
    if isinstance(value, (list, tuple)):
        return "[" + ",".join(_serialize(item) for item in value) + "]"
    raise TypeError(f"unsupported identity value type: {type(value).__name__}")


def _serialize_mapping(value: Mapping[Any, Any]) -> str:
    normalized: dict[str, Any] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise TypeError("identity mapping keys must be strings")
        normalized_key = _normalize_string(key, "mapping key")
        if normalized_key in normalized:
            raise ValueError(f"normalization collision for mapping key {normalized_key!r}")
        normalized[normalized_key] = item
    members = (
        _quote(key) + ":" + _serialize(normalized[key])
        for key in sorted(normalized)
    )
    return "{" + ",".join(members) + "}"


def _normalize_string(value: str, field: str) -> str:
    if any(0xD800 <= ord(character) <= 0xDFFF for character in value):
        raise ValueError(f"{field} contains an unpaired surrogate")
    return unicodedata.normalize("NFC", value)


def _quote(value: str) -> str:
    pieces = ['"']
    for character in value:
        codepoint = ord(character)
        if character == '"':
            pieces.append(r'\"')
        elif character == "\\":
            pieces.append(r"\\")
        elif codepoint <= 0x1F:
            pieces.append(_NAMED_ESCAPES.get(codepoint, f"\\u{codepoint:04X}"))
        else:
            pieces.append(character)
    pieces.append('"')
    return "".join(pieces)


def _serialize_float(value: float) -> str:
    if not math.isfinite(value):
        raise ValueError("identity numbers must be finite")
    if value == 0.0:
        return "0"

    text = repr(value)
    if "e" not in text and "E" not in text:
        return text[:-2] if text.endswith(".0") else text

    mantissa, exponent = text.lower().split("e")
    exponent_value = int(exponent)
    if value.is_integer():
        return str(int(value))
    if mantissa.endswith(".0"):
        mantissa = mantissa[:-2]
    exponent_text = str(exponent_value)
    return f"{mantissa}e{exponent_text}"


def is_sha256(value: str) -> bool:
    """Return whether *value* is a lowercase hexadecimal SHA-256 digest."""

    return bool(_HASH_RE.fullmatch(value))
