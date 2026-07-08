"""
Evidence — the auditable form each verification method leaves behind.

knowledge/trust/03-escalera-verificacion-metodos.md SS1.2: evidence is never
an amorphous dict; each method (differential/execution/known_truth/property/
metamorphic/human) has its own shape, discriminated by the `method` field.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

# ── rung 1: differential verification against an independent exact solver ──


class DifferentialReference(BaseModel):
    model_config = ConfigDict(frozen=True)

    solver: str
    version: str
    params_digest: str


class DifferentialEvidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    method: Literal["differential"] = "differential"
    reference: DifferentialReference
    reference_value: float
    candidate_value: float
    gap: float
    tolerance: float
    solver_status: Literal["OPTIMAL", "FEASIBLE", "TIMEOUT"]


# ── rung 2: execution / feasibility (run it for real, observe) ────────────


class ExecutionCheck(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    passed: bool


class ExecutionEnvironment(BaseModel):
    model_config = ConfigDict(frozen=True)

    package: str
    version: str


class ExecutionEvidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    method: Literal["execution"] = "execution"
    harness: str
    input_digest: str
    checks: tuple[ExecutionCheck, ...]
    runtime_ms: float
    environment: ExecutionEnvironment


# ── rung 3: known truth (comparison against a versioned corpus) ───────────


class KnownTruthEvidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    method: Literal["known_truth"] = "known_truth"
    dataset_id: str
    case_id: str
    expected_digest: str
    observed_digest: str
    match: bool
    tolerance: float


# ── rung 4: property-based (Hypothesis) ────────────────────────────────────


class PropertyCheck(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    passed: bool
    examples_run: int
    counterexample: str | None = None


class PropertyEvidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    method: Literal["property"] = "property"
    properties: tuple[PropertyCheck, ...]
    seed: int
    generator_version: str


# ── rung 4: metamorphic relations ──────────────────────────────────────────


class MetamorphicRelation(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    transform_digest: str
    expected_relation: Literal["equal", "scaled", "invariant"]
    held: bool


class MetamorphicEvidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    method: Literal["metamorphic"] = "metamorphic"
    relations: tuple[MetamorphicRelation, ...]


# ── rung 7: human judgment (always attributable — AX1) ─────────────────────


class HumanEvidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    method: Literal["human"] = "human"
    reviewer: str
    decision: str
    rationale: str
    reviewed_digest: str


Evidence = Annotated[
    DifferentialEvidence
    | ExecutionEvidence
    | KnownTruthEvidence
    | PropertyEvidence
    | MetamorphicEvidence
    | HumanEvidence,
    Field(discriminator="method"),
]
