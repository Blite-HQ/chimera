# Arquitectura Fase 2 — Ingesta multi-modal + knowledge graph verificable

**Fecha:** 2026-07-21 · **Estado:** propuesta de diseño, NO implementada — explícitamente fuera del
timeline del hackathon (ver `docs/research/README.md` para la distinción `knowledge/` vs `docs/research/`).
**Origen:** surge de un ejercicio personal (rama `ejercicio/sf-ratificacion-simulada`) evaluando si
construir un knowledge base + knowledge graph a partir de las clases del bootcamp pre-hackathon
(q-world/QWorld OQI + materiales del Quantathon) aporta valor. La conclusión de ese ejercicio fue
que el 90% del valor a corto plazo se resuelve con un track vivo mucho más barato — triage +
índice de ruteo sobre `knowledge/quantum/` (ver `knowledge/quantum/_triage-map.md` e `INDEX.md`,
en `main`) — y que la arquitectura ambiciosa descrita acá es un proyecto de Fase 2 legítimo, no un
acelerador de hackathon. Este documento existe para no perder el diseño mientras se construye lo
barato primero.
**Fuentes:** `docs/esquema-datos-v2.md` (hook `pgvector` ya reservado para "memoria/RAG, cuando
aplique"), `knowledge/quantum/00-kb-fuentes.md` §6 (checklist de incorporación al RAG de CHIMERA,
nunca ejecutada), `docs/arquitectura-reconciliada.md` (módulo `Context/RAG` y tool
`document_retriever`, marcados "diseñado, no implementado en el demo"), `docs/invariants.md`
(INV-2/PR2 — el verificador jamás es un modelo).

---

## 1 · Motivación y alcance

Chimera ya tiene tres piezas que apuntan a esto sin haberlo construido:

1. Un **hook de esquema reservado**: `docs/esquema-datos-v2.md` línea 25 ya declara la extensión
   `pgvector (memoria/RAG, cuando aplique)` — Fase 2 explícita desde antes de este documento.
2. Un **checklist de ingesta nunca ejecutado**: `knowledge/quantum/00-kb-fuentes.md` §6 lista 13
   documentos (papers arXiv, tutoriales, un dataset) "a descargar/convertir e indexar en
   `distributions/chimera/datasets/docs/`" — la intención de RAG existía, la ejecución no.
3. Un **módulo diseñado y no implementado**: `docs/arquitectura-reconciliada.md` ya nombra
   `Context/RAG` como módulo del engine y `document_retriever` como tool, marcados explícitamente
   "diseñado, no implementado en el demo".

**Alcance de este documento:** diseñar el sistema que cierra esas tres piezas — ingesta desde
fuentes heterogéneas (video, imagen, paper, repo), representación del conocimiento (KB y,
condicionalmente, KG), y sobre todo la parte que ningún RAG genérico tiene: **conocimiento con
procedencia verificable**, alineado a la capa DSSE/certificate que ya existe en
`engine/src/blite/certificate/`. Fuera de alcance: cuándo se construye (post-hackathon, sin fecha
comprometida), y cualquier cambio al runtime de producto actual — RAG/memoria de agente siguen
fuera del alcance del hackathon por regla de backlog (`knowledge/trust/13`, `knowledge/trust/17`).

**No-objetivo explícito:** este NO es el diseño del track vivo de triage de clases (eso ya se
ejecutó, ver `knowledge/quantum/_triage-map.md`). Es la versión "si esto se convirtiera en
infraestructura real" — para no reinventar el diseño desde cero si el equipo decide invertir en
esto después del hackathon.

## 2 · Ingesta multi-modal

Cuatro familias de fuente, cada una con su propio adaptador de extracción hacia texto plano +
metadata de procedencia (fuente, timestamp/página, autor si se conoce, licencia si aplica):

| Fuente                        | Extracción                                                                                                                                                                        | Notas de costo (aprendidas en el ejercicio de triage)                                                                                                       |
| ----------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Video/audio (clases, charlas) | Captions nativos primero (`yt-dlp --write-auto-subs`, gratis, minutos) → whisper/Groq solo si no hay captions                                                                     | YouTube rate-limita (`HTTP 429`) si se piden demasiados idiomas/videos seguidos sin pausas — pedir solo los idiomas necesarios y espaciar requests          |
| Slides/imágenes               | OCR (Tesseract) para texto denso; visión (modelo multimodal) para diagramas/fórmulas que el OCR rompe                                                                             | las fórmulas con notación bra-ket/Ising suelen romper OCR clásico — reservar el paso de visión para slides con matemática, no correrlo sobre todo el corpus |
| Papers (PDF)                  | extracción de texto + estructura (secciones, referencias) vía parser PDF; NO reinventar — `knowledge/quantum/00-kb-fuentes.md` ya tiene 8 arXiv IDs curados listos para este paso | curaduría humana (Sebas) ya hizo la selección; el pipeline no necesita descubrir papers, solo ingerir los ya elegidos                                       |
| Repos (GitHub)                | parsing de README + estructura de directorios + licencia (vía `gh api`, patrón ya usado en `knowledge/quantum/06`)                                                                | la nota 06 ya demuestra el patrón a mano: licencia primero, código solo si es MIT/Apache — automatizar ese chequeo, no solo el fetch                        |

**Lección operativa del ejercicio de triage (2026-07-21):** el mayor costo real no fue transcribir
— fue la **latencia de indexación de fuentes recién compartidas** (una carpeta de Drive compartida
el mismo día tardó más de 20 minutos en aparecer en búsqueda). Cualquier pipeline de ingesta debe
asumir que "recién compartido" ≠ "disponible para listar", y no bloquear el resto del pipeline
esperando una fuente lenta.

## 3 · Orquestación multi-modelo

Dos niveles de modelo, nunca uno solo, por costo y porque el trabajo es genuinamente distinto:

- **Nivel barato/bulk** (Fable 5, Groq, o el modelo más barato disponible por API): transcripción,
  limpieza de OCR, triage inicial (tema en 1 línea + tags), deduplicación. Alto volumen, baja
  ambigüedad por ítem. En el ejercicio de triage esto se aproximó con agentes paralelos —el patrón
  es correcto, el ruteo a un modelo específicamente barato quedó pendiente de infraestructura
  (no había una ruta directa a Groq/Fable desde este harness en el momento del ejercicio).
- **Nivel fuerte** (Opus/Sonnet): extracción de las notas destiladas finales, resolución de
  conflictos entre fuentes, decisión de qué entra al grafo como entidad vs. qué queda como texto
  plano. Bajo volumen, alta ambigüedad, es donde importa la calidad de juicio.

**Regla de ruteo:** ningún ítem pasa del nivel barato al fuerte sin razón — el gap-diff contra el
KB existente (§7) es el filtro. Si el nivel barato ya confirma que el contenido está cubierto,
el nivel fuerte nunca lo toca. Esto es lo que mantuvo el ejercicio de triage manual barato: de 11
sesiones de bootcamp procesadas, cero requirieron extracción de nivel fuerte porque el gap-diff no
encontró huecos críticos.

## 4 · Representación del conocimiento: KB vs. KG

**Tesis central: empezar en KB (chunks + embeddings, pgvector), escalar a KG solo si aparecen
queries multi-salto reales.** Un knowledge graph que nadie recorre en más de un salto es un índice
invertido con pasos extra.

**Cuándo el grafo se gana su costo:** cuando la pregunta natural del equipo/agente es
composicional — "¿qué algoritmos comparten la misma ancla de verificación que QAOA?" (salto
algoritmo→ancla→algoritmo) o "¿qué papers validan el approach que ya descartamos por la razón X?"
(salto decisión→razón→paper). El catálogo `knowledge/quantum/07-catalogo-algoritmos.md` ya
modela esto en tabla plana (algoritmo, cuándo usarlo, madurez, estado, ancla) — es exactamente el
esquema de entidades que un KG formalizaría:

```
Problema (Clase A/B/C/D) —resuelve_con→ Algoritmo —requiere→ Ancla (clase decisoria)
Algoritmo —validado_por→ Paper/Repo (con licencia)
Algoritmo —descartado_por→ Razón (con fuente: nota o clase del bootcamp)
```

**Recuperación:** para KB, similitud vectorial + reranking simple basta. Para KG (si se activa),
patrones de query fijos sobre el esquema de arriba (no un lenguaje de grafos genérico) —
la mayoría de las preguntas del equipo son "dado un problema, qué candidatos y por qué", no
exploración abierta del grafo.

## 5 · Alineación provenance/trust — el diferenciador real

Esto es lo que separa este diseño de un RAG genérico, y por lo que vale la pena que sea Chimera
quien lo construya y no una librería de terceros: **el conocimiento ingerido no solo se recupera,
se verifica.**

Cada nota destilada (KB o nodo de KG) lleva un bloque de procedencia — fuente exacta, timestamp o
página, hash del contenido origen — con la misma disciplina que `evidence` ya exige para los
claims de los proponentes cuánticos (`docs/spec-confianza-v3-2.md`). Atarlo a la capa DSSE/
certificate existente (`engine/src/blite/certificate/dsse.py`, `canonical.py`) significa que una
nota de conocimiento puede, en principio, tener el mismo tipo de certificado firmado que un
resultado de solver: no "esto es plausible según el RAG" sino "esto viene verificablemente de la
fuente X, timestamp Y, y no fue alterado desde la ingesta". Es la misma tesis del proyecto
(`confiable ≠ plausible`) aplicada a conocimiento en vez de a resultados de optimización.

**Restricción heredada de INV-2/PR2:** el pipeline de ingesta y el LLM que extrae/sintetiza notas
son _proponentes_ de conocimiento, nunca verificadores de nada aguas abajo. Si este sistema
alimentara alguna vez al Formulador de Chimera (§6 nota de drift), la verificación de las
propuestas del Formulador sigue siendo 100% no-modelo — el KG no cambia esa frontera, solo mejora
la calidad de lo que el Formulador propone.

## 6 · Loop de profundización incremental

No ingerir todo de una vez. El costo debe ser proporcional a la relevancia:

1. **Triage barato** sobre toda fuente nueva (tema, tags, relevancia estimada — el patrón ya
   validado en el ejercicio de 2026-07-21).
2. **Gap-diff** contra el KB/KG existente — ¿esto ya está cubierto?
3. **Extracción cara** solo para gaps confirmados por un humano (el checkpoint que el ejercicio
   llamó "A4" funcionó bien: barato de ejecutar, alto valor porque evita extracción especulativa).
4. **Re-triage periódico**, no continuo — cuando entra una fuente nueva o cuando un reto cambia de
   forma material (ver el histórico de "notas de drift" ya presente en `knowledge/quantum/07` §1.4
   como precedente de que los retos SÍ cambian de forma y el KB necesita poder señalarlo).

## 7 · Fases y costos (orden de magnitud, no comprometido)

| Fase | Qué construye                                                                                                     | Prerrequisito                                                            | Costo relativo                                                                                        |
| ---- | ----------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------- |
| 2.0  | Adaptadores de ingesta (video/imagen/paper/repo) + almacenamiento KB plano (pgvector, ya reservado en el esquema) | ninguno adicional al esquema v2 existente                                | bajo — mayormente conectar herramientas ya usadas en el ejercicio (yt-dlp, whisper/Groq, parser PDF)  |
| 2.1  | Orquestación multi-modelo con ruteo barato/fuerte + gap-diff automatizado                                         | 2.0                                                                      | medio — requiere acceso a un modelo barato real (Groq/Fable con API key), no solo el modelo de sesión |
| 2.2  | Bloque de procedencia + atado a DSSE/certificate                                                                  | 2.0, y que el certificate layer siga siendo la fuente de verdad de firma | medio-alto — toca código de producto (`engine/src/blite/certificate/`), necesita su propio ADR        |
| 2.3  | Knowledge graph (solo si 2.0-2.2 exponen queries multi-salto reales sin resolver)                                 | 2.0-2.2 en uso real por al menos unas semanas                            | alto, y condicional — no se construye por adelantado                                                  |

**Regla de decisión para pasar de fase:** cada fase se activa por evidencia de necesidad (una
pregunta real sin responder, un cuello de botella medido), no por calendario. Es la misma
disciplina de "catalogado vs. implementado" que `knowledge/quantum/07` ya aplica a algoritmos —
aplicada acá a infraestructura de conocimiento.

## 8 · Qué NO hacer (heredado del ejercicio que motivó este documento)

- No construir el grafo antes de tener preguntas reales que lo necesiten (§4).
- No mezclar este sistema con el runtime de producto de Chimera mientras RAG/memoria sigan
  fuera del alcance del hackathon (regla de backlog vigente en `knowledge/trust/13`).
- No gastar modelo fuerte en transcripción o triage masivo — es trabajo de nivel barato (§3).
- No commitear corpus crudo (transcripts, PDFs descargados) al repositorio — vive en storage
  aparte; el repo solo versiona las notas destiladas con procedencia, igual que
  `knowledge/quantum/` hoy.
