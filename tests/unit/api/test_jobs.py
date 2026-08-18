"""P11 — la app procrastinate del worker (`chimera_api.jobs`).

El hueco que cierra, textual del compose (#146): «`procrastinate worker` sin
app registrada FALLA al arrancar», y por eso el servicio quedó tras el perfil
`queue` esperando a este ítem. El primer test de este archivo es esa promesa
hecha ejecutable — si la app dejara de registrar su tarea, el worker volvería
a morir al arrancar y acá se vería antes que en un contenedor.

Todo corre con `InMemoryConnector` (utilidad de la propia librería): la cola
se ejercita sin Postgres, y la corrida VIVA contra compose queda para el
registro del ledger — no se simula acá lo que solo un worker de verdad prueba.
"""

from __future__ import annotations

from typing import Any, cast

import procrastinate
import pytest
from chimera_api.app import create_app
from chimera_api.jobs import (
    MISSION_TASK,
    QUEUE_NAME,
    MissionJob,
    apply_schema_if_missing,
    build_app,
    defer_mission,
    job_queue_enabled,
)
from fastapi.testclient import TestClient
from procrastinate.testing import InMemoryConnector

from blite.events import create_event_store
from blite.identity.identity import Identity
from blite.runtime.registry import EntryPointRegistry
from blite_capability.manifest import CapabilityManifest
from tests.conftest import authenticated


def _identity() -> Identity:
    return Identity(
        id="user:operador",
        kind="human",
        domain_id="domain-chimera",
        permissions=frozenset({"capability:invoke", "override:apply:run"}),
    )


def _job() -> MissionJob:
    return MissionJob(
        run_id="run-abc",
        identity=_identity().model_dump(mode="json"),
        mission="resolver la instancia",
        capability_id="cap.demo",
        inputs={"x": 1},
        max_turns=1,
        max_steps=6,
    )


def _app_en_memoria() -> tuple[procrastinate.App, InMemoryConnector]:
    connector = InMemoryConnector()
    return build_app(connector=connector), connector


def _tarea(app: procrastinate.App, nombre: str) -> Any:
    """`App.tasks` es `dict[str, Task[..., Unknown, ...]]` — los parámetros de
    una tarea son dinámicos por diseño de la librería. El contrato real de esta
    tarea lo sostiene `MissionJob`, no el tipo del dict."""
    return cast(Any, app).tasks[nombre]


class TestLaAppDelWorker:
    def test_la_app_registra_la_tarea_de_la_mision(self) -> None:
        """La causa EXACTA del crash-loop de #146: sin tarea registrada,
        `procrastinate worker` no arranca. Este test es la promesa del
        compose vuelta ejecutable."""
        app, _ = _app_en_memoria()

        assert MISSION_TASK in cast(Any, app).tasks

    def test_la_tarea_declara_la_cola_que_el_worker_escucha(self) -> None:
        """Si la tarea se encolara en una cola que el worker no escucha, el
        job quedaría eternamente pendiente y el run, colgado sin terminal —
        el modo de falla más silencioso de una cola."""
        app, _ = _app_en_memoria()

        assert _tarea(app, MISSION_TASK).queue == QUEUE_NAME


class TestEncolar:
    def test_encolar_una_mision_no_la_ejecuta_en_este_proceso(self) -> None:
        """La misma garantía que `RemoteJobStrategy` (#148): encolar no es
        ejecutar. El proceso que atiende el HTTP deja el trabajo escrito y se
        va; quien lo corre es el worker."""
        app, connector = _app_en_memoria()

        job_id = defer_mission(_job(), app=app)

        encolados = list(connector.jobs.values())
        assert len(encolados) == 1
        assert encolados[0]["task_name"] == MISSION_TASK
        assert encolados[0]["queue_name"] == QUEUE_NAME
        assert job_id

    def test_lo_encolado_es_exactamente_lo_que_la_tarea_sabe_leer(self) -> None:
        """ANTI-DRIFT de las dos puntas: lo que el api escribe en la cola
        vuelve a validar contra el MISMO modelo que el worker usa para leerlo.
        Un campo que se agregara de un lado y no del otro revienta acá y no en
        un worker en producción, con el run ya creado."""
        app, connector = _app_en_memoria()
        original = _job()

        defer_mission(original, app=app)

        encolado = next(iter(connector.jobs.values()))
        assert MissionJob.model_validate(encolado["args"]) == original

    def test_el_job_lleva_la_identidad_del_solicitante_y_nada_mas(self) -> None:
        """La autoridad del run es la de QUIEN lo pidió: viaja explícita en el
        job en vez de re-derivarse en el worker, porque re-derivarla sería
        cambiar en silencio con qué permisos corre un run ya autorizado."""
        job = _job()

        rehecha = Identity.model_validate(job.identity)

        assert rehecha == _identity()


class TestLaCompuertaDeDespliegue:
    def test_sin_la_env_la_cola_esta_apagada(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Default intacto: sin cola declarada, el camino sigue siendo
        `BackgroundTasks` — un despliegue sin worker no puede empezar a
        encolar runs que nadie va a levantar."""
        monkeypatch.delenv("CHIMERA_JOB_QUEUE", raising=False)

        assert job_queue_enabled() is False

    def test_con_la_env_declarada_la_cola_esta_prendida(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("CHIMERA_JOB_QUEUE", "procrastinate")

        assert job_queue_enabled() is True

    def test_un_valor_desconocido_es_error_de_configuracion(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Fail-closed en el arranque: un typo (`procastinate`) que se leyera
        como "apagado" mandaría todos los runs por el camino que no espera
        aprobaciones, en silencio."""
        monkeypatch.setenv("CHIMERA_JOB_QUEUE", "procastinate")

        with pytest.raises(ValueError, match="CHIMERA_JOB_QUEUE"):
            job_queue_enabled()


class _SchemaManagerFalso:
    def __init__(self) -> None:
        self.aplicaciones = 0

    def apply_schema(self) -> None:
        self.aplicaciones += 1


class _AppFalsa:
    """Doble explícito (cero mocks silenciosos) del par
    `check_connection`/`schema_manager` que el arranque consulta."""

    def __init__(self, *, esquema_presente: bool) -> None:
        self._presente = esquema_presente
        self.schema_manager = _SchemaManagerFalso()

    def check_connection(self) -> bool:
        return self._presente


class TestArranqueDelWorker:
    def test_aplica_el_esquema_cuando_falta(self) -> None:
        app = _AppFalsa(esquema_presente=False)

        aplicado = apply_schema_if_missing(app)

        assert aplicado is True
        assert app.schema_manager.aplicaciones == 1

    def test_no_lo_reaplica_si_ya_esta(self) -> None:
        """`procrastinate schema --apply` no es idempotente (falla si ya se
        aplicó), así que el arranque PREGUNTA antes — un worker que se
        reinicia no puede morir por haber arrancado dos veces."""
        app = _AppFalsa(esquema_presente=True)

        aplicado = apply_schema_if_missing(app)

        assert aplicado is False
        assert app.schema_manager.aplicaciones == 0


class TestElContratoDelJob:
    def test_un_campo_de_mas_revienta(self) -> None:
        """`extra="forbid"`, misma disciplina que el resto de los payloads:
        un dato que viaja pero que nadie lee es un contrato roto a medias."""
        with pytest.raises(ValueError, match="inesperado|extra"):
            MissionJob.model_validate({**_job().model_dump(), "campo_que_nadie_lee": 1})

    def test_el_job_serializa_a_json_nativo(self) -> None:
        """Procrastinate guarda los args como JSON en Postgres: un valor que
        no sea JSON nativo (un `frozenset` de permisos, por ejemplo)
        explotaría recién al encolar, con el run ya creado."""
        import json

        crudo: dict[str, Any] = _job().model_dump()

        assert json.loads(json.dumps(crudo)) == crudo


class _CapabilidadDemo:
    """Doble genérico (ADR-029) para que el registry del api resuelva algo."""

    @property
    def manifest(self) -> CapabilityManifest:
        return CapabilityManifest(
            id="cap.demo",
            description="generic test capability",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            side_effects="pure",
            required_permission="capability:invoke",
            interaction="request_response",
        )

    def invoke(self, inputs: dict[str, Any]) -> dict[str, Any]:
        return {}


class TestElApiEncolaEnVezDeEjecutar:
    """La costura entre `POST /runs` y la cola — el punto donde el despliegue
    elige proceso. Es lo único de P11 que el api decide; el resto es del
    worker."""

    def test_con_la_cola_prendida_el_run_no_corre_en_el_proceso_del_api(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("CHIMERA_JOB_QUEUE", "procrastinate")
        app, connector = _app_en_memoria()
        monkeypatch.setattr("chimera_api.jobs.get_app", lambda: app)

        store = create_event_store()
        registry = EntryPointRegistry({"cap.demo": _CapabilidadDemo()})
        client = authenticated(TestClient(create_app(store, registry=registry)))

        respuesta = client.post(
            "/runs",
            json={"mission": "una misión", "capability_id": "cap.demo", "max_turns": 1},
        )

        assert respuesta.status_code == 202
        run_id = respuesta.json()["run_id"]
        # Ni un evento: el api aceptó el run y lo dejó escrito para el worker.
        # Si esto fallara, `BackgroundTasks` habría corrido igual y tendríamos
        # el run ejecutándose DOS veces.
        assert store.read_stream(run_id) == ()
        encolado = next(iter(connector.jobs.values()))
        assert encolado["task_name"] == MISSION_TASK
        assert encolado["args"]["run_id"] == run_id

    def test_sin_la_cola_el_run_sigue_corriendo_en_el_api(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Regresión del default: sin `CHIMERA_JOB_QUEUE` el camino es el de
        siempre y el stream tiene sus eventos apenas responde el 202."""
        monkeypatch.delenv("CHIMERA_JOB_QUEUE", raising=False)
        store = create_event_store()
        registry = EntryPointRegistry({"cap.demo": _CapabilidadDemo()})
        client = authenticated(TestClient(create_app(store, registry=registry)))

        respuesta = client.post(
            "/runs",
            json={"mission": "una misión", "capability_id": "cap.demo", "max_turns": 1},
        )

        assert respuesta.status_code == 202
        tipos = [e.type for e in store.read_stream(respuesta.json()["run_id"])]
        assert "run.created" in tipos
