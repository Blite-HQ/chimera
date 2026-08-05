"""
Adapter de `ContentStore` sobre disco (P10/M24).

El puerto está congelado desde el freeze §12 y llevaba sin adapter: `put`
devolvía el digest en la letra y en ninguna parte del código. Esto lo
materializa con la propiedad que el puerto exige — **el contenido define su
identidad** (O3/L3): el mismo archivo subido dos veces es UN artifact, y el
digest es la dirección, no un metadato al lado.

SO2 (partición por dominio) se respeta literal: un digest es visible solo
dentro de su dominio. La deduplicación física entre dominios sería una
optimización interna y JAMÁS un canal de visibilidad, así que este adapter
particiona por dominio en disco y punto.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from blite.content import Artifact, ContentStore
from blite.content_fs import FileContext, FilesystemContentStore


@pytest.fixture()
def store(tmp_path: Path) -> FilesystemContentStore:
    return FilesystemContentStore(root=tmp_path)


_CTX = FileContext(domain_id="d-default")
_OTRO_DOMINIO = FileContext(domain_id="d-otro")


def test_cumple_el_puerto(store: FilesystemContentStore) -> None:
    assert isinstance(store, ContentStore)


def test_put_devuelve_el_digest_del_contenido(store: FilesystemContentStore) -> None:
    data = b"%PDF-1.7 un paper"

    artifact = store.put(data, "application/pdf", _CTX)

    assert artifact.digest == hashlib.sha256(data).hexdigest()
    assert artifact.size_bytes == len(data)
    assert artifact.media_type == "application/pdf"
    assert artifact.domain_id == "d-default"


def test_roundtrip_byte_a_byte(store: FilesystemContentStore) -> None:
    data = bytes(range(256))

    artifact = store.put(data, "application/octet-stream", _CTX)

    assert store.get(artifact.digest, _CTX) == data


def test_el_mismo_contenido_es_un_solo_artifact(store: FilesystemContentStore) -> None:
    """O3: el contenido define su identidad. Subirlo dos veces no crea dos."""
    primero = store.put(b"mismo", "text/plain", _CTX)
    segundo = store.put(b"mismo", "text/plain", _CTX)

    assert primero.digest == segundo.digest
    assert len(store.list(_CTX)) == 1


def test_un_digest_no_es_visible_desde_otro_dominio(
    store: FilesystemContentStore,
) -> None:
    """SO2: sin Channel con 'read', el dominio ajeno no lo ve — ni por stat."""
    artifact = store.put(b"secreto del dominio", "text/plain", _CTX)

    assert store.stat(artifact.digest, _OTRO_DOMINIO) is None
    assert store.list(_OTRO_DOMINIO) == ()
    with pytest.raises(KeyError):
        store.get(artifact.digest, _OTRO_DOMINIO)


def test_stat_de_un_digest_desconocido_es_none(store: FilesystemContentStore) -> None:
    assert store.stat("f" * 64, _CTX) is None


def test_get_de_un_digest_desconocido_falla_fuerte(
    store: FilesystemContentStore,
) -> None:
    """El puerto dice «o falla fuerte»: devolver b'' sería inventar contenido."""
    with pytest.raises(KeyError):
        store.get("f" * 64, _CTX)


def test_list_ordena_por_fecha_descendente(store: FilesystemContentStore) -> None:
    """Lo último subido primero — es lo que un listado de archivos necesita."""
    viejo = store.put(b"a", "text/plain", _CTX)
    nuevo = store.put(b"b", "text/plain", _CTX)

    digests = [a.digest for a in store.list(_CTX)]

    assert digests.index(nuevo.digest) < digests.index(viejo.digest)


def test_un_digest_con_traversal_no_sale_del_root(
    store: FilesystemContentStore,
) -> None:
    """El digest viene de la URL: un `../` no puede leer fuera del store."""
    with pytest.raises(KeyError):
        store.get("../../etc/passwd", _CTX)


def test_el_nombre_original_viaja_como_metadato(store: FilesystemContentStore) -> None:
    """El nombre NO es la identidad (el digest lo es) pero un humano necesita
    leerlo: viaja al lado, sin participar del direccionamiento."""
    artifact = store.put(b"x", "application/pdf", _CTX, filename="paper-qaoa.pdf")

    assert store.stat(artifact.digest, _CTX) is not None
    assert store.filename(artifact.digest, _CTX) == "paper-qaoa.pdf"


def test_artifact_es_el_modelo_congelado(store: FilesystemContentStore) -> None:
    assert isinstance(store.put(b"x", "text/plain", _CTX), Artifact)
