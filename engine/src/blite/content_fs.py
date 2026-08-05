"""
Adapter de `ContentStore` sobre disco (P10/M24) — freeze §12.

El puerto estaba congelado y sin adapter: `put()` existía en la letra y en
ninguna parte del código, así que no había dónde poner un archivo del proyecto
(Papers/M24 mostraba honest-empty por eso, no por diseño de UI).

Dos propiedades del puerto se implementan literal, no aproximadas:

- **El contenido define su identidad** (O3/L3). El digest ES la dirección: el
  mismo archivo subido dos veces produce UN artifact. Por eso el nombre del
  archivo no participa del direccionamiento — viaja al lado, como metadato
  legible por humanos, y dos nombres distintos del mismo contenido no lo
  duplican.
- **SO2: partición por dominio.** Un digest es visible solo dentro de su
  dominio salvo Channel con `read`. Se implementa con un directorio por
  dominio: la deduplicación física entre dominios sería una optimización
  interna y jamás un canal de visibilidad, así que acá no se deduplica cruzado.

Qué NO es esto: la tabla `artifacts` del esquema v2 sigue siendo el índice
relacional canónico. Este adapter guarda los bytes y su metadata en disco
porque es lo que un despliegue single-node necesita hoy; un adapter respaldado
por Postgres (o S3) implementa el MISMO puerto sin tocar a sus consumidores —
que es exactamente para lo que el puerto existe.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from blite.content import Artifact

_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
"""Un digest es 64 hex y nada más. Este patrón es también la defensa contra
path traversal: el digest llega desde una URL, y `../../etc/passwd` jamás
llega a tocar el disco porque no matchea."""

_METADATA_SUFFIX = ".meta.json"


@dataclass(frozen=True)
class FileContext:
    """El contexto mínimo que el puerto pide: quién pregunta, en qué dominio.

    El tipo concreto lo fija el gateway (freeze §8); este es el que usan las
    rutas de archivos mientras el cruce completo (C2/M2) no las envuelva."""

    domain_id: str


class FilesystemContentStore:
    """`ContentStore` sobre un directorio. Un subdirectorio por dominio."""

    def __init__(self, root: Path) -> None:
        self._root = root

    def put(
        self,
        data: bytes,
        media_type: str,
        ctx: object,
        *,
        filename: str | None = None,
    ) -> Artifact:
        """Escribe y devuelve el Artifact — el digest ES la identidad (O3)."""
        domain_id = _domain_of(ctx)
        digest = hashlib.sha256(data).hexdigest()
        directorio = self._domain_dir(domain_id)
        directorio.mkdir(parents=True, exist_ok=True)

        blob = directorio / digest
        artifact = Artifact(
            digest=digest,
            domain_id=domain_id,
            media_type=media_type,
            size_bytes=len(data),
            storage_ref=str(blob),
            created_at=datetime.now(UTC),
        )

        # Idempotencia por construcción: el mismo contenido reescribe los
        # mismos bytes. Se conserva el `created_at` original — la primera vez
        # que entró al proyecto es un dato, no un detalle de implementación.
        if blob.exists():
            existente = self._read_metadata(directorio, digest)
            if existente is not None:
                return existente

        blob.write_bytes(data)
        self._write_metadata(directorio, artifact, filename)
        return artifact

    def get(self, digest: str, ctx: object) -> bytes:
        """Bytes exactos, o falla fuerte — devolver vacío inventaría contenido."""
        blob = self._blob_path(digest, _domain_of(ctx))
        if blob is None or not blob.is_file():
            raise KeyError(f"artifact {digest!r} no visible en este dominio")
        return blob.read_bytes()

    def stat(self, digest: str, ctx: object) -> Artifact | None:
        """Metadata sin bytes; None si no es visible en el dominio del ctx."""
        domain_id = _domain_of(ctx)
        if self._blob_path(digest, domain_id) is None:
            return None
        return self._read_metadata(self._domain_dir(domain_id), digest)

    def list(self, ctx: object) -> tuple[Artifact, ...]:
        """Los artifacts del dominio, más recientes primero.

        Extensión sobre el puerto (que no declara `list`): un listado es lo que
        una vista de archivos necesita, y derivarlo del directorio evita un
        índice paralelo que podría divergir de los bytes."""
        directorio = self._domain_dir(_domain_of(ctx))
        if not directorio.is_dir():
            return ()
        artifacts = [
            artifact
            for meta in directorio.glob(f"*{_METADATA_SUFFIX}")
            if (artifact := self._parse_metadata(meta)) is not None
        ]
        return tuple(sorted(artifacts, key=lambda a: a.created_at, reverse=True))

    def filename(self, digest: str, ctx: object) -> str | None:
        """El nombre con el que se subió, si se declaró. No es la identidad."""
        directorio = self._domain_dir(_domain_of(ctx))
        raw = self._read_raw_metadata(directorio, digest)
        nombre = raw.get("filename") if raw is not None else None
        return nombre if isinstance(nombre, str) else None

    # ── interno ──────────────────────────────────────────────────────────────

    def _domain_dir(self, domain_id: str) -> Path:
        # El domain_id también llega de afuera: se sanitiza igual que el digest.
        seguro = re.sub(r"[^a-zA-Z0-9._-]", "_", domain_id)
        return self._root / seguro

    def _blob_path(self, digest: str, domain_id: str) -> Path | None:
        if not _DIGEST_PATTERN.match(digest):
            return None
        blob = self._domain_dir(domain_id) / digest
        return blob if blob.is_file() else None

    def _metadata_path(self, directorio: Path, digest: str) -> Path:
        return directorio / f"{digest}{_METADATA_SUFFIX}"

    def _write_metadata(
        self, directorio: Path, artifact: Artifact, filename: str | None
    ) -> None:
        payload = artifact.model_dump(mode="json")
        if filename is not None:
            payload["filename"] = filename
        self._metadata_path(directorio, artifact.digest).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def _read_raw_metadata(
        self, directorio: Path, digest: str
    ) -> dict[str, object] | None:
        if not _DIGEST_PATTERN.match(digest):
            return None
        ruta = self._metadata_path(directorio, digest)
        if not ruta.is_file():
            return None
        return _leer_json_objeto(ruta)

    def _read_metadata(self, directorio: Path, digest: str) -> Artifact | None:
        raw = self._read_raw_metadata(directorio, digest)
        return None if raw is None else _to_artifact(raw)

    def _parse_metadata(self, ruta: Path) -> Artifact | None:
        raw = _leer_json_objeto(ruta)
        return None if raw is None else _to_artifact(raw)


def _leer_json_objeto(ruta: Path) -> dict[str, object] | None:
    """El sidecar es un objeto JSON o no es nada — cualquier otra forma se
    ignora en vez de romper el listado entero por un archivo corrupto."""
    parsed: object = json.loads(ruta.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        return None
    # `json.loads` devuelve `Any`; el cast explícito es la frontera donde ese
    # `Any` se convierte en un tipo declarado. Las claves de un objeto JSON son
    # str por definición del formato.
    return cast("dict[str, object]", parsed)


def _to_artifact(raw: dict[str, object]) -> Artifact:
    """`extra="forbid"` del modelo obliga a soltar el `filename` del sidecar."""
    return Artifact.model_validate({k: v for k, v in raw.items() if k != "filename"})


def _domain_of(ctx: object) -> str:
    """El puerto deja el tipo del ctx al gateway; acá se exige que porte dominio.

    Sin dominio no hay visibilidad (SO2), así que un contexto que no lo trae es
    un error de programación, no un caso a degradar en silencio."""
    domain_id = getattr(ctx, "domain_id", None)
    if not isinstance(domain_id, str) or not domain_id:
        raise TypeError("el contexto de contenido debe portar un domain_id (SO2)")
    return domain_id


__all__ = ["FileContext", "FilesystemContentStore"]
