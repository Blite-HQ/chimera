"""Análisis del SET de políticas — ítem C13 (trust/13, forma de Cedar
Analysis sin su motor).

`policy_diff.py` compara TEXTO y dice qué líneas cambiaron. La pregunta que
importa al tocar una política de verificación es otra: *¿algún caso quedó con
menos exigencia?* — y se puede aflojar un caso agregando una regla, AMPLIANDO
el `match` de otra o reordenando. Un diff de texto muestra las tres como
«+3 -1».

Estos tests fijan las tres formas de relajar que el análisis tiene que cazar,
incluida la más silenciosa: ampliar una regla laxa para que cubra un caso que
antes caía bajo una estricta.
"""

from __future__ import annotations

import yaml

from blite.certificate.policy_analysis import analizar_relajaciones

ESTRICTA = yaml.safe_dump(
    {
        "policy_id": "p",
        "version": "1",
        "rules": [
            {
                "match": {"claim_type": "solution", "side_effects": "pure"},
                "criticality": "C3",
                "min_level": "AL3",
                "required_legs": 2,
                "required_anchors": ["solver", "execution"],
                "on_inconclusive": "mark",
            }
        ],
    }
).encode()


def _con_regla(**cambios: object) -> bytes:
    base = {
        "match": {"claim_type": "solution", "side_effects": "pure"},
        "criticality": "C3",
        "min_level": "AL3",
        "required_legs": 2,
        "required_anchors": ["solver", "execution"],
        "on_inconclusive": "mark",
    }
    return yaml.safe_dump(
        {"policy_id": "p", "version": "2", "rules": [{**base, **cambios}]}
    ).encode()


def test_una_politica_identica_no_relaja_nada() -> None:
    assert analizar_relajaciones(ESTRICTA, ESTRICTA) == ()


def test_endurecer_no_se_reporta_como_relajacion() -> None:
    """El análisis busca lo que AFLOJA; subir la exigencia es lo que se
    espera de un cambio y no debe generar ruido."""
    mas_estricta = _con_regla(min_level="AL4", required_legs=3)

    assert analizar_relajaciones(ESTRICTA, mas_estricta) == ()


def test_bajar_el_nivel_se_caza() -> None:
    hallazgos = analizar_relajaciones(ESTRICTA, _con_regla(min_level="AL2"))

    assert len(hallazgos) == 1
    assert "min_level baja de AL3 a AL2" in hallazgos[0].motivo


def test_quitar_una_pata_se_caza() -> None:
    hallazgos = analizar_relajaciones(ESTRICTA, _con_regla(required_legs=1))

    assert any("patas exigidas bajan de 2 a 1" in h.motivo for h in hallazgos)


def test_quitar_un_ancla_requerida_se_caza() -> None:
    hallazgos = analizar_relajaciones(ESTRICTA, _con_regla(required_anchors=["solver"]))

    assert any("deja de exigir anclas ['execution']" in h.motivo for h in hallazgos)


def test_perder_la_cobertura_de_un_caso_es_la_relajacion_mas_grande() -> None:
    """Si la política nueva no cubre un caso que la vieja sí cubría, ese caso
    pasa de tener exigencia a no tener ninguna — y el punto 7 lo reprobaría
    por fail-closed, que es correcto pero se descubre tarde."""
    sin_regla = yaml.safe_dump({"policy_id": "p", "version": "2", "rules": []}).encode()

    hallazgos = analizar_relajaciones(ESTRICTA, sin_regla)

    assert any("no cubre este caso" in h.motivo for h in hallazgos)


def test_ampliar_una_regla_laxa_para_tapar_una_estricta_se_caza() -> None:
    """LA forma silenciosa: no se toca la regla estricta ni se baja ningún
    número. Se AGREGA una regla laxa... que no relaja nada, porque la
    exigencia es el máximo. Lo que sí relaja es QUITAR la restricción de
    `match` de la estricta y dejar solo la laxa cubriendo el caso — un diff
    de texto muestra «una línea de match cambiada»."""
    # Arrange — la estricta deja de aplicar a `pure` (ahora solo a otro tipo)
    reemplazo = yaml.safe_dump(
        {
            "policy_id": "p",
            "version": "2",
            "rules": [
                {
                    "match": {"claim_type": "otro", "side_effects": "pure"},
                    "criticality": "C3",
                    "min_level": "AL3",
                    "required_legs": 2,
                    "required_anchors": ["solver", "execution"],
                    "on_inconclusive": "mark",
                },
                {
                    "match": {"claim_type": "solution"},
                    "criticality": "C1",
                    "min_level": "AL1",
                    "required_legs": 1,
                    "on_inconclusive": "mark",
                },
            ],
        }
    ).encode()

    # Act
    hallazgos = analizar_relajaciones(ESTRICTA, reemplazo)

    # Assert — el caso (solution, pure) quedó bajo la regla laxa
    caso = next(
        h for h in hallazgos if h.claim_type == "solution" and h.side_effects == "pure"
    )
    assert "min_level baja de AL3 a AL1" in caso.motivo
    assert "patas exigidas bajan de 2 a 1" in caso.motivo


def test_la_politica_de_la_distribucion_no_relajo_contra_si_misma() -> None:
    """Autocomprobación sobre el artefacto real que se distribuye."""
    from pathlib import Path  # noqa: PLC0415

    politica = (
        Path(__file__).resolve().parents[3]
        / "distributions"
        / "chimera"
        / "policies"
        / "verification-default.yaml"
    ).read_bytes()

    assert analizar_relajaciones(politica, politica) == ()
