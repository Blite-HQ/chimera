"""Unit tests de `capabilities_sim_api.recompute_seeded_failure`.

Corren contra un corpus sintético diminuto (números computables a mano) en
`tmp_path` — el corpus real (ieee14) lo cubre el seed
`tests/seeds/test_seed_ciencia_falla_sembrada.py`. La receta de digest es la
del corpus congelado (knowledge/islanding/01 §1.6): SHA-256 del JSON canónico
(claves ordenadas, sin espacios, ensure_ascii) SIN el campo `digest`.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from capabilities_sim_api import (
    CorpusIntegrityError,
    recompute_seeded_failure,
)


def _write_instance(
    corpus_dir: Path,
    *,
    family: str,
    convention: str,
    n_nodes: int,
    edges: list[list[int]],
    optimum: int,
    canonical: list[int],
    tamper_digest: bool = False,
) -> Path:
    """Escribe una instancia con el digest canónico de la receta §1.6."""
    record: dict[str, Any] = {
        "instancia": family,
        "convencion": convention,
        "n_nodos": n_nodes,
        "aristas": edges,
        "escala": 1,
        "optimo": optimum,
        "asignacion_canonica": canonical,
        "metodos": ["cpsat", "bruteforce"],
        "solver_status": "OPTIMAL",
    }
    canonical_json = json.dumps(
        record, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    digest = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
    if tamper_digest:
        digest = "0" * 64
    path = corpus_dir / f"{family}-{convention}.json"
    path.write_text(
        json.dumps({**record, "digest": digest}, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


@pytest.fixture
def corpus_dir(tmp_path: Path) -> Path:
    """Corpus sintético: familia `tri` (triángulo ponderado + su uniforme).

    tri-flujo: aristas (0,1,5) (0,2,3) (1,2,2) — óptimo 8 con x=[0,1,1];
    ningún flip degrada cero. tri-uniforme: pesos 1 — óptimo 2 con
    x=[0,0,1]; los flips de 0 y 1 degradan cero (minas).
    """
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    _write_instance(
        corpus,
        family="tri",
        convention="flujo",
        n_nodes=3,
        edges=[[0, 1, 5], [0, 2, 3], [1, 2, 2]],
        optimum=8,
        canonical=[0, 1, 1],
    )
    _write_instance(
        corpus,
        family="tri",
        convention="uniforme",
        n_nodes=3,
        edges=[[0, 1, 1], [0, 2, 1], [1, 2, 1]],
        optimum=2,
        canonical=[0, 0, 1],
    )
    return corpus


class TestRecompute:
    def test_flip_degrades_cut_and_reports_ratio(self, corpus_dir: Path) -> None:
        # Arrange — tri-flujo óptimo 8; flip del bus 1: [0,0,1] corta (0,2)+(1,2)=5
        result = recompute_seeded_failure(
            instance="tri-flujo", bus=1, corpus_dir=corpus_dir
        )

        # Assert
        assert result.cut_value == 5
        assert result.optimum == 8
        assert result.r == 5 / 8

    def test_forbidden_lists_are_zero_degradation_flips_per_convention(
        self, corpus_dir: Path
    ) -> None:
        # Act
        result = recompute_seeded_failure(
            instance="tri-flujo", bus=1, corpus_dir=corpus_dir
        )

        # Assert — en tri-flujo ningún flip mantiene el óptimo; en tri-uniforme
        # los flips de 0 y 1 dan otro corte óptimo (minas del guion §15.5)
        assert result.forbidden_flow == []
        assert result.forbidden_uniform == [0, 1]

    def test_flipping_a_zero_degradation_bus_reports_ratio_one(
        self, corpus_dir: Path
    ) -> None:
        # Act — bus 1 es mina en uniforme: el corte no se degrada
        result = recompute_seeded_failure(
            instance="tri-uniforme", bus=1, corpus_dir=corpus_dir
        )

        # Assert — la API recomputa; ser mina es dato, no error
        assert result.cut_value == result.optimum
        assert result.r == 1.0


class TestValidation:
    def test_rejects_malformed_instance_name(self, corpus_dir: Path) -> None:
        with pytest.raises(ValueError, match="instance"):
            recompute_seeded_failure(instance="tri_flujo", bus=1, corpus_dir=corpus_dir)

    def test_rejects_unknown_convention(self, corpus_dir: Path) -> None:
        with pytest.raises(ValueError, match="conven"):
            recompute_seeded_failure(instance="tri-pesos", bus=1, corpus_dir=corpus_dir)

    def test_rejects_bus_out_of_range(self, corpus_dir: Path) -> None:
        with pytest.raises(ValueError, match="bus"):
            recompute_seeded_failure(instance="tri-flujo", bus=3, corpus_dir=corpus_dir)

    def test_missing_instance_file_raises_file_not_found(
        self, corpus_dir: Path
    ) -> None:
        with pytest.raises(FileNotFoundError):
            recompute_seeded_failure(
                instance="cuadrado-flujo", bus=1, corpus_dir=corpus_dir
            )

    def test_rejects_family_with_path_traversal_characters(
        self, corpus_dir: Path
    ) -> None:
        # La familia viaja a una ruta de archivo: solo [a-z0-9] es válido
        with pytest.raises(ValueError, match="familia"):
            recompute_seeded_failure(
                instance="../evil-flujo", bus=1, corpus_dir=corpus_dir
            )


class TestDefaultCorpusDir:
    def test_finds_real_corpus_independent_of_cwd(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        # Arrange — cwd fuera del repo: el default resuelve vía __file__
        monkeypatch.chdir(tmp_path)

        # Act
        result = recompute_seeded_failure(instance="ieee14-flujo", bus=1)

        # Assert — encontró el corpus congelado real
        assert result.optimum == 57_070


class TestCorpusIntegrity:
    def test_digest_mismatch_fails_loud(self, tmp_path: Path) -> None:
        # Arrange — instancia con digest adulterado
        corpus = tmp_path / "corpus"
        corpus.mkdir()
        _write_instance(
            corpus,
            family="tri",
            convention="flujo",
            n_nodes=3,
            edges=[[0, 1, 5], [0, 2, 3], [1, 2, 2]],
            optimum=8,
            canonical=[0, 1, 1],
            tamper_digest=True,
        )
        _write_instance(
            corpus,
            family="tri",
            convention="uniforme",
            n_nodes=3,
            edges=[[0, 1, 1], [0, 2, 1], [1, 2, 1]],
            optimum=2,
            canonical=[0, 0, 1],
        )

        # Act / Assert
        with pytest.raises(CorpusIntegrityError, match="digest"):
            recompute_seeded_failure(instance="tri-flujo", bus=1, corpus_dir=corpus)

    def test_canonical_assignment_inconsistent_with_optimum_fails_loud(
        self, tmp_path: Path
    ) -> None:
        # Arrange — digest válido pero óptimo mentido: el digest es
        # auto-referencial, la consistencia corte(canónica)==óptimo no
        corpus = tmp_path / "corpus"
        corpus.mkdir()
        _write_instance(
            corpus,
            family="tri",
            convention="flujo",
            n_nodes=3,
            edges=[[0, 1, 5], [0, 2, 3], [1, 2, 2]],
            optimum=9,
            canonical=[0, 1, 1],
        )
        _write_instance(
            corpus,
            family="tri",
            convention="uniforme",
            n_nodes=3,
            edges=[[0, 1, 1], [0, 2, 1], [1, 2, 1]],
            optimum=2,
            canonical=[0, 0, 1],
        )

        # Act / Assert
        with pytest.raises(CorpusIntegrityError, match="canonica"):
            recompute_seeded_failure(instance="tri-flujo", bus=1, corpus_dir=corpus)
