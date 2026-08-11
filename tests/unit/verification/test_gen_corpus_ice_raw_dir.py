"""Fail-loud del directorio de snapshots del ICE (`scripts/gen_corpus_ice.py`).

Decisión #173.1 (opción b): la copia verbatim del portal del ICE ya no viaja
en este árbol (`NOTICE` §2, `docs/pre-flip-checklist.md` §4.2). El script no
puede morir con un `FileNotFoundError` críptico cuando faltan los snapshots
-- este archivo fija el contrato: mensaje legible (qué pasó, de dónde
bajarlos, dónde ponerlos, que la receta y los digests siguen vivos para
re-derivar y comprobar) + la posibilidad de apuntar el directorio por
argumento (`--raw-dir`) o por variable de entorno, en vez de una ruta clavada.

Todos los casos usan `tmp_path` -- nunca invocan el script contra el
directorio default real (`knowledge/islanding/raw/`, que este cambio borra):
eso evitaría disparar la derivación real y escribir sobre el corpus congelado
si algún día el árbol tuviera los snapshots puestos a mano.

`scripts/` no es un paquete instalable -- mismo patrón de carga por ruta que
`tests/unit/experiment/test_gen_corpus_rvsp.py`.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Protocol, cast

import pytest


class _GenModule(Protocol):
    DEFAULT_RAW_DIR: Path
    RAW_DIR_ENV_VAR: str
    NODES_FILENAME: str
    EDGES_FILENAME: str
    IceSnapshotsMissingError: type[FileNotFoundError]

    def resolve_raw_dir(self, raw_dir_arg: str | None = None) -> Path: ...

    def require_snapshots(self, raw_dir: Path) -> tuple[Path, Path]: ...

    def main(self, argv: list[str] | None = None) -> int: ...


def _find_repo_root() -> Path:
    for base in (Path(__file__).resolve(), *Path(__file__).resolve().parents):
        if (base / "scripts" / "gen_corpus_ice.py").is_file():
            return base
    msg = "scripts/gen_corpus_ice.py no encontrado sobre este archivo"
    raise FileNotFoundError(msg)


def _load_module() -> _GenModule:
    script_path = _find_repo_root() / "scripts" / "gen_corpus_ice.py"
    spec = importlib.util.spec_from_file_location("gen_corpus_ice", script_path)
    if spec is None or spec.loader is None:
        msg = f"no se pudo construir un spec de import para {script_path}"
        raise ImportError(msg)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return cast("_GenModule", module)


gen = _load_module()


class TestResolveRawDir:
    """Prioridad: `--raw-dir` explícito > variable de entorno > default del árbol."""

    def test_sin_argumento_ni_env_usa_el_default_del_arbol(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv(gen.RAW_DIR_ENV_VAR, raising=False)

        assert gen.resolve_raw_dir(None) == gen.DEFAULT_RAW_DIR

    def test_el_argumento_explicito_gana_sobre_la_env_var(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        env_dir = tmp_path / "desde-env"
        arg_dir = tmp_path / "desde-arg"
        monkeypatch.setenv(gen.RAW_DIR_ENV_VAR, str(env_dir))

        assert gen.resolve_raw_dir(str(arg_dir)) == arg_dir

    def test_sin_argumento_cae_a_la_env_var(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        env_dir = tmp_path / "desde-env"
        monkeypatch.setenv(gen.RAW_DIR_ENV_VAR, str(env_dir))

        assert gen.resolve_raw_dir(None) == env_dir


class TestRequireSnapshotsFailLoud:
    def test_directorio_vacio_levanta_con_mensaje_legible(self, tmp_path: Path) -> None:
        with pytest.raises(gen.IceSnapshotsMissingError) as excinfo:
            gen.require_snapshots(tmp_path)

        mensaje = str(excinfo.value)
        # No es un FileNotFoundError críptico: dice qué pasó, de dónde bajar
        # los datos, dónde ponerlos, y que la receta/digests siguen vivos.
        assert "datos-ice-se.opendata.arcgis.com" in mensaje
        assert "Subestaciones" in mensaje
        assert "LineasDeTransmision" in mensaje
        assert str(tmp_path) in mensaje
        assert gen.RAW_DIR_ENV_VAR in mensaje
        assert "--raw-dir" in mensaje
        assert "digest" in mensaje.lower()
        assert len(mensaje) > 200, "mensaje sospechosamente corto para ser 'legible'"

    def test_falta_solo_un_snapshot_tambien_se_reporta_por_nombre(
        self, tmp_path: Path
    ) -> None:
        (tmp_path / gen.NODES_FILENAME).write_text("{}", encoding="utf-8")

        with pytest.raises(gen.IceSnapshotsMissingError) as excinfo:
            gen.require_snapshots(tmp_path)

        assert gen.EDGES_FILENAME in str(excinfo.value)

    def test_con_ambos_snapshots_presentes_devuelve_las_rutas(
        self, tmp_path: Path
    ) -> None:
        nodes = tmp_path / gen.NODES_FILENAME
        edges = tmp_path / gen.EDGES_FILENAME
        nodes.write_text("{}", encoding="utf-8")
        edges.write_text("{}", encoding="utf-8")

        resolved_nodes, resolved_edges = gen.require_snapshots(tmp_path)

        assert resolved_nodes == nodes
        assert resolved_edges == edges


class TestMainFailsLoudNotCryptic:
    """`main()` no debe dejar escapar un traceback críptico -- atrapa el
    fail-loud, lo imprime legible, y devuelve un código de salida != 0."""

    def test_raw_dir_explicito_sin_snapshots_falla_legible_por_stderr(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        exit_code = gen.main(["--raw-dir", str(tmp_path)])

        assert exit_code != 0
        salida = capsys.readouterr().err
        assert "datos-ice-se.opendata.arcgis.com" in salida
        assert str(tmp_path) in salida

    def test_raw_dir_por_env_var_sin_snapshots_tambien_falla_legible(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setenv(gen.RAW_DIR_ENV_VAR, str(tmp_path))

        exit_code = gen.main([])

        assert exit_code != 0
        salida = capsys.readouterr().err
        assert str(tmp_path) in salida
