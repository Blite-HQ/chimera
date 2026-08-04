"""Estructura de `docker/studio-nginx.conf` — texto puro (SIN docker).

Complementa `tests/integration/test_compose_config.py`: aquí se verifica que
el reverse-proxy same-origin hacia `api:8000` esté cableado correctamente
(SSE-safe: `proxy_buffering off`, timeout largo) y que la fachada SPA tenga
el fallback a `index.html`. También se ancla que `compose.yaml` apunte al
Dockerfile real del servicio `studio`.
"""

from __future__ import annotations

import re
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


def _prefijos_servidos_por_el_api() -> set[str]:
    """Los prefijos de primer nivel que el API sirve DE VERDAD, leídos de sus
    rutas — no de una lista escrita a mano en este test."""
    from chimera_api.app import create_app

    from blite.events import create_event_store
    from blite.runtime.registry import EntryPointRegistry

    app = create_app(create_event_store(), registry=EntryPointRegistry({}))
    # `app.routes` NO sirve: FastAPI envuelve cada router incluido en un
    # `_IncludedRouter` y las rutas reales quedan adentro. El esquema OpenAPI
    # es la declaración que el propio API hace de lo que sirve.
    paths: list[str] = sorted(app.openapi()["paths"])
    return {path.split("/")[1] for path in paths if len(path.split("/")) > 1}


def test_nginx_proxea_exactamente_los_prefijos_que_el_api_sirve() -> None:
    """El allowlist de nginx == las rutas de primer nivel del API. Ni más ni menos.

    **De más** es superficie de ataque gratis y una pista falsa para quien lea
    la config: fue el caso de `/invoke`, proxeado durante meses hacia una ruta
    que ningún servidor implementó jamás (hallazgo 7, retirada por P-rt).

    **De menos** es peor porque el síntoma miente: la petición cae en el
    fallback de la SPA y el navegador recibe **HTML donde esperaba JSON**, con
    un error de parseo que no menciona a nginx por ningún lado. Pasó con `/me`
    (P6/M15), cazado recién contra compose. Por eso este test DERIVA la lista
    de las rutas reales del API en vez de fijarla a mano: una ruta nueva sin
    su prefijo en el proxy se pone roja acá, no en el navegador."""
    # Arrange
    text = _load_nginx_conf_text()
    esperados = _prefijos_servidos_por_el_api()

    # Act — el bloque `location ~ ^/(a|b|c)…` del proxy.
    match = re.search(r"location ~ \^/\(([^)]+)\)", text)
    assert match is not None, "no se encontró el bloque location del reverse-proxy"
    proxeados = set(match.group(1).split("|"))

    # Assert
    assert proxeados == esperados, (
        f"el proxy de nginx y las rutas del API divergieron.\n"
        f"  solo en nginx (superficie muerta): {sorted(proxeados - esperados)}\n"
        f"  solo en el API (devolverán HTML): {sorted(esperados - proxeados)}"
    )


def test_nginx_conf_no_proxea_la_ruta_fantasma_invoke() -> None:
    """`/invoke` se retiró junto con la ruta que lo motivaba (hallazgo 7);
    `apps/studio/src/gatewayClient.ts` documenta por qué se mató en vez de
    implementarla."""
    assert "invoke" not in _load_nginx_conf_text()


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
