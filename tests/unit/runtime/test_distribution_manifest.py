"""El `DistributionManifest` — lo que un DESPLIEGUE declara, fail-closed.

El freeze lo nombra desde §1 y lo daba por existente: los pins de versión que
`registry.py` espera («trabajo pendiente»), la matriz `interaction ×
execution_profile` que `validate_interaction_profile` valida sin que nadie lo
llame, y la allowlist de servidores externos que C-12 exige. Este archivo es su
contrato.

La regla que atraviesa todo: **fail-closed en DEPLOY, jamás en la primera
invocación**. Un despliegue mal declarado tiene que morir al arrancar, cuando
alguien está mirando — no a mitad de un run, cuando ya hay un claim colgando.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from blite.runtime.distribution import (
    DistributionManifest,
    McpServerSpec,
    load_distribution_manifest,
)


def _write(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "distribution.yaml"
    path.write_text(body, encoding="utf-8")
    return path


_MINIMO = """
version: 1
"""

_COMPLETO = """
version: 1
capability_pins:
  blite.solvers.qubo: '0.1.0'
execution_profiles:
  blite.mcp.invoke_tool: service
mcp_servers:
  ejemplo:
    transport: stdio
    command: uvx
    args: ['paquete-ejemplo==1.2.3']
    package_pin: 'paquete-ejemplo==1.2.3'
    egress: ['api.ejemplo.test']
    tools: ['leer_estado', 'listar_cosas']
"""


class TestCarga:
    def test_un_manifest_minimo_es_valido(self, tmp_path: Path) -> None:
        manifest = load_distribution_manifest(_write(tmp_path, _MINIMO))
        assert manifest.version == 1
        assert manifest.mcp_servers == {}

    def test_lee_pins_perfiles_y_servidores(self, tmp_path: Path) -> None:
        manifest = load_distribution_manifest(_write(tmp_path, _COMPLETO))
        assert manifest.capability_pins == {"blite.solvers.qubo": "0.1.0"}
        assert manifest.execution_profiles == {"blite.mcp.invoke_tool": "service"}
        assert set(manifest.mcp_servers) == {"ejemplo"}

    def test_una_version_desconocida_explota(self, tmp_path: Path) -> None:
        """Un manifest de otra versión se rechaza en vez de interpretarse a medias."""
        with pytest.raises(ValueError, match="version"):
            load_distribution_manifest(_write(tmp_path, "version: 99\n"))

    def test_un_campo_de_más_explota(self, tmp_path: Path) -> None:
        """`extra=forbid`: un typo en una llave de seguridad no puede pasar
        inadvertido como «no configurado»."""
        with pytest.raises(ValueError):
            load_distribution_manifest(
                _write(tmp_path, "version: 1\nmcp_serverss: {}\n")
            )

    def test_sin_archivo_devuelve_el_manifest_vacío_no_una_excepción(self) -> None:
        """Un despliegue sin manifest es legítimo (todo in-process, sin externos).

        Lo que NO es legítimo es un manifest presente y mal formado — ahí sí
        explota.
        """
        manifest = load_distribution_manifest(Path("/no/existe/distribution.yaml"))
        assert manifest == DistributionManifest()


class TestAllowlistDeServidoresMCP:
    """C-12: el vocabulario del tercero es DATO de configuración, y su
    superficie está declarada — no se descubre en runtime."""

    def test_un_servidor_fuera_de_la_lista_no_se_resuelve(self, tmp_path: Path) -> None:
        manifest = load_distribution_manifest(_write(tmp_path, _COMPLETO))
        assert manifest.server("ejemplo") is not None
        assert manifest.server("cualquier-otro") is None

    def test_un_tool_fuera_de_la_lista_del_servidor_no_está_permitido(
        self, tmp_path: Path
    ) -> None:
        """Que el servidor esté permitido NO permite todos sus tools.

        Un servidor MCP puede añadir tools entre versiones; heredar permiso por
        pertenecer al servidor sería aceptar superficie que nadie revisó.
        """
        manifest = load_distribution_manifest(_write(tmp_path, _COMPLETO))
        assert manifest.is_tool_allowed("ejemplo", "leer_estado")
        assert not manifest.is_tool_allowed("ejemplo", "borrar_todo")
        assert not manifest.is_tool_allowed("servidor-desconocido", "leer_estado")

    def test_un_servidor_sin_tools_declarados_no_permite_ninguno(
        self, tmp_path: Path
    ) -> None:
        """Lista vacía = nada permitido. Jamás «vacío significa todos»."""
        body = """
version: 1
mcp_servers:
  vacio:
    transport: stdio
    command: uvx
    args: ['x']
    package_pin: 'x==1'
    tools: []
"""
        manifest = load_distribution_manifest(_write(tmp_path, body))
        assert not manifest.is_tool_allowed("vacio", "lo-que-sea")

    def test_el_pin_del_paquete_es_obligatorio(self, tmp_path: Path) -> None:
        """Sin pin no hay reproducibilidad: `uvx paquete` trae lo que haya hoy."""
        body = """
version: 1
mcp_servers:
  sin_pin:
    transport: stdio
    command: uvx
    args: ['paquete']
    tools: ['x']
"""
        with pytest.raises(ValueError, match="package_pin"):
            load_distribution_manifest(_write(tmp_path, body))

    def test_el_egress_declarado_se_expone_tal_cual(self, tmp_path: Path) -> None:
        manifest = load_distribution_manifest(_write(tmp_path, _COMPLETO))
        assert manifest.egress_for("ejemplo") == ("api.ejemplo.test",)
        assert manifest.egress_for("desconocido") == ()


class TestDigestDeLaConfiguracion:
    def test_el_manifest_tiene_digest_estable(self, tmp_path: Path) -> None:
        """C-12: el vocabulario del tercero entra como datos CON DIGEST.

        Es lo que permite que una attestation diga contra QUÉ configuración se
        invocó — sin él, «se invocó un tool externo» no es una afirmación
        verificable.
        """
        a = load_distribution_manifest(_write(tmp_path, _COMPLETO))
        b = load_distribution_manifest(_write(tmp_path, _COMPLETO))
        assert a.digest() == b.digest()
        assert len(a.digest()) == 64

    def test_cambiar_la_allowlist_cambia_el_digest(self, tmp_path: Path) -> None:
        a = load_distribution_manifest(_write(tmp_path, _COMPLETO))
        b = load_distribution_manifest(
            _write(tmp_path, _COMPLETO.replace("'listar_cosas'", "'borrar_todo'"))
        )
        assert a.digest() != b.digest()


class TestMatrizDeDespachoEnDeploy:
    """El caller que `validate_interaction_profile` no tenía (censo §8.1-2)."""

    def test_un_par_valido_pasa(self) -> None:
        manifest = DistributionManifest(
            execution_profiles={"cap.a": "service"},
        )
        manifest.validate_profiles({"cap.a": "request_response"})

    def test_un_par_incompatible_muere_al_cargar_no_al_invocar(self) -> None:
        """`remote-job` sobre una capability `request_response`: prometerle un
        `JobRef` a quien espera un `Result` rompe el contrato del caller."""
        manifest = DistributionManifest(execution_profiles={"cap.a": "remote-job"})
        with pytest.raises(NotImplementedError, match="remote-job"):
            manifest.validate_profiles({"cap.a": "request_response"})

    def test_un_perfil_fuera_del_vocabulario_congelado_explota(self) -> None:
        manifest = DistributionManifest(execution_profiles={"cap.a": "inventado"})
        with pytest.raises(ValueError, match="execution_profile"):
            manifest.validate_profiles({"cap.a": "request_response"})

    def test_un_override_sobre_una_capability_que_no_existe_explota(self) -> None:
        """Un pin o perfil que apunta a nada es un despliegue mal declarado:
        alguien cree haber configurado algo que no está pasando."""
        manifest = DistributionManifest(execution_profiles={"cap.fantasma": "service"})
        with pytest.raises(ValueError, match="fantasma"):
            manifest.validate_profiles({"cap.a": "request_response"})


class TestFormaDelServidor:
    def test_el_transporte_esta_en_un_conjunto_cerrado(self) -> None:
        with pytest.raises(ValueError):
            McpServerSpec(
                transport="carrier-pigeon",  # type: ignore[arg-type]
                command="uvx",
                args=("x",),
                package_pin="x==1",
                tools=("t",),
            )
