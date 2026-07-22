"""
canonicalize() — C(x), the RFC 8785 (JCS) subset from the canonicalization
annex (docs/contract-freeze-anexo-canonicalizacion.md).

Every assertion below reproduces a vector from the annex SS6 byte-for-byte —
"los vectores de SS6 son el gate: la impl que no los reproduce byte a byte no
entra." V1-V4 are event vectors (canonicalize() takes plain dict views, the
Event model itself is a later piece of this session); V5 is the numeric/key-
ordering edge-case table.
"""

from __future__ import annotations

import hashlib

import pytest

from blite.certificate.canonical import JSONValue, canonicalize

PROVENANCE_PREFIX = b"blite/provenance/v1\n"

E1: dict[str, JSONValue] = {
    "id": "0198c0de-0000-7000-8000-000000000001",
    "stream_id": "run:8f2c1a9b",
    "seq": 1,
    "type": "run.started",
    "actor_id": "user:dylan",
    "domain_id": "d-default",
    "payload": {},
    "occurred_at": "2026-07-07T12:00:00.000000Z",
}

E2_PAYLOAD: dict[str, JSONValue] = {
    "verdict": "pass",
    "rung": 1,
    "gap": 0.1,
    "óptimo": True,
    "nota": "café ✓",
    "islands": [2, 3],
    "policy_id": "chimera-default@0.1.0",
    "detail": None,
    "cut_size": 5.0,
}

E2: dict[str, JSONValue] = {
    "id": "0198c0de-0000-7000-8000-000000000002",
    "stream_id": "run:8f2c1a9b",
    "seq": 2,
    "type": "verification.completed",
    "actor_id": "service:runtime",
    "domain_id": "d-default",
    "payload": E2_PAYLOAD,
    "occurred_at": "2026-07-07T12:00:01.500000Z",
}

V1_CANONICAL = (
    '{"actor_id":"user:dylan","domain_id":"d-default",'
    '"id":"0198c0de-0000-7000-8000-000000000001",'
    '"occurred_at":"2026-07-07T12:00:00.000000Z","payload":{},'
    '"seq":1,"stream_id":"run:8f2c1a9b","type":"run.started"}'
)

V2_CANONICAL = (
    '{"actor_id":"service:runtime","domain_id":"d-default",'
    '"id":"0198c0de-0000-7000-8000-000000000002",'
    '"occurred_at":"2026-07-07T12:00:01.500000Z",'
    '"payload":{"cut_size":5,"detail":null,"gap":0.1,"islands":[2,3],'
    '"nota":"café ✓","policy_id":"chimera-default@0.1.0","rung":1,'
    '"verdict":"pass","óptimo":true},"seq":2,"stream_id":"run:8f2c1a9b",'
    '"type":"verification.completed"}'
)

V1_SHA256 = "e80b95edd718a533312fc2b4ecdda321681898ea6f10c8460207b1f27a45cbdf"
V2_SHA256 = "456eeed54eb5a23a4cd74d2ec1c8735c0c89429533f30ca096330e0f64b4c0e8"
V3_SHA256 = "049e89fb6abf0936e7cd3cd3e2ca49905202a7e62dc7a1c5325873c882cd6acc"
V4_SHA256 = "1682394a91b2d25f1c41a5a100ea0d897bc43745b11f37783256a181b99ad9e8"


def test_v1_minimal_event_matches_annex_vector() -> None:
    c1 = canonicalize(E1)
    assert c1 == V1_CANONICAL.encode("utf-8")
    assert len(c1) == 206
    assert hashlib.sha256(c1).hexdigest() == V1_SHA256


def test_v2_unicode_null_float_nested_event_matches_annex_vector() -> None:
    c2 = canonicalize(E2)
    assert c2 == V2_CANONICAL.encode("utf-8")
    assert len(c2) == 370
    assert hashlib.sha256(c2).hexdigest() == V2_SHA256


def test_v3_provenance_hash_of_two_event_stream_matches_annex_vector() -> None:
    stream_bytes = (
        PROVENANCE_PREFIX + canonicalize(E1) + b"\n" + canonicalize(E2) + b"\n"
    )
    assert hashlib.sha256(stream_bytes).hexdigest() == V3_SHA256


def test_v4_mutating_one_field_changes_the_provenance_hash() -> None:
    mutated_payload: dict[str, JSONValue] = {**E2_PAYLOAD, "verdict": "fail"}
    e2_mutated: dict[str, JSONValue] = {**E2, "payload": mutated_payload}
    stream_bytes = (
        PROVENANCE_PREFIX + canonicalize(E1) + b"\n" + canonicalize(e2_mutated) + b"\n"
    )
    mutated_hash = hashlib.sha256(stream_bytes).hexdigest()
    assert mutated_hash == V4_SHA256

    original_stream = (
        PROVENANCE_PREFIX + canonicalize(E1) + b"\n" + canonicalize(E2) + b"\n"
    )
    assert mutated_hash != hashlib.sha256(original_stream).hexdigest()


# ── V5: numeric formatting and key-ordering edge cases ─────────────────────


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (2.0, b"2"),
        (0.1, b"0.1"),
        (-0.0, b"0"),
        (1e21, b"1000000000000000000000"),
        (1e-7, b"1e-7"),  # normative ECMAScript; Python repr() gives "1e-07"
    ],
)
def test_numeric_edge_cases_match_annex_vector(value: float, expected: bytes) -> None:
    assert canonicalize(value) == expected


# ── ECMAScript fixed-notation band [1e-6, 1e-4)  [S-F stress · SF-P1-1] ──────
# RFC 8785 (annex SS2 pt5) mandates ECMAScript Number::toString, which uses
# FIXED notation down to exponent -6 (values >= 1e-6). Python's repr() switches
# to exponential at < 1e-4, so a small `se_estimado`/`gap` (~1e-5) would make an
# independent verifier in another language compute a different digest, breaking
# the cross-language parity the annex promises (SS7 / D20). Values below the band
# (<= 1e-7) stay exponential in both — those must NOT change. Ground truth:
# Node.js String(v). Integer-valued floats (1e21) keep the annex's integer form.
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (1e-5, b"0.00001"),
        (1e-6, b"0.000001"),
        (1.5e-5, b"0.000015"),
        (2.5e-6, b"0.0000025"),
        (9.999e-6, b"0.000009999"),
        (1.234e-5, b"0.00001234"),
        (-1e-5, b"-0.00001"),
        (1e-4, b"0.0001"),  # boundary above the band: Python already fixed
        (5e-8, b"5e-8"),  # below the band: exponential in ECMAScript too
        (1e-7, b"1e-7"),  # below the band (frozen V5): must stay exponential
    ],
)
def test_ecmascript_fixed_notation_band(value: float, expected: bytes) -> None:
    assert canonicalize(value) == expected


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_nan_and_infinity_are_rejected(value: float) -> None:
    with pytest.raises(ValueError, match="NaN or Infinity"):
        canonicalize(value)


def test_object_keys_are_ordered_by_utf16_code_units() -> None:
    tricky: dict[str, JSONValue] = {"é": 1, "z": 2, "a": 3, "😀": 4}
    assert canonicalize(tricky) == '{"a":3,"z":2,"é":1,"😀":4}'.encode()
