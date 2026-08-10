"""
McpToolInvoker — UN manifest genérico para CUALQUIER tool MCP ajeno (C-12).

La resolución C-12 dice la parte difícil: los manifests de terceros NO son
`CapabilityManifest` de primera clase. Si cada tool ajeno se registrara como
capability propia, su vocabulario —«nexus», «job», lo que sea— entraría a un
manifest nuestro y ADR-029 se caería el primer día. Acá hay UNA capability, y
el vocabulario del tercero vive como DATO de configuración con digest en el
`DistributionManifest`.

Consecuencia que vale la pena decir en voz alta: **registrar un servidor MCP
nuevo no agrega vocabulario de escenario a ningún manifest, porque no agrega
ningún manifest.**
"""

from __future__ import annotations

from typing import Any

from blite_capability.manifest import CapabilityManifest

_MANIFEST = CapabilityManifest(
    id="blite.mcp.invoke_tool",
    description=(
        "Invoke a named tool on an external MCP server and return its result."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "server": {
                "type": "string",
                "description": "Identifier of an external server declared by the deployment",
            },
            "tool": {
                "type": "string",
                "description": "Name of the tool to invoke on that server",
            },
            "arguments": {
                "type": "object",
                "description": "Arguments forwarded to the tool, opaque to this capability",
            },
        },
        "required": ["server", "tool"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "content": {
                "type": "array",
                "description": "Result blocks returned by the tool",
            },
            "is_error": {"type": "boolean"},
            "import_attestation": {
                "type": "object",
                "description": "in-toto Statement certifying WHAT was imported and from where",
            },
        },
        "required": ["content", "is_error"],
    },
    tags=("interop", "external", "adapter"),
    side_effects="irreversible-external",
    required_permission="capability:invoke:mcp",
    interaction="request_response",
    execution_profile="service",
    version="0.1.0",
)


class McpToolInvoker:
    """La capability. No ejecuta nada: declara.

    El transporte vive en `blite.protocols.mcp` (el egreso pertenece a
    `protocols`, gobernado por authz — INV-6/Inv-E) y el dispatcher lo alcanza
    por `ServiceStrategy`. Una capability que levantara el proceso de un tercero
    desde dentro del engine sería justo la mediación que AX3 existe para evitar.
    """

    @property
    def manifest(self) -> CapabilityManifest:
        return _MANIFEST

    def invoke(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """SIEMPRE levanta — y eso es lo correcto, no una limitación.

        `execution_profile: service` significa que esta capability no corre en
        este proceso. Si el despacho llegara acá, algo resolvió mal el perfil, y
        un fallback silencioso a in-process ejecutaría un tool ajeno saltándose
        la allowlist, el pin y la attestation. Explota, fuerte.
        """
        msg = (
            "blite.mcp.invoke_tool no corre in-process (execution_profile: "
            "service). Si llegaste acá, el dispatcher resolvió mal el perfil — "
            "jamás un fallback silencioso: sin la ruta de servicio no hay "
            "allowlist, ni pin, ni attestation de importación."
        )
        raise NotImplementedError(msg)
