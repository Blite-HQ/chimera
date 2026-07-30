"""
Persistencia en disco de una sesión agéntica grabada (carril P4, mandato
Dylan 2026-07-29, tarea 3). Complementa `blite.protocols.model_server`
(A2, `ReplayManifest`/`InMemoryReplayManifest`) — ESE módulo define el
puerto+respaldo en memoria; ESTE módulo lo dumpea/carga de un directorio
(`knowledge/sessions/<nombre>/`, convención — este módulo no fija la ruta,
la recibe como parámetro).

Formato (documentado también en `docs/specs/harness-agentico.md` §"Formato
de sesión en disco"):

    <session_dir>/manifest.json          — `SessionManifest`
    <session_dir>/responses/<digest>.json — bytes EXACTOS de cada respuesta

`manifest.json` mapea `replay_key -> response_digest` (mismo par que
`ReplayManifest.record`, freeze §15.7 punto 4) más `backend_id`/`local` —
los DOS campos que faltan para reconstruir el `ModelRequest` exacto que hizo
match en el momento de grabar (`replay_key_digest` incluye `backend_id`,
freeze §15.7 punto 2: dos backends nunca colisionan).

`responses/<digest>.json` es content-addressed por el MISMO digest que
`ContentStore.put` ya calcula (freeze §12) — `load_session` no asume un
algoritmo de hash propio: re-`put()`ea los bytes leídos y compara contra el
digest declarado, así que la verificación de integridad es agnóstica al
algoritmo concreto del `ContentStore` inyectado.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, ValidationError

from blite.content import ContentStore
from blite.protocols.model_server import InMemoryReplayManifest

_MANIFEST_FILENAME = "manifest.json"
_RESPONSES_DIRNAME = "responses"
_RESPONSE_MEDIA_TYPE = "application/json"


class SessionCorruptError(Exception):
    """La sesión en disco no es consistente: falta `manifest.json`, un
    `responses/<digest>.json` referenciado no existe, sus bytes no hashean
    al digest declarado, o `manifest.json` no es JSON válido bajo
    `SessionManifest`. Fail-loud — jamás cargar una sesión parcial en
    silencio (freeze §15.7: el modo replay es la red de seguridad del
    air-gap del día D, no puede fundarse en una sesión dudosa)."""


class SessionEntry(BaseModel):
    """Un par `(replay_key, response_digest)` — mismo vocabulario que
    `ReplayManifest.record` (`blite.protocols.model_server`)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    replay_key: str
    response_digest: str


class SessionManifest(BaseModel):
    """`manifest.json` — `backend_id`/`local` completan el `ModelRequest`
    que cada `entries[i].replay_key` codifica; `mission` es metadata
    descriptiva para operadores (Dylan grabando sesiones), NUNCA consumida
    por `load_session` para reconstruir el replay."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    backend_id: str
    local: bool = False
    mission: str | None = None
    entries: tuple[SessionEntry, ...] = ()


def write_session(
    session_dir: Path,
    *,
    backend_id: str,
    local: bool,
    manifest: InMemoryReplayManifest,
    content_store: ContentStore,
    ctx: object,
    mission: str | None = None,
) -> None:
    """Dumpea un `InMemoryReplayManifest` ya poblado (p.ej. por
    `ModelServer(mode="record")`) a `session_dir` — crea el directorio si no
    existe (runbook de `scripts/record_session.py`: primera grabación de una
    sesión nueva)."""
    responses_dir = session_dir / _RESPONSES_DIRNAME
    responses_dir.mkdir(parents=True, exist_ok=True)

    entries: list[SessionEntry] = []
    for replay_key, response_digest in manifest.items():
        response_bytes = content_store.get(response_digest, ctx)
        (responses_dir / f"{response_digest}.json").write_bytes(response_bytes)
        entries.append(
            SessionEntry(replay_key=replay_key, response_digest=response_digest)
        )

    session = SessionManifest(
        backend_id=backend_id, local=local, mission=mission, entries=tuple(entries)
    )
    manifest_path = session_dir / _MANIFEST_FILENAME
    manifest_path.write_text(session.model_dump_json(indent=2) + "\n", encoding="utf-8")


def load_session(
    session_dir: Path, content_store: ContentStore, ctx: object
) -> tuple[InMemoryReplayManifest, str, bool]:
    """Inverso de `write_session`: reconstruye un `ReplayManifest` sobre
    `content_store` (típicamente un `ContentStore` FRESCO — el mismo que
    `ModelServer(mode="replay", ...)` usará) + el `backend_id`/`local` que el
    caller necesita para armar `ModelRequest`s que hagan match.

    Tipo de retorno CONCRETO (`InMemoryReplayManifest`, no el `ReplayManifest`
    Protocol) a propósito: expone `.items()` (enumeración, ver
    `blite.protocols.model_server`) a quien necesite volcar la sesión de
    nuevo — `ModelServer.manifest` acepta esta instancia igual, satisface el
    Protocol estructuralmente."""
    manifest_path = session_dir / _MANIFEST_FILENAME
    if not manifest_path.is_file():
        msg = f"sesión sin manifest: {manifest_path} no existe"
        raise SessionCorruptError(msg)

    try:
        session = SessionManifest.model_validate_json(
            manifest_path.read_text(encoding="utf-8")
        )
    except ValidationError as exc:
        msg = f"manifest de sesión inválido en {manifest_path}: {exc}"
        raise SessionCorruptError(msg) from exc

    replay_manifest = InMemoryReplayManifest()
    for entry in session.entries:
        response_path = (
            session_dir / _RESPONSES_DIRNAME / f"{entry.response_digest}.json"
        )
        if not response_path.is_file():
            msg = f"sesión corrupta: falta {response_path} referenciado por manifest"
            raise SessionCorruptError(msg)
        response_bytes = response_path.read_bytes()
        artifact = content_store.put(response_bytes, _RESPONSE_MEDIA_TYPE, ctx)
        if artifact.digest != entry.response_digest:
            msg = (
                f"sesión corrupta: {response_path} no hashea a "
                f"{entry.response_digest!r} (real: {artifact.digest!r}) — "
                "¿archivo editado a mano?"
            )
            raise SessionCorruptError(msg)
        replay_manifest.record(entry.replay_key, artifact.digest)

    return replay_manifest, session.backend_id, session.local


__all__ = [
    "SessionCorruptError",
    "SessionEntry",
    "SessionManifest",
    "load_session",
    "write_session",
]
