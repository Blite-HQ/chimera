"""Lógica pura de `blite.ingesta.snapshot.fetch` (docs/specs/capability-ingesta.md).

Envuelve `ContentSink.put(bytes, media_type, ctx) -> ArtifactLike` (puerto
LOCAL duck-typed, `ports.py` — ADR-008: cero import de `blite.*`) y produce
un dict con la forma de `blite.verification.provenance.ExternalSourceProvenance`
SIN importar esa clase. El cliente HTTP concreto contra el FeatureServer está
FUERA DE ALCANCE (spec §Fronteras): esta capability recibe los bytes YA
obtenidos (inyectados vía `inputs["content_store"]`/`inputs["content_base64"]`),
jamás hace red.

El digest de la instancia ES `sha256` sobre los bytes EXACTOS recibidos — lo
computa el `ContentSink` (mismo comportamiento que `InMemoryContentStore`),
no una segunda copia aquí.
"""

from __future__ import annotations

import base64
from datetime import datetime
from typing import Any

from blite_cap_ingesta.ports import ArtifactLike, ContentSink

_REQUIRED_FETCH_KEYS = (
    "content_base64",
    "media_type",
    "source_uri",
    "retrieved_at",
    "domain_id",
)


def _isoformat(value: Any) -> str:
    """Acepta `datetime` o `str` ya-ISO — nunca reformatea un timestamp que
    ya llegó como texto (mismo espíritu que "no reformatear floats")."""
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _artifact_to_dict(artifact: ArtifactLike) -> dict[str, Any]:
    return {
        "digest": artifact.digest,
        "domain_id": artifact.domain_id,
        "media_type": artifact.media_type,
        "size_bytes": artifact.size_bytes,
        "storage_ref": artifact.storage_ref,
        "created_at": _isoformat(artifact.created_at),
    }


def fetch_snapshot(inputs: dict[str, Any]) -> dict[str, Any]:
    """Implementación de `SnapshotFetch.invoke` — ver `tool.py` para el
    manifest y el wrapper de `Capability`."""
    missing = [key for key in _REQUIRED_FETCH_KEYS if key not in inputs]
    if missing:
        msg = f"blite.ingesta.snapshot.fetch: faltan llaves requeridas {missing}"
        raise ValueError(msg)

    content_store = inputs.get("content_store")
    if not isinstance(content_store, ContentSink):
        msg = (
            "blite.ingesta.snapshot.fetch: 'content_store' (ContentSink) es "
            "requerido en tiempo de invocación — NO es representable en el "
            "input_schema genérico (no es JSON); lo inyecta quien despache "
            "el job (docs/specs/capability-ingesta.md §Fronteras: Registry/"
            "Dispatcher no lo decide esta spec)"
        )
        raise TypeError(msg)

    data = base64.b64decode(inputs["content_base64"])
    media_type = str(inputs["media_type"])
    ctx: dict[str, Any] = {"domain_id": str(inputs["domain_id"])}
    artifact = content_store.put(data, media_type, ctx)

    http_status = inputs.get("http_status")
    provenance: dict[str, Any] = {
        "kind": "external-source",
        "uri": str(inputs["source_uri"]),
        "retrieved_at": _isoformat(inputs["retrieved_at"]),
        "content_type": media_type,
        "http_status": int(http_status) if http_status is not None else None,
    }
    return {"artifact": _artifact_to_dict(artifact), "provenance": provenance}
