"""Convención de branch-ids C-8 (`docs/specs/superficie-visual.md` §8).

La mitad CANÓNICA de la convención híbrida: `L{min}-{max}[-k]` para modelos
sin GIS (IEEE, sintéticas). Vive en el SDK porque es lo único que engine y
capabilities deben producir BYTE-IDÉNTICO (ADR-008: `blite_capability` es la
única interfaz compartida) — el productor de `partition` la aplica a una
instancia estampada sin re-etiquetarla, y `geojson_to_graph` la aplica al
derivar una instancia nueva.
"""

from __future__ import annotations

import pytest

from blite_capability.branch_ids import (
    CANONICAL_BRANCH_ID_CONVENTION,
    canonical_branch_id,
    canonical_branch_ids,
)


class TestIdIndividual:
    def test_ordena_los_buses_ascendente(self) -> None:
        # Arrange / Act / Assert — la rama (5,2) y la rama (2,5) son LA misma
        assert canonical_branch_id(5, 2) == "L2-5"
        assert canonical_branch_id(2, 5) == "L2-5"

    def test_la_paralela_va_como_sufijo_1_based(self) -> None:
        assert canonical_branch_id(3, 8, parallel_index=2) == "L3-8-2"

    def test_sin_paralela_no_hay_sufijo(self) -> None:
        assert canonical_branch_id(3, 8, parallel_index=None) == "L3-8"

    def test_indice_de_paralela_cero_o_negativo_es_error_de_uso(self) -> None:
        with pytest.raises(ValueError, match="1-based"):
            canonical_branch_id(3, 8, parallel_index=0)


class TestListaDeAristas:
    def test_pares_unicos_no_llevan_sufijo(self) -> None:
        # Arrange
        aristas = [[0, 1, 1], [1, 2, 1], [0, 2, 5]]

        # Act
        ids = canonical_branch_ids(aristas)

        # Assert
        assert ids == ("L0-1", "L1-2", "L0-2")

    def test_multi_aristas_reciben_sufijo_en_todas_desde_1(self) -> None:
        """«presente SOLO cuando hay multi-aristas» (§8): si el par se repite,
        las N reciben sufijo — jamás una sin y las otras con."""
        # Arrange
        aristas = [[3, 8, 1], [0, 1, 1], [8, 3, 2]]

        # Act
        ids = canonical_branch_ids(aristas)

        # Assert
        assert ids == ("L3-8-1", "L0-1", "L3-8-2")

    def test_el_sufijo_sigue_el_orden_de_entrada(self) -> None:
        aristas = [[8, 3, 1], [3, 8, 1], [3, 8, 1]]
        assert canonical_branch_ids(aristas) == ("L3-8-1", "L3-8-2", "L3-8-3")

    def test_ignora_el_peso(self) -> None:
        assert canonical_branch_ids([[0, 1, 99]]) == canonical_branch_ids([[0, 1]])

    def test_es_determinista_entre_llamadas(self) -> None:
        aristas = [[10, 2, 1], [2, 10, 1], [4, 4, 1]]
        assert canonical_branch_ids(aristas) == canonical_branch_ids(aristas)

    def test_lista_vacia_da_tupla_vacia(self) -> None:
        assert canonical_branch_ids([]) == ()

    def test_arista_mal_formada_falla_fuerte(self) -> None:
        """Validación en frontera: una arista sin dos extremos no se
        adivina."""
        with pytest.raises(ValueError, match="dos extremos"):
            canonical_branch_ids([[7]])


def test_la_convencion_esta_versionada() -> None:
    """C-8: la convención viaja CON la instancia — cambiarla produce una
    instancia nueva, jamás un re-etiquetado del dato estampado."""
    assert CANONICAL_BRANCH_ID_CONVENTION == "canonical-l-min-max@v1"
