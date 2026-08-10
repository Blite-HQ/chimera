"""`GET /datasets` — el catálogo que un despliegue publica (O4/M10).

Dos cosas distintas se prueban acá y conviene no confundirlas:

* el **router** contra manifests sintéticos — incluido el caso que importa,
  que un dataset roto no se degrade a catálogo a medias;
* el **cableado** en la app real, porque un router perfecto que nadie monta no
  responde nada.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from chimera_api.catalog import create_catalog_router
from fastapi import FastAPI
from fastapi.testclient import TestClient

from blite.catalog.corpus import embedded_digest
from blite.runtime.distribution import DatasetSpec, DistributionManifest

_SPEC = {
    "path": "corpus",
    "description": "Un corpus de ejemplo.",
    "license": "https://creativecommons.org/publicdomain/zero/1.0/",
    "url": "https://example.org/ejemplo",
    "title": "Ejemplo",
}


def _sellar(document: dict[str, Any]) -> dict[str, Any]:
    return {**document, "digest": embedded_digest(document)}


@pytest.fixture
def raiz(tmp_path: Path) -> Path:
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "alfa.json").write_text(
        json.dumps(_sellar({"instancia": "alfa", "valor": 1})), encoding="utf-8"
    )
    return tmp_path


@pytest.fixture
def cliente(raiz: Path) -> TestClient:
    manifest = DistributionManifest(datasets={"ejemplo": DatasetSpec(**_SPEC)})
    app = FastAPI()
    app.include_router(create_catalog_router(manifest, raiz))
    return TestClient(app)


class TestListado:
    def test_lista_lo_declarado_con_su_licencia_y_cuenta(
        self, cliente: TestClient
    ) -> None:
        cuerpo = cliente.get("/datasets").json()
        assert cuerpo == [
            {
                "dataset_id": "ejemplo",
                "title": "Ejemplo",
                "description": "Un corpus de ejemplo.",
                "license": "https://creativecommons.org/publicdomain/zero/1.0/",
                "url": "https://example.org/ejemplo",
                "version": "1.0.0",
                "instance_count": 1,
            }
        ]

    def test_un_despliegue_sin_datasets_responde_lista_vacia_no_404(
        self, tmp_path: Path
    ) -> None:
        """«Este despliegue no publica datos» es una respuesta, no un error.

        Una ruta que aparece y desaparece según la configuración es peor de
        operar que una que siempre está y a veces está vacía.
        """
        app = FastAPI()
        app.include_router(create_catalog_router(DistributionManifest(), tmp_path))
        respuesta = TestClient(app).get("/datasets")
        assert respuesta.status_code == 200
        assert respuesta.json() == []


class TestDetalle:
    def test_cada_instancia_trae_sus_tres_digests(self, cliente: TestClient) -> None:
        instancia = cliente.get("/datasets/ejemplo").json()["instances"][0]
        assert instancia["instance"] == "alfa"
        assert (
            len(
                {
                    instancia["file_sha256"],
                    instancia["embedded_digest"],
                    instancia["canonical_digest"],
                }
            )
            == 3
        )

    def test_un_dataset_no_declarado_es_404(self, cliente: TestClient) -> None:
        assert cliente.get("/datasets/fantasma").status_code == 404


class TestCroissant:
    def test_responde_el_documento_jsonld(self, cliente: TestClient) -> None:
        document = cliente.get("/datasets/ejemplo/croissant").json()
        assert document["@type"] == "sc:Dataset"
        assert document["name"] == "ejemplo"
        assert document["conformsTo"] == "http://mlcommons.org/croissant/1.0"

    def test_un_dataset_no_declarado_es_404_tambien_aca(
        self, cliente: TestClient
    ) -> None:
        assert cliente.get("/datasets/fantasma/croissant").status_code == 404


class TestDespliegueRoto:
    """La distinción que importa para quien opera: 404 es «no existe», 500 es
    «existe y está roto». Confundirlas manda a buscar el problema al lado
    equivocado."""

    def test_un_directorio_declarado_que_no_existe_es_500(self, tmp_path: Path) -> None:
        manifest = DistributionManifest(
            datasets={"ejemplo": DatasetSpec(**{**_SPEC, "path": "no-existe"})}
        )
        app = FastAPI()
        app.include_router(create_catalog_router(manifest, tmp_path))
        assert (
            TestClient(app, raise_server_exceptions=False)
            .get("/datasets/ejemplo")
            .status_code
            == 500
        )

    def test_un_digest_que_no_cuadra_no_se_publica_a_medias(
        self, raiz: Path, cliente: TestClient
    ) -> None:
        """El corpus deja de ser publicable ENTERO, no se omite la fila mala.

        Publicar el resto en silencio entregaría un catálogo que se ve sano y
        no lo está — exactamente el modo de falla que la disciplina de digests
        existe para impedir.
        """
        (raiz / "corpus" / "beta.json").write_text(
            json.dumps({"instancia": "beta", "valor": 2, "digest": "0" * 64}),
            encoding="utf-8",
        )
        respuesta = TestClient(cliente.app, raise_server_exceptions=False).get(
            "/datasets/ejemplo"
        )
        assert respuesta.status_code == 500


def test_la_app_real_monta_el_catalogo() -> None:
    """Cableado: un router impecable que nadie incluye no responde nada."""
    from chimera_api.app import create_app

    from blite.events import create_event_store

    cliente = TestClient(create_app(create_event_store()))
    respuesta = cliente.get("/datasets")

    assert respuesta.status_code == 200
    assert {fila["dataset_id"] for fila in respuesta.json()} == {
        "tfim-corpus",
        "tabular-corpus",
    }
