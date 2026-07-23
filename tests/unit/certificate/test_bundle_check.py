"""Checklist de 7 puntos (freeze §7) — adversarial: cada punto debe cazar su
forja. El fixture legítimo da 7/7; cada manipulación debe reprobar SU punto."""

from __future__ import annotations

import base64
import copy
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from blite.certificate.bundle_check import check_bundle

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "scripts" / "example-bundle.json"


@pytest.fixture()
def bundle() -> dict[str, Any]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _failed_points(bundle: dict[str, Any]) -> set[int]:
    return {r.number for r in check_bundle(bundle) if not r.ok}


def _retamper_payload(
    bundle: dict[str, Any], mutate: Callable[[dict[str, Any]], None]
) -> dict[str, Any]:
    """Re-encodea el payload con una mutación SIN re-firmar (forja post-emisión)."""
    tampered = copy.deepcopy(bundle)
    statement = json.loads(base64.b64decode(tampered["envelope"]["payload"]))
    mutate(statement)
    tampered["envelope"]["payload"] = base64.b64encode(
        json.dumps(statement).encode()
    ).decode("ascii")
    return tampered


def test_the_legitimate_bundle_passes_all_seven_points(bundle: dict[str, Any]) -> None:
    assert _failed_points(bundle) == set()


def test_point_1_catches_a_tampered_signature(bundle: dict[str, Any]) -> None:
    sig = bundle["envelope"]["signatures"][0]["sig"]
    raw = bytearray(base64.b64decode(sig))
    raw[0] ^= 0xFF
    bundle["envelope"]["signatures"][0]["sig"] = base64.b64encode(bytes(raw)).decode()
    assert 1 in _failed_points(bundle)


def test_point_2_catches_a_rewritten_stream(bundle: dict[str, Any]) -> None:
    # Reescribir la historia post-emisión: el hash recomputado ya no coincide
    bundle["stream"][1]["payload"]["job_id"] = "j-FORJADO"
    assert 2 in _failed_points(bundle)


def test_point_2_refuses_a_stream_without_terminal(bundle: dict[str, Any]) -> None:
    bundle["stream"] = bundle["stream"][:-1]  # corta el run.completed
    assert 2 in _failed_points(bundle)


def test_point_3_catches_a_swapped_deliverable(bundle: dict[str, Any]) -> None:
    digest = next(iter(bundle["deliverable_contents"]))
    bundle["deliverable_contents"][digest] = base64.b64encode(
        b"otro contenido"
    ).decode()
    assert 3 in _failed_points(bundle)


def test_point_4_catches_an_inflated_titular(bundle: dict[str, Any]) -> None:
    tampered = _retamper_payload(
        bundle, lambda s: s["predicate"].update({"titular_level": "AL4"})
    )
    assert 4 in _failed_points(tampered)


def test_point_5_catches_a_phantom_anchor(bundle: dict[str, Any]) -> None:
    # SF-P0-1: el digest existe pero ningún descriptor del Bundle lo respalda
    bundle["anchor_descriptors"] = []
    assert 5 in _failed_points(bundle)


def test_point_6_catches_a_reworded_claim(bundle: dict[str, Any]) -> None:
    tampered = _retamper_payload(
        bundle,
        lambda s: s["predicate"]["conclusions"][0].update(
            {"canonical_statement": "Un enunciado más ambicioso que el firmado"}
        ),
    )
    assert 6 in _failed_points(tampered)


def test_point_7_catches_a_single_leg_for_a_two_leg_policy(
    bundle: dict[str, Any],
) -> None:
    # La Policy exige 2 patas por independence_group para claim_type: solution
    tampered = _retamper_payload(
        bundle,
        lambda s: s["predicate"].update(
            {"attestations": s["predicate"]["attestations"][:1]}
        ),
    )
    assert 7 in _failed_points(tampered)


def test_point_7_catches_al4_without_proof(bundle: dict[str, Any]) -> None:
    def mutate(s: dict[str, Any]) -> None:
        s["predicate"]["attestations"][0]["level"] = "AL4"
        s["predicate"]["attestations"][0]["predicate"] = {}

    assert 7 in _failed_points(_retamper_payload(bundle, mutate))


def test_point_7_fails_closed_without_the_pinned_policy(bundle: dict[str, Any]) -> None:
    bundle["policy_yaml_b64"] = ""
    assert 7 in _failed_points(bundle)
