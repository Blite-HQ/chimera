"""Tests de `chimera_api.model_session` — persistencia en disco de una sesión
agéntica grabada (P4, mandato Dylan 2026-07-29, tarea 3).

Formato: `<session_dir>/manifest.json` (`SessionManifest`: `backend_id`,
`local`, `entries: [{replay_key, response_digest}]`) +
`<session_dir>/responses/<response_digest>.json` (bytes exactos de la
respuesta grabada, content-addressed — mismo digest que `ContentStore.put`
ya calcula, freeze §12). `write_session` dumpea un `InMemoryReplayManifest`
ya poblado (p.ej. por un `ModelServer(mode="record")`); `load_session` es su
inverso: reconstruye un `ReplayManifest` + `backend_id`/`local` sobre un
`ContentStore` fresco, para que `ModelServer(mode="replay", ...)` pegue.

Integridad: `load_session` NO confía ciegamente en el `response_digest`
declarado por el manifest — recalcula el digest real vía `content_store.put`
(el mismo puerto que graba, freeze §12) y compara; una divergencia (archivo
de respuesta corrupto/editado a mano) es `SessionCorruptError`, fail-loud,
jamás una sesión silenciosamente distinta a la que Dylan grabó.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from chimera_api.model_session import SessionCorruptError, load_session, write_session

from blite.protocols.model_server import InMemoryReplayManifest, ModelServer
from blite.runtime.content_store import InMemoryContentStore
from blite.serving.model_port import ModelRequest

_CTX = {"domain_id": "domain-default"}
_BACKEND_ID = "anthropic/claude-sonnet-test"


def _recorded_manifest() -> tuple[InMemoryContentStore, InMemoryReplayManifest]:
    """Dos entradas grabadas — mismo patrón que A2
    (`test_record_then_replay_round_trip_same_request_finds_the_fixture`)."""
    store = InMemoryContentStore()
    manifest = InMemoryReplayManifest()
    recorder_a = ModelServer(
        mode="record",
        content_store=store,
        ctx=_CTX,
        manifest=manifest,
        live_caller=lambda _req: b'{"capability_id": "cap.a", "inputs": {}}',
    )
    recorder_b = ModelServer(
        mode="record",
        content_store=store,
        ctx=_CTX,
        manifest=manifest,
        live_caller=lambda _req: b'{"capability_id": "cap.b", "inputs": {"x": 1}}',
    )
    recorder_a.call(
        ModelRequest(backend_id=_BACKEND_ID, local=False, prompt_digest="a" * 64)
    )
    recorder_b.call(
        ModelRequest(backend_id=_BACKEND_ID, local=False, prompt_digest="b" * 64)
    )
    return store, manifest


class TestWriteLoadRoundTrip:
    def test_write_then_load_reconstruye_el_manifest_reproducible(
        self, tmp_path: Path
    ) -> None:
        # Arrange
        store, manifest = _recorded_manifest()
        session_dir = tmp_path / "cr8-uniforme-demo"

        # Act
        write_session(
            session_dir,
            backend_id=_BACKEND_ID,
            local=False,
            manifest=manifest,
            content_store=store,
            ctx=_CTX,
        )
        fresh_store = InMemoryContentStore()
        loaded_manifest, backend_id, local = load_session(
            session_dir, fresh_store, _CTX
        )

        # Assert — mismos lookups que el manifest original (por cada replay_key
        # ya conocido), sobre un ContentStore COMPLETAMENTE fresco.
        assert backend_id == _BACKEND_ID
        assert local is False
        for replay_key, response_digest in manifest.items():
            assert loaded_manifest.lookup(replay_key) == response_digest
            assert fresh_store.get(response_digest, _CTX) == store.get(
                response_digest, _CTX
            )

    def test_los_archivos_en_disco_tienen_la_forma_declarada(
        self, tmp_path: Path
    ) -> None:
        # Arrange
        store, manifest = _recorded_manifest()
        session_dir = tmp_path / "una-sesion"

        # Act
        write_session(
            session_dir,
            backend_id=_BACKEND_ID,
            local=False,
            manifest=manifest,
            content_store=store,
            ctx=_CTX,
        )

        # Assert
        assert (session_dir / "manifest.json").is_file()
        for _replay_key, response_digest in manifest.items():
            assert (session_dir / "responses" / f"{response_digest}.json").is_file()


class TestLoadSessionCorrupta:
    def test_manifest_ausente_levanta_session_corrupt_error(
        self, tmp_path: Path
    ) -> None:
        with pytest.raises(SessionCorruptError):
            load_session(tmp_path / "no-existe", InMemoryContentStore(), _CTX)

    def test_archivo_de_respuesta_faltante_levanta_session_corrupt_error(
        self, tmp_path: Path
    ) -> None:
        # Arrange — manifest.json declara una entrada cuyo archivo NUNCA se
        # escribió (sesión a medio copiar / borrado accidental).
        store, manifest = _recorded_manifest()
        session_dir = tmp_path / "incompleta"
        write_session(
            session_dir,
            backend_id=_BACKEND_ID,
            local=False,
            manifest=manifest,
            content_store=store,
            ctx=_CTX,
        )
        for response_file in (session_dir / "responses").iterdir():
            response_file.unlink()

        # Act / Assert
        with pytest.raises(SessionCorruptError):
            load_session(session_dir, InMemoryContentStore(), _CTX)

    def test_archivo_de_respuesta_alterado_levanta_session_corrupt_error(
        self, tmp_path: Path
    ) -> None:
        # Arrange — el archivo fue editado a mano: sus bytes ya NO hashean al
        # `response_digest` que el propio nombre/manifest declaran.
        store, manifest = _recorded_manifest()
        session_dir = tmp_path / "alterada"
        write_session(
            session_dir,
            backend_id=_BACKEND_ID,
            local=False,
            manifest=manifest,
            content_store=store,
            ctx=_CTX,
        )
        responses_dir = session_dir / "responses"
        target = next(responses_dir.iterdir())
        target.write_bytes(b'{"capability_id": "manipulado", "inputs": {}}')

        # Act / Assert
        with pytest.raises(SessionCorruptError):
            load_session(session_dir, InMemoryContentStore(), _CTX)

    def test_manifest_json_malformado_levanta_session_corrupt_error(
        self, tmp_path: Path
    ) -> None:
        # Arrange
        session_dir = tmp_path / "manifest-roto"
        session_dir.mkdir()
        (session_dir / "manifest.json").write_text("esto no es json", encoding="utf-8")

        # Act / Assert
        with pytest.raises(SessionCorruptError):
            load_session(session_dir, InMemoryContentStore(), _CTX)
