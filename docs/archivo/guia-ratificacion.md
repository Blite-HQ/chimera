# Guía de ratificación del diseño congelado — Sebas · Steven · Geovanni

> **Estado: HISTÓRICO (2026-07-30, archivado por #112).** Proceso «CERRADA (2026-07-21)» de
> la era de dueños; cede autoridad al freeze, como su propio texto declara.
>
> **Estado: CERRADA (2026-07-21 — proceso completado; conservada como registro).** Los tres dueños
> respondieron dentro de la ventana y sus ratificaciones están auditadas
> (`docs/research/ratificacion-real-sf.md`) y convergidas contra el contrapeso simulado
> (`docs/research/convergencia-simulada-real-sf.md`, veredicto CONVERGEN). **La autoridad vigente es
> el freeze con sus 5 registros de cierre** — donde esta guía difiera (p. ej. modelo del demo:
> hoy Ollama Cloud [S-F-real]; identidad de ieee30: ABIERTA con 3 formas, decide Sebas), **el freeze
> manda**. Los pendientes de dueño viven en los registros del freeze, no acá.
>
> **⚠️ Actualización S-F (2026-07-20) — leer antes de ratificar.** Una auditoría adversarial
> pre-ratificación aplicó supersesiones al freeze (todas marcadas **[S-F]**, causas en su
> "Registro de cierre (S-F)"): ratifican sobre la versión YA corregida. Lo que cambia para
> ustedes: **(1)** la respuesta mínima es un **ack** ("OK mi plano" — 30 segundos); sin ack al
> **22-jul**, Dylan escala directo — el silencio ya no ratifica solo; **(2)** los ítems
> **ejecutables** de Sebas no son ratificables por silencio (el silencio no ejecuta scripts),
> pero la auditoría ya corrió la receta del corpus (6/6 digests, lock reparado) y la
> enumeración de ieee30 (óptimos confirmados) — su corrida **confirma, no estrena**; **(3)**
> por ratificación verbal de Geovanni (19-jul): todo el mes LOCAL, stretch = Fargate **o EKS**,
> y los modelos van **por API con keys** — Ollama queda como perfil opcional archivado
> (freeze §15.7 [S-F]); **(4)** el fixture de la falla sembrada quedó congelado:
> ieee14-flujo, **bus 1** (freeze §15.5 [S-F] — a Sebas le queda el criterio narrativo).

---

## 1 · Contexto general en 5 minutos (para los tres)

**Qué estamos construyendo.** Chimera es una plataforma de investigación donde cada resultado
no solo se calcula — se **verifica contra anclas que no son modelos** (un solver exacto, un
simulador de flujo de potencia, un corpus con óptimos probados) y se entrega con un
**certificado de confianza** firmado, verificable offline por un tercero. La tesis en una
línea: **lo cuántico (o cualquier modelo) propone; las anclas no-modelo verifican; confiable ≠
plausible.** Para el evento: resolvemos el Challenge 1 (particionamiento Max-Cut de una red
eléctrica) y el diferenciador es que la respuesta llega verificada, honesta y auditable — que
es exactamente lo que la rúbrica oficial premia ("rigor y honestidad por encima de la
ambición", reproducibilidad con deducción global si falta).

**Los cuatro planos y sus dueños** (igual que `CODEOWNERS`):

| Plano                   | Qué cubre                                                      | Dueño    |
| ----------------------- | -------------------------------------------------------------- | -------- |
| Confianza + integración | verificación, eventos, certificado, identidad, SSE, Studio     | Dylan    |
| Ejecución               | gateway/pipeline, runtime/loop, registry, serving/model router | Steven   |
| Ciencia                 | formulación QUBO/QAOA, corpus, estadística, ruta Quantinuum    | Sebas    |
| Infra                   | compose/despliegue, cola de jobs, secretos, dry-runs           | Geovanni |

**Qué pasó hasta hoy (línea de tiempo corta).** (1) Cada plano investigó y dejó notas en
`knowledge/` — las de ejecución las escribió Steven, las de ciencia parten del material de
Sebas, las de infra del de Geovanni. (2) Se consolidó todo y se validó la convergencia con la
spec de la capa de confianza v3.2 (`docs/convergencia-diseno-v32.md`). (3) Un panel adversarial
de stress tests produjo una lista de ajustes priorizados (los "P0/P1" que van a ver citados).
(4) Llegó el **enunciado oficial**: el C1 formula Max-Cut, emulador H2 de Quantinuum (exacto
≤26 qubits), Goemans-Williamson con CVXPY como baseline obligatorio, media±std de ≥5 corridas,
slot de 5 minutos. (5) El 18-jul se cerró el **contract freeze**: `docs/contract-freeze.md`
fija los contratos del mes, con TODAS las decisiones tomadas.

**Qué significa "congelado" y qué sigue.** Los contratos (tipos, puertos, eventos, esquema SQL)
están fijos; sobre ellos se generan los seeds de specs y tests, y sobre los seeds cada quien
desarrolla su área. Cambiar algo congelado no es editarlo: es una supersesión con causa
registrada — por eso este paso de ratificación importa AHORA, antes de construir.

**El mapa de documentos** (autoridad completa en `docs/README.md`):
`invariants.md` + `base-logica-formal.md` = constitución (no se toca) ·
`spec-confianza-v3-2.md` = vocabulario normativo de la capa de confianza ·
`contract-freeze.md` = LOS CONTRATOS DEL MES (el doc que ratifican) ·
`especificacion-contratos-v2.md` / `esquema-datos-v2.md` = semillas TS/SQL ·
`arquitectura-python.md` = arquitectura activa.

**Vocabulario mínimo para leer el freeze** (2 minutos): un **claim** es una afirmación
verificable ("esta partición es óptima para esta instancia"). Un **Verifier** la contrasta
contra un ancla y emite una **Attestation** con veredicto tri-estado (`pass · fail ·
inconclusive` — "no pude" es un resultado de primera clase, jamás se disfraza). La fuerza se
mide en **niveles AL0–AL4** con techo según la **clase decisoria** del verificador
(FORMAL_EXACT como CP-SAT llega a AL4 con checker independiente; EXECUTION como pandapower a
AL3; GROUND_TRUTH como el corpus a AL3; PROPERTY_RULE a AL2). La **criticidad C0–C3** dice
cuánta fuerza exige la Policy (C0 = "no verifiques" — el anti-teatro está integrado). El
**certificado** empaqueta conclusiones CON su alcance, supuestos y nivel titular = el mínimo
del camino crítico, jamás promedio. Los modelos/heurísticas probabilísticas son **Signal**:
informan, nunca deciden.

## 2 · Qué es "ratificar" (y qué NO es)

- **Es la revisión final del dueño sobre decisiones ya tomadas que llevan su nombre.** El
  diseño se entregó terminado; ustedes verifican que su plano quedó fiel a su investigación y
  a su criterio. "Ajustable bajo su criterio" es literal: si algo de tu área te parece mal,
  se cambia — sos el dueño.
- **Cómo responder (una de dos):** (a) "OK mi plano" — un mensaje a Dylan basta; o (b) objeción
  puntual: qué ítem, qué cambiarías y por qué. Los ajustes se incorporan como supersesión con
  causa — rápido, sin drama. **[S-F] El ack (a) es OBLIGATORIO, no opcional:** sin ack al
  **22-jul**, Dylan escala directo (llamada/mensaje); al 23 sin respuesta, las objeciones
  P0/P1 del contrapeso de tu plano se incorporan igual (son verificables contra el repo) y tus
  ítems "solo humanos" pasan a decisión de Dylan. El silencio derrota además el 20% de
  Explicación: un dueño que no leyó es un dueño que no explica en Q&A.
- **Regla de oro antes de objetar:** si algo de TU plano quedó distinto de como lo dejaste en
  tus notas, **el porqué está escrito** (hay un addendum fechado en tu propia nota, o la
  resolución en `convergencia-diseno-v32.md` §3). Leé el porqué primero; si no te convence,
  ESA es exactamente la objeción que queremos oír.
- **Qué NO está en revisión:** la base lógica (`invariants.md`/`base-logica-formal.md` — la
  constitución, nunca bajo revisión), el kernel de la spec v3.2 (cambios = versión mayor,
  post-evento), el formato/estilo de los docs, y las decisiones de OTRO plano — si ves algo
  cruzado que te preocupa, marcáselo a Dylan en vez de proponerle el cambio al otro dueño.
- Dónde está tu lista exacta: `contract-freeze.md` → sección **"Registro de cierre"** (punto 2)
  la resume por dueño; abajo está desplegada con checklist.

---

## 3 · Sebas — ciencia/cuántica (~90 min)

**Orden de lectura:** (1) §1 de esta guía · (2) `contract-freeze.md` §4 (tus anclas
re-etiquetadas por clase/AL), §11 (los campos de evidencia del claim proponente), §15.3
(corpus), §15.5 (falla sembrada) · (3) `knowledge/islanding/01` §1.4, §1.6, §1.8 y §2 ·
(4) el cierre de cada nota `knowledge/quantum/01–09` (cada una termina con "decidido —
ratificación final de Sebas" y dice qué) · (5) vistazo a `docs/perfil-stem-v1-0.md` §2
(tus herramientas curadas con parámetros fijados por digest).

**Checklist de validación:**

- [ ] **La estratificación del C1 (la decisión más importante de tu plano):** el corpus queda
      TAL CUAL (Max-Cut, alineado con el enunciado oficial — no se regenera); los chequeos físicos
      (`island_connectivity`, `power_balance`) viven como **análisis de limitaciones + extensión
      "constraint mixers"**, no en el camino core del claim de optimalidad. ¿De acuerdo?
- [ ] **S = 100** como parte de la definición de instancia (el redondeo es de la instancia, no
      error del solver) — islanding/01 §1.3.
- [ ] **Segunda ancla de ieee30 = enumeración exhaustiva vectorizada [S-F: YA CORRIÓ]** —
      la auditoría ejecutó las 2²⁹ asignaciones por convención y **ambos óptimos coinciden con
      CP-SAT** (35 / 32 170; evidencia con spec de máquina en islanding/01 §1.4). **[convergencia
      EC-3] La FORMA de registro de la identidad es TU llamada, con TRES opciones** (freeze §15.3):
      (a) re-estampar `@v1` con los digests nuevos, (b) versionar a `@v2`, (c) attestation externa
      sobre el MISMO digest (los JSON no se mutan). Ninguna se aplica hasta tu palabra — decila en
      el ack. GW-SDP solo cota de cordura.
- [ ] **Ejecutable (confirmación, ya no estreno):** regenerá el corpus con la receta exacta de
      islanding/01 §1.9 ([S-F]: `uv sync --all-packages --extra pandapower --extra ortools
--extra networkx`) y compará los 6 digests (§1.6 — por digest, jamás por bytes: Prettier
      reformatea los JSON). La auditoría ya reprodujo 6/6 con el lock reparado del repo.
- [ ] **Identidad del corpus:** `dataset_id = islanding-corpus/<instancia>-<convencion>@v1` ↔
      digest embebido (tabla completa en freeze §15.3).
- [ ] **Campos de evidencia (§11):** `circuit_digest`; `approximation_ratio` reportado como
      media±std de ≥5 corridas con seeds (jamás "la mejor"); `seeds.*`; `repair.*` viviendo en la
      extensión (no en el core); `mitigation.*` del corrector; y los multi-backend de tu nota 08
      (`transpiled_circuit_digest`, `backend_id`+versiones, `noise_config_digest`).
- [ ] **Consenso (ajuste a tu quantum/04 §4):** la réplica de MUESTREO con seeds pinned ahora
      SÍ es decisoria (pata CONSENSUS_REPLICATION, techo AL2); la concordancia entre modelos sigue
      siendo Signal. El addendum en tu nota explica el porqué.
- [ ] **Falla sembrada (§15.5) [S-F: vector CONGELADO — validá el criterio narrativo]:**
      ieee14-flujo, **bus 1** (0-indexed, bus de generación): degradación máxima 57 070 → 32 597
      (ratio 0.5712). El cómputo de los 14 flips probó que el bus NO podía elegirse a ojo: el
      flip del bus 7 degrada CERO (óptimo degenerado), y en uniforme los buses 0/1/11 también.
      Lo matemático está verificado 2× — lo tuyo es el guion físico (¿preferís otra historia de
      isla? decilo en el ack).
- [ ] **Tu entregable pendiente (el único dato que falta del plano):** `cr8` (~8 nodos desde
      los datos abiertos del ICE — datos-ice-se.opendata.arcgis.com, sugerencia textual del
      enunciado) + una instancia de **6 nodos** (`cr6`); mismo formato, doble ancla, digest.
      IDs ya reservados en freeze §15.3.

**Dónde más vale tu ojo (top 3):** la estratificación core-vs-limitaciones · el presupuesto
real de la enumeración vectorizada · el consenso-de-muestreo-como-AL2.

## 4 · Steven — plano de ejecución (~75 min)

**Orden de lectura:** (1) §1 de esta guía · (2) `contract-freeze.md` §1 (manifest/registry/
dispatcher), §2 (EventStore), §3 (vocabulario de eventos y máquinas de estado), §8 (pipeline),
§13 (Run jerárquico), §15.7 (model router) · (3) `docs/especificacion-contratos-v2.md`
(las marcas `[S-E]` señalan cada corrección) · (4) los **addenda fechados en TUS notas
`execution/01` y `execution/07`** — ahí está el porqué de los dos cambios sobre tu
investigación · (5) el bloque "Cerrado (S-E)" de `knowledge/execution/README.md`.

**Checklist de validación:**

- [ ] **Manifest v2 (§1):** sin `protocol`; con `interaction` (`request_response|job|stream`) y
      `execution_profile` (`in-process|service|remote-job`, default in-process, la distribución lo
      sobreescribe). Despacho: `remote-job` retorna `JobRef` (jamás Result síncrono); perfil no
      soportado ⇒ `NotImplementedError`, nunca fallback silencioso.
- [ ] **Las 8 etapas y la disolución de tu etapa `policy` (el cambio más grande sobre tu nota
      01):** `identity → authorization → guardrails → provenance:pre → mediation → verification →
provenance:post → egress`; la Policy se fija por digest al crear el case y la etapa de
      verificación la LEE — no es una etapa por invocación. Porqué: addendum de tu nota 01 +
      convergencia C2.
- [ ] **Tu pregunta §8.4 (reautorización a mitad de pipeline), cerrada así:** fail-closed —
      si el despacho revela un permiso distinto al evaluado en la etapa 2, el run falla y se
      re-invoca completo; jamás re-evaluación en vuelo.
- [ ] **Run jerárquico (cambio sobre tu nota 07):** se confirmó tu opción A (`stream_id =
run_id`, un stream por run) Y se agregó `parent_run_id` — sub-runs con stream propio que
      aportan claims al run raíz (el case/certificado siempre cuelga del raíz). Porqué: addendum
      de tu nota 07.
- [ ] **Semántica fijada:** step↔job 1:1 en Fase 1 (paralelismo = varios steps); al cancelar
      el run, un step RUNNING no recibe evento terminal — la proyección lo reporta `interrupted`;
      `max_steps` obligatorio.
- [ ] **Idempotencia (regla segura del mes):** `side_effects` manda — sin idempotencia
      garantizada NO hay reintento automático de pasos external (escala a humano con override
      registrado). El mecanismo fino es TU diseño en la fase de seeds (freeze §15.8).
- [ ] **Model router (tu frontera con Dylan, §15.7) [S-F]:** `ModelPort` (Protocol) en
      `serving` (cero red — AX3 por construcción) + `ModelServer` (adapter) en `protocols` bajo
      INV-6, envolviendo LiteLLM `Router` con un solo `model_list` — ahora **modelos por API
      con keys** (ratificación verbal de Geovanni; Ollama = perfil archivado) + backend
      **`replay`** con contrato de 5 puntos: **miss ⇒ `model.call.failed {replay_miss}`, JAMÁS
      passthrough a red** — exigí ese fail-closed por escrito, es TU frontera del día D.
- [ ] **[S-F] Las 3 reglas del run jerárquico (§13) — tu runtime produce los huérfanos si
      faltan:** cascada de cancelación (`parent_cancelled` + rechazo de appends post-terminales + barrido con `cancel(ref)`), `●ClaimEmitted {claim_digest, sub_run_id,
sub_run_provenance_hash}` al raíz, herencia de `policy_digest` fail-closed.
- [ ] **[S-F] Matriz `interaction × execution_profile` (§1):** se valida al CARGAR el
      DistributionManifest — override a `remote-job` solo si `interaction: job`; `stream` ⇒
      `NotImplementedError`. Es tu `Dispatcher` el que quedaba en contradicción.
- [ ] **[S-F] Timing:** el walking skeleton vence ~20-jul, ANTES del cierre del 23 — ratificá
      **§2/§3 PRIMERO** (es lo que el skeleton toca; incluye los streams de sistema
      `system:<componente>` que tu primer `registry.loaded` necesita).
- [ ] **Registry:** descubrimiento tolerante a fallos (excepción POR entry point), eventos
      `registry.loaded` / `registry.capability_load_failed` con `service:runtime`; versiones
      duplicadas se resuelven por pin del DistributionManifest (default determinista).
- [ ] **Tuyo al arrancar construcción:** el walking skeleton (compose postgres+api+studio con
      UN evento real de punta a punta, 48h) y el PR único con TODAS las deps.

**Dónde más vale tu ojo (top 3):** la etapa policy disuelta · `parent_run_id` · `ModelServer`
con LiteLLM en `protocols`.

## 5 · Geovanni — infra (~45 min)

**Orden de lectura:** (1) §1 de esta guía · (2) `contract-freeze.md` §7 (solo el bloque de
firma/custodia de llaves), §15.1 (soberanía), §15.4 (camino dorado/NO-va — Fargate), §15.8
(huecos con tu nombre) · (3) `knowledge/infra/01` §R (tu reconciliación, asignada) · (4) los
cierres de `infra/02` (cola) e `infra/03` (demo dual).

**Checklist de validación:**

- [ ] **Escalera de custodia de llaves (§7):** escalón 1 = env/archivo (hoy) → 2 = OpenBao
      Transit (Fase 2) → **3 = PKCS#11/HSM, mismo Protocol, declarado desde ya** (es contrato,
      no implementación de este mes — tu frontera con Dylan está marcada en trust/15 §4). Y la
      doctrina: "el keypair del certificado pertenece a la organización operadora, no al software".
- [ ] **Cola de jobs:** Procrastinate sobre el MISMO Postgres del event store, **sin Redis**
      (tu nota 02 §1.4; la cadena exacta con worker está en tu nota 03 §1.3 y quedó congelada
      en freeze §15.4 [S-F]) — el compose canónico del mes: `postgres + api + worker + studio`.
- [ ] **Demo dual [S-F — tu ratificación verbal del 19-jul, confirmala]:** el local manda;
      cloud degradado a stretch (**Fargate o EKS**) — solo se provisiona si el local quedó
      verde el 27 (P1-10); si se activa, subnet pública+IP para el pull de ECR (lo simple;
      VPC endpoints = forma de producción).
- [ ] **Modelos [S-F — supersede la decisión "Ollama ~3B"]:** por tu ratificación verbal, los
      modelos del mes van **por API con keys** (Anthropic + abiertos servidos por API; keys
      como secret files — jamás en imagen ni repo); `ollama` queda como perfil opcional
      archivado. El modo `replay` sigue siendo la config del día D (freeze §15.7 [S-F]) —
      el air-gap se prueba igual.
- [ ] **Calendario de dry-runs (27/29-jul)** — reconciliado con el freeze en tu nota 03 §1.5
      (bloque [S-F]: cloud condicionado al verde del 27; dry-run 2 con `replay`; segunda
      máquina del verify; reset de `pgdata`); lo ratificás vos con el equipo. **Además: decidí
      YA qué laptop es el equipo del demo y registrá su RAM** (nota 03 §5.8).
- [ ] **Tu reconciliación pendiente:** `infra/01` §R contra `invariants.md` (asignada a vos;
      los puntos detectados están listados ahí — ninguno toca contratos del engine este mes).
- [ ] **Huecos Fase 2 con tu nombre (§15.8):** ciclo de vida del recinto air-gapped (cómo
      entran parches/modelos/policies después del corte — bundles firmados en frontera) y la
      métrica north-star con Dylan.

**Dónde más vale tu ojo (top 3):** el escalón HSM + doctrina de llaves · Fargate-como-stretch ·
el calendario.

## 6 · Los tres juntos (15 min — decisiones de EQUIPO)

- [ ] **Posición operativa (§15.2, van a repetirla en todo Q&A — memorizarla VERBATIM,
      incluido "del cliente"):** "Chimera es análisis y verificación fuera de línea; no se
      conecta a SCADA/EMS ni actúa sobre la red; su salida es un expediente certificado que
      alimenta el procedimiento de aprobación vigente **del cliente**".
- [ ] **Camino dorado + lista NO-va (§15.4):** qué se construye este mes y qué explícitamente
      NO (Fase 2 entera, MCP, LLM en vivo, emulador en vivo, IEEE-30 cuántico, corrector en vivo…).
      Es la decisión de scope del equipo — mejor objetarla hoy que descubrirla el 25.
- [ ] **AcceptanceAuthority = el PI del programa (`user:dylan`)** para la elegibilidad C3 de
      verificadores (freeze §4) — designado por la Policy de la distribución.
- [ ] Recordatorio de rúbrica: **Explicación = 20%** — los cuatro deben poder explicar el
      código. Esta guía es el primer paso de ese 20%.

---

**Después de la ratificación:** se generan los seeds (specs en `docs/specs/`, tests semilla por
plano, `challenge1/reproduce.py`, el fixture de la falla sembrada, `scripts/verify-bundle.py`,
el PR único de dependencias) y cada quien desarrolla su área sobre ellos. Cualquier ajuste que
salga de esta ratificación se incorpora ANTES de eso — por eso el plazo del 23.
