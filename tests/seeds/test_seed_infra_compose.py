"""SEED · infra (Geovanni) — el compose canónico del mes, config-only.

freeze §15 [S-F] (O6): `postgres + api + worker + studio` (worker = misma
imagen que api, hoy con el entrypoint propio `python -m chimera_api.worker`
que P11 le dio — antes `procrastinate worker`, que sin app registrada moría
al arrancar; `ollama` SOLO perfil opcional archivado — EG-1). EG-3: llaves por convención `*_FILE`. EG-4: DATABASE_URL
con credencial vía secret, migraciones aplicadas (I6). infra/03 §record:
override `compose.record.yml` para el modo grabación. Sin levantar
contenedores: este seed valida la CONFIG, no el runtime.
"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

pytestmark = [
    pytest.mark.seed,
]


def test_the_canonical_compose_exists_with_the_frozen_services() -> None:
    # Arrange
    compose = ROOT / "compose.yaml"
    record_override = ROOT / "compose.record.yml"

    # Assert — servicios congelados + modo record separado (freeze §15 / infra/03)
    assert compose.exists()
    text = compose.read_text(encoding="utf-8")
    for service in ("postgres", "api", "worker", "studio"):
        assert service in text, f"servicio {service!r} ausente del compose canónico"
    assert "_FILE" in text, "custodia de llaves *_FILE ausente (EG-3)"
    assert record_override.exists(), "modo record sin override declarado (infra/03)"
