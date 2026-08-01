"""Evolución exacta de un operador hermítico (suma de términos de Pauli) por
diagonalización dispersa — ancla FORMAL_EXACT independiente del lado por
circuito (contrato de independencia S-C §3: este módulo NO importa ni
comparte helpers con `blite_cap_quantum.trotter`).

Convención de sitios (compartida con el lado cuántico, ver ese módulo): en
cada string de Pauli el índice i (de izquierda a derecha) es el sitio i. Esa
convención coincide con el orden natural del producto de Kronecker que este
módulo usa para construir H — por eso este lado NO necesita invertir el
string (a diferencia del lado Qiskit, que es little-endian).

H se construye como Σ coeficiente_k · (producto de Kronecker de matrices de
Pauli 2x2 en orden de sitio), disperso (`scipy.sparse`). Se evoluciona con
`scipy.sparse.linalg.expm_multiply(-i·t·H, psi0)` — sin construir el
propagador denso — y cada observable se evalúa como
`real(vdot(psi, O @ psi))`.
"""

from __future__ import annotations

from typing import Any, cast

# numpy/scipy no publican stubs completos bajo strict — se silencian SOLO los
# reportes de tipos desconocidos de terceros; las firmas propias de este
# módulo siguen bajo strict.
# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false

_PAULI_ALPHABET = frozenset("IXYZ")
_MIN_SITES = 1
_MAX_SITES = 14


def _is_number(value: Any) -> bool:
    """True si `value` es int/float real — rechaza bool (subclase de int)."""
    return not isinstance(value, bool) and isinstance(value, int | float)


def _validate_n_sites(raw: Any) -> int:
    if isinstance(raw, bool) or not isinstance(raw, int):
        msg = f"exact_evolve: n_sites debe ser entero, no {raw!r}"
        raise ValueError(msg)
    if not (_MIN_SITES <= raw <= _MAX_SITES):
        msg = f"exact_evolve: n_sites debe estar en [{_MIN_SITES}, {_MAX_SITES}], no {raw}"
        raise ValueError(msg)
    return raw


def _validate_pauli_string(raw: Any, n_sites: int, context: str) -> str:
    if not isinstance(raw, str) or len(raw) != n_sites:
        msg = (
            f"exact_evolve: {context}.pauli debe ser un string de longitud "
            f"n_sites={n_sites}, no {raw!r}"
        )
        raise ValueError(msg)
    if not set(raw) <= _PAULI_ALPHABET:
        msg = f"exact_evolve: {context}.pauli tiene símbolos fuera de {{I,X,Y,Z}}: {raw!r}"
        raise ValueError(msg)
    return raw


def _validate_terms(raw: Any, n_sites: int) -> list[dict[str, Any]]:
    if not isinstance(raw, list) or not raw:
        msg = "exact_evolve: 'terms' (lista no vacía) es requerido"
        raise ValueError(msg)
    validated: list[dict[str, Any]] = []
    for idx, term in enumerate(raw):
        if not isinstance(term, dict):
            msg = f"exact_evolve: terms[{idx}] debe ser un objeto, no {term!r}"
            raise ValueError(msg)
        pauli = _validate_pauli_string(term.get("pauli"), n_sites, f"terms[{idx}]")
        coefficient = term.get("coefficient")
        if not _is_number(coefficient):
            msg = (
                f"exact_evolve: terms[{idx}].coefficient debe ser numérico, "
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
            f"exact_evolve: initial_bitstring debe ser un string de longitud "
            f"n_sites={n_sites}, no {bitstring!r}"
        )
        raise ValueError(msg)
    if not set(bitstring) <= {"0", "1"}:
        msg = f"exact_evolve: initial_bitstring debe usar solo '0'/'1', no {bitstring!r}"
        raise ValueError(msg)
    return bitstring


def _validate_observables(raw: Any, n_sites: int) -> list[dict[str, Any]]:
    if not isinstance(raw, list) or not raw:
        msg = "exact_evolve: 'observables' (lista no vacía) es requerido"
        raise ValueError(msg)
    validated: list[dict[str, Any]] = []
    for idx, obs in enumerate(raw):
        if not isinstance(obs, dict):
            msg = f"exact_evolve: observables[{idx}] debe ser un objeto, no {obs!r}"
            raise ValueError(msg)
        label = obs.get("label")
        if not isinstance(label, str) or not label:
            msg = (
                f"exact_evolve: observables[{idx}].label debe ser un string "
                f"no vacío, no {label!r}"
            )
            raise ValueError(msg)
        pauli = _validate_pauli_string(obs.get("pauli"), n_sites, f"observables[{idx}]")
        validated.append({"label": label, "pauli": pauli})
    return validated


def _validate_time(raw: Any) -> float:
    if not _is_number(raw):
        msg = f"exact_evolve: time debe ser numérico, no {raw!r}"
        raise ValueError(msg)
    return float(raw)


def exact_evolve(inputs: dict[str, Any]) -> dict[str, Any]:
    """Evoluciona `psi0` bajo H = Σ coeficiente·Pauli hasta `time` y evalúa
    observables, por diagonalización dispersa (`expm_multiply`).

    Ver el docstring del módulo para la convención de sitios y el contrato de
    independencia respecto del lado por circuito.
    """
    import numpy as np
    import scipy
    from scipy import sparse
    from scipy.sparse.linalg import expm_multiply

    n_sites = _validate_n_sites(inputs.get("n_sites"))
    terms = _validate_terms(inputs.get("terms"), n_sites)
    time = _validate_time(inputs.get("time"))
    bitstring = _validate_initial_bitstring(inputs.get("initial_bitstring"), n_sites)
    observables = _validate_observables(inputs.get("observables"), n_sites)

    pauli_matrices = {
        "I": np.array([[1, 0], [0, 1]], dtype=complex),
        "X": np.array([[0, 1], [1, 0]], dtype=complex),
        "Y": np.array([[0, -1j], [1j, 0]], dtype=complex),
        "Z": np.array([[1, 0], [0, -1]], dtype=complex),
    }

    def pauli_operator(pauli: str) -> Any:
        """Producto de Kronecker en orden de sitio (índice i == sitio i)."""
        operator = sparse.csr_matrix(pauli_matrices[pauli[0]])
        for symbol in pauli[1:]:
            operator = sparse.kron(operator, pauli_matrices[symbol], format="csr")
        return operator

    dim = 2**n_sites
    hamiltonian = sparse.csr_matrix((dim, dim), dtype=complex)
    for term in terms:
        hamiltonian = hamiltonian + term["coefficient"] * pauli_operator(term["pauli"])

    psi0 = np.zeros(dim, dtype=complex)
    psi0[int(bitstring, 2)] = 1.0
    psi_t = expm_multiply(-1j * time * hamiltonian, psi0)

    expectations: list[dict[str, Any]] = []
    for obs in observables:
        operator = pauli_operator(obs["pauli"])
        value = float(np.real(np.vdot(psi_t, operator @ psi_t)))
        expectations.append({"label": obs["label"], "value": value})

    return {
        "expectations": expectations,
        "norm": float(np.linalg.norm(psi_t)),
        "method": "expm_multiply",
        "backend": f"scipy-{scipy.__version__}",
    }
