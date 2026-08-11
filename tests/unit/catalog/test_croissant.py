"""El builder de Croissant — forma del documento, sin validador de por medio.

Acá se prueba lo que decidimos nosotros: dónde va cada digest y qué columnas
existen. Que el documento sea Croissant VÁLIDO lo prueba el validador real en
`tests/integration/test_croissant_export.py`; las dos mitades son distintas y
ninguna reemplaza a la otra.
"""

from __future__ import annotations

from typing import Any

from blite.catalog.corpus import InstanceEntry
from blite.catalog.croissant import (
    CROISSANT_CONFORMS_TO,
    DIGEST_DISCIPLINES,
    DatasetDescription,
    build_croissant,
)

DESCRIPCION = DatasetDescription(
    dataset_id="ejemplo-corpus",
    name="Ejemplo",
    description="Un corpus de ejemplo.",
    license="https://creativecommons.org/publicdomain/zero/1.0/",
    url="https://example.org/ejemplo",
)


def _entrada(nombre: str, **identidad: str) -> InstanceEntry:
    return InstanceEntry(
        instance=nombre,
        file_name=f"{nombre}.json",
        file_sha256="a" * 64,
        embedded_digest="b" * 64,
        canonical_digest="c" * 64,
        identity=identidad,
    )


def _record_set(document: dict[str, Any]) -> dict[str, Any]:
    return document["recordSet"][0]


def _campos(document: dict[str, Any]) -> list[str]:
    return [f["name"] for f in _record_set(document)["field"]]


class TestDualidadDeDigests:
    """C-13: publicar «el digest» sin decir cuál rompe la verificabilidad."""

    def test_el_sha256_del_fileobject_es_el_de_los_bytes(self) -> None:
        """El spec de Croissant reserva `sha256` para los bytes distribuidos.

        Meter ahí el digest interno haría que `sha256sum` fallara para todo el
        que descargue el archivo — una verificación que falla siempre enseña a
        ignorar la verificación.
        """
        document = build_croissant(DESCRIPCION, [_entrada("alfa")])
        assert document["distribution"][0]["sha256"] == "a" * 64

    def test_los_tres_digests_viajan_etiquetados_en_el_record_set(self) -> None:
        document = build_croissant(DESCRIPCION, [_entrada("alfa")])
        for nombre, _ in DIGEST_DISCIPLINES:
            assert nombre in _campos(document)

    def test_cada_disciplina_viaja_con_su_explicacion(self) -> None:
        """Un tercero no debería tener que leer nuestro repo para saber cuál
        es cuál: la descripción va DENTRO del export."""
        document = build_croissant(DESCRIPCION, [_entrada("alfa")])
        por_nombre = {
            f["name"]: f["description"] for f in _record_set(document)["field"]
        }
        for nombre, texto in DIGEST_DISCIPLINES:
            assert por_nombre[nombre] == texto

    def test_los_datos_traen_los_tres_valores_por_instancia(self) -> None:
        document = build_croissant(DESCRIPCION, [_entrada("alfa")])
        fila = _record_set(document)["data"][0]
        assert fila["instances/file_sha256"] == "a" * 64
        assert fila["instances/embedded_digest"] == "b" * 64
        assert fila["instances/canonical_digest"] == "c" * 64


class TestColumnasDeIdentidad:
    def test_solo_entran_las_llaves_que_todas_las_instancias_traen(self) -> None:
        """Una columna a medias obligaría a rellenar el resto con vacío, y un
        `procedencia: ""` publicado se lee como «sin procedencia»."""
        document = build_croissant(
            DESCRIPCION,
            [
                _entrada("alfa", corpus="ejemplo", procedencia="curated_internal"),
                _entrada("beta", corpus="ejemplo"),
            ],
        )
        campos = _campos(document)
        assert "corpus" in campos
        assert "procedencia" not in campos

    def test_un_corpus_sin_identidad_opcional_no_gana_columnas_vacias(self) -> None:
        document = build_croissant(DESCRIPCION, [_entrada("alfa")])
        assert _campos(document) == [
            "instance",
            "file",
            *(nombre for nombre, _ in DIGEST_DISCIPLINES),
        ]


class TestMetadatos:
    def test_declara_la_version_del_spec_a_la_que_se_ajusta(self) -> None:
        document = build_croissant(DESCRIPCION, [_entrada("alfa")])
        assert document["conformsTo"] == CROISSANT_CONFORMS_TO

    def test_el_titulo_legible_no_pisa_el_identificador(self) -> None:
        """`name` en Croissant es el id; el título va en `alternateName`."""
        document = build_croissant(DESCRIPCION, [_entrada("alfa")])
        assert document["name"] == "ejemplo-corpus"
        assert document["alternateName"] == "Ejemplo"

    def test_los_opcionales_ausentes_no_aparecen_vacios(self) -> None:
        document = build_croissant(DESCRIPCION, [_entrada("alfa")])
        assert "citeAs" not in document
        assert "datePublished" not in document

    def test_un_corpus_vacio_produce_un_documento_sin_instancias(self) -> None:
        """Declarar un dataset que aún no tiene datos no debe explotar."""
        document = build_croissant(DESCRIPCION, [])
        assert document["distribution"] == []
        assert _record_set(document)["data"] == []
