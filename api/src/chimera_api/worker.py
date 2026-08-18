"""
P11 — el arranque del worker de la cola durable (`python -m chimera_api.worker`).

**Por qué un módulo propio y no `procrastinate worker` a secas** (que es lo
que el compose declaraba desde el MVP): la CLI de procrastinate quiere un
`--app` importable, o sea una `App` construida AL IMPORTAR — y construirla
exige el DSN, así que importar el paquete sin base fallaría (el api en Fase 1,
los tests). Además el arranque tiene un paso propio que la CLI no cubre:
instalar el esquema de la librería la primera vez, sin morir la segunda
(`procrastinate schema --apply` no es idempotente). Los dos motivos caben en
estas pocas líneas y dejan el compose con un comando que dice lo que hace.

Tres subcomandos, ninguno mágico:

- (sin argumentos) — aplica el esquema si falta y levanta el worker.
- `schema` — solo el esquema (útil para un `docker compose run` de
  mantenimiento, o para preparar la base antes de escalar workers).
- `healthcheck` — ¿hay base y hay esquema? Es lo que el healthcheck del
  compose corre: un worker "arriba" pero sin cola no es un worker sano.
"""

from __future__ import annotations

import logging
import os
import sys

from chimera_api.jobs import QUEUE_NAME, apply_schema_if_missing, get_app

_LOGGER = logging.getLogger(__name__)

_CONCURRENCY_ENV = "CHIMERA_WORKER_CONCURRENCY"
_DEFAULT_CONCURRENCY = 4
"""Cuántos trabajos a la vez. Mayor que 1 a propósito y por una razón
concreta de ESTE diseño: un run detenido esperando una aprobación humana
ocupa su slot hasta que alguien conteste, así que con concurrencia 1 la
primera aprobación pendiente congelaría la cola entera. No es afinamiento
prematuro — es la consecuencia directa de tener esperas largas."""


def _concurrency() -> int:
    raw = os.environ.get(_CONCURRENCY_ENV)
    if raw is None:
        return _DEFAULT_CONCURRENCY
    try:
        valor = int(raw)
    except ValueError:
        valor = 0
    if valor < 1:
        _LOGGER.warning(
            "%s=%r no es un entero positivo: se usa el default %s",
            _CONCURRENCY_ENV,
            raw,
            _DEFAULT_CONCURRENCY,
        )
        return _DEFAULT_CONCURRENCY
    return valor


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
    args = list(sys.argv[1:] if argv is None else argv)
    comando = args[0] if args else "worker"
    app = get_app()

    if comando == "healthcheck":
        with app.open():
            sano = app.check_connection()
        if not sano:
            _LOGGER.error("la cola no tiene esquema: el worker no puede consumir")
        return 0 if sano else 1

    if comando == "schema":
        with app.open():
            aplicado = apply_schema_if_missing(app)
        _LOGGER.info("esquema %s", "aplicado" if aplicado else "ya presente")
        return 0

    if comando != "worker":
        _LOGGER.error(
            "comando desconocido: %r (worker | schema | healthcheck)", comando
        )
        return 2

    with app.open():
        apply_schema_if_missing(app)
    # `run_worker` abre y cierra la app por su cuenta; el bloque de arriba se
    # cierra antes a propósito, para no dejar dos pools vivos por nada.
    app.run_worker(queues=[QUEUE_NAME], concurrency=_concurrency())
    return 0


if __name__ == "__main__":  # pragma: no cover - punto de entrada del proceso
    raise SystemExit(main())
