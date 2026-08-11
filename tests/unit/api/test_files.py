"""
Rutas de archivos del proyecto — `POST /files`, `GET /files`,
`GET /files/{digest}` (P10/M24).

Un archivo subido acá es un INSUMO con procedencia, jamás evidencia: el freeze
§7 es explícito en que contenido recuperado entra como `assumptions` con su
`ref{name, digest}` y nunca como `Attestation`. Por eso lo único que estas
rutas prometen es lo que pueden cumplir — que los bytes se recuperan idénticos
y que su digest los nombra.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import httpx
import pytest
from chimera_api.app import create_app
from fastapi.testclient import TestClient

from blite.events import create_event_store
from blite.runtime.registry import EntryPointRegistry


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("CHIMERA_FILES_DIR", str(tmp_path))
    return TestClient(create_app(create_event_store(), registry=EntryPointRegistry({})))


def _post_file(client: TestClient, data: bytes, **headers: str) -> httpx.Response:
    return cast(
        httpx.Response,
        client.post(
            "/files",
            content=data,
            headers={"Content-Type": "application/pdf", **headers},
        ),
    )


def _get(client: TestClient, url: str) -> httpx.Response:
    return cast(
        httpx.Response,
        client.get(url),
    )


def test_subir_devuelve_el_digest_del_contenido(client: TestClient) -> None:
    response = _post_file(client, b"%PDF-1.7 paper", **{"X-Filename": "qaoa.pdf"})

    assert response.status_code == 201
    body: dict[str, Any] = response.json()
    assert len(body["digest"]) == 64
    assert body["size_bytes"] == len(b"%PDF-1.7 paper")
    assert body["media_type"] == "application/pdf"
    assert body["filename"] == "qaoa.pdf"


def test_el_mismo_archivo_dos_veces_es_uno_solo(client: TestClient) -> None:
    """O3 — el contenido define su identidad; subirlo de nuevo no duplica."""
    primero = _post_file(client, b"mismo contenido").json()
    segundo = _post_file(client, b"mismo contenido").json()

    assert primero["digest"] == segundo["digest"]
    assert len(_get(client, "/files").json()) == 1


def test_listado_vacio_es_lista_vacia_no_error(client: TestClient) -> None:
    """Un proyecto sin archivos no es un fallo: es un proyecto sin archivos."""
    response = _get(client, "/files")

    assert response.status_code == 200
    assert response.json() == []


def test_descarga_devuelve_los_bytes_exactos(client: TestClient) -> None:
    data = bytes(range(256))
    digest = _post_file(
        client, data, **{"Content-Type": "application/octet-stream"}
    ).json()["digest"]

    response = _get(client, f"/files/{digest}")

    assert response.status_code == 200
    assert response.content == data


def test_un_digest_desconocido_es_404(client: TestClient) -> None:
    assert _get(client, f"/files/{'a' * 64}").status_code == 404


def test_un_digest_malformado_no_toca_el_disco(client: TestClient) -> None:
    """El digest llega de la URL: `../` no puede convertirse en una lectura."""
    assert _get(client, "/files/..%2F..%2Fetc%2Fpasswd").status_code == 404


def test_un_cuerpo_vacio_se_rechaza(client: TestClient) -> None:
    """Un archivo de cero bytes no es un archivo — es un error de subida."""
    assert _post_file(client, b"").status_code == 422


def test_el_listado_expone_lo_necesario_para_citar_el_archivo(
    client: TestClient,
) -> None:
    """Nombre para el humano, digest para el certificado (freeze §7: el
    `ref{name, digest}` de una assumption sale de acá)."""
    _post_file(client, b"un paper", **{"X-Filename": "tfim.pdf"})

    fila: dict[str, Any] = _get(client, "/files").json()[0]

    assert set(fila) >= {"digest", "filename", "media_type", "size_bytes", "created_at"}
    assert fila["filename"] == "tfim.pdf"


class TestNoSeSirveComoPaginaWeb:
    """`/files` se proxea en el MISMO origen que el Studio
    (`docker/studio-nginx.conf`), así que un archivo servido como
    `text/html` ejecutaría con la cookie de sesión del usuario adjunta: podría
    crear runs o responder approvals en su nombre. Que la cookie sea HttpOnly
    no alcanza — el navegador la manda sola.

    La defensa es en capas y ninguna sobra: `attachment` impide el render,
    `nosniff` impide que el navegador adivine HTML de un octet-stream, y el
    `Content-Type` peligroso se neutraliza en el origen."""

    def test_un_html_subido_no_se_sirve_como_html(self, client: TestClient) -> None:
        digest = _post_file(
            client,
            b"<script>fetch('/runs',{method:'POST'})</script>",
            **{"Content-Type": "text/html"},
        ).json()["digest"]

        response = _get(client, f"/files/{digest}")

        assert "text/html" not in response.headers["content-type"]

    def test_toda_descarga_va_como_adjunto(self, client: TestClient) -> None:
        digest = _post_file(client, b"%PDF-1.7", **{"X-Filename": "p.pdf"}).json()[
            "digest"
        ]

        response = _get(client, f"/files/{digest}")

        assert response.headers["content-disposition"].startswith("attachment")

    def test_toda_descarga_prohibe_el_sniffing(self, client: TestClient) -> None:
        digest = _post_file(client, b"x").json()["digest"]

        response = _get(client, f"/files/{digest}")

        assert response.headers["x-content-type-options"] == "nosniff"

    def test_un_nombre_con_salto_de_linea_no_inyecta_cabeceras(
        self, client: TestClient
    ) -> None:
        """El nombre viene de un header del cliente y vuelve en otro header:
        un CRLF ahí dentro partiría la respuesta en dos."""
        digest = _post_file(
            client, b"x", **{"X-Filename": 'a"\r\nSet-Cookie: robada=1'}
        ).json()["digest"]

        disposition = _get(client, f"/files/{digest}").headers["content-disposition"]

        # Lo que importa: la respuesta no se puede PARTIR (sin CR/LF) y el
        # nombre no puede salirse de sus comillas. El texto que quede adentro
        # del valor entrecomillado es inerte.
        assert "\r" not in disposition
        assert "\n" not in disposition
        assert disposition.count('"') == 2
        assert disposition.startswith('attachment; filename="')
