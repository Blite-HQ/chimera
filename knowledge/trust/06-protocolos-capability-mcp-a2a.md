# Nota 06 — Capability como abstracción universal; MCP/A2A/AsyncAPI como adapters + el contrato del job asíncrono

**Ítem del plan (§4 Dylan):** MCP (spec + python-sdk) + A2A solo lectura + el ajuste de `CapabilityManifest` (§1.C del plan maestro)
**Fecha:** 2026-07-02 · **Estado:** **VIGENTE (2026-07-30).** Era «insumo para el contract freeze del viernes» — el freeze se materializó el 2026-07-18, ya no es cosa futura; el meta-hallazgo (capability como abstracción universal, ADR-013) y el contrato del job asíncrono siguen vigentes.
**Fuentes:** Revisión de arquitectura de referencia de Chimera (ADR-013, el meta-hallazgo) · MCP spec 2025-11-25 + python-sdk verificados en vivo 2026-07-02 · A2A verificado en vivo · plan maestro §1.C

---

## 1 · Patrón / mecanismo

### 1.1 El meta-hallazgo (ADR-013): lo universal es NUESTRA abstracción, no un protocolo ajeno

Hacer de MCP "el contrato universal" acoplaría el núcleo a la semántica de un protocolo externo (anti-patrón hexagonal: el dominio dependiendo de un detalle). La verificación en vivo de la spec lo confirma — MCP modela bien agente↔herramienta request/response con utilidades de progreso/cancelación, pero **no** modela: jobs durables de minutos/horas (un solve en QPU), movimiento masivo de datos, ni colaboración entre pares (eso es A2A). **Lo que se congela: el puerto `Capability` es el contrato; MCP, A2A, HTTP, in-process son adapters en el borde.**

### 1.2 "execution mode" refinado: son DOS ejes, no uno

El plan maestro (§1.C) pide agregar "execution mode: in-process | service | job" al manifest. La investigación (ADR-013 + la forma de A2A) lo refina en dos ejes ortogonales:

1. **`interaction`** — semántica del contrato (qué debe manejar el caller): `request_response | job | stream`. Es parte del **manifest** (congelado): cambiarlo rompe a los consumidores.
2. **`execution_profile`** — empaquetado por despliegue (dónde corre): `in-process | service | remote-job`. Es **perfil de despliegue** (§1.C: "el empaquetado es un perfil de ejecución por despliegue"), así que el valor por defecto va en el manifest como _hint_, pero la distribución (`DistributionManifest`) puede sobreescribirlo sin tocar el contrato.

La clave que unifica laptop→supercomputadora (plan §1.C): "todo es un job asíncrono detrás del mismo puerto Capability, emitiendo eventos" — `interaction: request_response` es el caso degenerado que completa de inmediato.

### 1.3 El contrato del job asíncrono (los eventos que la QPU fuerza)

**Precedente verificado:** el task lifecycle de A2A (submitted → working → input-required → completed/canceled/failed) es la forma madura de exactamente esto. Nuestros eventos de job, alineados sin adoptar el protocolo:

| Evento                     | Payload mínimo                          | Cuándo                                  |
| -------------------------- | --------------------------------------- | --------------------------------------- |
| `capability.job.submitted` | `{job_id, capability_id, input_digest}` | Encolado (ANTES de ejecutar — PR1)      |
| `capability.job.progress`  | `{job_id, phase, pct?, detail?}`        | Progreso observable (opcional, N veces) |
| `capability.job.completed` | `{job_id, output_digest, produced_by}`  | Resultado disponible                    |
| `capability.job.failed`    | `{job_id, error_kind, detail}`          | Falla (sin filtrar internals)           |

Todos son filas del stream del run (nota 01) — el Studio los consume por SSE (nota 07) sin saber si el job corrió in-process o en una QPU real. `invoke()` sync-only queda **descartado por diseño**: el puerto devuelve resultado inmediato O un `job_id` cuyo desenlace llega por eventos.

### 1.4 MCP a fondo (verificado): el mapeo manifest → tool

- **Spec vigente: 2025-11-25** (JSON-RPC 2.0; stateful; tools/resources/prompts; utilidades de progress tracking y cancellation). Transportes: stdio y **streamable HTTP** (SSE sigue soportado en el SDK).
- **python-sdk: MIT, v1.28.1 estable** (jun 2026) — ⚠️ existe v2.0.0b1 en beta con breaking changes: **pinear v1.x**.
- Mapeo directo (la razón por la que la interop es "gratis"): `manifest.id → tool.name`, `description → description`, `input_schema → inputSchema`, `output_schema → outputSchema`. Un MCP server genérico puede iterar el registry y exponer cada capability como tool — un adapter, cero cambios al núcleo.
- Lo que MCP NO da (y por eso es adapter, no contrato): identidad del actor con permisos escalonados (AX1 — la seguridad MCP es consentimiento del host), verificación anclada, jobs durables desacoplados de la conexión. Todo eso vive de nuestro lado del puerto, en el gateway.
- **Dirección de la interop en Fase 1: SALIDA** (exponer capabilities como MCP server). La ENTRADA (consumir MCP servers de terceros como capabilities) pasa por el gateway completo (identidad→authz→...→verificación) — contrato listo, implementación Fase 2.

### 1.5 A2A (solo lectura) y AsyncAPI

- **A2A** (Apache-2.0, Linux Foundation — verificado): agent cards = descubrimiento de capacidades entre agentes (el análogo peer-to-peer de nuestro manifest); JSON-RPC sobre HTTP + SSE + push. **No se adopta ahora**; su task lifecycle ya informó nuestros eventos de job (§1.3), y el puerto Capability deja la puerta abierta a un adapter A2A Fase 2 sin rediseño.
- **AsyncAPI** (documentar contratos de eventos como OpenAPI documenta REST): valioso cuando haya consumidores externos del stream. Este mes el único consumidor es el Studio → **se difiere**; el contrato de eventos se congela en Pydantic + el doc del freeze.

## 2 · Decisión

| Referencia                              | Decisión                                                                               | Racional                                                    |
| --------------------------------------- | -------------------------------------------------------------------------------------- | ----------------------------------------------------------- |
| Puerto `Capability` universal (ADR-013) | **portar** (es nuestro; se congela con `interaction` + `execution_profile`)            | La unificación va en la gobernanza, no en el protocolo      |
| MCP python-sdk (v1.x, MIT)              | **integrar** (adapter de salida: registry → MCP server; implementación semana 3/bonus) | Interop estándar de la industria; mapeo 1:1 con el manifest |
| MCP como contrato universal             | **descartar**                                                                          | No modela async largo/datos masivos/A2A; acopla el núcleo   |
| A2A                                     | **inspirar** (task lifecycle → eventos de job) / adapter Fase 2                        | Apache-2.0; peer-to-peer no es alcance del mes              |
| AG-UI (para el Studio)                  | ver nota 07                                                                            | —                                                           |
| AsyncAPI                                | **descartar** este mes / reevaluar Fase 2                                              | Sin consumidores externos del stream aún; Pydantic basta    |

## 3 · Licencias

| Pieza                  | Licencia                                 | Verificado 2026-07-02                         |
| ---------------------- | ---------------------------------------- | --------------------------------------------- |
| MCP spec (2025-11-25)  | spec abierta (repo del proyecto)         | ✅ en vivo                                    |
| MCP python-sdk v1.28.1 | **MIT**                                  | ✅ en vivo (⚠️ pinear v1.x; v2 en beta rompe) |
| A2A                    | **Apache-2.0** (Linux Foundation)        | ✅ en vivo                                    |
| AsyncAPI spec          | Apache-2.0 ⚠️ (no verificado — diferido) | —                                             |

## 4 · Impacto en contrato

Contra la semilla TS §2 y el stub actual (`sdk/src/blite_capability/manifest.py`, que hoy NO tiene side_effects/permission/protocol):

1. **`CapabilityManifest` v2** (el cambio central del freeze — frontera con Steven, campos señalados aquí, mecánica del registry es suya):
   ```python
   class CapabilityManifest(BaseModel):
       id: str; description: str; version: str
       input_schema: dict; output_schema: dict
       tags: tuple[str, ...] = ()
       side_effects: Literal["pure", "reversible-external", "irreversible-external"]  # PR2/PR4 (consume nota 05)
       required_permission: str                                                        # AX1 (consume nota 08)
       interaction: Literal["request_response", "job", "stream"]                       # semántica congelada
       execution_profile: Literal["in-process", "service", "remote-job"] = "in-process"  # hint; la distribución puede sobreescribir
   ```
   (`protocol` de la semilla TS desaparece del manifest: el protocolo es del ADAPTER, no de la capability — ADR-013.)
2. **Eventos de job** (§1.3): 4 tipos nuevos en el vocabulario de eventos del run; `submitted` se escribe ANTES de ejecutar (PR1/AX2).
3. **Puerto `Capability.invoke`**: retorno = resultado inmediato | referencia de job; el desenlace SIEMPRE queda en eventos (aunque sea sync).
4. **Mapeo manifest→MCP tool** congelado como tabla (§1.4) — el adapter que lo implemente no necesita decisiones nuevas.
5. **`DistributionManifest`** (carpeta `distributions/chimera/`, carril Dylan): gana la potestad de sobreescribir `execution_profile` por despliegue.

## 5 · Reconciliación contra la base lógica

- **AX3 (el modelo nunca toca el mundo directo):** REFORZADO — exponer capabilities por MCP es un adapter DELANTE del gateway; consumir MCP externo pasa por el pipeline completo. Ningún protocolo puentea la mediación.
- **INV-1 (gateway único chokepoint):** INTACTO — los adapters de protocolo viven en el borde (`protocols/`), y protocols exige authz (INV-6).
- **PR1/AX2:** REFORZADO — `job.submitted` antes de ejecutar extiende el patrón provenance:pre al mundo asíncrono.
- **ADR-029 (manifests genéricos):** INTACTO — los campos nuevos son metadatos de gobernanza, no términos de escenario; el test de genericidad aplica igual.
- **Referencia que "contradice":** la seguridad de MCP descansa en consentimiento del host, sin identidad de actor escalonada — dato sobre MCP (su modelo de amenaza es el desktop host, no un engine multi-actor); por eso es adapter y no contrato.
