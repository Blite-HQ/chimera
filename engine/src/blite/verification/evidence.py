"""
Predicates por clase — la forma auditable que cada método deja. Vocabulario §4.

freeze §4: la evidence deja de ser unión embebida — son refs content-addressed
(`Attestation.evidence_digests` → Artifacts §12) con **predicates por clase**.
Refinamientos aditivos decididos (decisión registrada en el ledger):
- `formal_exact.differential.status` usa el enum REAL de CP-SAT; `MODEL_INVALID`
  e `INFEASIBLE` son **error de proceso** (no emiten Attestation) — construir
  un predicate con esos status EXPLOTA.
- `execution` carga `timed_out`.
- `property_rule` carga `backend`/`status`/`unsat_core` del backend formal.
- `consensus_replication` SOLO procesos no-modelo (S7) — réplicas con seeds
  pinneados; la concordancia entre modelos es Signal, jamás predicate.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

CpSatStatus = Literal["OPTIMAL", "FEASIBLE", "INFEASIBLE", "MODEL_INVALID", "UNKNOWN"]

_PROCESS_ERROR_STATUSES = frozenset({"INFEASIBLE", "MODEL_INVALID"})


class Proof(BaseModel):
    """Re-validación del checker independiente — vive DENTRO del bundle (§4-iii)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    certificate_ref: str
    checker_id: str
    checker_verdict: str


class Differential(BaseModel):
    """Comparación contra solver exacto independiente (CP-SAT)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    status: CpSatStatus
    objective: float
    reference_objective: float

    @field_validator("status")
    @classmethod
    def _status_es_veredicto_no_error(cls, v: str) -> str:
        if v in _PROCESS_ERROR_STATUSES:
            msg = f"{v}: error de proceso — NO emite Attestation (freeze §4, error ≠ fail)"
            raise ValueError(msg)
        return v


class FormalExactPredicate(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    method: Literal["formal_exact"] = "formal_exact"
    differential: Differential
    proof: Proof | None = None
    """Con proof el techo sube a AL4; sin él, AL3 (freeze §4)."""


class ExecutionCheck(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    passed: bool


class ExecutionEnvironment(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    package: str
    version: str


class ExecutionPredicate(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    method: Literal["execution"] = "execution"
    harness: str
    input_digest: str
    checks: tuple[ExecutionCheck, ...]
    runtime_ms: float
    environment: ExecutionEnvironment
    timed_out: bool = False


class GroundTruthPredicate(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    method: Literal["ground_truth"] = "ground_truth"
    dataset_id: str
    case_id: str
    expected_digest: str
    observed_digest: str
    match: bool
    tolerance: float


class PropertyCheck(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    passed: bool
    examples_run: int
    counterexample: str | None = None


class MetamorphicRelation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    transform_digest: str
    expected_relation: Literal["equal", "scaled", "invariant"]
    held: bool


class PropertyRulePredicate(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    method: Literal["property_rule"] = "property_rule"
    properties: tuple[PropertyCheck, ...] = ()
    relations: tuple[MetamorphicRelation, ...] = ()
    seed: int | None = None
    generator_version: str | None = None
    backend: str | None = None
    status: str | None = None
    unsat_core: str | None = None


class ConsensusLeg(BaseModel):
    """Una pata de consenso multi-backend — freeze §11 (campos multi-backend
    del claim proponente), portados aquí por
    `docs/specs/evidencia-externa.md` §`ConsensusReplicationPredicate`
    (extensión ADITIVA, Fase 1 Sebas). `transpiled_circuit_digest`: el
    circuito rebaseado al gate set nativo del backend (artefacto derivado
    DISTINTO del circuito fuente); `noise_config_digest`: parámetros de
    error efectivos (o `ideal`) canonicalizados — dos corridas con ruido
    distinto no son comparables sin esto."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    seed: int
    backend_id: str
    transpiled_circuit_digest: str
    noise_config_digest: str


class ConsensusReplicationPredicate(BaseModel):
    """Réplicas con seeds pinneados — SOLO procesos no-modelo (S7)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    method: Literal["consensus_replication"] = "consensus_replication"
    replicas: int = Field(ge=2)
    seeds: tuple[int, ...]
    agreement: bool
    legs: tuple[ConsensusLeg, ...] = ()
    """NUEVO, aditivo (spec evidencia-externa.md) — `replicas`/`seeds`/
    `agreement` INTACTOS, ningún campo existente cambia de forma. Vacío por
    default: no dispara el validador de abajo, los tests existentes de este
    predicate siguen verdes sin tocarlos."""

    @model_validator(mode="after")
    def _legs_match_replicas_and_seeds_when_present(
        self,
    ) -> ConsensusReplicationPredicate:
        if not self.legs:
            return self
        if len(self.legs) != self.replicas:
            msg = (
                f"ConsensusReplicationPredicate.legs: {len(self.legs)} patas != "
                f"replicas={self.replicas}"
            )
            raise ValueError(msg)
        leg_seeds = tuple(leg.seed for leg in self.legs)
        if leg_seeds != self.seeds:
            msg = (
                f"ConsensusReplicationPredicate.legs: seeds de las patas {leg_seeds} "
                f"!= seeds={self.seeds}"
            )
            raise ValueError(msg)
        return self


class HumanExpertPredicate(BaseModel):
    """Juicio humano — siempre atribuible (AX1)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    method: Literal["human_expert"] = "human_expert"
    reviewer: str
    decision: str
    rationale: str
    reviewed_digest: str


ClassPredicate = Annotated[
    FormalExactPredicate
    | ExecutionPredicate
    | GroundTruthPredicate
    | PropertyRulePredicate
    | ConsensusReplicationPredicate
    | HumanExpertPredicate,
    Field(discriminator="method"),
]
