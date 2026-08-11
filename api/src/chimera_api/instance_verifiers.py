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
closed, jamás toca el filesystem con un slug fuera de forma).

Reto 2 (`statistical`) resuelve contra el corpus `knowledge/tabular/corpus/
<slug>.json` + su CSV hermano (`<slug>.csv`) — MISMA disciplina fail-closed
de Part 1 (slug fuera de forma, archivo ausente, digest de record que no
coincide con su propio contenido ⇒ resolución vacía), MÁS un chequeo que C3
no necesita: el `csv_digest` embebido en el record se recomputa contra los
BYTES del CSV hermano — el record pinnea el CSV, así que un CSV swapeado se
detecta ahí, no solo un JSON tamperado.

Esos dos directorios (`knowledge/tfim/corpus/`, `knowledge/tabular/corpus/`)
son lo que ESTE despliegue declaró en `datasets:` del `DistributionManifest`
(decisión #167, G3 residual) — `_load_corpus_dirs_from_manifest` los lee una
vez al importar el módulo. Ya no son un literal clavado acá: un despliegue
sirve un corpus nuevo (o mueve uno existente) declarándolo en
`distributions/chimera/distribution.yaml`, sin tocar este archivo. Un
despliegue que no declara la familia entera falla cerrado (`None` ⇒
resolución vacía), la MISMA señal que un slug desconocido dentro de un
corpus sí declarado.

**Decisión de diseño (leg `ground_truth` de `statistical`, documentada aquí
porque es la pieza que este módulo decide y no la spec):** un leg
GROUND_TRUTH necesita valores esperados CONGELADOS. La fuente honesta son
los folds sellados + las etiquetas selladas — el claim transporta las
predicciones out-of-fold del modelo (`StatisticalClaim.predictions`); el
lado esperado es el vector de etiquetas congelado, cargado DIRECTO del CSV
verificado (`_load_tabular_labels`, jamás las etiquetas que el propio claim
pudiera declarar — el claim ni siquiera tiene un campo `labels`). El
adapter `_GroundTruthOverStatistical` RECOMPUTA la accuracy a partir de
`(predictions, frozen_labels)` — nunca toma la palabra del proponente sobre
su propia métrica. La referencia congelada contra la que se contrasta esa
accuracy recomputada es el baseline trivial "predecir siempre la clase
mayoritaria" (`_majority_baseline_accuracy`): un número que se computa con
CERO ajustes de modelo, directo del mismo vector de etiquetas congelado —
"committed BEFORE any fit" en el sentido más literal posible, sin inventar
un segundo artefacto de corpus que esta spec no pidió. La tolerancia
(`_STATISTICAL_ACCURACY_TOLERANCE`) es deliberadamente ancha (peso relativo
0.5): este leg es un piso de cordura ("el pipeline no es un clasificador
degenerado/invertido"), NO un gate de desempeño — la pregunta "¿el brazo
cuántico es competitivo frente al clásico?" es la del test de McNemar
(`knowledge/quantum/04-estadistica-evidencia.md` §6), que vive en el
resumen del reto, no en este verificador. La segunda pata
(`PropertyRuleVerifier`, ancla `rule`) corre las invariantes estructurales
baratas del catálogo C2 que no requieren la matriz de kernel completa:
`labels_binary` (sobre las etiquetas congeladas), `folds_partition` (sobre
el `folds` que el claim declara) y `predictions_aligned` — grupo de
independencia DISTINTO del leg `dataset` (dos métodos, no dos islas de la
misma corrida).

Dato semilla `sintetica-4bus` (decisión #8): la misma topología de 4 buses /
dos islas que prueba el golden path real en
`tests/unit/certificate/test_assemble.py::TestDosPatasReales` — coherencia
con el único camino ya probado de punta a punta con anclas reales.
"""

from __future__ import annotations

import csv
import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from blite.runtime.distribution import DistributionManifest, load_distribution_manifest
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
from blite.verification.orchestrator import ResultProjection
from blite.verification.partition import build_partition
from blite.verification.property_rule import PropertyRuleClaim, PropertyRuleVerifier
from blite.verification.structural_partition import StructuralPartitionVerifier
from blite.verification.verifier import Determinism, Verifier
from chimera_api.corpus_records import load_corpus_record

# api/src/chimera_api/instance_verifiers.py -> parents[3] es la raíz del
# repo (mismo cómputo que `_REPO_ROOT` en chimera_api.runs, misma
# profundidad de directorio).
_REPO_ROOT = Path(__file__).parents[3]

# Mismo cómputo que `DISTRIBUTION_MANIFEST_PATH` en `chimera_api.runs` —
# duplicado a propósito, no importado desde ahí: `runs` importa DE este
# módulo (`CLAIM_TYPE_VERIFIERS`, `resolve_verifiers`), así que un import de
# vuelta sería circular.
_DISTRIBUTION_MANIFEST_PATH = (
    _REPO_ROOT / "distributions" / "chimera" / "distribution.yaml"
)

_TFIM_DATASET_ID = "tfim-corpus"
_TABULAR_DATASET_ID = "tabular-corpus"


def _dataset_corpus_dir(manifest: DistributionManifest, dataset_id: str) -> Path | None:
    """Resuelve el directorio de instancias que ESTE despliegue declaró para
    `dataset_id` en `datasets:` (decisión #167, G3 residual) — `None` si el
    despliegue no lo declaró: ninguna instancia de esa familia ampara nada,
    la MISMA señal fail-closed que hoy da un slug desconocido
    (`resolve_verifiers` responde vacío, `chimera_api.runs` corta 400 —
    jamás un 500 por un despliegue que no declaró el dataset)."""
    spec = manifest.datasets.get(dataset_id)
    if spec is None:
        return None
    return _REPO_ROOT / spec.path


def _load_corpus_dirs_from_manifest() -> tuple[Path | None, Path | None]:
    """Se lee UNA vez al importar el módulo — mismo espíritu que
    `chimera_api.runs._build_dispatcher`/`_build_model_backend`: configura-
    ción de despliegue, no de request. `datasets:` reemplaza acá las dos
    rutas que este módulo tenía clavadas antes (#167, G3 residual): declarar
    un corpus nuevo (o mover uno existente) en el manifest alcanza, sin
    tocar este archivo."""
    manifest = load_distribution_manifest(_DISTRIBUTION_MANIFEST_PATH)
    return (
        _dataset_corpus_dir(manifest, _TFIM_DATASET_ID),
        _dataset_corpus_dir(manifest, _TABULAR_DATASET_ID),
    )


_TFIM_CORPUS_DIR, _TABULAR_CORPUS_DIR = _load_corpus_dirs_from_manifest()

_SOLVER_VERIFIER_ID = "verifier:cpsat-differential"
_SOLVER_INDEPENDENCE_GROUP = "leg-formal"
_SOLVER_ANCHOR_PROVENANCE = "cpsat-reference-v1"
_SOLVER_ANCHOR_KIND = "solver"

_EXECUTION_VERIFIER_ID = "verifier:pandapower-islanding"
_EXECUTION_INDEPENDENCE_GROUP = "leg-execution"
_EXECUTION_ANCHOR_KIND = "execution"

# V1/M18 — pata ESTRUCTURAL: la única constancia por sub-entidad disponible
# cuando la instancia no tiene dato eléctrico registrado (p. ej. una red
# derivada de un portal GIS: trae geometría y nombres, jamás impedancias).
# Techo AL2 por clase — nunca finge la fuerza de una ejecución.
_STRUCTURAL_VERIFIER_ID = "verifier:structural-partition"
_STRUCTURAL_INDEPENDENCE_GROUP = "leg-structural"
_STRUCTURAL_ANCHOR_KIND = "rule"
_STRUCTURAL_ANCHOR_PROVENANCE = "structural-partition-v1"
_STRUCTURAL_ANCHOR_DIGEST = hashlib.sha256(
    f"anchor:{_STRUCTURAL_ANCHOR_PROVENANCE}".encode()
).hexdigest()

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

# Reto 2 (§Contrato-3/5, ver docstring del módulo para el diseño completo):
# dos patas C2 por construcción — accuracy recomputada vs baseline trivial
# congelado (`dataset`) + invariantes estructurales del pipeline (`rule`).
_TABULAR_GT_VERIFIER_ID = "verifier:tabular-corpus"
_TABULAR_GT_INDEPENDENCE_GROUP = "leg-dataset-tabular"
_TABULAR_RULE_VERIFIER_ID = "verifier:pipeline-rules"
_TABULAR_RULE_INDEPENDENCE_GROUP = "leg-rule-pipeline"
_TABULAR_RULE_ANCHOR_PROVENANCE = "property-rule-builtin-v1"
_TABULAR_RULE_ANCHOR_DIGEST = hashlib.sha256(
    f"anchor:{_TABULAR_RULE_ANCHOR_PROVENANCE}".encode()
).hexdigest()
_STATISTICAL_PROPERTIES: tuple[str, ...] = (
    "labels_binary",
    "folds_partition",
    "predictions_aligned",
)
_STATISTICAL_ACCURACY_TOLERANCE = 0.5
"""Tolerancia relativa (L∞, `relative_series_error`) del leg ground_truth de
`statistical` — deliberadamente ANCHA (ver docstring del módulo): es un piso
de cordura contra un pipeline degenerado, no un gate de desempeño frente al
baseline clásico (eso es McNemar, fuera de este verificador)."""


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
    claim de dominio desde el payload normalizado del request, cómo resolver
    un `instance_id` en verifiers + descriptores de ancla, y —opcional— cómo
    traducir las attestations resultantes a la superficie que su dominio
    consume (`build_projection`, V1/M18)."""

    build_claim: Callable[[dict[str, Any]], Any]
    resolve: Callable[[str], VerifierResolution]
    build_projection: Callable[[Any], ResultProjection | None] | None = None


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


def _structural_verifier() -> Verifier:
    return StructuralPartitionVerifier(
        verifier_id=_STRUCTURAL_VERIFIER_ID,
        independence_group=_STRUCTURAL_INDEPENDENCE_GROUP,
        anchor_digest=_STRUCTURAL_ANCHOR_DIGEST,
    )


def _structural_descriptor() -> dict[str, Any]:
    return {
        "anchor_digest": _STRUCTURAL_ANCHOR_DIGEST,
        "kind": _STRUCTURAL_ANCHOR_KIND,
        "provenance": _STRUCTURAL_ANCHOR_PROVENANCE,
    }


def _resolve_solution(instance_id: str) -> VerifierResolution:
    """Reto 1 (compat total, decisión #7/#8): CP-SAT ampara SIEMPRE; la
    pata eléctrica (pandapower) se añade solo si `instance_id` trae dato
    registrado en `ELECTRICAL_DATA` — sin él, la segunda pata simplemente no
    existe, nunca se inventa.

    [V1/M18] Cuando ese dato NO existe entra la pata ESTRUCTURAL en su lugar
    (AL2, ancla `rule`): verifica lo que el grafo permite verificar —
    conectividad por isla y coherencia del corte— para que una instancia sin
    modelo eléctrico igual tenga constancia POR ISLA, que es lo que el mapa
    necesita para pintar badges. Es EXCLUYENTE con la eléctrica a propósito:
    donde pandapower corre, sus checks por isla son estrictamente más fuertes,
    y sumar una tercera pata inflaría el conteo de patas independientes del
    punto 7 sin agregar un método realmente nuevo."""
    verifiers: list[Verifier] = [_solver_verifier()]
    descriptors: list[dict[str, Any]] = [_solver_descriptor()]

    electrical_data = ELECTRICAL_DATA.get(instance_id)
    if electrical_data is not None:
        verifiers.append(_execution_verifier(electrical_data))
        descriptors.append(_execution_descriptor(electrical_data))
    else:
        verifiers.append(_structural_verifier())
        descriptors.append(_structural_descriptor())

    return VerifierResolution(tuple(verifiers), tuple(descriptors))


def _model_validating_builder(
    model: type[BaseModel],
) -> Callable[[dict[str, Any]], Any]:
    """Fábrica DRY de `build_claim`: la mayoría de los claim_types no
    necesitan más que validar el payload directo contra su modelo pydantic
    (los campos "de sobre" `canonical_statement`/`scope` ya viven en ESE
    mismo modelo, mezclados por el caller antes de invocar)."""

    def _build(payload: dict[str, Any]) -> Any:
        return model.model_validate(payload)

    return _build


def _load_json_corpus_record(directory: Path, slug: str) -> dict[str, Any] | None:
    """Carga+valida CUALQUIER corpus `<slug>.json` bajo `directory` con la
    MISMA disciplina de identidad (§15.3 generalizada, spec §Contrato-4).

    La regla vive en `chimera_api.corpus_records` desde que V3/M20 la
    necesitó también para `knowledge/rvsp/`: dos definiciones de "este
    corpus es el que dice ser" son una de más, y la que se relajara primero
    sería por donde entraría un dato tamperado. Compartido hoy entre C3
    (`tfim/`), C2 (`tabular/`) y la curva r-vs-p.
    """
    return load_corpus_record(directory, slug)


def _load_tfim_corpus_record(slug: str) -> dict[str, Any] | None:
    """Corpus C3 (declarado en `datasets: tfim-corpus` del manifest, ver
    `_load_corpus_dirs_from_manifest`) — ver `_load_json_corpus_record`.
    Despliegue que no declaró el dataset ⇒ `None` sin tocar el filesystem,
    la MISMA resolución vacía que da un slug desconocido."""
    if _TFIM_CORPUS_DIR is None:
        return None
    return _load_json_corpus_record(_TFIM_CORPUS_DIR, slug)


def _load_tabular_corpus_record(slug: str) -> dict[str, Any] | None:
    """Corpus C2 (declarado en `datasets: tabular-corpus` del manifest, ver
    `_load_corpus_dirs_from_manifest`) — ver `_load_json_corpus_record`.
    Despliegue que no declaró el dataset ⇒ `None` sin tocar el filesystem,
    la MISMA resolución vacía que da un slug desconocido."""
    if _TABULAR_CORPUS_DIR is None:
        return None
    return _load_json_corpus_record(_TABULAR_CORPUS_DIR, slug)


def _load_tabular_labels(slug: str, record: dict[str, Any]) -> tuple[int, ...] | None:
    """Carga los labels CRUDOS del CSV hermano (`<slug>.csv`) tras verificar
    sus BYTES contra `csv_digest` — el record pinnea el CSV, así que un CSV
    swapeado (mismo JSON, otro contenido) se detecta aquí, no solo un JSON
    tamperado (eso ya lo cubre `_load_tabular_corpus_record`). Fail-closed en
    cualquier anomalía: `None`, jamás deja pasar bytes no verificados.

    Los labels jamás viajan en el `StatisticalClaim` — son la mitad
    congelada del leg `ground_truth` (ver docstring del módulo, diseño C2);
    cargarlos aquí, server-side, es precisamente lo que evita que el
    verificador tenga que tomarle la palabra al proponente."""
    if _TABULAR_CORPUS_DIR is None:
        return None
    path = _TABULAR_CORPUS_DIR / f"{slug}.csv"
    if not path.is_file():
        return None
    try:
        expected_csv_digest = str(record["csv_digest"])
        label_column = str(record["columna_etiqueta"])
    except (KeyError, TypeError, ValueError):
        return None
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_csv_digest:
        return None
    try:
        reader = csv.reader(raw.decode("utf-8").splitlines())
        header = next(reader)
        label_index = header.index(label_column)
        labels = tuple(int(row[label_index]) for row in reader)
    except (StopIteration, ValueError, IndexError):
        return None
    return labels


def _majority_baseline_accuracy(labels: tuple[int, ...]) -> float:
    """Baseline trivial "predecir SIEMPRE la clase mayoritaria" — computable
    con CERO ajustes de modelo, directo del vector de etiquetas congelado
    (ver diseño en el docstring del módulo). La referencia que el leg
    ground_truth de `statistical` usa como `expected`."""
    ones = sum(labels)
    zeros = len(labels) - ones
    return max(zeros, ones) / len(labels)


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

    def verify_all(self, claim: Any, ctx: InvocationContext) -> tuple[Attestation, ...]:
        """Constancia ÚNICA (default del puerto, freeze §7 [MEJORADO
        C-6/#106]): este adapter no tiene sub-entidades que verificar por
        separado. Explícito porque satisface `Verifier` ESTRUCTURALMENTE."""
        return (self.verify(claim, ctx),)

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


class StatisticalClaim(BaseModel):
    """Claim de `statistical` (reto 2): «las predicciones out-of-fold del
    modelo concuerdan con las etiquetas selladas dentro de tolerancia y
    sostienen las invariantes estructurales del pipeline». Deliberadamente
    SIN campo `labels`: el lado esperado es SIEMPRE el vector congelado que
    `_load_tabular_labels` carga server-side (ver docstring del módulo) —
    un claim que pudiera declarar sus propias etiquetas podría fabricar el
    "ground truth" que lo verifica, exactamente lo que este diseño evita."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    case_id: str
    predictions: tuple[int, ...]
    folds: tuple[int, ...]
    canonical_statement: str
    scope: dict[str, Any]


@dataclass(frozen=True)
class _GroundTruthOverStatistical:
    """Adapta un `GroundTruthVerifier` para verificar un `StatisticalClaim`
    (reto 2, leg `dataset`) — ver el diseño completo en el docstring del
    módulo. RECOMPUTA la accuracy a partir de `(predictions, frozen_labels)`
    (`frozen_labels` cerrado en construcción, cargado del CSV sellado en
    `_resolve_statistical` — jamás del claim): nunca toma la palabra del
    proponente sobre su propia métrica."""

    inner: GroundTruthVerifier
    frozen_labels: tuple[int, ...]

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

    def verify_all(self, claim: Any, ctx: InvocationContext) -> tuple[Attestation, ...]:
        """Constancia ÚNICA (default del puerto, freeze §7 [MEJORADO
        C-6/#106]): este adapter no tiene sub-entidades que verificar por
        separado. Explícito porque satisface `Verifier` ESTRUCTURALMENTE."""
        return (self.verify(claim, ctx),)

    def verify(self, claim: Any, ctx: InvocationContext) -> Attestation:
        if not isinstance(claim, StatisticalClaim):
            msg = f"claim {type(claim).__name__} no es un StatisticalClaim"
            raise VerificationProcessError(msg)
        if len(claim.predictions) != len(self.frozen_labels):
            msg = (
                f"predictions ({len(claim.predictions)}) y las etiquetas "
                f"congeladas ({len(self.frozen_labels)}) tienen largo "
                "distinto — no hay accuracy bien planteada, no es un fail"
            )
            raise VerificationProcessError(msg)
        correct = sum(
            1
            for predicted, true in zip(
                claim.predictions, self.frozen_labels, strict=True
            )
            if predicted == true
        )
        accuracy = correct / len(self.frozen_labels)
        translated = GroundTruthClaim(
            case_id=self.inner.record.case_id,
            observed={"accuracy": accuracy},
            canonical_statement=claim.canonical_statement,
            scope=claim.scope,
        )
        return self.inner.verify(translated, ctx)


@dataclass(frozen=True)
class _PropertyRuleOverStatistical:
    """Adapta un `PropertyRuleVerifier` para verificar el MISMO
    `StatisticalClaim` — segunda pata C2 (`rule`), grupo de independencia
    DISTINTO del leg `dataset` (dos métodos, no dos islas de la misma
    corrida). Corre las invariantes estructurales baratas del catálogo C2
    que no requieren la matriz de kernel completa (`_STATISTICAL_
    PROPERTIES`): etiquetas binarias sobre `frozen_labels` (jamás las del
    claim — no las tiene), partición de folds y alineación predicciones↔
    etiquetas sobre lo que el claim SÍ declara."""

    inner: PropertyRuleVerifier
    frozen_labels: tuple[int, ...]

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

    def verify_all(self, claim: Any, ctx: InvocationContext) -> tuple[Attestation, ...]:
        """Constancia ÚNICA (default del puerto, freeze §7 [MEJORADO
        C-6/#106]): este adapter no tiene sub-entidades que verificar por
        separado. Explícito porque satisface `Verifier` ESTRUCTURALMENTE."""
        return (self.verify(claim, ctx),)

    def verify(self, claim: Any, ctx: InvocationContext) -> Attestation:
        if not isinstance(claim, StatisticalClaim):
            msg = f"claim {type(claim).__name__} no es un StatisticalClaim"
            raise VerificationProcessError(msg)
        subject: dict[str, Any] = {
            "labels": self.frozen_labels,
            "folds": claim.folds,
            "predictions": claim.predictions,
        }
        translated = PropertyRuleClaim(
            subject=subject,
            properties=_STATISTICAL_PROPERTIES,
            relations=(),
            canonical_statement=claim.canonical_statement,
            scope=claim.scope,
        )
        return self.inner.verify(translated, ctx)


def _resolve_statistical(instance_id: str) -> VerifierResolution:
    """Reto 2 (`statistical`, §Contrato-6 Part 1 punto 3): `instance_id` es
    un slug del corpus `knowledge/tabular/corpus/<slug>.json`. Fail-closed:
    slug desconocido, fuera de forma, corpus con digest tamperado, o CSV
    hermano cuyos bytes no coinciden con `csv_digest` ⇒ resolución vacía —
    el caller (`chimera_api.runs`) responde 400, jamás un 500. Ver el
    docstring del módulo para el diseño completo del leg ground_truth."""
    record = _load_tabular_corpus_record(instance_id)
    if record is None:
        return VerifierResolution((), ())

    frozen_labels = _load_tabular_labels(instance_id, record)
    if not frozen_labels:
        return VerifierResolution((), ())

    try:
        dataset_id = str(record["dataset_id"])
        case_id = str(record["instancia"])
        source_digest = str(record["digest"])
    except (KeyError, TypeError, ValueError):
        return VerifierResolution((), ())

    ground_truth_record = build_ground_truth_record(
        dataset_id=dataset_id,
        case_id=case_id,
        expected={"accuracy": _majority_baseline_accuracy(frozen_labels)},
        tolerance=_STATISTICAL_ACCURACY_TOLERANCE,
        source_digest=source_digest,
    )
    gt_verifier: Verifier = _GroundTruthOverStatistical(
        inner=GroundTruthVerifier(
            verifier_id=_TABULAR_GT_VERIFIER_ID,
            independence_group=_TABULAR_GT_INDEPENDENCE_GROUP,
            record=ground_truth_record,
        ),
        frozen_labels=frozen_labels,
    )
    rule_verifier: Verifier = _PropertyRuleOverStatistical(
        inner=PropertyRuleVerifier(
            verifier_id=_TABULAR_RULE_VERIFIER_ID,
            independence_group=_TABULAR_RULE_INDEPENDENCE_GROUP,
            anchor_digest=_TABULAR_RULE_ANCHOR_DIGEST,
        ),
        frozen_labels=frozen_labels,
    )

    verifiers = (gt_verifier, rule_verifier)
    descriptors = (
        {
            "anchor_digest": source_digest,
            "kind": "dataset",
            "provenance": dataset_id,
        },
        {
            "anchor_digest": _TABULAR_RULE_ANCHOR_DIGEST,
            "kind": "rule",
            "provenance": _TABULAR_RULE_ANCHOR_PROVENANCE,
        },
    )
    return VerifierResolution(verifiers, descriptors)


def _solution_projection(claim: Any) -> ResultProjection | None:
    """V1/M18 — el productor de `partition` para `solution` (C-8).

    Vive acá y no en el orquestador porque ESTE módulo es el que sabe de qué
    clase de problema habla cada `claim_type`; el engine sigue sin saber de
    particiones. Devuelve `None` cuando el claim no declara instancia: sin
    `topology_ref` la superficie no tendría a qué topología referirse, y una
    partición huérfana es peor que ninguna.

    `branch_ids=None` a propósito: el claim transporta las aristas, no los ids
    del portal, así que el corte se nombra con la convención CANÓNICA — que es
    derivable de esas mismas aristas por cualquier tercero.
    """
    if not isinstance(claim, OptimalityClaim):
        return None
    instance_id = str(claim.scope.get("instancia", ""))
    if not instance_id:
        return None

    def _project(attestation: Attestation) -> dict[str, Any] | None:
        partition = build_partition(
            attestation=attestation,
            assignment=claim.assignment,
            edges=claim.instance.edges,
            topology_ref=instance_id,
        )
        # La llave es la que la ruta de lectura ya esperaba
        # (`reads::_PARTITION_PAYLOAD_KEY`): el payload viaja ANIDADO, no
        # derramado sobre el evento.
        return None if partition is None else {"partition": partition}

    return _project


CLAIM_TYPE_VERIFIERS: dict[str, ClaimTypeEntry] = {
    "solution": ClaimTypeEntry(
        build_claim=_model_validating_builder(OptimalityClaim),
        resolve=_resolve_solution,
        build_projection=_solution_projection,
    ),
    "simulation_result": ClaimTypeEntry(
        build_claim=_model_validating_builder(SimulationSeriesClaim),
        resolve=_resolve_simulation_result,
    ),
    "statistical": ClaimTypeEntry(
        build_claim=_model_validating_builder(StatisticalClaim),
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


def resolve_result_projection(
    *, claim_type: str, claim: Any
) -> ResultProjection | None:
    """La proyección de superficie que ampara este claim, o `None` si su clase
    no declara ninguna (V1/M18).

    Hermana de `resolve_verifiers` y con la misma disciplina: un `claim_type`
    sin entrada no rescata nada — la superficie queda honest-empty en vez de
    recibir un payload fabricado.
    """
    entry = CLAIM_TYPE_VERIFIERS.get(claim_type)
    if entry is None or entry.build_projection is None:
        return None
    return entry.build_projection(claim)
