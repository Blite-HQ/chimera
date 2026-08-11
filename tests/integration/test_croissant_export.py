"""El export Croissant, contra el validador REAL de MLCommons.

Un export «según el spec» que ninguna herramienta acepta no publica nada. Este
archivo corre `mlcroissant` —la implementación de referencia de MLCommons—
sobre los datasets que ESTE despliegue declara de verdad, no sobre un fixture:
si mañana alguien agrega un dataset al `distribution.yaml` con una licencia mal
puesta o un digest que no cuadra, esto cae acá y no en la máquina de quien lo
descargue.

Lo que el validador aporta y un test de forma no puede: que el `@context` sea
el estándar, que el JSON-LD resuelva, que el `RecordSet` sea leíble y que los
`@id` referenciados existan. Lo que NO aporta —dónde va cada digest, qué
columnas hay— se prueba en `tests/unit/catalog/test_croissant.py`.
"""

# pyright: reportMissingTypeStubs=false
# ^ `mlcroissant` no publica stubs. Es la implementación de REFERENCIA de
#   MLCommons, y usarla es justamente el punto: validar contra el cliente real
#   del ecosistema en vez de contra un modelo nuestro del formato. La regla se
#   apaga acá —y solo acá—, con los accesos sin tipar acotados a `_registros`.

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, cast

import mlcroissant as mlc
import pytest

from blite.catalog.corpus import InstanceEntry, load_corpus
from blite.catalog.croissant import build_croissant
from blite.runtime.distribution import DatasetSpec, load_distribution_manifest

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = load_distribution_manifest(ROOT / "distributions/chimera/distribution.yaml")

DECLARADOS = sorted(MANIFEST.datasets)


@pytest.fixture(params=DECLARADOS, ids=DECLARADOS)
def dataset_id(request: pytest.FixtureRequest) -> str:
    return str(request.param)


def _spec(dataset_id: str) -> DatasetSpec:
    return MANIFEST.datasets[dataset_id]


def _instancias(dataset_id: str) -> tuple[InstanceEntry, ...]:
    return load_corpus(ROOT / _spec(dataset_id).path)


def _documento(dataset_id: str) -> dict[str, Any]:
    spec = _spec(dataset_id)
    return build_croissant(
        spec.description_for_export(dataset_id), _instancias(dataset_id)
    )


def _cargar_con_mlcroissant(document: dict[str, Any], tmp_path: Path) -> mlc.Dataset:
    """`mlcroissant` lee de disco; el documento se materializa para dárselo."""
    path = tmp_path / "croissant.json"
    path.write_text(json.dumps(document, indent=2), encoding="utf-8")
    return mlc.Dataset(jsonld=str(path))


def _registros(dataset: mlc.Dataset) -> list[dict[str, Any]]:
    """`records()` devuelve un iterable sin tipar; el cast lo dice una vez.

    La librería es la implementación de REFERENCIA de MLCommons y no publica
    stubs. Ese es el precio de validar contra el cliente real en vez de contra
    un modelo nuestro del formato, y se paga acá, acotado a esta frontera.
    """
    crudos: Any = dataset.records("instances")
    return [cast("dict[str, Any]", record) for record in crudos]


def test_hay_datasets_declarados_que_validar() -> None:
    """Guard del propio guard.

    Si alguien vacía `datasets:` del manifest, los tests parametrizados de
    abajo pasarían a cero casos y este archivo quedaría verde sin haber
    validado nada — el modo de falla más silencioso que existe.
    """
    assert DECLARADOS


def test_el_validador_de_mlcommons_no_reporta_errores(
    dataset_id: str, tmp_path: Path
) -> None:
    dataset = _cargar_con_mlcroissant(_documento(dataset_id), tmp_path)
    assert dataset.metadata.issues.errors == set()


def test_tampoco_reporta_avisos(dataset_id: str, tmp_path: Path) -> None:
    """Los avisos son propiedades RECOMENDADAS que faltan (cita, fecha…).

    Se exigen igual: un dataset publicado sin decir cómo citarlo es menos
    usable, que es justo lo que este export existe para arreglar. Si una
    versión nueva de `mlcroissant` recomienda algo más, esto cae y se decide
    qué hacer — en vez de acumular avisos que nadie mira.
    """
    dataset = _cargar_con_mlcroissant(_documento(dataset_id), tmp_path)
    assert dataset.metadata.issues.warnings == set()


def test_un_consumidor_real_lee_las_instancias_y_sus_digests(
    dataset_id: str, tmp_path: Path
) -> None:
    """El round-trip completo: se publica, se carga con la librería del
    ecosistema, y lo que sale es lo mismo que el catálogo tiene.

    Esto es lo que distingue «genera un JSON con forma de Croissant» de
    «publica un dataset que alguien puede usar».
    """
    # Arrange
    esperadas = {entry.instance: entry for entry in _instancias(dataset_id)}
    dataset = _cargar_con_mlcroissant(_documento(dataset_id), tmp_path)

    # Act
    leidas = {
        str(record["instances/instance"]): record for record in _registros(dataset)
    }

    # Assert
    assert set(leidas) == set(esperadas)
    for nombre, record in leidas.items():
        entry = esperadas[nombre]
        assert record["instances/file_sha256"] == entry.file_sha256
        assert record["instances/embedded_digest"] == entry.embedded_digest
        assert record["instances/canonical_digest"] == entry.canonical_digest


def test_el_sha256_publicado_verifica_contra_el_archivo_real(
    dataset_id: str, tmp_path: Path
) -> None:
    """La promesa que hace `sha256` en Croissant, comprobada contra el disco.

    Es la verificación que hará quien descargue el dataset. Si acá pasa y allá
    falla, publicamos una promesa rota.
    """
    directorio = ROOT / _spec(dataset_id).path
    dataset = _cargar_con_mlcroissant(_documento(dataset_id), tmp_path)

    publicados = 0
    for recurso in dataset.metadata.distribution:
        # Solo emitimos `FileObject`s; el `FileSet` del vocabulario no aplica
        # (ver el docstring del builder). Estrechar acá deja explícito que un
        # recurso de otro tipo NO se estaría verificando.
        assert isinstance(recurso, mlc.FileObject)
        crudo = (directorio / str(recurso.name)).read_bytes()
        assert recurso.sha256 == hashlib.sha256(crudo).hexdigest()
        publicados += 1

    assert publicados == len(_instancias(dataset_id))
