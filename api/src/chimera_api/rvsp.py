"""La curva r-vs-p que `GET /runs/{run_id}/rvsp` sirve — V3/M20 (C-9/#125).

Contrato congelado: `docs/specs/endpoints-studio.md` §"GET /runs/{run_id}/rvsp".
Wire snake_case, `baselines` CERRADO a tres claves (C-15: se extiende
coordinado cuando llegue `sa`, jamás con un catchall que dejaría entrar una
serie que ningún chart sabe pintar).

**El wire NO es el artefacto.** El record congelado
(`knowledge/rvsp/<instancia>.json`, `scripts/gen_corpus_rvsp.py`) además
lleva un bloque `metodo` — backend, shots, semillas, origen de los ángulos y
el `circuit_digest` por capa. Eso es la ETIQUETA de la curva y vive en el
artefacto porque la spec congeló el wire y dejó el método al dominio de
ciencia. Servir solo lo congelado es lo que mantiene la costura estable; la
etiqueta sigue siendo auditable en el corpus.

Sin datos ingeridos NO hay curva: la ruta responde 404, jamás una lista
vacía de puntos con cara de "el experimento dio esto".
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from chimera_api.corpus_records import load_corpus_record

# api/src/chimera_api/rvsp.py -> parents[3] es la raíz del repo (mismo
# cómputo que `_REPO_ROOT` en `instance_verifiers`/`runs`).
RVSP_CORPUS_DIR = Path(__file__).parents[3] / "knowledge" / "rvsp"


class RvspBaseline(BaseModel):
    """Un baseline clásico/exacto: su energía y su razón contra el óptimo."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    energy: float
    r: float = Field(ge=0.0, le=1.0)


class RvspBaselines(BaseModel):
    """Las TRES del contrato. `extra="forbid"` es el cierre de C-15: una
    cuarta serie no entra por accidente, entra por checkpoint coordinado."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    cpsat: RvspBaseline
    greedy: RvspBaseline
    gw: RvspBaseline


class RvspPoint(BaseModel):
    """Un punto de la curva: el ⟨C⟩ exacto y el estimador muestral, separados.

    Mantenerlos separados ES la honestidad de la curva: `r_esperado_*` no
    depende del muestreo y `r_muestral_*` sí; colapsarlos en un solo número
    borraría de qué se está hablando. `success_rate` (best-of-samples) es
    secundario a propósito — en instancias chicas trivializa el ratio.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    p: int = Field(gt=0)
    r_esperado_mean: float = Field(ge=0.0, le=1.0)
    r_muestral_mean: float = Field(ge=0.0, le=1.0)
    r_muestral_std: float = Field(ge=0.0)
    r_muestral_min: float = Field(ge=0.0, le=1.0)
    r_muestral_max: float = Field(ge=0.0, le=1.0)
    success_rate: float = Field(ge=0.0, le=1.0)


class RvspResponse(BaseModel):
    """El wire completo de `GET /runs/{run_id}/rvsp`."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    instance: str = Field(min_length=1)
    optimo: float = Field(gt=0.0)
    baselines: RvspBaselines
    points: list[RvspPoint]


def load_rvsp_record(
    instance_id: str, *, directory: Path | None = None
) -> RvspResponse | None:
    """La curva congelada de una instancia, o `None` fail-closed.

    Dos filtros en cadena, y ninguno degrada a dato parcial:
    1. identidad del corpus (`load_corpus_record`) — slug fuera de forma,
       archivo ausente o digest que no cierra ⇒ el record no existe;
    2. forma del wire (`RvspResponse`) — un record cuyo contenido no
       satisface el contrato (r fuera de [0,1], baseline faltante, óptimo no
       positivo) tampoco se sirve: emitir algo que el espejo Zod del Studio
       rechazaría sería romper la costura desde el lado del server.
    """
    record = load_corpus_record(directory or RVSP_CORPUS_DIR, instance_id)
    if record is None:
        return None
    wire: dict[str, Any] = {
        clave: record.get(clave)
        for clave in ("instance", "optimo", "baselines", "points")
    }
    try:
        return RvspResponse.model_validate(wire)
    except ValidationError:
        return None
