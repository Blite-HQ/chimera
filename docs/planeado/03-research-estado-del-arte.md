# Research de estado del arte — el resultado ideal por frente (R1–R6)

> **Estado: VIGENTE (2026-07-24).** Segunda mitad del research pre-Planeado: cómo lo hace
> la industria y cuál es el resultado ideal, aterrizado a las restricciones de Chimera
> (event-sourced, replay determinista, DSSE offline, capabilities agnósticas). Tres
> investigaciones con fuentes primarias (URLs clave inline; el detalle completo vive en
> los reportes de la sesión 2026-07-24). Complementa `02-cobertura-diseno.md`.

## Las tres tesis transversales

1. **Chimera ya construyó un motor de durable execution sin llamarlo así.** El stream
   append-only por run ES el "Event History" de Temporal; `provenance_hash` es la
   integridad del journal; los sub-runs son child workflows. No se adopta ningún motor:
   se formaliza el contrato que falta (abajo, R1). DBOS Transact (durable execution =
   librería + tu propio Postgres) es la validación externa de que este diseño es de
   producción — citarlo en el pitch técnico.
2. **Ingesta, evidencia externa e informe colapsan en UN patrón**: instancia con digest
   - receta de derivación en `provenance` + attestation DSSE. R2 define la receta; R3 es
     el caso donde la activity corre en un tercero (predicado estilo SLSA con `builder.id`
     externo); R4 es una derivación cuyo output es un PDF determinista. Cero maquinaria de
     confianza nueva; tres capabilities genéricas nuevas.
3. **En la UI no se adopta ningún protocolo externo — se proyecta.** El stream es más
   fuerte que AG-UI/Vercel AI SDK (ellos son transporte, el nuestro es fuente de verdad
   certificada). Se adoptan sus _vocabularios_ (start/delta/end, IDs estables,
   aprobaciones tipadas) y el semconv OTel GenAI como proyecciones derivadas del stream.

## R1 — El harness agéntico ideal

La industria convergió: **loop plano, sofisticación en el harness** (no en grafos).
Claude Code/OpenAI = while-loop donde el modelo propone y el harness ejecuta; Google ADK
= cada iteración emite eventos inmutables (la forma que Chimera ya tiene); LangGraph/MAF
= grafos estáticos (descartados: hardcodearían dominio contra el registry dinámico).

**El contrato a formalizar (los 5 componentes):**

1. **Loop**: `proponer → gobernar (8 etapas) → ejecutar → journalizar → verificar →
repetir`; el modelo propone, el harness es el único que ejecuta. Cada transición =
   evento inmutable.
2. **Plan como artefacto en el stream**: `plan.created` con ítems
   `{id, description, verification, status}` (patrón feature-list de Anthropic +
   `write_todos` de deepagents); el agente solo emite `plan.item_updated`; replanificar
   = append con causa. La historia del plan queda dentro del certificado.
3. **Terminación triple**: `max_turns` (~30 default, patrón OpenAI) + budget
   tokens/costo declarado al crear el run + **gate de verificación** ("done" solo si el
   verifier pasa — doctrina Anthropic); agotar budget cierra `exhausted`, jamás "done"
   implícito.
4. **Replay por digest con detección de no-determinismo** (la pieza Temporal que falta):
   ensayo journaliza `(request_digest canónico, resultado)` por CADA efecto (LLM call y
   capability); demo sirve por digest; mismatch ⇒ evento `replay.divergence` tipado ⇒ el
   certificado NO verifica. Propiedad resultante, exclusiva de Chimera: **el certificado
   DSSE verifica ⟺ el replay fue fiel**. (Lección langchain-replay: grabar decisiones
   del modelo en la frontera del router — donde ya está `MODEL_ROUTER_BACKEND` — no HTTP;
   vcrpy/cassettes descartados.)
5. **Gobernanza con semántica tripwire**: veredictos de guardrail/authz como eventos
   tipados con causa (no excepciones opacas); policies registradas y versionadas por
   digest como capabilities; aprobación humana con la forma elicitation de MCP (evento
   con JSON Schema, respuesta como evento, replay-able).

Observabilidad: proyector `stream → OTel GenAI` (`invoke_agent`/`chat`/`execute_tool`);
el timeline observado es exactamente lo certificado. Sin SDKs de instrumentación de
terceros dentro del runtime.

Descartes explícitos: Temporal/Restate como runtime (journal duplicado que competiría
con el stream), LangGraph/MAF como motor, CrewAI, vcrpy a nivel HTTP.

Fuentes clave: anthropic.com/engineering/effective-harnesses-for-long-running-agents ·
openai.github.io/openai-agents-python · google.github.io/adk-docs/events ·
github.com/dbos-inc/dbos-transact-py · github.com/sixty-north/langchain-replay.

## R2 — La capability de ingesta ideal

**Dos instancias, no una**: (1) el snapshot crudo como blob inmutable con
`sha256(bytes)` y provenance `{kind: "external-source", uri exacta, retrieved_at, …}` —
crítico porque los FeatureServer de ArcGIS del ICE son mutables y paginados: el ancla es
el snapshot, jamás la URL; (2) la instancia derivada con **receta estilo `dvc.lock` en
vocabulario PROV** dentro de `provenance`:
`{kind: "derivation", inputs: [{ref, digest}], recipe: {capability, version,
params_digest, code_ref}, run_id, assertions: [...]}`.

- Validación en frontera DENTRO de la receta: `geojson-pydantic` (RFC 7946) para geo,
  `pandera` para tabular; el resultado entra como `assertions` (idea del facet
  `dataQualityAssertions` de OpenLineage) — el certificado puede afirmar "pasó el
  contrato X".
- Determinismo del digest: ordenar features por ID estable, no reformatear floats de
  coordenadas (ojo al round-trip JCS/ECMAScript), una sola puerta de canonicalización.
- Descartes: DVC/lakeFS como infra (el event store + digests ya son un CAS con
  historia), PROV-O/RDF completo, Great Expectations. Croissant queda como export de
  publicación post-hackathon (sale casi gratis).

Fuentes clave: doc.dvc.org (dvc.lock) · slsa.dev/spec/v1.0/provenance ·
openlineage.io/docs/spec/facets · mlcommons.org (Croissant).

## R3 — Evidencia externa (corridas Nexus) ideal

Patrón **"evidencia importada con cadena de custodia"**, tres capas:

1. **Blob crudo**: respuesta de la API de Nexus, digest sobre bytes.
2. **Instancia normalizada**: `BackendResult.to_dict()` de pytket → esquema propio de
   counts con `bit_order` EXPLÍCITO (el footgun endianness Qiskit↔pytket) + backend +
   `{noisy_simulation, error_params}` → JCS → digest.
3. **Attestation de importación**: forma in-toto Statement v1 con predicado propio
   modelado sobre SLSA v1 — `externalParameters` (circuito+shots pedidos),
   `resolvedDependencies` (circuito compilado, modelo de ruido),
   `builder.id: "nexus://quantinuum/H2-1E"`, `invocationId: <job_id>`, timestamps —
   firmada con el DSSE/Ed25519 existente, entra por `deliverables` sin tocar el runtime.

Honestidad documentada: la firma atesta _quién importó, qué y cuándo_; la custodia
criptográfica termina en la API de Nexus (mismo modelo de confianza que SLSA en
`builder.id`); `job_id`+proyecto permiten re-consulta cruzada por terceros.

**Seguridad**: JAMÁS deserializar evidencia externa con `RuntimeDecoder` de Qiskit
(advisory GHSA-x4x5-jv3x-9c7m, ejecución de código arbitrario) — conversores planos.
Descartes: Sigstore/Rekor (overkill), QIR.

## R4 — El informe ideal

**El informe es una derivación más** (reutiliza R2 íntegro):

- Cada figura = instancia derivada (capability de plotting: instancias certificadas +
  params → PNG/SVG con digest y receta). Determinismo matplotlib: `svg.hashsalt` fijo +
  `SOURCE_DATE_EPOCH`.
- El PDF = derivación final con **Typst** (`typst-py`, ~300ms, sin toolchain LaTeX):
  plantilla versionada con digest + figuras + cifras → `typst.compile()` con
  `set document(date: none)` ⇒ **PDF byte-reproducible y digestable** (LaTeX/Quarto no
  dan eso). Verificar el informe = recompilar y comparar digests + DSSE offline.
- Trazabilidad visible (patrón showyourwork): cada figura/cifra con
  `sha256:… · cert:<id>` al pie; anexo de verificación con la tabla
  artefacto→digest→certificado.
- Descartes: LaTeX (peso), Quarto/papermill en el camino certificado (autoría humana,
  no determinista), C2PA (vigilar, no adoptar); WeasyPrint solo fallback.

Fuentes clave: show-your.work · github.com/messense/typst-py · peps.python.org/pep-0740.

## R5 — La superficie visual ideal

**Mapa (orden de construcción decidido: fallback primero):**

- **Primero (S, ~0.5 día, garantía del día D)**: mapa abstracto-geográfico SIN basemap —
  silueta de Costa Rica (Natural Earth GeoJSON) proyectada con `d3-geo` `fitSize()` a
  SVG con tokens del design system; red, hulls de islas y badges como SVG. Cero tiles,
  cero riesgo air-gap, estética 100% nuestra (estilo locator-map NYT/FT).
- **Upgrade (M, ~2 días)**: `maplibre-gl` + `react-map-gl@8/maplibre` +
  `pmtiles@4` + `@protomaps/basemaps@5` flavor `black` re-tokenizado;
  `pmtiles extract --region=cr` (decenas de MB, servible por el propio nginx del
  compose); **glyphs/sprites self-hosted** (el fallo silencioso clásico del air-gap —
  probar con red cortada); atribución ODbL visible.
- Patrón de capas (validado por OpenInfraMap, que es MapLibre): líneas color-por-isla y
  ancho-por-kV, subestaciones circle/symbol, islas como hulls (`turf`) con fill 0.08–0.12,
  badges = `maplibregl.Marker` montando el `AssuranceBadge` existente. Estados vivos vía
  `setFeatureState`.
- La vista topológica Cytoscape SE MANTIENE: el dual "diagrama + mapa" es el patrón
  PowSyBl. Descartes: deck.gl (escala no lo justifica), Leaflet (raster vs dark-first),
  `@powsybl/network-viewer` como dep (MUI/emotion chocan con shadcn — solo referencia
  UX), kepler.gl.

**Dataviz r vs p (S, ~1 día)**: Recharts (ya instalado ^3.8) vía `ChartContainer` shadcn:
`ComposedChart` + `Scatter` con `<ErrorBar>` `[lo, hi]` + `<ReferenceLine>` dasheadas por
baseline (GW/greedy/exacto), colores `--chart-*`; tabla de comparación estilo W&B Run
Comparer al lado (shadcn Table). Descartes: ECharts (rompe regla wrapper), visx,
Observable Plot. Ojo: mantener `ErrorBar` en configuración estándar (historial de bugs
en configs exóticas).

**UX agéntica (M, 1–2 días + scrubber)**: plan-checklist viva (Claude Code) + cards por
paso colapsadas con drill-down a evidencia (Devin) + **scrubber de replay del timeline**
(Manus) — casi gratis sobre el catch-up `Last-Event-ID` existente y es la feature UX que
más directamente vende el plano de confianza: replay verificable con hash. Aprobación
humana como par de eventos propios con card inline bloqueante (semántica
`tool-approval-request/response` de Vercel, patrón Operator). Reducer del cliente con
convención start/delta/end e IDs estables (`stepId`/`jobId`), transiciones
`pending→running→ok|failed`.

## R6 — Endpoints

Sin research externo necesario: REST plano coherente con lo existente (`GET /runs`,
`GET /runs/{id}/…` por vista §9), especificado en `docs/specs/` con el mismo formato de
`confianza-api-sse.md`. Las formas ya están congeladas; falta solo la ruta y el egress.

## Riesgos puntuales acumulados

1. Glyphs/sprites de mapa por CDN = fallo silencioso del air-gap (probar sin red).
2. `RuntimeDecoder` de Qiskit sobre JSON externo = CVE (conversores planos siempre).
3. Floats de coordenadas en JCS (formato ECMAScript) — preservar valor fuente.
4. `maplibre-gl@6` es major reciente — `^5` es la versión de guerra si algo cojea.
5. ODbL: atribución visible si entra basemap OSM.

## Aterrizaje: de research a specs

Cada frente produce ahora su spec ejecutable en `docs/specs/` (formato existente,
autoridad: el freeze + este doc): (1) `harness-agentico.md` — el contrato de los 5
componentes R1 + el supersede de "pipeline fijo" que requiere ratificación de Steven
(`02-cobertura-diseno.md` §choque); (2) `capability-ingesta.md` (R2); (3)
`evidencia-externa.md` (R3); (4) `informe-derivado.md` (R4); (5) `superficie-visual.md`
(R5, incluye payloads de plan/aprobación que extienden §9); (6) `endpoints-studio.md`
(R6). Con specs aprobadas arrancan las sesiones de implementación por dominio.
