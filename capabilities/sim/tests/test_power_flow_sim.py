"""Unit tests de `PowerFlowSim._invoke_impl` (pandapower real, red diminuta).

Topología genérica (dict): buses/slack/branches/loads — cero términos de
escenario (ADR-029: el manifest ya lo gatea tests/invariants).
"""

from __future__ import annotations

from typing import Any

import pytest

from blite_cap_sim import PowerFlowSim


def _two_bus_topology() -> dict[str, Any]:
    """Slack en 0, carga en 1, una rama — resoluble a mano."""
    return {
        "buses": [{"id": 0, "vn_kv": 110.0}, {"id": 1, "vn_kv": 110.0}],
        "slack": [{"bus": 0}],
        "branches": [
            {
                "from": 0,
                "to": 1,
                "length_km": 10.0,
                "r_ohm_per_km": 0.06,
                "x_ohm_per_km": 0.4,
                "c_nf_per_km": 10.0,
                "max_i_ka": 0.5,
            }
        ],
        "loads": [{"bus": 1, "p_mw": 10.0, "q_mvar": 2.0}],
    }


class TestPowerFlow:
    def test_two_bus_network_converges_with_electrical_metrics(self) -> None:
        # Act
        result = PowerFlowSim().invoke({"topology": _two_bus_topology()})

        # Assert
        assert result["converged"] is True
        metrics = result["metrics"]
        assert len(metrics["bus_vm_pu"]) == 2
        assert metrics["bus_vm_pu"][0] == pytest.approx(1.0)
        assert metrics["branch_p_from_mw"][0] > 10.0  # carga + pérdidas
        assert metrics["total_losses_mw"] > 0.0

    def test_non_converging_case_reports_converged_false(self) -> None:
        # Arrange — carga físicamente imposible para la rama
        topology = _two_bus_topology()
        topology["loads"] = [{"bus": 1, "p_mw": 1e6, "q_mvar": 0.0}]

        # Act
        result = PowerFlowSim().invoke({"topology": topology})

        # Assert — no convergencia es resultado del esquema, no excepción
        assert result["converged"] is False


class TestInputValidation:
    def test_missing_topology_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="topology"):
            PowerFlowSim().invoke({})

    def test_topology_without_buses_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="buses"):
            PowerFlowSim().invoke({"topology": {"slack": [{"bus": 0}]}})

    def test_topology_without_slack_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="slack"):
            PowerFlowSim().invoke(
                {"topology": {"buses": [{"id": 0, "vn_kv": 110.0}]}}
            )
