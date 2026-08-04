"""
Guard del `policy_digest` de la distribución (P9/M14).

`policy_digest` es `sha256` de los BYTES del YAML de la policy
(`blite.certificate.assemble`), y viaja dentro de cada certificado emitido:
es la respuesta a «bajo qué reglas se verificó esto». Un bundle estampado
ayer solo sigue siendo comprobable si esos bytes no se movieron.

El riesgo que este test cubre es de EMPAQUETADO, no de contenido. Al declarar
`distributions/chimera` como paquete instalable (P9), quedó a un paso de
distancia el error de empaquetar también `policies/`: el archivo pasaría a
resolverse desde el site-packages del wheel, con otro final de línea u otra
normalización, y el digest cambiaría **sin que nadie editara una política**.
Los certificados viejos dejarían de casar y la causa sería invisible.

Por eso los digests se pinnean acá. Cambiarlos es legítimo —una política puede
evolucionar— pero exige tocar esta lista a propósito, con la ceremonia que
corresponda; jamás como efecto colateral de un cambio de build.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
_POLICIES = _REPO / "distributions" / "chimera" / "policies"

_DIGESTS_PINNEADOS = {
    "verification-default.yaml": (
        "6d61afa4cb5879d3d1663b0988b5802e7d868b44f8e38cf093efe389c5d60de4"
    ),
    "reto2-statistical.yaml": (
        "39f76d7a2273ad4904489c53bcc130832549496e35db9d9b22b40cdf31094f93"
    ),
    "reto3-simulation.yaml": (
        "b437c00500cc3cef926c777e0488d9483b79bd6637753af8f7d285d1ed5d3ccb"
    ),
}


@pytest.mark.parametrize("nombre", sorted(_DIGESTS_PINNEADOS))
def test_policy_digest_byte_identico(nombre: str) -> None:
    """El digest de cada policy es el pinneado — byte a byte."""
    ruta = _POLICIES / nombre
    assert ruta.is_file(), f"la policy {nombre} desapareció de la distribución"

    digest = hashlib.sha256(ruta.read_bytes()).hexdigest()

    assert digest == _DIGESTS_PINNEADOS[nombre], (
        f"{nombre} cambió de digest ({digest}). Si fue a propósito, actualizá el "
        "pin acá con la ceremonia correspondiente; si no lo tocaste, revisá el "
        "empaquetado: una policy servida desde el wheel en vez del árbol rompe "
        "todo certificado ya emitido."
    )


def test_la_distribucion_no_empaqueta_las_policies() -> None:
    """Las policies son DATOS montados, no contenido del wheel.

    Empaquetarlas les cambiaría la ruta de resolución y, con ella, el riesgo
    del test de arriba. El `pyproject.toml` de la distribución lo declara; este
    test lo vuelve ejecutable."""
    pyproject = (_REPO / "distributions" / "chimera" / "pyproject.toml").read_text(
        encoding="utf-8"
    )

    assert "bypass-selection = true" in pyproject, (
        "la distribución dejó de ser un paquete sin código — si ahora empaqueta "
        "archivos, verificá que `policies/` NO esté entre ellos"
    )
