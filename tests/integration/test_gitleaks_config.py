"""Las allowlists de `.gitleaks.toml` — que silencien ruido y NADA más.

Este archivo existe por un fallo real: la primera versión de la allowlist de
anotaciones anclaba a línea completa, así que cubría `signing_key: Tipo` sola
en su línea pero seguía marcando `def firmar(key: ed25519.Ed25519PrivateKey)`.
CI se puso roja y el diagnóstico costó más de lo que cuesta este archivo.

**Por qué se ejerce el binario y no las regexes.** La tentación es leer el TOML
y correr las regexes con el `re` de Python. No sirve: gitleaks las aplica a
targets distintos (`line`, `match`, `secret`) según la allowlist, con RE2 y no
con `re`. Un test así probaría un modelo del motor, y un modelo equivocado del
motor es exactamente lo que produjo el fallo. Se corre gitleaks de verdad.

En CI esto corre en el job Security, que es donde el binario existe. En local
se salta si no está instalado — el pre-commit ya avisa de esa ausencia.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / ".gitleaks.toml"

RUIDO = """\
def firmar(key: ed25519.Ed25519PrivateKey) -> bytes: ...


class Firmante:
    signing_key: cryptography.hazmat.Ed25519PrivateKey

    def __init__(
        self, private_key: ed25519.Ed25519PrivateKey | None = None, *, v: int = 1
    ) -> None: ...


# En prosa: `signing_key: ed25519.Ed25519PrivateKey` es una anotación.
"""
"""Anotaciones de tipo, en las cuatro posiciones que aparecen de verdad en el
repo: parámetro, atributo de clase, firma multilínea y código inline en un
comentario. Ninguna tiene valor; ninguna es un secreto."""

SECRETOS = """\
api_key = "sk_live_4eC39HqLyjWDarjtT1zdp7dcABCDEF"
signing_key: str = 'ghp_16C7e42F292c6912E7710c838347Ae178B4a'
"""
"""Asignaciones CON valor, y con los MISMOS nombres de campo que el ruido: la
excepción tiene que distinguir por la forma del valor, jamás por el nombre."""

pytestmark = pytest.mark.skipif(
    shutil.which("gitleaks") is None, reason="gitleaks no instalado"
)


def _escanear(directorio: Path) -> list[str]:
    """Corre gitleaks con NUESTRA config y devuelve los archivos con hallazgo."""
    reporte = directorio / "reporte.json"
    binario = shutil.which("gitleaks")
    assert binario is not None
    subprocess.run(  # noqa: S603 — binario resuelto por `which`, sin shell
        [
            binario,
            "dir",
            "--no-banner",
            "--redact",
            "-f",
            "json",
            "-r",
            str(reporte),
            str(directorio),
        ],
        capture_output=True,
        check=False,
    )
    hallazgos = json.loads(reporte.read_text(encoding="utf-8"))
    return [Path(h["File"]).name for h in hallazgos]


@pytest.fixture
def arbol(tmp_path: Path) -> Path:
    shutil.copy(CONFIG_PATH, tmp_path / ".gitleaks.toml")
    (tmp_path / "ruido.py").write_text(RUIDO, encoding="utf-8")
    (tmp_path / "secretos.py").write_text(SECRETOS, encoding="utf-8")
    return tmp_path


def test_una_anotacion_de_tipo_no_es_un_hallazgo(arbol: Path) -> None:
    """El ruido que motivó la excepción, en sus cuatro formas."""
    assert "ruido.py" not in _escanear(arbol)


def test_un_secreto_real_sigue_siendo_un_hallazgo(arbol: Path) -> None:
    """La contraprueba, que es la que importa.

    Una allowlist es la única parte de un escáner que puede QUITAR detección.
    Si alguien la ensancha hasta cubrir `campo: valor` en general, este test
    cae antes de que un secreto de verdad pase inadvertido.
    """
    assert "secretos.py" in _escanear(arbol)


def test_toda_allowlist_dice_por_que_existe() -> None:
    """Una excepción sin motivo escrito es una excepción que nadie puede revisar.

    No necesita gitleaks, pero vive acá porque cuida el mismo archivo.
    """
    config = tomllib.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    sin_descripcion = [
        allowlist
        for allowlist in config["allowlists"]
        if not allowlist.get("description", "").strip()
    ]
    assert sin_descripcion == []
