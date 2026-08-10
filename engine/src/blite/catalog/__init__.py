"""Catálogo de datasets — qué datos tiene un despliegue, y cómo se identifican.

Dos piezas, deliberadamente separadas:

* `corpus` — lee un directorio de instancias y calcula sus digests. Toca disco.
* `croissant` — convierte eso en un documento Croissant. Función pura.

Ninguna de las dos sabe de qué trata el dato. Un dataset es un directorio de
documentos JSON con un nombre de instancia y un digest embebido; qué haya
dentro —una red, una cadena de espines, una tabla— es asunto del despliegue que
lo declara, no de este código (ADR-029).
"""

from blite.catalog.corpus import (
    CorpusError,
    InstanceEntry,
    embedded_digest,
    load_corpus,
)
from blite.catalog.croissant import (
    CROISSANT_CONFORMS_TO,
    DIGEST_DISCIPLINES,
    build_croissant,
)

__all__ = [
    "CROISSANT_CONFORMS_TO",
    "DIGEST_DISCIPLINES",
    "CorpusError",
    "InstanceEntry",
    "build_croissant",
    "embedded_digest",
    "load_corpus",
]
