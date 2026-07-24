"""
Evidencia externa importada — capas 2/3 de la receta de custodia. [S-G · Sebas]

`docs/specs/evidencia-externa.md` §Contrato: la capa 1 (blob crudo) reutiliza
`ExternalSourceProvenance` TAL CUAL (capability-ingesta.md, cero tipo nuevo —
vive en `blite.verification.provenance`, no en este módulo). Este módulo
aporta las dos capas propias de evidencia de terceros:

- `NormalizedCounts` — capa 2, el esquema PROPIO de counts (NO se re-expone
  `BackendResult.to_dict()` de pytket tal cual: acoplaría el contrato a una
  librería externa que cambia forma entre versiones). `bit_order` es campo
  OBLIGATORIO, SIN default implícito — el footgun que mata
  (`knowledge/quantum/08` §1.5): Qiskit es little-endian (q0 a la derecha),
  pytket default es ILO-BE (q[0] a la izquierda, MSB); sin `bit_order`
  explícito, dos implementaciones honestas decodifican el MISMO conteo
  distinto.
- `ExternalImportStatement` — capa 3, in-toto Statement v1 / predicado SLSA
  PROPIO (`https://blite.dev/ExternalImport/v1`). Certifica LA IMPORTACIÓN
  (custodia: "esto vino de Nexus, en este momento, con estos parámetros"),
  JAMÁS sustituye la `Attestation` clase `consensus_replication`
  (`blite.verification.evidence.ConsensusReplicationPredicate`) que usa
  estos counts como UNA pata de consenso multi-backend — son dos
  afirmaciones distintas sobre el mismo dato (spec §Ortogonalidad).
- `normalize_counts` — el conversor PLANO exigido por la spec: parseo
  EXPLÍCITO campo a campo de un dict crudo de corrida (`runs/nexus/*.json`
  del espejo). `bit_order`/`noisy_simulation`/`error_params` los decide el
  CALLER (determinación empírica contra el corpus de islanding —
  `scripts/import_nexus_runs.py`); esta función NUNCA adivina.

Seguridad dura — NO NEGOCIABLE (spec §Seguridad dura): JAMÁS deserializar
JSON externo con el decoder con estado de Qiskit que reconstruye objetos
arbitrarios desde `__type__`/`__value__` (CVE GHSA-x4x5-jv3x-9c7m,
ejecución de código arbitrario sobre JSON no confiable). La AUSENCIA de ese
deserializador en este módulo ES el contrato
(`tests/seeds/test_seed_evidencia_importacion.py::
test_import_statement_never_deserializes_with_qiskit_runtime_decoder` hace
`grep` de su nombre sobre `inspect.getsource(external_evidence)`) — por eso
ese nombre NUNCA se escribe en este archivo, tampoco en la prosa de este
docstring; todo conversor de la capa 2 es PLANO (`json.loads` estándar +
parseo explícito campo a campo, `normalize_counts` abajo).

`inputs`/`recipe`/`assertions` de la `DerivationProvenance` que envuelve
`NormalizedCounts` se importan de `blite.verification.provenance`
(capability-ingesta.md) — este módulo NO reintroduce el par
`Provenance`/`ContentStore`.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, cast

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

BitOrder = Literal["msb-left", "msb-right"]
"""`msb-left`: el bit MÁS a la izquierda de la clave es el qubit 0 (MSB) —
default pytket ILO-BE. `msb-right`: el bit más a la izquierda es el LSB —
lectura estilo Qiskit (little-endian, equivalente a `BasisOrder.dlo` en
pytket). Sin default: cargar este campo a mano SIEMPRE, nunca inferirlo
implícitamente (`knowledge/quantum/08` §1.5)."""

_SHA256_PREFIX = "sha256:"


def _strip_sha256_prefix(value: str) -> str:
    """`"sha256:" + hex` -> `hex` — el subject/digest de in-toto porta el
    hex crudo bajo la llave `sha256`, el prefijo es convención interna
    nuestra (mismo patrón que el resto del repo, p. ej. los tests de
    `provenance.py`)."""
    if value.startswith(_SHA256_PREFIX):
        return value[len(_SHA256_PREFIX) :]
    return value


class NormalizedCounts(BaseModel):
    """Capa 2 — `docs/specs/evidencia-externa.md` §Capa 2. Instancia derivada
    de `BackendResult.to_dict()` (pytket) a través de `normalize_counts()`;
    el resultado (canonicalizado con `C(x)`, la ÚNICA puerta —
    `blite.certificate.canonical.canonicalize`) es lo que
    `ContentStore.put()` guarda como `Artifact`."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    counts: dict[str, int]
    bit_order: BitOrder
    backend: str
    noisy_simulation: bool
    error_params: dict[str, Any] | None = None

    @model_validator(mode="after")
    def _error_params_none_when_not_noisy(self) -> NormalizedCounts:
        # spec §Capa 2: "error_params: ... None si noisy_simulation=false" —
        # honestidad documentada, no se inventan parámetros de ruido para una
        # corrida ideal.
        if not self.noisy_simulation and self.error_params is not None:
            msg = (
                "NormalizedCounts.error_params debe ser None cuando "
                "noisy_simulation=False (docs/specs/evidencia-externa.md §Capa 2)"
            )
            raise ValueError(msg)
        return self


_EXTERNAL_PARAMETERS_REQUIRED_KEYS = frozenset({"circuit_digest", "shots_requested"})
_DEPENDENCY_REQUIRED_KEYS = frozenset({"name", "digest"})


class ExternalImportStatement(BaseModel):
    """Capa 3 — `docs/specs/evidencia-externa.md` §Capa 3. in-toto Statement
    v1 / predicado SLSA propio (`predicateType`
    `https://blite.dev/ExternalImport/v1`). `resolved_dependencies` porta
    `transpiled_circuit_digest`/`noise_config_digest` — YA congelados del
    lado del claim proponente (freeze §11), reutilizados aquí sin campo
    nuevo. `inputs`/`resolved_dependencies` quedan `tuple[dict, ...]`
    GENÉRICOS a propósito — mismo espíritu que
    `DerivationProvenance.inputs`/`.assertions` (`provenance.py`): el
    contrato del seed los indexa por clave
    (`statement.resolved_dependencies[0]["name"]`), un sub-modelo anidado no
    sería subscriptable ahí."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    subject_name: str
    subject_digest: str
    external_parameters: dict[str, Any]
    resolved_dependencies: tuple[dict[str, Any], ...]
    builder_id: str
    invocation_id: str
    started_on: datetime | None = None
    finished_on: datetime | None = None

    @field_validator("external_parameters")
    @classmethod
    def _external_parameters_has_required_keys(
        cls, value: dict[str, Any]
    ) -> dict[str, Any]:
        missing = _EXTERNAL_PARAMETERS_REQUIRED_KEYS - value.keys()
        if missing:
            msg = (
                "ExternalImportStatement.external_parameters: faltan llaves "
                f"{sorted(missing)}"
            )
            raise ValueError(msg)
        return value

    @field_validator("resolved_dependencies")
    @classmethod
    def _dependencies_carry_name_and_digest(
        cls, value: tuple[dict[str, Any], ...]
    ) -> tuple[dict[str, Any], ...]:
        for item in value:
            missing = _DEPENDENCY_REQUIRED_KEYS - item.keys()
            if missing:
                msg = (
                    "ExternalImportStatement.resolved_dependencies: entrada "
                    f"sin {sorted(missing)} — {item!r}"
                )
                raise ValueError(msg)
            digest = item["digest"]
            if not isinstance(digest, dict) or "sha256" not in digest:
                msg = (
                    "ExternalImportStatement.resolved_dependencies: "
                    f"'digest' sin llave 'sha256' — {item!r}"
                )
                raise ValueError(msg)
        return value

    def to_intoto(self) -> dict[str, Any]:
        """Renderiza el dict in-toto Statement v1 (spec §Capa 3) — la forma
        que se canonicaliza con `C(x)` y se guarda vía `ContentStore.put()`;
        su digest entra a `deliverables[{artifact_ref:
        "external-import:<job_id>", digest}]` del certificado (freeze §7,
        T6/#64a) — CERO firma DSSE individual en Fase 1."""
        metadata: dict[str, Any] = {}
        if self.started_on is not None:
            metadata["startedOn"] = self.started_on.isoformat()
        if self.finished_on is not None:
            metadata["finishedOn"] = self.finished_on.isoformat()
        return {
            "_type": "https://in-toto.io/Statement/v1",
            "subject": [
                {
                    "name": self.subject_name,
                    "digest": {"sha256": _strip_sha256_prefix(self.subject_digest)},
                }
            ],
            "predicateType": "https://blite.dev/ExternalImport/v1",
            "predicate": {
                "externalParameters": self.external_parameters,
                "resolvedDependencies": [
                    dict(dep) for dep in self.resolved_dependencies
                ],
                "builder": {"id": self.builder_id},
                "invocationId": self.invocation_id,
                "metadata": metadata,
            },
        }


_NEXUS_RUN_REQUIRED_KEYS = frozenset({"counts", "device"})


def normalize_counts(
    run: dict[str, Any],
    *,
    bit_order: BitOrder,
    noisy_simulation: bool,
    error_params: dict[str, Any] | None = None,
) -> NormalizedCounts:
    """Conversor PLANO capa 1 -> capa 2
    (`blite.evidencia.nexus.normalize_counts`, spec §Capa 2): parseo
    EXPLÍCITO campo a campo de un dict crudo de corrida Nexus
    (`runs/nexus/*.json` del espejo, ya un dict de Python — nunca se
    deserializa aquí, el caller ya hizo `json.loads` plano antes de
    llamar). `bit_order`/`noisy_simulation`/`error_params` son decisiones
    del CALLER (determinación empírica contra el corpus, no adivinadas
    aquí — `scripts/import_nexus_runs.py`)."""
    missing = _NEXUS_RUN_REQUIRED_KEYS - run.keys()
    if missing:
        msg = f"normalize_counts: corrida sin {sorted(missing)} — llaves: {sorted(run.keys())}"
        raise ValueError(msg)
    raw_counts = run["counts"]
    if not isinstance(raw_counts, dict):
        msg = f"normalize_counts: 'counts' debe ser dict, recibido {type(raw_counts).__name__}"
        raise TypeError(msg)
    typed_counts = cast("dict[str, Any]", raw_counts)
    counts = {str(bitstring): int(count) for bitstring, count in typed_counts.items()}
    backend = str(run["device"])
    return NormalizedCounts(
        counts=counts,
        bit_order=bit_order,
        backend=backend,
        noisy_simulation=noisy_simulation,
        error_params=error_params,
    )
