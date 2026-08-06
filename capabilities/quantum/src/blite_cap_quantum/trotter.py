"""Evolución temporal por circuito (Trotter-Suzuki) — proponente independiente
del ancla exacta (contrato de independencia S-C §3: este módulo NO importa ni
comparte helpers con `blite_cap_numeric.exact_evolve`).

Convención de sitios: en cada string de Pauli el índice i (de izquierda a
derecha) es el sitio i. Qiskit usa little-endian (el qubit 0 es el carácter
MÁS a la derecha del label), así que cada string se invierte explícitamente
(`label[::-1]`) antes de construir un `Pauli`/`SparsePauliOp` — el índice de
QUBIT sigue siendo el índice de sitio (no se invierte para colocar
compuertas), solo el LABEL de texto se invierte.

Los términos se reagrupan en bloques mutuamente conmutantes, determinista
(orden por string de Pauli, no por el orden de llegada del caller) antes de
construir el `SparsePauliOp`: dentro de un bloque los términos conmutan
exactamente, así que listarlos consecutivos en el operador y dejar que
`PauliEvolutionGate` los aplique en ese orden reproduce la fórmula de
producto por bloques (para el operador de referencia, exactamente 2
bloques) sin depender de cómo el caller haya ordenado `terms`.

**Trampa medida (no documentada por Qiskit):** `PauliEvolutionGate.to_matrix()`
— y por tanto `Statevector.evolve()`/`Operator()` sobre un circuito que
todavía contiene la compuerta SIN decompilar — recomputa la exponencial
EXACTA del operador, ignorando por completo la síntesis de Trotter pedida.
Sobre el circuito sin decompilar, el resultado es idéntico para cualquier
`steps` (el control negativo de §4.3 jamás fallaría — exactamente el
síntoma de "código compartido" que ese test existe para cazar). `transpile`
a compuertas básicas ANTES de construir el `Statevector` fuerza la síntesis
real.
"""

from __future__ import annotations

from typing import Any, cast

# Qiskit no publica stubs completos bajo strict — se silencian SOLO los
# reportes de tipos desconocidos de terceros; las firmas propias de este
# módulo siguen bajo strict.
# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false

_PAULI_ALPHABET = frozenset("IXYZ")
_MIN_SITES = 1
_MAX_SITES = 14
_DEFAULT_STEPS = 16
_DEFAULT_ORDER = 1
_VALID_ORDERS = (1, 2)
_BASIS_GATES = ("rz", "ry", "rx", "h", "cx")


def _is_number(value: Any) -> bool:
    """True si `value` es int/float real — rechaza bool (subclase de int)."""
    return not isinstance(value, bool) and isinstance(value, int | float)


def _validate_n_sites(raw: Any) -> int:
    if isinstance(raw, bool) or not isinstance(raw, int):
        msg = f"TrotterEvolve: n_sites debe ser entero, no {raw!r}"
        raise ValueError(msg)
    if not (_MIN_SITES <= raw <= _MAX_SITES):
        msg = f"TrotterEvolve: n_sites debe estar en [{_MIN_SITES}, {_MAX_SITES}], no {raw}"
        raise ValueError(msg)
    return raw


def _validate_pauli_string(raw: Any, n_sites: int, context: str) -> str:
    if not isinstance(raw, str) or len(raw) != n_sites:
        msg = (
            f"TrotterEvolve: {context}.pauli debe ser un string de longitud "
            f"n_sites={n_sites}, no {raw!r}"
        )
        raise ValueError(msg)
    if not set(raw) <= _PAULI_ALPHABET:
        msg = f"TrotterEvolve: {context}.pauli tiene símbolos fuera de {{I,X,Y,Z}}: {raw!r}"
        raise ValueError(msg)
    return raw


def _validate_terms(raw: Any, n_sites: int) -> list[dict[str, Any]]:
    if not isinstance(raw, list) or not raw:
        msg = "TrotterEvolve: 'terms' (lista no vacía) es requerido"
        raise ValueError(msg)
    validated: list[dict[str, Any]] = []
    for idx, term in enumerate(raw):
        if not isinstance(term, dict):
            msg = f"TrotterEvolve: terms[{idx}] debe ser un objeto, no {term!r}"
            raise ValueError(msg)
        pauli = _validate_pauli_string(term.get("pauli"), n_sites, f"terms[{idx}]")
        coefficient = term.get("coefficient")
        if not _is_number(coefficient):
            msg = (
                f"TrotterEvolve: terms[{idx}].coefficient debe ser numérico, "
                f"no {coefficient!r}"
            )
            raise ValueError(msg)
        validated.append(
            {"pauli": pauli, "coefficient": float(cast("int | float", coefficient))}
        )
    return validated


def _validate_initial_bitstring(raw: Any, n_sites: int) -> str:
    bitstring = raw if raw is not None else "0" * n_sites
    if not isinstance(bitstring, str) or len(bitstring) != n_sites:
        msg = (
            f"TrotterEvolve: initial_bitstring debe ser un string de longitud "
            f"n_sites={n_sites}, no {bitstring!r}"
        )
        raise ValueError(msg)
    if not set(bitstring) <= {"0", "1"}:
        msg = (
            f"TrotterEvolve: initial_bitstring debe usar solo '0'/'1', no {bitstring!r}"
        )
        raise ValueError(msg)
    return bitstring


def _validate_observables(raw: Any, n_sites: int) -> list[dict[str, Any]]:
    if not isinstance(raw, list) or not raw:
        msg = "TrotterEvolve: 'observables' (lista no vacía) es requerido"
        raise ValueError(msg)
    validated: list[dict[str, Any]] = []
    for idx, obs in enumerate(raw):
        if not isinstance(obs, dict):
            msg = f"TrotterEvolve: observables[{idx}] debe ser un objeto, no {obs!r}"
            raise ValueError(msg)
        label = obs.get("label")
        if not isinstance(label, str) or not label:
            msg = (
                f"TrotterEvolve: observables[{idx}].label debe ser un string "
                f"no vacío, no {label!r}"
            )
            raise ValueError(msg)
        pauli = _validate_pauli_string(obs.get("pauli"), n_sites, f"observables[{idx}]")
        validated.append({"label": label, "pauli": pauli})
    return validated


def _validate_time(raw: Any) -> float:
    if not _is_number(raw):
        msg = f"TrotterEvolve: time debe ser numérico, no {raw!r}"
        raise ValueError(msg)
    return float(raw)


def _validate_steps(raw: Any) -> int:
    if isinstance(raw, bool) or not isinstance(raw, int) or raw < 1:
        msg = f"TrotterEvolve: steps debe ser entero >= 1, no {raw!r}"
        raise ValueError(msg)
    return raw


def _validate_order(raw: Any) -> int:
    if isinstance(raw, bool) or raw not in _VALID_ORDERS:
        msg = f"TrotterEvolve: order debe estar en {_VALID_ORDERS}, no {raw!r}"
        raise ValueError(msg)
    return raw


def _paulis_commute(a: str, b: str) -> bool:
    """Dos Pauli strings conmutan sii el número de posiciones donde ambos son
    no-identidad y DISTINTOS es par."""
    mismatches = sum(
        1 for ca, cb in zip(a, b, strict=True) if ca != "I" and cb != "I" and ca != cb
    )
    return mismatches % 2 == 0


def _group_commuting_terms(terms: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    """Agrupa `terms` en bloques mutuamente conmutantes, determinista.

    Ordena por el string de Pauli (no por el orden de llegada del caller) y
    asigna cada término al primer bloque existente con el que conmuta con
    TODOS sus miembros; si ninguno califica, abre un bloque nuevo. Para el
    operador de referencia (acoplamiento de vecinos + campo local, ver
    knowledge/quantum/11 §1.3) esto produce exactamente 2 bloques.
    """
    ordered = sorted(terms, key=lambda term: str(term["pauli"]))
    groups: list[list[dict[str, Any]]] = []
    for term in ordered:
        for group in groups:
            if all(_paulis_commute(term["pauli"], other["pauli"]) for other in group):
                group.append(term)
                break
        else:
            groups.append([term])
    return groups


def trotter_evolve(inputs: dict[str, Any]) -> dict[str, Any]:
    """Evoluciona `psi0` bajo H = Σ coeficiente·Pauli hasta `time` con un
    circuito de Trotter-Suzuki (`PauliEvolutionGate` + `Statevector`).

    Ver el docstring del módulo para la convención de sitios, el reagrupado
    determinista y la trampa de `to_matrix()` que este código evita.
    """
    import hashlib

    import numpy as np
    import qiskit
    from qiskit import QuantumCircuit, qasm3, transpile
    from qiskit.circuit.library import PauliEvolutionGate
    from qiskit.quantum_info import Pauli, SparsePauliOp, Statevector
    from qiskit.synthesis import LieTrotter, SuzukiTrotter

    n_sites = _validate_n_sites(inputs.get("n_sites"))
    terms = _validate_terms(inputs.get("terms"), n_sites)
    time = _validate_time(inputs.get("time"))
    bitstring = _validate_initial_bitstring(inputs.get("initial_bitstring"), n_sites)
    observables = _validate_observables(inputs.get("observables"), n_sites)
    steps = _validate_steps(inputs.get("steps", _DEFAULT_STEPS))
    order = _validate_order(inputs.get("order", _DEFAULT_ORDER))

    groups = _group_commuting_terms(terms)
    labels: list[str] = []
    coefficients: list[float] = []
    for group in groups:
        for term in group:
            labels.append(str(term["pauli"])[::-1])
            coefficients.append(term["coefficient"])
    operator = SparsePauliOp(labels, np.array(coefficients, dtype=complex))

    if order == 1:
        synthesis: Any = LieTrotter(reps=steps)
        method = "lie-trotter"
    else:
        synthesis = SuzukiTrotter(order=2, reps=steps)
        method = "suzuki-2"

    evolution_gate = PauliEvolutionGate(operator, time=time, synthesis=synthesis)
    circuit = QuantumCircuit(n_sites)
    for site, bit in enumerate(bitstring):
        if bit == "1":
            circuit.x(site)
    circuit.append(evolution_gate, range(n_sites))

    # Ver la nota de módulo: sin este transpile, Statevector cae en el atajo
    # EXACTO de to_matrix() y el resultado no dependería de `steps`.
    transpiled = transpile(circuit, basis_gates=list(_BASIS_GATES))
    state = Statevector(transpiled)

    expectations: list[dict[str, Any]] = []
    for obs in observables:
        pauli = Pauli(obs["pauli"][::-1])
        value = float(np.real(state.expectation_value(pauli)))
        expectations.append({"label": obs["label"], "value": value})

    digest = hashlib.sha256(qasm3.dumps(transpiled).encode("utf-8")).hexdigest()

    return {
        "expectations": expectations,
        "norm": float(np.linalg.norm(state.data)),
        "method": method,
        "backend": f"qiskit-{qiskit.__version__}",
        "steps": steps,
        "order": order,
        "circuit_depth": transpiled.depth(),
        "circuit_digest": digest,
    }
