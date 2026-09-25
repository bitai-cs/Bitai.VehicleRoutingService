import re

import pytest

from vehicle_routing_web.domain.exceptions import InvalidPayloadError
from vehicle_routing_web.domain.payload_hash import compute_payload_hash, parse_payload


def _hash(raw: bytes) -> str:
    return compute_payload_hash(parse_payload(raw))


def test_hash_is_sha256_hex():
    assert re.fullmatch(r"[0-9a-f]{64}", _hash(b'{"a": 1}'))


def test_hash_ignores_key_order_and_whitespace():
    assert _hash(b'{"a": 1, "b": {"x": [1, 2], "y": "z"}}') == _hash(b'{"b":{"y":"z","x":[1,2]},\n"a":1}')


def test_hash_ignores_utf8_bom():
    assert _hash(b'{"a": 1}') == _hash(b'\xef\xbb\xbf{"a": 1}')


def test_hash_differs_for_different_content():
    assert _hash(b'{"a": 1}') != _hash(b'{"a": 2}')


def test_hash_is_sensitive_to_array_order():
    assert _hash(b'{"a": [1, 2]}') != _hash(b'{"a": [2, 1]}')


def test_hash_handles_non_ascii_deterministically():
    assert _hash('{"label": "Café"}'.encode()) == _hash(b'{"label": "Caf\\u00e9"}')


@pytest.mark.parametrize(
    "raw",
    [b"", b"not json", b"[1, 2]", b'"text"', b"42", b"null", b'{"a": NaN}', b'{"a": Infinity}', b"\xff\xfe\x00"],
)
def test_parse_rejects_non_object_or_invalid_json(raw):
    with pytest.raises(InvalidPayloadError):
        parse_payload(raw)


def test_parse_rejects_deeply_nested_input():
    with pytest.raises(InvalidPayloadError):
        parse_payload(b'{"a":' + b"[" * 100_000 + b"]" * 100_000 + b"}")
