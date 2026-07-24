"""Topologia electrica ieee14 congelada — verificacion por isla REAL (Task 2).

Carga el envelope `knowledge/islanding/ieee14-topology.json`
(`scripts/gen_ieee14_topology.py`), reconstruye `ExecutionLimits` desde el
dato, e instancia `ExecutionVerifier` real (pandapower, sin mocks) contra un
`OptimalityClaim` sobre el MISMO grafo del corpus congelado
(`knowledge/islanding/corpus/ieee14-flujo.json`, 20 aristas, buses 0..13).

Sin el JSON/adapter, todo lo de abajo falla (RED): no hay dato electrico real
para ieee14 y `ExecutionVerifier` no tiene topologia que cargar.

Biparticion VALIDA congelada (D4, docs/mvp/decisiones.md) — se documenta y
se re-verifica con networkx en este mismo archivo (no se congela a ciegas):
  A = {0,1,2,3,4,5}         (fuentes case14 presentes: 0,1,2,5)
  B = {6,7,8,9,10,11,12,13} (fuente case14 presente: 7)
Ambos lados son subgrafos conexos del grafo del corpus.

Biparticion INVALIDA (la del demo original, brief SS"Hechos verificados"):
  A2 = {0,1,2,3,4,5,6}, B2 = {7,8,9,10,11,12,13}
B2 queda desconectada: el bus 7 (fuente) no tiene ninguna arista interna
hacia el resto de B2 (su unica arista en el corpus es 6-7, y 6 esta en A2)
-> hard-fail por `island_connectivity`, ANTES de intentar correr el flujo.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import networkx as nx

from blite.verification.context import InvocationContext
from blite.verification.evidence import ExecutionPredicate
from blite.verification.exact_solver import MaxCutInstance, OptimalityClaim
from blite.verification.execution import ExecutionLimits, ExecutionVerifier

CTX = InvocationContext(
    run_id="run-ieee14-exec", actor_id="service:runtime", domain_id="dom-ieee14"
)
ANCHOR_DIGEST = hashlib.sha256(b"anchor:ieee14-topology-v1").hexdigest()


def _find_repo_root() -> Path:
    marker = Path("knowledge") / "islanding" / "ieee14-topology.json"
    for base in (Path(__file__).resolve(), *Path(__file__).resolve().parents):
        if (base / marker).is_file():
            return base
    msg = "knowledge/islanding/ieee14-topology.json no encontrado sobre este archivo"
    raise FileNotFoundError(msg)


def _cargar_envelope() -> dict[str, Any]:
    ruta = _find_repo_root() / "knowledge" / "islanding" / "ieee14-topology.json"
    return json.loads(ruta.read_text(encoding="utf-8"))


def _digest_canonico(envelope: dict[str, Any]) -> str:
    sin_digest = {k: v for k, v in envelope.items() if k != "digest"}
    canonico = json.dumps(
        sin_digest, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(canonico.encode("utf-8")).hexdigest()


def _cargar_edges_corpus() -> tuple[tuple[int, int, int], ...]:
    ruta = (
        _find_repo_root() / "knowledge" / "islanding" / "corpus" / "ieee14-flujo.json"
    )
    registro = json.loads(ruta.read_text(encoding="utf-8"))
    return tuple((int(i), int(j), int(w)) for i, j, w in registro["aristas"])


ENVELOPE = _cargar_envelope()
EDGES = _cargar_edges_corpus()
GRAPH = MaxCutInstance(n_nodes=14, edges=EDGES)


def _verifier() -> ExecutionVerifier:
    limits = ExecutionLimits(**ENVELOPE["limits"])
    return ExecutionVerifier(
        verifier_id="verifier:pandapower-ieee14",
        independence_group="leg-execution",
        anchor_digest=ANCHOR_DIGEST,
        topology=ENVELOPE["topology"],
        limits=limits,
    )


def _claim(assignment: tuple[int, ...], statement: str) -> OptimalityClaim:
    return OptimalityClaim(
        instance=GRAPH,
        assignment=assignment,
        canonical_statement=statement,
        scope={"instancia": "ieee14"},
    )


def _predicate_of(att: Any) -> ExecutionPredicate:
    assert isinstance(att.predicate, ExecutionPredicate)
    return att.predicate


class TestDigest:
    def test_digest_embebido_reproduce_el_canonico(self) -> None:
        assert ENVELOPE["digest"] == _digest_canonico(ENVELOPE)


class TestSanidadRedCompleta:
    """Una isla = los 14 buses de un lado: el modelo declarado esta bien
    formado y converge en banda por si solo, sin particion."""

    def test_toda_la_red_como_una_sola_isla_pasa(self) -> None:
        assignment = tuple([0] * 14)
        att = _verifier().verify(
            _claim(assignment, "ieee14 completa es una isla factible"), CTX
        )

        assert att.verdict == "pass"
        assert all(c.passed for c in _predicate_of(att).checks)


class TestIslaValida:
    ISLA_A = frozenset({0, 1, 2, 3, 4, 5})
    ISLA_B = frozenset({6, 7, 8, 9, 10, 11, 12, 13})

    def test_biparticion_congelada_es_conexa_por_lado_y_con_fuente(self) -> None:
        """No se congela a ciegas: se re-verifica con networkx en el test."""
        grafo = nx.Graph((i, j) for i, j, _ in EDGES)
        fuentes = {int(s["bus"]) for s in ENVELOPE["topology"]["slack"]}

        assert set(self.ISLA_A) | set(self.ISLA_B) == set(range(14))
        assert nx.is_connected(grafo.subgraph(self.ISLA_A))
        assert nx.is_connected(grafo.subgraph(self.ISLA_B))
        assert self.ISLA_A & fuentes
        assert self.ISLA_B & fuentes

    def test_biparticion_valida_pasa(self) -> None:
        assignment = tuple(0 if b in self.ISLA_A else 1 for b in range(14))
        att = _verifier().verify(
            _claim(assignment, "biparticion ieee14 electricamente factible"), CTX
        )

        assert att.verdict == "pass"
        assert all(c.passed for c in _predicate_of(att).checks)


class TestIslaInvalida:
    ISLA_A2 = frozenset({0, 1, 2, 3, 4, 5, 6})
    ISLA_B2 = frozenset({7, 8, 9, 10, 11, 12, 13})

    def test_isla_b2_esta_desconectada_en_el_grafo(self) -> None:
        """Confirma el hecho verificado del brief antes de aserta el fail."""
        grafo = nx.Graph((i, j) for i, j, _ in EDGES)

        assert not nx.is_connected(grafo.subgraph(self.ISLA_B2))

    def test_isla_desconectada_falla_por_island_connectivity(self) -> None:
        assignment = tuple(0 if b in self.ISLA_A2 else 1 for b in range(14))
        att = _verifier().verify(
            _claim(assignment, "particion con isla desconectada (bus 7)"), CTX
        )

        assert att.verdict == "fail"
        fallidos = {c.name for c in _predicate_of(att).checks if not c.passed}
        assert any(name.endswith("island_connectivity") for name in fallidos)
