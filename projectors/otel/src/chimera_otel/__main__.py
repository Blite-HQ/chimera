"""El servicio: lee el stream, proyecta, exporta, avanza el cursor. Y repite.

    python -m chimera_otel [--once]

Corre bajo el perfil `otel` del compose, junto a un collector OTLP. El camino
por defecto del stack NO lo incluye (S-F §1): observabilidad es opcional, y un
proyector caído jamás debe poder afectar un run.

Variables de entorno:

| var                            | qué es                                      |
| ------------------------------ | ------------------------------------------- |
| `CHIMERA_OTEL_DATABASE_URL`    | DSN del usuario SOLO-SELECT                 |
| `OTEL_EXPORTER_OTLP_ENDPOINT`  | collector (default `http://localhost:4318`) |
| `CHIMERA_OTEL_CURSOR`          | archivo de cursor propio                    |
| `CHIMERA_OTEL_INTERVAL`        | segundos entre pasadas (default 2)          |
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

from chimera_otel.export import build_provider, export_all
from chimera_otel.projection import TracePlan, project_run
from chimera_otel.source import CursorFile, group_by_run, read_batch

_DEFAULT_CURSOR = Path(
    os.environ.get("CHIMERA_OTEL_CURSOR", "/var/lib/chimera-otel/cursor.json")
)
_DEFAULT_INTERVAL = float(os.environ.get("CHIMERA_OTEL_INTERVAL", "2"))


def _connect() -> object:
    dsn = os.environ.get("CHIMERA_OTEL_DATABASE_URL")
    if not dsn:
        msg = "CHIMERA_OTEL_DATABASE_URL no está definido (usuario SOLO-SELECT)"
        raise SystemExit(msg)
    import psycopg  # noqa: PLC0415 - dependencia pesada, solo el servicio la necesita

    return psycopg.connect(dsn, autocommit=True)


def run_once(connection: object, cursor: CursorFile) -> int:
    """Una pasada de catch-up. Devuelve cuántas trazas exportó."""
    after = cursor.read()
    batch = read_batch(connection, after)  # type: ignore[arg-type]
    if not batch:
        return 0

    plans: list[TracePlan] = []
    for run_events in group_by_run(batch):
        plan = project_run(run_events)
        if plan is not None:
            plans.append(plan)

    provider, generator = build_provider(OTLPSpanExporter())
    exported = export_all(provider, generator, plans)
    provider.force_flush()
    provider.shutdown()

    cursor.write(max(int(event["global_seq"]) for event in batch))
    return exported


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="una pasada y salir")
    parser.add_argument("--cursor", type=Path, default=_DEFAULT_CURSOR)
    parser.add_argument("--interval", type=float, default=_DEFAULT_INTERVAL)
    args = parser.parse_args(argv)

    connection = _connect()
    cursor = CursorFile(args.cursor)

    while True:
        exported = run_once(connection, cursor)
        print(f"chimera-otel: {exported} traza(s) exportada(s)", file=sys.stderr)
        if args.once:
            return 0
        time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
