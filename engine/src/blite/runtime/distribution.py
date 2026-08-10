"""
`DistributionManifest` — lo que un DESPLIEGUE declara (freeze §1).

El freeze lo nombra desde el principio y lo daba por existente: los pins de
versión que `registry.py` espera («trabajo pendiente del DistributionManifest»),
la matriz `interaction × execution_profile` que `validate_interaction_profile`
sabe validar sin que nadie la llamara, y —desde C-12— la allowlist de servidores
MCP externos. Este módulo lo materializa.

**Fail-closed en DEPLOY, jamás en la primera invocación.** Un despliegue mal
declarado tiene que morir al arrancar, cuando alguien está mirando, no a mitad
de un run cuando ya hay un claim colgando. Por eso `validate_profiles` se llama
al cargar el registry, no dentro de `invoke`.

**Es configuración, no dominio.** El manifest no sabe qué es un reto ni una red:
declara ids, versiones, perfiles y hosts. El vocabulario del tercero (los
nombres de sus tools) entra como DATO con digest — ADR-029 intacto por
construcción, que es exactamente lo que C-12 resolvió.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

from blite.catalog.croissant import DatasetDescription
from blite.runtime.dispatch import validate_interaction_profile

SUPPORTED_VERSION = 1

_DIGEST_DOMAIN = "blite/distribution-manifest/v1"
"""Prefijo de dominio versionado (misma disciplina que el anexo de
canonicalización): cambiar CÓMO se digesta un manifest = bump del prefijo."""

McpTransport = Literal["stdio", "http"]


class McpServerSpec(BaseModel):
    """Un servidor MCP externo, con TODA su superficie declarada.

    Nada acá se descubre en runtime: qué se ejecuta, con qué versión, a dónde
    puede salir y qué tools se pueden llamar. Un servidor MCP puede añadir tools
    entre versiones — heredar permiso por pertenecer al servidor sería aceptar
    superficie que nadie revisó.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    transport: McpTransport
    package_pin: str
    """Versión EXACTA del paquete del servidor (`nombre==x.y.z`).

    SIN default a propósito: `uvx paquete` sin pin trae lo que haya hoy en el
    índice, y una capability gobernada no puede depender de eso. Es también lo
    que la attestation de importación cita como `builder`."""
    command: str = ""
    """Ejecutable (transporte `stdio`). Sale de la allowlist, jamás del claim."""
    args: tuple[str, ...] = ()
    url: str = ""
    """Endpoint (transporte `http`)."""
    egress: tuple[str, ...] = ()
    """Hosts que ESTE servidor puede tocar. Declarativo: lo consume la política
    de egreso del gateway (Inv-E — egreso lo decide authz, no el adapter)."""
    tools: tuple[str, ...] = ()
    """Allowlist de tools. Vacía = ninguno permitido, jamás «todos»."""

    @field_validator("package_pin")
    @classmethod
    def _pin_no_vacio(cls, value: str) -> str:
        if not value.strip():
            msg = (
                "McpServerSpec.package_pin no puede ir vacío — sin pin no hay "
                "reproducibilidad ni `builder` que citar en la attestation"
            )
            raise ValueError(msg)
        return value


class DatasetSpec(BaseModel):
    """Un dataset que ESTE despliegue publica (O4/M10).

    La plataforma no sabe qué datos tiene: los descubre porque un despliegue
    los declara. Por eso los nombres de dominio viven acá —en configuración—
    y no en el código, que es justo lo que ADR-029 pide.

    `license` es OBLIGATORIA y no tiene default. Publicar un dataset sin decir
    bajo qué términos se puede usar traslada el problema a quien lo descargue,
    que es quien menos puede resolverlo; y un default («desconocida», «propia»)
    sería una respuesta inventada a una pregunta legal. Si el despliegue no
    sabe la licencia, no publica el dataset.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    path: str
    """Directorio de instancias, relativo a la raíz del repo."""
    description: str
    license: str
    """Identificador SPDX o URL de la licencia bajo la que se publica."""
    url: str
    """Dónde vive el dataset — la página a la que apunta el export."""
    title: str = ""
    """Título legible. `name` en Croissant es el identificador, no el título."""
    version: str = "1.0.0"
    cite_as: str = ""
    date_published: str = ""

    @field_validator("path", "description", "license", "url")
    @classmethod
    def _sin_vacios(cls, value: str) -> str:
        if not value.strip():
            msg = (
                "DatasetSpec: `path`, `description`, `license` y `url` son "
                "obligatorios — un dataset publicado sin ellos no es usable "
                "por un tercero, que es el único motivo para publicarlo"
            )
            raise ValueError(msg)
        return value

    def description_for_export(self, dataset_id: str) -> DatasetDescription:
        return DatasetDescription(
            dataset_id=dataset_id,
            name=self.title,
            description=self.description,
            license=self.license,
            url=self.url,
            version=self.version,
            cite_as=self.cite_as,
            date_published=self.date_published,
        )


class DistributionManifest(BaseModel):
    """Lo que este despliegue declara. Vacío = todo in-process, sin externos."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    version: int = SUPPORTED_VERSION
    capability_pins: Mapping[str, str] = Field(default_factory=dict)
    """`{capability_id: versión}` — resuelve ids duplicados por despliegue con
    default determinista (freeze §1: jamás `latest`)."""
    execution_profiles: Mapping[str, str] = Field(default_factory=dict)
    """Override de perfil por capability. Validado contra la matriz AL CARGAR."""
    mcp_servers: Mapping[str, McpServerSpec] = Field(default_factory=dict)
    datasets: Mapping[str, DatasetSpec] = Field(default_factory=dict)
    """`{dataset_id: spec}` — el catálogo que este despliegue publica."""

    @field_validator("version")
    @classmethod
    def _version_soportada(cls, value: int) -> int:
        if value != SUPPORTED_VERSION:
            msg = (
                f"DistributionManifest version {value} no soportada "
                f"(esta build entiende {SUPPORTED_VERSION}) — un manifest de otra "
                "versión se rechaza, jamás se interpreta a medias"
            )
            raise ValueError(msg)
        return value

    # ── Servidores externos ────────────────────────────────────────────────

    def server(self, server_id: str) -> McpServerSpec | None:
        return self.mcp_servers.get(server_id)

    def is_tool_allowed(self, server_id: str, tool: str) -> bool:
        spec = self.server(server_id)
        return spec is not None and tool in spec.tools

    def egress_for(self, server_id: str) -> tuple[str, ...]:
        spec = self.server(server_id)
        return spec.egress if spec is not None else ()

    # ── Identidad ──────────────────────────────────────────────────────────

    def digest(self) -> str:
        """Digest de la configuración declarada.

        Es lo que permite que una attestation diga contra QUÉ configuración se
        invocó un tool ajeno: sin él, «se invocó un tool externo» no es una
        afirmación verificable por nadie.
        """
        payload = json.dumps(
            self.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
        )
        return hashlib.sha256(f"{_DIGEST_DOMAIN}\n{payload}".encode()).hexdigest()

    # ── Fail-closed de deploy ──────────────────────────────────────────────

    def profile_for(self, capability_id: str, default: str = "in-process") -> str:
        return self.execution_profiles.get(capability_id, default)

    def validate_profiles(self, interactions: Mapping[str, str]) -> None:
        """Valida la matriz `interaction × execution_profile` del despliegue.

        `interactions` = `{capability_id: interaction}` tal como los manifests
        cargados lo declaran. Un override sobre una capability que no existe es
        un despliegue mal declarado —alguien cree haber configurado algo que no
        está pasando— y también explota.
        """
        for capability_id, profile in self.execution_profiles.items():
            if capability_id not in interactions:
                msg = (
                    f"execution_profiles declara {capability_id!r}, que no está "
                    "entre las capabilities cargadas — override sobre nada"
                )
                raise ValueError(msg)
            validate_interaction_profile(interactions[capability_id], profile)


def load_distribution_manifest(path: Path) -> DistributionManifest:
    """Carga el manifest. Sin archivo ⇒ manifest vacío; MAL FORMADO ⇒ explota.

    La asimetría es deliberada: un despliegue sin manifest es legítimo (todo
    in-process, sin externos), pero uno que declara algo y lo declara mal no
    puede arrancar con la mitad de su configuración ignorada.
    """
    if not path.is_file():
        return DistributionManifest()
    raw: Any = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        msg = f"{path}: el manifest debe ser un mapa YAML"
        raise ValueError(msg)
    return DistributionManifest.model_validate(raw)
