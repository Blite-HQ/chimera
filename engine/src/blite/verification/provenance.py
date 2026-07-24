"""
`Provenance` — receta de derivación PROV/`dvc.lock` (costura B↔C). [Fase 1 · Sebas+Dylan]

docs/specs/capability-ingesta.md §Contrato (R2): una instancia derivada carga su
receta como unión discriminada por `kind` —

  - `ExternalSourceProvenance` — el snapshot crudo; el ancla es el snapshot (bytes),
    JAMÁS la URL (dos fetches a la misma URL en instantes distintos son evidencia
    distinta, con digests distintos, y eso es correcto).
  - `DerivationProvenance` — el resultado de una capability de derivación MÁS su
    receta `{inputs, recipe, run_id, assertions}`.

La `Provenance` se canonicaliza con la ÚNICA puerta (`blite.certificate.canonical`)
y se guarda vía `ContentStore.put()` como cualquier `Artifact` — hereda
digest/identidad gratis, sin agregar ningún campo a `Artifact` (freeze §12 intacto).

Reutilizada TAL CUAL por el dominio del informe (docs/specs/informe-derivado.md):
cada figura y el PDF final son instancias `DerivationProvenance` con
`recipe.capability = "blite.report.*"` — cero tipo nuevo para el reporte.

INV-2 (verificación no importa serving): este módulo es datos puros (Pydantic) —
no importa nada de `blite.serving`. La canonicalización se aplica DESDE afuera
(el llamador pasa `model_dump(mode="json")` por `canonicalize`), como en las seeds.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal, TypedDict

from pydantic import BaseModel, ConfigDict, Field


class InputRef(TypedDict):
    """Un insumo pinneado por digest: `{ref, digest}` (capability-ingesta.md §Contrato).

    `ref` nombra el rol del insumo (`"snapshot:…"`, `"template"`, `"figure:<n>"`,
    `"cifra:<n>"`); `digest` lo pinnea. Dict subscriptable a propósito: el contrato
    se lee `provenance.inputs[i]["ref"]` (ver seeds de ingesta e informe).
    """

    ref: str
    digest: str


class DerivationRecipe(TypedDict):
    """La receta reproducible: qué capability, qué versión, digest de sus params y
    el `code_ref` que la fija — todo lo que un verificador independiente necesita
    para RECOMPUTAR la derivación desde los mismos insumos pinneados."""

    capability: str
    version: str
    params_digest: str
    code_ref: str


class DataQualityAssertion(TypedDict):
    """Validación de forma en frontera, DENTRO de la receta (geojson-pydantic/pandera).

    Pase o falle, entra como evidencia: el certificado afirma "esta derivación pasó
    el contrato de forma X", jamás "confía en que pasó" (capability-ingesta.md
    §Validación en frontera). `detail` es libre o `None`."""

    name: str
    passed: bool
    detail: dict[str, Any] | None


class ExternalSourceProvenance(BaseModel):
    """Snapshot crudo de una fuente externa — el ancla es el snapshot (bytes), JAMÁS
    la URL (capability-ingesta.md §Dos instancias)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["external-source"] = "external-source"
    uri: str
    retrieved_at: datetime
    content_type: str | None = None
    http_status: int | None = None


class DerivationProvenance(BaseModel):
    """Instancia derivada + su receta, en vocabulario PROV/`dvc.lock`.

    El PDF/figura del informe hereda TODOS los digests de sus insumos
    (informe-derivado.md §b): `inputs` incluye la plantilla, cada figura y cada
    cifra citada, todos por digest — verificar = recompilar desde esos insumos y
    comparar digests, sin re-confiar en quien lo generó."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["derivation"] = "derivation"
    inputs: tuple[InputRef, ...]
    recipe: DerivationRecipe
    run_id: str
    assertions: tuple[DataQualityAssertion, ...] = ()


Provenance = Annotated[
    ExternalSourceProvenance | DerivationProvenance,
    Field(discriminator="kind"),
]
"""Unión discriminada por `kind` — el tipo que viaja como payload aditivo de
`capability.job.completed {output_digest, provenance_digest}` (freeze §3)."""
