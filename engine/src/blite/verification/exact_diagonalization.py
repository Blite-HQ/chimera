"""
ExactDiagonalizationVerifier — el adapter `formal_exact` del reto C3 (TFIM +
Trotter). Vocabulario §4 / docs/specs/generalidad-retos.md §Contrato-3/4;
matemática y números de oro en knowledge/quantum/11-receta-c3-tfim-trotter.md.

Independencia (S-C §3, receta §2): el proponente evoluciona un CIRCUITO
(RZZ/RX + Qiskit `Statevector`, en `blite_cap_quantum.trotter`); este
verificador evoluciona el OPERADOR por diagonalización EXACTA densa
(`numpy.linalg.eigh`) — ninguna aproximación de Trotter, ningún paso
temporal. La capability hermana `blite.numeric.exact_evolve` (recompute
del mismo operador para otros consumidores) usa Krylov DISPERSO
(`scipy.sparse.linalg.expm_multiply`) — la elección de rutina DENSA aquí es
deliberada, no un antojo de estilo: es la segunda pata de independencia
algorítmica que la spec exige (dos métodos de recompute distintos, no el
mismo método invocado dos veces).

ADR-008: el engine JAMÁS importa un paquete `blite_cap_*` — el
import-linter lo prohíbe. Por eso este módulo reimplementa su propia
diagonalización exacta en vez de reusar la de la capability.

Convención de sitios (receta §1.1, compartida con `blite_cap_numeric.
exact_evolve` — independencia de IMPLEMENTACIÓN, no de convención): en cada
string de Pauli el índice i, de izquierda a derecha, es el sitio i. Esa
convención coincide con el orden natural del producto de Kronecker que este
módulo usa para construir H.

Reglas duras (§Deliverable-1):
- Dimensión > `max_dense_dimension` ⇒ `inconclusive`/AL0/
  `budget_exhausted`, JAMÁS un cambio silencioso de algoritmo (punto 2).
- Norma del estado recomputado que se desvía de 1 más allá de 1e-9 ⇒
  `VerificationProcessError` — un ancla rota es una falla de PROCESO,
  jamás un `fail` del candidato (punto 6).
- `relative_tolerance`/`max_dense_dimension` entran a `verifier_params_digest`
  (C-14, #106): dos corridas con tolerancia o presupuesto distintos jamás
  comparten digest de params.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

# numpy: NO es una dependencia nueva de este módulo — `pandapower>=3.5.4`
# (dependencia DIRECTA de chimera-engine, engine/pyproject.toml) hard-requiere
# numpy, así que ya vive en `uv.lock`. Este import no toca ese lock.
# numpy/scipy no publican stubs completos bajo pyright strict — se silencian
# SOLO los reportes de tipos desconocidos de terceros; las firmas propias de
# este módulo siguen bajo strict (mismo patrón que
# capabilities/numeric/src/blite_cap_numeric/exact_evolve.py).
# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false
import numpy as np
from pydantic import BaseModel, ConfigDict, Field, model_validator

from blite.certificate.canonical import JSONValue, canonicalize
from blite.verification.anchor import AnchorKind
from blite.verification.attestation import Attestation, Verdict, VerifierClass
from blite.verification.claim import claim_view_digest
from blite.verification.context import InvocationContext
from blite.verification.evidence import Differential, FormalExactPredicate
from blite.verification.exact_solver import VerificationProcessError
from blite.verification.verifier import Determinism

_PAULI_ALPHABET = frozenset("IXYZ")
_BIT_ALPHABET = frozenset("01")
_CORRELATOR_LABEL_PREFIX = "ZZ"
"""Regla de agrupación EXPLÍCITA (§Deliverable-1): un label que empieza con
"ZZ" pertenece a la serie correlador ⟨ZᵢZᵢ₊₁⟩; cualquier otro label
pertenece a la serie de un solo sitio ⟨Zᵢ⟩ (u otro observable de un
sitio). No hay heurística implícita — es este prefijo, nada más."""
_NORM_TOLERANCE = 1e-9
_DEFAULT_RELATIVE_TOLERANCE = 0.05
_DEFAULT_MAX_DENSE_DIMENSION = 1024


class SpinTerm(BaseModel):
    """Un término del Hamiltoniano: `coeficiente · (Pauli de N sitios)`."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    pauli: str
    coefficient: float


class SeriesObservable(BaseModel):
    """Un observable de la serie: su `label` (usado SOLO para la regla de
    agrupación) y el string de Pauli que lo define."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    label: str
    pauli: str


class SimulationSeriesClaim(BaseModel):
    """Claim de simulación: «la serie `series` (alineada posicionalmente con
    `observables`) reproduce la evolución de `initial_bitstring` bajo `terms`
    hasta `time`»."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    n_sites: int = Field(ge=1)
    terms: tuple[SpinTerm, ...]
    time: float
    initial_bitstring: str
    observables: tuple[SeriesObservable, ...]
    series: tuple[float, ...]
    canonical_statement: str
    scope: dict[str, Any]

    @model_validator(mode="after")
    def _formas_validas(self) -> SimulationSeriesClaim:
        for idx, term in enumerate(self.terms):
            _validar_pauli(term.pauli, self.n_sites, f"terms[{idx}]")
        if (
            len(self.initial_bitstring) != self.n_sites
            or not set(self.initial_bitstring) <= _BIT_ALPHABET
        ):
            msg = (
                f"initial_bitstring debe ser un string de longitud "
                f"n_sites={self.n_sites} sobre {{0,1}}, no "
                f"{self.initial_bitstring!r}"
            )
            raise ValueError(msg)
        if not self.observables:
            msg = "observables no puede estar vacío"
            raise ValueError(msg)
        for idx, obs in enumerate(self.observables):
            _validar_pauli(obs.pauli, self.n_sites, f"observables[{idx}]")
        if len(self.series) != len(self.observables):
            msg = (
                f"series de largo {len(self.series)} no coincide con "
                f"observables de largo {len(self.observables)} — la "
                "alineación posicional candidata↔observable está rota"
            )
            raise ValueError(msg)
        return self


def _validar_pauli(pauli: str, n_sites: int, context: str) -> None:
    if len(pauli) != n_sites or not set(pauli) <= _PAULI_ALPHABET:
        msg = (
            f"{context}.pauli debe tener longitud n_sites={n_sites} sobre "
            f"{{I,X,Y,Z}}, no {pauli!r}"
        )
        raise ValueError(msg)


def relative_series_error(
    candidate: tuple[float, ...], reference: tuple[float, ...]
) -> float:
    """Definición congelada de error relativo (receta §4.1):

    `err(candidata, referencia) = max_i|cand_i - ref_i| / max(max_i|ref_i|, ε)`
    con ε = 1e-12. Es una cota L∞ a la ESCALA de la serie de referencia —
    insensible a que la serie cruce cero (un criterio por-elemento estaría
    mal planteado ahí, receta §4.1) y estrictamente más informativa que un
    promedio, que escondería un sitio malo entre muchos buenos.
    """
    diffs = tuple(abs(c - r) for c, r in zip(candidate, reference, strict=True))
    scale = max((abs(r) for r in reference), default=0.0)
    return max(diffs, default=0.0) / max(scale, 1e-12)


def _group_by_label(
    observables: tuple[SeriesObservable, ...], series: tuple[float, ...]
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    """Parte `series` en (serie de un sitio, serie correlador) según la
    regla EXPLÍCITA de `_CORRELATOR_LABEL_PREFIX`. Devuelve tuplas vacías
    para el grupo ausente — el llamador decide si un grupo vacío se anota."""
    singles = tuple(
        value
        for obs, value in zip(observables, series, strict=True)
        if not obs.label.startswith(_CORRELATOR_LABEL_PREFIX)
    )
    correlators = tuple(
        value
        for obs, value in zip(observables, series, strict=True)
        if obs.label.startswith(_CORRELATOR_LABEL_PREFIX)
    )
    return singles, correlators


def _pauli_matrix(symbol: str) -> Any:
    if symbol == "I":
        return np.eye(2, dtype=complex)
    if symbol == "X":
        return np.array([[0, 1], [1, 0]], dtype=complex)
    if symbol == "Y":
        return np.array([[0, -1j], [1j, 0]], dtype=complex)
    return np.array([[1, 0], [0, -1]], dtype=complex)  # "Z"


def _pauli_operator(pauli: str) -> Any:
    """Producto de Kronecker en orden de sitio (índice i == sitio i,
    izquierda a derecha — receta §1.1)."""
    operator = _pauli_matrix(pauli[0])
    for symbol in pauli[1:]:
        operator = np.kron(operator, _pauli_matrix(symbol))
    return operator


def _dense_hamiltonian(terms: tuple[SpinTerm, ...], n_sites: int) -> Any:
    dim = 2**n_sites
    hamiltonian = np.zeros((dim, dim), dtype=complex)
    for term in terms:
        hamiltonian = hamiltonian + term.coefficient * _pauli_operator(term.pauli)
    return hamiltonian


def _evolve(hamiltonian: Any, psi0: Any, time: float) -> Any:
    """`exp(-i·H·t)·ψ₀` por eigh denso: sin Trotter, sin paso temporal —
    el ancla FORMAL_EXACT (`anchor_kind: solver`)."""
    eigenvalues, eigenvectors = np.linalg.eigh(hamiltonian)
    coefficients = eigenvectors.conj().T @ psi0
    phases = np.exp(-1j * eigenvalues * time)
    return eigenvectors @ (phases * coefficients)


def _expectation(operator: Any, psi: Any) -> float:
    return float(np.real(np.vdot(psi, operator @ psi)))


def _default_binary_digest() -> str:
    return hashlib.sha256(f"numpy-eigh-{np.__version__}".encode()).hexdigest()


def claim_digest_of(claim: SimulationSeriesClaim) -> str:
    """Delegación al helper común (§7 del anexo) — un solo lugar computa la
    vista claim↔digest."""
    return claim_view_digest(claim.canonical_statement, claim.scope)


@dataclass(frozen=True)
class ExactDiagonalizationVerifier:
    """Adapter de la clase `formal_exact`: recomputa la evolución exacta del
    MISMO Hamiltoniano declarado por el claim (diagonalización densa,
    `numpy.linalg.eigh`) y contrasta contra la serie candidata."""

    verifier_id: str
    independence_group: str
    anchor_digest: str
    relative_tolerance: float = _DEFAULT_RELATIVE_TOLERANCE
    max_dense_dimension: int = _DEFAULT_MAX_DENSE_DIMENSION
    verifier_binary_digest: str = field(default_factory=_default_binary_digest)

    # Campos de instancia (init=False) y no ClassVar: el Protocol `Verifier`
    # los declara como atributos de instancia — pyright exige que coincidan
    # (mismo patrón que exact_solver.py).
    verifier_class: VerifierClass = field(default="formal_exact", init=False)
    anchor_kind: AnchorKind = field(default="solver", init=False)
    determinism: Determinism = field(default="deterministic", init=False)

    @property
    def _params(self) -> dict[str, JSONValue]:
        return {
            "routine": "dense-eigh-v1",
            "site_order": "left-to-right",
            "relative_tolerance": self.relative_tolerance,
            "max_dense_dimension": self.max_dense_dimension,
        }

    @property
    def verifier_params_digest(self) -> str:
        return hashlib.sha256(canonicalize(self._params)).hexdigest()

    def verify(self, claim: Any, ctx: InvocationContext) -> Attestation:
        if not isinstance(claim, SimulationSeriesClaim):
            msg = f"claim {type(claim).__name__} no es un SimulationSeriesClaim"
            raise VerificationProcessError(msg)

        dimension = 2**claim.n_sites
        if dimension > self.max_dense_dimension:
            return self._inconclusive_budget_exhausted(claim, ctx)

        hamiltonian = _dense_hamiltonian(claim.terms, claim.n_sites)
        psi0 = np.zeros(dimension, dtype=complex)
        psi0[int(claim.initial_bitstring, 2)] = 1.0
        psi_t = _evolve(hamiltonian, psi0, claim.time)

        norm = float(np.linalg.norm(psi_t))
        if abs(norm - 1.0) > _NORM_TOLERANCE:
            # Ancla rota (unitariedad violada) es una falla de PROCESO — el
            # recompute mismo es defectuoso, jamás se disfraza de `fail`
            # sobre el candidato (§Deliverable-1 punto 6).
            msg = (
                f"norma del estado recomputado {norm} se desvía de 1 más "
                f"allá de {_NORM_TOLERANCE} — ancla rota, no un fail del "
                "candidato"
            )
            raise VerificationProcessError(msg)

        reference_series = tuple(
            _expectation(_pauli_operator(obs.pauli), psi_t) for obs in claim.observables
        )

        candidate_singles, candidate_correlators = _group_by_label(
            claim.observables, claim.series
        )
        reference_singles, reference_correlators = _group_by_label(
            claim.observables, reference_series
        )

        errors: list[float] = []
        if reference_singles:
            errors.append(relative_series_error(candidate_singles, reference_singles))
        if reference_correlators:
            errors.append(
                relative_series_error(candidate_correlators, reference_correlators)
            )
        worst_error = max(errors)
        verdict: Verdict = "pass" if worst_error <= self.relative_tolerance else "fail"

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
            # objective/reference_objective cargan (peor error relativo
            # observado, 0.0 = concordancia perfecta) en vez de un escalar
            # único: este claim no tiene UN objetivo escalar (son DOS series
            # con posiblemente dos errores distintos) — `pass ⟺ objective <=
            # relative_tolerance` mantiene el par de campos legible sin
            # inventar un tercer campo nuevo en `Differential`.
            predicate=FormalExactPredicate(
                differential=Differential(
                    status="EXACT_DIAGONALIZATION",
                    objective=worst_error,
                    reference_objective=0.0,
                    relative_tolerance=self.relative_tolerance,
                )
            ),
            issued_at=datetime.now(UTC),
        )

    def _inconclusive_budget_exhausted(
        self, claim: SimulationSeriesClaim, ctx: InvocationContext
    ) -> Attestation:
        """Rehúso HONESTO (§Deliverable-1 punto 2): sin presupuesto denso
        suficiente, el verificador se abstiene con AL0/`budget_exhausted` en
        vez de cambiar de algoritmo en silencio (p. ej. caer a disperso) —
        eso sería exactamente el tipo de sustitución que rompe la
        independencia algorítmica que esta clase de verificador promete.
        `anchor_digest=None`: el freeze (`_letra_del_freeze`) solo exige
        ancla para veredictos pass/fail, nunca para `inconclusive`."""
        return Attestation(
            verifier_id=self.verifier_id,
            verifier_class=self.verifier_class,
            anchor_kind=self.anchor_kind,
            level="AL0",
            verdict="inconclusive",
            inconclusive_reason="budget_exhausted",
            scope=claim.scope,
            independence_group=self.independence_group,
            run_id=ctx.run_id,
            claim_digest=claim_digest_of(claim),
            verifier_binary_digest=self.verifier_binary_digest,
            verifier_params_digest=self.verifier_params_digest,
            anchor_digest=None,
            predicate=FormalExactPredicate(
                differential=Differential(
                    status="EXACT_DIAGONALIZATION",
                    objective=0.0,
                    reference_objective=0.0,
                    relative_tolerance=self.relative_tolerance,
                )
            ),
            issued_at=datetime.now(UTC),
        )
