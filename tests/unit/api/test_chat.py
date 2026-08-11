"""Rutas de conversación del run — `chimera_api.chat` (P3, spec
`docs/specs/chat-conversacion.md` §Contrato-2/3).

Lo que el seed (`tests/seeds/test_seed_chat_conversacion.py`) fija es la
FORMA del contrato; acá va el comportamiento fino que la spec exige y el
seed no cubre: 404 vs 409 (respuestas distintas para «no existe» y «ya
terminó»), 422 de body vacío, el `author` estampado por la identidad y NO por
el body, y el drenado queue-to-next-turn del §Contrato-5 contra el loop real.
"""

from __future__ import annotations

from typing import Any, cast

import httpx
import pytest
from chimera_api.app import create_app
from fastapi.testclient import TestClient

from blite.events import create_event_store
from blite.events.store import EventStore

_RUN = "run-conversacion"
_DOMINIO = "domain-conversacion"


def _store_abierto(run_id: str = _RUN) -> EventStore:
    """Un run vivo (created + started, sin terminal) — acepta conversación."""
    store = create_event_store()
    store.append(
        stream_id=run_id,
        type="run.created",
        actor_id="user:dylan",
        domain_id=_DOMINIO,
        payload={
            "run_id": run_id,
            "actor_id": "user:dylan",
            "domain_id": _DOMINIO,
            "max_steps": 4,
            "policy_digest": "d" * 64,
        },
        expected_seq=0,
    )
    store.append(
        stream_id=run_id,
        type="run.started",
        actor_id="service:runtime",
        domain_id=_DOMINIO,
        payload={},
        expected_seq=1,
    )
    return store


def _get(client: TestClient, url: str) -> httpx.Response:
    return cast(
        httpx.Response,
        client.get(url),
    )


def _post(client: TestClient, url: str, body: dict[str, Any]) -> httpx.Response:
    return cast(
        httpx.Response,
        client.post(url, json=body),
    )


class TestPostMessages:
    def test_run_desconocido_es_404_no_409(self) -> None:
        """«No existe» y «ya terminó» son respuestas DISTINTAS: un 409 sobre
        un run inexistente mentiría diciendo que alguna vez existió."""
        client = TestClient(create_app(create_event_store()))
        assert (
            _post(client, "/runs/run-fantasma/messages", {"text": "hola"}).status_code
            == 404
        )

    def test_texto_vacio_es_422(self) -> None:
        client = TestClient(create_app(_store_abierto()))
        assert _post(client, f"/runs/{_RUN}/messages", {"text": ""}).status_code == 422

    def test_author_lo_estampa_la_identidad_jamas_el_body(self) -> None:
        """§Contrato-2: `author` NO viaja en el body — un cliente no puede
        decir que el mensaje lo escribió otro. Mandarlo es 422 (extra=forbid)."""
        client = TestClient(create_app(_store_abierto()))
        respuesta = _post(
            client,
            f"/runs/{_RUN}/messages",
            {"text": "hola", "author": "user:impostor"},
        )
        assert respuesta.status_code == 422

    def test_el_evento_lleva_el_dominio_del_run_no_el_del_proceso(self) -> None:
        """El `domain_id` sale del `run.created` del propio run: un evento
        del stream jamás cambia de dominio a mitad de camino."""
        store = _store_abierto()
        client = TestClient(create_app(store))
        _post(client, f"/runs/{_RUN}/messages", {"text": "seguí"})
        mensaje = next(
            e for e in store.read_stream(_RUN) if e.type == "mission.message"
        )
        assert mensaje.domain_id == _DOMINIO
        assert mensaje.actor_id == mensaje.payload["author"]
        assert mensaje.payload["text"] == "seguí"
        assert mensaje.payload["run_id"] == _RUN

    def test_mensajes_sucesivos_conservan_el_orden_del_stream(self) -> None:
        store = _store_abierto()
        client = TestClient(create_app(store))
        for texto in ("uno", "dos", "tres"):
            assert (
                _post(client, f"/runs/{_RUN}/messages", {"text": texto}).status_code
                == 202
            )
        textos = [
            e.payload["text"]
            for e in store.read_stream(_RUN)
            if e.type == "mission.message"
        ]
        assert textos == ["uno", "dos", "tres"]


class TestPostCancel:
    def test_run_desconocido_es_404(self) -> None:
        client = TestClient(create_app(create_event_store()))
        assert _post(client, "/runs/run-fantasma/cancel", {}).status_code == 404

    def test_segundo_cancel_es_409(self) -> None:
        """`run.cancelled` es terminal: cancelar dos veces es conflicto, no
        idempotencia silenciosa."""
        client = TestClient(create_app(_store_abierto()))
        assert _post(client, f"/runs/{_RUN}/cancel", {}).status_code == 202
        assert _post(client, f"/runs/{_RUN}/cancel", {}).status_code == 409

    def test_reason_propia_viaja_al_payload(self) -> None:
        store = _store_abierto()
        client = TestClient(create_app(store))
        _post(client, f"/runs/{_RUN}/cancel", {"reason": "me equivoqué de instancia"})
        cancelado = next(
            e for e in store.read_stream(_RUN) if e.type == "run.cancelled"
        )
        assert cancelado.payload["reason"] == "me equivoqué de instancia"


class TestDrenadoQueueToNextTurn:
    """§Contrato-5 contra el loop REAL — no un doble del drenado."""

    def test_el_mensaje_llega_al_turno_siguiente_jamas_al_en_curso(self) -> None:
        from blite.runtime.content_store import InMemoryContentStore
        from blite.runtime.dispatch import ProfileDispatcher
        from blite.runtime.loop import ProposedStep, TurnContext, execute_run
        from blite.runtime.mission import MissionMessagePayload
        from blite.runtime.registry import EntryPointRegistry
        from blite_capability.manifest import CapabilityManifest

        class _Echo:
            @property
            def manifest(self) -> CapabilityManifest:
                return CapabilityManifest(
                    id="cap.echo",
                    description="generic test capability",
                    input_schema={"type": "object"},
                    output_schema={"type": "object"},
                    side_effects="pure",
                    required_permission="capability:invoke",
                    interaction="request_response",
                )

            def invoke(self, inputs: dict[str, Any]) -> dict[str, Any]:
                return {"ok": True}

        store = create_event_store()
        vistos: list[tuple[int, tuple[str, ...]]] = []

        def _proposer(ctx: TurnContext) -> ProposedStep:
            vistos.append((ctx.turn, tuple(m.text for m in ctx.pending_messages)))
            # El mensaje se journaliza DENTRO del turno 1: la spec exige que
            # NO se vea en el turno en curso, solo en el siguiente.
            if ctx.turn == 1:
                store.append(
                    stream_id="run-drenado",
                    type="mission.message",
                    actor_id="user:dylan",
                    domain_id="domain-a",
                    payload=MissionMessagePayload(
                        run_id="run-drenado",
                        message_id="msg-1",
                        author="user:dylan",
                        text="cambiá de rumbo",
                    ).model_dump(),
                )
            return ProposedStep(capability_id="cap.echo", inputs={})

        execute_run(
            store,
            EntryPointRegistry({"cap.echo": _Echo()}),
            ProfileDispatcher(),
            InMemoryContentStore(),
            run_id="run-drenado",
            actor_id="user:dylan",
            domain_id="domain-a",
            max_steps=64,
            policy_digest="pol-1",
            capability_id="cap.echo",
            inputs={},
            max_turns=3,
            proposer=_proposer,
        )

        # Turno 1 sin mensajes (el suyo llegó DESPUÉS de armarse su contexto);
        # turno 2 con el mensaje; turno 3 ya drenado — jamás se re-entrega.
        assert vistos == [
            (1, ()),
            (2, ("cambiá de rumbo",)),
            (3, ()),
        ]


class TestSkipHonestoCubreElResumen:
    """Segunda mitad de #104, encontrada por una corrida VIVA (P-rt).

    El skip por-stream cubría la PROYECCIÓN; pero `_run_summary` también
    puede explotar (ensamblar el certificado de ese run), y entonces
    `GET /runs` volvía a morir con 500 por un run ajeno al pedido — el mismo
    defecto que #104 cierra, una capa más abajo."""

    def test_un_resumen_que_explota_no_tumba_el_listado(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """El fallo se inyecta en `_run_summary` con un doble ETIQUETADO (no
        un mock silencioso): así se ejercita la rama sin depender de que
        exista hoy un stream capaz de romper el ensamblado — el que había
        (la tupla de `plan.created`) quedó arreglado en la raíz."""
        import chimera_api.reads as reads
        from chimera_api.app import create_app

        original = reads._run_summary  # pyright: ignore[reportPrivateUsage] — el doble tiene que envolver la MISMA función que la ruta usa

        def _resumen_que_explota(
            resources: object, run_id: str, actor_id: str
        ) -> object:
            if run_id == "run-que-rompe":
                msg = "ensamblado imposible para este run"
                raise RuntimeError(msg)
            return original(resources, run_id, actor_id)  # pyright: ignore[reportArgumentType]

        monkeypatch.setattr(reads, "_run_summary", _resumen_que_explota)

        store = _store_abierto()
        store.append(
            stream_id="run-que-rompe",
            type="run.created",
            actor_id="user:dylan",
            domain_id=_DOMINIO,
            payload={
                "run_id": "run-que-rompe",
                "actor_id": "user:dylan",
                "domain_id": _DOMINIO,
                "max_steps": 4,
                "policy_digest": "d" * 64,
            },
            expected_seq=0,
        )
        client = TestClient(create_app(store))

        listado = _get(client, "/runs")
        assert listado.status_code == 200
        filas: list[dict[str, Any]] = listado.json()
        assert [f["run_id"] for f in filas] == [_RUN]

        reporte: dict[str, Any] = _get(client, "/runs/discarded").json()
        descartados: list[dict[str, Any]] = reporte["discarded_streams"]
        assert [f["stream_id"] for f in descartados] == ["run-que-rompe"]
        assert descartados[0]["error_kind"] == "RuntimeError"

    def test_las_dos_rutas_salen_del_mismo_computo(self) -> None:
        """Si divergieran, `/runs/discarded` dejaría de explicar lo que
        `/runs` omitió — y el reporte pasaría a ser decorativo."""
        from chimera_api.app import create_app

        store = _store_abierto()
        store.append(
            stream_id="run-envenenado",
            type="run.created",
            actor_id="user:dylan",
            domain_id=_DOMINIO,
            payload={"run_id": "run-envenenado"},
            expected_seq=0,
        )
        client = TestClient(create_app(store))

        filas: list[dict[str, Any]] = _get(client, "/runs").json()
        reporte: dict[str, Any] = _get(client, "/runs/discarded").json()
        listados = [f["run_id"] for f in filas]
        descartados = [f["stream_id"] for f in reporte["discarded_streams"]]

        assert _RUN in listados
        assert descartados == ["run-envenenado"]
        assert not set(listados) & set(descartados)
