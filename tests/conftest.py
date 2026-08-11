"""
Shared pytest fixtures for the Chimera test suite.
"""

from __future__ import annotations

from typing import cast

import httpx
from fastapi.testclient import TestClient


def authenticated(client: TestClient) -> TestClient:
    """F1.2 (401-obligatorio) — helper compartido de los tests de API.

    `chimera_api.auth.SessionAuth.identity_from` ya no fabrica una Identity
    default cuando falta la cookie: toda ruta que resuelve identidad exige
    `POST /auth/session` primero. `TestClient` persiste cookies en la
    instancia, así que basta con emitir la sesión una vez antes del primer
    request real — este helper es ese único punto, para no repetir la
    llamada en cada archivo de test.
    """
    emitida = cast(httpx.Response, client.post("/auth/session"))
    if emitida.status_code != 200:
        raise AssertionError(
            "no se pudo emitir la sesión del test: "
            f"POST /auth/session devolvió {emitida.status_code}. "
            "Sin esto cada request daría 401 y la causa real quedaría tapada."
        )
    return client
