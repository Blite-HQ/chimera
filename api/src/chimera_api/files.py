"""
Archivos del proyecto — `POST /files`, `GET /files`, `GET /files/{digest}`
(P10/M24). [E · P-ui]

**Un archivo subido no es evidencia.** El freeze §7 es explícito: contenido
recuperado entra como `assumptions` con su `ref{name, digest}`, jamás como
`Attestation` ni dentro de `conclusions`. Estas rutas no prometen más que eso
— guardan bytes, los nombran por su digest y los devuelven idénticos. Quien
quiera citar un paper en un certificado usa ese digest; el peso probatorio lo
sigue poniendo un verificador, no el hecho de que alguien haya subido un PDF.

**Por qué el cuerpo es crudo y no multipart:** `UploadFile` exige
`python-multipart`, una dependencia más para transportar exactamente los
mismos bytes. El nombre viaja en `X-Filename` y el tipo en `Content-Type`, que
es donde HTTP ya los pone. Menos superficie, mismo resultado.
"""

# pyright: reportUnusedFunction=false
# ^ Los handlers de FastAPI se registran por DECORADOR, no por llamada.

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response

from blite.content_fs import FileContext, FilesystemContentStore
from chimera_api.auth import SessionAuth

_DEFAULT_MEDIA_TYPE = "application/octet-stream"

_MEDIA_TYPES_ACTIVOS = frozenset(
    {
        "text/html",
        "application/xhtml+xml",
        "image/svg+xml",
        "text/xml",
        "application/xml",
        "application/javascript",
        "text/javascript",
    }
)
"""Tipos que un navegador EJECUTA. `/files` se proxea en el MISMO origen que el
Studio (`docker/studio-nginx.conf`), así que servir un `text/html` subido lo
haría correr con la cookie de sesión del usuario adjunta: podría crear runs o
responder approvals en su nombre. Que la cookie sea HttpOnly no ayuda — el
navegador la manda sola. Estos tipos se sirven neutralizados."""
_FILES_DIR_ENV = "CHIMERA_FILES_DIR"
_DEFAULT_FILES_DIR = "/app/var/files"
"""Default del contenedor. En compose es un volumen: sin él los archivos del
proyecto morirían con cada `docker compose up --build`, que es justo lo que un
almacén direccionado por contenido no debe hacer."""


def files_dir() -> Path:
    return Path(os.environ.get(_FILES_DIR_ENV, _DEFAULT_FILES_DIR))


def _nombre_seguro(nombre: str) -> str:
    """El nombre llega en un header del cliente y vuelve en otro header: un
    CRLF ahí dentro partiría la respuesta en dos (header injection), y una
    comilla escaparía del `filename="..."`. Se conserva solo lo imprimible y
    sin comillas — el nombre es comodidad, la identidad es el digest."""
    limpio = "".join(c for c in nombre if c.isprintable() and c not in '"\\')
    return limpio[:_MAX_FILENAME] or "descarga"


_MAX_FILENAME = 200


def create_files_router(session_auth: SessionAuth) -> APIRouter:
    """Router de archivos sobre el adapter DURABLE del puerto `ContentStore`.

    Store propio, no `resources.content`: ese es el almacén de EVIDENCIA de los
    runs y hoy es `InMemoryContentStore`. Migrarlo al adapter durable es un
    cambio del plano de confianza (la evidencia dejaría de evaporarse al
    reiniciar) y merece su propia decisión — no entra de contrabando en una
    feature de producto. Ambos hablan el mismo puerto, así que unificarlos
    después no toca a ningún consumidor."""
    router = APIRouter()
    store = FilesystemContentStore(root=files_dir())

    def _ctx(request: Request) -> FileContext:
        """SO2 — el dominio sale de la IDENTIDAD del que pregunta, no de una
        constante de arranque: es lo único que hace real la partición por
        dominio cuando haya más de uno."""
        return FileContext(domain_id=session_auth.identity_from(request).domain_id)

    def _fila(digest: str, ctx: FileContext) -> dict[str, Any]:
        artifact = store.stat(digest, ctx)
        if artifact is None:
            raise HTTPException(status_code=404, detail="archivo desconocido")
        return {
            "digest": artifact.digest,
            "filename": store.filename(digest, ctx),
            "media_type": artifact.media_type,
            "size_bytes": artifact.size_bytes,
            "created_at": artifact.created_at.isoformat(),
        }

    @router.post("/files", status_code=201)
    async def upload_file(request: Request) -> dict[str, Any]:
        """201 con la fila del archivo. Idempotente por contenido: subir dos
        veces el mismo PDF devuelve el mismo digest y no crea una segunda
        entrada (O3 — el contenido define su identidad)."""
        ctx = _ctx(request)
        data = await request.body()
        if not data:
            raise HTTPException(
                status_code=422,
                detail="el cuerpo está vacío — un archivo de cero bytes no es un archivo",
            )
        media_type = request.headers.get("content-type") or _DEFAULT_MEDIA_TYPE
        filename = request.headers.get("x-filename")
        artifact = store.put(
            data,
            media_type,
            ctx,
            **({"filename": filename} if filename else {}),
        )
        return _fila(artifact.digest, ctx)

    @router.get("/files")
    def list_files(request: Request) -> list[dict[str, Any]]:
        """Los archivos del dominio, más recientes primero. `[]` es la
        respuesta honesta de un proyecto sin archivos, no un 404."""
        ctx = _ctx(request)
        return [_fila(artifact.digest, ctx) for artifact in store.list(ctx)]

    @router.get("/files/{digest}")
    def download_file(digest: str, request: Request) -> Response:
        """Los bytes exactos. Un digest desconocido —o malformado— es 404: no
        hay diferencia observable entre «no existe» y «no es un digest», y
        distinguirlos solo le contaría al que prueba cómo está guardado."""
        ctx = _ctx(request)
        try:
            data = store.get(digest, ctx)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="archivo desconocido") from exc
        artifact = store.stat(digest, ctx)
        declarado = artifact.media_type if artifact is not None else _DEFAULT_MEDIA_TYPE
        # Tres capas, ninguna sobra: el tipo activo se neutraliza en el origen,
        # `attachment` impide el render aunque el tipo pasara, y `nosniff`
        # impide que el navegador adivine HTML de un octet-stream.
        media_type = (
            _DEFAULT_MEDIA_TYPE
            if declarado.split(";")[0].strip().lower() in _MEDIA_TYPES_ACTIVOS
            else declarado
        )
        nombre = store.filename(digest, ctx) or digest
        return Response(
            content=data,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{_nombre_seguro(nombre)}"',
                "X-Content-Type-Options": "nosniff",
            },
        )

    return router


__all__ = ["create_files_router", "files_dir"]
