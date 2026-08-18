"""
P11 — la cola durable: la app procrastinate que el worker levanta.

**El hueco que cierra.** `blite.runtime.jobs` (#148) entregó el PUERTO
`JobQueue` y declaró su frontera: el adapter concreto y el flip del perfil
`queue` del compose exigían Postgres vivo para verificarse. El servicio
`worker` existía desde el MVP con `command: procrastinate worker` y **sin app
registrada**, así que arrancaba y moría; #146 lo escondió tras el perfil
`queue` con una condición explícita — «se saca el perfil cuando la cola
exista, no antes». Este módulo es esa app.

**Por qué vale la pena, más allá de tener un worker.** Con `BackgroundTasks`
(decisión #11) un run vive en un hilo del servidor HTTP, así que una compuerta
de aprobación NO puede esperar a una persona sin clavar ese hilo — y de ahí la
conclusión de #183: sin cola durable, un approval humano-en-el-lazo genuino no
puede existir, porque el único `approval.requested` posible nace de un turno
que ya cerró el run. En un worker esperar es lo normal: el run se queda VIVO
mientras un humano decide, la respuesta entra por `POST /runs/{id}/approvals/
{id}` sobre un stream ABIERTO (202, no 409) y `approval.responded` cae DENTRO
del corte de procedencia (freeze §2). Eso es lo que esta cola compra.

**Dónde vive y por qué acá.** `blite.runtime` jamás importa `procrastinate`
(mismo principio que `ModelPort` con litellm, AX3-b: la casa del SDK está
afuera del runtime). La app necesita el registry, el content store y el
`EventStore` YA construidos, y quien los arma es la raíz de composición del
despliegue — `chimera_api`. El worker corre la MISMA imagen que el api
(`docker/api.Dockerfile`), así que resuelve las mismas capabilities por entry
points: la id encolada se resuelve contra SU registry, jamás se serializa
código (#148).

**Lo que este módulo NO hace, y por qué:** no registra una estrategia
`remote-job` en el dispatcher. Ver `chimera_api.runs` y el ledger — el loop
todavía no sabe journalizar honestamente un trabajo que fue ENCOLADO y no
ejecutado, y decidir qué emite ahí es contrato, no wiring.
"""

from __future__ import annotations

import functools
import logging
import os
from typing import Any, Protocol, cast

import procrastinate
from procrastinate.connector import BaseConnector
from pydantic import BaseModel, ConfigDict

_LOGGER = logging.getLogger(__name__)

QUEUE_NAME = "chimera"
"""Cola única. Un solo nombre mientras haya un solo tipo de trabajo: colas
separadas son una decisión de OPERACIÓN (aislar latencias, dar prioridades) y
se toman cuando hay dos cargas que compitan, no antes."""

TASK_NAMESPACE = "chimera"
_MISSION_TASK_NAME = "run_mission"

MISSION_TASK = f"{TASK_NAMESPACE}:{_MISSION_TASK_NAME}"
"""Nombre estable de la tarea: `namespace:nombre`, la forma que procrastinate
compone al montar el blueprint (el separador es suyo, no nuestro).

Es CONTRATO entre dos procesos: el api lo escribe en Postgres y el worker lo
resuelve al leerlo, así que renombrarlo deja huérfanos los jobs ya encolados."""

_JOB_QUEUE_ENV = "CHIMERA_JOB_QUEUE"
_PROCRASTINATE = "procrastinate"
_DATABASE_URL_ENV = "CHIMERA_DATABASE_URL"


def _blueprint() -> procrastinate.Blueprint:
    """Un Blueprint NUEVO por app, y no uno de módulo.

    Dos razones, las dos verificadas contra la librería: (1) una `App`
    necesita conector —y por lo tanto DSN— al construirse, así que importar
    este módulo sin base (el api en Fase 1, los tests) no puede depender de
    que exista una app; (2) `add_tasks_from` MUTA el blueprint de origen (le
    antepone el namespace y le reasigna el dueño), de modo que montar uno
    compartido dos veces produce `chimera:chimera:run_mission` y la segunda
    app queda sin la tarea que cree tener."""
    blueprint = procrastinate.Blueprint()
    blueprint.task(name=_MISSION_TASK_NAME, queue=QUEUE_NAME)(run_mission)
    return blueprint


class MissionJob(BaseModel):
    """El contrato del job — validado en las DOS puntas (misma disciplina
    `frozen`/`extra="forbid"` que los payloads del wire).

    Viajan primitivas, jamás objetos vivos: el api no puede mandarle al worker
    su `RunResources` ni su proposer (serializar código es justo lo que el
    patrón de entry points evita, #148), así que manda lo que describe el
    trabajo y el worker reconstruye el resto con SU propia infra.

    `inputs` viaja RESUELTO (no `instance_id` crudo): lo que el worker corre
    es exactamente lo que el api decidió, sin una segunda resolución que
    pudiera divergir.

    `identity` es la del solicitante, serializada. Viaja explícita porque la
    autoridad del run es la de quien lo pidió: re-derivarla en el worker (de
    una env var, digamos) cambiaría en silencio con qué permisos corre un run
    ya autorizado."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str
    identity: dict[str, Any]
    mission: str
    capability_id: str
    inputs: dict[str, Any]
    max_turns: int
    max_steps: int
    budget: dict[str, Any] | None = None
    thread_id: str | None = None
    project_id: str | None = None


def job_queue_enabled() -> bool:
    """¿Este despliegue manda los runs de misión a la cola durable?

    Ausente ⇒ `False`: el camino sigue siendo `BackgroundTasks`, byte-idéntico
    a antes de P11 (un despliegue sin worker no puede empezar a encolar runs
    que nadie va a levantar). Un valor desconocido es error de CONFIGURACIÓN y
    revienta: leer un typo como "apagado" mandaría todos los runs por el
    camino que no espera aprobaciones, en silencio."""
    raw = os.environ.get(_JOB_QUEUE_ENV, "").strip()
    if not raw:
        return False
    if raw != _PROCRASTINATE:
        msg = (
            f"{_JOB_QUEUE_ENV}={raw!r} no es un backend de cola conocido "
            f"(único valor soportado: {_PROCRASTINATE!r})"
        )
        raise ValueError(msg)
    return True


def _connector() -> procrastinate.PsycopgConnector:
    """Conector ASÍNCRONO a propósito: procrastinate exige uno para correr un
    worker (el sync solo sabe encolar). Para encolar desde el api —que es
    código sync— se deriva el sync de este mismo (`get_sync_connector`), así
    que el DSN se declara UNA vez."""
    dsn = os.environ.get(_DATABASE_URL_ENV)
    if not dsn:
        msg = (
            f"{_DATABASE_URL_ENV} ausente: la cola durable es Postgres. "
            f"Sin base no hay cola — no hay fallback en memoria, porque una "
            f"cola que se pierde al reiniciar no es durabilidad (#148)."
        )
        raise ValueError(msg)
    return procrastinate.PsycopgConnector(conninfo=dsn)


def build_app(*, connector: BaseConnector | None = None) -> procrastinate.App:
    """La app con sus tareas registradas — lo que le faltaba al worker."""
    app = procrastinate.App(
        connector=connector if connector is not None else _connector()
    )
    app.add_tasks_from(_blueprint(), namespace=TASK_NAMESPACE)
    return app


@functools.cache
def get_app() -> procrastinate.App:
    """Una app por proceso: construirla abre un pool de conexiones detrás."""
    return build_app()


def defer_mission(job: MissionJob, *, app: procrastinate.App | None = None) -> str:
    """Encola el run de misión y vuelve — encolar NO es ejecutar (#148).

    Corre en el hilo del request HTTP, que es sync, así que usa el conector
    sync derivado del asíncrono. Se abre y se cierra por llamada: crear un run
    es una operación rara y pesada de por sí, y no dejar un pool colgando del
    proceso del api evita que el ciclo de vida de la cola se enrede con el de
    FastAPI."""
    resolved = app if app is not None else get_app()
    with (
        resolved.replace_connector(resolved.connector.get_sync_connector()) as sync_app,
        sync_app.open(),
    ):
        # `App.tasks` está tipado como `dict[str, Task[..., Unknown, ...]]`:
        # los parámetros de una tarea son dinámicos por diseño de la
        # librería, así que el tipo del `defer` no puede conocerse acá. El
        # contrato REAL de esos kwargs lo sostiene `MissionJob` en las dos
        # puntas — que es más fuerte que lo que este cast concede.
        tarea = cast(Any, sync_app).tasks[MISSION_TASK]
        return str(tarea.defer(**job.model_dump()))


class _SchemaHost(Protocol):
    """Lo único que el arranque necesita de la app — declarado como puerto
    para que el test lo cubra con un doble explícito en vez de parchear."""

    def check_connection(self) -> bool: ...

    @property
    def schema_manager(self) -> Any: ...


def apply_schema_if_missing(app: _SchemaHost) -> bool:
    """Instala el esquema de procrastinate si no está. Devuelve si lo aplicó.

    `procrastinate schema --apply` NO es idempotente (su propia ayuda lo dice:
    «won't work if the schema has already been applied»), así que el arranque
    pregunta primero: un worker que se reinicia —o dos que arrancan juntos—
    no puede morir por haber arrancado dos veces. El esquema no va en
    `engine/sql/init_v2.sql` porque no es nuestro: es DDL de la librería,
    atada a SU versión, y copiarla ahí la congelaría contra un upgrade."""
    if app.check_connection():
        return False
    _LOGGER.info("esquema de procrastinate ausente: aplicándolo")
    app.schema_manager.apply_schema()
    return True


# ── La tarea ────────────────────────────────────────────────────────────────


def run_mission(**payload: Any) -> None:
    """El run de misión, ejecutado en el worker.

    Sync a propósito: procrastinate corre las tareas sync en un hilo
    (`sync_to_async`), que es exactamente lo que una espera bloqueante de
    aprobación necesita — y lo que un hilo del servidor HTTP no podía dar.
    El paralelismo lo da `--concurrency` del worker, no este código.
    """
    _run_mission_job(MissionJob.model_validate(payload))


def _run_mission_job(job: MissionJob) -> None:
    """Delega en la raíz de composición del despliegue.

    Import perezoso de `chimera_api.runs`: ese módulo importa éste para
    encolar, y el ciclo se rompe acá — en el sentido que solo el worker
    recorre. Mismo patrón que el invocador MCP en `runs.py`.

    El armado del run (proposer, cruce del gateway, plan, compuerta de
    aprobación) NO se duplica acá: vive donde ya vivía, y este módulo aporta
    lo único que es suyo — que exista un proceso donde correrlo."""
    from chimera_api.runs import execute_mission_job

    execute_mission_job(job)


__all__ = [
    "MISSION_TASK",
    "TASK_NAMESPACE",
    "QUEUE_NAME",
    "MissionJob",
    "apply_schema_if_missing",
    "build_app",
    "defer_mission",
    "get_app",
    "job_queue_enabled",
    "run_mission",
]
