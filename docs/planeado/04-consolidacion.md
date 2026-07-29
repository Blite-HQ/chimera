# Consolidación Planeado/Mejorado — convergencia validada y backlog operativo

> **Estado: VIGENTE (2026-07-24).** Cierra el ciclo de research: valida que diseño ↔
> investigación convergen, resuelve las divergencias, y deja EL backlog operativo de
> Planeado y Mejorado. El criterio sigue siendo `00-criterio-niveles.md`; las tablas de
> backlog de ese doc quedan superseded por este. Ejecución: `05-plan-paralelo.md`.

## 1 · Veredicto de convergencia: CONVERGEN

El diseño congelado y el research de estado del arte llegan al mismo lugar por caminos
independientes. Evidencia:

| Diseño (congelado)                                                                                              | Research (fuentes vivas)                                                                       | Señal                                                 |
| --------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- | ----------------------------------------------------- |
| `●PlanCreated` YA está en el catálogo de eventos §14                                                            | R1: plan como artefacto de eventos en el stream                                                | el diseño anticipó el plan del agente                 |
| `execution/03`: "durabilidad por replay del event log, NO motor nuevo" (Temporal/DBOS comparados sin verificar) | R1 llega a lo mismo con fuentes vivas + añade replay-por-digest y detección de no-determinismo | convergencia independiente                            |
| §15.3: identidad instancia = digest del JSON canónico + provenance                                              | R2: receta PROV estilo dvc.lock dentro de `provenance`                                         | misma doctrina, R2 la extiende a ingesta              |
| §11 + `quantum/08`: campos multi-backend por pata (transpiled digest, backend_id, noise)                        | R3: instancia normalizada de counts + predicado SLSA                                           | el diseño pedía los campos; R3 trae la forma estándar |
| §7 deliverables `{ref, digest}` + §12 ContentStore + punto 3 verify-bundle                                      | R4: PDF Typst determinista como deliverable                                                    | el sustrato ya soporta el informe                     |
| §9: "SSE simple; AG-UI descartado este mes"                                                                     | Tesis 3: proyectar vocabularios, jamás adoptar protocolos de wire                              | misma decisión, ahora con argumento de industria      |
| §15.4: replay como config de primera clase                                                                      | R1: replay por digest como propiedad certificable                                              | R1 lo vuelve demostrable ("verifica ⟺ fiel")          |

## 2 · Divergencias y su resolución (decisión #64)

1. **Pipeline fijo (freeze §13) vs loop que planifica (P4)** — la única dura, ya
   identificada en `02-cobertura-diseno.md`. Resolución: supersede formal en la Fase 0
   del plan paralelo, con ratificación de Steven ANTES de tocar `loop.py`. El agente
   elige sub-runs del registry (limpia el set hardcodeado de §13); la replanificación se
   modela como steps nuevos, no como re-entrada al gateway (respeta §8).
2. **Attestation de importación Nexus**: R3 la propuso como DSSE individual; el freeze
   (T6) fija Fase 1 = attestations EMBEBIDAS en el payload del certificado. Resolución:
   **embebida en Fase 1** con su `predicateType` de importación; DSSE individual queda
   Fase 2 (ya declarado). Cero cambio al modelo de verificación.
3. **`claim_type` de ingesta/derivación**: el perfil STEM está CONGELADO. Resolución:
   **extensión aditiva** (anexo al perfil, mismo mecanismo que las capas del freeze),
   ratifica el dueño del plano de confianza.
4. **Vistas SSE nuevas** (mapa, plan del agente, aprobación): extensión aditiva del
   contrato §9 — payloads nuevos, sin tocar los congelados.

## 3 · PLANEADO consolidado (backlog operativo)

Organizado por dominio de ejecución (ver `05-plan-paralelo.md`). Cada feature cita su
base de diseño y su research.

### Dominio A — Harness agéntico

| ID  | Feature                                                                                                                                                                                                                    | Base               |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------ |
| A1  | Supersede "pipeline fijo" → loop agéntico (ceremonia de contrato + ratificación Steven)                                                                                                                                    | 02 §choque         |
| A2  | Adapter ModelServer (LiteLLM: `replay`/`record`/vivo por API) tras el puerto `ModelPort`                                                                                                                                   | §15.7 · exec/05/09 |
| A3  | Loop plano de 5 componentes: proponer→gobernar→ejecutar→journalizar→verificar; plan como eventos (`plan.created`/`plan.item_updated` sobre `●PlanCreated` §14); terminación triple (max_turns+budget+gate de verificación) | R1 · exec/02       |
| A4  | Sub-runs: spawn + `●ClaimEmitted` + cascada de cancelación + herencia de policy (contrato §13 ya decidido, solo construir)                                                                                                 | §13                |
| A5  | Replay por digest de TODO efecto + evento `replay.divergence` ("certificado verifica ⟺ replay fiel") + grabación de sesión agéntica completa                                                                               | R1 · exec/03       |
| A6  | Gobernanza tripwire: veredictos de etapa como eventos tipados; aprobación humana estilo elicitation (par de eventos, replay-able)                                                                                          | R1 · trust/13/16   |

### Dominio B — Datos y evidencia (ciencia)

| ID  | Feature                                                                                                                                                                       | Base            |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------- |
| B1  | Capability de ingesta GeoJSON→grafo: snapshot crudo + receta PROV con assertions (geojson-pydantic/pandera); claim_type como anexo del perfil                                 | R2 · exec/10    |
| B2  | Instancias cr6/cr8 + red ICE 70 nodos al corpus (gate: ratificación Sebas §1.9 + actualizar guard de digests)                                                                 | §15.3           |
| B3  | `ConsensusReplicationPredicate` ampliado a campos §11 + importador de las 19 corridas Nexus (attestation de importación EMBEBIDA, predicado SLSA; sin `RuntimeDecoder` — CVE) | R3 · quantum/08 |
| B4  | Artefacto de extrapolación honesta (ieee30→70 nodos clásico, barrera 26 qubits)                                                                                               | §15.3           |

### Dominio C — Informe (entregable)

| ID  | Feature                                                                                               | Base    |
| --- | ----------------------------------------------------------------------------------------------------- | ------- |
| C1  | Capability de plotting determinista (svg.hashsalt + SOURCE_DATE_EPOCH) con receta                     | R4      |
| C2  | Capability de informe: plantilla Typst versionada + typst-py → PDF byte-reproducible ≤8p              | R4      |
| C3  | Binding cifra→certificado (pie `sha256 · cert:<id>` + anexo de verificación) + slides + statement SDK | R4 · §7 |

### Dominio D — Studio (frontend)

| ID  | Feature                                                                                                                  | Base          |
| --- | ------------------------------------------------------------------------------------------------------------------------ | ------------- |
| D1  | Honestidad: ramas live en las 6 queries, matar spike/`DEMO_RUN_ID`/carrera SSE; modo Replay SOLO etiquetado con banner   | 02 §P1        |
| D2  | Compose live: `VITE_API_URL` en Dockerfile+compose (ojo: dos env vars distintas)                                         | 02 §P2        |
| D3  | Egress + vistas contra rutas nuevas (lista runs, artifacts, knowledge, evidence, ablation, topología)                    | R6            |
| D4  | Mapa: fase 1 SVG (silueta CR + d3-geo + tokens, garantía air-gap) → fase 2 MapLibre+PMTiles (glyphs/sprites self-hosted) | R5            |
| D5  | r vs p: Recharts `ErrorBar`+`ReferenceLine` vía ChartContainer + tabla comparativa                                       | R5            |
| D6  | Timeline agéntico: plan-checklist + cards por paso con drill-down + scrubber de replay + card de aprobación inline       | R5 · trust/18 |

### Dominio E — API (runtime-api)

| ID  | Feature                                                                                                                 | Base    |
| --- | ----------------------------------------------------------------------------------------------------------------------- | ------- |
| E1  | Rutas nuevas: `GET /runs`, artifacts, knowledge, step-evidence, ablation, topología/partición (formas §9 ya congeladas) | R6      |
| E2  | Payloads SSE nuevos: plan del agente, aprobación, mapa (extensión aditiva §9)                                           | R5 · §9 |

Transversales: P9 guion+video (tras integración) · P10 sanitización continua.

## 4 · MEJORADO consolidado

Sobre la base Planeado. De la lista previa + lo nuevo del research:

| ID  | Ítem                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| M1  | LLM vivo como default de escena + chat multi-turno libre                                                                                                                                                                                                                                                                                                                                                                                        |
| M2  | Cruce del gateway por step + flip AX1                                                                                                                                                                                                                                                                                                                                                                                                           |
| M3  | Z3 RuleVerifier                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| M4  | Attestation por isla de primera clase                                                                                                                                                                                                                                                                                                                                                                                                           |
| M5  | Pata Guppy/qnexus viva (orquestar corridas H2 nuevas)                                                                                                                                                                                                                                                                                                                                                                                           |
| M6  | Extensiones cuánticas: ZNE, warm-start, QEC/Iceberg                                                                                                                                                                                                                                                                                                                                                                                             |
| M7  | Retos 2/3 con la misma plataforma                                                                                                                                                                                                                                                                                                                                                                                                               |
| M8  | Fase 2 del freeze (hash-chain, StatusList, DSSE por attestation, OpenBao/HSM, SPIFFE, Rekor) + Fargate/BYOC + MCP de salida + ingesta KG                                                                                                                                                                                                                                                                                                        |
| M9  | _(nuevo)_ Proyector stream→OTel GenAI + backend Langfuse self-hosted                                                                                                                                                                                                                                                                                                                                                                            |
| M10 | _(nuevo)_ Export Croissant de instancias (publicación de datasets)                                                                                                                                                                                                                                                                                                                                                                              |
| M11 | _(nuevo)_ Baseline SA como capability (greedy ya cumple "GW + ≥1")                                                                                                                                                                                                                                                                                                                                                                              |
| M12 | _(nuevo)_ Upgrade mapa: deck.gl si la escala de datos lo justifica alguna vez                                                                                                                                                                                                                                                                                                                                                                   |
| M13 | _(nuevo)_ Adapter genérico MCP-cliente en el registry: cualquier MCP server externo (ej. qnexus-mcp) expone sus tools como capabilities gobernadas (manifest + egress policy + attestation de importación) — dentro del runtime se prefiere el SDK directo; MCP-cliente es para integraciones de terceros arbitrarias                                                                                                                           |
| M14 | _(nuevo, auditoría Fase 2 #95)_ `distributions/chimera` como paquete raíz de composición real (api + capabilities + extras curados) — reemplaza el `--all-packages --all-extras` del Dockerfile y adelgaza la imagen (hoy 10.9GB)                                                                                                                                                                                                               |
| M15 | _(nuevo, directriz Dylan 29-jul)_ Sidebar completo del Studio: apartado de user/organization, selector real multi-proyecto (varios proyectos simulados o reales), colapsar/expandir el sidebar                                                                                                                                                                                                                                                  |
| M16 | _(nuevo, directriz Dylan 29-jul)_ Branding: icono/logo de Chimera en condiciones. Brief desde las ~21 referencias que Dylan curó (Downloads de su máquina): marca geométrica mínima estilo ciencia/tech — trazos de línea topológicos (ondas/red de nodos-aristas), monocromo + un acento (el teal de la paleta), legible a 16px, variantes claro/oscuro; candidatos naturales: red-de-nodos (la partición) o el glifo de 3 barras de confianza |
| M17 | _(nuevo, directriz Dylan 29-jul)_ Navegación con URLs reales (router + deep-link a run/tab, breadcrumb ya navegable desde Fase 2) y "go-back" consistente en artifacts/papers/knowledge                                                                                                                                                                                                                                                         |
