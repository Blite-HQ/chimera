"""Tests de `scripts/record_session.py` — runbook para grabar una sesión
agéntica REAL (carril P4, mandato Dylan 2026-07-29, tarea 4). El script NO se
ejecuta acá contra litellm/una API key real (PROHIBIDO en esta sesión) —
solo se ejercita `--fake`: un `live_caller` + registry deterministas locales
recorren el MISMO camino de producción (proposer real → `ModelServer(mode=
"record")` → `chimera_api.model_session.write_session`), sin red.

`scripts/` no es un paquete instalable (mismo patrón que
`tests/unit/experiment/test_gen_extrapolation.py` /
`tests/unit/experiment/test_exp_r_vs_p.py`): el módulo se carga por ruta.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Protocol, cast

from chimera_api.model_session import load_session

from blite.runtime.content_store import InMemoryContentStore


class _RecordSessionModule(Protocol):
    """Firma tipada de `scripts/record_session.py` para pyright strict (el
    módulo en sí no está en el `include` de pyright — ver comentario en
    `chimera_api.runs._load_corpus_matrix` — pero este archivo de test SÍ)."""

    def record_session(
        self,
        *,
        session_dir: Path,
        mission: str,
        instance_id: str | None,
        capability_id: str | None,
        model_id: str,
        max_turns: int,
        fake: bool,
    ) -> str: ...

    def main(self, argv: list[str] | None = None) -> int: ...


def _find_script() -> Path:
    for base in (Path(__file__).resolve(), *Path(__file__).resolve().parents):
        candidate = base / "scripts" / "record_session.py"
        if candidate.is_file():
            return candidate
    msg = "scripts/record_session.py no encontrado sobre este archivo"
    raise FileNotFoundError(msg)


def _load_module() -> _RecordSessionModule:
    script_path = _find_script()
    spec = importlib.util.spec_from_file_location("record_session", script_path)
    if spec is None:
        msg = f"no se pudo construir un spec de import para {script_path}"
        raise ImportError(msg)
    loader = spec.loader
    if loader is None:
        msg = f"el spec de {script_path} no tiene loader"
        raise ImportError(msg)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return cast(_RecordSessionModule, module)


rs = _load_module()

_CTX = {"domain_id": "domain-default"}


class TestRecordSessionFake:
    def test_fake_graba_una_sesion_cargable_por_load_session(
        self, tmp_path: Path
    ) -> None:
        # Arrange
        session_dir = tmp_path / "sesion-fake-dry-run"

        # Act
        run_id = rs.record_session(
            session_dir=session_dir,
            mission="particionar una red de prueba y certificar el corte",
            instance_id=None,
            capability_id=None,
            model_id="anthropic/claude-sonnet-test",
            max_turns=1,
            fake=True,
        )

        # Assert — el runbook completo (proposer real -> ModelServer(record)
        # -> write_session) deja algo que `load_session` puede recargar.
        assert run_id.startswith("run-")
        assert (session_dir / "manifest.json").is_file()
        loaded_manifest, backend_id, local = load_session(
            session_dir, InMemoryContentStore(), _CTX
        )
        assert backend_id == "anthropic/claude-sonnet-test"
        assert local is False
        assert loaded_manifest.items() != ()

    def test_main_con_flag_fake_retorna_cero(self, tmp_path: Path) -> None:
        # Arrange
        session_dir = tmp_path / "sesion-cli"

        # Act
        exit_code = rs.main(
            [
                "--session-dir",
                str(session_dir),
                "--mission",
                "misión vía CLI",
                "--max-turns",
                "1",
                "--fake",
            ]
        )

        # Assert
        assert exit_code == 0
        assert (session_dir / "manifest.json").is_file()
