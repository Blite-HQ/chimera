"""
GroundTruthVerifier — el adapter `ground_truth` genérico (ancla `dataset`).
Vocabulario §4 / docs/specs/generalidad-retos.md §Contrato-3/4.

Contrasta valores etiquetados (`observed`) de un claim contra un
`GroundTruthRecord` CONGELADO suministrado en construcción — series de ED
del corpus C3 hoy (`tfim-corpus/...`), casos del corpus C2 mañana
(`tabular-corpus/...`, reto 2): el verificador es agnóstico al reto, la
identidad y el contenido del record son DATO (regla generalizada §4 de la
spec / ADR-029 — el conocimiento de reto vive en `knowledge/` y en los
datos, jamás aquí).

Dos reglas duras que distinguen esto de una simple comparación de dicts:

1. **Auto-consistencia del REGISTRO es un error de PROCESO, no un
   veredicto** (receta 11 §5.1, misma doctrina que el corpus de islanding:
   «se reporta, NUNCA se sobreescribe»). Antes de comparar nada se recomputa
   el digest de auto-consistencia del record (`embedded_digest`, sobre los
   campos propios del record — incluido `source_digest`); si no coincide,
   el record fue MUTADO o RECONSTRUIDO de forma inconsistente entre su
   construcción y su verificación, y el fallo es del verificador, jamás del
   proponente — un `fail` ahí acusaría al candidato por un defecto de quien
   construyó el record.

   Esto es DISTINTO de que el ARTEFACTO FUENTE (el archivo del corpus) haya
   sido tamperado: un chequeo que recomputa un digest sobre los campos del
   PROPIO record y lo compara contra un digest embebido en ESE MISMO record
   es circular — si el mismo código que construyó el record también computa
   el digest de comparación, jamás puede detectar que el ARCHIVO de origen
   fue manipulado (solo detecta que el objeto en memoria es internamente
   consistente consigo mismo). Esa garantía la da `source_digest` — el
   digest embebido del propio archivo del corpus — verificado al CARGARLO
   (no aquí; Part 1 / `chimera_api.instance_verifiers`, fail-closed), y es
   lo que la Attestation ancla vía `anchor_digest`.
2. **Un desacuerdo en el CONJUNTO de labels también es un error de
   PROCESO**: un label que el candidato reporta y el record no define (o
   viceversa) significa que no hay nada que comparar — no es que el
   candidato "falló" un valor, es que la pregunta está mal planteada.

Scoring: reusa `relative_series_error` de `exact_diagonalization` — mismo
mecanismo L∞-relativo (receta §4.1), pero esto es *scoring* COMPARTIDO, NO
un ancla compartida (§Deliverable-2): el ancla de este verificador es el
`GroundTruthRecord` congelado, un grupo de independencia DISTINTO del
recompute vivo de `ExactDiagonalizationVerifier` (receta 11 §2 — «dos patas
C3 por construcción»).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from blite.certificate.canonical import JSONValue, canonicalize
from blite.verification.anchor import AnchorKind
from blite.verification.attestation import Attestation, Verdict, VerifierClass
from blite.verification.claim import claim_view_digest
from blite.verification.context import InvocationContext
from blite.verification.evidence import GroundTruthPredicate
from blite.verification.exact_diagonalization import relative_series_error
from blite.verification.exact_solver import VerificationProcessError
from blite.verification.verifier import Determinism

_SCORING_ALGORITHM_ID = "ground-truth-relative-series-error-v1"


class GroundTruthRecord(BaseModel):
    """El ancla CONGELADA: valores esperados por label + su tolerancia +
    digest embebido self-consistente (identidad generalizada, spec §4)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    dataset_id: str
    case_id: str
    expected: dict[str, float]
    tolerance: float
    """NO es una tolerancia absoluta — se compara con la MISMA semántica
    L∞-relativa de `relative_series_error` (receta §4.1), reusada como
    scoring compartido (ver docstring del módulo)."""
    source_digest: str
    """El digest EMBEBIDO del artefacto CONGELADO de origen (p. ej. el
    campo `digest` del JSON del corpus C3) — LO QUE la Attestation ancla
    (`anchor_digest`, más abajo). Su verificación — que el archivo fuente no
    fue tamperado — ocurre al CARGAR el corpus, no en este verificador
    (Part 1, `chimera_api.instance_verifiers`, fail-closed)."""
    embedded_digest: str
    """Digest de auto-consistencia del REGISTRO en memoria (record-
    integrity, NO integridad de la fuente): recomputado por `_record_digest`
    sobre los campos propios del record (incluido `source_digest`) y
    comparado en `verify()`. Detecta que el record fue mutado o
    reconstruido de forma inconsistente entre su construcción y su
    verificación — por ejemplo, un `model_copy(update=...)` que tocó un
    campo sin recomputar el digest. NO detecta manipulación del artefacto
    de origen: esa garantía la da `source_digest` (ver arriba)."""


class GroundTruthClaim(BaseModel):
    """Claim: «los valores `observed` (por label) concuerdan con el corpus
    congelado `case_id`»."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    case_id: str
    observed: dict[str, float]
    canonical_statement: str
    scope: dict[str, Any]


def _record_digest(record: GroundTruthRecord) -> str:
    """SHA-256 del JSON canónico del record SIN `embedded_digest` — chequeo
    de auto-consistencia del REGISTRO (record-integrity): detecta que el
    record en memoria fue mutado o reconstruido de forma distinta entre su
    construcción original y el momento de `verify()`. Incluye
    `source_digest` en la vista — si alguien reconstruye el record con OTRO
    `source_digest` sin recomputar `embedded_digest`, esto también lo caza.

    NO detecta ni pretende detectar manipulación del artefacto CONGELADO de
    origen (el archivo del corpus): esa garantía la da `source_digest`
    (verificado al cargar el corpus, no aquí — Part 1 del dispatcher)."""
    view: dict[str, JSONValue] = {
        "dataset_id": record.dataset_id,
        "case_id": record.case_id,
        "expected": dict(record.expected),
        "tolerance": record.tolerance,
        "source_digest": record.source_digest,
    }
    return hashlib.sha256(canonicalize(view)).hexdigest()


def build_ground_truth_record(
    *,
    dataset_id: str,
    case_id: str,
    expected: dict[str, float],
    tolerance: float,
    source_digest: str,
) -> GroundTruthRecord:
    """Constructor conveniente: computa `embedded_digest` (auto-consistencia
    del record) con el MISMO algoritmo que `_record_digest` recomputa en
    `verify()` — un caller externo (p. ej. el dispatcher de
    `chimera_api.instance_verifiers`) no reimplementa la vista canónica a
    mano, así que no puede dejarla divergir por accidente."""
    draft = GroundTruthRecord(
        dataset_id=dataset_id,
        case_id=case_id,
        expected=expected,
        tolerance=tolerance,
        source_digest=source_digest,
        embedded_digest="",
    )
    return draft.model_copy(update={"embedded_digest": _record_digest(draft)})


def claim_digest_of(claim: GroundTruthClaim) -> str:
    """Delegación al helper común (§7 del anexo) — un solo lugar computa la
    vista claim↔digest."""
    return claim_view_digest(claim.canonical_statement, claim.scope)


def _default_binary_digest() -> str:
    """No hay solver externo aquí (a diferencia de CP-SAT/eigh): el "binario"
    es el propio algoritmo de scoring, versionado por su id."""
    return hashlib.sha256(_SCORING_ALGORITHM_ID.encode()).hexdigest()


@dataclass(frozen=True)
class GroundTruthVerifier:
    """Adapter de la clase `ground_truth`: contrasta `observed` contra un
    `GroundTruthRecord` congelado (ancla `dataset`)."""

    verifier_id: str
    independence_group: str
    record: GroundTruthRecord
    verifier_binary_digest: str = field(default_factory=_default_binary_digest)

    verifier_class: VerifierClass = field(default="ground_truth", init=False)
    anchor_kind: AnchorKind = field(default="dataset", init=False)
    determinism: Determinism = field(default="deterministic", init=False)

    @property
    def _params(self) -> dict[str, JSONValue]:
        return {
            "scoring": _SCORING_ALGORITHM_ID,
            "dataset_id": self.record.dataset_id,
            "case_id": self.record.case_id,
        }

    @property
    def verifier_params_digest(self) -> str:
        return hashlib.sha256(canonicalize(self._params)).hexdigest()

    @property
    def anchor_digest(self) -> str:
        """El ancla es el artefacto FUENTE congelado — `source_digest` del
        record, NO `embedded_digest` (ese es el chequeo de auto-consistencia
        del record EN MEMORIA, ver docstring de `GroundTruthRecord` — un
        chequeo circular si se usara como ancla: el mismo código que
        construye el record también lo recomputaría). Bindear la Attestation
        a `source_digest` es lo que hace que el ancla corresponda a los
        bytes EXACTOS del corpus verificados al cargarlo (Part 1 del
        dispatcher), a diferencia de un dato que el propio verificador
        podría reconstruir de cualquier forma internamente consistente."""
        return self.record.source_digest

    def verify(self, claim: Any, ctx: InvocationContext) -> Attestation:
        if not isinstance(claim, GroundTruthClaim):
            msg = f"claim {type(claim).__name__} no es un GroundTruthClaim"
            raise VerificationProcessError(msg)

        recomputed = _record_digest(self.record)
        if recomputed != self.record.embedded_digest:
            msg = (
                f"GroundTruthRecord {self.record.dataset_id}/"
                f"{self.record.case_id}: digest embebido "
                f"{self.record.embedded_digest} no coincide con el "
                f"recomputado {recomputed} — el record fue mutado o "
                "reconstruido de forma inconsistente entre construcción y "
                "verificación (chequeo de record-integrity; NO detecta "
                "tampering del artefacto fuente — eso lo cubre "
                "source_digest, verificado al cargar el corpus), jamás un "
                "fail del candidato"
            )
            raise VerificationProcessError(msg)

        expected_labels = set(self.record.expected)
        observed_labels = set(claim.observed)
        if expected_labels != observed_labels:
            missing = sorted(expected_labels - observed_labels)
            extra = sorted(observed_labels - expected_labels)
            msg = (
                f"labels de {self.record.case_id} no coinciden entre "
                f"expected y observed: faltan {missing}, sobran {extra} — "
                "no hay nada que comparar, no es un fail"
            )
            raise VerificationProcessError(msg)

        labels = sorted(expected_labels)
        expected_values = tuple(self.record.expected[label] for label in labels)
        observed_values = tuple(claim.observed[label] for label in labels)

        error = relative_series_error(observed_values, expected_values)
        verdict: Verdict = "pass" if error <= self.record.tolerance else "fail"

        expected_view: dict[str, JSONValue] = dict(self.record.expected)
        observed_view: dict[str, JSONValue] = dict(claim.observed)
        expected_digest = hashlib.sha256(canonicalize(expected_view)).hexdigest()
        observed_digest = hashlib.sha256(canonicalize(observed_view)).hexdigest()

        return Attestation(
            verifier_id=self.verifier_id,
            verifier_class=self.verifier_class,
            anchor_kind=self.anchor_kind,
            level="AL3",
            verdict=verdict,
            scope=claim.scope,
            independence_group=self.independence_group,
            run_id=ctx.run_id,
            claim_digest=claim_digest_of(claim),
            verifier_binary_digest=self.verifier_binary_digest,
            verifier_params_digest=self.verifier_params_digest,
            anchor_digest=self.anchor_digest,
            predicate=GroundTruthPredicate(
                dataset_id=self.record.dataset_id,
                case_id=self.record.case_id,
                expected_digest=expected_digest,
                observed_digest=observed_digest,
                match=(verdict == "pass"),
                tolerance=self.record.tolerance,
            ),
            issued_at=datetime.now(UTC),
        )
