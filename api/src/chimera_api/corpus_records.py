"""La regla de identidad del corpus, en un solo lugar (§15.3 generalizada).

Extraído de `instance_verifiers` cuando V3/M20 necesitó la MISMA disciplina
para `knowledge/rvsp/`: slug fuera de forma, archivo ausente, o digest que no
cierra sobre el propio contenido ⇒ `None`, fail-closed. Duplicarla habría
significado dos definiciones de "este corpus es el que dice ser", y la que
se relajara primero sería la que un dato tamperado usaría para entrar.

El digest es JSON canónico PLANO (`json.dumps` con `sort_keys`),
deliberadamente NO el JCS de `blite.certificate.canonical` — ese es el
algoritmo de otro anexo, para digests de contenido de certificado, no para
identidad de corpus. `scripts/gen_corpus_rvsp.record_digest` implementa la
misma regla del lado productor.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

CORPUS_SLUG_PATTERN = re.compile(r"[a-z0-9][a-z0-9-]*")
"""Un `instance_id` que viaja en un body HTTP jamás se interpola en una ruta
de archivo sin pasar por este guard primero (traversal incluido)."""


def corpus_record_digest(record_without_digest: dict[str, Any]) -> str:
    """SHA-256 del record SIN su campo `digest` — su identidad."""
    return hashlib.sha256(
        json.dumps(
            record_without_digest,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode()
    ).hexdigest()


def load_corpus_record(directory: Path, slug: str) -> dict[str, Any] | None:
    """Carga+valida `<slug>.json` bajo `directory`, o `None` fail-closed.

    Un corpus malformado (JSON roto, campo ausente, tipo inesperado) es la
    MISMA señal que un digest que no coincide — jamás un 500 por un dato de
    conocimiento corrupto, y jamás un dato no verificado río abajo.
    """
    if not CORPUS_SLUG_PATTERN.fullmatch(slug):
        return None
    path = directory / f"{slug}.json"
    if not path.is_file():
        return None
    try:
        record: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        embedded = record["digest"]
        record_without_digest = {k: v for k, v in record.items() if k != "digest"}
        if not isinstance(embedded, str):
            return None
        if corpus_record_digest(record_without_digest) != embedded:
            return None
    except (OSError, KeyError, TypeError, ValueError):
        return None
    return record
