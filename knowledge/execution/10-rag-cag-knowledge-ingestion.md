# Nota 10 — Ingesta de conocimiento (video→texto): RAG vs CAG vs fine-tuning, y dónde vive el knowledge graph que consume el agente

**Ítem del plan:** plano de ejecución (Steven) — la organización de la Quantathon CR 2026 subió varios
videos estilo curso (contenido semi-completo, no un manual único) y el equipo quiere convertirlos en
conocimiento que el propio agente de Chimera pueda consultar en tiempo de ejecución — no solo
documentación para que el equipo lea. Esta nota compara los mecanismos (RAG, CAG, fine-tuning,
knowledge graph) y fija dónde engancha esto en lo que ya está congelado, antes de que existan specs/tests.
**Fecha:** 2026-07-21 · **Estado:** investigación inicial — **fuera del alcance de
`docs/contract-freeze.md` (S-E, ya CONGELADO)**. Esto es candidato a un ítem nuevo `[ejecución]`/`[frontera]`
si Dylan no ve objeciones — el propio freeze exige que cualquier cambio post-cierre sea "supersesión con
causa registrada (L2), jamás edición silenciosa" (`contract-freeze.md`, regla 3). Esta nota no edita el
freeze; es el insumo para decidir si se edita.
**Fuentes:** `knowledge/execution/02-runtime-agent-loop.md` §1.3/§1.4 (forma de `RunStep`, dónde
engancharía un paso de recuperación) · `knowledge/execution/09-model-server-egress.md` (AX3 aplicado a
cualquier llamada de modelo, incluida una llamada de embeddings) · `docs/contract-freeze.md` §12
(`Artifact`/`ContentStore`, ya congelado — el sustrato de almacenamiento que esta nota reutiliza sin
pedir nada nuevo) · `docs/contract-freeze.md` §15.1 (doctrina de soberanía de datos, aplicable por
analogía si el corpus dejara de ser público) · `docs/invariants.md` (INV-2, AX3, Inv-E, ADR-029) ·
conocimiento general sobre RAG/CAG/fine-tuning (referencia conceptual, **no verificado en vivo esta
sesión** — sin `WebFetch`/`WebSearch` de papers o docs de proveedor).

---

## 1 · Patrón / mecanismo

### 1.1 El problema real, sin adornos

Los videos de la organización son "estilo curso" pero con contenido semi-completo — ningún video por sí
solo es la fuente autoritativa, y el conjunto probablemente se solapa, se contradice en detalles menores,
o deja huecos. El objetivo no es "resumir los videos" para que una persona los lea — es que **el agente
de Chimera pueda consultar ese contenido en medio de un run**, de la misma forma en que hoy consultaría
cualquier otro contexto antes de invocar un modelo (nota 09 / freeze §15.7). Esto es, en el vocabulario ya
congelado, **contexto de apoyo para un `model.call.requested`** — no un ancla, no un verificador, no un
dato decisorio (ver §13).

### 1.2 Tres mecanismos comparados — qué hace cada uno con "video convertido en texto"

- **RAG (retrieval-augmented generation):** el texto (transcrito, dividido en fragmentos) se guarda
  indexado (típicamente embeddings + búsqueda por similitud); en cada paso que lo necesite, el runtime
  recupera los `k` fragmentos más relevantes a la pregunta actual y los inyecta en el prompt antes de
  llamar al modelo. El corpus puede crecer sin límite práctico — solo crece el índice, no el prompt.
- **CAG (cache-augmented generation):** en vez de recuperar fragmentos por pregunta, se precarga **todo**
  el corpus (o la porción relevante) en la ventana de contexto del modelo una sola vez, aprovechando cache
  de prompt/KV para que consultas repetidas sobre el mismo contexto no vuelvan a pagar el costo de
  proceso completo. No hay paso de "búsqueda" — todo el contenido ya está en el contexto. Escala mal si el
  corpus no cabe en la ventana de contexto (o cabe pero a un costo de tokens que no se justifica para la
  fracción del corpus realmente relevante a cada pregunta).
- **Fine-tuning:** el contenido se usa para reentrenar (o entrenar un adapter tipo LoRA sobre) un modelo,
  de forma que el conocimiento quede en los pesos en vez de en un documento externo. No hay paso de
  recuperación ni de contexto — el modelo "ya sabe" sin que se le recuerde en cada llamada.

### 1.3 Dónde engancha esto en lo que ya está congelado — no hace falta inventar un mecanismo nuevo de almacenamiento

Este es el hallazgo central de la nota: **el freeze ya tiene el sustrato que esto necesita, sin pedir nada
nuevo.**

- Cada video transcrito, y cada fragmento (`chunk`) derivado de esa transcripción, es un **`Artifact`**
  tal cual está congelado en `contract-freeze.md` §12: `{digest (sha256 de la forma canónica), domain_id,
media_type, size_bytes, storage_ref, created_at}`. `ContentStore.put()` ya existe como contrato — un
  fragmento de conocimiento indexado es, ni más ni menos, contenido con su propio digest recuperable byte
  a byte. Esto reutiliza SO2 (particionado por dominio) sin cambios: si el corpus de un video fuera
  sensible por dominio (no es el caso de contenido público del evento, pero el mecanismo debe sostenerlo),
  la partición ya aplica.
- Un paso de recuperación (RAG) es, en el vocabulario de la nota 02, **un `RunStep` más** — de un `kind`
  nuevo (ej. `"retrieval"`), cuyo `input_digest` es la pregunta/contexto que disparó la búsqueda y cuyo
  `output_digest` apunta a los `Artifact`s de los fragmentos recuperados (no a un resumen con pérdida —
  nota 02 §1.3 ya exige esto para CUALQUIER `RunStep`, esta nota no relaja ese requisito). El paso de
  recuperación antecede, y alimenta, un `model.call.requested` (nota 09 / freeze §3) — el `prompt_digest`
  de esa llamada debe incluir el contenido recuperado completo, no una referencia que se resuelva después
  (si no, el replay de la nota 03 reconstruye el ORDEN pero no puede verificar que el CONTENIDO fue el
  mismo — el mismo modo de falla que la nota 02 §6 ya identificó para cualquier llamada de modelo).
- Si el mecanismo de recuperación usa un modelo de embeddings para calcular similitud, **esa llamada
  también es una llamada de modelo bajo AX3** (nota 09) — no puede salir directo desde código de runtime
  arbitrario; pasa por el mismo `ModelPort`/`ModelServer` mediado, aunque el "modelo" en este caso sea un
  encoder de embeddings y no un LLM generativo. Esta nota no inventa una excepción a AX3 para embeddings.

### 1.4 Knowledge graph — una capa aparte, no un mecanismo que compita con RAG

Un knowledge graph (entidades + relaciones extraídas del mismo corpus transcrito — ej. "QAOA" `usa`
"Ising model", "Quantinuum H2" `implementa` "emulador H-series") no es una alternativa a RAG/CAG, es una
**estructura adicional que se construye ENCIMA del mismo corpus** para responder preguntas relacionales
que la similitud vectorial sola no resuelve bien (ej. "¿qué técnicas de corrección de errores se mencionan
en los videos que hablan de Selene?" es una pregunta de relación, no de similitud semántica pura). Se
puede construir sin RAG, pero construirlo SIN antes tener el corpus indexado y con digest/procedencia
(§1.3) es resolver el problema al revés — el grafo hereda la misma necesidad de trazabilidad que
cualquier otro `Artifact` de esta nota.

## 2 · Alternativas consideradas

- **(A) RAG — recuperación por similitud sobre un corpus indexado, vía un `RunStep` de tipo retrieval.**
- **(B) CAG — todo el corpus relevante precargado en la ventana de contexto, sin paso de búsqueda.**
- **(C) Fine-tuning — el contenido se hornea en los pesos de un modelo (completo o vía adapter LoRA).**
- **(D) Knowledge graph como capa adicional sobre (A) — extracción de entidades/relaciones del mismo
  corpus, consultable además de (o en vez de) la búsqueda vectorial simple.**
- **(E) Ningún mecanismo — dejar los videos como referencia humana, fuera del sistema.** (el estado
  implícito de hoy: es la opción por omisión si no se decide nada.)

## 3 · Por qué no (descartadas)

- **(C) Fine-tuning, descartada — no por costo/tiempo únicamente, sino por incompatibilidad de
  arquitectura.** Todo el proyecto está construido sobre la idea de que una afirmación vale según de
  dónde salió — anclas, digests, certificados, `assumptions` con `{statement, ref?{name, digest}}` (freeze
  §7). Un modelo fine-tuneado "sabe" algo sin que exista ningún digest, ningún `Artifact`, ninguna
  referencia recuperable que explique de dónde salió ese conocimiento — es exactamente la forma de
  conocimiento que el resto del sistema estructuralmente evita para cualquier afirmación que necesite
  sustento (INV-2, PR2). Fine-tuning es la herramienta correcta para comportamiento/formato (que un
  modelo siga cierto estilo o esquema de salida) — no para inyectar hechos de un corpus que cambia y que
  se necesita poder citar. Descartada también por motivo práctico: con el tiempo del evento no hay margen
  para curar un dataset de fine-tuning de calidad ni para re-evaluar que no degradó el comportamiento
  general del modelo en otras tareas del sistema.
- **(B) CAG como reemplazo TOTAL de RAG — descartada mientras no se sepa el volumen del corpus.** Si el
  conjunto completo de transcripciones no cabe cómodo en la ventana de contexto (o cabe pero a un costo de
  tokens que se paga en CADA llamada aunque el 90% del contenido sea irrelevante a la pregunta puntual),
  CAG deja de ser viable o deja de ser barato. No se descarta como dirección futura (§12) si el corpus
  termina siendo chico — se descarta como decisión POR DEFECTO sin conocer el volumen real (pregunta
  abierta, §10).
- **(D) Knowledge graph como PRIMER paso (antes de tener el corpus indexado con digest/procedencia) —
  descartada.** Construir relaciones entre entidades sin que el corpus fuente ya esté versionado con
  digest es resolver el problema de trazabilidad al revés — el grafo terminaría apuntando a texto que no
  se puede verificar byte a byte contra su fuente. Se recomienda como capa POSTERIOR (§12), no como punto
  de partida.
- **(E) No hacer nada — descartada, es el motivo por el que existe esta nota.** El equipo ya identificó
  que el contenido de los videos es valioso; dejarlo fuera del sistema porque no hay un mecanismo diseñado
  es exactamente el mismo riesgo que motivó la nota 01 sobre el gateway ("sin una forma explícita, es una
  aspiración, no un mecanismo").

## 4 · Decisión

| Referencia                                                       | Decisión                                     | Racional                                                                                                                                                                  |
| ---------------------------------------------------------------- | -------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| RAG (recuperación por similitud, `RunStep` de tipo retrieval)    | **portar** (propuesta, pendiente de Dylan)   | Encaja sin fricción en `RunStep`/`Artifact`/`ContentStore` ya congelados; da trazabilidad por diseño (§1.3), que es exactamente lo que el proyecto exige en todo lo demás |
| CAG (precarga de contexto, sin paso de búsqueda)                 | **inspirar** (dirección futura condicionada) | Válida si el corpus resulta chico (pregunta abierta, §10); no se compromete como mecanismo principal sin ese dato                                                         |
| Fine-tuning sobre el contenido de los videos                     | **descartar**                                | Incompatible con la exigencia de trazabilidad del proyecto (§3); herramienta equivocada para inyección de hechos, no de comportamiento                                    |
| Knowledge graph sobre el mismo corpus indexado                   | **inspirar** (fase posterior, no bloqueante) | Aporta sobre preguntas relacionales que la similitud vectorial sola no resuelve bien; depende de tener el corpus indexado con digest primero (§1.4)                       |
| Reutilizar `Artifact`/`ContentStore` (freeze §12) para el corpus | **integrar**                                 | Ya congelado; cero contrato nuevo de almacenamiento necesario                                                                                                             |
| Embeddings/retrieval como llamada mediada por AX3                | **portar**                                   | Ninguna llamada de modelo (generativo o de embeddings) sale del camino ya congelado (nota 09) — sin excepción para este caso                                              |

## 5 · Tradeoffs

| Eje                                                | RAG                                                        | CAG                                                                         | Fine-tuning                                                                                                                                             |
| -------------------------------------------------- | ---------------------------------------------------------- | --------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Trazabilidad/citabilidad de cada afirmación        | Alta — el fragmento recuperado es un `Artifact` con digest | Alta — el contexto cacheado sigue siendo texto explícito en el prompt       | **Ninguna** — el conocimiento vive en pesos, sin referencia recuperable                                                                                 |
| Costo de actualizar el corpus                      | Bajo — se reindexa el `Artifact` nuevo/corregido           | Bajo — se recarga el contexto                                               | Alto — exige reentrenar/re-adaptar y reevaluar                                                                                                          |
| Escala con el tamaño del corpus                    | Buena — el índice crece, el prompt no                      | Mala si el corpus no cabe en la ventana de contexto                         | N/A — el "tamaño" ya no es un costo en tiempo de inferencia, pero sí en entrenamiento                                                                   |
| Latencia por consulta                              | Media (paso de búsqueda + llamada)                         | Baja en consultas repetidas sobre el mismo contexto cacheado                | Mínima (no hay paso extra) — pero esto es exactamente el problema: no hay forma de auditar qué usó                                                      |
| Riesgo de alucinación citando mal la fuente        | Presente si el retrieval trae contexto irrelevante (§6)    | Presente, mismo riesgo si el contexto cacheado incluye ruido                | Alto — no hay fuente que citar correcta o incorrectamente, el modelo "improvisa" con más confianza aparente                                             |
| Encaje con AX3/mediación ya congelada              | Directo — el paso de retrieval es un `RunStep` más         | Directo — sigue siendo una llamada de modelo mediada                        | No aplica el mismo control — un modelo fine-tuneado sigue pasando por `ModelPort`, pero el conocimiento en sí nunca pasó por ningún gate de procedencia |
| Esfuerzo de implementación en el tiempo del evento | Medio (vector store + paso de recuperación)                | Bajo si el corpus es chico, alto si hay que trocear por límites de contexto | Alto (dataset curado + entrenamiento + evaluación de regresión)                                                                                         |

## 6 · Modos de falla

- **Transcripción con errores contaminando la base de conocimiento silenciosamente.** Un ASR (reconocimiento
  de voz) que transcribe mal un término técnico (ej. "Selene" como "selena", o un valor numérico mal
  transcrito) introduce un error que después se recupera y se cita como si fuera la fuente original —
  el sistema tiene TRAZABILIDAD (se puede señalar el `Artifact` exacto), pero no tiene CORRECCIÓN
  automática; el error queda visible pero no se detecta solo. **Mitigación no implementada:** cada
  transcripción debería guardar también una referencia al video/timestamp original, para que una revisión
  humana pueda cotejar rápido si algo recuperado se ve raro — mismo patrón que el corpus de islanding
  (`dataset_id` + digest, freeze §15.3), no un mecanismo nuevo.
- **Retrieval trae contexto irrelevante y el modelo alucina de todas formas, citando una fuente que no
  dice eso.** Este es el modo de falla que más se parece al problema que el resto del proyecto ya resolvió
  para verificación (Inv-E: un veredicto de verificación no fabrica autorización) — aquí el riesgo
  análogo es que un fragmento recuperado (aunque tenga digest legítimo) no fabrique una afirmación que el
  fragmento no sostiene. **Esto es exactamente por lo que el contenido recuperado debe tratarse como
  contexto de apoyo/asunción, nunca como `Attestation`** (ver §13) — el problema no se "arregla" con mejor
  retrieval, se contiene con la separación de tipos que el proyecto ya aplica en todo lo demás.
- **Ningún digest/procedencia en los fragmentos recuperados — rompe exactamente la trazabilidad que se
  supone que RAG da sobre fine-tuning.** Si la implementación del vector store no preserva el vínculo
  fragmento→`Artifact`→video-fuente (ej. un pipeline que solo guarda embeddings y texto plano, sin volver
  a poder reconstruir de qué video salió byte a byte), se pierde la ventaja central de esta nota (§3) sin
  que nadie lo note hasta que alguien pregunte "¿de dónde salió esto?" y no haya respuesta.
- **Fine-tuning "fantasma" — alguien lo prueba "para ver si ayuda" y ahora hay conocimiento no auditable en
  el sistema.** Aunque esta nota descarta fine-tuning como mecanismo principal (§3), el riesgo de gobernanza
  real es que alguien lo intente de forma ad hoc sin que quede registrado — un modelo fine-tuneado corriendo
  en producción sin que su origen/dataset esté documentado es un caso peor que "no tener el conocimiento":
  es tener conocimiento no verificable presentándose con la misma confianza que uno que sí lo es.
- **CAG con contexto cacheado que no se invalida cuando la fuente cambia.** Si se corrige una transcripción
  (por el modo de falla de arriba) pero el contexto ya estaba cacheado/precargado, consultas posteriores
  siguen viendo la versión vieja hasta que algo fuerce una invalidación explícita — un riesgo de "verdad
  stale" que RAG no tiene de la misma forma porque cada consulta reindexada recupera el `Artifact` vigente.

## 7 · Licencias

| Pieza                                                   | Licencia                   | Verificado                                                                                                                                                                   |
| ------------------------------------------------------- | -------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Patrón RAG / CAG / fine-tuning (conceptos, no librería) | N/A — patrón, no código    | conocimiento general, **no verificado en vivo esta sesión**                                                                                                                  |
| ASR para transcripción (ej. Whisper y derivados)        | Típicamente MIT/Apache-2.0 | **no verificado en vivo esta sesión** — nombre de referencia, sin confirmar versión/licencia exacta                                                                          |
| Vector store                                            | Depende de la elección     | **PENDIENTE** — ver §10; candidato obvio es `pgvector` sobre el mismo Postgres ya presente en el walking skeleton (evita infraestructura nueva), pero no se verificó en vivo |

No se propone ninguna dependencia nueva como decisión firme en esta nota — la elección de herramienta
concreta de transcripción/embeddings/vector store queda como pregunta abierta (§10), no como parte
congelada de esta propuesta.

## 8 · Impacto en contrato

1. **Ningún cambio al contrato de `Artifact`/`ContentStore` (freeze §12).** Un video transcrito y sus
   fragmentos son `Artifact`s como cualquier otro — se reutiliza tal cual.
2. **Propuesta de forma, no congelada:** un nuevo `kind` de `RunStep` (ej. `"retrieval"`) que antecede a un
   `model.call.requested` cuando el paso necesita contexto recuperado; su `output_digest` apunta a los
   `Artifact`s de los fragmentos usados, no a un resumen.
3. **El mecanismo de recuperación (embeddings/similitud) es una capability o un puerto de modelo más bajo
   AX3 — nunca una excepción.** Si se modela como capability (vía Registry, nota 04), hereda ADR-029
   (genéricidad: "recuperar contexto relevante dado una consulta" es una descripción genérica, "buscar en
   los videos de la Quantathon" NO lo es — el término de escenario vive en el contenido de la KB, no en el
   manifest, mismo principio que ya rige el resto de capabilities).
4. **Frontera con el plano de confianza — pendiente de acuerdo con Dylan, no decidida aquí:** si un claim
   del sistema depende de contenido recuperado, ese contenido debería aparecer en `assumptions` del
   certificado (freeze §7 — `{statement, ref?{name, digest}}`), NUNCA como parte de `conclusions` ni como
   sustento de un `Attestation`. Esta nota propone la regla; su encaje exacto en el esquema de `Policy`/
   `Certificate` es terreno de Dylan (mismo patrón de frontera que `CapabilityManifest`/`execution_profile`
   en el freeze §1).
5. **Ningún cambio a `docs/contract-freeze.md` en esta nota.** Si Dylan no ve objeciones, el siguiente paso
   es una edición explícita del freeze (supersesión con causa, regla 3 del propio documento) que incorpore
   esto como ítem `[ejecución]`/`[frontera]` nuevo — no una edición silenciosa.

## 9 · Implicaciones de test / spec

- **Test de digest recuperable:** cada fragmento devuelto por un paso de retrieval debe corresponder a un
  `Artifact` existente en el `ContentStore`, recuperable byte a byte — nunca un resumen con pérdida
  (extiende directamente el requisito ya existente de la nota 02 §1.3 al nuevo `kind` de `RunStep`).
- **Test de prompt replay-friendly:** el `prompt_digest` de un `model.call.requested` que use contenido
  recuperado debe incluir ese contenido completo, no una referencia que se resuelva distinto en un replay
  futuro (mismo modo de falla "replay no determinista" de la nota 02 §6, aplicado aquí).
- **Test de separación de tipos (el más importante de esta nota):** un test que verifique que contenido
  recuperado por RAG **no puede** producir ni sustituir un `Attestation` — análogo al test ya recomendado
  en la nota 01 §9 sobre que la etapa de egreso no acepte un `Signal` como si fuera una decisión de authz.
  Aquí el análogo es: la etapa de verificación no debería tener firma de tipos que acepte "fragmento
  recuperado" como argumento de un veredicto.
- **Test de procedencia del corpus:** cada transcripción debe conservar su referencia al video/timestamp
  fuente (mismo patrón `dataset_id` + digest del corpus de islanding, freeze §15.3) — sin este test, el
  modo de falla "transcripción con errores silenciosos" (§6) no tiene forma de detectarse en CI.
- Ninguno de estos tests existe hoy — señalados como trabajo futuro derivado de este diseño, igual que el
  resto de notas de esta carpeta.

## 10 · Supuestos y preguntas abiertas

**Supuestos (marcados explícitamente, no verificados):**

- Los videos son contenido público del propio evento (no datos del cliente) — la doctrina de soberanía de
  datos (freeze §15.1, "los datos de red del cliente jamás egresan") no debería aplicar aquí, pero esta
  nota no lo confirma con nadie del equipo.
- El corpus de video transcrito es candidato a usarse EN TIEMPO DE EJECUCIÓN por el agente (no solo como
  documentación de referencia para el equipo humano) — esto es lo que motiva tratarlo con el mismo rigor
  de trazabilidad que cualquier otro dato que un run consuma.

**Preguntas abiertas (no decidido en esta nota):**

- **¿Cuántos videos / cuánto texto en total?** Determina directamente si CAG es viable (§3) — no
  investigado.
- **¿Quién transcribe y con qué herramienta?** (ASR local vs. servicio) — afecta si esa llamada también
  cruza AX3/mediación (si el ASR es un servicio de red, sí) y qué licencia aplica (§7).
- **¿Dónde vive el vector store?** Candidato obvio: `pgvector` sobre el mismo Postgres del walking
  skeleton (cero infraestructura nueva, coherente con la doctrina de "lites propios" del freeze) — no
  verificado en vivo, no decidido.
- **¿Esto es responsabilidad de ejecución (Steven) o de confianza (Dylan), o frontera de ambos?** Esta nota
  asume frontera (mecanismo = Steven, qué constituye evidencia/asunción declarada = Dylan) por analogía con
  `CapabilityManifest`, pero no lo confirma — es el primer punto a resolver en sesión conjunta (ver
  encabezado de esta nota).
- **¿Esto entra al camino dorado del demo (freeze §15.4) o es soporte de investigación del equipo, fuera
  del alcance del mes?** Cambia completamente la prioridad — si es soporte de investigación únicamente
  (el equipo consultando la KB para entender el dominio, no el agente de Chimera consultándola en vivo
  durante el demo), el diseño se simplifica bastante y varias de las preguntas de arriba dejan de ser
  bloqueantes para el mes.

## 11 · Recomendación mínima de POC

Si Dylan no ve objeciones y esto entra al alcance del mes: (1) transcribir UN video de prueba con un ASR
cualquiera disponible; (2) trocear el texto y guardar cada fragmento como `Artifact` vía el `ContentStore`
ya congelado (cero contrato nuevo); (3) un único `RunStep` de tipo retrieval que recupere el/los
fragmento(s) más relevantes a una pregunta de prueba y los inyecte en un `model.call.requested`,
verificando que el `prompt_digest` resultante incluye el contenido recuperado completo (test de §9); (4)
confirmar explícitamente que el fragmento recuperado se maneja como asunción/contexto, nunca como
`Attestation` (el test de separación de tipos, también §9). Ningún vector store "de producción", ningún
knowledge graph, ninguna cobertura del corpus completo — el POC valida el MECANISMO con el mínimo de
alcance, igual que el resto de recomendaciones de POC de esta carpeta.

## 12 · Dirección later / producción

Fuera de alcance de esta nota, como dirección conceptual: CAG se vuelve la opción más simple si el corpus
completo termina cabiendo cómodo en una ventana de contexto razonable — en ese caso, sáltese el paso de
retrieval por completo y precárguese el contexto una vez, revisando periódicamente si la fuente cambió
(mitigación del modo de falla de "contexto cacheado stale", §6). El knowledge graph es la extensión natural
si, una vez que el corpus esté indexado con digest/procedencia (§1.4), el equipo encuentra preguntas
recurrentes de tipo relacional que la búsqueda vectorial simple no resuelve bien — no se compromete su
diseño aquí. Una dirección no explorada en esta nota: si el pipeline de transcripción/ingesta en sí mismo
necesitara un control de calidad (ej. una revisión que confirme que la transcripción de un segmento crítico
es fiel al audio original), eso sería un caso más del patrón "certificación de capability" ya congelado
(freeze §7, modo amortizado) — pero investigar esa aplicación queda fuera del alcance de esta pasada.

## 13 · Reconciliación contra la base lógica (`docs/invariants.md`)

- **INV-2 (el verificador nunca es un modelo):** INTACTO, con una advertencia activa — el mecanismo de
  recuperación (embeddings/similitud) es en sí mismo una forma de modelo, y por diseño **nunca debe poder
  producir un `Attestation`**. Esta nota no le da ninguna vía para hacerlo (§8, §9); el riesgo real es de
  disciplina de implementación (que alguien, en la práctica, trate un buen resultado de retrieval como si
  fuera una verificación), exactamente el mismo tipo de riesgo que la nota 01 §6 ya documentó para
  `Signal`/`Attestation` — esta nota extiende esa misma cautela al contenido recuperado por RAG.
- **AX3 (modelo/serving no toca el mundo directo):** INTACTO por diseño — cualquier llamada de modelo
  involucrada (generación o embeddings) pasa por el mismo `ModelPort`/`ModelServer` ya congelado (nota 09);
  esta nota no propone ninguna ruta de red alternativa para el mecanismo de recuperación.
- **Inv-E (egreso solo por autorización, nunca por verificación):** relacionado pero no idéntico — el
  riesgo análogo aquí es que contenido recuperado (con apariencia de fuente legítima, digest incluido)
  fabrique una afirmación que su fuente no sostiene realmente. La separación de tipos propuesta en §8/§9
  (recuperado ≠ `Attestation`, siempre asunción/contexto) es la misma defensa estructural que Inv-E aplica
  para verificación — no un mecanismo nuevo, una extensión del mismo principio.
- **ADR-029 (manifests genéricos):** INTACTO si el mecanismo de recuperación se modela como capability
  genérica ("recuperar contexto relevante dado una consulta") — el conocimiento específico del dominio
  (Quantathon, QAOA, Quantinuum) vive en el CONTENIDO de la base de conocimiento, nunca en el nombre o
  código del mecanismo de recuperación en sí. Esta nota lo señala como requisito, no lo implementa.
- **ADR-008 (capabilities fuera del core):** aplicaría igual si el mecanismo de retrieval se registra como
  capability vía el Registry (nota 04) — no se investigó si esa es la forma correcta o si amerita un puerto
  nuevo separado del Registry de capabilities (pregunta abierta adicional, no listada en §10 por no haberse
  identificado hasta este punto de la redacción — se deja anotada aquí para no perderla).
- **Ninguna referencia contradice la base lógica.** RAG, CAG y fine-tuning son patrones/técnicas genéricas,
  sin licencia ni dependencia comprometida en esta nota; la restricción real (recuperado ≠ decisorio) es
  enteramente derivada de invariantes ya congelados, no de las técnicas en sí.
