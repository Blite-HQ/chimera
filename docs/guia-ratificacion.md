# Guía de ratificación del diseño congelado — Sebas · Steven · Geovanni

> **Estado: VIGENTE (proceso — caduca al cierre de la ratificación).** El diseño del mes quedó
> **congelado el 2026-07-18** (`contract-freeze.md`). Esta guía existe para que cada dueño pueda
> ratificar SU parte sin leerse todo el repo: da el contexto general, dice exactamente qué
> validar por área, dónde está el porqué de cada decisión, y cómo responder.
> **Plazo propuesto: 23-jul (feature freeze).** Sin objeción a esa fecha, la parte queda
> ratificada y se arranca la construcción encima (seeds de specs/tests → features).

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
  causa — rápido, sin drama.
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
- [ ] **Segunda ancla de ieee30 = enumeración exhaustiva vectorizada** (numpy por bloques,
      x₀=0, 2²⁹ asignaciones; GW-SDP solo como cota de cordura). Hoy ratificás la DECISIÓN; el
      código se integra al script §1.9 en la fase de seeds y ahí la corrés.
- [ ] **Ejecutable ya:** regenerá el corpus con el script actual de islanding/01 §1.9 y
      compará los 6 digests contra los archivos congelados (receta §1.6).
- [ ] **Identidad del corpus:** `dataset_id = islanding-corpus/<instancia>-<convencion>@v1` ↔
      digest embebido (tabla completa en freeze §15.3).
- [ ] **Campos de evidencia (§11):** `circuit_digest`; `approximation_ratio` reportado como
      media±std de ≥5 corridas con seeds (jamás "la mejor"); `seeds.*`; `repair.*` viviendo en la
      extensión (no en el core); `mitigation.*` del corrector; y los multi-backend de tu nota 08
      (`transpiled_circuit_digest`, `backend_id`+versiones, `noise_config_digest`).
- [ ] **Consenso (ajuste a tu quantum/04 §4):** la réplica de MUESTREO con seeds pinned ahora
      SÍ es decisoria (pata CONSENSUS_REPLICATION, techo AL2); la concordancia entre modelos sigue
      siendo Signal. El addendum en tu nota explica el porqué.
- [ ] **Falla sembrada (§15.5):** el vector es tuyo — mover 1 bus de la partición verificada
      debe dar `fail` inequívoco en milisegundos, jamás `inconclusive`. ¿Ves un bus candidato en
      ieee14?
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
- [ ] **Model router (tu frontera con Dylan, §15.7):** `ModelPort` (Protocol) en `serving`
      (cero red — AX3 por construcción) + `ModelServer` (adapter) en `protocols` bajo INV-6,
      envolviendo LiteLLM `Router` (un solo `model_list`: cloud + Ollama) + backend **`replay`**
      como tercera config de primera clase; eventos `model.call.requested/completed` con digests.
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
      (tu nota 02) — el compose del mes queda `postgres + api + worker + studio [+ ollama]`.
- [ ] **Demo dual:** el local manda; **Fargate degradado a stretch** — solo se provisiona si el
      local quedó verde el 27 (P1-10); si se activa, subnet pública+IP para el pull de ECR (lo
      simple; VPC endpoints = forma de producción).
- [ ] **Modelo de Ollama (decisión tuya con Steven):** chico ~3B cuantizado (default
      `llama3.2:3b`), que quepa junto al statevector de ieee14 en la RAM del equipo del demo; se
      mide en el dry-run 1. (El LLM está FUERA del camino crítico del demo — el modo `replay` es
      la config del día D.)
- [ ] **Calendario de dry-runs (27/29-jul)** — está como propuesta en tu nota 03; lo ratificás
      vos con el equipo.
- [ ] **Tu reconciliación pendiente:** `infra/01` §R contra `invariants.md` (asignada a vos;
      los puntos detectados están listados ahí — ninguno toca contratos del engine este mes).
- [ ] **Huecos Fase 2 con tu nombre (§15.8):** ciclo de vida del recinto air-gapped (cómo
      entran parches/modelos/policies después del corte — bundles firmados en frontera) y la
      métrica north-star con Dylan.

**Dónde más vale tu ojo (top 3):** el escalón HSM + doctrina de llaves · Fargate-como-stretch ·
el calendario.

## 6 · Los tres juntos (15 min — decisiones de EQUIPO)

- [ ] **Posición operativa (§15.2, van a repetirla en todo Q&A):** "Chimera es análisis y
      verificación fuera de línea; no se conecta a SCADA/EMS ni actúa sobre la red; su salida es
      un expediente certificado que alimenta el procedimiento de aprobación vigente".
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
