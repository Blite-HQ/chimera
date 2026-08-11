"""
Escáner del gate de agnosticismo multi-capa (O11) — la lógica, sin veredicto.

Vive aparte de `test_agnosticism_layers.py` para poder probarse contra archivos
sintéticos: un gate que solo se valida por «hoy pasa» no distingue entre estar
sano y estar ciego.

Fuente de términos: `scenario_denylist.txt` — el MISMO archivo que vigila los
manifests (`test_capability_genericity.py`). Un término se agrega una vez y las
dos compuertas lo heredan; dos listas serían drift garantizado.
"""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path

REPO_ROOT = Path(__file__).parents[2]
DENYLIST_PATH = Path(__file__).parent / "scenario_denylist.txt"
EXCEPTIONS_PATH = Path(__file__).parent / "agnosticism_exceptions.toml"

#: `doctrina` = la regla citándose a sí misma · `contrato` = identificador YA
#: estampado en bundles emitidos (cambiarlo re-digesta: exige ceremonia) ·
#: `deuda` = fuga real, con el ítem de backlog que la mata.
VALID_KINDS = ("doctrina", "contrato", "deuda")


@dataclass(frozen=True)
class Finding:
    """Una aparición de vocabulario de escenario en una capa que debe ser genérica."""

    path: str
    line: int
    term: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line} — {self.term!r}"


@dataclass(frozen=True)
class ExceptionEntry:
    """Una fuga DECLARADA: dónde, qué término, de qué clase y qué la mata."""

    path: str
    terms: tuple[str, ...]
    kind: str
    causa: str
    muere_con: str

    def covers(self, finding: Finding) -> bool:
        """Cubre el archivo COMPLETO para los términos que declara.

        Deliberadamente sin número de línea: anclar a la línea convierte cada
        edición del archivo en una falla del gate y entrena a la gente a
        renumerar sin pensar.
        """
        return finding.path == self.path and finding.term in self.terms


@dataclass(frozen=True)
class LayerSpec:
    """Una capa que debe ser genérica y los archivos suyos que se escanean."""

    root: str
    patterns: tuple[str, ...]
    exclude: tuple[str, ...] = ()

    def files(self) -> tuple[Path, ...]:
        base = REPO_ROOT / self.root
        if not base.is_dir():
            return ()
        found: set[Path] = set()
        for pattern in self.patterns:
            found.update(p for p in base.glob(pattern) if p.is_file())
        kept = [p for p in sorted(found) if not self._excluded(p, base)]
        return tuple(kept)

    def _excluded(self, path: Path, base: Path) -> bool:
        """`fnmatch` sobre la ruta relativa en POSIX.

        `Path.match` NO trata `**` como recursivo en 3.12 — una exclusión que
        parece cubrir subdirectorios y no lo hace es peor que no tenerla. Con
        `fnmatch`, `*` sí cruza `/`, así que `*lenses/*` cubre cualquier
        profundidad y el comportamiento es el que dice el patrón.
        """
        rel = path.relative_to(base).as_posix()
        return any(fnmatch(rel, pattern) for pattern in self.exclude)


#: Excluidos POR DOCTRINA (no por conveniencia):
#: - tests: nombrar el escenario que se prueba es legítimo.
#: - `fixtures/`: son DATOS etiquetados (modo Replay con banner), misma clase que
#:   `knowledge/` o las políticas de `distributions/`.
#: - `lenses/`: el punto de enchufe de dominio del Studio (P13). Su propio código
#:   lo declara: «la única parte del Studio que puede nombrar capabilities de
#:   redes eléctricas, y por eso vive acá y no en el shell» (`gridLens.tsx`). Es
#:   el equivalente de `capabilities/` en el lado D — si una lente no pudiera
#:   nombrar su dominio, no habría dónde ponerlo.
#: `capabilities/` no aparece porque ADR-008 pone el dominio justo ahí — lo que
#: sí se le exige (manifest genérico) lo vigila `test_capability_genericity.py`.
_TS_EXCLUDE = (
    "*.test.ts",
    "*.test.tsx",
    "*fixtures/*",
    "*lenses/*",
    "*.d.ts",
)

GENERIC_LAYERS: tuple[LayerSpec, ...] = (
    LayerSpec(root="sdk/src", patterns=("**/*.py",)),
    LayerSpec(root="engine/src", patterns=("**/*.py",)),
    LayerSpec(root="api/src", patterns=("**/*.py",)),
    LayerSpec(
        root="apps/studio/src", patterns=("**/*.ts", "**/*.tsx"), exclude=_TS_EXCLUDE
    ),
    LayerSpec(
        root="packages",
        patterns=("**/src/**/*.ts", "**/src/**/*.tsx"),
        exclude=_TS_EXCLUDE,
    ),
)


def load_denylist() -> tuple[str, ...]:
    """Términos de escenario, en minúsculas (mismo archivo que el gate de manifests)."""
    return tuple(
        line.strip().lower()
        for line in DENYLIST_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    )


def load_exceptions() -> tuple[ExceptionEntry, ...]:
    """Lee `agnosticism_exceptions.toml`. Sin archivo = sin excepciones (gate duro)."""
    if not EXCEPTIONS_PATH.is_file():
        return ()
    raw = tomllib.loads(EXCEPTIONS_PATH.read_text(encoding="utf-8"))
    entries: list[ExceptionEntry] = []
    for item in raw.get("exception", []):
        entries.append(
            ExceptionEntry(
                path=str(item.get("path", "")),
                terms=tuple(str(t).lower() for t in item.get("terms", ())),
                kind=str(item.get("kind", "")),
                causa=str(item.get("causa", "")),
                muere_con=str(item.get("muere_con", "")),
            )
        )
    return tuple(entries)


def _pattern_for(term: str) -> re.Pattern[str]:
    """Palabra completa e insensible a mayúsculas, con `_` y `-` como frontera.

    Ni `\\b` ni la subcadena sirven aquí:

    - por subcadena, `ice` matchearía `service`/`slice`/`device` y el gate
      moriría de ruido — que es como mueren los gates;
    - con `\\b`, `_` es carácter de palabra, así que `_ISLANDING_CORPUS_DIR` NO
      matchea `islanding` — y el nombre de un identificador es justo donde el
      vocabulario de escenario se esconde mejor.

    La frontera es «cualquier cosa que no sea letra o dígito». (El gate de
    manifests sí usa subcadena: ahí el texto es corto y controlado.)
    """
    return re.compile(rf"(?<![0-9a-z]){re.escape(term)}(?![0-9a-z])", re.IGNORECASE)


def scan_paths(
    paths: tuple[Path, ...], base: Path, terms: tuple[str, ...]
) -> tuple[Finding, ...]:
    """Busca `terms` en `paths`; las rutas de los hallazgos son relativas a `base`."""
    patterns = [(term, _pattern_for(term)) for term in terms]
    findings: list[Finding] = []
    for path in paths:
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        rel = path.relative_to(base).as_posix()
        for lineno, line in enumerate(text.splitlines(), start=1):
            for term, pattern in patterns:
                if pattern.search(line):
                    findings.append(Finding(path=rel, line=lineno, term=term))
    return tuple(findings)


def scan_generic_layers() -> tuple[Finding, ...]:
    """Barrido completo de las capas genéricas contra el denylist compartido."""
    terms = load_denylist()
    findings: list[Finding] = []
    for layer in GENERIC_LAYERS:
        findings.extend(scan_paths(layer.files(), REPO_ROOT, terms))
    return tuple(findings)
