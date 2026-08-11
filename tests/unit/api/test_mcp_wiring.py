"""El cliente MCP gobernado: allowlist fail-closed y attestation de importación.

Lo que exige red (el round-trip real) se verifica VIVO contra `qnexus-mcp`; lo
que decide comportamiento —a quién se le dice que no, y qué se certifica— se
prueba acá.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from chimera_api.mcp_wiring import (
    MCP_CAPABILITY_ID,
    PREDICATE_TYPE,
    build_import_statement,
    build_mcp_invoker,
)

from blite.protocols.mcp import (
    McpCallResult,
    McpInvocationRefusedError,
    McpTransportError,
    build_child_env,
    invoke_mcp_tool,
)
from blite.runtime.dispatch import ProfileDispatcher, ServiceStrategy
from blite.runtime.distribution import DistributionManifest, McpServerSpec
from blite_cap_mcp import McpToolInvoker


def _manifest() -> DistributionManifest:
    return DistributionManifest(
        mcp_servers={
            "servidor-ok": McpServerSpec(
                transport="stdio",
                package_pin="paquete==1.2.3",
                command="uvx",
                args=("paquete==1.2.3",),
                egress=("api.ejemplo.test",),
                tools=("leer_estado",),
            )
        }
    )


def _result(is_error: bool = False) -> McpCallResult:
    return McpCallResult(
        server_id="servidor-ok",
        tool="leer_estado",
        content=({"type": "text", "text": "ok"},),
        is_error=is_error,
        server_name="paquete",
        server_version="1.2.3",
        package_pin="paquete==1.2.3",
    )


class TestFailClosed:
    """Antes de levantar NADA se comprueba qué declaró el despliegue."""

    def test_servidor_fuera_de_la_allowlist_se_rechaza_sin_tocar_la_red(self) -> None:
        with pytest.raises(McpInvocationRefusedError, match="no declarado"):
            invoke_mcp_tool(_manifest(), {"server": "pirata", "tool": "leer_estado"})

    def test_tool_fuera_de_la_allowlist_del_servidor_se_rechaza(self) -> None:
        """Que el servidor esté permitido no permite todos sus tools."""
        with pytest.raises(McpInvocationRefusedError, match="allowlist"):
            invoke_mcp_tool(
                _manifest(), {"server": "servidor-ok", "tool": "borrar_todo"}
            )

    def test_argumentos_que_no_son_objeto_se_rechazan(self) -> None:
        with pytest.raises(McpInvocationRefusedError, match="arguments"):
            invoke_mcp_tool(
                _manifest(),
                {
                    "server": "servidor-ok",
                    "tool": "leer_estado",
                    "arguments": "no soy dict",
                },
            )

    def test_un_transporte_sin_adapter_explota_en_vez_de_caer_a_otro(self) -> None:
        manifest = DistributionManifest(
            mcp_servers={
                "http-server": McpServerSpec(
                    transport="http",
                    package_pin="x==1",
                    url="https://ejemplo.test/mcp",
                    tools=("t",),
                )
            }
        )
        with pytest.raises(McpTransportError, match="transporte"):
            invoke_mcp_tool(manifest, {"server": "http-server", "tool": "t"})


class TestAttestationDeImportacion:
    def test_el_builder_es_la_coordenada_del_tool_ajeno(self) -> None:
        """C-12, literal: `builder.id = mcp://<server>/<tool>`."""
        statement = build_import_statement(
            _result(), manifest=_manifest(), arguments={}
        ).to_intoto()
        assert (
            statement["predicate"]["builder"]["id"] == "mcp://servidor-ok/leer_estado"
        )
        assert statement["predicateType"] == PREDICATE_TYPE
        assert statement["_type"] == "https://in-toto.io/Statement/v1"

    def test_cita_el_pin_exigido_y_la_version_que_el_servidor_dice_ser(self) -> None:
        """Si divergen, la attestation lo MUESTRA en vez de esconderlo."""
        deps = build_import_statement(
            _result(), manifest=_manifest(), arguments={}
        ).to_intoto()["predicate"]["resolvedDependencies"]
        paquete = next(d for d in deps if d["name"] == "mcp-server-package")
        assert paquete["pin"] == "paquete==1.2.3"
        assert (paquete["reported_name"], paquete["reported_version"]) == (
            "paquete",
            "1.2.3",
        )

    def test_ancla_la_configuracion_bajo_la_que_se_invoco(self) -> None:
        """Sin el digest del manifest, «se invocó un tool externo» no es
        verificable: nadie sabría contra qué allowlist ni con qué pins."""
        manifest = _manifest()
        deps = build_import_statement(
            _result(), manifest=manifest, arguments={}
        ).to_intoto()["predicate"]["resolvedDependencies"]
        conf = next(d for d in deps if d["name"] == "distribution-manifest")
        assert conf["digest"]["sha256"] == manifest.digest()

    def test_los_argumentos_viajan_por_digest_jamas_en_claro(self) -> None:
        """Una attestation no es lugar para contenido: los argumentos los pone
        el proponente y pueden llevar cualquier cosa."""
        secreto = {"token": "no-deberia-viajar-en-claro"}
        statement = build_import_statement(
            _result(), manifest=_manifest(), arguments=secreto
        ).to_intoto()
        assert "no-deberia-viajar-en-claro" not in str(statement)
        assert (
            len(statement["predicate"]["externalParameters"]["arguments_digest"]) == 64
        )

    def test_un_resultado_de_error_del_tool_tambien_se_certifica(self) -> None:
        """El tool falló ≠ la importación no ocurrió. Se registra lo que pasó."""
        statement = build_import_statement(
            _result(is_error=True), manifest=_manifest(), arguments={}
        ).to_intoto()
        assert statement["predicate"]["externalParameters"]["is_error"] is True


class TestDespacho:
    def test_sin_invocador_inyectado_el_perfil_service_no_cae_a_in_process(
        self,
    ) -> None:
        """El fallback silencioso se saltaría allowlist, pin y attestation."""
        with pytest.raises(NotImplementedError, match="service"):
            ProfileDispatcher().resolve("service")

    def test_con_invocador_el_perfil_resuelve(self) -> None:
        dispatcher = ProfileDispatcher(
            service=ServiceStrategy(build_mcp_invoker(_manifest()))
        )
        assert isinstance(dispatcher.resolve("service"), ServiceStrategy)

    def test_el_invocador_solo_atiende_la_capability_de_mcp(self) -> None:
        invoker = build_mcp_invoker(_manifest())
        with pytest.raises(NotImplementedError, match="invocador de servicio"):
            invoker("blite.solvers.qubo", {})

    def test_la_capability_declara_el_perfil_que_el_dispatcher_resuelve(self) -> None:
        """La costura entera en una línea: el manifest dice `service`, el
        dispatcher tiene estrategia para `service`, y el id calza."""
        manifest = McpToolInvoker().manifest
        assert manifest.id == MCP_CAPABILITY_ID
        assert manifest.execution_profile == "service"


class TestEntornoDelProcesoAjeno:
    """Un binario de terceros no hereda nuestro entorno.

    Heredarlo le entregaría la contraseña de la base y la key del modelo por
    conveniencia. La lista es BLANCA a propósito: una denylist se queda corta el
    día que alguien agrega una variable nueva, y el modo de falla es entregarla.
    """

    def test_solo_pasan_path_home_y_las_del_gestor_de_paquetes(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("CHIMERA_DB_PASSWORD", "secreto-de-la-base")
        monkeypatch.setenv("CHIMERA_MODEL_API_KEY", "sk-secreta")
        monkeypatch.setenv("UV_CACHE_DIR", "/app/var/uv-cache")

        env = build_child_env(str(tmp_path))

        assert env["HOME"] == str(tmp_path)
        assert env["UV_CACHE_DIR"] == "/app/var/uv-cache"
        assert "PATH" in env
        assert "CHIMERA_DB_PASSWORD" not in env
        assert "CHIMERA_MODEL_API_KEY" not in env

    def test_el_home_es_propio_no_el_del_proceso_padre(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Muchos servidores MCP escriben su config al arrancar — por eso un
        contenedor endurecido con `--no-create-home` los rompe."""
        monkeypatch.setenv("HOME", "/home/del-padre")
        assert build_child_env(str(tmp_path))["HOME"] == str(tmp_path)
