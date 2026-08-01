"""Validación de las 6 instancias nuevas del corpus (B2): `cr6`/`cr8` ×
{uniforme, voltaje} (copiadas verbatim del espejo `reto1-vanilla`) e
`ice` × {uniforme, voltaje} (derivadas por `scripts/gen_corpus_ice.py` a
través de `blite.ingesta.geojson.to_graph`).

No confía en el archivo: recomputa el digest canónico y — para `cr6`/`cr8` —
compara contra el digest conocido del espejo (identidad congelada, pinneada
también en `scripts/verify_corpus_digests.py::ESPERADOS_CHIMERA_B2`); para
`ice` verifica la aritmética honesta declarada en la spec (68 nodos, 90
aristas, un único componente conexo de las 70 subestaciones del snapshot).
También ejercita el guard generalizado (`scripts/verify_corpus_digests.py`)
como smoke: debe terminar en verde sobre el corpus completo (8 IEEE + 4 cr +
2 ice = 14).
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import re
import runpy
from pathlib import Path
from typing import Any

import networkx as nx
import pytest

_REPO = Path(__file__).resolve().parents[3]
_CORPUS = _REPO / "knowledge" / "islanding" / "corpus"
_VERIFY_SCRIPT = _REPO / "scripts" / "verify_corpus_digests.py"

# Digests conocidos del espejo `reto1-vanilla/data/{cr6,cr8}-*.json` — mismo
# ancla que `ESPERADOS_CHIMERA_B2` del guard generalizado; pinneados aquí de
# forma independiente (no se importa el guard para no acoplar el test a su
# implementación).
_CR_DIGESTS_ESPERADOS = {
    "cr6-uniforme": "e8b2121c61399aa758a356835f1e849e435377ebc2eadf0dd08356c702b680db",
    "cr6-voltaje": "aab9f07fd8e7f6be84d90fc97493de3603b82b3dec80627699051dc706e3dd0c",
    "cr8-uniforme": "66bb6c5ae0eadb1c697436ea36c069b3bf3c3a4ef436d1eda9540a3e79f91392",
    "cr8-voltaje": "0af00267250f0838ce5445659238c180fe88771383001aa4c745e36462d1aa5b",
}
_ICE_CONVENCIONES = ("uniforme", "voltaje")
_ICE_N_NODOS = 68
_ICE_ARISTAS = 90
_ICE_SUBESTACIONES_SNAPSHOT = 70
_ICE_AISLADAS = 2
_ICE_DESCARTADAS = 8


def _cargar(nombre: str) -> dict[str, Any]:
    return json.loads((_CORPUS / f"{nombre}.json").read_text(encoding="utf-8"))


def _digest_canonico(registro: dict[str, Any]) -> str:
    sin_digest = {k: v for k, v in registro.items() if k != "digest"}
    canonico = json.dumps(
        sin_digest, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(canonico.encode("utf-8")).hexdigest()


class TestCrInstancesMatchTheMirrorVerbatim:
    @pytest.mark.parametrize("nombre", sorted(_CR_DIGESTS_ESPERADOS))
    def test_digest_interno_recomputa(self, nombre: str) -> None:
        registro = _cargar(nombre)

        assert registro["digest"] == _digest_canonico(registro)

    @pytest.mark.parametrize("nombre", sorted(_CR_DIGESTS_ESPERADOS))
    def test_digest_coincide_con_el_espejo(self, nombre: str) -> None:
        registro = _cargar(nombre)

        assert registro["digest"] == _CR_DIGESTS_ESPERADOS[nombre]


class TestIceInstances:
    @pytest.mark.parametrize("convencion", _ICE_CONVENCIONES)
    def test_digest_interno_recomputa(self, convencion: str) -> None:
        registro = _cargar(f"ice-{convencion}")

        assert registro["digest"] == _digest_canonico(registro)

    @pytest.mark.parametrize("convencion", _ICE_CONVENCIONES)
    def test_n_nodos_es_68_no_70(self, convencion: str) -> None:
        """Honestidad: n_nodos es el grafo REAL (68, componente conexo), no
        las 70 subestaciones crudas del snapshot."""
        registro = _cargar(f"ice-{convencion}")

        assert registro["n_nodos"] == _ICE_N_NODOS
        assert len(registro["nodos"]) == _ICE_N_NODOS

    @pytest.mark.parametrize("convencion", _ICE_CONVENCIONES)
    def test_90_aristas_en_un_unico_componente_conexo(self, convencion: str) -> None:
        registro = _cargar(f"ice-{convencion}")
        aristas = registro["aristas"]

        assert len(aristas) == _ICE_ARISTAS
        for i, j, w in aristas:
            assert isinstance(i, int)
            assert isinstance(j, int)
            assert isinstance(w, int)
            assert i < j
        pares = [(i, j) for i, j, _ in aristas]
        assert pares == sorted(pares)

        grafo = nx.Graph((i, j) for i, j, _ in aristas)
        assert grafo.number_of_nodes() == _ICE_N_NODOS
        assert nx.is_connected(grafo)

    @pytest.mark.parametrize("convencion", _ICE_CONVENCIONES)
    def test_optimo_null_con_notas_honestas(self, convencion: str) -> None:
        """n=68>14: sin doble ancla de fuerza bruta — spec §Parte 2: `optimo`
        queda `null`, la razón y la aritmética de aislados/descartados
        quedan documentadas en `notas`, nunca ocultas."""
        registro = _cargar(f"ice-{convencion}")

        assert registro["optimo"] is None
        assert registro["asignacion_canonica"] is None
        notas = " ".join(registro["notas"])
        assert str(_ICE_SUBESTACIONES_SNAPSHOT) in notas
        assert str(_ICE_N_NODOS) in notas
        assert str(_ICE_AISLADAS) in notas
        assert str(_ICE_DESCARTADAS) in notas

    @pytest.mark.parametrize("convencion", _ICE_CONVENCIONES)
    def test_provenance_embebida_trae_ambas_ramas(self, convencion: str) -> None:
        """`DerivationProvenance` + `ExternalSourceProvenance` de la
        capability quedan embebidas (spec §Parte 2), discriminadas por
        `kind`."""
        registro = _cargar(f"ice-{convencion}")
        provenance = registro["provenance"]

        assert provenance["derivation"]["kind"] == "derivation"
        assert provenance["derivation"]["recipe"]["capability"] == (
            "blite.ingesta.geojson.to_graph"
        )
        assert set(provenance["external_sources"]) == {
            "ice-subestaciones",
            "ice-lineas-transmision",
        }
        for source in provenance["external_sources"].values():
            assert source["kind"] == "external-source"
            assert source["uri"].startswith("https://")

    @pytest.mark.parametrize("convencion", _ICE_CONVENCIONES)
    def test_definicion_peso_documenta_la_convencion(self, convencion: str) -> None:
        registro = _cargar(f"ice-{convencion}")

        assert registro["definicion_peso"]
        if convencion == "uniforme":
            assert "circuito" in registro["definicion_peso"].lower()
        else:
            assert "tension" in registro["definicion_peso"].lower()


class TestVerifyCorpusDigestsGuard:
    """`scripts/verify_corpus_digests.py` generalizado — debe terminar en
    verde sobre TODO el corpus versionado, sin suposiciones de cardinalidad.
    Se corre in-process vía `runpy` (evita `subprocess` sobre un path fijo —
    S603 — y de paso deja `main()` instrumentado por `coverage`).

    [G1 2026-07-31] Este test PINNEABA "internos: 14/14" y se rompió al entrar
    el corpus C3 (9 puntos ⇒ 23) — la misma fragilidad de cardinalidad que la
    clase existe para prohibir, un piso más arriba. Ahora asserta el
    INVARIANTE (todo archivo self-consistente, todo pin que exista coincide)
    y que la cobertura incluye ambos directorios."""

    @staticmethod
    def _run_guard() -> tuple[int, str]:
        namespace = runpy.run_path(str(_VERIFY_SCRIPT), run_name="__not_main__")
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            exit_code = namespace["main"]()
        return exit_code, buffer.getvalue()

    def test_guard_exits_zero_over_the_full_corpus(self) -> None:
        exit_code, stdout = self._run_guard()

        assert exit_code == 0, stdout
        internos = re.search(r"internos: (\d+)/(\d+)", stdout)
        pinneados = re.search(r"pinneados: (\d+)/(\d+)", stdout)
        assert internos is not None and pinneados is not None, stdout
        # Todos self-consistentes y todos los pinneados coincidiendo — sin
        # fijar CUANTOS son: el corpus crece por diseño.
        assert internos.group(1) == internos.group(2), stdout
        assert pinneados.group(1) == pinneados.group(2), stdout
        assert int(internos.group(1)) >= 14, stdout

    def test_guard_cubre_los_dos_corpus_versionados(self) -> None:
        """Cobertura real, no solo cardinalidad: el guard corre sobre el
        corpus de islanding (reto 1) Y el corpus TFIM (reto 3)."""
        _, stdout = self._run_guard()

        assert "ieee6-flujo" in stdout
        assert "chain-n8-h10" in stdout

    def test_guard_no_longer_assumes_exactly_eight_files(self) -> None:
        """Regresión: el guard viejo tenia `if len(archivos) != 8` — verifica
        que la fuente ya no la trae (el corpus creció sin romper el
        veredicto)."""
        source = _VERIFY_SCRIPT.read_text(encoding="utf-8")

        assert "!= 8" not in source
