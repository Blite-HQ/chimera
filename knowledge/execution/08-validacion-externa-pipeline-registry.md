# Nota 08 — Validación externa del pipeline y del registry: MS AGT en vivo, middleware FastAPI/ASGI, Composio/Cerebrum como patrón de registry

**Ítem del plan (§4, Steven):** cerrar las tres referencias externas que el plan asignaba al plano de
ejecución y que las notas 01–07 no verificaron en vivo (su investigación derivó todo de los invariantes):
(a) el pipeline/chokepoint real del MS Agent Governance Toolkit contrastado contra las 7 etapas de la
nota 01, (b) cómo se implementa un pipeline de etapas sobre FastAPI/ASGI y qué NO debe ser middleware,
(c) Composio y Cerebrum como patrón de registry de tools (no su auth — eso ya lo cubrió trust/14).
**Fecha:** 2026-07-14 · **Estado:** decidida e incorporada al contract freeze (S-E 2026-07-18 —
el README del plano la lista en "Cerrado (S-E)"; encabezado alineado en S-F) — revisión final
de Steven en la ratificación, como el resto del plano
**Fuentes:** `microsoft/agent-governance-toolkit` — árbol del repo, `policy-engine/spec/SPECIFICATION.md`
(Agent Control Specification, ACS), `policy-engine/docs/integrations/litellm-proxy.md`, `LICENSE` raíz y
`policy-engine/LICENSE.acs` (**verificado en vivo 2026-07-14** vía `gh api`; el repo fue reestructurado
desde el clon de trust/09 del 2026-07-07 — `agent-mesh/` vive ahora bajo `agent-governance-python/`) ·
docs oficiales de Starlette (`starlette.io/middleware`) y FastAPI (`/tutorial/middleware/`,
`/tutorial/bigger-applications/`) (**verificado en vivo 2026-07-14**) · Composio: `docs.composio.dev`
(`tools-direct/toolkit-versioning`, `fetching-tools`) + `ComposioHQ/composio` (**verificado en vivo
2026-07-14**) · Cerebrum: `agiresearch/Cerebrum` (`cerebrum/manager/tool.py`, `cerebrum/config/config.yaml`,
`LICENSE`) y `agiresearch/AIOS` (**verificado en vivo 2026-07-14**) · `knowledge/execution/01` (las 7
etapas) · `knowledge/execution/04` (registry por entry points) · `knowledge/trust/09` (AGT, ángulo audit
chain/firma — esta nota cubre el ángulo pipeline, la mitad que trust/09 dejó señalada como "de Steven") ·
`knowledge/trust/14` (Composio como AUTH — no se duplica aquí) · `docs/invariants.md`

---

## 1 · Patrón / mecanismo

### 1.1 (a) MS AGT: el chokepoint real no es un pipeline lineal — son 8 intervention points sobre un host-PEP

La pieza pipeline del AGT es el **ACS** (`policy-engine/`, Rust, spec normativo propio en
`spec/SPECIFICATION.md`). Su forma, verificada en vivo:

- **Separación PDP/PEP explícita.** El runtime ACS es un _policy decision point_ puro: _"Intervention
  point evaluation performs no input or output of its own"_ — red, clasificadores, llamadas a modelo,
  llamadas a tool y ensamblado de streams pertenecen al **host**, que es el _policy enforcement point_.
  El host arma un **snapshot JSON completo** por punto y llama al runtime; el runtime devuelve un verdict.
- **8 intervention points** (spec §4), nombrados y cerrados — un punto desconocido falla cerrado con
  `runtime_error:intervention_point_unknown`:

  | Punto AGT         | Posición                                 | Etapa análoga de la nota 01                     |
  | ----------------- | ---------------------------------------- | ----------------------------------------------- |
  | `agent_startup`   | arranque de agente/sesión                | (sin análogo — ver §1.2)                        |
  | `input`           | ingreso de la solicitud externa          | 1 identidad + 3 guardrails-pre (aprox.)         |
  | `pre_model_call`  | ANTES de enviar el request al modelo     | (sin análogo explícito — ver §1.2)              |
  | `post_model_call` | después de la respuesta del modelo       | (sin análogo explícito)                         |
  | `pre_tool_call`   | antes de UNA invocación concreta de tool | 2 authz + 5 despacho (la decisión previa)       |
  | `post_tool_call`  | después de la invocación                 | 6 verificación (misma posición, otra semántica) |
  | `output`          | la respuesta final ensamblada            | 7 egreso                                        |
  | `agent_shutdown`  | cierre de agente/sesión                  | (sin análogo)                                   |

- **Orden interno de una evaluación** (spec §6, obligatorio): resolver config del punto → resolver
  `policy_target` del snapshot → proyectar el tool (solo en puntos de tool) → input preliminar →
  **annotators** (clasificadores/LLM probabilísticos, en orden lexicográfico, **fail-closed**:
  `annotation_failed`/`annotation_timeout` ⇒ deny) → input final → despacho de la política determinista →
  normalización del verdict → validación/aplicación del transform. Todo error ⇒ `deny` con razón reservada.
- **Verdicts** (spec §13): `allow | deny | warn | escalate | transform`. Cada evaluación deriva
  `input_identity`/`enforced_identity` (= `sha256:` del policy input canónico); una aprobación humana de
  `escalate` se liga a `enforced_identity` y el SDK **rederiva** el digest antes de proceder
  (`approval_action_mismatch` si difiere). Obligaciones del host (spec §17): jamás ejecutar un `deny`;
  `escalate` sin approval path configurado ⇒ tratar como `deny`.
- **Streaming** (spec §18): _"The runtime evaluates whole snapshots and not live token streams"_ — el host
  DEBE ensamblar la salida streamed antes de `post_model_call` y antes de `output`. El hook de LiteLLM
  Proxy que el propio repo publica (`docs/integrations/litellm-proxy.md`) lo implementa: `streaming: buffer`
  drena el stream, evalúa, y re-emite los chunks originales solo si hubo allow; un deny se lanza antes de
  ceder el primer chunk.

**Veredicto contra las 7 etapas de la nota 01:**

1. **Confirma la propiedad estructural central** (nota 01 §1.3): la decisión de autorización ocurre ANTES
   del despacho (`pre_tool_call` precede a la ejecución), el egreso es el último punto gobernado
   (`output`), y todo es fail-closed. También confirma que un punto post-acción no des-ejecuta: un
   `escalate` en `post_tool_call` llega "solo después de que la acción ya ejecutó" — la misma razón por la
   que nuestra etapa 6 (verificación) jamás puede sustituir a la 2 (authz).
2. **No confirma (ni refuta) el orden interno 1→4** (identidad→authz→guardrails→policy): el AGT no tiene
   esas responsabilidades como etapas ordenadas — las funde en **una** evaluación de política por punto, y
   la identidad la resuelve el host fuera del ACS. Nuestro orden sigue derivándose de los invariantes
   propios, no de esta referencia.
3. **Qué agrega que la nota 01 no tiene:** (i) **puntos pre/post alrededor de la llamada a modelo** —
   en la nota 01 el modelo queda implícito dentro del despacho; el AGT lo trata como una frontera mediada
   con chokepoint propio en ambas direcciones (evidencia directa para la nota 09); (ii) **puntos de ciclo
   de vida** `agent_startup`/`agent_shutdown` — soporte externo para la pregunta abierta de la nota 04 §10
   (¿evento `registry.loaded` al arrancar?); (iii) **simetría pre/post en cada cruce de frontera** — la
   nota 01 solo tiene un punto posterior al despacho (verificación).
4. **Qué hace distinto (y dónde lo nuestro es más fuerte):** en ACS los annotators (la capa probabilística)
   **alimentan la decisión de política** y fallan cerrado; en nuestro diseño INV-3/Inv-E los
   `GuardrailSignal` son un tipo disjunto que jamás informa authz ni egreso. No contradice nuestros
   invariantes (es otra factorización), pero Inv-E es estructuralmente más fuerte en lo nuestro: el AGT
   además **no tiene verificación anclada en absoluto** — su `post_tool_call` es política sobre el
   resultado, no una `Attestation` con `AnchorKind`. El diferenciador del proyecto queda intacto.

### 1.2 (b) FastAPI/ASGI: qué es middleware y qué es pipeline explícito

Verificado en vivo contra docs oficiales:

- **Orden real de ejecución.** FastAPI, textual: _"The last middleware added is the outermost, and the
  first is the innermost."_ Con `app.add_middleware(A)` y luego `add_middleware(B)`, el request pasa
  B → A → ruta (y la respuesta al revés). En Starlette con la lista del constructor es al revés en
  apariencia (_"Middleware is evaluated from top-to-bottom"_: el primero de la lista es el más externo).
  Es decir: **el orden depende del mecanismo de registro** — exactamente la clase de "orden por convención"
  que la nota 01 §3 descartó en su alternativa (B).
- **`BaseHTTPMiddleware`: la limitación documentada hoy es contextvars.** Starlette, textual: _"Using
  `BaseHTTPMiddleware` will prevent changes to `contextvars.ContextVar`s from propagating upwards."_ Los
  docs recomiendan middleware **ASGI puro** (_"greater control over behavior and enhanced
  interoperability"_) para superar sus limitaciones. El gotcha histórico de streaming/SSE bufferizado bajo
  `BaseHTTPMiddleware` **ya no aparece como limitación en los docs actuales** (las versiones recientes de
  Starlette lo mitigaron); queda como chequeo declarado confirmar el comportamiento exacto en la versión de
  Starlette que el repo termine pineando — la recomendación de abajo no depende de ese detalle porque
  evita `BaseHTTPMiddleware` por completo.
- **`Depends` por router.** FastAPI, textual: las dependencias de `APIRouter(dependencies=[...])` _"will
  have the list of `dependencies` evaluated/executed before them […] The router dependencies are executed
  first, then the dependencies in the decorator, and then the normal parameter dependencies."_ Corren por
  request, con tipos, dentro del routing — pero no devuelven valores al handler (solo las de parámetro).

**Recomendación concreta de mapeo (la que la nota 01 dejó sin resolver a nivel HTTP):**

| Preocupación                                                      | Mecanismo                                                                                                | Por qué                                                                                                                                                                                                                                                                                                                                                              |
| ----------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| request-id/trace, barrera de errores del servidor, CORS si aplica | **middleware ASGI puro** (nunca `BaseHTTPMiddleware`)                                                    | transversal a TODO transporte, sin estado tipado del dominio; ASGI puro no rompe contextvars ni envuelve la respuesta                                                                                                                                                                                                                                                |
| resolución de identidad (etapa 1) como pre-condición HTTP         | **candidata a `Depends` a nivel de router** (orden garantizado por docs: router → decorator → parámetro) | corre dentro del routing con acceso tipado al request; PERO ver matiz abajo                                                                                                                                                                                                                                                                                          |
| **las 7 etapas de la nota 01 (identidad→…→egreso)**               | **pipeline explícito in-process invocado por el endpoint del gateway — NO middleware**                   | las etapas necesitan un `ctx` tipado que se pasa en orden (decisión de authz inmutable, policy resuelta, resultado del despacho), emiten eventos, y su ORDEN debe ser testeable como una tupla única (nota 01 §9); en middleware el orden vive en el registro de la app (invertido según el mecanismo) y no hay handoff tipado — irrecuperable para el test de orden |
| SSE (`GET /runs/{run_id}/events`, trust/07)                       | pasa por los middleware ASGI puros sin envoltura                                                         | al no usar `BaseHTTPMiddleware` no hay adaptador de respuesta que bufferice el stream                                                                                                                                                                                                                                                                                |

Matiz sobre la etapa 1 como `Depends`: es viable, pero mover UNA etapa al mecanismo HTTP y dejar seis en
el pipeline parte el orden en dos sistemas — la recomendación de esta nota es mantener **las 7 dentro del
`Pipeline`** y usar `Depends` solo para preocupaciones de transporte (parseo/validación del body), de modo
que INV-1 tenga un solo mecanismo auditable. El precedente AGT apunta igual: su runtime evalúa snapshots
completos por punto, nunca mete la evaluación "dentro" del transporte (spec §18) — el transporte ensambla,
el chokepoint decide.

### 1.3 (c) Composio y Cerebrum como patrón de registry — decisión por referencia

**Composio (el ángulo registry; trust/14 ya cubrió el ángulo auth y el incidente de mayo 2026):**

- El catálogo de tools es **remoto y hosteado**: `tools.get(user_id, ...)` resuelve contra
  `backend.composio.dev/api/v3.1/tools`; los schemas se obtienen del API en runtime, identificados por
  **slug** (`GMAIL_SEND_EMAIL`). El descubrimiento ES una llamada a su nube.
- **Versionado por toolkit, pineable por despliegue**: formato `YYYYMMDD_NN` (ej. `20251027_00`);
  se pinea en el constructor (`Composio(toolkit_versions={"github": "20251027_00"})`). Detalle valioso:
  **el default sin versión es la versión base `00000000_00`, NO `latest`** — default determinista, no
  flotante. Su guía: pin cuando el output se parsea programáticamente; `latest` cuando lo consume un LLM.
- Aporte real al registry de la nota 04: solo la **semántica de versionado** — "pin por despliegue con
  default determinista" es exactamente la forma que la opción (D) de nota 04 §2 y su pregunta abierta de
  versiones duplicadas necesitan (mapea a `DistributionManifest`, trust/06 §1.2). El resto (catálogo
  remoto) contradice el registry local por entry points y la postura air-gapped.

**Cerebrum (SDK de AIOS) — el patrón hub, estudiado como lección negativa:**

- Registry estilo **hub remoto de paquetes propios**: `agent_hub_url`/`tool_hub_url =
https://app.aios.foundation` (config.yaml verificado); endpoints `cerebrum/tools/{upload,download,list,
check_updates}`; versionado semver con cache local (`platformdirs.user_cache_dir`); el paquete es un
  dict con metadata + **todos los archivos en base64**; la carga es
  `importlib.util.spec_from_file_location` + inyección en `sys.modules` de código **descargado del hub,
  sin verificación de firma observable en el manager**.
- **Hallazgo de licencia (material):** el archivo `LICENSE` de `agiresearch/Cerebrum` es un **archivo
  vacío de 1 byte** (un salto de línea; GitHub lo reporta `NOASSERTION`). El `LICENSE` de
  `agiresearch/AIOS` está igual (1 byte). Sin texto de licencia no hay concesión de derechos utilizable —
  inusable como dependencia con independencia de cualquier mérito técnico.
- Aporte por contraste: nuestro registry (nota 04) solo carga código **ya instalado** por el gestor de
  paquetes (resolución de dependencias, lockfile, revisión humana del `pyproject.toml`) — una cadena de
  suministro estrictamente más fuerte que "descargar del hub y ejecutar". El `check_updates`+cache de
  Cerebrum es una re-implementación débil de lo que `uv`/pip ya dan. Y el AGT demuestra la versión
  correcta del patrón hub: manifest firmado con el digest del artefacto adentro y verificación fail-closed
  en install y en CADA carga (trust/09 §1.4) — si Fase 2 alguna vez quisiera distribución remota de
  capabilities, la referencia es esa, no esta.

## 2 · Decisión

| Referencia                                                                                    | Decisión                                                      | Racional                                                                                                                                                 |
| --------------------------------------------------------------------------------------------- | ------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| AGT/ACS como validación externa del chokepoint (8 intervention points, host-PEP, fail-closed) | **inspirar**                                                  | Confirma decisión-antes-de-despacho, egreso-último y fail-closed; no dicta nuestro orden interno 1→4 (que sigue derivado de invariantes propios)         |
| Puntos `pre_model_call`/`post_model_call` como frontera mediada explícita                     | **inspirar** (insumo directo de la nota 09)                   | El AGT trata la llamada a modelo como cruce gobernado con punto propio — evidencia para dónde vive el egress del router                                  |
| Puntos `agent_startup`/`agent_shutdown`                                                       | **inspirar** (apoya `registry.loaded`, nota 04 §10)           | Precedente externo de instrumentar el ciclo de vida, no solo el request                                                                                  |
| Fusión AGT de guardrails-probabilísticos dentro de la decisión de política                    | **descartar**                                                 | Nuestra separación tipada (`GuardrailSignal` ≠ decisión de authz, INV-3/Inv-E) es más fuerte; adoptarla la debilitaría                                   |
| Middleware ASGI puro para transversales de transporte (request-id, barrera de errores)        | **portar**                                                    | Patrón oficial recomendado por Starlette; sin dependencia nueva                                                                                          |
| `BaseHTTPMiddleware`                                                                          | **descartar**                                                 | Limitación documentada de contextvars + historial de gotchas de streaming; ASGI puro lo cubre todo                                                       |
| Las 7 etapas como middleware chain HTTP                                                       | **descartar**                                                 | El orden viviría en el registro de la app (invertido según mecanismo) sin handoff tipado ni test de orden posible — reabre lo que la nota 01 §3(B) cerró |
| Las 7 etapas como `Pipeline` explícito in-process invocado por el endpoint                    | **portar**                                                    | Coherente con nota 01 §8 y con el precedente AGT (transporte ensambla, chokepoint decide)                                                                |
| `Depends` por router para transporte (parseo/validación)                                      | **integrar** (mecanismo de FastAPI, ya dependencia del stack) | Orden documentado y garantizado; no sustituye ninguna etapa                                                                                              |
| Semántica de versionado de Composio (pin por despliegue, default determinista ≠ latest)       | **inspirar**                                                  | Forma exacta para la pregunta de versiones de nota 04 §10 vía `DistributionManifest`; sin dependencia                                                    |
| Composio como registry (catálogo remoto hosteado)                                             | **descartar**                                                 | Descubrimiento = llamada a su nube; incompatible con entry points locales y postura air-gapped (auth ya descartado en trust/14)                          |
| Cerebrum / hub AIOS como patrón de registry                                                   | **descartar**                                                 | Código remoto ejecutado sin firma + LICENSE vacío (1 byte, sin concesión de derechos); lección negativa documentada                                      |

## 3 · Licencias

| Pieza                                                                   | Licencia                                                                                  | Verificado                                                                                               |
| ----------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| microsoft/agent-governance-toolkit (raíz y `policy-engine/LICENSE.acs`) | **MIT**                                                                                   | ✅ en vivo 2026-07-14 (`gh api`, ambos archivos) — reconfirma trust/09 tras la reestructuración del repo |
| FastAPI                                                                 | **MIT**                                                                                   | ✅ en vivo 2026-07-14 (SPDX del repo)                                                                    |
| Starlette                                                               | **BSD-3-Clause**                                                                          | ✅ en vivo 2026-07-14 (SPDX del repo)                                                                    |
| Composio (repo `ComposioHQ/composio`)                                   | **MIT — solo el SDK cliente**; catálogo/backend cerrados (`backend.composio.dev`)         | ✅ en vivo 2026-07-14 (SPDX) — consistente con trust/14                                                  |
| Cerebrum (`agiresearch/Cerebrum`)                                       | **sin licencia efectiva** — `LICENSE` existe pero está vacío (1 byte); SPDX `NOASSERTION` | ✅ en vivo 2026-07-14 (contenido del archivo, `Cg==` base64 = `"\n"`)                                    |
| AIOS (`agiresearch/AIOS`)                                               | **sin licencia efectiva** — mismo hallazgo (`LICENSE` de 1 byte)                          | ✅ en vivo 2026-07-14                                                                                    |

No se propone ninguna dependencia nueva en esta nota (FastAPI/Starlette ya son del stack).

## 4 · Impacto en contrato

1. **Ningún contrato del freeze cambia.** Esta nota valida externamente la forma de `GatewayStage`/
   `Pipeline` de la nota 01 §8 y le agrega la decisión de capa HTTP: middleware ASGI puro solo para
   transporte; las 7 etapas como pipeline explícito dentro del endpoint del gateway (tabla en §1.2). Esto
   refina la pregunta abierta de nota 01 §10 ("¿el pipeline corre in-process?") con respaldo de referencia,
   no solo supuesto.
2. **Insumo para nota 04 / `DistributionManifest` [frontera]:** la semántica "versión pineada por
   despliegue con default determinista (nunca `latest` implícito)" queda propuesta como forma para resolver
   la pregunta de versiones duplicadas (nota 04 §10) — a ratificar con Dylan porque la potestad de
   override es del `DistributionManifest` (trust/06 §1.2).
3. **Insumo para nota 09:** el AGT gobierna `pre_model_call`/`post_model_call` como frontera explícita, y
   su propio hook de LiteLLM Proxy media el tráfico de modelo en un chokepoint — la nota 09 usa esto como
   evidencia de patrón para el egress del model router.
4. **Semilla Fase 2 (sin contrato hoy):** si alguna vez hay distribución remota de capabilities, el patrón
   es el plugin signing del AGT (manifest firmado, digest del artefacto adentro, fail-closed en install y
   en cada carga — trust/09 §1.4), no el hub sin firma de Cerebrum.

## 5 · Reconciliación contra la base lógica

- **INV-1 (gateway único chokepoint):** REFORZADO — la referencia más citada de la industria implementa
  exactamente "el transporte ensambla, el chokepoint decide"; y la decisión de NO usar middleware para las
  etapas evita que el orden del chokepoint dependa del registro de middlewares de la app (un segundo lugar
  de verdad que INV-1 no controla).
- **Inv-E / INV-6 (egreso solo por authz):** INTACTOS y contrastados — el AGT llega a la misma posición
  estructural (deny jamás se ejecuta; escalate sin approval ⇒ deny; `output` es el último punto gobernado)
  por otro camino; donde difiere (annotators probabilísticos alimentando la decisión), nuestra separación
  tipada es deliberadamente más fuerte y se mantiene.
- **INV-3 (guardrails no decide egreso):** INTACTO — se descarta explícitamente importar la factorización
  AGT que fusiona detección probabilística con la decisión de política.
- **INV-2 / PR2 (el verificador nunca es un modelo):** INTACTO — el AGT no tiene verificación anclada;
  nada en esta nota importa semántica de "policy verdict" hacia `Attestation`.
- **ADR-008 / ADR-029 (registry por entry points, manifests genéricos):** REFORZADOS por contraste — los
  dos registries externos estudiados (catálogo cloud de Composio, hub sin firma de Cerebrum) validan por
  la negativa la elección de entry points locales sobre paquetes instalados; solo se toma prestada la
  semántica de versionado pineado, que no toca la genericidad del manifest.
- **Ninguna referencia contradice la base lógica.** Las divergencias encontradas (fusión
  annotators/política en AGT, catálogos remotos) son datos sobre las referencias y decisiones de descarte,
  no tensiones con invariantes.
