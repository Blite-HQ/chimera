# Registro histórico ADR-001–027

> **Estado: VIGENTE como registro (2026-07-30).** Rescate del saneamiento S3
> (decisión #112): este archivo hace resolubles desde `docs/adr/` los IDs
> `ADR-001`…`ADR-027` que código y esquema citan (`engine/sql/init_v2.sql:82`,
> `pyproject.toml:161,178,194`, `docs/esquema-datos-v2.md:127`, docstrings del
> engine). La fuente original es `docs/arquitectura-arc42-adrs.md` §12 (era del
> núcleo TS; las filas 001/002/012 están supersedidas por el pivote a Python —
> ver el header de ese doc). Solo ADR-008 y ADR-029 tienen expediente completo
> propio en esta carpeta; el resto vive únicamente en este registro. Promover
> una fila a expediente completo sigue el criterio de `docs/adr/README.md`.

## Tabla de decisiones (copiada de arc42 §12 — forma: decisión · invariante que sirve · fase)

| ADR     | Decisión                                                                             | Sirve a                       | Fase |
| ------- | ------------------------------------------------------------------------------------ | ----------------------------- | ---- |
| 001     | Núcleo TypeScript/NestJS; ciencia Python/FastAPI **(supersedida: núcleo Python)**    | Restricción de equipo         | 1    |
| 002     | Runtime sobre Node.js (Bun solo para _tooling_) **(supersedida: núcleo Python)**     | Restricción de equipo         | 1    |
| 003     | Monolito modular                                                                     | Restricción de equipo         | 1    |
| 004     | El Engine es dueño del loop (agentes nativos delgados)                               | AX3                           | 1    |
| 005→013 | Tres formas de integración → abstracción **Capability**; protocolos como _adapters_  | Interoperabilidad sin acoplar | 1→2  |
| 006     | Adoptar estándares abiertos, no inventar propietarios                                | No-dependencia                | 1    |
| 007→017 | Verificación anclada → **policy-as-code** + _attestations_                           | PR2/PR4, D18                  | 1→2  |
| 008     | La ciencia es una Capability, no parte del núcleo (**expediente:** ADR-008)          | Genericidad                   | 1    |
| 009→016 | Event Sourcing → **registro a prueba de manipulación**                               | AX2, D14–D16                  | 1→2  |
| 010     | Separación Leyes / Parámetros                                                        | AX1–AX3 vs configuración      | 1    |
| 011     | Profundidad sobre amplitud (un servicio QUBO completo)                               | Foco                          | 1    |
| 012     | PostgreSQL + pgvector + cola nativa de Node **(supersedida: Procrastinate/psycopg)** | Restricción de equipo         | 1    |
| 014     | **Governed-Invocation Gateway** unificado                                            | AX3/PR2/PR3/Inv-E             | 1→2  |
| 015     | Motor de ejecución durable                                                           | D16, robustez                 | 2    |
| 018     | Capacidades + bóveda + _zero-trust_                                                  | AX1, seguridad                | 1→2  |
| 019     | Plano de control sin datos / plano de datos soberano                                 | PR3, D19                      | 2    |
| 020     | Aislamiento microVM/WASM                                                             | AX3, Inv-E                    | 2    |
| 021     | Event Store con streams/snapshots/proyecciones                                       | D16, escalabilidad            | 2    |
| **022** | `override` como evento de primera clase + registro no desactivable                   | AX2 (cierre)                  | 1→2  |
| **023** | Agregado `Domain` / frontera / canal                                                 | AX1b (cierre)                 | 1→2  |
| **024** | Gateway como punto único de egreso y acción externa                                  | AX3/PR3/Inv-E                 | 1→2  |
| **025** | Certificado de confianza como salida de primera clase                                | D20 + demostración            | 1→2  |
| **026** | Camino de modelo local de primera clase                                              | Autonomía (D19)               | 1→2  |
| **027** | El puerto `Verifier` excluye modelos por construcción                                | D18                           | 1    |

## Invariante → componente → mecanismo (condensado de arc42 §6 — la fuente manda en el detalle)

| Invariante         | Componente que lo garantiza                 | Mecanismo / ADR                                                          |
| ------------------ | ------------------------------------------- | ------------------------------------------------------------------------ |
| AX1a (identidad)   | Identidad (JWT; SPIFFE Fase 2) + Gateway    | toda invocación estampa identidad o se rechaza                           |
| AX1b (aislamiento) | Agregado `Domain` + canales + Gateway       | cruce de dominio sin canal declarado = rechazo (ADR-023)                 |
| AX2 (meta-audit.)  | Registro a prueba de manipulación + Gateway | `override` evento de primera clase, registro no desactivable (ADR-022)   |
| AX3 (mediación)    | Gateway punto único + sandbox               | el modelo no tiene ruta directa al mundo (ADR-020)                       |
| PR1 (observab.)    | Event Store                                 | cada acción emite evento (event sourcing)                                |
| PR2/PR4 (verif.)   | Verifiers no-modelo + Gateway               | compuerta antes de comprometerse; commit del gateway (ADR-027)           |
| PR3 / Inv-E        | Gateway único punto de egreso + `Domain`    | egreso solo por autorización; la verificación jamás lo provoca (ADR-024) |
| D14–D16            | Event Store + hash-chain (Fase 2)           | procedencia reconstruible por replay                                     |
| D17–D18            | Verifiers no-modelo                         | por construcción (ADR-027)                                               |
| D19 (soberanía)    | Custodia + Policy + camino de modelo local  | ADR-026; ver nota de rescate abajo                                       |
| D20 (confianza)    | Certificado de confianza                    | artefacto de primera clase (ADR-025)                                     |
| D22 (integridad)   | AX2                                         | cerrar AX2 la cierra                                                     |

## Nota de rescate — ADR-026 y `ModelServer.local: boolean` (D19)

El único portador **tipado** del invariante de autonomía local-first (D19/ADR-026)
era `docs/archivo/especificacion-contratos.md` (contratos TS v1) §7: `ModelServer.local: boolean` con el
racional «`true` preserva autonomía». La semilla v2 lo perdió al unificar en
`ModelPort`, y el código actual (`engine/src/blite/serving/model_port.py`) porta el
campo sin codificar el invariante como tipo. El freeze §15.7 conserva la forma
(`id`, `local: boolean` — D19 local-first, `complete()`) y la supersesión
[S-F-real] registra honestamente `local: false` para los backends por API del mes.
Rescate S3 (#112): el concepto queda registrado aquí; volverlo garantía de tipo es
trabajo de backlog, no de saneamiento.
