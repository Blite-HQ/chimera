# Cobertura del diseño existente vs backlog Planeado — validación pre-research

> **Estado: VIGENTE (2026-07-24).** Validación pedida por Dylan antes del research:
> ¿cuánto del backlog Planeado v2 ya está contemplado en el diseño (freeze, arquitectura,
> knowledge, ratificaciones)? Ejecutada con tres auditorías paralelas sobre `mvp/base`.
> Referencias exactas por sub-pieza en los reportes de sesión; aquí el consolidado.

## Veredicto global

**La intuición de Dylan es correcta: la mayor parte de Planeado YA está diseñada** —
en muchos casos decidida, congelada y hasta construida. Lo que falta se concentra en
tres frentes de research genuinos (agencia, ingesta, informe) y **un choque de contrato
que hay que resolver explícitamente antes de construir P4**.

## Matriz consolidada

| Ítem                  | Cobertura                                | Ya contemplado (dónde)                                                                                                                                                                                  | Hueco real                                                                                                                                                                                                                                                                          |
| --------------------- | ---------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| P1 honestidad Studio  | **Alta**                                 | seam fixtures↔live (`env.ts`), egress único (`gatewayClient`, INV-1), patrón live en `loadCertificate`                                                                                                  | ramas live en 6 queries; banner "Replay" (cero semilla de UI)                                                                                                                                                                                                                       |
| P2 compose live       | **Alta** (bug, no diseño)                | compose canónico O6; nginx ya proxea `/runs`                                                                                                                                                            | threading de `VITE_API_URL` en build; OJO: conviven DOS env vars (`VITE_GATEWAY_URL` ≠ `VITE_API_URL`) — cablear solo la primera no enciende nada                                                                                                                                   |
| P3 API-driven         | **Media**                                | formas de payload por vista CONGELADAS (§9, trust/07: 6 vistas, verification por isla); SSE + certificado especificados                                                                                 | las RUTAS: GET /runs, artifacts, knowledge, step-evidence, ablation, topología no tienen spec ni egress                                                                                                                                                                             |
| P4 agente real        | **Media (borde) / Baja (corazón)**       | ModelServer/replay DECIDIDO (§15.7, ratificado Steven), eventos `model.call.*` (§3), sub-runs+claims al raíz DECIDIDO (§13, 3 reglas), puerto `ModelPort` sembrado en código                            | el LOOP QUE PLANIFICA: ver "el choque de contrato"; adapter LiteLLM sin construir; 5 huecos de research abajo                                                                                                                                                                       |
| P5 paridad generativa | **Alta en ciencia / Nula en ingesta**    | QUBO+QAOA(Aer+seed)+GW/greedy/exacto+estadística ≥5 semillas: CONSTRUIDOS como capabilities; identidad digest+proveniencia congelada (§15.3); campos multi-backend por pata DISEÑADOS (§11, quantum/08) | capability de INGESTA GeoJSON→grafo = hueco total (ni claim schema ni código); importador de las 19 corridas Nexus; `ConsensusReplicationPredicate` no carga los campos §11 (`backend_id`, `job_id`, `counts`…); SA ausente (greedy ya cumple "GW + ≥1" — propuesta: SA a Mejorado) |
| P6 informe            | **Alta en sustrato / Nula en mecanismo** | deliverables `{artifact_ref, digest}` anti-TOCTOU (§7), ContentStore (§12), `assemble.py` ya acepta bytes, verify-bundle punto 3 los valida                                                             | el ENSAMBLADOR no existe en ningún diseño: PDF ≤8p desde resultados certificados + binding cifra→certificado; pregunta abierta: ¿capability "report" o capa de plataforma?                                                                                                          |
| P7 visual             | **Alta en grafo / Nula en geo**          | Cytoscape + badges por isla + payload de partición con verification POR ISLA: decidido y spikeado                                                                                                       | TODO lo geográfico: sin GeoJSON en Chimera (vive en `reto1-vanilla`), sin coordenadas en payloads ("model space"), sin librería de mapas; r vs p existe como PNG de script, no como vista                                                                                           |
| P8 escalado           | **Alta**                                 | escalera congelada (§15.3): ieee14 construido, ieee30 doble-ancla (Sebas), doctrina de extrapolación 26-qubits decidida                                                                                 | cr6/cr8 dentro de Chimera (ratificación Sebas pendiente, §1.9); red ICE 70 nodos como instancia; generador del artefacto de extrapolación                                                                                                                                           |

## El choque de contrato (resolver ANTES de construir P4)

La Fase 1 congeló deliberadamente lo contrario del mandato:

- freeze §13: "el loop (**pipeline fijo en Fase 1**)"; sub-runs fijados como
  formular/QAOA/baseline/verificar; `loop.py:1-9` lo materializa ("NO ReAct, NO
  plan-execute").
- Ratificación runtime 23-jul (#4): "el golden path del demo **no invoca modelos**;
  ModelServer/replay DIFERIDO deliberadamente".
- La arquitectura VIGENTE (`arquitectura-reconciliada.md` §2.1) dice lo contrario del
  freeze: "no es un pipeline… el modelo elige en runtime". La tensión ya vivía en los
  docs; P4 la vuelve inevitable.

**Resolución requerida:** supersede formal de "pipeline fijo Fase 1" → "loop agéntico
Planeado" registrado en `decisiones.md`, ratificación de Steven (es su plano), y diseño
del loop ANTES de tocar `loop.py`. Colaterales a resolver en el mismo acto: §8 prohíbe
re-entrada al gateway (replanificación la necesita), y el set de sub-runs deja de ser
fijo (el agente lo elige — de paso limpia el roce con la regla de agnosticismo).

## Fricciones menores (con dueño)

1. **P6 vs `05-entregable.md`** (informe a mano, CERRADO): P6 lo supersede; mientras el
   ensamblador no exista, el camino a mano sigue siendo el fallback del entregable.
2. **Corpus clavado en 8 archivos** (`verify_corpus_digests.py` + tabla §15.3): agregar
   cr6/cr8 exige actualizar guard + re-estampar tabla + **ratificación de Sebas** (§1.9).
3. **Egreso a Nexus**: cr8 es clase pública (datos abiertos, pesos proxy) → doctrina
   §15.1 lo permite; pero la guarda `anchor_requires_unauthorized_egress` es semilla —
   cualquier orquestación qnexus futura debe pasar por Policy de clase-de-dato.
4. **SSE sin vocabulario de agente**: §9/trust-07 descartaron chat (AG-UI Fase 2); P4
   necesita payloads nuevos (plan del agente, turnos) — extensión del contrato, no
   violación.
5. **trust/18 arrastra vocabulario `rung`** ya migrado en código (ET-9): nota de limpieza.

## Agenda de research (lo que de verdad no está diseñado)

| #   | Frente                                              | Alcance                                                                                                                                                                                                                                                                                                                                                                      |
| --- | --------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| R1  | **Loop agéntico** (P4)                              | misión NL → plan estructurado como artefacto con digest; control del loop (terminación, replanificación-ante-fallo, reintentos con efectos); prompt del planner replay-determinista (catálogo de capabilities inyectado); grabación de una SESIÓN agéntica completa como fixture (el replay §15.7 es por-llamada, no por-sesión); contrato conversacional mínimo (turno→run) |
| R2  | **Capability de ingesta** (P5)                      | GeoJSON/CSV → grafo ponderado con digest+proveniencia como capability genérica + su `claim_type`/schema en el perfil STEM (generalizar `build_cr_instances.py` del espejo, no copiarlo)                                                                                                                                                                                      |
| R3  | **Evidencia multi-backend + importador Nexus** (P5) | ampliar `ConsensusReplicationPredicate` a los campos ya diseñados en §11/quantum-08; importador de corridas pre-ejecutadas (job_id, counts, `seeds.sampler:"unsupported"`)                                                                                                                                                                                                   |
| R4  | **Ensamblador de informe** (P6)                     | PDF ≤8p generado desde resultados certificados, cada figura/cifra ligada a `claim_digest`/`deliverable.digest`; decidir: capability vs capa; el PDF entra al bundle como deliverable (el sustrato ya lo soporta)                                                                                                                                                             |
| R5  | **Capa geográfica** (P7)                            | coordenadas/proyección en el payload de red (extensión §9), librería de mapa compatible con el design system, GeoJSON del ICE importado con digest; vista r vs p en el Studio                                                                                                                                                                                                |
| R6  | **Specs de endpoints** (P3)                         | rutas + contratos de GET /runs, artifacts, knowledge, step-evidence, ablation, topología/partición (las formas §9 ya existen; falta la ruta)                                                                                                                                                                                                                                 |

Orden sugerido: R6 y R3 son mecánicos (diseño corto, desbloquean P1–P3 y P5); R2 y R4
son diseño mediano; R1 es el research profundo y toca contrato congelado (empezar por el
supersede); R5 corre en paralelo con el design system.
