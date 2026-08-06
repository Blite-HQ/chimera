"""Productor de `partition` (V1/M18 — C-8, `docs/specs/superficie-visual.md`
§4/§8).

Las tres reglas que se prueban acá:

1. **Verdict POR ISLA** = `derive_execution_verdict` sobre el SUBCONJUNTO de
   checks `island-{k}:*` de esa isla — ningún check de otra isla contamina, y
   un check global (sin prefijo) pertenece al resultado, no a una isla.
2. **Nada fabricado**: una attestation sin checks por isla NO produce
   partición (honest-empty), y una isla jamás reporta más nivel que la
   attestation que la ampara.
3. **Identidad del corte**: `cut_branch_ids` sale de la convención C-8, no de
   índices improvisados.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from blite.verification.attestation import Attestation
from blite.verification.evidence import (
    Differential,
    ExecutionCheck,
    ExecutionEnvironment,
    ExecutionPredicate,
    FormalExactPredicate,
)
from blite.verification.partition import (
    ISLAND_ID_PREFIX,
    build_partition,
    island_checks_by_island,
)

_EDGES = ((0, 1, 4), (1, 2, 7), (2, 3, 5), (0, 3, 2))


def _execution_attestation(
    checks: tuple[ExecutionCheck, ...],
    *,
    verdict: str = "pass",
    level: str = "AL3",
) -> Attestation:
    return Attestation(
        verifier_id="verifier:pandapower-islanding",
        verifier_class="execution",
        anchor_kind="execution",
        level=level,  # pyright: ignore[reportArgumentType]
        verdict=verdict,  # pyright: ignore[reportArgumentType]
        inconclusive_reason=("undecidable" if verdict == "inconclusive" else None),
        scope={"instancia": "sintetica-4bus"},
        independence_group="leg-execution",
        run_id="run-1",
        claim_digest="c" * 64,
        verifier_binary_digest="b" * 64,
        verifier_params_digest="p" * 64,
        anchor_digest="a" * 64,
        predicate=ExecutionPredicate(
            harness="pandapower-islanding-v1",
            input_digest="i" * 64,
            checks=checks,
            runtime_ms=12.0,
            environment=ExecutionEnvironment(package="pandapower", version="3.5.4"),
        ),
        issued_at=datetime(2026, 8, 5, tzinfo=UTC),
    )


def _formal_attestation() -> Attestation:
    return Attestation(
        verifier_id="verifier:cpsat-differential",
        verifier_class="formal_exact",
        anchor_kind="solver",
        level="AL1",
        verdict="pass",
        scope={"instancia": "sintetica-4bus"},
        independence_group="leg-formal",
        run_id="run-1",
        claim_digest="c" * 64,
        verifier_binary_digest="b" * 64,
        verifier_params_digest="p" * 64,
        anchor_digest="a" * 64,
        predicate=FormalExactPredicate(
            differential=Differential(
                status="OPTIMAL", objective=11.0, reference_objective=11.0
            )
        ),
        issued_at=datetime(2026, 8, 5, tzinfo=UTC),
    )


def _checks(*names_passed: tuple[str, bool]) -> tuple[ExecutionCheck, ...]:
    return tuple(ExecutionCheck(name=n, passed=p) for n, p in names_passed)


class TestAgrupacionDeChecks:
    def test_agrupa_por_prefijo_de_isla(self) -> None:
        # Arrange
        attestation = _execution_attestation(
            _checks(
                ("island-0:island_connectivity", True),
                ("island-1:island_connectivity", True),
                ("island-0:island_has_source", True),
            )
        )

        # Act
        grupos = island_checks_by_island(attestation)

        # Assert
        assert set(grupos) == {"island-0", "island-1"}
        # los checks entran TAL CUAL (evidencia sin reescribir), en su orden
        assert [c.name for c in grupos["island-0"]] == [
            "island-0:island_connectivity",
            "island-0:island_has_source",
        ]

    def test_un_check_global_no_pertenece_a_ninguna_isla(self) -> None:
        """C-8 literal: «un check global (`power_balance` de red completa)
        pertenece al resultado, no a una isla»."""
        # Arrange
        attestation = _execution_attestation(
            _checks(("island-0:island_connectivity", True), ("power_balance", False))
        )

        # Act
        grupos = island_checks_by_island(attestation)

        # Assert
        assert set(grupos) == {"island-0"}

    def test_un_predicado_sin_checks_no_agrupa_nada(self) -> None:
        assert island_checks_by_island(_formal_attestation()) == {}

    def test_el_prefijo_es_el_de_la_convencion(self) -> None:
        assert ISLAND_ID_PREFIX == "island-"


class TestVerdictPorIsla:
    def test_cada_isla_deriva_de_sus_propios_checks_sin_contaminarse(self) -> None:
        # Arrange — la isla 1 falla; la isla 0 está sana
        attestation = _execution_attestation(
            _checks(
                ("island-0:island_connectivity", True),
                ("island-0:island_has_source", True),
                ("island-1:island_connectivity", True),
                ("island-1:island_has_source", False),
            ),
            verdict="fail",
        )

        # Act
        partition = build_partition(
            attestation=attestation,
            assignment=(0, 0, 1, 1),
            edges=_EDGES,
            topology_ref="sintetica-4bus@v1",
        )

        # Assert
        assert partition is not None
        veredictos = {
            i["id"]: i["verification"]["verdict"] for i in partition["islands"]
        }
        assert veredictos == {"island-0": "pass", "island-1": "fail"}

    def test_la_abstencion_del_metodo_es_inconclusive_no_fail(self) -> None:
        """El check de abstención declarado por el harness (no-convergencia)
        es cota del método — jamás un veredicto en contra."""
        # Arrange
        attestation = _execution_attestation(
            _checks(
                ("island-0:island_connectivity", True),
                ("island-0:island_has_source", True),
                ("island-0:powerflow_converged", False),
            ),
            verdict="inconclusive",
            level="AL0",
        )

        # Act
        partition = build_partition(
            attestation=attestation,
            assignment=(0, 0, 0, 0),
            edges=_EDGES,
            topology_ref="sintetica-4bus@v1",
        )

        # Assert
        assert partition is not None
        isla = partition["islands"][0]
        assert isla["verification"]["verdict"] == "inconclusive"
        assert isla["verification"]["level"] == "AL0"

    def test_una_isla_jamas_reporta_mas_nivel_que_su_attestation(self) -> None:
        # Arrange — attestation AL0 (otra isla abstuvo); esta isla pasó
        attestation = _execution_attestation(
            _checks(
                ("island-0:island_connectivity", True),
                ("island-1:powerflow_converged", False),
            ),
            verdict="inconclusive",
            level="AL0",
        )

        # Act
        partition = build_partition(
            attestation=attestation,
            assignment=(0, 0, 1, 1),
            edges=_EDGES,
            topology_ref="sintetica-4bus@v1",
        )

        # Assert
        assert partition is not None
        niveles = {i["id"]: i["verification"]["level"] for i in partition["islands"]}
        assert niveles == {"island-0": "AL0", "island-1": "AL0"}

    def test_el_bloque_por_isla_trae_la_forma_completa_del_contrato(self) -> None:
        """freeze §9 sin excepción: `verification` POR ISLA, con los 6
        campos que `topologySnapshotSchema` exige."""
        # Arrange
        attestation = _execution_attestation(
            _checks(("island-0:island_connectivity", True))
        )

        # Act
        partition = build_partition(
            attestation=attestation,
            assignment=(0, 0, 0, 0),
            edges=_EDGES,
            topology_ref="sintetica-4bus@v1",
        )

        # Assert
        assert partition is not None
        verification = partition["islands"][0]["verification"]
        assert set(verification) == {
            "verdict",
            "verifier_class",
            "level",
            "anchor_kind",
            "method",
            "summary",
        }
        assert verification["verifier_class"] == "execution"
        assert verification["anchor_kind"] == "execution"
        assert verification["method"] == "pandapower-islanding-v1"
        assert verification["summary"]


class TestNadaFabricado:
    def test_sin_checks_por_isla_no_hay_particion(self) -> None:
        """Honest-empty: la pata formal no dice NADA por isla, así que no se
        inventa un badge por isla a partir de su veredicto global."""
        # Act
        partition = build_partition(
            attestation=_formal_attestation(),
            assignment=(0, 0, 1, 1),
            edges=_EDGES,
            topology_ref="sintetica-4bus@v1",
        )

        # Assert
        assert partition is None

    def test_una_isla_del_assignment_sin_checks_propios_tampoco_se_inventa(
        self,
    ) -> None:
        """Si el harness solo reportó la isla 0, la isla 1 no aparece con un
        veredicto prestado — la partición reporta lo que fue verificado."""
        # Arrange
        attestation = _execution_attestation(
            _checks(("island-0:island_connectivity", True))
        )

        # Act
        partition = build_partition(
            attestation=attestation,
            assignment=(0, 0, 1, 1),
            edges=_EDGES,
            topology_ref="sintetica-4bus@v1",
        )

        # Assert
        assert partition is not None
        assert [i["id"] for i in partition["islands"]] == ["island-0"]

    def test_assignment_que_no_casa_con_las_aristas_falla_fuerte(self) -> None:
        attestation = _execution_attestation(
            _checks(("island-0:island_connectivity", True))
        )
        with pytest.raises(ValueError, match="fuera de rango"):
            build_partition(
                attestation=attestation,
                assignment=(0, 1),
                edges=_EDGES,
                topology_ref="x@v1",
            )


class TestIdentidadDelCorte:
    def test_el_corte_usa_la_convencion_canonica_y_cuenta_su_costo(self) -> None:
        # Arrange — assignment (0,0,1,1) corta (1,2,w=7) y (0,3,w=2)
        attestation = _execution_attestation(
            _checks(
                ("island-0:island_connectivity", True),
                ("island-1:island_connectivity", True),
            )
        )

        # Act
        partition = build_partition(
            attestation=attestation,
            assignment=(0, 0, 1, 1),
            edges=_EDGES,
            topology_ref="sintetica-4bus@v1",
        )

        # Assert
        assert partition is not None
        assert partition["cut_branch_ids"] == ["L1-2", "L0-3"]
        assert partition["cut_cost"] == 9.0

    def test_los_branch_ids_del_dato_ganan_sobre_la_convencion_canonica(self) -> None:
        """Mitad GIS de C-8: si la instancia trae SUS ids (edge_id_property),
        el corte los cita — el dato del cliente conserva su identidad."""
        # Arrange
        attestation = _execution_attestation(
            _checks(
                ("island-0:island_connectivity", True),
                ("island-1:island_connectivity", True),
            )
        )

        # Act
        partition = build_partition(
            attestation=attestation,
            assignment=(0, 0, 1, 1),
            edges=_EDGES,
            branch_ids=("70140", "70141", "70142", "70143"),
            topology_ref="ice-uniforme@v1",
        )

        # Assert
        assert partition is not None
        assert partition["cut_branch_ids"] == ["70141", "70143"]

    def test_branch_ids_desalineados_fallan_fuerte(self) -> None:
        attestation = _execution_attestation(
            _checks(("island-0:island_connectivity", True))
        )
        with pytest.raises(ValueError, match="1:1"):
            build_partition(
                attestation=attestation,
                assignment=(0, 0, 1, 1),
                edges=_EDGES,
                branch_ids=("solo-uno",),
                topology_ref="x@v1",
            )

    def test_los_bus_ids_son_strings_del_wire_en_orden(self) -> None:
        attestation = _execution_attestation(
            _checks(
                ("island-0:island_connectivity", True),
                ("island-1:island_connectivity", True),
            )
        )
        partition = build_partition(
            attestation=attestation,
            assignment=(0, 1, 1, 0),
            edges=_EDGES,
            topology_ref="x@v1",
        )
        assert partition is not None
        por_isla = {i["id"]: i["bus_ids"] for i in partition["islands"]}
        assert por_isla == {"island-0": ["0", "3"], "island-1": ["1", "2"]}

    def test_las_etiquetas_de_isla_son_dato_opcional(self) -> None:
        """El `name` del contrato es dato de la instancia, no vocabulario del
        productor: sin etiquetas, el nombre ES el id."""
        attestation = _execution_attestation(
            _checks(("island-0:island_connectivity", True))
        )
        sin_etiqueta = build_partition(
            attestation=attestation,
            assignment=(0, 0, 0, 0),
            edges=_EDGES,
            topology_ref="x@v1",
        )
        con_etiqueta = build_partition(
            attestation=attestation,
            assignment=(0, 0, 0, 0),
            edges=_EDGES,
            topology_ref="x@v1",
            island_labels={"island-0": "Norte"},
        )
        assert sin_etiqueta is not None and con_etiqueta is not None
        assert sin_etiqueta["islands"][0]["name"] == "island-0"
        assert con_etiqueta["islands"][0]["name"] == "Norte"
