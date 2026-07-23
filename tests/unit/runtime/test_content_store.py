"""ContentStore mínimo de Fase 1 — freeze §12, alcance P0-3 (put/get/stat).

Contrato: el digest ES la identidad (O3/L3 — sha256, `put()` lo devuelve);
SO2: un digest es visible SOLO dentro de su dominio — la dedup física es
optimización interna, jamás canal de visibilidad (mismo contenido en dos
dominios = dos filas, cero fuga); `get()` recupera bytes exactos o falla
fuerte; ctx sin dominio = fail-closed.
"""

from __future__ import annotations

import hashlib

import pytest

from blite.content import Artifact, ContentStore
from blite.runtime.content_store import InMemoryContentStore

_CTX_A = {"domain_id": "domain-a"}
_CTX_B = {"domain_id": "domain-b"}


def test_put_returns_artifact_whose_digest_is_the_sha256_identity() -> None:
    store = InMemoryContentStore()
    data = b'{"x":1}'

    artifact = store.put(data, "application/json", _CTX_A)

    assert isinstance(store, ContentStore)
    assert isinstance(artifact, Artifact)
    assert artifact.digest == hashlib.sha256(data).hexdigest()
    assert artifact.domain_id == "domain-a"
    assert artifact.media_type == "application/json"
    assert artifact.size_bytes == len(data)


def test_get_recovers_the_exact_bytes() -> None:
    store = InMemoryContentStore()
    data = b"payload exacto \xc3\xb1"

    digest = store.put(data, "application/octet-stream", _CTX_A).digest

    assert store.get(digest, _CTX_A) == data


def test_put_is_idempotent_within_a_domain() -> None:
    store = InMemoryContentStore()

    first = store.put(b"same", "text/plain", _CTX_A)
    second = store.put(b"same", "text/plain", _CTX_A)

    # El contenido define su identidad (O3): mismo digest, misma fila.
    assert first == second


def test_same_content_in_two_domains_is_two_rows_zero_leak() -> None:
    store = InMemoryContentStore()

    in_a = store.put(b"shared", "text/plain", _CTX_A)
    in_b = store.put(b"shared", "text/plain", _CTX_B)

    assert in_a.digest == in_b.digest
    assert in_a.domain_id == "domain-a"
    assert in_b.domain_id == "domain-b"
    assert store.get(in_a.digest, _CTX_A) == b"shared"
    assert store.get(in_b.digest, _CTX_B) == b"shared"


def test_get_outside_the_domain_fails_strong_never_leaks() -> None:
    store = InMemoryContentStore()
    digest = store.put(b"solo domain-a", "text/plain", _CTX_A).digest

    # SO2: la dedup física jamás es canal de visibilidad (AX1b/Inv-E).
    with pytest.raises(KeyError):
        store.get(digest, _CTX_B)


def test_stat_returns_metadata_in_domain_and_none_outside() -> None:
    store = InMemoryContentStore()
    artifact = store.put(b"stat me", "text/plain", _CTX_A)

    assert store.stat(artifact.digest, _CTX_A) == artifact
    assert store.stat(artifact.digest, _CTX_B) is None
    assert store.stat("0" * 64, _CTX_A) is None


def test_ctx_without_domain_id_fails_closed() -> None:
    store = InMemoryContentStore()

    with pytest.raises(TypeError, match="domain_id"):
        store.put(b"x", "text/plain", {})
    with pytest.raises(TypeError, match="domain_id"):
        store.get("0" * 64, object())
