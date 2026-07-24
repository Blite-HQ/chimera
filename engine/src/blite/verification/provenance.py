"""
`Provenance` — unión discriminada de la instancia derivada. [S-G · Sebas+Dylan]

docs/specs/capability-ingesta.md §Contrato: cero maquinaria de confianza
nueva (R2) — esta `Provenance` NO reemplaza `Artifact`/`ContentStore`
(freeze §12, `blite.content`), los complementa. La "instancia" completa que
viaja por `capability.job.completed{output_digest, provenance_digest}` es el
par `{artifact: Artifact, provenance_digest: str}`: la `Provenance` misma se
canonicaliza con `blite.certificate.canonical.canonicalize` (la ÚNICA puerta,
freeze-anexo §2) y se guarda ELLA MISMA vía `ContentStore.put()` como
cualquier otro `Artifact` — CERO campo nuevo en `Artifact`.

Dos ramas, discriminadas por `kind`:
- `ExternalSourceProvenance` — el snapshot crudo llegó de una fuente externa
  (p. ej. un FeatureServer). El ANCLA es el blob, JAMÁS la uri: dos fetches a
  la misma uri en instantes distintos son evidencia distinta (digests
  distintos), y eso es correcto, no un bug.
- `DerivationProvenance` — el resultado de una capability de derivación MÁS
  su receta en vocabulario PROV/`dvc.lock` (`inputs`/`recipe`/`run_id`/
  `assertions`).

`inputs`/`recipe`/`assertions` quedan `dict`/`tuple[dict, ...]` GENÉRICOS a
propósito — NO sub-modelos Pydantic anidados. El contrato del seed
(`tests/seeds/test_seed_ingesta_receta.py`) los indexa por clave
(`provenance.recipe["capability"]`, `provenance.assertions[0]["passed"]`); un
sub-modelo anidado no sería subscriptable ahí. `DataQualityAssertion` vive
aparte como la forma VALIDADA que un `recipe.capability` concreto usa para
construir cada entrada de `assertions` antes de volcarla a dict plano
(`.model_dump(mode="json")`) — mismo espíritu que el facet
`dataQualityAssertions` de OpenLineage citado en R2: el certificado puede
afirmar "esta derivación pasó el contrato de forma X", nunca "confía en que
pasó".

ADR-008: este módulo vive en `blite.verification` — las capabilities
(`blite_cap_*`) NUNCA lo importan (frontera de import-linter); construyen
dicts con esta MISMA forma sin acoplarse al tipo. La validación de shape que
hacen los `field_validator` de abajo es defensiva (falla temprano si alguien
arma una `Provenance` a mano con una receta incompleta), no re-implementa
nada del gate de canonicalización.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, field_validator

_RECIPE_REQUIRED_KEYS = frozenset(
    {"capability", "version", "params_digest", "code_ref"}
)


class ExternalSourceProvenance(BaseModel):
    """Snapshot crudo desde una fuente externa — el ancla es el blob, NUNCA
    la uri (docs/specs/capability-ingesta.md §Contrato, punto 1)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["external-source"] = "external-source"
    uri: str
    retrieved_at: datetime
    content_type: str | None = None
    http_status: int | None = None


class DataQualityAssertion(BaseModel):
    """Forma validada de una entrada de `DerivationProvenance.assertions` —
    el `recipe.capability` la construye y la vuelca a dict plano. NO es el
    tipo del campo `assertions` (ver docstring del módulo): es la fábrica que
    un implementador de receta usa para no inventar la forma a mano."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    passed: bool
    detail: dict[str, Any] | None = None


class DerivationProvenance(BaseModel):
    """Instancia derivada + su receta, vocabulario PROV/`dvc.lock`
    (docs/specs/capability-ingesta.md §Contrato, punto 2)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["derivation"] = "derivation"
    inputs: tuple[dict[str, Any], ...]
    recipe: dict[str, Any]
    run_id: str
    assertions: tuple[dict[str, Any], ...]

    @field_validator("inputs")
    @classmethod
    def _inputs_carry_ref_and_digest(
        cls, value: tuple[dict[str, Any], ...]
    ) -> tuple[dict[str, Any], ...]:
        for item in value:
            if "ref" not in item or "digest" not in item:
                msg = f"DerivationProvenance.inputs: entrada sin 'ref'/'digest' — {item!r}"
                raise ValueError(msg)
        return value

    @field_validator("recipe")
    @classmethod
    def _recipe_has_required_keys(cls, value: dict[str, Any]) -> dict[str, Any]:
        missing = _RECIPE_REQUIRED_KEYS - value.keys()
        if missing:
            msg = f"DerivationProvenance.recipe: faltan llaves {sorted(missing)}"
            raise ValueError(msg)
        return value

    @field_validator("assertions")
    @classmethod
    def _assertions_carry_name_and_passed(
        cls, value: tuple[dict[str, Any], ...]
    ) -> tuple[dict[str, Any], ...]:
        for item in value:
            if "name" not in item or "passed" not in item:
                msg = (
                    "DerivationProvenance.assertions: entrada sin 'name'/'passed' "
                    f"— {item!r}"
                )
                raise ValueError(msg)
        return value


Provenance = Annotated[
    ExternalSourceProvenance | DerivationProvenance,
    Field(discriminator="kind"),
]
"""Unión discriminada por `kind` — freeze §12 no gana un campo nuevo en
`Artifact`; esta unión vive SIEMPRE al lado, nunca dentro."""

_PROVENANCE_ADAPTER: TypeAdapter[ExternalSourceProvenance | DerivationProvenance] = (
    TypeAdapter(Provenance)
)


def parse_provenance(
    data: dict[str, Any],
) -> ExternalSourceProvenance | DerivationProvenance:
    """Reconstruye la rama correcta desde un dict plano (p. ej. el payload que
    una capability de ingesta devuelve) — fail-loud si `kind` no matchea
    ninguna rama o faltan campos."""
    return _PROVENANCE_ADAPTER.validate_python(data)
