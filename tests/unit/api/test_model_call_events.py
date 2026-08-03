"""`model.call.*` emitidos y el conductor de fidelidad de replay (P4/M31).

El vocabulario `model.call.requested|completed|failed` está CONGELADO desde el
freeze §3 y hasta ahora no lo emitía nadie: la llamada de modelo era el único
efecto del sistema sin rastro propio, y por eso `find_replay_divergences`
(`blite.runtime.replay`, ya implementado) era infraestructura sin uso. Estos
tests fijan las dos mitades: que los eventos SALEN, y que con ellos la
comprobación de fidelidad detecta de verdad una respuesta cambiada.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from chimera_api.app import create_app
from chimera_api.model_session import (
    SESSION_MANIFEST_VERSION,
    SessionCorruptError,
    SessionEntry,
    SessionManifest,
    compute_entries_digest,
    load_session,
    write_session,
)

from blite.events import create_event_store
from blite.protocols.model_server import InMemoryReplayManifest, ModelServer
from blite.runtime.content_store import InMemoryContentStore

_CTX = {"domain_id": "domain-default"}


class TestSessionManifestVersionYDigest:
    def test_write_session_estampa_version_y_digest_del_conjunto(
        self, tmp_path: Path
    ) -> None:
        write_session(
            tmp_path / "s",
            backend_id="anthropic/test",
            local=False,
            manifest=InMemoryReplayManifest(),
            content_store=InMemoryContentStore(),
            ctx=_CTX,
        )
        manifest = SessionManifest.model_validate_json(
            (tmp_path / "s" / "manifest.json").read_text(encoding="utf-8")
        )
        assert manifest.version == SESSION_MANIFEST_VERSION
        assert manifest.entries_digest == compute_entries_digest(())

    def test_digest_del_conjunto_no_depende_del_orden(self) -> None:
        a = SessionEntry(replay_key="k-a", response_digest="d-a")
        b = SessionEntry(replay_key="k-b", response_digest="d-b")
        assert compute_entries_digest((a, b)) == compute_entries_digest((b, a))

    def test_quitar_una_entrada_a_mano_es_sesion_corrupta(self, tmp_path: Path) -> None:
        """El pin del CONJUNTO (freeze §15.7 punto 4). Antes, cada respuesta
        hasheaba bien por separado y nadie miraba el set: sacarle una entrada
        a la sesión pasaba inadvertido."""
        store = InMemoryContentStore()
        manifest = InMemoryReplayManifest()
        servidor = ModelServer(
            mode="record",
            content_store=store,
            ctx=_CTX,
            manifest=manifest,
            live_caller=lambda _req: b'{"capability_id": "cap.x", "inputs": {}}',
        )
        from blite.serving.model_port import ModelRequest

        for prompt in (b"uno", b"dos"):
            artefacto = store.put(prompt, "application/json", _CTX)
            servidor.call(
                ModelRequest(
                    backend_id="anthropic/test",
                    local=False,
                    prompt_digest=artefacto.digest,
                )
            )
        session_dir = tmp_path / "s"
        write_session(
            session_dir,
            backend_id="anthropic/test",
            local=False,
            manifest=manifest,
            content_store=store,
            ctx=_CTX,
        )

        # Mutilación: se quita una entrada dejando el digest viejo.
        original = SessionManifest.model_validate_json(
            (session_dir / "manifest.json").read_text(encoding="utf-8")
        )
        mutilado = original.model_copy(update={"entries": original.entries[:1]})
        (session_dir / "manifest.json").write_text(
            mutilado.model_dump_json(indent=2), encoding="utf-8"
        )

        with pytest.raises(SessionCorruptError, match="conjunto de entradas"):
            load_session(session_dir, InMemoryContentStore(), _CTX)

    def test_version_desconocida_es_sesion_corrupta(self, tmp_path: Path) -> None:
        session_dir = tmp_path / "s"
        (session_dir / "responses").mkdir(parents=True)
        futuro = SessionManifest(
            backend_id="anthropic/test", version="blite/model-session/v99"
        )
        (session_dir / "manifest.json").write_text(
            futuro.model_dump_json(indent=2), encoding="utf-8"
        )
        with pytest.raises(SessionCorruptError, match="formato desconocido"):
            load_session(session_dir, InMemoryContentStore(), _CTX)


class TestFailFastRecordEfimero:
    def test_record_sin_declarar_lo_efimero_falla_al_construir_la_app(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Arrancar la API en `record` quemaría llamadas de modelo REALES
        —con su costo— a un manifest que muere con el proceso. Se declara."""
        monkeypatch.setenv("CHIMERA_MODEL_BACKEND", "record")
        monkeypatch.delenv("CHIMERA_ALLOW_EPHEMERAL_RECORD", raising=False)
        with pytest.raises(ValueError, match="record_session.py"):
            create_app(create_event_store())

    def test_record_declarado_explicitamente_arranca(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("CHIMERA_MODEL_BACKEND", "record")
        monkeypatch.setenv("CHIMERA_ALLOW_EPHEMERAL_RECORD", "1")
        assert create_app(create_event_store()) is not None


class TestKeyPorArchivo:
    def test_key_file_puebla_la_env_var(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from chimera_api.runs import load_model_api_key_from_file

        key = tmp_path / "model.key"
        key.write_text("sk-secreta\n", encoding="utf-8")
        monkeypatch.delenv("CHIMERA_MODEL_API_KEY", raising=False)
        monkeypatch.setenv("CHIMERA_MODEL_API_KEY_FILE", str(key))

        load_model_api_key_from_file()

        import os

        assert os.environ["CHIMERA_MODEL_API_KEY"] == "sk-secreta"

    def test_env_var_explicita_gana_sobre_el_archivo(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Quien exporta la env var a mano está depurando: un archivo montado
        no se la pisa en silencio."""
        from chimera_api.runs import load_model_api_key_from_file

        key = tmp_path / "model.key"
        key.write_text("del-archivo", encoding="utf-8")
        monkeypatch.setenv("CHIMERA_MODEL_API_KEY", "de-la-env")
        monkeypatch.setenv("CHIMERA_MODEL_API_KEY_FILE", str(key))

        load_model_api_key_from_file()

        import os

        assert os.environ["CHIMERA_MODEL_API_KEY"] == "de-la-env"

    def test_archivo_ilegible_falla_en_el_arranque(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from chimera_api.runs import load_model_api_key_from_file

        monkeypatch.delenv("CHIMERA_MODEL_API_KEY", raising=False)
        monkeypatch.setenv("CHIMERA_MODEL_API_KEY_FILE", str(tmp_path / "no-existe"))
        with pytest.raises(ValueError, match="no se puede leer"):
            load_model_api_key_from_file()


class TestConductorDeFidelidad:
    """El conductor que vuelve VIVA la propiedad R1 (P4/M31)."""

    def _sesion_con_una_llamada(self) -> tuple[Any, str, str, str]:
        """Graba una llamada y devuelve (manifest, backend_id, prompt_digest,
        response_digest) — el par que el stream journalizaría."""
        from blite.serving.model_port import ModelRequest

        store = InMemoryContentStore()
        manifest = InMemoryReplayManifest()
        servidor = ModelServer(
            mode="record",
            content_store=store,
            ctx=_CTX,
            manifest=manifest,
            live_caller=lambda _req: b'{"capability_id": "cap.x", "inputs": {}}',
        )
        prompt = store.put(b'{"protocol":"x"}', "application/json", _CTX)
        respuesta = servidor.call(
            ModelRequest(
                backend_id="anthropic/test", local=False, prompt_digest=prompt.digest
            )
        )
        return manifest, "anthropic/test", prompt.digest, respuesta.response_digest

    def _stream(self, prompt_digest: str, response_digest: str) -> tuple[Any, ...]:
        from blite.events import create_event_store

        store = create_event_store()
        store.append(
            stream_id="run-fid",
            type="model.call.requested",
            actor_id="user:dylan",
            domain_id="domain-default",
            payload={
                "backend_id": "anthropic/test",
                "local": False,
                "prompt_digest": prompt_digest,
            },
            expected_seq=0,
        )
        store.append(
            stream_id="run-fid",
            type="model.call.completed",
            actor_id="user:dylan",
            domain_id="domain-default",
            payload={"response_digest": response_digest},
            expected_seq=1,
        )
        return store.read_stream("run-fid")

    def test_replay_fiel_no_reporta_divergencias(self) -> None:
        from chimera_api.replay_fidelity import check_run_fidelity, session_recomputer

        manifest, backend_id, prompt_d, response_d = self._sesion_con_una_llamada()
        divergencias = check_run_fidelity(
            "run-fid",
            self._stream(prompt_d, response_d),
            session_recomputer(manifest, backend_id=backend_id, local=False),
        )
        assert divergencias == ()

    def test_respuesta_cambiada_produce_divergencia_tipada(self) -> None:
        """El caso que da sentido a todo: la sesión promete OTRA respuesta
        para el mismo request ⇒ el replay no fue fiel, y se dice con un
        evento tipado en vez de una excepción silenciosa."""
        from chimera_api.replay_fidelity import check_run_fidelity, session_recomputer

        manifest, backend_id, prompt_d, response_d = self._sesion_con_una_llamada()
        # El stream journaliza un response_digest que NO es el de la sesión.
        otro = "f" * 64
        divergencias = check_run_fidelity(
            "run-fid",
            self._stream(prompt_d, otro),
            session_recomputer(manifest, backend_id=backend_id, local=False),
        )

        assert len(divergencias) == 1
        d = divergencias[0]
        assert d.effect_kind == "model_call"
        assert d.expected_response_digest == otro
        assert d.actual_response_digest == response_d
        assert d.run_id == "run-fid"

    def test_efecto_no_recomputable_se_reporta_jamas_se_finge(self) -> None:
        """Un check que no se pudo hacer NO es un check que pasó: recomputar
        un `capability_job` es re-ejecutar la capability — política que este
        conductor no toma, y lo dice."""
        from chimera_api.replay_fidelity import (
            UnrecomputableEffectError,
            session_recomputer,
        )

        from blite.runtime.replay import JournaledEffect

        manifest, backend_id, _, _ = self._sesion_con_una_llamada()
        recompute = session_recomputer(manifest, backend_id=backend_id, local=False)
        with pytest.raises(UnrecomputableEffectError, match="capability_job"):
            recompute(
                JournaledEffect(
                    effect_kind="capability_job",
                    request_digest="a" * 64,
                    response_digest="b" * 64,
                )
            )
