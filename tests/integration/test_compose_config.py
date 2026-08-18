"""Estructura de `compose.yaml` — config-only, SIN docker (pure pyyaml).

Complementa el seed `tests/seeds/test_seed_infra_compose.py` (que solo mira
substrings) con aserciones sobre el YAML parseado: los 4 servicios exactos,
el secreto top-level, custodia `*_FILE` (EG-3, ninguna contraseña literal),
el publish de postgres en loopback y el mount de `engine/sql/init_v2.sql`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
COMPOSE_PATH = ROOT / "compose.yaml"


def _load_compose() -> dict[str, Any]:
    return yaml.safe_load(COMPOSE_PATH.read_text(encoding="utf-8"))


def test_the_default_path_is_exactly_the_four_services_that_work() -> None:
    """Lo que `docker compose up` levanta sin argumentos.

    Un servicio SIN `profiles:` arranca siempre, así que este conjunto es la
    promesa que le hacemos a un externo: postgres + api + worker + studio y
    nada más. `worker` había salido a un perfil en #146 (arrancaba y moría sin
    app procrastinate registrada) con una condición explícita — «se saca el
    perfil cuando la cola exista, no antes»; P11 la cumplió. O3 sumó el perfil
    `otel`, pero el camino por defecto no puede crecer sin que este test lo
    diga.
    """
    # Arrange
    compose = _load_compose()

    # Act
    default_path = {
        name
        for name, service in compose["services"].items()
        if not service.get("profiles")
    }

    # Assert
    assert default_path == {"postgres", "api", "worker", "studio"}


def test_every_optional_service_declares_the_profile_that_gates_it() -> None:
    """Los servicios de perfil, uno por uno y con nombre.

    El conjunto se lista explícito para que agregar uno sea una decisión y no
    un descuido: un servicio nuevo o cambia este test, o no existe.
    """
    # Arrange
    compose = _load_compose()

    # Act
    profiled = {
        name: set(service["profiles"])
        for name, service in compose["services"].items()
        if service.get("profiles")
    }

    # Assert
    assert profiled == {
        "otel-collector": {"otel"},
        "otel-projector": {"otel"},
        # C8/C9: custodia de llaves y testigo de transparencia — opcionales
        # por la misma razón que los de arriba, y enumerados acá para que
        # agregar uno nuevo sin perfil siga rompiendo este test.
        "openbao": {"custody"},
        "rekor": {"transparency"},
    }


def test_the_projector_never_gets_the_credentials_of_the_engine() -> None:
    """S-F §2: el proyector lee con un rol SOLO-SELECT, no con el del engine.

    Si algún día recibiera `postgres_password`, la frontera de solo-lectura
    quedaría en manos del código en vez del motor.
    """
    # Arrange
    compose = _load_compose()

    # Act
    projector_secrets = set(compose["services"]["otel-projector"].get("secrets", []))

    # Assert
    assert projector_secrets == {"otel_password"}
    assert "postgres_password" not in projector_secrets


def test_top_level_secret_declares_the_postgres_password_file() -> None:
    # Arrange
    compose = _load_compose()

    # Act
    postgres_password_secret = compose["secrets"]["postgres_password"]

    # Assert
    assert postgres_password_secret["file"] == "./secrets/postgres_password.txt"


def test_compose_text_never_carries_a_literal_password() -> None:
    # Arrange
    text = COMPOSE_PATH.read_text(encoding="utf-8")

    # Assert — solo la variante *_FILE puede aparecer (EG-3); jamás el valor.
    assert "POSTGRES_PASSWORD_FILE:" in text
    assert "POSTGRES_PASSWORD:" not in text
    assert "password=" not in text


def test_every_service_needing_the_db_password_uses_the_file_convention() -> None:
    # Arrange
    compose = _load_compose()
    services = compose["services"]
    services_needing_db_password = ("postgres", "api", "worker")

    # Assert
    for name in services_needing_db_password:
        service = services[name]
        env: dict[str, Any] = service.get("environment") or {}
        secrets_list: list[Any] = service.get("secrets") or []
        env_has_file_ref = any(key.endswith("_FILE") for key in env)
        assert env_has_file_ref or secrets_list, (
            f"servicio {name!r} necesita la contraseña de DB pero no la "
            "referencia vía *_FILE ni vía secrets:"
        )


def test_postgres_publishes_only_on_loopback_5544() -> None:
    # Arrange
    compose = _load_compose()

    # Act
    ports = compose["services"]["postgres"]["ports"]

    # Assert
    assert ports == ["127.0.0.1:5544:5432"]


def test_postgres_mounts_init_v2_sql_into_the_initdb_directory() -> None:
    # Arrange
    compose = _load_compose()

    # Act
    volumes = compose["services"]["postgres"]["volumes"]

    # Assert
    assert any(
        "./engine/sql/init_v2.sql" in volume
        and "/docker-entrypoint-initdb.d/" in volume
        for volume in volumes
    ), f"init_v2.sql no está montado en /docker-entrypoint-initdb.d/: {volumes!r}"
