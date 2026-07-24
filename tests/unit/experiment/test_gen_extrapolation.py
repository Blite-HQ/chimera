"""Tests de INVARIANTES para `scripts/gen_extrapolation.py` — B4 (artefacto de
extrapolación honesta, `docs/planeado/04-consolidacion.md` §3).

Cuatro contratos (brief B4):
  1. Régimen: n<=26 -> "quantum-eligible", n>26 -> "classical-only"; ieee30/
     ICE traen `quantum: null` con la razón de la barrera (nunca vacío
     "por descuido").
  2. ICE-68: `optimo=null` -> banda `[greedy, gw, sdp_bound]`, JAMÁS un r
     inventado; `greedy_cut <= gw_cut <= sdp_upper_bound` (sanity, con
     tolerancia numérica del solver SDP).
  3. Determinismo: dos corridas de `build_artifact()` -> mismo digest.
  4. Coherencia: los r cuánticos citados (best_cut) coinciden con el
     `best_cut` que `scripts/import_nexus_runs.py` ya declaró en la
     provenance de `knowledge/nexus/normalized/` (fuente independiente,
     computada en B3) — y los `job_id` citados existen en
     `knowledge/nexus/index.json` para esa instancia.

`scripts/` no es un paquete instalable (mismo patrón que
`tests/unit/experiment/test_exp_r_vs_p.py`): el módulo se carga por ruta y
se envuelve tras un `Protocol` tipado para pyright strict.

Costo: `build_artifact()` resuelve una SDP (cvxpy) por instancia (8 en
total, incluyendo n=68 dos veces) — del orden de 10-15s por corrida. La
mayoría de las clases comparten UN solo `artifact` vía el fixture
`module`-scoped `artifact` en vez de reconstruirlo por test; solo
`TestBuildArtifactDeterminism` paga una segunda corrida completa (es
exactamente lo que ese test necesita probar).
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any, Protocol, cast

import pytest

# Triángulo w01=1, w12=2, w02=3 (mismo `_G6`/`_TRIANGLE_MATRIX` que
# test_exp_r_vs_p.py y capabilities/solvers/tests/test_qubo_solver.py).
_TRIANGLE_ARISTAS: list[list[int]] = [[0, 1, 1], [1, 2, 2], [0, 2, 3]]
_TRIANGLE_OPTIMO = 5


class _ExtrapolationModule(Protocol):
    """Firma tipada de las funciones puras/orquestación de gen_extrapolation.py."""

    BARRIER_QUBITS: int
    INSTANCES: tuple[str, ...]

    def regime_for(self, n_nodos: int) -> str: ...

    def decode_bitstring(self, bitstring: str, order: str) -> list[int]: ...

    def cut_value(self, aristas: list[list[int]], assignment: list[int]) -> int: ...

    def nexus_run_stats(
        self,
        counts: dict[str, int],
        order: str,
        aristas: list[list[int]],
        optimo: int,
    ) -> dict[str, Any]: ...

    def load_corpus_instance(self, name: str) -> dict[str, Any]: ...

    def load_normalized_counts(self, stem: str) -> dict[str, int]: ...

    def load_nexus_index(self) -> dict[str, Any]: ...

    def build_row(self, name: str, index: dict[str, Any]) -> dict[str, Any]: ...

    def build_artifact(self) -> dict[str, Any]: ...


def _find_script() -> Path:
    for base in (Path(__file__).resolve(), *Path(__file__).resolve().parents):
        candidate = base / "scripts" / "gen_extrapolation.py"
        if candidate.is_file():
            return candidate
    msg = "scripts/gen_extrapolation.py no encontrado sobre este archivo"
    raise FileNotFoundError(msg)


def _repo_root() -> Path:
    return _find_script().parent.parent


def _load_module() -> _ExtrapolationModule:
    script_path = _find_script()
    spec = importlib.util.spec_from_file_location("gen_extrapolation", script_path)
    if spec is None:
        msg = f"no se pudo construir un spec de import para {script_path}"
        raise ImportError(msg)
    loader = spec.loader
    if loader is None:
        msg = f"el spec de {script_path} no tiene loader"
        raise ImportError(msg)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return cast(_ExtrapolationModule, module)


gx = _load_module()


def _row(artifact: dict[str, Any], instance: str) -> dict[str, Any]:
    for row in artifact["instances"]:
        if row["instance"] == instance:
            return cast(dict[str, Any], row)
    msg = f"{instance} no está en artifact['instances']"
    raise KeyError(msg)


@pytest.fixture(scope="module")
def artifact() -> dict[str, Any]:
    """UNA corrida completa de `build_artifact()`, reusada por todos los
    tests que solo necesitan LEER el artefacto (no probar determinismo)."""
    return gx.build_artifact()


class TestRegimeFor:
    def test_boundary_at_26_is_quantum_eligible(self) -> None:
        assert gx.regime_for(26) == "quantum-eligible"

    def test_27_is_classical_only(self) -> None:
        assert gx.regime_for(27) == "classical-only"

    def test_small_n_is_quantum_eligible(self) -> None:
        assert gx.regime_for(6) == "quantum-eligible"

    def test_ice_68_is_classical_only(self) -> None:
        assert gx.regime_for(68) == "classical-only"


class TestDecodeBitstring:
    def test_msb_left_reads_chars_as_is(self) -> None:
        assert gx.decode_bitstring("0110", "msb-left") == [0, 1, 1, 0]

    def test_msb_right_reverses(self) -> None:
        assert gx.decode_bitstring("0110", "msb-right") == [0, 1, 1, 0][::-1]


class TestCutValue:
    def test_triangle_all_same_side_has_zero_cut(self) -> None:
        assert gx.cut_value(_TRIANGLE_ARISTAS, [0, 0, 0]) == 0

    def test_triangle_optimal_split_reaches_five(self) -> None:
        # x0=0 fijo (ruptura de simetría); separar el nodo 2 (aristas w=2+3)
        # dobla las dos aristas más pesadas -> corte 5 (óptimo del G6).
        assert gx.cut_value(_TRIANGLE_ARISTAS, [0, 0, 1]) == _TRIANGLE_OPTIMO


class TestNexusRunStats:
    def test_pure_computation_matches_hand_check(self) -> None:
        # 3 shots del bitstring "01" (cut=1 sobre una arista w=1,
        # optimo=1) + 1 shot de "00" (cut=0) -> ratio_best=1.0,
        # ratio_mean=(3*1+1*0)/4/1=0.75.
        counts = {"01": 3, "00": 1}
        aristas = [[0, 1, 1]]

        stats = gx.nexus_run_stats(counts, "msb-left", aristas, optimo=1)

        assert stats == {
            "shots": 4,
            "best_cut": 1,
            "ratio_best": 1.0,
            "ratio_mean": 0.75,
        }


class TestCoherenceWithNexus:
    """Bullet 4 del brief: el r cuántico citado coincide con
    `knowledge/nexus/` — fuente independiente (B3, `import_nexus_runs.py`).
    No necesita el fixture `artifact` — trabaja directo sobre los archivos
    de `knowledge/nexus/`, más barato y más específico."""

    def test_recomputed_best_cut_matches_import_provenance(self) -> None:
        # Arrange — cr6-uniforme p1 H2-1LE, la primera corrida importada.
        stem = "cr6-uniforme-p1-s0-H2-1LE"
        record = gx.load_corpus_instance("cr6-uniforme")
        counts = gx.load_normalized_counts(stem)

        # La provenance de la corrida (fuente independiente del importador
        # B3) declara el best_cut que decodificó — mismo archivo que
        # `load_normalized_counts` lee, campo `provenance`.
        normalized_json = json.loads(
            (
                _repo_root() / "knowledge" / "nexus" / "normalized" / f"{stem}.json"
            ).read_text(encoding="utf-8")
        )
        declared_best_cut = normalized_json["provenance"]["assertions"][1]["detail"][
            "best_cut"
        ]

        # Act
        stats = gx.nexus_run_stats(
            counts, "msb-left", record["aristas"], optimo=record["optimo"]
        )

        # Assert
        assert stats["best_cut"] == declared_best_cut

    def test_quantum_runs_cite_job_ids_present_in_nexus_index(
        self, artifact: dict[str, Any]
    ) -> None:
        index = gx.load_nexus_index()
        expected_job_ids = {
            imp["job_id"]
            for imp in index["imports"]
            if imp["instance"] == "cr6-uniforme"
        }

        row = _row(artifact, "cr6-uniforme")
        cited_job_ids = {run["job_id"] for run in row["quantum"]}

        assert cited_job_ids == expected_job_ids
        assert len(expected_job_ids) > 0


class TestBuildRowRegime:
    def test_quantum_eligible_instance_carries_real_quantum_runs(
        self, artifact: dict[str, Any]
    ) -> None:
        row = _row(artifact, "cr6-uniforme")

        assert row["regime"] == "quantum-eligible"
        assert row["reason"] is None
        assert row["quantum"] is not None
        assert len(row["quantum"]) > 0
        for run in row["quantum"]:
            assert 0.0 <= run["ratio_mean"] <= 1.0
            assert 0.0 <= run["ratio_best"] <= 1.0

    def test_ieee30_is_classical_only_with_barrier_reason(
        self, artifact: dict[str, Any]
    ) -> None:
        row = _row(artifact, "ieee30-uniforme")

        assert row["regime"] == "classical-only"
        assert row["quantum"] is None
        assert row["reason"] == "excede la barrera de 26 qubits del emulador H2"
        assert row["optimo"] is not None  # ieee30 SÍ tiene óptimo probado


class TestIceBand:
    def test_ice_has_no_invented_ratio_only_a_band(
        self, artifact: dict[str, Any]
    ) -> None:
        row = _row(artifact, "ice-uniforme")

        assert row["optimo"] is None
        assert row["quantum"] is None
        assert row["reason"] == "excede la barrera de 26 qubits del emulador H2"
        assert row["r_gw"] is None
        assert row["r_greedy"] is None
        assert row["band"] is not None
        assert len(row["band"]) == 3

    @pytest.mark.parametrize("instance", ["ice-uniforme", "ice-voltaje"])
    def test_band_is_ordered_greedy_le_gw_le_sdp_bound(
        self, artifact: dict[str, Any], instance: str
    ) -> None:
        row = _row(artifact, instance)
        greedy_cut, gw_cut, sdp_bound = row["band"]
        # Tolerancia relativa: el SDP se resuelve numéricamente (SCS/
        # Clarabel), no en aritmética exacta (mismo argumento que
        # capabilities/graphs/tests/test_maxcut.py).
        tolerance = abs(sdp_bound) * 1e-6 + 1e-6

        assert greedy_cut <= gw_cut + tolerance
        assert gw_cut <= sdp_bound + tolerance


class TestBuildArtifactDeterminism:
    def test_two_full_runs_produce_the_same_digest(
        self, artifact: dict[str, Any]
    ) -> None:
        second = gx.build_artifact()

        assert artifact["digest"] == second["digest"]
        assert artifact == second

    def test_digest_excludes_itself_from_its_own_input(
        self, artifact: dict[str, Any]
    ) -> None:
        without_digest = {k: v for k, v in artifact.items() if k != "digest"}
        canonical = json.dumps(
            without_digest, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        )
        expected = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

        assert artifact["digest"] == expected


class TestHonestLimitations:
    def test_qaoa_never_beats_gw_in_this_frozen_dataset(
        self, artifact: dict[str, Any]
    ) -> None:
        beats = artifact["honest_limitations"]["qaoa_vs_gw"][
            "instances_where_qaoa_beat_gw"
        ]

        assert beats == []

    def test_barrier_summary_lists_classical_only_instances(
        self, artifact: dict[str, Any]
    ) -> None:
        barrier = artifact["honest_limitations"]["barrier_26_qubits"]

        assert barrier["value"] == 26
        assert "ieee30-uniforme" in barrier["classical_only_instances"]
        assert "ice-uniforme" in barrier["classical_only_instances"]
        assert "ice-voltaje" in barrier["classical_only_instances"]
        assert "cr6-uniforme" in barrier["quantum_eligible_instances"]

    def test_ice_summary_lists_both_ice_instances(
        self, artifact: dict[str, Any]
    ) -> None:
        ice = artifact["honest_limitations"]["ice_no_ground_truth"]

        assert set(ice["instances"]) == {"ice-uniforme", "ice-voltaje"}


class TestAllInstancesRegimeMatchesBarrier:
    @pytest.mark.parametrize("name", list(gx.INSTANCES))
    def test_regime_is_consistent_with_n_nodos_and_barrier(
        self, artifact: dict[str, Any], name: str
    ) -> None:
        row = _row(artifact, name)

        expected_regime = (
            "quantum-eligible"
            if row["n_nodos"] <= gx.BARRIER_QUBITS
            else "classical-only"
        )
        assert row["regime"] == expected_regime
        if row["regime"] == "classical-only":
            assert row["quantum"] is None
            assert row["reason"]
        else:
            assert row["quantum"] is not None
            assert row["reason"] is None
