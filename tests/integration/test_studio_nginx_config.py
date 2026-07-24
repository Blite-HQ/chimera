"""Estructura de `docker/studio-nginx.conf` — texto puro (SIN docker).

Complementa `tests/integration/test_compose_config.py`: aquí se verifica que
el reverse-proxy same-origin hacia `api:8000` esté cableado correctamente
(SSE-safe: `proxy_buffering off`, timeout largo) y que la fachada SPA tenga
el fallback a `index.html`. También se ancla que `compose.yaml` apunte al
Dockerfile real del servicio `studio`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
COMPOSE_PATH = ROOT / "compose.yaml"
STUDIO_DOCKERFILE_PATH = ROOT / "docker" / "studio.Dockerfile"
STUDIO_NGINX_CONF_PATH = ROOT / "docker" / "studio-nginx.conf"


def _load_compose() -> dict[str, Any]:
    return yaml.safe_load(COMPOSE_PATH.read_text(encoding="utf-8"))


def _load_nginx_conf_text() -> str:
    return STUDIO_NGINX_CONF_PATH.read_text(encoding="utf-8")


def test_nginx_conf_proxies_to_the_api_service_on_port_8000() -> None:
    # Arrange
    text = _load_nginx_conf_text()

    # Assert
    assert "proxy_pass http://api:8000;" in text


def test_nginx_conf_disables_proxy_buffering_for_sse() -> None:
    # Arrange
    text = _load_nginx_conf_text()

    # Assert — SSE regression guard: sin esto, /runs/{id}/events se buferea
    # y el cliente nunca ve los eventos según se producen.
    assert "proxy_buffering off;" in text


def test_nginx_conf_proxies_the_three_gateway_prefixes() -> None:
    # Arrange
    text = _load_nginx_conf_text()

    # Assert
    assert "location ~ ^/(invoke|runs|health)" in text


def test_nginx_conf_has_the_spa_fallback_to_index_html() -> None:
    # Arrange
    text = _load_nginx_conf_text()

    # Assert
    assert "try_files $uri $uri/ /index.html;" in text


def test_compose_studio_service_builds_from_the_studio_dockerfile() -> None:
    # Arrange
    compose = _load_compose()

    # Act
    dockerfile = compose["services"]["studio"]["build"]["dockerfile"]

    # Assert
    assert dockerfile == "docker/studio.Dockerfile"
    assert STUDIO_DOCKERFILE_PATH.exists(), (
        f"{STUDIO_DOCKERFILE_PATH} no existe pero compose.yaml lo referencia"
    )
