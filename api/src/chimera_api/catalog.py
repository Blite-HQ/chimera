"""
Catálogo de datasets — qué datos publica este despliegue (O4/M10).

Tres rutas de lectura pura, sin estado y sin efectos:

| ruta                              | qué responde                              |
| --------------------------------- | ----------------------------------------- |
| `GET /datasets`                   | los datasets declarados, con su licencia   |
| `GET /datasets/{id}`              | las instancias de uno, con sus tres digests |
| `GET /datasets/{id}/croissant`    | el mismo dataset en Croissant (MLCommons)  |

**Nada de esto sabe de qué tratan los datos.** La plataforma no trae datasets:
un despliegue los DECLARA en su `distribution.yaml` (`DatasetSpec`), con ruta,
descripción, licencia y URL. Cambiar de dominio —de una red a una cadena de
espines a una tabla— es editar configuración, no tocar este archivo. Es la
misma forma que C-12 usó para los servidores MCP, y por el mismo motivo:
ADR-029 se sostiene por construcción, no por vigilancia.

**Fail-closed, con el error del lado correcto.** Un dataset declarado cuyo
directorio no existe, o cuyo digest embebido dejó de cuadrar, responde 500 y no
un catálogo a medias: es un defecto del despliegue, no una petición inválida.
Un `dataset_id` que nadie declaró responde 404. La diferencia importa para
quien opera: 404 es «no existe», 500 es «existe y está roto».
"""

# pyright: reportUnusedFunction=false
# ^ Mismo motivo que en `reads.py`: los handlers se registran por decorador.

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from blite.catalog.corpus import CorpusError, InstanceEntry, load_corpus
from blite.catalog.croissant import build_croissant
from blite.runtime.distribution import DatasetSpec, DistributionManifest


class DatasetSummary(BaseModel):
    """Una fila de `GET /datasets`."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    dataset_id: str
    title: str
    description: str
    license: str
    url: str
    version: str
    instance_count: int


class InstanceSummary(BaseModel):
    """Una instancia, con los tres digests etiquetados por disciplina (C-13)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    instance: str
    file: str
    file_sha256: str
    embedded_digest: str
    canonical_digest: str
    identity: dict[str, str]


class DatasetDetail(BaseModel):
    """`GET /datasets/{dataset_id}`."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    dataset_id: str
    title: str
    description: str
    license: str
    url: str
    version: str
    instances: tuple[InstanceSummary, ...]


def _to_summary(entry: InstanceEntry) -> InstanceSummary:
    return InstanceSummary(
        instance=entry.instance,
        file=entry.file_name,
        file_sha256=entry.file_sha256,
        embedded_digest=entry.embedded_digest,
        canonical_digest=entry.canonical_digest,
        identity=dict(entry.identity),
    )


def create_catalog_router(manifest: DistributionManifest, repo_root: Path) -> APIRouter:
    """El router del catálogo, sobre lo que el despliegue declaró.

    `repo_root` entra inyectada y no se deduce acá: la ruta de un dataset es
    relativa a la raíz del despliegue, y un módulo que la adivine con
    `__file__` se rompe en cuanto la imagen del contenedor cambia de layout.
    """
    router = APIRouter()

    def _spec(dataset_id: str) -> DatasetSpec:
        spec = manifest.datasets.get(dataset_id)
        if spec is None:
            raise HTTPException(status_code=404, detail="dataset desconocido")
        return spec

    def _instances(dataset_id: str, spec: DatasetSpec) -> tuple[InstanceEntry, ...]:
        try:
            return load_corpus(repo_root / spec.path)
        except CorpusError as exc:
            # 500, no 404: el despliegue declaró este dataset y no puede
            # entregarlo. Quien pidió no hizo nada mal.
            raise HTTPException(
                status_code=500,
                detail=f"dataset {dataset_id!r} declarado pero ilegible: {exc}",
            ) from exc

    @router.get("/datasets")
    def list_datasets() -> tuple[DatasetSummary, ...]:
        return tuple(
            DatasetSummary(
                dataset_id=dataset_id,
                title=spec.title or dataset_id,
                description=spec.description,
                license=spec.license,
                url=spec.url,
                version=spec.version,
                instance_count=len(_instances(dataset_id, spec)),
            )
            for dataset_id, spec in sorted(manifest.datasets.items())
        )

    @router.get("/datasets/{dataset_id}")
    def get_dataset(dataset_id: str) -> DatasetDetail:
        spec = _spec(dataset_id)
        return DatasetDetail(
            dataset_id=dataset_id,
            title=spec.title or dataset_id,
            description=spec.description,
            license=spec.license,
            url=spec.url,
            version=spec.version,
            instances=tuple(
                _to_summary(entry) for entry in _instances(dataset_id, spec)
            ),
        )

    @router.get("/datasets/{dataset_id}/croissant")
    def get_croissant(dataset_id: str) -> dict[str, Any]:
        """El dataset en Croissant 1.0 — JSON-LD, tal como sale del builder.

        Sin modelo pydantic de por medio a propósito: un `extra="forbid"`
        sobre JSON-LD arbitrario recortaría el documento, y lo que se publica
        tiene que ser exactamente lo que el validador de MLCommons acepta.
        """
        spec = _spec(dataset_id)
        return build_croissant(
            spec.description_for_export(dataset_id),
            _instances(dataset_id, spec),
        )

    return router
