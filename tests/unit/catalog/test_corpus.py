"""Lectura de un corpus — las tres disciplinas de digest, y el fail-closed.

Lo que este archivo protege es C-13: que los tres digests sean tres COSAS
distintas y que ninguno se recalcule para que cuadre con otro. El día que
alguien «arregle» un digest que no cuadra reescribiéndolo, estos tests caen.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from blite.catalog.corpus import (
    CorpusError,
    embedded_digest,
    load_corpus,
)


def _sellar(document: dict[str, object]) -> dict[str, object]:
    """Un documento de corpus bien formado: su digest calculado sobre sí mismo."""
    return {**document, "digest": embedded_digest(document)}


def _escribir(root: Path, nombre: str, document: dict[str, object]) -> Path:
    path = root / f"{nombre}.json"
    path.write_text(json.dumps(document, indent=2), encoding="utf-8")
    return path


@pytest.fixture
def corpus(tmp_path: Path) -> Path:
    _escribir(tmp_path, "alfa", _sellar({"instancia": "alfa", "valor": 1}))
    _escribir(
        tmp_path,
        "beta",
        _sellar(
            {
                "instancia": "beta",
                "valor": 2,
                "corpus": "ejemplo",
                "dataset_id": "ejemplo/beta@v1",
                "procedencia": "synthetic_generated",
            }
        ),
    )
    return tmp_path


class TestLectura:
    def test_lee_las_instancias_ordenadas_por_archivo(self, corpus: Path) -> None:
        entradas = load_corpus(corpus)
        assert [e.instance for e in entradas] == ["alfa", "beta"]

    def test_la_identidad_opcional_ausente_no_se_inventa(self, corpus: Path) -> None:
        """Un corpus viejo sin `procedencia` reporta que no la tiene.

        Rellenarla con `""` publicaría «sin procedencia» cuando la verdad es
        «este corpus no declara procedencia» — que es otra cosa.
        """
        alfa, beta = load_corpus(corpus)
        assert alfa.identity == {}
        assert beta.identity["procedencia"] == "synthetic_generated"

    def test_un_directorio_declarado_que_no_existe_explota(
        self, tmp_path: Path
    ) -> None:
        with pytest.raises(CorpusError, match="no existe"):
            load_corpus(tmp_path / "fantasma")

    def test_un_directorio_vacio_es_un_corpus_vacio_no_un_error(
        self, tmp_path: Path
    ) -> None:
        """Declarar un dataset que todavía no tiene instancias es legítimo."""
        assert load_corpus(tmp_path) == ()


class TestLasTresDisciplinas:
    """C-13: tres digests correctos a la vez sobre el MISMO documento."""

    def test_los_tres_son_distintos_entre_si(self, corpus: Path) -> None:
        entrada = load_corpus(corpus)[0]
        assert (
            len(
                {entrada.file_sha256, entrada.embedded_digest, entrada.canonical_digest}
            )
            == 3
        )

    def test_el_de_bytes_es_el_que_reporta_sha256sum(self, corpus: Path) -> None:
        """Si esto se rompe, la verificación estándar falla en todo el mundo."""
        entrada = load_corpus(corpus)[0]
        crudo = (corpus / entrada.file_name).read_bytes()
        assert entrada.file_sha256 == hashlib.sha256(crudo).hexdigest()

    def test_el_de_bytes_cambia_con_el_formato_y_el_interno_no(
        self, tmp_path: Path
    ) -> None:
        """La razón de ser de la dualidad, en un solo test.

        El mismo documento guardado con otra indentación es otro archivo para
        `sha256sum` y la MISMA instancia para el corpus. Publicar solo uno de
        los dos digests deja a un tercero sin forma de saber cuál esperaba.
        """
        document = _sellar({"instancia": "alfa", "valor": 1})
        (tmp_path / "alfa.json").write_text(json.dumps(document), encoding="utf-8")
        compacto = load_corpus(tmp_path)[0]

        (tmp_path / "alfa.json").write_text(
            json.dumps(document, indent=4), encoding="utf-8"
        )
        indentado = load_corpus(tmp_path)[0]

        assert compacto.file_sha256 != indentado.file_sha256
        assert compacto.embedded_digest == indentado.embedded_digest
        assert compacto.canonical_digest == indentado.canonical_digest

    def test_el_interno_ignora_su_propia_llave_y_el_canonico_no(
        self, corpus: Path
    ) -> None:
        """Por qué el interno y el canónico difieren SIEMPRE, por construcción."""
        entrada = load_corpus(corpus)[0]
        document = json.loads((corpus / entrada.file_name).read_text(encoding="utf-8"))
        assert embedded_digest(document) == entrada.embedded_digest
        # Quitarle el digest al documento no cambia el interno...
        del document["digest"]
        assert embedded_digest(document) == entrada.embedded_digest


class TestFailClosed:
    def test_un_digest_que_no_cuadra_explota_en_vez_de_re_sellarse(
        self, tmp_path: Path
    ) -> None:
        """La regla del freeze §15.3, ejercida.

        Un archivo que dejó de coincidir con su digest es un incidente. El
        modo de falla que este test prohíbe es el cómodo: recalcular y seguir.
        """
        _escribir(
            tmp_path, "alfa", {"instancia": "alfa", "valor": 1, "digest": "0" * 64}
        )
        with pytest.raises(CorpusError, match="digest manda"):
            load_corpus(tmp_path)

    def test_sin_nombre_de_instancia_explota(self, tmp_path: Path) -> None:
        _escribir(tmp_path, "alfa", _sellar({"valor": 1}))
        with pytest.raises(CorpusError, match="instancia"):
            load_corpus(tmp_path)

    def test_sin_digest_explota(self, tmp_path: Path) -> None:
        _escribir(tmp_path, "alfa", {"instancia": "alfa", "valor": 1})
        with pytest.raises(CorpusError, match="digest"):
            load_corpus(tmp_path)

    def test_dos_archivos_con_la_misma_instancia_explotan(self, tmp_path: Path) -> None:
        """El nombre de instancia es la llave del catálogo.

        Con duplicados, `GET /datasets/{id}` devolvería dos filas con la misma
        llave y quien consuma elegiría una en silencio.
        """
        _escribir(tmp_path, "uno", _sellar({"instancia": "alfa", "valor": 1}))
        _escribir(tmp_path, "dos", _sellar({"instancia": "alfa", "valor": 2}))
        with pytest.raises(CorpusError, match="aparece en"):
            load_corpus(tmp_path)

    def test_un_json_roto_detiene_la_carga_entera(self, tmp_path: Path) -> None:
        """Un catálogo a medias es peor que ninguno: quien lo consuma no tiene
        forma de saber qué le faltó."""
        _escribir(tmp_path, "alfa", _sellar({"instancia": "alfa", "valor": 1}))
        (tmp_path / "roto.json").write_text("{no soy json", encoding="utf-8")
        with pytest.raises(CorpusError, match="no es JSON"):
            load_corpus(tmp_path)
