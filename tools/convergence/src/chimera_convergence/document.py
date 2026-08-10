"""
Carga una matriz declarada en TOML y la reporta.

TOML y no JSON porque esto lo escribe una persona a mano mientras lee dos
documentos, y porque admite comentarios: la justificación de por qué un eje
está en un cuadrante y no en otro pertenece al lado del eje, no en un anexo.

El formato, entero:

```toml
[tracks]
a = "la simulación (acta X)"
b = "la ratificación real (doc Y)"

[attestations.frozen_decisions_intact]
holds = true
evidence = "grep sobre invariants.md — cero decisiones tocadas"

[attestations.substance_survived]
holds = true
evidence = "stress independiente sobre HEAD final: GO, cero regresión"

[[axis]]
id = "EX-1"
what = "las semillas no llegan a la máquina de estados"
artifact = "engine/src/blite/runtime/run_loop.py"
quadrant = "A"
source_a_evidence = "acta sim §4.2"
source_b_evidence = "corrida propia, run_loop.py:210"
severity = "P0"
fix_available = true
disposition = "portar el fix de la rama de ejercicio"
```
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any, cast

from chimera_convergence.matrix import (
    Attestation,
    Axis,
    MatrixError,
    Quadrant,
    Severity,
    Verdict,
    verdict,
)

_ATTESTATION_KEYS = ("frozen_decisions_intact", "substance_survived")

_CAMPOS_TEXTO = (
    "what",
    "artifact",
    "variant",
    "source_a_evidence",
    "source_b_evidence",
    "disposition",
)


def _tabla(value: Any, donde: str) -> dict[str, Any]:
    """Una entrada del TOML que tiene que ser una tabla, y lo dice si no lo es."""
    if not isinstance(value, dict):
        msg = f"{donde}: se esperaba una tabla, llegó {type(value).__name__}"
        raise MatrixError(msg)
    return cast("dict[str, Any]", value)


def _texto(raw: dict[str, Any], key: str, axis_id: str) -> str:
    value = raw.get(key, "")
    if not isinstance(value, str):
        msg = f"{axis_id}: `{key}` debe ser texto"
        raise MatrixError(msg)
    return value


def _enum[T: (Quadrant, Severity)](
    kind: type[T], raw: str, key: str, axis_id: str
) -> T:
    try:
        return kind(raw)
    except ValueError as exc:
        validos = ", ".join(repr(member.value) for member in kind)
        msg = f"{axis_id}: `{key}` = {raw!r} no es válido (opciones: {validos})"
        raise MatrixError(msg) from exc


def _axis(raw: dict[str, Any]) -> Axis:
    axis_id = raw.get("id", "")
    if not isinstance(axis_id, str) or not axis_id.strip():
        msg = "un eje sin `id` no se puede citar en ningún veredicto"
        raise MatrixError(msg)

    umbrella = raw.get("umbrella")
    if umbrella is not None and not isinstance(umbrella, bool):
        msg = f"{axis_id}: `umbrella` es un juicio sí/no, no {umbrella!r}"
        raise MatrixError(msg)

    fix_available = raw.get("fix_available", False)
    if not isinstance(fix_available, bool):
        msg = f"{axis_id}: `fix_available` debe ser booleano"
        raise MatrixError(msg)

    textos = {key: _texto(raw, key, axis_id) for key in _CAMPOS_TEXTO}
    return Axis(
        id=axis_id,
        quadrant=_enum(Quadrant, _texto(raw, "quadrant", axis_id), "quadrant", axis_id),
        severity=_enum(Severity, _texto(raw, "severity", axis_id), "severity", axis_id),
        umbrella=umbrella,
        fix_available=fix_available,
        **textos,
    )


def _attestation(raw: dict[str, Any] | None, key: str) -> Attestation | None:
    """Ausente ⇒ `None`, que el veredicto trata como «sin declarar».

    Deliberadamente NO se inventa un default optimista: un criterio que nadie
    escribió es un criterio que nadie comprobó.
    """
    if raw is None:
        return None
    holds = raw.get("holds")
    if not isinstance(holds, bool):
        msg = f"attestations.{key}: `holds` debe ser booleano"
        raise MatrixError(msg)
    evidence = raw.get("evidence", "")
    if not isinstance(evidence, str):
        msg = f"attestations.{key}: `evidence` debe ser texto"
        raise MatrixError(msg)
    return Attestation(holds=holds, evidence=evidence)


def load(path: Path) -> tuple[tuple[Axis, ...], dict[str, Attestation | None]]:
    """Lee la matriz. Un archivo mal formado explota; jamás se interpreta a medias."""
    try:
        raw: dict[str, Any] = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        msg = f"{path.name}: TOML inválido — {exc}"
        raise MatrixError(msg) from exc

    ejes_raw: Any = raw.get("axis", [])
    if not isinstance(ejes_raw, list):
        msg = f"{path.name}: `axis` debe ser una lista de tablas `[[axis]]`"
        raise MatrixError(msg)

    axes = tuple(
        _axis(_tabla(entry, "[[axis]]")) for entry in cast("list[Any]", ejes_raw)
    )

    attestations_raw: Any = raw.get("attestations", {})
    if not isinstance(attestations_raw, dict):
        msg = f"{path.name}: `attestations` debe ser una tabla"
        raise MatrixError(msg)
    declaradas = cast("dict[str, Any]", attestations_raw)

    attestations = {
        key: _attestation(
            _tabla(declaradas[key], f"attestations.{key}")
            if key in declaradas
            else None,
            key,
        )
        for key in _ATTESTATION_KEYS
    }
    return axes, attestations


def evaluate(path: Path) -> Verdict:
    axes, attestations = load(path)
    return verdict(
        axes,
        frozen_decisions_intact=attestations["frozen_decisions_intact"],
        substance_survived=attestations["substance_survived"],
    )


def render(result: Verdict) -> str:
    """El reporte, en el orden en que se lee: veredicto, cifras, por qué no."""
    counts = result.counts
    lineas = [
        f"VEREDICTO: {'CONVERGEN' if result.converge else 'DIVERGEN'}",
        "",
        f"  ejes                     {counts.total}",
        f"  (A) convergencia         {counts.by_quadrant['A']}",
        f"  (B) ganancia de B        {counts.by_quadrant['B']}   "
        "← puntos ciegos de la fuente A",
        f"  (C) silencio de B        {counts.by_quadrant['C']}",
        f"  (D) conflicto            {counts.by_quadrant['D']}   "
        f"({counts.unresolved_conflicts} sin resolver)",
        "",
        f"  la fuente B afirmó algo en {counts.asserted_by_b} ejes; "
        f"la fuente A ya lo había cazado en {counts.by_quadrant['A']} "
        f"({counts.convergence_rate:.0%})",
    ]
    if result.reasons:
        lineas += ["", "NO converge porque:"]
        lineas += [f"  · {reason}" for reason in result.reasons]
    return "\n".join(lineas)
