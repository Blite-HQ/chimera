# CHIMERA — Validación a profundidad de la ratificación simulada (S-F) · 2026-07-19

> **Qué es esto.** Segunda pasada sobre el acta `ratificacion-simulada-sf.md`: 4 verificadores
> independientes con postura de **refutación** (asumir que cada hallazgo está mal hasta que la
> evidencia primaria del repo lo confirme), que además barrieron cada dominio MÁS ALLÁ de lo que la
> guía pregunta — incluido el **plano de confianza (dueño Dylan), que ningún checklist de la guía
> revisa**. Ejercicio personal: vive solo en la rama `ejercicio/sf-ratificacion-simulada`.
> Cero archivos del repo modificados por la verificación.

## 1 · Resultado global

| Dominio               | Hallazgos del acta | Confirmados | Matizados   | Refutados | Nota                                                                                                                                                                       |
| --------------------- | ------------------ | ----------- | ----------- | --------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Ciencia (Anexo A)     | 5                  | 5           | 0           | 0         | Crash del lock **reproducido en vivo**; 6 digests regenerados 2 veces; cada número de O5 recomputado al dígito (57 070 / 32 597 / 0.5712 / degeneración del bus 7 exacta)  |
| Ejecución (Anexo B)   | 11                 | 11          | 0           | 0         | Evidencia línea a línea; un argumento secundario matizado en Obj 3 (la proyección SÍ podría derivar `awaiting-verification` de `●VerificationStarted` — eso decide el fix) |
| Infra (Anexo C)       | 7 + 7 riesgos      | 6 + riesgos | 1 (O6)      | 0         | O6: la sustancia (compose no congelado) es cierta; la letra "solo en guía + README" era imprecisa (también vive en infra/03)                                               |
| Equipo/guía (Anexo D) | 12                 | 11          | 2 con matiz | 0         | D-9: el "(§13" colgante es referencia a backlog externo, no errata interna — el fix cambia                                                                                 |

**Veredicto compartido de los 4 verificadores: el acta no infló problemas** — todos los hallazgos
sobrevivieron la refutación con evidencia primaria, ninguna objeción invalida una decisión de
diseño congelada, y los fixes van en la dirección correcta (con los refinamientos de §2).

## 2 · Ajustes que la validación le hace a los fixes del acta

1. **Marca de las correcciones: S-F fechada, jamás `[S-E]` retroactiva.** S-E cerró el 18-jul;
   etiquetar correcciones de hoy como S-E falsearía el registro. Causa: "auditoría de ratificación
   S-F".
2. **Re-lock (P0 #1):** verificado que pandapower 3.3.3 + numpy 2.5.1 (lo que resolvería el lock
   hoy) también reproduce 6/6 digests. Endurecer además el floor del extra
   (`pandapower>=2.13` → `>=3.3`) para que una resolución futura no regrese a la combinación rota.
3. **`awaiting-verification` (P0 #2):** de las dos opciones del acta, la correcta es la (b) —
   sub-estado de proyección derivado de `●VerificationStarted/Completed`, misma doctrina que
   `interrupted`; un evento nuevo sería innecesario.
4. **Cascada de cancelación (P1 #7):** la disyuntiva "rechazar vs aceptar marcado `late`" NO puede
   quedar abierta: debe ser **rechazo** — un append post-terminal cambia los bytes del stream y
   rompe el recompute del `provenance_hash` de un certificado ya emitido. Además la cancelación del
   job en cola ya tiene maquinaria (`cancel(ref)` en infra/02:59) — solo falta cablearla.
5. **`●ClaimEmitted` (P1 #7):** payload `{claim_digest, sub_run_id, sub_run_provenance_hash}` — el
   hash del stream del sub-run encadenado en el evento del raíz pinnea transitivamente el trabajo
   (estilo Merkle); sin él, `sub_run_id` es un puntero sin integridad.
6. **Replay (P0 #3), 3 piezas que al fix del acta le faltaban:** la clave del fixture no puede ser
   solo `prompt_digest` (dos backends con el mismo prompt colisionan) — digest Regla 2 sobre el
   request canónico **incluyendo id de modelo/backend** con prefijo de dominio versionado; los
   fixtures en ContentStore necesitan `domain_id` (SO2); y el SET de fixtures del día D se pinnea
   por digest (manifest), o el modo grabación puede mutar la config del demo silenciosamente.
7. **`interaction`×`execution_profile` (P1 #8):** validar la matriz completa al CARGAR el
   DistributionManifest (fail-closed en deploy, no en la primera invocación), y cubrir la tercera
   celda: `interaction: stream` ⇒ `NotImplementedError` en Fase 1 (hoy no tiene semántica alguna).
8. **@v1/@v2 de ieee30 (P1 #5):** @v2 es el mínimo coherente; alternativa aún más limpia que Sebas
   podría preferir — no mutar los JSON y registrar la segunda ancla como attestation externa sobre
   el MISMO digest (separa identidad de instancia vs historia de verificación).
9. **Presupuesto de la enumeración (P1 #6):** registrarlo CON spec de máquina — el verificador
   midió 13.5 s/bloque (~7.2 min/convención) donde el acta midió 11.4 s (~6 min): mismo orden,
   ~20% de varianza entre máquinas; el número sin hardware no es reproducible.
10. **Llaves en compose (P2):** el fix file-based choca con la letra de trust/15 (prescribe env
    vars) — necesita convención `*_FILE` en el KeyProvider o entrypoint que exporte el env.
11. **Referencia "(§13" de trust/15 (P2):** no borrarla — nombrar el referente real (carril del
    backlog externo, misma fuente que "ficha G4").

## 3 · Hallazgos NUEVOS de los barridos extendidos

### 3.1 · Ciencia (E1–E5)

- **E1 (P1) — El cumplimiento del enunciado ("red regional REAL de 6–12 nodos") pende de cr8/cr6
  sin fallback compatible.** ieee9 (9, sintética), ieee14 (14 — fuera del rango), ieee30 (30): si
  cr8/cr6 no llegan, NADA del diseño congelado satisface "real" ni "6–12", y el criterio de
  suficiencia (p=1, r ≥ 0.6) se define sobre una instancia de 6 nodos que el corpus no tiene.
  Salvable: la convención `uniforme` solo necesita topología — que los datos ArcGIS del ICE SÍ
  dan. Declarar `cr8-uniforme`/`cr6-uniforme` construibles solo-topología y elevar cr8/cr6 a P1
  con gate de fecha (~25-jul).
- **E2 (P2)** — La fórmula oficial de r no está citada verbatim en ningún doc; si fuera sobre
  energías y no cortes, los números divergen brutalmente (r_C = 0.5712 vs r_E ≈ −0.02 en el
  ejemplo del acta). Registrar la fórmula textual del enunciado en quantum/00 §1.6.
- **E3 (P2)** — El protocolo "media±std de ≥5 corridas" no está pinneado como dato (¿qué varía
  entre corridas? ¿ddof?). Seed S-G: `replication_protocol` versionado con digest.
- **E4 (P2)** — Valores superseded (W=5.9, τ̂=0.3, g=2) siguen vivos sin marca en quantum/02 §1.3
  (λ=65.6) y quantum/04 §3 (~590 muestras) — la misma violación de "regla de oro" que el acta cazó
  en execution/03, en el plano de Sebas.
- **E5 (P2)** — El análisis de flips/degeneración (el que salvó al fixture de la mina del bus 7)
  no es parte del procedimiento de congelamiento de cr8/cr6 — si el clímax migra a cr8, la mina
  puede reaparecer. Añadirlo al checklist de §1.8.

### 3.2 · Ejecución (N1–N7)

- **N1 (P1)** — `unanchored_steps`/`coverage_stats` del **predicate mínimo del mes** (freeze:98,
  P0-2) no existen ni en `TrustCertificate` ni en `trust_certificates` — el gemelo exacto del
  patrón de la Obj 1 (`cancelled`), no cazado por el acta. Mismo lote de supersesión.
- **N2 (P1)** — **Los eventos sin run no tienen `stream_id` posible**: `stream_id = run_id` es LA
  convención congelada (§2) pero `registry.loaded`, `○PolicyChanged`, `●AnchorRegistered`… se
  emiten sin run, y `events.stream_id` es NOT NULL — el walking skeleton no puede escribir su
  primer `registry.loaded` sin inventar una convención no congelada. Declarar streams de sistema y
  acotar `provenance_hash` a streams de run.
- **N3 (P2)** — El evento de métricas por run (freeze:91, P1-14) no tiene `type` en el vocabulario
  cerrado — inemitible tal como está.
- **N4 (P2)** — `interaction: 'stream'` es valor congelado sin semántica de despacho (cubierto por
  el ajuste 7 de §2).
- **N5 (P2)** — Contratos citados por el freeze sin semilla: `Registry`, `DispatchStrategy`/
  `Dispatcher`/`JobRef`, `RunStep`, `KeyProvider`. Declarar "van directo a Python en S-G" o
  agregar sección.
- **N6/N7 (P2 menores)** — índice duplicado `idx_events_stream` vs el UNIQUE; `Attestation` TS sin
  `run_id` mientras la columna SQL es NOT NULL.

### 3.3 · Infra (I1–I11)

- **I1 (P2)** — La config del día D (`replay`) no tiene forma en el compose de diseño: ni valor de
  env documentado ni volumen para los fixtures.
- **I2 (P2)** — `image: ollama/ollama` sin tag = `latest` implícito, contra la doctrina "pin
  determinista jamás latest" del propio freeze.
- **I3 (P2)** — Incoherencia perfil↔default: `docker compose up` pelado no levanta ollama
  (`profiles: [local-llm]`) pero el api arranca apuntándole.
- **I4 (P2)** — El worker no tiene config de model router, pero infra/02 §5.3 dice que los jobs
  pasan por el router como cualquier llamador.
- **I5 (P2, si Fargate)** — El idle timeout del ALB (default 60 s) mata SSE de larga vida; en
  local falta además `proxy_read_timeout`. Heartbeat SSE + timeout ↑.
- **I6 (P2)** — **Nadie aplica el schema**: el compose no tiene paso de migraciones (ni DDL del
  event store ni `procrastinate schema --apply`) — lo primero que chocará el walking skeleton.
- **I7 (P2)** — `COPY . /app` sin `.dockerignore`: arrastra `.git`, `node_modules` y `./secrets/`
  a la imagen.
- **I8 (P2, pre-flip)** — **`.gitignore` no ignora `secrets/`** y el repo se hace público ~1-ago.
  Una línea, HOY.
- **I9 (P2)** — `docs/deployment.md` contradice infra en Fase 2: "Terraform/CDK automatizado" (vs
  Pulumi Automation API decidido) y "SQS/Redis" (vs doctrina sin-Redis).
- **I10 (P2)** — Air-gap: el bundle del Studio no debe referenciar CDNs (fuentes/íconos), y si la
  máquina de build ≠ equipo del demo falta el traslado sin registry (`docker save/load`).
- **I11 (P2)** — Licencias: sin problema P0/P1 para el flip (Mitiq GPL ya encuarentenada bien);
  único refinamiento: verificar el árbol TRANSITIVO de cvxpy en el PR único (versiones viejas
  instalaban ECOS **GPL-3.0** como default; pinnear una cuyo default sea Clarabel/SCS +
  pip-licenses) y conectar esa fila a la tabla L de infra.

### 3.4 · Plano de confianza (T1–T17) — el hueco estructural que nadie ratifica

La guía cubre ciencia/ejecución/infra/equipo; los §§4–7, 9–12 y 14 del freeze — el plano de Dylan,
EL diferenciador — no tienen revisor asignado. Este barrido es esa revisión que faltaba. Ninguno
contradice la constitución; varios son huecos que _permitirían_ estados que ella prohíbe.

- **T1 (P1-alto)** — **La Policy real del repo habla el vocabulario muerto que el freeze eliminó:**
  `distributions/chimera/policies/verification-default.yaml` usa `min_rung`/`escalation: # rung 7`
  y `policy.py:36` tiene `min_rung: int`, mientras freeze §4 decreta que `rung` desaparece y §6
  define la Policy como matriz C0–C3. El `policy_digest` (bytes exactos del YAML, Regla 1) que se
  estampa en cada run pinnearía HOY una política de vocabulario supersedido.
- **T2 (P1)** — **`titular_level` no está definido computablemente**: "mínimo del camino crítico"
  sin grafo de claims (Fase 2) no se puede computar; `conclusions[]` vacío es válido (S6) y el mín
  de conjunto vacío daría AL4 vacuo; omitir un claim débil de `conclusions[]` inflaría el titular
  sin detección. Fix de 3 líneas: titular := mín(conclusions[].level); camino crítico DEBE
  listarse; vacío ⇒ AL0.
- **T3 (P1)** — **Un `pass` sin ancla es representable** (`anchorDigest?` nullable sin
  restricción) — roza D10 de la constitución (verificada ⇔ existe ancla). El nullable es legítimo
  SOLO para `inconclusive`. `CHECK (verdict <> 'pass' OR anchor_digest IS NOT NULL)`.
- **T4 (P1)** — **El AL4 del demo no tiene dónde registrar al checker**: la spec exige
  `proof∅ {certificate_ref, checker_id, checker_verdict}` para AL4 y las semillas de Attestation
  no tienen `proof`/`coverage`/`reruns` — el titular-AL4 del pitch no puede demostrar la
  re-validación dentro del bundle.
- **T5 (P1)** — **"C3 exige 2 patas" es incomputable**: el conteo es por `independence_group`
  (spec:94/123) y ese campo no existe en ningún contrato. El demo no puede probar sus 2 patas ante
  un auditor.
- **T6 (P1)** — **"Attestations DSSE" del bundle: cuatro documentos, cuatro formas, ninguna firma
  persistida.** Decisión de 3 líneas (dueño Dylan): Fase 1 = attestations embebidas en el payload
  DSSE del certificado (una firma ampara todo; S2 declarado limitación Fase 1) y corregir §7.
- **T7 (P1)** — **`claim_digest` sin vista canónica**: el anexo pinnea `view(e)` para eventos pero
  jamás define qué campos entran en `C(claim)` — dos implementaciones honestas producirían digests
  distintos, exactamente la falla que el anexo existe para matar. `view(claim) =
{canonical_statement, scope}` + vector V6.
- **T8 (P1)** — Ratifica independientemente el hueco provenance_hash↔sub-runs del acta (Obj 5 de
  Steven); el fix con `sub_run_provenance_hash` (ajuste 5 de §2) lo cierra.
- **T9 (P2)** — El catálogo ● se adoptó como lista de nombres: mapeo a eventos con punto incompleto
  (~8 filas faltantes), `●CertificateReissued/Revoked` sin marca de fase vs `revocation: "none"`.
- **T10 (P2)** — El vector V2 del anexo congela `"rung": 1` en su payload — nota de 1 línea: "dato
  arbitrario del gate de hashing, NO forma normativa" (los vectores no se regeneran sin romper
  hashes).
- **T11 (P2)** — `verify-bundle.py` sin checklist explícito puede degradar a "firma válida":
  enumerar los 5 chequeos Fase 1 (firma/PAE, recompute provenance_hash, digests de deliverables,
  titular=mín, pass⇒ancla).
- **T12 (P2)** — Ratifica el drift Guardrail→`Detector`/`Signal` + `AuthzDecision` inexistente en
  semillas (ya en el acta como cruzado).
- **T13 (P2)** — Gemelo de N1 visto desde confianza (`coverage_stats`/`gap` por conclusión).
- **T14 (P2)** — `trust_certificates` con PK `run_id` no puede representar `●CertificateReissued`
  (contra L2): declarar "Fase 1: una emisión por run" o PK compuesta.
- **T15 (P2)** — La Policy §6 no tiene contrato semilla (solo el YAML muerto de T1): estampar que
  el seed Pydantic es S-G con dueño.
- **T16 (P2)** — Colisión de numeración D1–D5 (spec) vs D1–D22 (base lógica) — el freeze cita
  ambos sin desambiguar.
- **T17 (P2)** — `TrustCertificate.actor` embebe la `Identity` completa (un certificado
  compartible portaría los permisos del actor); el SQL ya lo hace bien (`actor_id`).

## 4 · Lista de acción consolidada post-validación

**P0 (antes de S-G — sin cambios del acta, todos confirmados, con los endurecimientos de §2):**
re-lock pandapower (+floor `>=3.3`) · semillas vs máquina de estados (`cancelled`, `max_steps`,
`awaiting-verification` opción (b)) **+ N1/T13 en el mismo lote** · contrato replay (con clave de
fixture backend+dominio y manifest pinneado) · fixture falla sembrada = ieee14-flujo bus 1.

**P1 (ventana de ratificación, antes del 23):** los 8 del acta confirmados (con ajustes de §2) **+
los nuevos**: T1 (Policy YAML al vocabulario §6), T2 (titular computable), T3 (pass⇒ancla), T4
(proof∅/AL4), T5 (`independence_group`), T6 (decisión DSSE), T7 (`view(claim)` + V6), N2 (streams
de sistema), E1 (cr8/cr6-uniforme como fallback de cumplimiento, gate ~25-jul).

**P2:** los del acta + E2–E5, N3–N7, I1–I11, T9–T17 — ninguno bloquea, varios son de una línea;
**I8 (`secrets/` al `.gitignore`) conviene hacerlo HOY** por el flip público del ~1-ago.

## 5 · Fase siguiente (pendiente de decisión de Dylan)

El plan acordado: con las ratificaciones validadas, un par de tests que demuestren que los cambios
mejoran algo real y no rompen nada. Propuesta concreta, en esta misma rama:

1. **Aplicar los fixes P0/P1 como supersesiones S-F fechadas** (docs + semillas + lock).
2. **Gates existentes** en verde: pytest invariants, lint-imports, tsc, hook de la marca.
3. **Tests nuevos que prueban el valor de cada fix**: la receta oficial del corpus corre y da 6/6
   digests con el lock re-lockeado (antes: crash) · script de flips como test del fixture (bus 1
   degrada 0.5712, bus 7 delata la mina si alguien lo cambia) · test de proyección que un
   `run.cancelled` es representable (antes: violaba el CHECK) · validación de la matriz
   interaction×profile · el YAML de Policy valida contra el schema §6.

---

## Anexo V-A · Verificador de ciencia (rol adversarial sobre Anexo A)

Método: postura de refutación; cada número recomputado desde los archivos congelados;
reproducciones ejecutadas de verdad en scratchpad; cero escrituras al repo.

### Tabla de veredictos (ciencia)

| Hallazgo                                                     | Veredicto                        | Evidencia primaria                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | Juicio del fix                                                                                                                 |
| ------------------------------------------------------------ | -------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| **O1 / P0 #1** — receta no ejecutable + lock roto            | **CONFIRMADO (las 3 patas)**     | (a) `uv.lock:1815-16` pandapower **3.1.2**, `:1641-42` numpy **2.5.1**, `:1763` ortools 9.15.6755, `:1623` networkx 3.6.1. (b) pandapower/ortools/networkx son extras opcionales en los pyproject de `capabilities/{sim,solvers,graphs}` — el sync default no los instala; reproducido: `uv run --no-sync python -c "import pandapower"` → `ModuleNotFoundError`. (c) **Crash reproducido en vivo**: pandapower 3.1.2 + numpy 2.5.1 + `pp.runpp(pn.case14())` → `ValueError: assignment destination is read-only`. (d) Con 3.3.3 + 2.5.0 el script §1.9 completo regeneró y los 6 digests reproducen EXACTOS (incl. márgenes 0.0298/0.0322/0.0090). (e) "ancla EXECUTION" literal: `contract-freeze.md:76` y `:206`. | **CORRECTO + endurecimiento**: 3.3.3 + numpy 2.5.1 (resolución actual) también reproduce 6/6; subir floor del extra a `>=3.3`. |
| **O2 / P1 #6** — ancla vectorizada "integrada" que no existe | **CONFIRMADO**                   | Freeze `:200` "integrada… se corre en la ratificación"; `islanding/01:41` ídem; el script: `FUERZA_BRUTA_MAX_N = 14` (`:130`), única enumeración `itertools.product` (`:172-181`), **numpy ni se importa**. Guía degrada en silencio (`guia:106-108`). Presupuesto medido independiente: 13.5 s/bloque → ~7.2 min/convención (~20% sobre el acta — varianza de máquina).                                                                                                                                                                                                                                                                                                                                             | **CORRECTO**; registrar presupuesto CON spec de máquina.                                                                       |
| **O3 / P1 #5** — colisión @v1 re-estampado                   | **CONFIRMADO con matiz de cita** | Freeze `:187` ("no se sobreescribe") y `:200` (mutar `metodos`) coexisten; la frase "el digest se re-estampa" vive en `islanding/01:41`, no en el freeze. La colisión real: se ordena mutar la identidad sin mecanismo de versionado.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                | **CORRECTO** (@v2 = doctrina `freeze:18`); alternativa más limpia: attestation externa sobre el MISMO digest.                  |
| **O4 / P2** — formateo                                       | **CONFIRMADO + causa raíz**      | Repo 33 líneas vs `json.dumps(indent=2)` 131; digest IGUAL / bytes DIFIEREN en los 6; el "(Prettier?)" confirmado: `package.json:30-32` lint-staged corre `prettier --write` sobre `*.json` en cada commit.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | **CORRECTO** — la opción buena es "comparación solo por digest canónico" (acoplar el writer a Prettier sería frágil).          |
| **O5 / P0 #4** — bus 7 CERO; bus 1 0.5712                    | **CONFIRMADO en cada número**    | Recompute propio: óptimo 57 070 reproduce; flip bus 7 → 57 070 (degradación 0; bus 7 = hoja colgante con única arista w=0, el condensador síncrono); flip bus 1 → 32 597 (máxima, 0.5712 exacto, respeta x₀=0, bus de generación); bus 0 → 33 831 y rompe x₀=0; uniforme: buses 0/1/11 degradan CERO y el óptimo uniforme tiene 16 testigos — más degenerado de lo que el acta dice.                                                                                                                                                                                                                                                                                                                                 | **CORRECTO**; ver E5 — el análisis de flips debe repetirse al congelar cr8/cr6.                                                |

Colaterales que aguantaron refutación: digests 6/6 = tabla freeze = embebidos · márgenes x.5
reproducidos · ieee9 bipartito (óptimo = |E| = 9) · addendum de consenso coincide con freeze
§4/§11 y perfil STEM §2 · campos multi-backend idénticos freeze §11 ↔ quantum/08 §4. La elevación
de O1 a P0 en la síntesis está justificada (ángulo ancla-EXECUTION), no es inflación.

### Barrido extendido (ciencia)

E1–E5 (detalle en §3.1). Donde barrí y NO encontré nada: escalera vs tope H2 (ieee30 → 29 qubits
con x₀=0 > 26, "solo clásico" correcto) · aritmética del statevector coherente · caveat de seed
del emulador remoto ya cubierto por `quantum/08:101` · aislamiento GPL de Mitiq correcto · gates
del corrector AI-QEM bien condicionados · GW+greedy registrado consistente · quantum/05 (REGRID)
intachable en separación proponente/verificador.

### Veredicto de conjunto (ciencia)

Los 5 hallazgos sobrevivieron verificación hostil con evidencia primaria; ninguno inflado (único
matiz: atribución de cita en O3). Lo que el acta NO vio: E1 — el cumplimiento del rango oficial
6–12/"real" pende de cr8/cr6 sin fallback compatible; es lo que un juez técnico cazaría primero.

## Anexo V-B · Verificador de ejecución (rol adversarial sobre Anexo B)

Mapeo: P0 #2 = Obj 1+2+3 · P0 #3 = Obj 9 · P1 #7 = Obj 4+5+6 · P1 #8 = Obj 8.

### Tabla de veredictos (ejecución)

| Obj                                | Veredicto              | Evidencia                                                                                                                                                                                                                   | Juicio del fix                                                                                                                                                                               |
| ---------------------------------- | ---------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1 — `cancelled` ausente            | **CONFIRMADO**         | `contratos:118` union sin `cancelled`; `esquema:169-170` CHECK idéntico; `freeze:60` congela CANCELLED y `:163` lo lista terminal; `[S-E · C4]` (`contratos:145`) promete el vocabulario completo pero el union no se tocó. | **CORRECTO con corrección**: marca S-F fechada, no `[S-E]` retroactiva (`freeze:18-19`).                                                                                                     |
| 2 — `max_steps` en ninguna semilla | **CONFIRMADO**         | Grep exhaustivo: hits solo en `freeze:66,164`, `guia:160`, `exec/02:116,169`. Cita exacta `freeze:66` "el guard del loop es contrato, no cortesía".                                                                         | **CORRECTO**; si viaja en el payload de `run.created`, el payload congelado `{run_id, actor_id, domain_id}` (`freeze:60`) también se supersede.                                              |
| 3 — dos máquinas de Run            | **CONFIRMADO (matiz)** | `freeze:60` vs `:163` (§13 confiesa el origen: "+ el estado `awaiting-verification` de la semilla"). Matiz: la proyección SÍ podría derivarlo de `●VerificationStarted` (`freeze:171`) — nadie lo declara.                  | **CORRECTO** — el matiz decide: opción (b), sub-estado derivado; evento nuevo innecesario.                                                                                                   |
| 4 — cancelación jerárquica         | **CONFIRMADO**         | Cero reglas (grep); `exec/07:252` "No resuelto" pre-jerarquía; addendum S-E solo cerró el caso del step.                                                                                                                    | (i) correcto; (iii) más barato: `cancel(ref)` ya existe (`infra/02:59`); (ii) **elegir RECHAZO** — un append post-terminal rompe el recompute del provenance_hash de un certificado emitido. |
| 5 — claims al raíz sin mecanismo   | **CONFIRMADO**         | `anexo:57` (`read_stream(run_stream)` singular); `freeze:161` sin mecanismo; `:173` claims = digests.                                                                                                                       | **CORRECTO**; mejor: payload con `sub_run_provenance_hash` (encadenado estilo Merkle).                                                                                                       |
| 6 — herencia `policy_digest`       | **CONFIRMADO**         | `contratos:126` ("al crear el run raíz"); `esquema:176` NOT NULL para todo run sin regla.                                                                                                                                   | **CORRECTO**; enforcement natural: creación del sub-run.                                                                                                                                     |
| 7 — PolicyChanged sin palanca      | **CONFIRMADO**         | R-Pol1 en `spec:68`, `freeze:86,171`; revocación `"none"` (`freeze:100`); overrides solo RELAJAN (AX2); escalación existe (`freeze:89,171`).                                                                                | **CORRECTO**; localizar afectados = query sobre `runs_projection.policy_digest`.                                                                                                             |
| 8 — interaction×profile            | **CONFIRMADO**         | `freeze:35` override sin condición; `:44` `remote-job` ⇒ JobRef; `exec/06` sin regla cruzada.                                                                                                                               | Dirección correcta; **mejor**: validar la matriz completa al cargar el DistributionManifest + celda `stream` (N4).                                                                           |
| 9 — replay                         | **CONFIRMADO**         | Todo lo escrito: `freeze:63,208,223`; `exec/09` no lo detalla.                                                                                                                                                              | **CORRECTO pero incompleto en 3 puntos** (clave con backend, `domain_id` SO2, manifest de fixtures pinneado).                                                                                |
| 10 — reintento sin addendum        | **CONFIRMADO**         | `exec/03:51-52` textual; `:5` "insumo para contract freeze" sin addendum (01 y 07 sí lo tienen). Matiz: exec/03 §12 ya apuntaba en esa dirección.                                                                           | **CORRECTO.**                                                                                                                                                                                |
| 11 — menores (i)–(iv)              | **CONFIRMADO ×4**      | (iii) peor de lo dicho: `freeze:97` fija `subject.name = "run:<id>"` — con `run_id` prefijado quedaría `"run:run:…"`, contamina el certificado. (iv) exec/09 sí fue actualizada; 08 es la rezagada.                         | Correctos; (ii) necesario, no cosmético (el freeze cita `serving.route()` como mecánica congelada).                                                                                          |

Doctrina: ningún fix del Anexo B reabre una decisión congelada; único desvío el etiquetado
retroactivo (corregido en §2.1).

### Barrido extendido (ejecución)

N1–N7 (detalle en §3.2).

### Veredicto de conjunto (ejecución)

11/11 confirmadas con evidencia línea a línea; las tres "reglas sin especificar" son huecos
genuinos que S-G no podría llenar sin decisiones de contrato. El acta mejoró el proyecto pero no
agotó el terreno: dos P1 nuevos (N1, N2).

## Anexo V-C · Verificador de infra (rol adversarial sobre Anexo C)

### Tabla de veredictos (infra)

| Ítem                       | Veredicto                                  | Evidencia                                                                                                                                                                                                                                                                                               | Juicio del fix                                                                                                   |
| -------------------------- | ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| O1 precarga Ollama         | **CONFIRMADO — sin matiz salvador**        | `infra/03:134` (ollama solo en `backend`), `:138-139` (`internal: true` incondicional — los profiles gatean el servicio, no la red), `:149` (el pull declarado corre DENTRO del contenedor). Agravante: el `exec` exige además `--profile local-llm` activo.                                            | **CORRECTO** (la variante más limpia: `docker run --rm -v <vol>:/root/.ollama ollama/ollama pull …` en el host). |
| O2 calendario              | **CONFIRMADO — fechas verificadas en git** | Filas textuales (`infra/03:189,192`) vs `freeze:208`; nota fechada 14-jul, importada en `b467937` (15-jul); los commits del 18-jul (`8a3958f`, `b39e860`) tocaron la nota pero NO esas filas (diff verificado). Matiz: el calendario es PROPUESTA — pero es exactamente lo que la guía manda ratificar. | **CORRECTO.**                                                                                                    |
| O3 llaves                  | **CONFIRMADO**                             | `trust/15:26` define las 2 env vars; el compose solo declara `pg_password` (`infra/03:81,145-146`).                                                                                                                                                                                                     | **CORRECTO con nota**: file-based choca con la letra env-var de trust/15 — convención `*_FILE` o entrypoint.     |
| O4 DATABASE_URL            | **CONFIRMADO (bug de DISEÑO)**             | `infra/03:95,116` sin password vs `:80` `POSTGRES_PASSWORD_FILE`; es bloque de diseño, no archivo — P2 del acta ya era la severidad correcta.                                                                                                                                                           | **CORRECTO.**                                                                                                    |
| O5 RAM                     | **CONFIRMADO**                             | 2¹⁴×16 B = 0.25 MiB exacto; grep exhaustivo: cero presupuesto local, cero spec de equipo en TODO el repo (solo sizing Fargate).                                                                                                                                                                         | **CORRECTO** (estimado 6–8 GiB plausible).                                                                       |
| O6 compose canónico        | **MATIZADO**                               | Sustancia SÍ (freeze solo fija el skeleton `:210`; infra/02 sin worker `:45,111`; la cita "(tu nota 02)" de la guía es incorrecta). Letra NO: la cadena con worker también vive en `infra/03:110-117,248`.                                                                                              | **CORRECTO** (el hueco real: ningún doc congelado la tiene).                                                     |
| O7 egress/secretos Fargate | **CONFIRMADO (matiz menor)**               | `infra/01:113,208` vs `infra/03:155,252(d)`; `deployment.md:33` nombra Secrets Manager pero para Modo C Fase 2. Nota: los SG outbound no pueden ser "cerrados" a secas (ECR + API del modelo) — razón de más para diseñarlo.                                                                            | **CORRECTO.**                                                                                                    |

Riesgos del día D: verificables y confirmados — #2 segunda máquina (exigida 2 veces: `freeze:214,103`;
ausente del calendario), #5 sin `restart:`, #7 PR de deps como predecesor (`freeze:210`); mixtos
(hueco verificable + efecto de juicio técnico) — #1 nginx SSE (nada de `proxy_buffering` en ningún
doc), #3 reset pgdata; juicio operativo puro — #4 WSL2, #6 checklist física.

### Barrido extendido (infra)

I1–I11 (detalle en §3.3). Licencias: repo MIT; tabla L toda Apache-2.0/MIT; Dramatiq LGPL
descartada; hypothesis MPL "no vendorizar" y PyJWT ⚠️ ya registrados; Mitiq GPL correctamente
encuarentenada (quantum/09:71,83).

### Veredicto de conjunto (infra)

Los dos P1 (O1, O2) salen REFORZADOS de la refutación; severidades bien calibradas; única
imprecisión de letra en O6 sin efecto de sustancia. El compose de diseño necesita una pasada SRE
completa antes de volverse archivo real, pero nada invalida una decisión congelada.

## Anexo V-D · Verificador de equipo + plano de confianza

### Tabla de veredictos (Anexo D del acta)

| #     | Hallazgo                                   | Veredicto                  | Evidencia                                                                                                              |
| ----- | ------------------------------------------ | -------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| D-1   | Registro pt.2 omite §4-AcceptanceAuthority | **CONFIRMADO**             | `freeze:78` vs `:266`; la guía sí la pregunta (`guia:218`)                                                             |
| D-2   | §2/§5 [ejecución] sin pregunta a Steven    | **CONFIRMADO**             | `freeze:53,82` vs `guia:133-135`                                                                                       |
| D-3   | §10 invisible para todos                   | **CONFIRMADO**             | `freeze:133`; ausente de toda lectura/checklist                                                                        |
| D-4   | §12 frontera sin asignar a Steven          | **CONFIRMADO**             | `freeze:150` vs `guia §4` y `freeze:266`                                                                               |
| D-5   | Modelo Ollama sin firma de Steven          | **CONFIRMADO con matiz**   | El checklist de Steven menciona Ollama como backend (`guia:164-167`), pero no la decisión del modelo ~3B               |
| D-6   | "§15.8" completo a Geovanni                | **CONFIRMADO**             | `freeze:266` vs tabla `:229-235` (filas de Steven y Dylan)                                                             |
| D-7   | Tag §7 sin frontera                        | **CONFIRMADO (cosmético)** | `freeze:93` vs `guia:186-189`                                                                                          |
| OBJ-1 | 20% sin segundo paso                       | **CONFIRMADO**             | Grep: "20%" solo en `guia:220-221`; infra/03 18-jul sin explicación cruzada                                            |
| D-8   | Guía recorta "del cliente"                 | **CONFIRMADO**             | `freeze:183` vs `guia:214` — verbatim comparado                                                                        |
| D-9   | "(§13" colgante en trust/15                | **CONFIRMADO con matiz**   | Se usa 2 veces consistente (`trust/15:3,54`) — referencia a backlog externo, no errata; el fix es nombrar el referente |
| D-10  | `workspace_id`/`principal_id` no recogido  | **CONFIRMADO**             | `infra/01:224-228` ("sí registrar en el freeze") vs grep cero en el freeze                                             |
| D-11  | Parches al silencio=ratificación           | **COHERENTES**             | El ack ya existe como opción (`guia:73-75`); `freeze:200` exige literalmente CORRER el script — el silencio no ejecuta |

### Hallazgos del plano de confianza (T1–T17)

Detalle en §3.4; evidencia clave: T1 `distributions/chimera/policies/verification-default.yaml` +
`engine/src/blite/verification/policy.py:36` vs `freeze:74` y §6 (freeze:84-91) + Regla 1 del
anexo (`anexo:74`) · T2 `freeze:98` vs `:173` + `spec:60` (S6) + `esquema:212` (NOT NULL) · T3
`contratos:261` + `esquema:198` vs `freeze:75` y `base-logica:43` (D10) · T4 `spec:90,57` +
`perfil:38,68` vs `freeze:75` y semillas · T5 `freeze:88` + `perfil:68` vs `spec:94,123` (grep:
solo `independence_basis` del runner) · T6 `freeze:103` vs `spec:90` vs `contratos:308` vs
`esquema:185-224` · T7 `anexo:40-53` (view(e)) vs `:73` (`C(claim)` sin definir) + `spec:88` ·
T10 `anexo:106,113` vs `freeze:74,118` · T14 `esquema:209` vs L2 + `spec:102`.

### Veredicto de conjunto (equipo + confianza)

11/12 del Anexo D confirmados contra el repo (2 matices que afinan el fix, no lo invalidan). El
hueco estructural era real: 8 P1 nuevos viven exactamente en el plano que nadie ratifica, y
ninguno invalida una decisión congelada — todos cerrables con supersesiones de pocas líneas antes
del 23-jul. El certificado (EL diferenciador) hoy promete en su letra más de lo que sus semillas
pueden probar; eso se cierra antes de S-G.
