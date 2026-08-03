"""ExactDiagonalizationVerifier (TFIM + Trotter, C3) — el adapter `formal_exact`
del reto 3. Vocabulario §4 / docs/specs/generalidad-retos.md §Contrato-3/4;
matemática y números de oro en knowledge/quantum/11-receta-c3-tfim-trotter.md
§1.1 (convención), §4.1 (definición de error relativo), §4.2/§4.3 (malla y
control negativo).

El helper `_dense_reference` reimplementa la diagonalización densa DESDE
CERO en este archivo de test (no importa nada de `exact_diagonalization`
salvo el propio verificador y sus tipos) — si este helper y el módulo bajo
prueba concuerdan, ninguno de los dos tiene un bug de convención compartido
por accidente. Es la misma disciplina de independencia que S-C §3 exige
entre proponente y verificador, aplicada aquí entre el test y el código.
"""

from __future__ import annotations

import hashlib
from typing import Any

# numpy/scipy no publican stubs completos bajo pyright strict — se silencian
# SOLO los reportes de tipos desconocidos de terceros (mismo patrón que
# engine/src/blite/verification/exact_diagonalization.py).
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false
import numpy as np
import pytest
from pydantic import ValidationError

from blite.certificate.canonical import JSONValue, canonicalize
from blite.verification.attestation import Attestation
from blite.verification.context import InvocationContext
from blite.verification.evidence import Differential, FormalExactPredicate
from blite.verification.exact_diagonalization import (
    ExactDiagonalizationVerifier,
    SeriesObservable,
    SimulationSeriesClaim,
    SpinTerm,
)
from blite.verification.exact_solver import VerificationProcessError
from blite.verification.verifier import Verifier

CTX = InvocationContext(
    run_id="run:test", actor_id="service:runtime", domain_id="dom:test"
)
ANCHOR_DIGEST = hashlib.sha256(b"anchor:dense-eigh-reference-v1").hexdigest()

# ── Números de oro (receta §4.2) ─────────────────────────────────────────
#
# Recomputados en vivo desde el corpus C3 (corrección de la coordinación,
# 2026-08-01, 9 decimales) — confirmados aquí de forma INDEPENDIENTE con dos
# rutas numéricas propias (numpy.linalg.eigh denso y scipy.sparse.linalg.
# expm_multiply disperso) que concuerdan a 8 decimales entre sí.
#
# Hecho físico (receta §5.3, precisado): el valor de BORDE ⟨Z₀⟩ SÍ es
# independiente de N (el cono de luz de Lieb-Robinson a t=1 no distingue
# cadenas de distinto largo desde el borde). El valor de BULK profundo
# (max_i|⟨Zᵢ⟩| en el sitio más lejano de cualquier borde) NO lo es para
# N=6: sus sitios centrales están a distancia 2 de AMBOS bordes (nunca a
# distancia ≥3), así que jamás alcanzan el valor convergido 0.868053451 que
# sí alcanzan N=8/12 — es un hecho de tamaño finito, no redondeo.
GOLDEN_Z0: dict[tuple[int, float], float] = {
    (6, 0.5): 0.672315358,
    (6, 1.0): -0.033021664,
    (6, 2.0): -0.436531883,
    (8, 0.5): 0.672315358,
    (8, 1.0): -0.033021664,
    (8, 2.0): -0.436531883,
}
GOLDEN_ZZ01: dict[tuple[int, float], float] = {
    (6, 0.5): 0.655737403,
    (6, 1.0): 0.434250542,
    (6, 2.0): 0.479045353,
    (8, 0.5): 0.655737403,
    (8, 1.0): 0.434250562,
    (8, 2.0): 0.479050526,
}
GOLDEN_MAX_Z: dict[tuple[int, float], float] = {
    (6, 0.5): 0.868022662,
    (6, 1.0): 0.342568234,
    (6, 2.0): 0.436531883,
    (8, 0.5): 0.868053451,
    (8, 1.0): 0.343341166,
    (8, 2.0): 0.436531883,
}

_PAULI = {
    "I": np.eye(2, dtype=complex),
    "X": np.array([[0, 1], [1, 0]], dtype=complex),
    "Y": np.array([[0, -1j], [1j, 0]], dtype=complex),
    "Z": np.array([[1, 0], [0, -1]], dtype=complex),
}


def _operator(pauli: str) -> Any:
    op = _PAULI[pauli[0]]
    for symbol in pauli[1:]:
        op = np.kron(op, _PAULI[symbol])
    return op


def _dense_reference(claim: SimulationSeriesClaim) -> tuple[float, ...]:
    """ED independiente y completa sobre CUALQUIER claim (no solo TFIM) —
    ver docstring del módulo."""
    dim = 2**claim.n_sites
    hamiltonian = np.zeros((dim, dim), dtype=complex)
    for term in claim.terms:
        hamiltonian = hamiltonian + term.coefficient * _operator(term.pauli)
    eigenvalues, eigenvectors = np.linalg.eigh(hamiltonian)
    psi0 = np.zeros(dim, dtype=complex)
    psi0[int(claim.initial_bitstring, 2)] = 1.0
    coefficients = eigenvectors.conj().T @ psi0
    psi_t = eigenvectors @ (np.exp(-1j * eigenvalues * claim.time) * coefficients)
    return tuple(
        float(np.real(np.vdot(psi_t, _operator(obs.pauli) @ psi_t)))
        for obs in claim.observables
    )


def _tfim_terms(n_sites: int, h: float, j: float = 1.0) -> tuple[SpinTerm, ...]:
    """H = -J·Σ ZᵢZᵢ₊₁ - h·Σ Xᵢ, cadena abierta (receta §1.1)."""
    terms: list[SpinTerm] = []
    for i in range(n_sites - 1):
        pauli = "".join("Z" if k in (i, i + 1) else "I" for k in range(n_sites))
        terms.append(SpinTerm(pauli=pauli, coefficient=-j))
    for i in range(n_sites):
        pauli = "".join("X" if k == i else "I" for k in range(n_sites))
        terms.append(SpinTerm(pauli=pauli, coefficient=-h))
    return tuple(terms)


def _z_observable(n_sites: int, site: int) -> SeriesObservable:
    pauli = "".join("Z" if k == site else "I" for k in range(n_sites))
    return SeriesObservable(label=f"Z{site}", pauli=pauli)


def _zz_observable(n_sites: int, site: int) -> SeriesObservable:
    pauli = "".join("Z" if k in (site, site + 1) else "I" for k in range(n_sites))
    return SeriesObservable(label=f"ZZ{site}", pauli=pauli)


def _tfim_observables(n_sites: int) -> tuple[SeriesObservable, ...]:
    return tuple(_z_observable(n_sites, i) for i in range(n_sites)) + tuple(
        _zz_observable(n_sites, i) for i in range(n_sites - 1)
    )


def _tfim_claim(
    n_sites: int, h: float, series: tuple[float, ...]
) -> SimulationSeriesClaim:
    return SimulationSeriesClaim(
        n_sites=n_sites,
        terms=_tfim_terms(n_sites, h),
        time=1.0,
        initial_bitstring="0" * n_sites,
        observables=_tfim_observables(n_sites),
        series=series,
        canonical_statement="la serie Trotter reproduce la ED dentro de 5%",
        scope={"n_sites": n_sites, "h": h},
    )


def _exact_claim(n_sites: int, h: float) -> SimulationSeriesClaim:
    """El claim cuya `series` ES la ED — construye el esqueleto, recomputa
    la referencia con `_dense_reference`, y la reinyecta como candidata."""
    placeholder = tuple(0.0 for _ in range(2 * n_sites - 1))
    skeleton = _tfim_claim(n_sites, h, placeholder)
    reference = _dense_reference(skeleton)
    return _tfim_claim(n_sites, h, reference)


def make_verifier(**overrides: Any) -> ExactDiagonalizationVerifier:
    params: dict[str, Any] = {
        "verifier_id": "verifier:exact-diagonalization-tfim",
        "independence_group": "leg-formal-ed",
        "anchor_digest": ANCHOR_DIGEST,
    }
    params.update(overrides)
    return ExactDiagonalizationVerifier(**params)


def differential_of(att: Attestation) -> Differential:
    """Narrowing del union ClassPredicate a la evidencia formal_exact."""
    assert isinstance(att.predicate, FormalExactPredicate)
    return att.predicate.differential


class TestNumerosDeOro:
    """Receta §4.2 — el ED recomputado debe reproducir estos valores a
    1e-6. Ver el comentario de `GOLDEN_MAX_Z` para la corrección N=6."""

    @pytest.mark.parametrize(
        "n_sites,h",
        [(6, 0.5), (6, 1.0), (6, 2.0), (8, 0.5), (8, 1.0), (8, 2.0)],
    )
    def test_referencia_reproduce_los_numeros_de_oro(
        self, n_sites: int, h: float
    ) -> None:
        placeholder = tuple(0.0 for _ in range(2 * n_sites - 1))
        claim = _tfim_claim(n_sites, h, placeholder)
        reference = _dense_reference(claim)

        z_series = reference[:n_sites]
        zz_series = reference[n_sites:]

        assert z_series[0] == pytest.approx(GOLDEN_Z0[(n_sites, h)], abs=1e-6)
        assert zz_series[0] == pytest.approx(GOLDEN_ZZ01[(n_sites, h)], abs=1e-6)
        assert max(abs(v) for v in z_series) == pytest.approx(
            GOLDEN_MAX_Z[(n_sites, h)], abs=1e-6
        )


class TestVeredictoPass:
    def test_serie_igual_a_la_ed_pasa(self) -> None:
        claim = _exact_claim(8, 1.0)
        att = make_verifier().verify(claim, CTX)

        assert att.verdict == "pass"
        assert att.level == "AL3"
        assert att.anchor_digest == ANCHOR_DIGEST
        diff = differential_of(att)
        assert diff.status == "EXACT_DIAGONALIZATION"
        assert diff.relative_tolerance == 0.05
        assert diff.objective == pytest.approx(0.0, abs=1e-9)
        assert diff.reference_objective == 0.0


class TestControlDeDosSeries:
    """Receta §4.3: en h/J=0.5 (con Trotter r=2) la serie ⟨Zᵢ⟩ pasaría sola
    (0.04569 < 0.05) mientras el correlador ⟨ZᵢZᵢ₊₁⟩ excede el 5%
    (0.07867) — anotar una sola serie daría un falso pass. Esta prueba
    fuerza esa MISMA forma directamente sobre la ED (no reproduce los
    números de Trotter r=2 letra a letra — no hace falta: basta con que Z
    quede dentro y ZZ quede fuera para cazar un verificador de una sola
    serie)."""

    def test_solo_la_serie_zz_excede_5_por_ciento_falla(self) -> None:
        n_sites, h = 8, 0.5
        placeholder = tuple(0.0 for _ in range(2 * n_sites - 1))
        reference = _dense_reference(_tfim_claim(n_sites, h, placeholder))
        z_series = reference[:n_sites]
        zz_series = list(reference[n_sites:])
        scale = max(abs(v) for v in zz_series)
        zz_series[0] += 0.10 * scale  # 10% > 5% de tolerancia sobre L∞
        perturbed = z_series + tuple(zz_series)

        claim = _tfim_claim(n_sites, h, perturbed)
        att = make_verifier().verify(claim, CTX)

        assert att.verdict == "fail"
        assert differential_of(att).objective > 0.05


class TestPresupuestoAgotado:
    """N=12 ⇒ dimensión 4096 > max_dense_dimension=1024 (default). El
    verificador se abstiene HONESTAMENTE en vez de cambiar de algoritmo
    (p. ej. caer a disperso) en silencio."""

    def test_dimension_excede_max_dense_dimension_es_inconclusive(self) -> None:
        n_sites = 12
        placeholder = tuple(0.0 for _ in range(2 * n_sites - 1))
        claim = _tfim_claim(n_sites, 1.0, placeholder)

        att = make_verifier().verify(claim, CTX)

        assert att.verdict == "inconclusive"
        assert att.level == "AL0"
        assert att.inconclusive_reason == "budget_exhausted"
        assert att.anchor_digest is None


class TestDeterminismo:
    def test_dos_corridas_identicas_salvo_issued_at(self) -> None:
        claim = _exact_claim(6, 1.0)
        verifier = make_verifier()

        a = verifier.verify(claim, CTX).model_dump(exclude={"issued_at"})
        b = verifier.verify(claim, CTX).model_dump(exclude={"issued_at"})

        assert a == b


class TestParamsDigest:
    """C-14 (#106), literal: la tolerancia y el presupuesto denso entran al
    `verifier_params_digest` — dos corridas con cualquiera de los dos
    distinto jamás comparten digest."""

    def test_cambia_con_relative_tolerance(self) -> None:
        base = make_verifier()
        distinto = make_verifier(relative_tolerance=0.10)

        assert base.verifier_params_digest != distinto.verifier_params_digest

    def test_cambia_con_max_dense_dimension(self) -> None:
        base = make_verifier()
        distinto = make_verifier(max_dense_dimension=2048)

        assert base.verifier_params_digest != distinto.verifier_params_digest


class TestAtributosDelPuertoYProtocolo:
    def test_atributos(self) -> None:
        verifier = make_verifier()

        assert verifier.verifier_class == "formal_exact"
        assert verifier.anchor_kind == "solver"
        assert verifier.determinism == "deterministic"
        assert isinstance(verifier, Verifier)


class TestClaimDigest:
    def test_sigue_la_convencion_del_anexo(self) -> None:
        claim = _exact_claim(6, 0.5)
        att = make_verifier().verify(claim, CTX)

        view: dict[str, JSONValue] = {
            "canonical_statement": claim.canonical_statement,
            "scope": claim.scope,
        }
        expected = hashlib.sha256(b"blite/claim/v1\n" + canonicalize(view)).hexdigest()
        assert att.claim_digest == expected


class TestEndianness:
    """Pin de convención (receta §1.1): el índice i, de izquierda a derecha,
    es el sitio i — la MISMA convención que usa
    `blite_cap_numeric.exact_evolve` (independencia de implementación, no
    de convención)."""

    def test_x_en_sitio_0_solamente_distingue_z0_de_z1(self) -> None:
        claim = SimulationSeriesClaim(
            n_sites=2,
            terms=(SpinTerm(pauli="XI", coefficient=-1.0),),
            time=1.0,
            initial_bitstring="00",
            observables=(
                SeriesObservable(label="Z0", pauli="ZI"),
                SeriesObservable(label="Z1", pauli="IZ"),
            ),
            series=(0.0, 0.0),  # candidata irrelevante: solo se lee la ED
            canonical_statement="pin de endianness: X en sitio 0 no mueve Z1",
            scope={},
        )

        z0, z1 = _dense_reference(claim)

        # Si el orden de sitios estuviera invertido, Z0/Z1 se
        # intercambiarían — el par (uno oscila, el otro es invariante) solo
        # es correcto con la convención izquierda-a-derecha declarada.
        assert z0 != pytest.approx(z1)
        assert z1 == pytest.approx(1.0, abs=1e-9)  # H no toca el sitio 1


class TestValidacionDeEntrada:
    """§Deliverable-1 — cada rama del `model_validator` levanta
    `ValidationError`, jamás produce un claim silenciosamente inválido."""

    def _kwargs(self, **overrides: Any) -> dict[str, Any]:
        base: dict[str, Any] = {
            "n_sites": 2,
            "terms": (SpinTerm(pauli="ZZ", coefficient=-1.0),),
            "time": 1.0,
            "initial_bitstring": "00",
            "observables": (SeriesObservable(label="Z0", pauli="ZI"),),
            "series": (0.5,),
            "canonical_statement": "x",
            "scope": {},
        }
        base.update(overrides)
        return base

    def test_pauli_de_termino_de_largo_incorrecto_levanta(self) -> None:
        with pytest.raises(ValidationError):
            SimulationSeriesClaim(
                **self._kwargs(terms=(SpinTerm(pauli="Z", coefficient=1.0),))
            )

    def test_pauli_de_termino_fuera_del_alfabeto_levanta(self) -> None:
        with pytest.raises(ValidationError):
            SimulationSeriesClaim(
                **self._kwargs(terms=(SpinTerm(pauli="ZA", coefficient=1.0),))
            )

    def test_pauli_de_observable_de_largo_incorrecto_levanta(self) -> None:
        with pytest.raises(ValidationError):
            SimulationSeriesClaim(
                **self._kwargs(observables=(SeriesObservable(label="Z0", pauli="Z"),))
            )

    def test_pauli_de_observable_fuera_del_alfabeto_levanta(self) -> None:
        with pytest.raises(ValidationError):
            SimulationSeriesClaim(
                **self._kwargs(observables=(SeriesObservable(label="Z0", pauli="ZA"),))
            )

    def test_initial_bitstring_de_largo_incorrecto_levanta(self) -> None:
        with pytest.raises(ValidationError):
            SimulationSeriesClaim(**self._kwargs(initial_bitstring="0"))

    def test_initial_bitstring_fuera_del_alfabeto_levanta(self) -> None:
        with pytest.raises(ValidationError):
            SimulationSeriesClaim(**self._kwargs(initial_bitstring="02"))

    def test_observables_vacio_levanta(self) -> None:
        with pytest.raises(ValidationError):
            SimulationSeriesClaim(**self._kwargs(observables=(), series=()))

    def test_series_de_largo_distinto_a_observables_levanta(self) -> None:
        with pytest.raises(ValidationError):
            SimulationSeriesClaim(**self._kwargs(series=(0.1, 0.2)))

    def test_claim_de_tipo_incorrecto_levanta_process_error(self) -> None:
        with pytest.raises(VerificationProcessError):
            make_verifier().verify(object(), CTX)


class TestTechoAL4:
    """El techo `formal_exact` es AL4 (`CLASS_CEILINGS`), pero AL4 exige
    `proof` — que no tenemos. Regresión de una línea: el freeze
    (`Attestation._letra_del_freeze`) sigue mordiendo sin él."""

    def test_al4_sin_proof_levanta(self) -> None:
        att = make_verifier().verify(_exact_claim(6, 1.0), CTX)

        with pytest.raises(ValidationError):
            Attestation(
                verifier_id=att.verifier_id,
                verifier_class=att.verifier_class,
                anchor_kind=att.anchor_kind,
                level="AL4",
                verdict=att.verdict,
                scope=att.scope,
                independence_group=att.independence_group,
                run_id=att.run_id,
                claim_digest=att.claim_digest,
                verifier_binary_digest=att.verifier_binary_digest,
                verifier_params_digest=att.verifier_params_digest,
                anchor_digest=att.anchor_digest,
                predicate=att.predicate,
                issued_at=att.issued_at,
            )
