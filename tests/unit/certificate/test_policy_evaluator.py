"""Evaluador de Policy COMPLETO en el punto 7 — ítem C15 (censo §8.5-3).

Dos huecos, y el segundo es peor que el primero:

1. **`min_level` no se comprobaba.** Una conclusión AL1 bajo una regla que
   exige AL3 pasaba el punto 7 — el certificado decía «verificado bajo esta
   Policy» sin cumplir el nivel que esa Policy exige.
2. **`MatchCondition.side_effects` se ignoraba** y la regla se elegía con el
   PRIMER `claim_type` que casara. Consecuencia: la regla
   `{side_effects: irreversible-external}` de la Policy —sin `claim_type`, la
   más estricta de todas— era INALCANZABLE, y un claim irreversible se
   evaluaba con la regla `pure`. El caso más peligroso, juzgado por la vara
   más laxa.

La corrección es monotónica (freeze §6, «deny unless proven»): aplican TODAS
las reglas cuyas dimensiones restringidas satisface el claim, y la exigencia
es el MÁXIMO — el orden del YAML deja de decidir.
"""

from __future__ import annotations

import base64
import copy
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml

from blite.certificate.bundle_check import check_bundle

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "scripts" / "example-bundle.json"


@pytest.fixture()
def bundle() -> dict[str, Any]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _failed_points(bundle: dict[str, Any]) -> set[int]:
    return {r.number for r in check_bundle(bundle) if not r.ok}


def _punto_7(bundle: dict[str, Any]) -> tuple[str, ...]:
    return next(r for r in check_bundle(bundle) if r.number == 7).failures


def _con_predicate(
    bundle: dict[str, Any], mutar: Callable[[dict[str, Any]], None]
) -> dict[str, Any]:
    """Muta el payload firmado SIN re-firmar (el punto 1 caerá; a este
    archivo solo le importa el 7)."""
    forjado = copy.deepcopy(bundle)
    statement = json.loads(base64.b64decode(forjado["envelope"]["payload"]))
    mutar(statement)
    forjado["envelope"]["payload"] = base64.b64encode(
        json.dumps(statement).encode()
    ).decode("ascii")
    forjado.pop("attestation_envelopes", None)
    return forjado


def _con_policy(bundle: dict[str, Any], reglas: list[dict[str, Any]]) -> dict[str, Any]:
    """Reemplaza la Policy pinneada por una escrita para el caso. El
    `policy_digest` deja de casar (falla su propia parte del punto 7), así
    que los tests miran el MENSAJE, no el simple ok/fallo."""
    forjado = copy.deepcopy(bundle)
    forjado["policy_yaml_b64"] = base64.b64encode(
        yaml.safe_dump({"policy_id": "test", "version": "0", "rules": reglas}).encode()
    ).decode("ascii")
    forjado.pop("attestation_envelopes", None)
    return forjado


# ── Hueco 1 · min_level ─────────────────────────────────────────────────


def test_una_conclusion_por_debajo_del_nivel_exigido_reprueba(
    bundle: dict[str, Any],
) -> None:
    """EL agujero del censo: AL1 bajo una regla AL3 pasaba."""

    def bajar_nivel(s: dict[str, Any]) -> None:
        s["predicate"]["conclusions"][0].update({"level": "AL1"})

    forjado = _con_predicate(bundle, bajar_nivel)

    assert any("nivel AL1 < AL3" in falla for falla in _punto_7(forjado))


def test_el_nivel_no_se_le_exige_a_una_conclusion_refutada(
    bundle: dict[str, Any],
) -> None:
    """Una refutación tiene AL0 por construcción: exigirle nivel volvería
    toda refutación una falla del certificado, cuando refutar es un veredicto
    de primera clase. El socavamiento del titular ya lo cubre el punto 4."""

    def mutar(s: dict[str, Any]) -> None:
        s["predicate"]["conclusions"][0].update({"verdict": "refuted", "level": "AL0"})
        for att in s["predicate"]["attestations"]:
            att["verdict"] = "fail"

    fallas = _punto_7(_con_predicate(bundle, mutar))

    assert not any("nivel" in falla for falla in fallas)


# ── Hueco 2 · side_effects y la regla inalcanzable ──────────────────────


def test_un_claim_irreversible_se_juzga_con_la_regla_irreversible(
    bundle: dict[str, Any],
) -> None:
    """La regla `{side_effects: irreversible-external}` de la Policy real no
    tiene `claim_type`: con el matcher viejo (primer claim_type que casa) era
    inalcanzable, y un claim irreversible caía bajo la regla `pure`. Acá se
    marca el claim como irreversible en su `claim.emitted` y la exigencia
    sube."""
    # Arrange — mismo claim, ahora declarado irreversible en el stream
    forjado = copy.deepcopy(bundle)
    for event in forjado["stream"]:
        if event["type"] == "claim.emitted":
            event["payload"]["irreversible"] = True
    reglas = [
        {
            "match": {"side_effects": "pure", "claim_type": "solution"},
            "criticality": "C1",
            "min_level": "AL1",
            "on_inconclusive": "mark",
        },
        {
            "match": {"side_effects": "irreversible-external"},
            "criticality": "C3",
            "min_level": "AL4",
            "required_legs": 2,
            "on_inconclusive": "hold_run",
        },
    ]

    # Act / Assert — la exigencia AL4 de la regla estricta se aplica
    fallas = _punto_7(_con_policy(forjado, reglas))
    assert any("nivel AL3 < AL4" in falla for falla in fallas)


def test_la_exigencia_es_el_maximo_de_las_reglas_aplicables(
    bundle: dict[str, Any],
) -> None:
    """Monotónica: dos reglas aplicables ⇒ manda la más estricta, no la
    primera del YAML. Con «la primera que casa», mover una línea del archivo
    cambiaba la exigencia sin que nadie lo notara."""
    reglas = [
        {  # laxa, primera a propósito
            "match": {"claim_type": "solution"},
            "criticality": "C1",
            "min_level": "AL1",
            "required_legs": 1,
            "on_inconclusive": "mark",
        },
        {  # estricta, segunda
            "match": {"side_effects": "pure", "claim_type": "solution"},
            "criticality": "C3",
            "min_level": "AL3",
            "required_legs": 5,
            "on_inconclusive": "mark",
        },
    ]

    fallas = _punto_7(_con_policy(bundle, reglas))

    assert any("< 5 exigidas" in falla for falla in fallas)


def test_un_claim_sin_side_effects_declarados_no_casa_una_regla_que_los_exige(
    bundle: dict[str, Any],
) -> None:
    """Fail-closed: si el stream no declara los efectos del claim, una regla
    que los restringe NO aplica — y si ninguna otra aplica, el bundle falla.
    Evaluar con la regla `pure` «porque es la que hay» es exactamente cómo un
    claim irreversible pasaría por inofensivo."""
    forjado = copy.deepcopy(bundle)
    forjado["stream"] = [e for e in forjado["stream"] if e["type"] != "claim.emitted"]

    assert any("sin regla de Policy" in falla for falla in _punto_7(forjado))


def test_el_bundle_vigente_pasa_el_evaluador_completo(bundle: dict[str, Any]) -> None:
    """La otra mitad de la ceremonia: endurecer no puede tumbar lo que el
    sistema produce hoy."""
    assert _failed_points(bundle) == set()
