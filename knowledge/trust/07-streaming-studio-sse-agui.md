# Nota 07 — Streaming del Studio: SSE simple vs AG-UI + el contrato de eventos por vista + hallazgos del spike

**Ítems del plan (§4 Dylan):** #4 (parcial: streaming Studio↔Engine) y #5 (spike Cytoscape)
**Fecha:** 2026-07-03 · **Estado:** **VIGENTE (2026-07-30).** Escrita como «insumo para el contract freeze» — el freeze se materializó el 2026-07-18 (`docs/contract-freeze.md`), ya no es cosa futura; la decisión SSE-simple y el contrato de eventos por vista siguen vigentes.
**Fuentes:** CHIMERA-Studio-Frontend (vistas y comportamientos) · AG-UI verificado en vivo 2026-07-03 (MIT, ~16 tipos de evento, transport-agnóstico) · nota 01 (cursor global/notify-then-catchup) · spike en `apps/studio/src/spike/`

---

## 1 · Patrón / mecanismo

### 1.1 La decisión: SSE simple gana (para este Studio, este mes)

| Criterio                | SSE simple                                                                                                                                | AG-UI                                                                                                                                                                 |
| ----------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Naturaleza del Studio   | ✅ read-only sobre proyecciones (regla `studio-solo-por-api`); no muta, no chatea                                                         | Diseñado para interacción bidireccional agente↔usuario (estado compartido, tool calls en la UI)                                                                       |
| Reanudación             | ✅ `Last-Event-ID` nativo del estándar SSE → mapea 1:1 al `global_seq` (nota 01)                                                          | Transport-agnóstico: la reanudación la resuelve cada integración                                                                                                      |
| Vocabulario             | Nuestros eventos YA existen (el event log es la fuente); SSE solo los transporta                                                          | Sus ~16 tipos de evento (mensajes, tool calls, state deltas) modelan un chat de agente — **no** procedencia/verificación/certificado, que es lo que el Studio muestra |
| Dependencias            | Cero en el cliente (`EventSource` nativo del navegador)                                                                                   | SDK + adaptación de vocabulario                                                                                                                                       |
| Costo de migrar después | Bajo: si Fase 2 trae un Studio interactivo (chat con el agente), AG-UI se monta como **otro endpoint** sin tocar el stream de procedencia | —                                                                                                                                                                     |

**Decisión: SSE simple.** El match decisivo es de vocabulario: AG-UI modela _conversación con un agente_; nuestro stream modela _procedencia verificable de un run_. Forzar lo segundo dentro de lo primero sería el mismo error que "MCP como contrato universal" (nota 06). AG-UI queda anotado para cuando el Studio gane superficie conversacional (Fase 2), como protocolo del canal _interactivo_ — nunca del canal de procedencia.

### 1.2 El contrato SSE Studio↔Engine

- **Endpoint:** `GET /runs/{run_id}/events` (SSE). Reconexión con `Last-Event-ID: <global_seq>` → catch-up desde el cursor (nota 01, patrón notify-then-catchup: cero eventos perdidos).
- **Forma de cada mensaje SSE:** `id:` = `global_seq` · `event:` = el `type` del evento del run · `data:` = JSON del evento **proyectado para UI** (subset del Event completo: sin prev_hash/hash, payload ya resuelto). El Studio nunca ve eventos crudos de otros streams (proyección, no fuente).
- **Autenticación:** JWT (nota 08) — `EventSource` no permite headers custom → token por cookie o query param firmado de corta vida; señalado para la sesión de seguridad del API (carril Steven + auditoría semana 2).

### 1.3 Payload mínimo por vista (del doc CHIMERA-Studio-Frontend §2)

| Vista                         | Eventos que consume                                          | Payload mínimo                                                                                                                                                                                  |
| ----------------------------- | ------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Run en vivo (timeline)**    | todos los del stream, en orden                               | `{global_seq, type, actor_id, occurred_at, step_id?, resumen}`                                                                                                                                  |
| **Inspector de paso**         | `tool.invoked`, `capability.job.*`, `verification.completed` | por paso: capability_id, input/output digest, y la **attestation completa** (rung, verdict, method, evidence)                                                                                   |
| **Visualizador de red**       | `verification.completed` + resultado del paso de partición   | `{topology_ref, islands[{id, bus_ids, verification:{verdict, rung, anchor_kind, method, summary}}], cut_branch_ids[], cut_cost}` — **exactamente la forma validada por el spike** (`ieee14.ts`) |
| **Certificado**               | `run.completed` + emisión del certificado                    | el envelope DSSE completo (nota 02) — se renderiza legible, se ofrece como descarga JSON                                                                                                        |
| **Ablación**                  | métricas por run (nota 05)                                   | `{variant: quantum\|classical, cut_cost, wall_ms, verification_latency_ms}` × 2 runs                                                                                                            |
| **Explorador de procedencia** | stream completo paginado por `global_seq`                    | Event proyectado + filtros por type/actor                                                                                                                                                       |

La regla de la UI ("el nivel de confianza SIEMPRE visible") se traduce a contrato: **todo payload que represente un resultado lleva su bloque `verification` embebido** — la UI no puede renderizar un resultado sin badge porque el dato no llega sin él.

### 1.4 Hallazgos del spike (`apps/studio/src/spike/`)

Construido: Cytoscape.js con IEEE-14 (topología estándar, 14 buses / 20 líneas, layout preset), partición 2 islas coloreadas (A: buses 1–5, B: 6–14), 3 aristas de corte punteadas en rojo, **overlay de badges por isla** (verdict + escalón, posicionado por `renderedBoundingBox` y re-anclado en pan/zoom) + panel lateral con attestations del run y nivel agregado. Base Tailwind v4 (plugin Vite) + componentes convención shadcn (Badge/Card con variantes).

**Verificado 2026-07-03:** `pnpm build` verde (tsc estricto + vite, 1.5s) · `pnpm lint` verde (`--max-warnings=0`) · `pnpm arch` (dependency-cruiser INV-1) verde — 14 módulos, 0 violaciones. Verificación visual: `pnpm -C apps/studio dev`.

1. **Cytoscape validado** ✅ — API directa (sin wrapper React: el ciclo de vida manual con `useEffect`/`destroy` es trivial); tipos TS incluidos en el paquete (⚠️ `@types/cytoscape` es un stub deprecado — NO instalarlo); layout `preset` con coordenadas del diagrama estándar se ve legible sin tuning.
2. **Overlay HTML sobre el canvas** ✅ — badges como divs absolutos sincronizados con `pan zoom resize` es suficiente y mantiene los componentes UI en React/Tailwind (no en el canvas) — accesible y estilable.
3. **Tailwind v4 + convención shadcn** ✅ — `@tailwindcss/vite` sin config file; componentes por variantes funcionan; el `shadcn init` completo (components.json, Radix) queda para el build real del Studio.
4. **Supply-chain gate del repo** ⚠️ — `minimumReleaseAge: 20160` (14 días) en `pnpm-workspace.yaml` bloqueó la instalación (rollup 4.62.2 ya lockeado tiene ~13.9 días). Se instaló con override puntual de CLI (`--config.minimumReleaseAge=0`) y se verificó a mano que TODO lo nuevo cumple la política: cytoscape 3.34.0 (31 días), tailwindcss/@tailwindcss/vite **4.3.1** (21 días — se evitó 4.3.2 de 4 días). El lockfile de rollup no se tocó; en ~1 día el conflicto desaparece solo.
5. **Peso del bundle** ⚠️ — cytoscape empuja el chunk a ~597 KB (192 KB gzip); para el Studio real: `manualChunks` o import dinámico de la vista de red. No bloquea el spike.
6. **El dato que la vista exige** → ya reflejado en §1.3: la vista de red necesita el bloque `verification` POR ISLA, no solo el global — eso baja al contrato de payload.

## 2 · Decisión

| Referencia                                   | Decisión                                                            | Racional                                                           |
| -------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------ |
| SSE simple (`EventSource` + `Last-Event-ID`) | **portar** (patrón estándar, cero deps)                             | §1.1; mapea al cursor global; reconexión gratis                    |
| AG-UI                                        | **descartar** este mes / candidato Fase 2 para el canal interactivo | MIT, activo; vocabulario de chat-agente, no de procedencia         |
| assistant-ui / CopilotKit                    | **descartar** este mes                                              | Componentes de chat; el Studio no es un chatbot (Studio doc §8)    |
| Cytoscape.js (API directa)                   | **integrar** ✅ (instalado; validado por el spike)                  | MIT; tipos propios; el grafo es objeto de análisis, no solo dibujo |
| react-cytoscapejs (wrapper)                  | **descartar**                                                       | El ciclo de vida manual es trivial; una dep menos                  |
| Tailwind v4 + convención shadcn              | **integrar** (4.3.1) / `shadcn init` completo en el build real      | Validado por el spike; velocidad + pulido                          |

## 3 · Licencias

| Pieza                                 | Licencia                               | Verificado                    |
| ------------------------------------- | -------------------------------------- | ----------------------------- |
| Cytoscape.js 3.34.0                   | **MIT**                                | ✅ (metadata npm, 2026-07-03) |
| tailwindcss / @tailwindcss/vite 4.3.1 | **MIT**                                | ✅ (npm)                      |
| AG-UI                                 | **MIT** (sin dependencia — descartado) | ✅ en vivo                    |
| SSE / EventSource                     | estándar web (WHATWG)                  | —                             |

## 4 · Impacto en contrato

1. **Endpoint SSE** `GET /runs/{run_id}/events` con `id = global_seq`, `event = type`, reanudación por `Last-Event-ID` (frontera con Steven: la ruta es del API; la forma del stream y el cursor son de este plano — señalado).
2. **Payloads por vista** (§1.3) — en particular: el resultado de partición DEBE llevar `verification` por isla; el certificado viaja como envelope DSSE completo; las métricas de ablación como evento.
3. **Regla de contrato UI:** ningún payload de resultado sin bloque `verification` — la honestidad enforzada por forma de dato, no por disciplina de frontend.
4. **Autenticación del stream** (cookie/param firmado) — decisión de implementación para la sesión del API; el claim set es el de la nota 08.
5. **Stack del Studio congelado:** Cytoscape (red), SSE nativo (stream), Tailwind+shadcn (UI). React Flow (árbol de descomposición) y Recharts (ablación) quedan preseleccionados sin validar — no bloquean el freeze.

## 5 · Reconciliación contra la base lógica

- **INV-1 (Studio solo por API/gatewayClient):** INTACTO — el spike no agrega ningún egress (datos estáticos; dependency-cruiser verde); el SSE real entrará como método del gatewayClient.
- **Read-only sobre la verdad del Engine:** REFORZADO — el contrato SSE entrega proyecciones, jamás la tabla cruda; el Studio no puede mutar nada porque no existe endpoint de mutación en su contrato.
- **"Nivel de confianza siempre visible":** convertido de principio de UI a **regla de forma del payload** (§4.3).
- **Ninguna referencia contradijo la base lógica.** AG-UI empuja a que la UI participe del loop del agente (estado compartido bidireccional) — dato sobre AG-UI: útil para copilots, contrario a un Studio que es superficie de verificación read-only.
