"""Conversor pandapower -> InstanceElectricalData (Fase 1, certificado real
sobre ieee6-flujo). Reusable: ieee9/ieee14 lo van a necesitar despues."""

from __future__ import annotations

import pandapower.networks as pn
from chimera_api.pandapower_electrical_data import from_pandapower_network


class TestFromPandapowerNetwork:
    def test_case6ww_produce_seis_buses_con_vn_kv_real(self) -> None:
        # Arrange
        net = pn.case6ww()

        # Act
        data = from_pandapower_network(net, provenance="pandapower-case6ww-v1")

        # Assert
        buses = data.topology["buses"]
        assert len(buses) == 6
        assert all(b["vn_kv"] == 230.0 for b in buses)

    def test_case6ww_slack_incluye_ext_grid_y_generadores(self) -> None:
        # Arrange
        net = pn.case6ww()

        # Act
        data = from_pandapower_network(net, provenance="pandapower-case6ww-v1")

        # Assert -- ext_grid en bus 0, gen en buses 1 y 2 (fuentes reales de case6ww)
        slack_buses = {s["bus"] for s in data.topology["slack"]}
        assert slack_buses == {0, 1, 2}

    def test_case6ww_branches_traen_r_y_x_reales(self) -> None:
        # Arrange
        net = pn.case6ww()

        # Act
        data = from_pandapower_network(net, provenance="pandapower-case6ww-v1")

        # Assert -- 11 lineas en servicio, r/x > 0 (no placeholders)
        branches = data.topology["branches"]
        assert len(branches) == 11
        assert all(b["r_ohm_per_km"] > 0 and b["x_ohm_per_km"] > 0 for b in branches)

    def test_case6ww_loads_traen_p_mw_real(self) -> None:
        # Arrange
        net = pn.case6ww()

        # Act
        data = from_pandapower_network(net, provenance="pandapower-case6ww-v1")

        # Assert -- 3 cargas de 70 MW en buses 3,4,5
        loads = {(load_["bus"], load_["p_mw"]) for load_ in data.topology["loads"]}
        assert loads == {(3, 70.0), (4, 70.0), (5, 70.0)}

    def test_provenance_y_digest_quedan_registrados(self) -> None:
        # Arrange
        net = pn.case6ww()

        # Act
        data = from_pandapower_network(net, provenance="pandapower-case6ww-v1")

        # Assert
        assert data.provenance == "pandapower-case6ww-v1"
        assert len(data.anchor_digest) == 64  # sha256 hexdigest
