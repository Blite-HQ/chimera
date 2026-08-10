"""
Lectura de un corpus: qué instancias hay y con qué identidad.

**Tres digests, tres disciplinas, y por eso C-13 existe.** Un mismo documento
JSON admite más de un digest legítimo, y publicar «el digest» sin decir cuál
convierte una promesa de verificabilidad en ruido:

| digest              | sobre qué                              | quién lo usa                        |
| ------------------- | -------------------------------------- | ----------------------------------- |
| `file_sha256`       | los BYTES del archivo distribuido      | quien descarga (`sha256sum`, Croissant) |
| `embedded_digest`   | el JSON compacto SIN la llave `digest`  | la identidad interna del corpus     |
| `canonical_digest`  | `C(documento)` del anexo, entero        | el kernel de confianza de esta plataforma |

Los tres son correctos y ninguno sustituye a otro: los bytes cambian con un
final de línea, el interno no; el interno ignora su propia llave, el canónico
no. El export los publica ETIQUETADOS — jamás uno solo, jamás re-digestando.

**Nunca se reescribe un digest.** El interno se recalcula solo para COMPROBAR
que el archivo es consistente consigo mismo; si no coincide, esto explota en
vez de estampar el valor nuevo. La regla del freeze §15.3 es que el digest
manda: un archivo que dejó de coincidir con su digest es un incidente, no una
oportunidad de re-sellar.

**No sabe de qué trata el dato.** Un corpus es un directorio de documentos con
nombre de instancia y digest. Qué haya adentro es del despliegue que lo declara.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from blite.certificate.canonical import canonicalize

INSTANCE_KEY = "instancia"
DIGEST_KEY = "digest"
"""Las DOS llaves que un documento de corpus debe traer. Es toda la convención
que esta capa impone: sin nombre no hay identidad, sin digest no hay
verificabilidad."""

IDENTITY_KEYS = ("dataset_id", "corpus", "procedencia")
"""Llaves de identidad OPCIONALES. Los corpus más nuevos las traen; los más
viejos no, y eso se reporta como ausencia en vez de rellenarse — un
`procedencia` inventado es peor que un `procedencia` faltante."""


class CorpusError(Exception):
    """El corpus no se puede leer con integridad. Jamás se degrada a parcial."""


def empty_identity() -> dict[str, str]:
    return {}


@dataclass(frozen=True)
class InstanceEntry:
    """Una instancia del corpus, con sus tres digests y su identidad declarada."""

    instance: str
    file_name: str
    file_sha256: str
    embedded_digest: str
    canonical_digest: str
    identity: Mapping[str, str] = field(default_factory=empty_identity)


def embedded_digest(document: Mapping[str, Any]) -> str:
    """La disciplina interna del corpus: compacto, ASCII, sin la llave `digest`.

    Se replica exacta —incluido `ensure_ascii=True`— porque es la que produjo
    los valores ya estampados. Cualquier variación (separadores, escape de
    no-ASCII, orden) da otro número y rompería la identidad de todo el corpus.
    """
    sin_digest = {k: v for k, v in document.items() if k != DIGEST_KEY}
    payload = json.dumps(
        sin_digest, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def _leer_documento(path: Path) -> dict[str, Any]:
    try:
        raw: Any = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        msg = f"{path.name}: no es JSON válido — {exc}"
        raise CorpusError(msg) from exc
    if not isinstance(raw, dict):
        msg = f"{path.name}: un documento de corpus debe ser un objeto JSON"
        raise CorpusError(msg)
    return cast("dict[str, Any]", raw)


def _entrada(path: Path) -> InstanceEntry:
    document = _leer_documento(path)

    for required in (INSTANCE_KEY, DIGEST_KEY):
        if not str(document.get(required, "")).strip():
            msg = (
                f"{path.name}: falta {required!r} — sin esa llave la instancia "
                "no tiene identidad publicable"
            )
            raise CorpusError(msg)

    declarado = str(document[DIGEST_KEY])
    recalculado = embedded_digest(document)
    if declarado != recalculado:
        msg = (
            f"{path.name}: el digest embebido no corresponde al contenido "
            f"(declara {declarado[:12]}…, calcula {recalculado[:12]}…). El "
            "digest manda: esto se reporta, jamás se re-sella"
        )
        raise CorpusError(msg)

    return InstanceEntry(
        instance=str(document[INSTANCE_KEY]),
        file_name=path.name,
        file_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        embedded_digest=declarado,
        # `canonicalize` habla el modelo de datos JSON, y esto ya lo es por
        # haber salido de `json.loads` — no hace falta convertir nada.
        canonical_digest=hashlib.sha256(canonicalize(document)).hexdigest(),
        identity={
            key: str(document[key])
            for key in IDENTITY_KEYS
            if str(document.get(key, "")).strip()
        },
    )


def load_corpus(root: Path) -> tuple[InstanceEntry, ...]:
    """Todas las instancias de un directorio, ordenadas por nombre de archivo.

    Fail-closed: un directorio que no existe, un documento roto, un digest que
    no cuadra o dos instancias con el mismo nombre detienen la carga entera. Un
    catálogo a medias es peor que ninguno — quien lo consuma no tiene forma de
    saber qué le faltó.
    """
    if not root.is_dir():
        msg = f"{root}: el directorio de dataset declarado no existe"
        raise CorpusError(msg)

    entradas = tuple(_entrada(path) for path in sorted(root.glob("*.json")))

    vistos: dict[str, str] = {}
    for entrada in entradas:
        if entrada.instance in vistos:
            msg = (
                f"{root.name}: la instancia {entrada.instance!r} aparece en "
                f"{vistos[entrada.instance]} y en {entrada.file_name} — el "
                "nombre de instancia es la llave del catálogo"
            )
            raise CorpusError(msg)
        vistos[entrada.instance] = entrada.file_name

    return entradas
