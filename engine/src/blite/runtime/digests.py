"""
Forma canónica mínima de Fase 1 + digest vía ContentStore. [C2/M2]

Extraído de `loop.py` (era `_canonical_json` privado) para que el runtime y
las etapas de provenance del gateway digieran EXACTAMENTE igual — un
`input_digest` del `run.step.started` (loop) y el del `capability.job.submitted`
(cruce) DEBEN coincidir byte a byte; dos canonicalizaciones divergentes
envenenarían la procedencia. La canonicalización RFC 8785 completa llega con
la vista canónica del anexo — misma nota que traía `loop.py`.
"""

from __future__ import annotations

import json

from blite.content import ContentStore

JSON_MEDIA_TYPE = "application/json"


def canonical_json(obj: object) -> bytes:
    """Claves ordenadas, sin espacios — la forma mínima de Fase 1."""
    return json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()


def digest_via(content: ContentStore, obj: object, domain_id: str) -> str:
    """Persiste la forma canónica y retorna su digest (hash-first, §12)."""
    artifact = content.put(
        canonical_json(obj), JSON_MEDIA_TYPE, {"domain_id": domain_id}
    )
    return artifact.digest
