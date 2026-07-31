# Spec — capability de ingesta: snapshot + receta de derivación (costura B↔A, R2)

**Gobernada por:** freeze §1 (`CapabilityManifest` v2) · freeze §3 (vocabulario `capability.job.*`)
· freeze §12 (`Artifact`/`ContentStore`) · freeze §14 (`●ClaimEmitted`) · freeze-anexo-canonicalización
§2 (`C(x)`) · `perfil-stem-v1-0.md` §1 (registro `claim_type`) · **Dueño:** Sebas+Dylan ·
**Estado:** SPEC (2026-07-24)

> Insumo: `docs/planeado/03-research-estado-del-arte.md` §R2 · `knowledge/execution/10-rag-cag-knowledge-ingestion.md`
> (mismo sustrato `Artifact`/`ContentStore`, mismo principio "recuperado ≠ decisorio" aplicado aquí a
> "ingerido ≠ ancla") · `knowledge/trust/06-protocolos-capability-mcp-a2a.md` §1.2/§1.4 (los dos ejes del
> manifest, el vocabulario `capability.job.*`).

## Contrato

**Cero maquinaria de confianza nueva (R2):** esta spec no crea un almacén, un algoritmo de digest ni un
verificador nuevo. Reutiliza tal cual `ContentStore.put/get/stat` (freeze §12), `C(x)` (el ÚNICO gate de
canonicalización — `blite/certificate/canonical.py`, freeze-anexo §2) y el vocabulario `capability.job.*`
(freeze §3). Lo único nuevo son DOS instancias de datos y su receta.

### Dos instancias, no una

1. **Snapshot crudo** — blob inmutable. Se ingiere con `ContentStore.put(bytes_de_la_respuesta,
media_type, ctx) -> Artifact`; el digest **es** `sha256` sobre los bytes exactos recibidos del
   FeatureServer (ContentStore no canonicaliza contenido opaco — Regla 1 del anexo aplicada por
   analogía: los bytes tal cual, jamás una re-serialización). **El ancla es el snapshot, JAMÁS la URL**:
   los FeatureServer ArcGIS del ICE son mutables y paginados — dos fetches a la misma URL en instantes
   distintos son evidencia distinta con digests distintos, y eso es correcto, no un bug.
   **[S3 2026-07-30]** (ejemplo de dominio Reto-1 — no forma del contrato: la regla genérica
   es «el ancla es el snapshot, jamás la fuente mutable»; ArcGIS/FeatureServer del ICE es el
   caso del reto que la justifica, no parte del contrato — censo §4.)
2. **Instancia derivada** — el resultado de una capability de derivación (p. ej. "convertir el
   FeatureServer crudo en un grafo de topología") **más su receta**, en vocabulario PROV/`dvc.lock`:

   ```
   Provenance =
     | ExternalSourceProvenance {kind: "external-source", uri, retrieved_at,
                                  content_type?, http_status?}
     | DerivationProvenance      {kind: "derivation",
                                   inputs: [{ref: str, digest: str}, ...],
                                   recipe: {capability: str, version: str,
                                            params_digest: str, code_ref: str},
                                   run_id: str,
                                   assertions: [DataQualityAssertion, ...]}

   DataQualityAssertion = {name: str, passed: bool, detail: dict | None}
   ```

   `Provenance` es una unión discriminada por `kind` (Pydantic, `frozen=True, extra="forbid"`) — módulo
   NUEVO `engine/src/blite/verification/provenance.py` (Fase 1, Sebas+Dylan; no existe hoy).
   **[S3 2026-07-30]** Existe (D-N7): `engine/src/blite/verification/provenance.py` está en el
   árbol con la unión `Provenance` — el «no existe hoy» quedó histórico. **No se
   agrega ningún campo a `Artifact`** (freeze §12 queda intacto): la `Provenance` se canonicaliza con
   `C(x)` y se guarda ELLA MISMA vía `ContentStore.put()` — hereda digest/identidad gratis, sin sustrato
   nuevo. La "instancia" completa es el par `{artifact: Artifact, provenance_digest: str}`; ese par viaja
   como payload adicional (aditivo, freeze §3 no lo prohíbe) de `capability.job.completed
{output_digest, provenance_digest}`.

### Validación en frontera, DENTRO de la receta

El `recipe.capability` de una `DerivationProvenance` ejecuta su propia validación de forma ANTES de
declarar la instancia derivada válida: **`geojson-pydantic`** (RFC 7946) para geometría, **`pandera`**
para tabular. El resultado — pase o falle — entra como `assertions` (mismo espíritu que el facet
`dataQualityAssertions` de OpenLineage citado en R2): el certificado puede afirmar "esta derivación pasó
el contrato de forma X", nunca "confía en que pasó".

**[S3 2026-07-30]** (ejemplo de dominio Reto-1 — no forma del contrato: la forma genérica es
«la receta valida en frontera y registra `assertions`»; qué librería concreta valida qué —
geoespacial/tabular — es del dominio de la capability, no del contrato de ingesta — censo §4.)

### Determinismo del digest (la regla que rompe silenciosamente sin disciplina)

1. **Ordenar features por un ID estable** antes de canonicalizar — un FeatureServer paginado no
   garantiza orden de iteración estable entre páginas/corridas; sin este paso, dos fetches del MISMO
   dataset producen digests distintos por puro orden de llegada, no por contenido.
2. **NO reformatear floats de coordenadas** — la canonicalización de números (`C(x)` §2 del anexo) YA
   resuelve el round-trip JCS/ECMAScript (shortest round-trip, banda `[1e-6,1e-4)` fija); reformatear
   coords ANTES de pasarlas por `C(x)` (redondeo "cosmético", notación distinta) es una segunda
   canonicalización no auditada que puede divergir de la primera.

   **[S3 2026-07-30]** (ejemplo de dominio Reto-1 — no forma del contrato: «features» y
   «coordenadas» son el caso GIS del reto; la regla genérica de los puntos 1-2 es «orden
   estable por ID antes de canonicalizar, y una sola canonicalización — jamás reformateo
   previo del dato» — censo §4.)

3. **Una sola puerta de canonicalización**: toda instancia derivada de esta spec pasa por
   `blite.certificate.canonical.canonicalize` — el MISMO gate que `provenance_hash`/`claim_digest`. Cero
   copias derivadas (la lección `SF-P1-1` del anexo: una segunda copia del formateo de floats es
   exactamente el modo de falla que ya mordió una vez).

### `claim_type` — extensión ADITIVA del perfil STEM

`perfil-stem-v1-0.md` §1 ya registra `derivation` (kernel, extendido: "plantillas de inferencia
científica registradas"). Esta spec **propone** agregar `ingestion` como fila nueva del mismo registro
(schema mínimo: `{source_ref: digest, provenance_digest: digest}`, techo AL3 — mismo patrón que
`simulation_result`). **No se edita `perfil-stem-v1-0.md` en esta sesión** (documento CONGELADO,
importado S-E): la fila queda propuesta aquí, a **ratificar por su dueño (Dylan) en Fase 1**, mismo
patrón que el resto de ítems `[S-F]` pendientes de ratificación de este repo. `derivation` se usa tal
cual ya está registrado — cero cambio ahí.

### Dos capabilities nuevas, `CapabilityManifest` v2

| id                               | `side_effects`        | `required_permission`               | `interaction`      | `execution_profile` | Propósito                                 |
| -------------------------------- | --------------------- | ----------------------------------- | ------------------ | ------------------- | ----------------------------------------- |
| `blite.ingesta.snapshot.fetch`   | `reversible-external` | `capability:ingest:external-source` | `job`              | `in-process` (hint) | Trae el snapshot crudo del FeatureServer  |
| `blite.ingesta.geojson.to_graph` | `pure`                | `capability:ingest:derive`          | `request_response` | `in-process` (hint) | Deriva topología/grafo del snapshot crudo |

**[S3 2026-07-30]** (ejemplo de dominio Reto-1 — no forma del contrato: los dos `id`
concretos y el output «topología/grafo» de la tabla son la instancia del reto — roza
ADR-029; la forma del contrato genérico es el par snapshot+derivación con manifest v2 —
censo §4.)

Paquete Fase 1: `capabilities/ingesta/src/blite_cap_ingesta/` (mismo patrón `blite_cap_<domain>` que
`blite_cap_sim`/`blite_cap_quantum`).

**[S3 2026-07-30]** Existe (D-N7): `capabilities/ingesta/src/blite_cap_ingesta/` está en el
árbol — el paquete dejó de ser «Fase 1» pendiente.

**DISCREPANCIA A FLAGGEAR (no es competencia de esta spec arreglarla):** `sdk/src/blite_capability/manifest.py`
hoy es un `@dataclass(frozen=True)` con `{id, description, input_schema, output_schema, version, tags}` —
**SIN** `side_effects`/`required_permission`/`interaction`/`execution_profile` (los 4 campos del freeze
§1). Esta spec **programa contra el manifest v2 congelado**, no contra el stub actual. El "carril de
Dylan" (actualizar `manifest.py` a Pydantic v2 con los 4 campos) es una dependencia pendiente de Fase 1,
compartida por TODAS las capabilities nuevas del plan — no exclusiva de ingesta.

### Interface con A (ejecución)

La ingesta corre como **sub-run** (o, si no amerita claims propios de camino crítico, como `RunStep` del
loop del run raíz — criterio de §13 del freeze: "es sub-run SOLO la unidad que produce claims propios que
el certificado citará"). Cada capability emite su rastro `capability.job.submitted/progress/completed|failed`
sin cambios de forma. La derivación emite un `●ClaimEmitted` con `claim_type ∈ {ingestion, derivation}`
(payload §14/§6, ya tipado en `engine/src/blite/verification/claim.py::ClaimEmittedPayload` — reutilizado
tal cual, sin campos nuevos en el evento).

## Interfaces con otros dominios

| Interfaz                                                                                 | Dominio                                     | Estado                                                                                                  |
| ---------------------------------------------------------------------------------------- | ------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| `CapabilityManifest` v2 (side_effects/required_permission/interaction/execution_profile) | A · ejecución (Registry/Dispatcher, Steven) | SPEC — discrepancia con `sdk/manifest.py` flaggeada arriba, pendiente Fase 1                            |
| `capability.job.{submitted,progress,completed,failed}`                                   | A · ejecución                               | VERDE (freeze §3, reutilizado sin cambio de forma; `provenance_digest` es campo aditivo del payload)    |
| `●ClaimEmitted{claim_type: ingestion\|derivation}`                                       | confianza (Dylan)                           | SPEC — `derivation` ya registrado (perfil §1); `ingestion` propuesto aquí, ratificación pendiente Dylan |
| `ContentStore.put/get/stat`                                                              | frontera (Dylan)                            | VERDE (freeze §12, reutilizado sin cambios)                                                             |
| `canonicalize()` / `C(x)`                                                                | confianza (Dylan)                           | VERDE (freeze-anexo §2, reutilizado — única puerta)                                                     |
| `assertions` → `PropertyRulePredicate` (evidence.py)                                     | confianza (Dylan)                           | SPEC — uso nuevo del predicate existente para dataQualityAssertions                                     |
| Run jerárquico / `parent_run_id` (§13)                                                   | frontera (Dylan+Steven)                     | VERDE (freeze §13, reutilizado — criterio step-vs-sub-run aplicado tal cual)                            |

## Fronteras (qué NO decide esta spec)

- No decide el Registry/Dispatcher (execution/04/06, Steven) — solo el manifest y los 2 `id` nuevos.
- No decide credenciales/cliente HTTP concreto contra ArcGIS ni su despliegue (infra, Geovanni).
- No re-implementa `canonicalize()`/`C(x)` — reutiliza la única puerta ya congelada.
- No decide el `dataset_id`↔digest final de `cr8`/`cr6` (§15.3 del freeze, corpus de islanding — otro
  corpus, otro dueño Sebas, otra spec); esta spec da el MECANISMO genérico de ingesta, no el dato.
- No ratifica por sí misma la fila `ingestion` en `perfil-stem-v1-0.md` §1 — queda propuesta, a decisión
  del dueño del perfil.
- No decide la forma final del cliente FeatureServer (paginación, reintentos) — eso es del `recipe.capability`
  concreto en Fase 1.

## Tests de contrato (fixtures de costura)

Convención de origen único (`docs/specs/README.md` §Fixtures de costura): el generador Python (Fase 1)
emitirá `tests/fixtures/contract/ingesta/snapshot-example.json` y
`tests/fixtures/contract/ingesta/derivation-example.json`, espejados a
`apps/studio/src/fixtures/contract/ingesta/*.json`. **Declarados aquí, NO generados en esta sesión** — el
modelo `Provenance` que los produce todavía no existe (Fase 0 entrega contrato + seed xfail, no la
feature).

**[S3 2026-07-30]** Generados (D-N8): `tests/fixtures/contract/ingesta/{snapshot-example,derivation-example}.json`
y su espejo en `apps/studio/src/fixtures/contract/ingesta/` existen commiteados, y el modelo
`Provenance` que los produce vive en `engine/src/blite/verification/provenance.py` (D-N7) —
las dos afirmaciones del párrafo anterior quedaron históricas.

## Tests semilla

- `tests/seeds/test_seed_ingesta_receta.py` — `xfail(strict=False)`, Fase 1 Sebas+Dylan: fija la FORMA de
  `DerivationProvenance` (inputs/recipe/run_id/assertions) y el requisito de "una sola puerta de
  canonicalización".
