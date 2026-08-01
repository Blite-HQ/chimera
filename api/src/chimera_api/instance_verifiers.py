"""Registro instancia→verifiers — plan `docs/mvp/01-runtime-api.md` §3,
generalizado por `docs/specs/generalidad-retos.md` §Contrato-6 (G3): el
hardcode `_OPTIMALITY_CLAIM_TYPES = {"solution"}` se reemplaza por un
registro declarativo por `claim_type` (`CLAIM_TYPE_VERIFIERS`) — la misión
resuelve por CLASE de problema, no por slug del corpus de un reto concreto.

Módulo PURO (sin FastAPI): resuelve qué adapters del puerto `Verifier`
amparan un claim, dado su `claim_type` y el `instance_id` que lo declara, y
cómo construir el claim de dominio desde el payload del request.

Regla fail-closed (decisión #7, conservada): un `claim_type` sin entrada en
`CLAIM_TYPE_VERIFIERS`, o una entrada cuya resolución no ampara la instancia
con NINGÚN verifier, es la señal para que el caller (`chimera_api.runs`)
devuelva 400 — jamás un run sin verificación.

Reto 1 (`solution`) se re-expresa como la primera entrada del registro
(compat total, mismos ids `verifier:cpsat-differential`/
`verifier:pandapower-islanding`, mismos grupos de independencia, mismo
`ELECTRICAL_DATA`). Reto 3 (`simulation_result`) resuelve contra el corpus
`knowledge/tfim/corpus/<slug>.json` (Part 1 de la spec — carga+digest fail-
closed, jamás toca el filesystem con un slug fuera de forma). Reto 2
(`statistical`) registra la CLAVE sin verificadores reales todavía
(TODO(G2): `property_rule` + corpus C2 no existen aún) — su resolución es
SIEMPRE vacía, así que el fail-closed corta antes de construir ningún claim.

Dato semilla `sintetica-4bus` (decisión #8): la misma topología de 4 buses /
dos islas que prueba el golden path real en
`tests/unit/certificate/test_assemble.py::TestDosPatasReales` — coherencia
con el único camino ya probado de punta a punta con anclas reales.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from blite.verification.anchor import AnchorKind
from blite.verification.attestation import Attestation, VerifierClass
from blite.verification.context import InvocationContext
from blite.verification.exact_diagonalization import (
    ExactDiagonalizationVerifier,
    SimulationSeriesClaim,
)
from blite.verification.exact_solver import (
    ExactSolverVerifier,
    OptimalityClaim,
    VerificationProcessError,
)
from blite.verification.execution import ExecutionLimits, ExecutionVerifier
from blite.verification.ground_truth import (
    GroundTruthClaim,
    GroundTruthVerifier,
    build_ground_truth_record,
)
from blite.verification.verifier import Determinism, Verifier

# api/src/chimera_api/instance_verifiers.py -> parents[3] es la raíz del
# repo (mismo cómputo que `_REPO_ROOT` en chimera_api.runs, misma
# profundidad de directorio).
_REPO_ROOT = Path(__file__).parents[3]
_TFIM_CORPUS_DIR = _REPO_ROOT / "knowledge" / "tfim" / "corpus"

# Mismo patrón de slug que `chimera_api.runs._load_corpus_matrix` — un
# `instance_id` que viaja en el body HTTP jamás se interpola en una ruta de
# archivo sin pasar por este guard primero (validación en frontera, ataque
# de traversal incluido).
_CORPUS_SLUG_PATTERN = re.compile(r"[a-z0-9][a-z0-9-]*")

_SOLVER_VERIFIER_ID = "verifier:cpsat-differential"
_SOLVER_INDEPENDENCE_GROUP = "leg-formal"
_SOLVER_ANCHOR_PROVENANCE = "cpsat-reference-v1"
_SOLVER_ANCHOR_KIND = "solver"

_EXECUTION_VERIFIER_ID = "verifier:pandapower-islanding"
_EXECUTION_INDEPENDENCE_GROUP = "leg-execution"
_EXECUTION_ANCHOR_KIND = "execution"

SOLVER_ANCHOR_DIGEST = hashlib.sha256(
    f"anchor:{_SOLVER_ANCHOR_PROVENANCE}".encode()
).hexdigest()

# Reto 3 (§Contrato-3): dos patas C3 por construcción — recompute ED
# (`solver`) + series congeladas del corpus (`dataset`), grupos de
# independencia DISTINTOS.
_ED_VERIFIER_ID = "verifier:ed-dense"
_ED_INDEPENDENCE_GROUP = "leg-formal-ed"
_GT_VERIFIER_ID = "verifier:tfim-corpus"
_GT_INDEPENDENCE_GROUP = "leg-dataset-tfim"


@dataclass(frozen=True)
class InstanceElectricalData:
    """Dato eléctrico versionado de una instancia (conocimiento, no código)."""

    topology: dict[str, Any]
    limits: ExecutionLimits
    anchor_digest: str
    provenance: str


@dataclass(frozen=True)
class VerifierResolution:
    """Verifiers que amparan un claim + sus descriptores de ancla, en orden."""

    verifiers: tuple[Verifier, ...]
    anchor_descriptors: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class ClaimTypeEntry:
    """Lo que el registro declara para UN `claim_type`: cómo construir el
    claim de dominio desde el payload normalizado del request, y cómo
    resolver un `instance_id` en verifiers + descriptores de ancla."""

    build_claim: Callable[[dict[str, Any]], Any]
    resolve: Callable[[str], VerifierResolution]


_SINTETICA_4BUS_PROVENANCE = "pandapower-sintetica-v1"

# Topología EXACTA de TestDosPatasReales.TOPOLOGY (4 buses, dos islas
# {0,1}/{2,3}, 3 branches, 2 loads) — el único golden path ya probado con
# CP-SAT y pandapower reales sobre la misma partición.
_SINTETICA_4BUS = InstanceElectricalData(
    topology={
        "buses": [{"id": i, "vn_kv": 20.0} for i in range(4)],
        "slack": [{"bus": 0, "vm_pu": 1.0}, {"bus": 2, "vm_pu": 1.0}],
        "branches": [
            {"from": 0, "to": 1, "r_ohm_per_km": 0.05, "x_ohm_per_km": 0.1},
            {"from": 2, "to": 3, "r_ohm_per_km": 0.05, "x_ohm_per_km": 0.1},
            {"from": 1, "to": 2, "r_ohm_per_km": 0.05, "x_ohm_per_km": 0.1},
        ],
        "loads": [{"bus": 1, "p_mw": 1.0}, {"bus": 3, "p_mw": 1.0}],
    },
    limits=ExecutionLimits(),
    anchor_digest=hashlib.sha256(
        f"anchor:{_SINTETICA_4BUS_PROVENANCE}".encode()
    ).hexdigest(),
    provenance=_SINTETICA_4BUS_PROVENANCE,
)

ELECTRICAL_DATA: dict[str, InstanceElectricalData] = {"sintetica-4bus": _SINTETICA_4BUS}


def _solver_verifier() -> Verifier:
    return ExactSolverVerifier(
        verifier_id=_SOLVER_VERIFIER_ID,
        independence_group=_SOLVER_INDEPENDENCE_GROUP,
        anchor_digest=SOLVER_ANCHOR_DIGEST,
    )


def _solver_descriptor() -> dict[str, Any]:
    return {
        "anchor_digest": SOLVER_ANCHOR_DIGEST,
        "kind": _SOLVER_ANCHOR_KIND,
        "provenance": _SOLVER_ANCHOR_PROVENANCE,
    }


def _execution_verifier(data: InstanceElectricalData) -> Verifier:
    return ExecutionVerifier(
        verifier_id=_EXECUTION_VERIFIER_ID,
        independence_group=_EXECUTION_INDEPENDENCE_GROUP,
        anchor_digest=data.anchor_digest,
        topology=data.topology,
        limits=data.limits,
    )


def _execution_descriptor(data: InstanceElectricalData) -> dict[str, Any]:
    return {
        "anchor_digest": data.anchor_digest,
        "kind": _EXECUTION_ANCHOR_KIND,
        "provenance": data.provenance,
    }


def _resolve_solution(instance_id: str) -> VerifierResolution:
    """Reto 1 (compat total, decisión #7/#8): CP-SAT ampara SIEMPRE; la
    pata eléctrica (pandapower) se añade solo si `instance_id` trae dato
    registrado en `ELECTRICAL_DATA` — sin él, la segunda pata simplemente no
    existe, nunca se inventa."""
    verifiers: list[Verifier] = [_solver_verifier()]
    descriptors: list[dict[str, Any]] = [_solver_descriptor()]

    electrical_data = ELECTRICAL_DATA.get(instance_id)
    if electrical_data is not None:
        verifiers.append(_execution_verifier(electrical_data))
        descriptors.append(_execution_descriptor(electrical_data))

    return VerifierResolution(tuple(verifiers), tuple(descriptors))


def _model_validating_builder(model: type[BaseModel]) -> Callable[[dict[str, Any]], Any]:
    """Fábrica DRY de `build_claim`: la mayoría de los claim_types no
    necesitan más que validar el payload directo contra su modelo pydantic
    (los campos "de sobre" `canonical_statement`/`scope` ya viven en ESE
    mismo modelo, mezclados por el caller antes de invocar)."""

    def _build(payload: dict[str, Any]) -> Any:
        return model.model_validate(payload)

    return _build


def _corpus_record_digest(record_without_digest: dict[str, Any]) -> str:
    """La regla de digest del CORPUS (`scripts/verify_corpus_digests.py`,
    regla 15.3 generalizada) — JSON canónico PLANO (`json.dumps` con
    `sort_keys`), deliberadamente NO `blite.certificate.canonical` (ese es
    el algoritmo JCS de otro anexo, para otro propósito: digests de
    contenido de certificado, no identidad de corpus)."""
    return hashlib.sha256(
        json.dumps(
            record_without_digest,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode()
    ).hexdigest()


def _load_tfim_corpus_record(slug: str) -> dict[str, Any] | None:
    """Carga+valida el corpus C3 `<slug>.json` — fail-closed en CUALQUIER
    anomalía (slug fuera de forma, archivo ausente, digest que no coincide
    con su propio contenido): devuelve `None`, jamás deja pasar un dato no
    verificado a un verificador. El slug se valida ANTES de tocar el
    filesystem (path traversal)."""
    if not _CORPUS_SLUG_PATTERN.fullmatch(slug):
        return None
    path = _TFIM_CORPUS_DIR / f"{slug}.json"
    if not path.is_file():
        return None
    try:
        record: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        embedded = record["digest"]
        record_without_digest = {k: v for k, v in record.items() if k != "digest"}
        if not isinstance(embedded, str):
            return None
        if _corpus_record_digest(record_without_digest) != embedded:
            return None
    except (OSError, KeyError, TypeError, ValueError):
        # Corpus malformado (JSON roto, campo ausente, tipo inesperado) es
        # la MISMA señal fail-closed que un digest que no coincide — jamás
        # un 500 por un dato de conocimiento corrupto.
        return None
    return record


def _expected_from_tfim_corpus(record: dict[str, Any]) -> dict[str, float]:
    """`{label: valor}` mezclando `observables_z`+`serie_z` y
    `observables_zz`+`serie_zz` por posición (§Contrato-6, Part 1)."""
    expected: dict[str, float] = {}
    for obs, value in zip(record["observables_z"], record["serie_z"], strict=True):
        expected[str(obs["label"])] = float(value)
    for obs, value in zip(record["observables_zz"], record["serie_zz"], strict=True):
        expected[str(obs["label"])] = float(value)
    return expected


@dataclass(frozen=True)
class _GroundTruthOverSimulationSeries:
    """Adapta un `GroundTruthVerifier` (que espera un `GroundTruthClaim`)
    para verificar el MISMO `SimulationSeriesClaim` que
    `ExactDiagonalizationVerifier` consume — la segunda pata C3 (`dataset`)
    contrasta los MISMOS labels que el candidato reportó contra el corpus
    congelado, sin que el candidato tenga que declarar una segunda forma de
    claim aparte para una sola conclusión (§Contrato-3: "dos patas C3 por
    construcción" son dos MÉTODOS de verificación, no dos submissions)."""

    inner: GroundTruthVerifier

    @property
    def verifier_id(self) -> str:
        return self.inner.verifier_id

    @property
    def independence_group(self) -> str:
        return self.inner.independence_group

    @property
    def verifier_class(self) -> VerifierClass:
        return self.inner.verifier_class

    @property
    def anchor_kind(self) -> AnchorKind:
        return self.inner.anchor_kind

    @property
    def determinism(self) -> Determinism:
        return self.inner.determinism

    def verify(self, claim: Any, ctx: InvocationContext) -> Attestation:
        if not isinstance(claim, SimulationSeriesClaim):
            msg = f"claim {type(claim).__name__} no es un SimulationSeriesClaim"
            raise VerificationProcessError(msg)
        observed = {
            obs.label: value
            for obs, value in zip(claim.observables, claim.series, strict=True)
        }
        translated = GroundTruthClaim(
            case_id=self.inner.record.case_id,
            observed=observed,
            canonical_statement=claim.canonical_statement,
            scope=claim.scope,
        )
        return self.inner.verify(translated, ctx)


def _resolve_simulation_result(instance_id: str) -> VerifierResolution:
    """Reto 3 (`simulation_result`, §Contrato-6 Part 1): `instance_id` es un
    slug del corpus `knowledge/tfim/corpus/<slug>.json`. Fail-closed: slug
    desconocido, fuera de forma, o corpus con digest tamperado ⇒ resolución
    vacía — el caller (`chimera_api.runs`) responde 400, jamás un 500."""
    record = _load_tfim_corpus_record(instance_id)
    if record is None:
        return VerifierResolution((), ())

    try:
        dataset_id = str(record["dataset_id"])
        case_id = str(record["instancia"])
        tolerance = float(record["tolerancia_relativa"])
        source_digest = str(record["digest"])
        expected = _expected_from_tfim_corpus(record)
    except (KeyError, TypeError, ValueError):
        return VerifierResolution((), ())

    solver_anchor_digest = hashlib.sha256(f"anchor:{dataset_id}".encode()).hexdigest()
    ed_verifier: Verifier = ExactDiagonalizationVerifier(
        verifier_id=_ED_VERIFIER_ID,
        independence_group=_ED_INDEPENDENCE_GROUP,
        anchor_digest=solver_anchor_digest,
        relative_tolerance=tolerance,
    )

    ground_truth_record = build_ground_truth_record(
        dataset_id=dataset_id,
        case_id=case_id,
        expected=expected,
        tolerance=tolerance,
        source_digest=source_digest,
    )
    gt_verifier: Verifier = _GroundTruthOverSimulationSeries(
        GroundTruthVerifier(
            verifier_id=_GT_VERIFIER_ID,
            independence_group=_GT_INDEPENDENCE_GROUP,
            record=ground_truth_record,
        )
    )

    verifiers = (ed_verifier, gt_verifier)
    descriptors = (
        {
            "anchor_digest": solver_anchor_digest,
            "kind": "solver",
            "provenance": dataset_id,
        },
        {
            "anchor_digest": source_digest,
            "kind": "dataset",
            "provenance": dataset_id,
        },
    )
    return VerifierResolution(verifiers, descriptors)


def _build_statistical_claim_stub(payload: dict[str, Any]) -> Any:
    # TODO(G2): sin `GroundTruthPredicate`/`property_rule` de C2 todavía
    # (docs/specs/generalidad-retos.md §Contrato-3) — este `build_claim`
    # NUNCA se invoca en la práctica: `_resolve_statistical` devuelve
    # resolución vacía SIEMPRE, así que el fail-closed de
    # `chimera_api.runs._start_claim_run` corta antes de construir nada.
    msg = "claim_type 'statistical' aún no tiene verificadores (G2 pendiente)"
    raise NotImplementedError(msg)


def _resolve_statistical(instance_id: str) -> VerifierResolution:
    # TODO(G2): corpus C2 (`tabular-corpus/...`) y `PropertyRuleVerifier` no
    # existen todavía — resolución SIEMPRE vacía, fail-closed por diseño
    # (docs/specs/generalidad-retos.md §Contrato-6 Part 1, punto 3).
    del instance_id
    return VerifierResolution((), ())


CLAIM_TYPE_VERIFIERS: dict[str, ClaimTypeEntry] = {
    "solution": ClaimTypeEntry(
        build_claim=_model_validating_builder(OptimalityClaim),
        resolve=_resolve_solution,
    ),
    "simulation_result": ClaimTypeEntry(
        build_claim=_model_validating_builder(SimulationSeriesClaim),
        resolve=_resolve_simulation_result,
    ),
    # TODO(G2): sin corpus C2 (`tabular-corpus/...`) ni `PropertyRuleVerifier`
    # todavía — la CLAVE existe (§Contrato-6 Part 1, punto 3: la mission del
    # reto 2 debe fallar 400, no 404-por-claim_type-desconocido) pero
    # `resolve` es SIEMPRE vacía y `build_claim` nunca llega a invocarse.
    "statistical": ClaimTypeEntry(
        build_claim=_build_statistical_claim_stub,
        resolve=_resolve_statistical,
    ),
}


def resolve_verifiers(*, claim_type: str, instance_id: str) -> VerifierResolution:
    """Resuelve los verifiers que amparan `claim_type` sobre `instance_id`.

    Fail-closed (firma y comportamiento CONSERVADOS, decisión #7 / spec
    §Contrato-6): `claim_type` fuera de `CLAIM_TYPE_VERIFIERS` devuelve una
    resolución vacía — ninguna instancia rescata un tipo de claim no
    amparado, y ninguna entrada registrada rescata una instancia que su
    propia `resolve` no ampare."""
    entry = CLAIM_TYPE_VERIFIERS.get(claim_type)
    if entry is None:
        return VerifierResolution((), ())
    return entry.resolve(instance_id)
