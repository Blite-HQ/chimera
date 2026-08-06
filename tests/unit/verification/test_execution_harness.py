"""Puerto `ExecutionHarness` — ítem C14 (trust/12 §1.4).

La clase `execution` tenía UN adapter y ese adapter era pandapower: «correr
de verdad y observar» significaba, en el código, «correr un flujo de
potencia». El puerto separa QUÉ significa ejecutar (del dominio) de QUÉ
significa verificar por ejecución (genérico).

Dos propiedades cargan el peso y por eso tienen test propio: `dispose` corre
SIEMPRE (incluso si `run` explotó), y la guarda PASS_TO_PASS cuenta como roto
un check que DESAPARECIÓ — borrar el test incómodo es la forma más limpia de
«arreglarlo».
"""

from __future__ import annotations

import pytest

from blite.verification.harness import (
    ExecutionHarness,
    HarnessOutcome,
    HarnessProcessError,
    HarnessSpec,
    Isolation,
    pass_to_pass_holds,
    run_harness,
)

SPEC = HarnessSpec(
    harness_id="pytest-suite@1",
    isolation="in_process",
    inputs_digest="a" * 64,
    pass_to_pass=frozenset({"test_a", "test_b"}),
    fail_to_pass=frozenset({"test_c"}),
)


class _HarnessDoble:
    """Implementación mínima que registra el ORDEN de las fases."""

    isolation: Isolation = "in_process"

    def __init__(
        self, *, revienta: bool = False, passed: set[str] | None = None
    ) -> None:
        self.fases: list[str] = []
        self._revienta = revienta
        self._passed = passed if passed is not None else {"test_a", "test_b", "test_c"}

    def prepare(self, spec: HarnessSpec) -> None:
        self.fases.append("prepare")

    def run(self, spec: HarnessSpec) -> HarnessOutcome:
        self.fases.append("run")
        if self._revienta:
            msg = "el entorno del harness no arrancó"
            raise HarnessProcessError(msg)
        return HarnessOutcome(
            passed=frozenset(self._passed),
            failed=frozenset(),
            runtime_ms=1.0,
        )

    def collect(self, spec: HarnessSpec, outcome: HarnessOutcome) -> HarnessOutcome:
        self.fases.append("collect")
        return outcome

    def dispose(self, spec: HarnessSpec) -> None:
        self.fases.append("dispose")


def test_el_doble_satisface_el_puerto() -> None:
    assert isinstance(_HarnessDoble(), ExecutionHarness)


def test_las_cuatro_fases_corren_en_orden() -> None:
    harness = _HarnessDoble()

    run_harness(harness, SPEC)

    assert harness.fases == ["prepare", "run", "collect", "dispose"]


def test_dispose_corre_aunque_run_explote() -> None:
    """Un harness que no limpia convierte la verificación siguiente en una
    corrida contaminada, y el segundo resultado deja de significar lo mismo
    que el primero. La garantía es del helper, no de que cada implementador
    se acuerde de su try/finally."""
    harness = _HarnessDoble(revienta=True)

    with pytest.raises(HarnessProcessError):
        run_harness(harness, SPEC)

    assert harness.fases == ["prepare", "run", "dispose"]


def test_la_guarda_pass_to_pass_pasa_cuando_todo_sigue_verde() -> None:
    outcome = run_harness(_HarnessDoble(), SPEC)

    assert pass_to_pass_holds(SPEC, outcome) == ()


def test_romper_un_test_que_ya_pasaba_rompe_la_guarda() -> None:
    """Sin esta mitad, «arreglado» incluye «arreglado rompiendo otras cosas»
    — el resultado que un proponente optimiza si nadie lo mira."""
    outcome = run_harness(_HarnessDoble(passed={"test_a", "test_c"}), SPEC)

    assert pass_to_pass_holds(SPEC, outcome) == ("test_b",)


def test_hacer_desaparecer_un_test_tambien_rompe_la_guarda() -> None:
    """Un check declarado que no aparece en `passed` cuenta como roto aunque
    tampoco esté en `failed`: borrarlo es la forma más limpia de arreglarlo."""
    outcome = HarnessOutcome(
        passed=frozenset({"test_a"}), failed=frozenset(), runtime_ms=1.0
    )

    assert pass_to_pass_holds(SPEC, outcome) == ("test_b",)


def test_el_aislamiento_es_parte_de_la_spec_y_se_declara() -> None:
    """AX3: que un despliegue use `in_process` es una decisión VISIBLE en la
    evidencia, no un silencio."""
    assert SPEC.isolation == "in_process"
    aislado = HarnessSpec(harness_id="x@1", isolation="microvm", inputs_digest="b" * 64)
    assert aislado.isolation == "microvm"
