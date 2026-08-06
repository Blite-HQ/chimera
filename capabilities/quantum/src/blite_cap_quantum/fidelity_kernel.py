"""Kernel de fidelidad cuantico por overlap de statevectors (recipe
knowledge/quantum/02-recetario-formulacion-por-reto.md SS2.2/SS2.3;
docs/mejorado/03-research.md R1 — hallazgo tecnico mayor).

**Por que UN producto de matrices y no m^2 circuitos:** el presupuesto de
circuitos de la nota 02 SS2.2 (~18675 evaluaciones, submuestreo a 100-200
filas) aplica a un kernel evaluado POR CIRCUITO (con shots, en hardware o en
un simulador que solo da counts). Con un simulador de statevector el limite
desaparece: cada fila necesita construirse UNA sola vez (`qiskit.quantum_info
.Statevector`), y el kernel completo sale de un solo producto matricial:

    Psi_x (m_x, 2^n) ; Psi_y (m_y, 2^n)
    K = |Psi_x @ Psi_y^dagger|^2          (una multiplicacion, no m_x*m_y
                                            circuitos)

Esto es lo que hace viable correr el dataset COMPLETO (3276 filas) en vez del
submuestreo de la nota 02 (research R1, "DIVERGENCIA con nota 02 SS2.2").

**Feature map:** solo "angle" esta implementado (RY(x_i) por qubit i,
`reps` repeticiones con un anillo de CX entrelazando repeticiones sucesivas
para que `reps > 1` sea genuinamente mas expresivo, no una rotacion
redundante). El manifest NO anuncia otros valores — anunciar un enum que
`invoke` rechaza es la mentira de contrato que el repo ya corrigio una vez
(ver `tool.py::QaoaSolver` backend).

**PSD como DATO, nunca reparado en silencio (recipe SS2.3 / nota 04 SS5.3):**
K = |Psi_x Psi_x^dagger|^2 sobre el MISMO conjunto (self-Gram, `y` ausente)
es PSD por construccion — es un producto de Schur (elemento a elemento) de la
matriz de Gram G = Psi_x Psi_x^dagger (PSD, es un Gram autentico en el
espacio de Hilbert) consigo misma conjugada (tambien PSD): el producto de
Schur de dos matrices PSD es PSD (teorema de Schur). En simulador exacto
`lambda_min` deberia salir ~0 salvo ruido de punto flotante; con `shots` (no
implementado aun en este modulo) si podria caer bajo cero de verdad. El PSD
solo se analiza/repara para el self-Gram (`y` ausente): un kernel rectangular
test-vs-train (`y` provisto, forma distinta a la de `x`) no es la matriz de
Gram de un unico conjunto y no tiene una nocion de PSD bien definida — para
ese caso se reporta `lambda_min=None`, `repaired=False`,
`psd_repair="none"` (el metodo REALMENTE aplicado, nunca lo pedido si no
aplica).
"""

from __future__ import annotations

from typing import Any

# Qiskit no publica stubs completos bajo strict — se silencian SOLO los
# reportes de tipos desconocidos de terceros; las firmas propias de este
# modulo siguen bajo strict.
# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false

_MIN_QUBITS = 1
_MAX_QUBITS = 14
_DEFAULT_REPS = 1
_DEFAULT_PSD_REPAIR = "clip"
_VALID_PSD_REPAIR = ("clip", "none")
_VALID_FEATURE_MAPS = ("angle",)


def _is_number(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, int | float)


def _validate_vectors(raw: Any, name: str, n_qubits: int | None) -> list[list[float]]:
    if not isinstance(raw, list) or not raw:
        msg = f"FidelityKernel: '{name}' (lista no vacia) es requerido"
        raise ValueError(msg)
    width = n_qubits
    validated: list[list[float]] = []
    for i, row in enumerate(raw):
        if not isinstance(row, list) or not row:
            msg = f"FidelityKernel: {name}[{i}] debe ser una lista no vacia, no {row!r}"
            raise ValueError(msg)
        if width is None:
            width = len(row)
            if not (_MIN_QUBITS <= width <= _MAX_QUBITS):
                msg = (
                    f"FidelityKernel: cada vector de '{name}' implica "
                    f"{width} qubits, fuera de [{_MIN_QUBITS}, {_MAX_QUBITS}]"
                )
                raise ValueError(msg)
        elif len(row) != width:
            msg = (
                f"FidelityKernel: {name}[{i}] tiene longitud {len(row)}, "
                f"esperada {width}"
            )
            raise ValueError(msg)
        parsed: list[float] = []
        for j, value in enumerate(row):
            if not _is_number(value):
                msg = (
                    f"FidelityKernel: {name}[{i}][{j}] debe ser numerico, no {value!r}"
                )
                raise ValueError(msg)
            parsed.append(float(value))
        validated.append(parsed)
    return validated


def _validate_feature_map(raw: Any) -> str:
    value = raw if raw is not None else _VALID_FEATURE_MAPS[0]
    if value not in _VALID_FEATURE_MAPS:
        msg = (
            f"FidelityKernel: feature_map debe ser uno de "
            f"{_VALID_FEATURE_MAPS}, no {value!r}"
        )
        raise ValueError(msg)
    return value


def _validate_reps(raw: Any) -> int:
    value = raw if raw is not None else _DEFAULT_REPS
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        msg = f"FidelityKernel: reps debe ser entero >= 1, no {value!r}"
        raise ValueError(msg)
    return value


def _validate_psd_repair(raw: Any) -> str:
    value = raw if raw is not None else _DEFAULT_PSD_REPAIR
    if value not in _VALID_PSD_REPAIR:
        msg = (
            f"FidelityKernel: psd_repair debe ser uno de "
            f"{_VALID_PSD_REPAIR}, no {value!r}"
        )
        raise ValueError(msg)
    return value


def _build_statevectors(vectors: list[list[float]], reps: int) -> Any:
    """Construye Psi (m, 2^n) — una fila por vector de entrada, UNA sola vez
    cada una (nunca un circuito por PAR)."""
    import numpy as np
    from qiskit import QuantumCircuit
    from qiskit.quantum_info import Statevector

    n_qubits = len(vectors[0])
    dim = 2**n_qubits
    psi = np.empty((len(vectors), dim), dtype=complex)
    for row_idx, features in enumerate(vectors):
        circuit = QuantumCircuit(n_qubits)
        for rep in range(reps):
            for qubit, value in enumerate(features):
                circuit.ry(value, qubit)
            # anillo de CX entre repeticiones (no tras la ultima) — sin esto,
            # reps>1 seria una rotacion RY redundante (RY(a) o RY(a) = RY(2a))
            # en vez de una capa genuinamente mas expresiva.
            if rep < reps - 1 and n_qubits > 1:
                for qubit in range(n_qubits):
                    circuit.cx(qubit, (qubit + 1) % n_qubits)
        psi[row_idx] = Statevector(circuit).data
    return psi


def fidelity_kernel(inputs: dict[str, Any]) -> dict[str, Any]:
    """Calcula la matriz de kernel de fidelidad K(a, b) = |<psi(a)|psi(b)>|^2
    entre `x` y `y` (o el Gram simetrico de `x` consigo mismo si `y` esta
    ausente) — ver el docstring del modulo para el algoritmo, el feature map
    y la reparacion PSD."""
    import numpy as np

    x = _validate_vectors(inputs.get("x"), "x", None)
    n_qubits = len(x[0])
    y_raw = inputs.get("y")
    self_gram = y_raw is None
    y = x if self_gram else _validate_vectors(y_raw, "y", n_qubits)

    _validate_feature_map(inputs.get("feature_map"))
    reps = _validate_reps(inputs.get("reps"))
    psd_repair = _validate_psd_repair(inputs.get("psd_repair"))

    psi_x = _build_statevectors(x, reps)
    psi_y = psi_x if self_gram else _build_statevectors(y, reps)

    overlap = psi_x @ psi_y.conj().T
    kernel = np.abs(overlap) ** 2

    lambda_min: float | None = None
    repaired = False
    applied_method = "none"

    if self_gram:
        # Simetria EXACTA bit a bit: (K + K^T)/2 es simetrica en punto
        # flotante porque la suma IEEE-754 es conmutativa (a+b == b+a).
        kernel = (kernel + kernel.T) / 2.0
        eigenvalues = np.linalg.eigvalsh(kernel)
        lambda_min = float(eigenvalues.min())
        if psd_repair == "clip":
            applied_method = "clip"
            eigvals, eigvecs = np.linalg.eigh(kernel)
            clipped = np.clip(eigvals, 0.0, None)
            kernel = (eigvecs * clipped) @ eigvecs.T
            kernel = (kernel + kernel.T) / 2.0
            repaired = True
        else:
            applied_method = "none"

    return {
        "kernel": kernel.tolist(),
        "lambda_min": lambda_min,
        "psd_repair": applied_method,
        "repaired": repaired,
        "n_qubits": n_qubits,
    }
