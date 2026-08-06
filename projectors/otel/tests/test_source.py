"""La fuente: cursor propio y agrupación por run — sin Postgres.

Lo que necesita una base de datos (el `SELECT`) se verifica vivo contra el
compose; lo que decide comportamiento se prueba acá.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from chimera_otel.source import CursorFile, group_by_run, row_to_event


class TestCursor:
    def test_sin_archivo_arranca_desde_el_principio(self, tmp_path: Path) -> None:
        assert CursorFile(tmp_path / "no-existe.json").read() == 0

    def test_ida_y_vuelta(self, tmp_path: Path) -> None:
        cursor = CursorFile(tmp_path / "sub" / "cursor.json")
        cursor.write(42)
        assert cursor.read() == 42

    def test_un_cursor_corrupto_reproyecta_en_vez_de_explotar(
        self, tmp_path: Path
    ) -> None:
        """Reproyectar es idempotente (§4), así que la opción segura es barata.

        La alternativa —levantar— dejaría el proyector muerto por un archivo de
        estado, que es justo lo que un consumer opcional no debe hacer.
        """
        path = tmp_path / "cursor.json"
        path.write_text("{no es json", encoding="utf-8")
        assert CursorFile(path).read() == 0

    def test_un_cursor_sin_la_llave_tambien(self, tmp_path: Path) -> None:
        path = tmp_path / "cursor.json"
        path.write_text('{"otra_cosa": 9}', encoding="utf-8")
        assert CursorFile(path).read() == 0


class TestFilaAEvento:
    def test_normaliza_la_fila_al_wire(self) -> None:
        fila = (
            "run-1",
            2,
            77,
            "run.started",
            "user:x",
            "chimera",
            {"a": 1},
            datetime(2026, 8, 5, 10, 0, tzinfo=UTC),
        )
        evento = row_to_event(fila)
        assert evento["stream_id"] == "run-1"
        assert evento["global_seq"] == 77
        assert evento["payload"] == {"a": 1}
        assert evento["occurred_at"].startswith("2026-08-05T10:00")

    def test_acepta_el_payload_como_texto(self) -> None:
        """Según el driver, `jsonb` puede llegar como dict o como str."""
        fila = ("run-1", 1, 1, "t", "a", "d", '{"b": 2}', "2026-08-05T10:00:00+00:00")
        assert row_to_event(fila)["payload"] == {"b": 2}


class TestAgrupacion:
    def test_un_lote_con_varios_runs_no_produce_una_traza_mezclada(self) -> None:
        """Un trace por run (§3): proyectar el lote «tal cual» los fundiría."""
        lote = [
            {"stream_id": "run-a", "seq": 1},
            {"stream_id": "run-b", "seq": 1},
            {"stream_id": "run-a", "seq": 2},
        ]
        grupos = list(group_by_run(lote))
        assert [len(g) for g in grupos] == [2, 1]
        assert {e["stream_id"] for e in grupos[0]} == {"run-a"}
