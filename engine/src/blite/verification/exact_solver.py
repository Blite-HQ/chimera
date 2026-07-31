"""
ExactSolverVerifier — el adapter `formal_exact` del puerto Verifier (nota 10).

Verificación diferencial contra CP-SAT (OR-Tools): no confía en el número que
reportó el proponente — recomputa el objetivo del candidato, resuelve la MISMA
instancia de forma exacta e independiente, y compara. Tres reglas duras:

- `error` ≠ `fail` (§1.2): `INFEASIBLE`/`MODEL_INVALID`/contradicción son
  fallas del proceso — levantan `VerificationProcessError`, jamás emiten
  Attestation. Un candidato MEJOR que el óptimo probado es contradicción
  fail-loud (el modelo del verificador difiere del objetivo real).
- `FEASIBLE` por presupuesto agotado es `inconclusive` para optimalidad —
  es cota, no ancla (§1.3). `UNKNOWN` idem (sin incumbente: el campo
  `reference_objective` queda en 0).
- Determinismo reproducible (§1.4): `workers=1`, seed fija,
  `max_deterministic_time` (jamás tiempo de reloj) y ruptura de simetría
  `x_0 = 0`. Todo va al `verifier_params_digest` — la corrida es replayable.

Caso demo (§1.5): Max-Cut con pesos ENTEROS ⇒ comparación exacta, tolerancia
cero. El escalado float de QUBO general queda fuera hasta que un claim real
lo necesite.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from importlib import metadata
from typing import Any

from ortools.sat.python import cp_model
from pydantic import BaseModel, ConfigDict, Field, model_validator

from blite.certificate.canonical import JSONValue, canonicalize
from blite.verification.anchor import AnchorKind
from blite.verification.attestation import Attestation, Verdict, VerifierClass
from blite.verification.claim import claim_view_digest
from blite.verification.context import InvocationContext
from blite.verification.evidence import (
    CpSatStatus,
    Differential,
    FormalExactPredicate,
)
from blite.verification.verifier import Determinism

_RANDOM_SEED = 1
_DEFAULT_MAX_DETERMINISTIC_TIME = 60.0

_STATUS_NAMES: dict[int, CpSatStatus] = {
    int(cp_model.OPTIMAL): "OPTIMAL",
    int(cp_model.FEASIBLE): "FEASIBLE",
    int(cp_model.INFEASIBLE): "INFEASIBLE",
    int(cp_model.MODEL_INVALID): "MODEL_INVALID",
    int(cp_model.UNKNOWN): "UNKNOWN",
}


class VerificationProcessError(RuntimeError):
    """Falla del PROCESO de verificación — jamás se disfraza de verdict."""


class MaxCutInstance(BaseModel):
    """Instancia Max-Cut con pesos enteros (el caso exacto del demo, §1.5)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    n_nodes: int = Field(ge=1)
    edges: tuple[tuple[int, int, int], ...]

    @model_validator(mode="after")
    def _aristas_dentro_del_grafo(self) -> MaxCutInstance:
        for u, v, _w in self.edges:
            if not (0 <= u < self.n_nodes and 0 <= v < self.n_nodes):
                msg = f"arista ({u},{v}) fuera del rango [0,{self.n_nodes})"
                raise ValueError(msg)
            if u == v:
                msg = f"lazo ({u},{u}): un self-loop nunca aporta al corte"
                raise ValueError(msg)
        return self


class OptimalityClaim(BaseModel):
    """Claim de optimalidad: «la asignación `x` es óptima para la instancia»."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    instance: MaxCutInstance
    assignment: tuple[int, ...]
    claimed_objective: int | None = None
    canonical_statement: str
    scope: dict[str, Any]

    @model_validator(mode="after")
    def _asignacion_valida(self) -> OptimalityClaim:
        if len(self.assignment) != self.instance.n_nodes:
            msg = (
                f"asignación de largo {len(self.assignment)} para "
                f"{self.instance.n_nodes} nodos"
            )
            raise ValueError(msg)
        if not set(self.assignment) <= {0, 1}:
            msg = "la asignación debe ser binaria (0/1)"
            raise ValueError(msg)
        return self


def cut_value(
    assignment: tuple[int, ...], edges: tuple[tuple[int, int, int], ...]
) -> int:
    """Recompute directo del objetivo — paso 1 del diferencial (§1.1)."""
    return sum(w for u, v, w in edges if assignment[u] != assignment[v])


def map_optimality_verdict(
    status: CpSatStatus, *, candidate: int, reference: int
) -> Verdict:
    """El mapeo exacto `(status × comparación) → verdict` para claims de
    optimalidad (§1.2). Error de proceso levanta — no hay verdict."""
    if status in ("INFEASIBLE", "MODEL_INVALID"):
        msg = (
            f"{status}: falla del verificador, no del candidato — hay un "
            "candidato en mano, el problema no puede ser infactible"
        )
        raise VerificationProcessError(msg)
    if status == "OPTIMAL":
        if candidate > reference:
            msg = (
                f"contradicción: candidato {candidate} MEJOR que el óptimo "
                f"probado {reference} — el modelo del verificador difiere "
                "del objetivo real; jamás pass silencioso"
            )
            raise VerificationProcessError(msg)
        return "pass" if candidate == reference else "fail"
    return "inconclusive"  # FEASIBLE (cota, no ancla) | UNKNOWN


def _default_binary_digest() -> str:
    version = metadata.version("ortools")
    return hashlib.sha256(f"ortools-cpsat-{version}".encode()).hexdigest()


def claim_digest_of(claim: OptimalityClaim) -> str:
    """Delegación al helper común (§7) — un solo lugar computa la vista."""
    return claim_view_digest(claim.canonical_statement, claim.scope)


@dataclass(frozen=True)
class ExactSolverVerifier:
    """Adapter de la clase `formal_exact`: contrasta el claim contra CP-SAT
    exacto e independiente."""

    verifier_id: str
    independence_group: str
    anchor_digest: str
    verifier_binary_digest: str = field(default_factory=_default_binary_digest)
    max_deterministic_time: float = _DEFAULT_MAX_DETERMINISTIC_TIME

    # Campos de instancia (init=False) y no ClassVar: el Protocol `Verifier`
    # los declara como atributos de instancia — pyright exige que coincidan.
    verifier_class: VerifierClass = field(default="formal_exact", init=False)
    anchor_kind: AnchorKind = field(default="solver", init=False)
    determinism: Determinism = field(default="deterministic", init=False)

    @property
    def _params(self) -> dict[str, JSONValue]:
        return {
            "formulation": "maxcut-xor-linearization-v1",
            "num_search_workers": 1,
            "random_seed": _RANDOM_SEED,
            "max_deterministic_time": self.max_deterministic_time,
            "symmetry_breaking": "x0=0",
            "abs_tol": 0,
        }

    @property
    def verifier_params_digest(self) -> str:
        return hashlib.sha256(canonicalize(self._params)).hexdigest()

    def verify(self, claim: Any, ctx: InvocationContext) -> Attestation:
        if not isinstance(claim, OptimalityClaim):
            msg = f"claim {type(claim).__name__} no es un OptimalityClaim"
            raise VerificationProcessError(msg)

        candidate = cut_value(claim.assignment, claim.instance.edges)
        # La spec (§1.1 paso 1) permite fallar la energía mentida SIN resolver,
        # pero el Differential congelado exige un `status` real de CP-SAT —
        # saltarse el solve obligaría a fabricar evidencia. Se resuelve siempre
        # (el costo lo acota max_deterministic_time); el short-circuit queda
        # para la discusión de freeze de los refinamientos del evidence
        # (nota 10 §4).
        status, reference = self._solve_reference(claim.instance)
        verdict = map_optimality_verdict(
            status, candidate=candidate, reference=reference
        )
        # Paso 1 (§1.1): el recompute desmiente el número reportado ⇒ fail,
        # aunque la asignación fuera óptima — el claim afirmó un valor falso.
        is_lied_energy = (
            claim.claimed_objective is not None and claim.claimed_objective != candidate
        )
        if is_lied_energy:
            verdict = "fail"

        return Attestation(
            verifier_id=self.verifier_id,
            verifier_class=self.verifier_class,
            anchor_kind=self.anchor_kind,
            level="AL3" if verdict != "inconclusive" else "AL0",
            verdict=verdict,
            inconclusive_reason=(
                # Presupuesto DETERMINISTA agotado — jamás reloj de pared (§1.4)
                "budget_exhausted" if verdict == "inconclusive" else None
            ),
            scope=claim.scope,
            independence_group=self.independence_group,
            run_id=ctx.run_id,
            claim_digest=claim_digest_of(claim),
            verifier_binary_digest=self.verifier_binary_digest,
            verifier_params_digest=self.verifier_params_digest,
            anchor_digest=self.anchor_digest,
            predicate=FormalExactPredicate(
                differential=Differential(
                    status=status,
                    objective=candidate,
                    reference_objective=reference,
                )
            ),
            issued_at=datetime.now(UTC),
        )

    def _solve_reference(self, instance: MaxCutInstance) -> tuple[CpSatStatus, int]:
        """Solve exacto de referencia — formulación XOR linealizada (§1.5)."""
        model = cp_model.CpModel()
        x = [model.new_bool_var(f"x{i}") for i in range(instance.n_nodes)]
        model.add(x[0] == 0)  # ruptura de simetría: asignación canónica (§1.4)

        objective_terms: list[Any] = []
        for k, (u, v, w) in enumerate(instance.edges):
            y = model.new_bool_var(f"y{k}")
            # Las 4 restricciones fuerzan y == x_u XOR x_v sobre binarias —
            # modelo exacto y agnóstico al signo del peso (§1.5).
            model.add(y <= x[u] + x[v])
            model.add(y <= 2 - x[u] - x[v])
            model.add(y >= x[u] - x[v])
            model.add(y >= x[v] - x[u])
            objective_terms.append(w * y)
        model.maximize(sum(objective_terms))

        solver = cp_model.CpSolver()
        solver.parameters.num_search_workers = 1
        solver.parameters.random_seed = _RANDOM_SEED
        solver.parameters.max_deterministic_time = self.max_deterministic_time
        status = _STATUS_NAMES[int(solver.solve(model))]

        if status in ("INFEASIBLE", "MODEL_INVALID"):
            msg = f"{status} construyendo la referencia: bug de modelado, no verdict"
            raise VerificationProcessError(msg)
        has_incumbent = status in ("OPTIMAL", "FEASIBLE")
        reference = round(solver.objective_value) if has_incumbent else 0
        return status, reference
