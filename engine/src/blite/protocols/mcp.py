"""
Adapter de salida MCP — el transporte hacia un servidor de terceros.

Vive en `blite.protocols` porque **esto es EGRESO**: sale del proceso, habla un
protocolo ajeno y ejecuta código que no es nuestro. `protocols` es la capa que
el contrato de layers pone por encima de `authz` (INV-6) precisamente para eso;
`runtime` no hace egreso y por eso el `ServiceStrategy` recibe este invocador
inyectado en vez de importarlo.

**Fail-closed, en este orden y por esta razón:**

1. ¿El servidor está en la allowlist del despliegue? Si no: no se resuelve.
2. ¿El tool está en la allowlist DE ESE SERVIDOR? Un servidor MCP puede añadir
   tools entre versiones — heredar permiso por pertenecer al servidor sería
   aceptar superficie que nadie revisó.
3. Recién entonces se levanta el proceso, con el comando y el PIN que declara
   el manifest. Ni el comando ni la versión salen jamás del claim: eso sería
   ejecución arbitraria disfrazada de invocación de capability.

**El proceso ajeno NO hereda nuestro entorno.** Se le arma uno mínimo y
explícito: `PATH`, un `HOME` temporal propio, y las variables del gestor de
paquetes si el comando lo necesita. Heredar el entorno del api le entregaría a
un binario de terceros la contraseña de la base, la key del modelo y todo lo
demás que viva ahí — por conveniencia. Un `HOME` propio además es lo que muchos
servidores MCP necesitan de verdad (escriben su config al arrancar) y es la
razón por la que un contenedor endurecido con `--no-create-home` los rompe.

Lo que este módulo NO hace: decidir si el egreso está permitido. Eso es de
`authz` (Inv-E). Acá se aplica lo que el despliegue declaró.
"""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
from dataclasses import dataclass
from typing import Any, cast

from blite.runtime.distribution import DistributionManifest, McpServerSpec

_DEFAULT_TIMEOUT_S = 60.0

_MAX_GROUP_DEPTH = 8
"""Tope de desanidado: un `ExceptionGroup` puede contener otro, y una espera
`while` sobre estructura ajena es un cuelgue esperando ocurrir."""

_ENV_PREFIXES_PASSTHROUGH = ("UV_",)
"""Únicas variables del entorno del api que cruzan al proceso ajeno: las del
gestor de paquetes, que el propio `command` necesita para resolver su pin. Todo
lo demás —credenciales incluidas— se queda de este lado."""


def build_child_env(home: str) -> dict[str, str]:
    """El entorno EXPLÍCITO del proceso de terceros.

    Lista blanca, no lista negra: una denylist de secretos se queda corta el día
    que alguien agrega una variable nueva, y el modo de falla es entregarla.
    """
    env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": home,
    }
    env.update(
        {
            key: value
            for key, value in os.environ.items()
            if key.startswith(_ENV_PREFIXES_PASSTHROUGH)
        }
    )
    return env


class McpInvocationRefusedError(Exception):
    """El despliegue no declara esta invocación. No es un fallo del tool."""


class McpTransportError(Exception):
    """El round-trip falló. Es un error de PROCESO, jamás un veredicto."""


@dataclass(frozen=True)
class McpCallResult:
    """Lo que volvió del tercero, más de dónde vino."""

    server_id: str
    tool: str
    content: tuple[dict[str, Any], ...]
    is_error: bool
    server_name: str
    server_version: str
    package_pin: str


def _resolve(
    manifest: DistributionManifest, server_id: str, tool: str
) -> McpServerSpec:
    spec = manifest.server(server_id)
    if spec is None:
        msg = (
            f"servidor MCP {server_id!r} no declarado por este despliegue — "
            "la allowlist es la superficie, no una sugerencia"
        )
        raise McpInvocationRefusedError(msg)
    if not manifest.is_tool_allowed(server_id, tool):
        msg = (
            f"tool {tool!r} no está en la allowlist de {server_id!r} "
            f"(permitidos: {', '.join(spec.tools) or 'ninguno'})"
        )
        raise McpInvocationRefusedError(msg)
    return spec


async def _round_trip(
    spec: McpServerSpec, tool: str, arguments: dict[str, Any], timeout_s: float
) -> tuple[tuple[dict[str, Any], ...], bool, str, str]:
    # Import perezoso: el SDK de MCP solo se necesita cuando el despliegue
    # declara un servidor externo, y arrastrarlo siempre encarecería la imagen
    # de todo despliegue que no use ninguno.
    from mcp import ClientSession, StdioServerParameters  # noqa: PLC0415
    from mcp.client.stdio import stdio_client  # noqa: PLC0415

    if spec.transport != "stdio":
        msg = f"transporte {spec.transport!r} sin adapter todavía — jamás un fallback"
        raise McpTransportError(msg)

    with tempfile.TemporaryDirectory(prefix="chimera-mcp-home-") as home:
        params = StdioServerParameters(
            command=spec.command, args=list(spec.args), env=build_child_env(home)
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                init = await asyncio.wait_for(session.initialize(), timeout=timeout_s)
                result = await asyncio.wait_for(
                    session.call_tool(tool, arguments), timeout=timeout_s
                )

    blocks: tuple[dict[str, Any], ...] = tuple(
        json.loads(block.model_dump_json()) for block in result.content
    )
    return (
        blocks,
        bool(result.is_error),
        init.server_info.name,
        init.server_info.version,
    )


def _unwrap_group(exc: BaseException) -> BaseException:
    """Saca el fallo REAL de dentro de un `ExceptionGroup` de `anyio`.

    Su mensaje es «unhandled errors in a TaskGroup» y no dice nada: un error
    opaco es indistinguible de un fallo silencioso, que es justo lo que este
    repo no acepta en ninguna frontera.
    """
    actual: BaseException = exc
    for _ in range(_MAX_GROUP_DEPTH):
        if not isinstance(actual, BaseExceptionGroup):
            break
        inner = cast("tuple[BaseException, ...]", actual.exceptions)
        if not inner:
            break
        actual = inner[0]
    return cast("BaseException", actual)


def invoke_mcp_tool(
    manifest: DistributionManifest,
    inputs: dict[str, Any],
    *,
    timeout_s: float = _DEFAULT_TIMEOUT_S,
) -> McpCallResult:
    """Invoca un tool ajeno, si el despliegue lo declaró."""
    server_id = str(inputs.get("server", ""))
    tool = str(inputs.get("tool", ""))
    raw_arguments: object = inputs.get("arguments") or {}
    if not isinstance(raw_arguments, dict):
        msg = "`arguments` debe ser un objeto"
        raise McpInvocationRefusedError(msg)
    arguments = cast("dict[str, Any]", raw_arguments)

    spec = _resolve(manifest, server_id, tool)

    try:
        blocks, is_error, name, version = asyncio.run(
            _round_trip(spec, tool, arguments, timeout_s)
        )
    except McpTransportError:
        raise
    except Exception as exc:  # noqa: BLE001 — se traduce a error de PROCESO
        # `anyio` envuelve el fallo real en un ExceptionGroup cuyo mensaje es
        # «unhandled errors in a TaskGroup» y no dice NADA. Se desenvuelve: un
        # error opaco es indistinguible de un fallo silencioso.
        causa = _unwrap_group(exc)
        msg = (
            f"round-trip MCP contra {server_id!r} falló: "
            f"{type(causa).__name__}: {causa}"
        )
        raise McpTransportError(msg) from exc

    return McpCallResult(
        server_id=server_id,
        tool=tool,
        content=blocks,
        is_error=is_error,
        server_name=name,
        server_version=version,
        package_pin=spec.package_pin,
    )
