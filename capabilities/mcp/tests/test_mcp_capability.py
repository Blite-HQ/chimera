"""El manifest genérico y la negativa a correr in-process (C-12)."""

from __future__ import annotations

import pytest

from blite_cap_mcp import McpToolInvoker


class TestManifestGenerico:
    def test_hay_una_sola_capability_para_todos_los_tools_ajenos(self) -> None:
        """C-12 en una línea: el vocabulario del tercero NO está acá.

        `server` y `tool` son PARÁMETROS de entrada, no ids de capability. Si
        cada tool ajeno fuera su propia capability, su vocabulario entraría a un
        manifest nuestro y ADR-029 se caería el primer día.
        """
        manifest = McpToolInvoker().manifest
        assert manifest.id == "blite.mcp.invoke_tool"
        assert set(manifest.input_schema["properties"]) == {
            "server",
            "tool",
            "arguments",
        }

    def test_el_perfil_es_service_no_in_process(self) -> None:
        assert McpToolInvoker().manifest.execution_profile == "service"

    def test_declara_el_peor_efecto_posible(self) -> None:
        """No sabemos qué hace el tool de un extraño.

        Asumir reversibilidad inventaría una garantía que no tenemos, y la regla
        de reintentos del freeze §13 LEE este campo — un default optimista haría
        que el runtime reintente algo irreversible.
        """
        assert McpToolInvoker().manifest.side_effects == "irreversible-external"

    def test_pide_permiso_propio(self) -> None:
        assert McpToolInvoker().manifest.required_permission == "capability:invoke:mcp"

    def test_la_salida_promete_la_attestation_de_importacion(self) -> None:
        props = McpToolInvoker().manifest.output_schema["properties"]
        assert "import_attestation" in props


class TestNoCorreInProcess:
    def test_invocarla_directo_explota_en_vez_de_ejecutar(self) -> None:
        """Un fallback silencioso a in-process ejecutaría un tool ajeno
        saltándose la allowlist, el pin y la attestation."""
        with pytest.raises(NotImplementedError, match="service"):
            McpToolInvoker().invoke({"server": "x", "tool": "y"})
