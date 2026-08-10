"""
Raíz de composición del cliente MCP (O5/M13, resolución C-12).

Acá se juntan las piezas que a propósito no se conocen entre sí:

| pieza                        | qué aporta                         | por qué no lo hace otro                     |
| ---------------------------- | ---------------------------------- | -------------------------------------------- |
| `blite.runtime.distribution` | la allowlist declarada + su digest | es configuración de despliegue, no egreso   |
| `blite.protocols.mcp`        | el round-trip                      | el egreso vive en `protocols` (INV-6)       |
| esta raíz                    | la attestation de importación      | **Inv-E prohíbe que `protocols` la construya** |

Esa última fila no es burocracia: Inv-E existe para que ninguna «verificación»
pueda justificar un egreso. Si el adapter de salida pudiera construir
attestations, la frontera sería una convención. Por eso el egreso devuelve un
resultado plano y es acá donde se le pone la attestation encima.

**Predicado propio, y por qué NO se reusa el de Nexus.** C-12 decía «reusa
evidencia-externa». No se puede sin mentir: `ExternalImportStatement` valida
llaves OBLIGATORIAS `circuit_digest` y `shots_requested` — es un import de job
CUÁNTICO con nombre genérico. Una llamada a un tool MCP no tiene circuito ni
shots, y rellenarlas sería fabricar campos para pasar un validador. Generalizar
ese modelo toca un contrato congelado ⇒ **ceremonia**, y una sesión de dominio
no la ejecuta sola: queda REPORTADA. Mientras tanto, este predicado propio
(`https://blite.dev/McpToolImport/v1`) es aditivo y no toca nada congelado; el
día de la ceremonia se fusionan.

**Qué certifica, y qué NO.** Certifica LA IMPORTACIÓN: que este despliegue
invocó ESTE tool, en ESTE servidor, con ESTE pin, bajo ESTA configuración
(digest del `DistributionManifest`), y que el resultado tiene ESTE digest. **No**
dice que el resultado sea correcto — eso sería una `Attestation` científica, y
un tool ajeno no es un ancla. Misma ortogonalidad que la evidencia de Nexus
(`docs/specs/evidencia-externa.md` §Ortogonalidad).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, ConfigDict

from blite.protocols.mcp import McpCallResult, invoke_mcp_tool
from blite.runtime.distribution import DistributionManifest

MCP_CAPABILITY_ID = "blite.mcp.invoke_tool"

PREDICATE_TYPE = "https://blite.dev/McpToolImport/v1"
STATEMENT_TYPE = "https://in-toto.io/Statement/v1"


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


class McpImportStatement(BaseModel):
    """in-toto Statement v1 de una invocación de tool ajeno."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    subject_name: str
    subject_digest: str
    builder_id: str
    """`mcp://<server>/<tool>` — quién produjo lo importado (C-12, literal)."""
    invocation_id: str
    external_parameters: dict[str, Any]
    resolved_dependencies: tuple[dict[str, Any], ...]

    def to_intoto(self) -> dict[str, Any]:
        return {
            "_type": STATEMENT_TYPE,
            "predicateType": PREDICATE_TYPE,
            "subject": [
                {"name": self.subject_name, "digest": {"sha256": self.subject_digest}}
            ],
            "predicate": {
                "builder": {"id": self.builder_id},
                "invocationId": self.invocation_id,
                "externalParameters": self.external_parameters,
                "resolvedDependencies": list(self.resolved_dependencies),
            },
        }


def build_import_statement(
    result: McpCallResult, *, manifest: DistributionManifest, arguments: dict[str, Any]
) -> McpImportStatement:
    content_digest = _digest([dict(block) for block in result.content])
    return McpImportStatement(
        subject_name=f"mcp:{result.server_id}/{result.tool}",
        subject_digest=content_digest,
        builder_id=f"mcp://{result.server_id}/{result.tool}",
        invocation_id=f"{result.server_id}:{result.tool}:{content_digest[:16]}",
        external_parameters={
            "server_id": result.server_id,
            "tool": result.tool,
            # Los argumentos viajan por DIGEST, no en claro: pueden llevar
            # cualquier cosa que el proponente haya puesto, y una attestation no
            # es lugar para contenido.
            "arguments_digest": _digest(arguments),
            "is_error": result.is_error,
        },
        resolved_dependencies=(
            {
                "name": "mcp-server-package",
                "digest": {"sha256": _digest(result.package_pin)},
                "pin": result.package_pin,
                # Lo que el servidor DICE ser, al lado del pin que le exigimos.
                # Si divergen, la attestation lo muestra en vez de esconderlo.
                "reported_name": result.server_name,
                "reported_version": result.server_version,
            },
            {
                "name": "distribution-manifest",
                "digest": {"sha256": manifest.digest()},
            },
        ),
    )


def build_mcp_invoker(
    manifest: DistributionManifest,
) -> Callable[[str, dict[str, Any]], dict[str, Any]]:
    """El invocador que `ServiceStrategy` recibe inyectado."""

    def invoke(capability_id: str, inputs: dict[str, Any]) -> dict[str, Any]:
        if capability_id != MCP_CAPABILITY_ID:
            msg = (
                f"ServiceStrategy recibió {capability_id!r}; este despliegue solo "
                f"tiene invocador de servicio para {MCP_CAPABILITY_ID!r}"
            )
            raise NotImplementedError(msg)

        arguments: dict[str, Any] = inputs.get("arguments") or {}
        result = invoke_mcp_tool(manifest, inputs)
        statement = build_import_statement(
            result, manifest=manifest, arguments=arguments
        )
        return {
            "content": [dict(block) for block in result.content],
            "is_error": result.is_error,
            "import_attestation": statement.to_intoto(),
        }

    return invoke
