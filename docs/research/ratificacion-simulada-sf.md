# CHIMERA — Acta de ratificación SIMULADA (S-F) · 2026-07-19

> **Qué es esto.** Simulación de la etapa S-F ejecutada por 4 revisores independientes (agentes con
> contexto fresco, uno por dueño + uno de equipo/completitud), siguiendo EXACTAMENTE los órdenes de
> lectura y checklists de `docs/guia-ratificacion.md`. **Es el CONTRAPESO, no el sustituto**: sirve
> para (a) comparar contra lo que respondan Sebas/Steven/Geovanni, (b) ser el piso si alguno no hace
> su pasada o la hace superficial. **No enviarla a los compañeros antes de que hagan su revisión** —
> contaminaría la independencia que este proceso busca. **Ejercicio personal: vive SOLO en la rama
> `ejercicio/sf-ratificacion-simulada` — jamás se mergea a main.** La validación a profundidad de
> estos hallazgos (¿confirmado/refutado/matizado?) está en `ratificacion-simulada-sf-validacion.md`.
>
> **Integridad:** la simulación no modificó ningún archivo del repo (`git status` limpio al cierre).
> El ítem ejecutable de Sebas se corrió DE VERDAD en entorno efímero (scratchpad).

---

## 1 · Veredictos globales

| Rol simulado             | Veredicto                      | En una línea                                                                                                                                                                         |
| ------------------------ | ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Sebas (ciencia/cuántica) | **RATIFICARÍA CON OBJECIONES** | Fondo científico sólido, 6/6 digests reproducen — pero la receta oficial de ratificación NO corre con el `uv.lock` del repo, y hay drift freeze↔repo + colisión de identidad @v1.    |
| Steven (ejecución)       | **RATIFICARÍA CON OBJECIONES** | Los dos addenda grandes (policy disuelta, `parent_run_id`) se ACEPTAN — pero las semillas v2 contradicen la máquina de estados congelada y hay 3 reglas jerárquicas sin especificar. |
| Geovanni (infra)         | **RATIFICARÍA CON OBJECIONES** | Decisiones de fondo sanas — pero el calendario de infra/03 no fue reconciliado con el freeze y el compose de diseño tiene 2 bugs operativos concretos.                               |
| Equipo (§6)              | **3 RATIFICA + 1 OBJETA P2**   | Posición operativa, camino dorado y AcceptanceAuthority pasan; el 20% de "Explicación" no tiene segundo paso.                                                                        |

**Lectura global:** ninguna objeción invalida una decisión de diseño congelada — la sustancia del
freeze sobrevive la revisión adversarial. Casi todo es letra-vs-realidad (el freeze afirma estados
del repo que no existen), semillas incompletas, y operativa del demo. Todo cerrable antes del 23-jul.

## 2 · Lista consolidada priorizada

### P0 — cerrar ANTES de S-G (romperían seeds o el demo)

1. **Re-lock de dependencias — el `uv.lock` rompe el ancla EXECUTION.** El lock pinnea
   pandapower 3.1.2 + numpy 2.5.1 y esa combinación **crashea en `pp.runpp`**
   (`ValueError: assignment destination is read-only`); además pandapower/ortools/networkx son
   extras opcionales que el sync default no instala ⇒ la receta oficial de ratificación del corpus
   (`uv run` desde la raíz, islanding/01 §1.9) falla dos veces. No es solo la receta: **pandapower
   es el ancla EXECUTION del demo** (freeze §4). Fix: re-lock a pandapower 3.3.3 (versión con la
   que el corpus reproduce exacto), documentar el comando de sync exacto en §1.9, registrar
   versiones del lock como evidencia del corpus. _(Hallazgo: solo apareció por CORRER la receta.)_
2. **Las semillas v2 contradicen la máquina de estados congelada.** `cancelled` falta en
   `Run.status` (`especificacion-contratos-v2.md` L118) y en el CHECK de `runs_projection`
   (`esquema-datos-v2.md`) — un `run.cancelled` sería improyectable; `max_steps` ("contrato, no
   cortesía", freeze §3) no existe en ninguna semilla; `awaiting-verification` está en §13 pero no
   en §3 ni tiene evento que lo dispare. Fix: corregir ambas semillas con marca `[S-E]` propia +
   unificar §3/§13 (dueño: Dylan).
3. **El backend `replay` — la config del día D — no tiene contrato construible.** Falta: miss ⇒
   `model.call.failed {error_kind: replay_miss}` y JAMÁS passthrough a red (sería exactamente el
   "fallback silencioso" que el freeze prohíbe); canonicalización del prompt (Regla 2 del anexo
   sobre el request canónico); fixtures content-addressed + modo grabación. Fix: contrato de 4
   líneas como seed de S-G (frontera Steven↔Dylan, §15.7).
4. **El fixture de la falla sembrada NO puede elegir el bus a ojo.** Cómputo real de los 14 flips
   sobre la partición óptima congelada: en **ieee14-flujo el flip del bus 7 degrada CERO** (óptimo
   degenerado — daría "mismo valor", el escenario que §15.5 prohíbe); en ieee14-uniforme los buses
   0, 1 y 11 también degradan cero. **Propuesta: congelar instancia=ieee14, convención=flujo,
   bus=1** (0-indexed): degradación máxima (corte 32 597 vs óptimo 57 070, ratio 0.5712), respeta
   x₀=0, narrativa física buena (bus de generación). Ratifica: Sebas.

### P1 — cerrar en la ventana de ratificación (antes del 23)

5. **Colisión de identidad ieee30:** el freeze ordena re-estampar el digest al agregar
   `bruteforce_vectorized` a `metodos` manteniendo `@v1` — contradice su propia regla "el archivo
   congelado manda, no se sobreescribe". Fix recomendado: los ieee30 post-segunda-ancla nacen
   **`@v2`** con supersesión registrada. Decide: Sebas (es SU identidad de ancla).
6. **Drift freeze↔repo sobre la ancla vectorizada:** freeze §15.3 e islanding/01 §1.4 dicen
   "integrada al script §1.9" — el script solo tiene fuerza bruta `itertools` (max n=14). El
   "presupuesto explícito" prometido ya está MEDIDO por esta simulación: **~6 min/convención,
   ~12 min ieee30 completo** (numpy mono-hilo, bloques de 2²⁴ ≈ 11.4 s / 0.3 GiB). Fix: supersesión
   menor de la letra ("integración en S-G") + escribir el presupuesto.
7. **Run jerárquico sin 3 reglas (sin ellas `parent_run_id` produce huérfanos):** (i) cascada de
   cancelación (`run.cancelled {reason: parent_cancelled}` a sub-runs activos + rechazo de appends
   tardíos + barrido del job en cola); (ii) mecanismo del "aporte de claims al raíz" — hoy el
   `provenance_hash` solo ampara UN stream, el certificado referenciaría trabajo fuera de su hash
   (fix: evento en el stream raíz tipo `●ClaimEmitted {claim_digest, sub_run_id}`); (iii) herencia
   obligatoria del `policy_digest` del raíz, divergencia = fail-closed. Dueños: Steven (i) + Dylan (ii, iii).
8. **Regla de validez `interaction`×`execution_profile`:** la distribución puede sobreescribir a
   `remote-job` una capability `request_response` y romper el contrato del caller (JobRef donde se
   promete Result). Fix: validación del DistributionManifest — override a `remote-job` solo si
   `interaction: job`; incompatible ⇒ `NotImplementedError`.
9. **Calendario infra/03 §1.5 sin reconciliar con el freeze (es del 14-jul):** filas 24–25 con
   "stack AWS arriba" incondicional (vs P1-10 Fargate-stretch-si-verde-el-27) y dry-run 2 con
   "modelo por API externa" (vs P1-8: `replay` es la config del día D). Fix: addendum de 2 líneas.
10. **La precarga del modelo Ollama es estructuralmente imposible tal como está escrita:** el
    servicio vive SOLO en la red `internal: true` ⇒ `docker compose exec ollama ollama pull` no
    tiene ruta a internet NUNCA. Fix: override de precarga documentado (compose.preload.yml / pull
    en host con volumen montado) antes del 24-jul.
11. **El Registro de cierre del freeze tiene huecos de asignación:** la fila "equipo" omite
    §4-AcceptanceAuthority (marcada "ratificación final del equipo" en §4); ítems `[ejecución]` de
    §2 (durabilidad = replay del log), §5 (egress solo `AuthzDecision`), §10 (Stage emite su evento
    de override) y §12 (ContentStore, frontera) no tienen pregunta a Steven en guía ni registro.
    Fix: una supersesión cosmética única, causa "auditoría de ratificación S-F".
12. **Silencio=ratificación necesita dos parches:** exigir ack mínimo ("OK mi plano", 30 s) con
    escalación de Dylan al 22-jul; y los ítems EJECUTABLES de Sebas (correr corpus, cr8/cr6) son
    **no ratificables por silencio** — el silencio no ejecuta scripts.

### P2 — deuda menor / operativa (selección; detalle en anexos)

- **Corpus/formateo:** el script §1.9 no es productor byte-exacto (Prettier reformateó los JSON) —
  declarar "artefactos generados se comparan por digest canónico, exentos de formateo" o alinear el
  writer. Aplica igual a cr8/cr6 y fixtures de S-G.
- **cr8 realista:** los datos ArcGIS del ICE casi seguro dan topología GIS sin caso de flujo
  corrible ⇒ o cr8 nace solo `uniforme` (documentado) o los supuestos de modelado se declaran como
  assumptions del corpus. Fijar fecha límite (~25-jul) y opener de respaldo (ieee9).
- **Compose/demo:** llaves Ed25519 (`CHIMERA_TRUST_CERT_KEY`/`CHIMERA_JWT_KEY`) sin ruta de
  custodia en el compose (solo existe `pg_password`); `DATABASE_URL` sin credencial vs
  `POSTGRES_PASSWORD_FILE` (auth failure al primer `up`); presupuesto RAM real ≈ **6–8 GiB pico**
  (el statevector de ieee14 es trivial: 0.25 MiB; el consumidor es Ollama+Studio+solvers) ⇒ equipo
  del demo ≥16 GB — **decidir HOY qué laptop es**; compose canónico del mes no congelado en ningún
  doc normativo (guía dice `+worker`, infra/02 no, freeze solo skeleton sin worker).
- **Día D (riesgos que ningún checklist pregunta):** nginx sin `proxy_buffering off` congela el SSE
  (el clímax visual); la **segunda máquina del verify offline** no está en ninguna fila del
  calendario; reset de `pgdata` entre ensayos (los runs de prueba aparecerían en el Studio el día
  D); `.wslconfig`/memoria de Docker Desktop en el equipo real; `restart: unless-stopped`; checklist
  física (sleep/batería/proyector).
- **Notas por estampar:** addendum del reintento `reversible-external` en execution/03 (único
  cambio a notas de Steven sin porqué escrito — el cambio es correcto, pero viola la "regla de oro"
  de la guía §2); encabezado de execution/08 desactualizado; semilla §5 conserva
  `Guardrail`/`GuardrailSignal` sin la renominación `Detector`/`Signal` del freeze;
  `Attestation.anchorDigest` nullable vs "binding a 4 digests"; formato de `run_id` vs vector V1
  del anexo (`"run:8f2c1a9b"`).
- **20% Explicación sin segundo paso:** agregar al dry-run 1 una ronda de explicación cruzada
  (cada dueño explica 5 min un plano ajeno) + banco de Q&A por plano como seed de S-P; commitear un
  extracto de la rúbrica a `knowledge/` (hoy la cifra "20%" solo existe en la guía).
- **Citas menores:** guía §6 recorta "del cliente" de la posición operativa (alinearla verbatim —
  es LA frase de Q&A); guía §5 cita "(tu nota 02)" para una cadena de compose que la nota no
  contiene; trust/15 §4 referencia colgante "(§13)"; infra/01 §I pedía fijar vocabulario
  `workspace_id`/`principal_id` en el freeze y no fue recogido ni diferido.

## 3 · Lo que SOLO los dueños reales pueden cerrar (la simulación no sustituye esto)

- **Sebas:** la decisión @v1/@v2 de ieee30 · si ~6 min/convención de enumeración basta o se
  optimiza · el criterio físico/narrativo del bus de la falla (bus 1 es el óptimo matemático; el
  guion puede preferir otra historia) · el modelado de cr8 desde datos GIS · si 5 corridas con
  seeds pinned bastan como "independencia" para la pata AL2.
- **Steven:** la cascada de cancelación (es SU runtime el que produce huérfanos) · exigir el
  fail-closed de `replay` por escrito · la validez `interaction`×`profile` (es SU Dispatcher) ·
  **timing**: el walking skeleton vence ~20-jul, ANTES del cierre del 23 ⇒ ratificar §2/§3 PRIMERO
  (es lo que el skeleton toca) · confirmar que acepta el endurecimiento del reintento.
- **Geovanni:** ¿el "baseline Terraform externo" (infra/01 §R pt.2) existe de verdad? ·
  expectativas sobre Pulumi (nada del mes lo usa; el stretch sería a mano) · fechas 27/29 vs su
  disponibilidad real · tabla de licencias L · la spec del equipo del demo (RAM).
- **Equipo:** memorizar la posición operativa VERBATIM (§15.2 con "del cliente") · el corte
  camino-dorado/NO-va es la decisión de scope que hay que objetar hoy y no descubrir el 25 · firma
  formal de AcceptanceAuthority (y declarar como limitación Fase 1 que Dylan diseña Y acepta —
  separación de deberes, análoga al S2 de llaves).

## 4 · Cómo usar esta acta

1. **Al llegar cada ratificación real:** comparar contra el anexo del dueño. Lo que el compañero
   levante y aquí no esté = ganancia real (registrarlo). Lo que esté aquí y el compañero no vio =
   conversarlo antes del 23, sin decir que salió de una simulación si no ayuda.
2. **Si alguien no responde al 22-jul:** su anexo es el piso — las objeciones P0/P1 de su plano se
   incorporan igual (son verificables contra el repo, no opiniones), y sus ítems "solo humanos"
   pasan a la escalación de Dylan.
3. **Independiente de los compañeros, hay trabajo YA de Dylan:** los P0 #1–#3 y los P1 #5–#8 y #11
   son verificables hoy contra el repo y conviene dejarlos corregidos (supersesión con causa) antes
   de que las ratificaciones reales lleguen — así los compañeros ratifican sobre la versión buena.

---

## Anexo A · Informe completo — rol Sebas (ciencia/cuántica)

## (a) Veredicto global: **RATIFICARÍA CON OBJECIONES**

El fondo científico es sólido y fiel a la investigación del plano: los 6 digests canónicos reproducen exactos, la estratificación Max-Cut-core/física-extensión es correcta frente al enunciado, y el addendum de consenso preserva el diseño original de la nota 04. Pero la **receta ejecutable de ratificación no corre tal como está escrita** (extras ausentes + lockfile incompatible que crashea), el freeze **afirma una integración de código que no existe** (ancla vectorizada "integrada al script §1.9"), y hay una **colisión normativa sin resolver** entre "el archivo congelado manda, no se sobreescribe" y "el digest de ieee30 se re-estampa en @v1". Ninguna objeción invalida una decisión científica; todas son de letra/ejecutabilidad y se arreglan antes del 23-jul.

## (b) Tabla por ítem del checklist (guía §3)

| Ítem                                                   | Veredicto                  | Causa                                                                                                                                                                                                                                                                                                                                                  |
| ------------------------------------------------------ | -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Estratificación C1 core-vs-limitaciones                | **RATIFICA**               | Coherente en freeze §15.3 (Δ1), §11 (`repair.*` en extensión) y quantum/05 §4 — el corpus Max-Cut queda alineado con el enunciado oficial.                                                                                                                                                                                                             |
| S = 100 como definición de instancia                   | **RATIFICA**               | islanding/01 §1.3 lo argumenta bien (redondeo = instancia, no error del solver); reproduje los márgenes al umbral x.5 exactos (0.0298 / 0.0322 / 0.0090).                                                                                                                                                                                              |
| Segunda ancla ieee30 = enumeración vectorizada         | **OBJETA P1**              | La decisión es sana, pero freeze §15.3 e islanding §1.4 dicen "integrada al script §1.9" y el script NO la contiene; el "presupuesto explícito" prometido no está escrito (lo medí: ~6 min/convención).                                                                                                                                                |
| Ejecutable: regenerar corpus + comparar 6 digests      | **OBJETA P1**              | Digests 6/6 reproducen — pero SOLO en entorno efímero con las versiones de la nota; la receta oficial (`uv run` desde la raíz) falla dos veces (ver (d)).                                                                                                                                                                                              |
| Identidad `dataset_id`↔digest                          | **RATIFICA con caveat P1** | Tabla freeze §15.3 = digests embebidos = digests recomputados, verificado. El caveat: el re-estampado de ieee30 en `@v1` contradice la propia regla de identidad (objeción 3).                                                                                                                                                                         |
| Campos de evidencia §11                                | **RATIFICA**               | Verificado campo por campo contra quantum/03 §1, 04 §8, 05 §4, 08 §4 y 09 §4 — cero drift; los multi-backend (`transpiled_circuit_digest`, `backend_id`+versiones, `noise_config_digest`) son idénticos entre freeze §11 y quantum/08 §4.                                                                                                              |
| Consenso de muestreo = CONSENSUS_REPLICATION techo AL2 | **RATIFICA**               | El addendum existe (quantum/04 §4, bloque "AJUSTE S-E") y el porqué convence: réplicas con seeds pinned son procesos no-modelo (S7); la concordancia entre-modelos sigue Signal — el diseño original queda intacto en su mitad (b). Coherente con freeze §4, §11, quantum/08 §2.3 y perfil STEM §2 ("Runner de replicación… solo procesos no-modelo"). |
| Falla sembrada §15.5                                   | **RATIFICA con hallazgo**  | El contrato es correcto y mi análisis PRUEBA que la cautela era necesaria: hay buses cuyo flip degrada CERO. Candidato concreto abajo (objeción 5).                                                                                                                                                                                                    |
| Entregables cr8/cr6                                    | **RATIFICA**               | IDs reservados en freeze §15.3, especificación §1.8 actualizada contra el enunciado, W=5.9/g=2 correctamente supersedidos. Riesgo real señalado en (e): la convención `flujo` exige un caso de flujo corrible, no solo topología GIS.                                                                                                                  |

## (c) Objeciones detalladas

**O1 (P1) — La receta de ratificación no es ejecutable en el workspace.** Pega a: islanding/01 §1.9 ("Correr desde la raíz del repo con el Python del workspace") y freeze §15.3 ("ratificación final de Sebas = correr y comparar digests"). Hechos: (i) `uv run python` desde la raíz da `ModuleNotFoundError: pandapower` — pandapower/ortools/networkx son _extras opcionales_ de `capabilities/sim`, `solvers` y `graphs`, no instalados por el sync default; (ii) peor: `uv.lock` pinnea **pandapower 3.1.2 + numpy 2.5.1**, y esa combinación **crashea en `pp.runpp`** (`ValueError: assignment destination is read-only`); (iii) la nota registra la generación con **pandapower 3.3.3 + numpy 2.5.0**, que el lock no respalda. Para el proyecto cuya tesis es reproducibilidad por digest, el entorno generador del corpus no está pinneado por el lock del repo. **Fix:** re-lock con pandapower 3.3.3 (o pin exacto de extras) + escribir en §1.9 el comando de sync exacto (`uv sync --all-packages --all-extras` o equivalente) + registrar las versiones del lock como parte de la evidencia del corpus.

**O2 (P1) — Drift freeze↔repo↔guía sobre la ancla vectorizada.** Freeze §15.3: "integrada al script de islanding/01 §1.9… se corre en la ratificación". islanding/01 §1.4: "integrada a este script §1.9". Realidad: el script §1.9 solo tiene la fuerza bruta `itertools` con `FUERZA_BRUTA_MAX_N = 14`; ieee30 sigue con una sola ancla. La guía §3 lo degrada en silencio a "hoy ratificás la DECISIÓN; el código se integra en la fase de seeds". El freeze afirma un estado del repo que no existe — exactamente el tipo de drift que este proceso debía cazar. **Fix:** supersesión menor de la letra del freeze ("integración en S-G") o integrar el código antes del cierre de S-F; en ambos casos escribir el presupuesto explícito prometido (dato medido: ver (d)).

**O3 (P1) — Colisión normativa: re-estampado ieee30 vs regla de identidad.** Freeze §15.3 decreta "el archivo congelado manda: una regeneración que no reproduzca el digest se reporta, no se sobreescribe" Y, tres párrafos después, ordena que al ratificar `metodos` pase a `["cpsat","bruteforce_vectorized"]` con "el digest se re-estampa" (islanding §1.4). Cambiar `metodos` cambia el JSON ⇒ cambia el digest ⇒ obliga a sobreescribir los dos ieee30 y deja obsoletas 2 filas de la tabla congelada — manteniendo `@v1`. Si `dataset_id`↔digest es la identidad del ancla, mutar el digest sin subir versión rompe la regla que la misma sección congela. **Fix (recomendado):** los ieee30 post-segunda-ancla nacen como `@v2` con supersesión registrada y la tabla del freeze gana dos filas; alternativa mínima: marcar HOY las filas ieee30 como "provisionales hasta ratificación" en §15.3.

**O4 (P2) — El script §1.9 no es el productor byte-exacto de los archivos congelados.** Los JSON del repo tienen arrays internos en una línea (estilo Prettier); el script emite `json.dumps(indent=2)` puro (cada entero en su línea). Correr el script dentro del repo ensuciaría los 6 archivos en `git diff` aunque los digests canónicos sobrevivan. **Fix:** alinear el writer con el formateo del repo, o anotar en §1.6/§1.9 que la única comparación válida es el digest canónico, jamás bytes del archivo.

**O5 — Falla sembrada: el vector NO puede elegirse a ojo (hallazgo que valida el contrato).** Computé la degradación de los 14 flips posibles sobre la partición óptima congelada:

- **ieee14-flujo: flip del bus 7 degrada CERO** — produce _otra asignación óptima_ (57 070). El óptimo es degenerado más allá del par complemento; un vector elegido al azar podía aterrizar en "mismo valor", el escenario que §15.5 prohíbe.
- **ieee14-uniforme: buses 0, 1 y 11 degradan CERO.** Si el fixture no pinnea la convención, hay 3 minas.

**Bus candidato propuesto: bus 1 (0-indexed) sobre ieee14-flujo.** Degradación máxima: corte 32 597 vs óptimo 57 070 (ratio 0.5712 — visualmente dramático), mantiene la canonicalización x₀=0 intacta, y la refutación es un recompute contra el corpus en milisegundos, `fail` inequívoco. Narrativa física: en case14 el bus 1 es bus de generación — "mover un generador de isla" se cuenta solo. Evitar bus 0 (flipearlo rompe x₀=0 y enreda la historia con la simetría de complemento). **El fixture debe congelar: instancia=ieee14, convención=flujo, bus=1.**

## (d) Resultado del ítem ejecutable

Script §1.9 extraído del markdown y ejecutado en el scratchpad (cero escrituras al repo; `git status` limpio al cierre):

1. **Con las versiones registradas en la nota** (pandapower 3.3.3, networkx 3.6.1, ortools 9.15.6755, numpy 2.5.0, vía `uv run --no-project --with …`): **los 6 digests canónicos reproducen EXACTOS** — `dee38c…`, `59fb22…`, `fb9c37…`, `c7880b…`, `a86412…`, `a3aed5…` — idénticos a los embebidos y a la tabla del freeze §15.3. Óptimos, |E|, W, `metodos`, `solver_status` y los tres márgenes al umbral x.5 también reproducen. Los _bytes_ de archivo difieren solo por formateo (O4).
2. **Con la receta oficial del workspace**: FALLA. `uv run python …` → `ModuleNotFoundError: pandapower`; y con las versiones del `uv.lock` (pandapower 3.1.2 + numpy 2.5.1) → crash en `pp.runpp` (O1).
3. **Verificación independiente §1.6** (recompute del digest embebido sin deps): 6/6 OK, y 6/6 = tabla freeze §15.3.
4. **Presupuesto de la enumeración 2²⁹ (medido, no estimado):** bloque de 2²⁴ asignaciones × 41 aristas en numpy = 11.4 s y ~0.3 GiB ⇒ **~366 s (≈6 min) por convención, ~12 min ieee30 completo**, mono-hilo. Viable para la corrida de ratificación; ese es el número que "presupuesto explícito" debe decir.

## (e) Lo que el Sebas real debe mirar personalmente

1. **La decisión @v1 vs @v2 de ieee30** (O3) — es SU identidad de ancla; nadie más debería resolverla.
2. **El presupuesto de la enumeración**: mis ~6 min/convención son numpy mono-hilo naïve; decidir si basta o si se empaqueta en uint64/bloques Gray para bajarlo — y si 12 min cabe en el flujo de ratificación o corre offline con log.
3. **El criterio físico del bus de la falla sembrada**: bus 1 maximiza degradación matemática, pero el guion del demo puede preferir un bus con mejor historia de isla (carga vs generación); la degeneración del bus 7 merece una línea en el guion ("hasta el óptimo tiene testigos múltiples").
4. **cr8 con convención `flujo`**: los datos abiertos del ICE (ArcGIS) casi seguro dan topología GIS, no un caso de flujo corrible en pandapower (faltan impedancias/cargas/despacho). Construir el caso base es una decisión de modelado con supuestos que hay que declarar como assumptions del corpus — o aceptar que cr8 nace solo `uniforme` y documentarlo.
5. **El juicio estadístico del techo AL2** para réplicas de muestreo: el addendum es coherente con S7, pero solo el dueño puede decir si 5 corridas con seeds pinned constituyen "independencia" suficiente para una pata decisoria o si exige más réplicas/entornos.

## (f) Hallazgos cruzados fuera del plano — para Dylan

- **[para Dylan] Lockfile drift (toca infra/ejecución):** `uv.lock` pinnea pandapower 3.1.2 que crashea con el numpy lockeado — esto no solo rompe la regeneración del corpus: **pandapower es el ancla EXECUTION del demo** (freeze §4); si el lock no corre `runpp`, el verificador de ejecución tampoco. Re-lock antes del walking skeleton.
- **[para Dylan] Formateo post-generación:** algún hook (Prettier?) reformateó los JSON del corpus después de generados. Cualquier script generador futuro (cr8/cr6, fixtures de S-G) va a sufrir lo mismo; definir la política "artefactos generados: se comparan por digest canónico, exentos de formateo" o alinear los writers.
- **[para Dylan] Letra de la guía vs freeze sobre el timing de la ancla vectorizada** (O2): la guía dice "decisión hoy, código en seeds"; el freeze dice "se corre en la ratificación". Alinear antes de que el Sebas real lea ambos y pierda 20 minutos en la misma discrepancia.
- **[para Dylan] Nota menor:** islanding/01 §1.6 documenta bien que el digest del corpus NO es el `claim_digest` del anexo de canonicalización (objetos distintos) — vale la pena repetir esa distinción en el seed de `verify-bundle.py` para que nadie los confunda en código.

Archivos clave: `docs/contract-freeze.md` (§15.3 líneas 185–202, §11 líneas 137–148, §15.5 líneas 212–214) · `knowledge/islanding/01-corpus-benchmarks.md` (§1.4 línea 41, §1.9 líneas 103–301) · `knowledge/quantum/04-estadistica-evidencia.md` (addendum líneas 66–72) · corpus en `knowledge/islanding/corpus/`.

---

## Anexo B · Informe completo — rol Steven (ejecución)

## (a) Veredicto global — Steven

**RATIFICARÍA CON OBJECIONES.**
Las decisiones congeladas del plano de ejecución son fieles a mi investigación o la mejoran con causa escrita: los dos cambios grandes (policy disuelta, `parent_run_id`) se sostienen técnicamente y los aceptaría. Pero las semillas v2 que el freeze declara "ya corregidas" tienen al menos dos omisiones que contradicen la máquina de estados congelada (`cancelled` y `max_steps` ausentes), y hay tres reglas sin especificar que S-G no puede inventar solo (cascada de cancelación jerárquica, mecanismo del "aporte de claims al raíz", contrato del backend `replay`). Nada de esto invalida el freeze; todo debe cerrarse ANTES de generar seeds.

## (b) Tabla por ítem del checklist (guía §4)

| #   | Ítem                                                                                      | Veredicto     | Causa (1 línea)                                                                                                                                                                                                                                              |
| --- | ----------------------------------------------------------------------------------------- | ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1   | Manifest v2 sin `protocol`, `interaction`+`execution_profile`, JobRef/NotImplementedError | **OBJETA P1** | Fiel al freeze §1 y a execution/06, pero la sobreescritura de perfil por distribución puede volver `remote-job` una capability `request_response` sin regla de validez                                                                                       |
| 2   | Disolución de la etapa `policy` (8 etapas)                                                | **RATIFICA**  | El porqué (C2 + R-Pol1) se sostiene; el caso borde "policy endurecida vs run pinneado" queda como objeción operativa menor (ver c.7)                                                                                                                         |
| 3   | Reautorización a mitad de pipeline fail-closed                                            | **RATIFICA**  | Cierra mi pregunta §8.4 exactamente en la dirección segura; coherente con la intersección de permisos §8                                                                                                                                                     |
| 4   | Run jerárquico = opción A + `parent_run_id`                                               | **OBJETA P1** | Mi opción A sobrevive intacta, pero la jerarquía llega sin regla de cascada de cancelación, sin mecanismo del aporte de claims al raíz y sin herencia declarada de `policy_digest`                                                                           |
| 5   | step↔job 1:1, cancelación⇒`interrupted`, `max_steps` obligatorio                          | **OBJETA P1** | La máquina congelada NO es representable en las semillas: `cancelled` falta en `Run.status` (contratos v2) y en el CHECK de `runs_projection` (esquema v2); `max_steps` no existe en ninguna semilla; `awaiting-verification` no tiene evento que lo dispare |
| 6   | Idempotencia gobernada por `side_effects`                                                 | **OBJETA P2** | La regla es correcta y MÁS segura que mi nota 03 (que permitía reintento libre de `reversible-external`), pero es un tercer cambio a mis notas SIN addendum fechado — viola la propia "regla de oro" de la guía §2                                           |
| 7   | ModelPort/ModelServer + LiteLLM Router + backend `replay`                                 | **OBJETA P1** | La estructura es sólida (AX3/INV-6 verificados en vivo en nota 09), pero `replay` — la config del día D — está subespecificado: qué pasa en cache-miss, canonicalización del prompt, dónde viven los fixtures                                                |
| 8   | Registry tolerante a fallos + eventos + pin de versiones                                  | **RATIFICA**  | Freeze §1 reproduce fielmente execution/04 (excepción POR entry point, `registry.loaded`/`capability_load_failed` con `service:runtime`, pin determinista jamás `latest`)                                                                                    |
| 9   | Walking skeleton 48h + PR único de deps                                                   | **RATIFICA**  | Freeze §15.4 tal como la guía lo afirma; nota de calendario: vence ~20-jul, ANTES del cierre de ratificación del 23 (ver e)                                                                                                                                  |

Verificación anti-drift guía↔freeze↔contratos: **cada sección que la guía cita dice lo que la guía afirma** (§1, §2, §3, §8, §13, §15.7 verificados línea por línea); las marcas `[S-E]` listadas en el encabezado de contratos v2 (C1, C3/C4, P0-2, P1-2, P1-5, execution/09) existen todas en su sitio. El problema no son las correcciones presentes sino las **incompletas** (ver c.1).

## (c) Objeciones detalladas — Steven

**1. [P1] La corrección C3/C4 se aplicó incompleta: `cancelled` no existe en las semillas.**
Freeze §3 congela `CREATED → RUNNING → {COMPLETED | FAILED | CANCELLED}` y §13 lista `cancelled` como terminal. Pero `docs/especificacion-contratos-v2.md` línea 118 declara `status: 'created' | 'running' | 'awaiting-verification' | 'completed' | 'failed'` (sin `cancelled`), y `docs/esquema-datos-v2.md` (~línea 168) tiene el mismo CHECK sin `cancelled`: un `run.cancelled` sería improyectable. El comentario `[S-E · C4]` dice "el vocabulario COMPLETO es el del freeze §3" pero el union de estados no se tocó. **Fix:** corregir ambas semillas al importar el error a S-G (agregar `'cancelled'` al union y al CHECK), con marca `[S-E]` propia.

**2. [P1] `max_steps` es "contrato, no cortesía" (freeze §3) pero ninguna semilla lo carga.**
Ni `Run` (contratos v2 §3) ni `runs_projection` (esquema v2 §5) tienen el campo. Si el guard del loop es contrato, tiene que vivir en el dato del Run (o su payload de `run.created`). **Fix:** agregar `maxSteps`/`max_steps NOT NULL` a las semillas o declarar explícitamente en qué payload viaja.

**3. [P1] `awaiting-verification` existe en §13 pero no en la máquina de §3 ni en el vocabulario de eventos.**
El freeze tiene dos máquinas de Run que no coinciden: §3 (sin `awaiting-verification`) y §13 (con él). Ningún evento `run.*` del vocabulario dispara la entrada a ese estado — una proyección derivada de eventos no puede producirlo. **Fix:** decidir UNA de dos: (a) evento nuevo (`run.verification_pending`), o (b) declarar `awaiting-verification` sub-estado derivado de proyección (como `interrupted`), y unificar §3/§13.

**4. [P1] Cancelación jerárquica sin regla: huérfanos reales en cola.**
`run.cancelled` es por-run y la jerarquía viaja solo en `parent_run_id`. Cancelar el raíz deja sub-runs RUNNING aportando claims a un run muerto; peor: con step↔job 1:1 y cola Procrastinate (infra/02), un worker puede completar el job DESPUÉS del `run.cancelled` y apendear `run.step.completed` a un stream cuya proyección ya reportó `interrupted` — la regla "un step RUNNING no recibe evento terminal" está enunciada del lado de lectura pero nadie la hace cumplir del lado de escritura. **Fix (3 reglas para S-G):** (i) cascada: `run.cancelled` del raíz ⇒ el runtime emite `run.cancelled {reason: "parent_cancelled"}` en cada sub-run activo con `actor_id: service:runtime`; (ii) post-cancelación, los appends de `run.step.*`/`capability.job.*` de ese run se rechazan (o se aceptan marcados `late` — elegir una); (iii) barrido best-effort del job en cola. Pega a freeze §3/§13 y a infra/02.

**5. [P1] "Los sub-runs aportan claims al raíz" no tiene mecanismo, y el `provenance_hash` solo ampara UN stream.**
El anexo de canonicalización §4 computa `provenance_hash` sobre `read_stream(run_stream)` — singular. Si las conclusions del certificado provienen de claims verificados en streams de sub-runs, ¿qué evento en el stream RAÍZ los registra? Sin eso, el certificado (que cuelga del raíz, D5) referencia trabajo cuya procedencia no está amparada por su propio hash. **Fix:** regla explícita — el aporte se materializa como evento en el stream del raíz (p.ej. `●ClaimEmitted {claim_digest, sub_run_id}`), de modo que el `provenance_hash` del raíz cubra todas las conclusions. Frontera con Dylan (anexo + §7 + §13).

**6. [P1] Herencia de `policy_digest` en sub-runs no declarada.**
`policy_digest` es obligatorio por run (§13) y se fija "al crear el run raíz" (contratos v2 §3). Si un sub-run se crea tarde y la Policy cambió, ¿puede pinnear un digest distinto al del raíz? El certificado quedaría compuesto de claims verificados bajo policies distintas. **Fix:** regla — sub-run hereda el `policy_digest` del raíz; divergencia = error de contrato fail-closed (mismo espíritu que la reautorización §8).

**7. [P2] Policy endurecida no alcanza runs pinneados y no hay palanca compensatoria.**
Consecuencia directa de disolver mi etapa 4: `○PolicyChanged` "no afecta cases en vuelo" (R-Pol1) y la revocación es `"none"` en Fase 1. Si una Policy se endurece por vulnerabilidad descubierta, los cases en vuelo corren bajo la exigencia vieja sin alarma. **Fix barato con maquinaria existente:** al `○PolicyChanged`, abrir `●EscalationOpened` sobre los cases en vuelo afectados (la escalación vía tareas ya está en §6). No exige nueva infra ni rompe R-Pol1.

**8. [P1] Combinación `interaction: request_response` × `execution_profile: remote-job` sin regla de validez.**
El manifest dice qué maneja el caller (`interaction`); la distribución puede sobreescribir el perfil por despliegue (§1). Sobreescribir a `remote-job` una capability `request_response` rompe el contrato del caller (recibiría `JobRef` donde su semántica promete Result). Ni freeze §1 ni execution/06 lo cubren. **Fix:** validación del `DistributionManifest` — override a `remote-job` solo si `interaction: job`; par incompatible ⇒ `NotImplementedError` (misma doctrina anti-fallback que ya congelamos).

**9. [P1] El backend `replay` no está especificado con detalle suficiente para construirlo.**
Todo lo escrito: "prompt fijo + respuesta cacheada" (§15.7) + eventos con `prompt_digest`/`response_digest` (§3). Falta: (a) comportamiento en miss — si `replay` cae en passthrough a red en un miss, se viola la doctrina air-gapped del día D con exactamente el "fallback silencioso" que el freeze prohíbe para el despacho; (b) canonicalización del prompt para que el digest sea estable (¿Regla 2 del anexo sobre `ModelRequest`? no está dicho); (c) dónde viven los fixtures (¿`ContentStore` por `prompt_digest`? ¿archivos?) y cómo se graban. **Fix:** seed de S-G con contrato de 4 líneas: miss ⇒ `model.call.failed {error_kind: replay_miss}` jamás red; digest = Regla 2 sobre el request canónico; fixtures content-addressed; modo grabación explícito.

**10. [P2] Tercer cambio a mis notas sin addendum: la regla de reintento de `reversible-external`.**
Mi nota 03 §1.4 decía "un paso `pure` o `reversible-external` puede reintentarse automáticamente sin daño"; el freeze §13 mueve `reversible-external` al bucket "sin idempotencia garantizada NO hay reintento". El cambio es CORRECTO (reversible ≠ idempotente: re-aplicar una acción compensable duele hasta que se compensa) y lo acepto — pero la guía §2 promete que todo cambio a mis notas tiene el porqué escrito en un addendum fechado, y `execution/03` sigue diciendo "insumo para contract freeze". **Fix:** estampar el addendum en la nota 03 (mismo formato que 01/07).

**11. [P2] Menores:** (i) `interrupted` no pertenece al conjunto cerrado de `RunStep.status` — falta declarar el tipo de la vista de proyección que sí lo contiene; (ii) `serving.route() -> BackendChoice` (nota 09 §1.3) no tiene contrato en la semilla §7 — el `ModelPort` de la semilla modela un backend, no el router; (iii) el vector V1 del anexo usa `stream_id: "run:8f2c1a9b"` mientras el freeze dice `stream_id = run_id` — declarar el formato del `run_id`; (iv) el encabezado de `execution/08` sigue en "pendiente validación y ratificación de Steven" mientras el README lo declara decidido en S-E.

## (d) Juicio sobre los dos addenda — ¿aceptar o pelear?

**Etapa `policy` disuelta: ACEPTAR.** Mi diseño original (etapa 4 por invocación) tenía una virtud: conocer la exigencia ANTES de pagar el despacho. Pero el diseño nuevo la conserva y la mejora: la Policy pinneada al crear el case + `●PlanCreated` permiten detectar infactibilidad (sin ancla elegible, presupuesto) al crear el case — MÁS temprano que mi etapa 4. Además, resolución por invocación podía producir policies distintas para steps del mismo case (incoherencia del nivel titular) y hacía imposible el `policy_digest` único que el certificado exige. La reproducibilidad gana. Mi única contra real es el caso de endurecimiento tardío (objeción 7), que se resuelve con escalación, no resucitando la etapa. No pelearía.

**`parent_run_id` sobre mi opción A: ACEPTAR, con condiciones.** Aquí hay que ser honesto: mi opción A sobrevivió textual (un stream por run, correlación por payload, opciones B/C siguen descartadas) — el addendum no cambia mi diseño, lo EXTIENDE con la jerarquía que mi nota no vio y que D5 (certificado del raíz) necesita. Pero la extensión reintroduce, a granularidad de sub-run, exactamente el costo que mi análisis de la opción B advertía: "reconstruir todo el run" ahora exige fusionar N streams por `global_seq`, y el SSE `GET /runs/{run_id}/events` es por-run. Tolerable porque la lista NO-va acota a "sin árboles profundos". Lo que NO acepto tal cual es ratificar la jerarquía sin las tres reglas de las objeciones 4, 5 y 6 — sin ellas, `parent_run_id` es un puntero decorativo con huérfanos. También falta el criterio step-vs-sub-run (¿cuándo formular/QAOA/baseline son sub-runs y cuándo steps del loop fijo?) — pregunta de una línea que los seeds deben responder.

## (e) Lo que el Steven real debe mirar personalmente

1. **La cancelación jerárquica (objeción 4)** — es SU runtime + SU semántica step↔job la que produce los huérfanos; nadie más va a ver este caso antes del demo.
2. **El contrato del backend `replay` (objeción 9)** — es la config del día D y es su frontera §15.7; debe exigir el fail-closed en miss por escrito antes de S-G.
3. **La regla de validez `interaction`×`execution_profile` (objeción 8)** — es su `Dispatcher` el que quedaría en contradicción.
4. **El calendario del walking skeleton:** vence ~20-jul, tres días ANTES del cierre de ratificación (23-jul). Está construyendo sobre un diseño aún no ratificado por él mismo — riesgo bajo (un evento de punta a punta), pero debe saberlo y ratificar §2/§3 (Event/EventStore/vocabulario) PRIMERO, porque es lo que el skeleton toca.
5. **Releer la nota 03 vs freeze §13** (objeción 10) y confirmar que acepta el endurecimiento del reintento — es el único cambio a sus notas que llegó sin porqué estampado.

## (f) Hallazgos cruzados — para Dylan

- **[para Dylan · P1]** `cancelled` ausente en `Run.status` de contratos v2 y en el CHECK de `runs_projection` (esquema v2) — la importación "con correcciones aplicadas" dejó C3/C4 incompleta (objeción 1; el dueño de las semillas es él).
- **[para Dylan · P1]** Mecanismo del aporte de claims al raíz + alcance del `provenance_hash` (objeción 5) — pega al anexo de canonicalización §4 y al certificado §7, ambos su plano.
- **[para Dylan · P2]** `docs/especificacion-contratos-v2.md` §5 conserva `Guardrail`/`GuardrailSignal` (`name/flagged/confidence`) sin la renominación del freeze §5 a `Detector`/`Signal` ni los campos `{detector, target, score/label, non_decisional: true}`, y sin marca `[S-E]` — drift semilla↔freeze en su plano. Además la firma de `GatewayStage` de la semilla §8 no refleja el refuerzo `[ejecución]` de que egress solo acepta `AuthzDecision`.
- **[para Dylan · P2]** `Attestation.anchorDigest` es opcional en la semilla y en el SQL, pero el freeze §4 dice "binding a 4 digests" sin opcionalidad — decidir si `property_rule`/`human_expert` justifican el nullable y documentarlo.
- **[para Dylan · P2]** Formato de `run_id` vs el vector V1 del anexo (`"run:8f2c1a9b"`) — una línea en los seeds evita dos convenciones.
- **[para Dylan · P2]** Estampar el estado S-E en `execution/03` (addendum del reintento) y `execution/08` (encabezado desactualizado).

**Archivos leídos:** `docs/guia-ratificacion.md`, `docs/contract-freeze.md`, `docs/especificacion-contratos-v2.md`, `docs/esquema-datos-v2.md`, `docs/convergencia-diseno-v32.md`, `docs/contract-freeze-anexo-canonicalizacion.md`, `knowledge/execution/{01,02,03,04,06,07,08,09,README}.md`. No se modificó ningún archivo.

---

## Anexo C · Informe completo — rol Geovanni (infra)

Método seguido: guía §5 en orden exacto — guía §1 → freeze §7 (bloque firma/custodia) / §15.1 / §15.4 / §15.8 → `infra/01` §R → cierres de `infra/02` (§2, §5) e `infra/03` (§5.7 + actualización 18-jul). Cruces adversariales contra `docs/deployment.md`, `knowledge/trust/15` §1/§4 y el compose de diseño de `infra/03` §1.3. No se modificó ningún archivo.

## (a) Veredicto global — Geovanni

**RATIFICARÍA CON OBJECIONES.**

Las decisiones de fondo del plano son sólidas y están bien fundadas en fuente primaria (Procrastinate sobre el mismo Postgres sin Redis; Fargate sin GPU verificado en doc AWS; escalera de custodia con doctrina de llaves; local-manda). Pero el calendario de dry-runs — que es exactamente lo que la guía me pide ratificar — **no fue reconciliado con el freeze del 18-jul**: sus filas contradicen P1-10 (Fargate stretch) y P1-8 (replay como config del día D). Y el compose de diseño tiene dos bugs operativos concretos (la precarga del modelo Ollama es estructuralmente imposible con `internal: true`; la conexión api→postgres no tiene credencial) que romperían la preparación del 24–25 tal como está escrita.

## (b) Tabla por ítem del checklist (guía §5)

| Ítem                                                                                          | Veredicto                       | Causa                                                                                                                                                                                                                      |
| --------------------------------------------------------------------------------------------- | ------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Escalera de custodia §7 + doctrina "el keypair pertenece a la organización operadora"         | **RATIFICA**                    | La guía refleja el freeze §7 verbatim; la frontera existe en trust/15 §4.4; escalón 3 solo vive en el freeze (correcto: es supersesión P1-3, el freeze manda)                                                              |
| Cola: Procrastinate, mismo Postgres, sin Redis; compose `postgres+api+worker+studio[+ollama]` | **RATIFICA** (con nota P2 — O6) | La decisión está textual en infra/02 §2/§5.5; pero la cadena exacta CON worker no está congelada en ningún doc normativo — solo en la guía y el README de infra; infra/02 la enuncia SIN worker                            |
| Demo dual: Fargate stretch condicionado al verde del 27 + subnet pública/IP para pull de ECR  | **OBJETA P1** (O2)              | Freeze §15.4 e infra/03 §5.7(d) coinciden entre sí, pero el calendario infra/03 §1.5 (filas 24–25: "stack AWS arriba") quedó sin reconciliar con P1-10                                                                     |
| Modelo Ollama ~3B cuantizado default `llama3.2:3b`                                            | **OBJETA P2** (O5)              | infra/03 §5.7(c) coincide con la guía, pero la restricción es trivial (statevector de 14 qubits ≈ 0.25 MiB) y NO existe presupuesto de RAM ni spec del equipo del demo en ninguna nota                                     |
| Calendario dry-runs 27/29-jul                                                                 | **OBJETA P1** (O1, O2)          | Las fechas cierran con el roadmap, pero la fila del dry-run 2 aún dice "modelo por API externa" (contradice P1-8/NO-va), el día 28 quedó sobrecargado y la precarga del modelo del 24–25 es inejecutable como está escrita |
| Reconciliación `infra/01` §R                                                                  | **RATIFICA**                    | La lista existe de verdad (4 puntos, líneas 232–241) y ninguno toca contratos del engine, tal como afirma la guía; el punto 2 ("baseline Terraform externo") requiere confirmación del Geovanni real                       |
| Huecos §15.8 (recinto air-gapped Fase 2 · north-star)                                         | **RATIFICA**                    | La tabla del freeze coincide con la guía: dueños y fases correctos                                                                                                                                                         |

Anti-drift guía↔freeze↔notas: **todas las citas de la guía §5 dicen lo que la guía afirma** salvo la cita "(tu nota 02)" para la cadena del compose (ver O6) — el drift real está _dentro_ de infra/03 (calendario pre-freeze no actualizado), no entre guía y freeze.

## (c) Objeciones detalladas — Geovanni

**O1 — P1 · La precarga del modelo Ollama es estructuralmente imposible en el compose de diseño.**
`infra/03` §1.3: el servicio `ollama` está SOLO en la red `backend`, que es `internal: true` ("cero egress estructural"). El procedimiento de precarga declarado en la misma sección — `docker compose exec ollama ollama pull <modelo>` — corre _dentro_ de ese contenedor, que no tiene ruta a internet **nunca**, ni antes del corte físico. El prerequisito "todo se precarga antes del corte" se auto-bloquea. **Fix:** override documentado de precarga (`compose.preload.yml` con red no-interna solo para ese paso), o `ollama pull` en el host con el volumen montado, o `docker network connect` temporal — una nota de 3 líneas en §1.3, antes del 24-jul.

**O2 — P1 · El calendario de infra/03 no fue reconciliado con el freeze que lo degrada.**
Dos contradicciones fechables: (i) filas 24–25: "push a ECR; stack AWS arriba" **incondicional**, mientras freeze §15.4/P1-10 dice "Fargate stretch: solo si el local quedó verde el 27"; (ii) fila dry-run 2 (29-jul): "modelo por API externa" — un LLM generando en vivo, que la lista NO-va corta explícitamente (P1-8: `replay` es la config de primera clase del día D). El calendario es del 14-jul; la actualización del 18-jul le agregó los entregables de rúbrica pero no tocó estas filas. **Fix:** addendum de dos líneas en §1.5 — (a) el stack AWS se levanta el 28 condicionado al verde del 27, o supersesión explícita de P1-10 aclarando que _provisionar_ barato ≠ _activar_; (b) el dry-run 2 ensaya con `MODEL_ROUTER_BACKEND=replay`, api-externa como extra no-bloqueante.

**O3 — P2 · Las dos llaves Ed25519 no tienen ruta de custodia en el compose.**
Escalón 1 = "env/archivo (hoy)"; trust/15 §1 define `CHIMERA_TRUST_CERT_KEY` y `CHIMERA_JWT_KEY`. El compose de diseño solo declara el secreto `pg_password` — ningún servicio recibe las llaves, y no está decidido si van como secret file o env (env plano en el yml sería un anti-patrón para la llave que firma EL diferenciador del proyecto). **Fix:** declarar ambos secretos file-based, montados solo donde viva el Signer (la separación S2 del freeze §7 lo agradece).

**O4 — P2 · La conexión api/worker→Postgres fallará como está diseñada.**
`DATABASE_URL: postgresql://chimera@postgres:5432/chimera` no lleva credencial, pero Postgres se levanta con `POSTGRES_PASSWORD_FILE` — la imagen oficial exige scram para conexiones remotas. Primer `docker compose up` del walking skeleton: auth failure. **Fix:** entrypoint que componga la URL desde el secret (o `PGPASSFILE`).

**O5 — P2 · El presupuesto de RAM del demo no existe; la restricción escrita es teatral.**
"Que quepa junto al statevector de ieee14" es trivialmente cierto: 2¹⁴ amplitudes × 16 B ≈ **0.25 MiB**. El consumidor real: Ollama (llama3.2:3b Q4 ≈ 2 GiB pesos, ~3–4 GiB residentes) + navegador/Studio (~1–1.5 GiB) + api/worker con ortools/pandapower (~1–1.5 GiB) + Postgres (~0.3 GiB) ≈ **6–8 GiB pico** → exige equipo de ≥16 GB. "Se mide en el dry-run 1" no sustituye registrar la spec del equipo ANTES del 27 — descubrir el 27 que la laptop es de 8 GB quema el único slack. **Fix:** una línea en infra/03 con el equipo designado y su RAM.

**O6 — P2 · El compose canónico del mes no está congelado en ningún documento normativo.**
La cadena `postgres + api + worker + studio [+ ollama]` aparece solo en la guía y en el README de infra; infra/02 la enuncia **sin** worker; el freeze solo fija el walking skeleton (`postgres+api+studio`). **Fix:** una línea en el freeze (o addendum en infra/02) fijando la lista completa de servicios.

**O7 — P2 (condicional a Fargate) · Egress y secretos cloud sin diseñar.**
Subnet pública + IP pública = egress irrestricto salvo SG outbound cerrados — infra/01 §4.4 predica "SG cerrados" y la nota 03 no dice nada de outbound; tampoco está diseñado dónde viven la password de RDS ni la API key del modelo externo. **Fix:** tres líneas en infra/03 §1.4, solo si el stretch se dispara.

## (d) Riesgos operativos del día D que el checklist no pregunta

1. **SSE a través de nginx:** sin `proxy_buffering off` (+ `X-Accel-Buffering: no`), los badges por isla — el clímax visual — se congelan. Debe ser parte de la definición del `nginx.conf`, no un descubrimiento del 27.
2. **La segunda máquina del verify offline** no aparece en ninguna fila del calendario: Python + `cryptography` + bundle, sin red, preparada y ensayada. Agregarla a la fila 24–25.
3. **Higiene de estado entre ensayos:** `pgdata` persiste — los runs de los ensayos aparecerían en el Studio el día D. Falta script de reset (`down -v` + seed) como parte del guion.
4. **WSL2/Docker Desktop memory cap:** el default capea la RAM de la VM — puede OOMear a Ollama aunque la laptop tenga 16 GB. Verificar `.wslconfig` en el equipo real.
5. **Sin `restart:` en ningún servicio:** un crash del worker a mitad de demo no se auto-recupera. `restart: unless-stopped` cuesta una línea.
6. **Laptop en modo demo:** sleep/lid/throttling en batería durante CP-SAT+LLM; salida al proyector con el Studio dark-first. Checklist física para el 27.
7. **Las imágenes del 24–25 dependen del PR único de deps de S-G ya mergeado** (y de que la cuarentena npm P2-4 no muerda) — ese PR es el verdadero predecesor del calendario y no está en él.

## (e) Lo que el Geovanni real debe mirar personalmente

- **El "baseline Terraform externo"** (`infra/01` §R punto 2): solo él sabe si es real o un recuerdo del documento original.
- **Pulumi + Automation API** quedó "integrar — motor de los dos planos" (infra/01 §D) pero nada del mes lo usa: confirmar que nadie espera Pulumi funcionando para el 29.
- **Las fechas 27/29 contra su disponibilidad real.**
- **La tabla de licencias L de infra/01** — marcada "ratificación de Geovanni pendiente".
- **La doctrina de llaves y la frontera con Dylan** (trust/15 §4.4: ¿OpenBao compartido o por servicio? — Fase 2).
- **La spec del equipo del demo** (O5): decidir HOY qué laptop es y cuánta RAM tiene.

## (f) Hallazgos cruzados fuera de mi plano — para Dylan

- **[para Dylan]** `trust/15` §4 punto 4 tiene una referencia colgante: "Frontera con Geovanni **(§13**, no decidido por mí)" — esa nota no tiene §13.
- **[para Dylan]** `infra/01` §I pedía "fijar el vocabulario común de identificadores (`workspace_id`/`principal_id`) en el freeze" — el freeze no lo recoge. O se registra como diferido con dueño, o se pierde en silencio.
- **[para Dylan]** La guía §5 cita "(tu nota 02)" para la cadena de compose con worker que la nota 02 no contiene (ver O6).
- **[para Dylan]** Que el walking skeleton sea `postgres+api+studio` **sin worker** es razonable, pero conviene una palabra que evite que alguien lo lea como el compose del mes.
- **[para Dylan]** Plano de Sebas: el "presupuesto explícito" de la enumeración 2²⁹ no tiene número en ningún doc — asegurar que se corra antes del 23, porque si no cierra, `metodos` de ieee30 no puede pasar a `["cpsat","bruteforce_vectorized"]` dentro de la ventana.

---

## Anexo D · Informe completo — equipo (§6) + crítico de completitud de la guía

Barrido realizado sobre: `docs/guia-ratificacion.md`, `docs/contract-freeze.md` (completo, incl. Registro de cierre), `docs/convergencia-diseno-v32.md` §3, `docs/perfil-stem-v1-0.md`, `docs/especificacion-contratos-v2.md`, `knowledge/islanding/01`, `knowledge/quantum/01–09`, `knowledge/execution/01/07/README`, `knowledge/infra/01/02/03`, `knowledge/trust/15`. Cero archivos modificados.

## (a) Tabla — los 4 ítems de equipo (guía §6)

| #   | Ítem                                           | Veredicto                                | Causa (resumen)                                                                                                                                                                                                                                                                                                                                                                                                                        |
| --- | ---------------------------------------------- | ---------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Posición operativa (freeze §15.2)              | **RATIFICA**                             | Defendible y repetible: una oración con negativas concretas (no SCADA/EMS, no actúa sobre la red) y una positiva concreta (expediente certificado → procedimiento de aprobación vigente del cliente). Coherente con la doctrina de soberanía §15.1, el demo air-gapped, PR4 y `human_expert` = ingeniero responsable del cliente, no despachador en el lazo. Sobrevive el Q&A tipo ICE porque no promete operación: promete evidencia. |
| 2   | Camino dorado + NO-va (freeze §15.4)           | **RATIFICA** (con 2 notas de vigilancia) | El corte es correcto para las fechas: nada en NO-va es exigible en vivo en un slot de 5 min (H2 en vivo = riesgo de cola/latencia; IEEE-30 cuántico es literalmente imposible — H2 exacto ≤26 qubits vs 30 buses; corrector en vivo tiene gate go/no-go abierto). Lo apretado está DENTRO del scope, no fuera — ver objeciones.                                                                                                        |
| 3   | AcceptanceAuthority = `user:dylan` (freeze §4) | **RATIFICA** (con caveat Fase 2)         | Bien especificado: mecanismo (registro firmado), alcance (elegibilidad C3), designación **vía Policy de la distribución** — reemplazable por despliegue, coherente con la doctrina de llaves. PI como autoridad única es lo correcto para el mes. Caveat: Dylan diseña los verificadores Y los acepta (separación de deberes) — declararlo como limitación Fase 1, análogo al S2 Signer≠Verifier.                                      |
| 4   | Plan del 20% "Explicación"                     | **OBJETA — P2**                          | El plan NO va más allá de la guía misma. Detalle abajo.                                                                                                                                                                                                                                                                                                                                                                                |

## (b) Objeciones detalladas

**OBJ-1 (P2, ítem 4) — El 20% de Explicación no tiene segundo paso.** La guía §6 dice "esta guía es el primer paso de ese 20%", pero en todo el repo no existe el segundo: `knowledge/infra/03` (actualización 2026-07-18) agrega al dry-run el ensayo de 5 min, la corrida de reproducibilidad y el checklist de entregables — pero nada sobre "los cuatro pueden explicar el código". Agravante: la cifra "20%" aparece **solo** en la guía (línea 220); el enunciado/rúbrica no está commiteado, así que el peso ni siquiera es verificable en el repo. **Fix:** (1) agregar a la agenda del dry-run 1 (27-jul) una ronda de explicación cruzada — cada dueño explica 5 min un plano ajeno — + banco de Q&A por plano como seed de S-P; (2) commitear un extracto de la rúbrica oficial a `knowledge/`.

**Notas de vigilancia del ítem 2 (no bloquean):**

- **cr8 sin go/no-go:** la escalera del demo abre con "cr8 (core, en vivo)" pero los datos están "en curso" y no hay fecha límite. Fijar ≈25-jul y opener de respaldo (ieee9).
- **GW/CVXPY es "baseline oficial obligatorio" (Δ6)** pero en el freeze vive como "chequeo de cordura" (§15.3): asegurar que la comparación QAOA-vs-GW sea artefacto de primera clase del informe ≤8 páginas.
- Ventana 23→27 agresiva; el mitigante real es el walking skeleton de 48h (vence ≈20-jul) — si se atrasa, la ventana muere. Protegerlo como el ítem #1 de la semana.

## (c) Huecos de completitud de la guía

Todas las citas de sección de la guía **existen y son correctas** (verificadas una por una). Los huecos son de **cobertura**, no de citación:

1. **[P1] La fila "equipo" del Registro de cierre omite §4-AcceptanceAuthority.** El freeze §4 la marca "ratificación final del equipo", pero el Registro pt.2 solo lista "equipo → §15.2/§15.4". La guía §6 sí la pregunta — el hueco es del freeze. Fix: agregar §4 a la fila (supersesión cosmética).
2. **[P2] §2 y §5 con merge [ejecución] pero sin pregunta a Steven:** (a) proyección `RunState` + "durabilidad del mes = replay del log" (freeze §2 — en su orden de lectura pero sin ítem de checklist); (b) "egreso acepta `AuthzDecision`, jamás `Signal`" (freeze §5 — ni en lectura ni en checklist). Mitigante: ambos "entraron tal cual" de sus notas.
3. **[P2] Freeze §10 tiene un ítem [ejecución] invisible para todos:** "el `Stage` que aplica un override emite su evento él mismo antes de aplicarlo".
4. **[P2] §12 Artifact/ContentStore está tageado [confianza / frontera]** — frontera = mecánica de Steven — pero Steven no lo tiene en lectura ni checklist. Mitigante: el alcance del mes es put/get/stat mínimo.
5. **[P2] Decisión conjunta con una sola firma:** el modelo Ollama ~3B es "decisión tuya con Steven" (guía §5) pero el checklist de Steven nunca la menciona.
6. **[P2] Registro pt.2 asigna a Geovanni "§15.8" completo**, pero esa tabla tiene filas de Steven y Dylan. Fix: precisar a "§15.8 (sus filas)".
7. **[P2] El tag del freeze §7 no refleja la frontera Geovanni↔Dylan** que la guía sí marca. Cosmético.

## (d) Opinión: silencio = ratificación al 23-jul

Razonable como protección de calendario — el modelo operativo es "Dylan+Claude entregan, los dueños ratifican", la supersesión con causa sigue disponible, y un hackathon no puede bloquearse por un dueño que no responde. Pero tiene dos fallas concretas: **(1)** varios ítems no son revisiones sino **acciones** — Sebas debe correr el script, comparar digests y aportar cr8/cr6; el silencio no ejecuta scripts. **(2)** El silencio derrota al propio 20% de Explicación: un dueño que no leyó es un dueño que no explica en Q&A. Fix barato: ack mínimo ("OK mi plano" — 30 segundos), silencio al 22-jul = escalación directa de Dylan, e ítems ejecutables de Sebas **no ratificables por silencio**.

## (e) Hallazgos sueltos para Dylan

- La guía §6 cita la posición operativa **recortando "del cliente"** del final (freeze §15.2 la tiene). Es LA frase de Q&A: alinear verbatim.
- Los estimados "~90/75/45 min" son de lectura; el de Sebas no incluye tiempo de máquina. Avisárselo.
- El enunciado oficial no está en el repo — para el flip público (~1-ago) un extracto de rúbrica en `knowledge/` resuelve la verificabilidad del 20% y el contexto para lectores externos.
- Registro pt.1 vs pt.2 del freeze tienen desalineaciones internas (huecos 1, 2 y 6): vale una supersesión cosmética única, causa "auditoría de ratificación S-F".
