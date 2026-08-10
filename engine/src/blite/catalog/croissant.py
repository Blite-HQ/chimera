"""
Export Croissant (MLCommons) de un dataset del catálogo — función pura.

Croissant es el formato de metadatos de datasets de MLCommons: JSON-LD sobre
schema.org, que es lo que leen las herramientas de ML para descubrir, verificar
y cargar un dataset sin que nadie escriba un parser a medida. Publicar en él es
lo que convierte «tenemos un corpus» en «cualquiera puede usar nuestro corpus».

**Lo que resuelve C-13.** Croissant tiene UNA propiedad `sha256` por archivo, y
significa exactamente una cosa: el digest de los bytes distribuidos. Nuestros
digests internos NO son eso. Meter el interno en `sha256` haría que la
verificación estándar (`sha256sum`) fallara en todo el mundo, y meter solo el de
bytes tiraría la identidad del corpus. Por eso:

* `sha256` de cada `cr:FileObject` = los bytes. Literal, como manda el spec.
* un `cr:RecordSet` llamado `instances` publica los TRES digests etiquetados,
  como datos inline — legible por máquina, sin prosa que interpretar.

Ninguno se recalcula para que cuadre con el otro: son disciplinas distintas
sobre el mismo documento y las tres son correctas a la vez.

**Un `cr:FileObject` por instancia, sin archivo comprimido.** La alternativa
idiomática (un archivo `.zip` + un `cr:FileSet`) exigiría publicar el `sha256`
de un archivo que no existe. Un digest inventado en el campo que el spec reserva
para verificar es peor que un export menos elegante.

Verificado contra el validador real de `mlcroissant` — ver
`tests/integration/test_croissant_export.py`.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from blite.catalog.corpus import InstanceEntry

CROISSANT_CONFORMS_TO = "http://mlcommons.org/croissant/1.0"

BLITE_NAMESPACE = "https://blite.dev/croissant/v1#"
"""Namespace propio para lo que Croissant no vocabulariza. Declarado en el
`@context`: un consumidor que no lo entienda lo ignora, en vez de tropezar."""

_ENCODING = "application/json"

DIGEST_DISCIPLINES: tuple[tuple[str, str], ...] = (
    (
        "file_sha256",
        "SHA-256 of the distributed file bytes. This is what `sha256sum` "
        "reports and what the `sha256` property of each FileObject repeats. "
        "Changes with line endings and whitespace.",
    ),
    (
        "embedded_digest",
        "SHA-256 of the compact JSON serialisation of the document with its "
        "own `digest` key removed (sorted keys, no spaces, ASCII-escaped). "
        "This is the corpus identity and it is immutable: it is verified on "
        "read and never rewritten.",
    ),
    (
        "canonical_digest",
        "SHA-256 of the canonical form C(document) used by this platform's "
        "trust kernel, over the WHOLE document including its `digest` key. "
        "Differs from the embedded digest by construction, not by mistake.",
    ),
)
"""Las tres disciplinas, con la explicación que viaja EN el export. Un tercero
no debería tener que leer nuestro repo para saber cuál es cuál."""

_CONTEXT: dict[str, Any] = {
    "@language": "en",
    "@vocab": "https://schema.org/",
    "citeAs": "cr:citeAs",
    "column": "cr:column",
    "conformsTo": "dct:conformsTo",
    "cr": "http://mlcommons.org/croissant/",
    "data": {"@id": "cr:data", "@type": "@json"},
    "dataType": {"@id": "cr:dataType", "@type": "@vocab"},
    "dct": "http://purl.org/dc/terms/",
    "equivalentProperty": "cr:equivalentProperty",
    "examples": {"@id": "cr:examples", "@type": "@json"},
    "extract": "cr:extract",
    "field": "cr:field",
    "fileProperty": "cr:fileProperty",
    "fileObject": "cr:fileObject",
    "fileSet": "cr:fileSet",
    "format": "cr:format",
    "includes": "cr:includes",
    "isLiveDataset": "cr:isLiveDataset",
    "jsonPath": "cr:jsonPath",
    "key": "cr:key",
    "md5": "cr:md5",
    "parentField": "cr:parentField",
    "path": "cr:path",
    "rai": "http://mlcommons.org/croissant/RAI/",
    "recordSet": "cr:recordSet",
    "references": "cr:references",
    "regex": "cr:regex",
    "repeated": "cr:repeated",
    "replace": "cr:replace",
    "samplingRate": "cr:samplingRate",
    "sc": "https://schema.org/",
    "separator": "cr:separator",
    "source": "cr:source",
    "subField": "cr:subField",
    "transform": "cr:transform",
    "blite": BLITE_NAMESPACE,
}
"""El `@context` de Croissant 1.0 tal cual, más nuestro namespace. Se copia
completo a propósito: el validador compara el conjunto de llaves y avisa de
cualquier desviación, así que recortarlo «porque no usamos esas» produce un
export que el ecosistema marca como no estándar."""


@dataclass(frozen=True)
class DatasetDescription:
    """Lo que un despliegue dice de su dataset. Metadatos, no dominio."""

    dataset_id: str
    name: str
    description: str
    license: str
    url: str
    version: str = "1.0.0"
    cite_as: str = ""
    date_published: str = ""


def _field(field_id: str, name: str, description: str) -> dict[str, Any]:
    return {
        "@type": "cr:Field",
        "@id": field_id,
        "name": name,
        "description": description,
        "dataType": "sc:Text",
    }


def _common_identity_keys(instances: Sequence[InstanceEntry]) -> tuple[str, ...]:
    """Solo las llaves de identidad que TODAS las instancias traen.

    Una columna que existe para la mitad del corpus obligaría a rellenar la
    otra mitad con vacío, y un `procedencia: ""` publicado se lee como «sin
    procedencia» cuando en realidad es «este corpus no lo declara».
    """
    if not instances:
        return ()
    comunes = set(instances[0].identity)
    for entry in instances[1:]:
        comunes &= set(entry.identity)
    return tuple(sorted(comunes))


def build_croissant(
    description: DatasetDescription, instances: Sequence[InstanceEntry]
) -> dict[str, Any]:
    """El documento Croissant del dataset. Sin I/O: entra catálogo, sale JSON-LD."""
    distribution = [
        {
            "@type": "cr:FileObject",
            "@id": entry.file_name,
            "name": entry.file_name,
            "description": f"Instance {entry.instance}.",
            "contentUrl": entry.file_name,
            "encodingFormat": _ENCODING,
            "sha256": entry.file_sha256,
        }
        for entry in instances
    ]

    identity_keys = _common_identity_keys(instances)
    fields = [
        _field("instances/instance", "instance", "Name of the instance."),
        _field("instances/file", "file", "File that carries the instance."),
        *(
            _field(f"instances/{name}", name, texto)
            for name, texto in DIGEST_DISCIPLINES
        ),
        *(
            _field(
                f"instances/{key}",
                key,
                f"Identity key `{key}` as declared by the dataset itself.",
            )
            for key in identity_keys
        ),
    ]

    data = [
        {
            "instances/instance": entry.instance,
            "instances/file": entry.file_name,
            "instances/file_sha256": entry.file_sha256,
            "instances/embedded_digest": entry.embedded_digest,
            "instances/canonical_digest": entry.canonical_digest,
            **{f"instances/{key}": entry.identity[key] for key in identity_keys},
        }
        for entry in instances
    ]

    document: dict[str, Any] = {
        "@context": _CONTEXT,
        "@type": "sc:Dataset",
        "@id": description.dataset_id,
        "name": description.dataset_id,
        "description": description.description,
        "conformsTo": CROISSANT_CONFORMS_TO,
        "license": description.license,
        "url": description.url,
        "version": description.version,
        "distribution": distribution,
        "recordSet": [
            {
                "@type": "cr:RecordSet",
                "@id": "instances",
                "name": "instances",
                "description": (
                    "One record per instance: its identity and its three "
                    "digests, each under the discipline that produced it."
                ),
                "key": {"@id": "instances/instance"},
                "field": fields,
                "data": data,
            }
        ],
    }
    if description.name and description.name != description.dataset_id:
        # `name` en Croissant es el identificador (sin espacios); el título
        # legible va en `alternateName`, que es donde schema.org lo espera.
        document["alternateName"] = description.name
    if description.cite_as:
        document["citeAs"] = description.cite_as
    if description.date_published:
        document["datePublished"] = description.date_published
    return document
