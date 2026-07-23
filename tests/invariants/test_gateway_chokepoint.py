"""
INV-1 como gate: nadie invoca el Registry por fuera del gateway/runtime.

Nota execution/01 §6/§9 (modo de falla "bypass del gateway", mitigación
acordada con Dylan): import-linter restringe imports ENTRE paquetes, pero no
impide que un módulo del engine invoque el despacho de capabilities
directamente. Este test cierra ese hueco al estilo de
test_enforced_anchors.py: escanea los imports reales (AST) de todo
`engine/src/blite` y falla si un módulo fuera de `blite.gateway`/
`blite.runtime` importa `blite.runtime.registry` — la única puerta del
engine hacia capabilities (ADR-008) solo se cruza desde el chokepoint.
"""

from __future__ import annotations

import ast
from pathlib import Path

ENGINE_SRC = Path(__file__).parents[2] / "engine" / "src" / "blite"

# Los únicos paquetes con derecho a tocar el registry: el chokepoint (INV-1)
# y el propio runtime que lo implementa/despacha.
ALLOWED_PREFIXES = ("gateway", "runtime")

REGISTRY_MODULE = "blite.runtime.registry"


def _module_imports_registry(source: str) -> bool:
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(alias.name.startswith(REGISTRY_MODULE) for alias in node.names):
                return True
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module.startswith(REGISTRY_MODULE):
                return True
            # `from blite.runtime import registry` — mismo bypass, otra forma.
            if module == "blite.runtime" and any(
                alias.name == "registry" for alias in node.names
            ):
                return True
    return False


def test_engine_source_tree_exists() -> None:
    """Backstop (patrón test_enforced_anchors): si el árbol no está, el escaneo
    de abajo pasaría en silencio con cero archivos — eso es un fallo, no un pass."""
    assert ENGINE_SRC.is_dir(), f"no existe {ENGINE_SRC} — el escaneo sería vacío"


def test_no_module_outside_gateway_or_runtime_imports_the_registry() -> None:
    """El despacho de capabilities solo se alcanza vía el chokepoint (INV-1)."""
    offenders: list[str] = []
    for py_file in sorted(ENGINE_SRC.rglob("*.py")):
        relative = py_file.relative_to(ENGINE_SRC)
        if relative.parts and relative.parts[0] in ALLOWED_PREFIXES:
            continue
        if _module_imports_registry(py_file.read_text(encoding="utf-8")):
            offenders.append(str(relative))
    assert not offenders, (
        f"módulos fuera de blite.gateway/blite.runtime importan "
        f"{REGISTRY_MODULE!r} (bypass del chokepoint, INV-1 / nota 01 §6): "
        f"{offenders}"
    )
