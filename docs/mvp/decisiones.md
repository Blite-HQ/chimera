# Registro de decisiones — cierre MVP → Planeado → Mejorado

> **Estado: VIGENTE — REGISTRO GLOBAL de decisiones, solo-anexar (2026-07-30,
> #111/#118).** Este es EL registro de decisiones de todo el proyecto
> (MVP → Planeado → Mejorado → …), autoridad vigente y el doc más citado desde
> código vivo. Regla dura: **solo-anexar** — nada de lo ya escrito se edita ni
> se borra; las correcciones son decisiones nuevas que superseden con causa.
> Vive bajo `docs/mvp/` por razones históricas; el `git mv` a `docs/` quedó
> DIFERIDO al refactoring documental final (#111 supersedida parcialmente por
> #118 — la decisión de moverlo sigue en pie, cambió el CUÁNDO). El bloque de
> convención de abajo es HISTÓRICO (la ratificación por dueños murió con #94);
> se conserva por el principio solo-anexar.

Convención original (histórica, derogada por #94):

> Convención (mandato de Dylan 2026-07-23): NADIE espera una opinión. La decisión se toma
> en el momento según feature/contexto/diseño/arquitectura, se registra AQUÍ, y el dueño
> del dominio la ratifica o edita DESPUÉS. Formato: fecha · nivel · dominio · decisión ·
> racional · cómo revertirla. Las decisiones del cierre del carril 1 (12) están en
> `docs/archivo/decisiones-delegadas-2026-07-23.md`.

| #   | Fecha | Nivel    | Dominio                                             | Decisión                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | Racional                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | Reversión                                                                                                                                                                                                                                                                                                                                                                               |
| --- | ----- | -------- | --------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | 07-23 | MVP      | planner                                             | Los planes de cierre viven en el repo (`docs/mvp/`), no en archivos locales                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | Redundancia: cualquier sesión/persona continúa con `git pull` aunque una sesión muera                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | mover a otro canal                                                                                                                                                                                                                                                                                                                                                                      |
| 2   | 07-23 | MVP      | planner                                             | Baselines GW/greedy entran al MVP (no eran del plan original de capabilities)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 | La rúbrica del reto los hace OBLIGATORIOS (15% + comparación 20%)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 | —                                                                                                                                                                                                                                                                                                                                                                                       |
| 3   | 07-23 | MVP      | planner                                             | Escala "país" (>26 nodos) = clásico + extrapolación honesta, sin pata cuántica                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                | Límite físico del H2 (26 qubits); el freeze ya lo fijó y la rúbrica premia la honestidad                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | correr H2 real si Quantinuum lo permite                                                                                                                                                                                                                                                                                                                                                 |
| 4   | 07-23 | MVP      | planner                                             | Modelo operativo: Opus valida / Sonnet implementa / Fable planifica y audita E2E                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              | Mandato de Dylan (uso responsable de tokens + redundancia)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | —                                                                                                                                                                                                                                                                                                                                                                                       |
| 5   | 07-23 | MVP      | planner                                             | Dato eléctrico ieee14: `pandapower.networks.case14()` como modelo declarado + límites estándar de planeamiento, PENDIENTE ratificación Sebas                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | Único faltante del golden path; el anchor_digest pinnea el modelo — honesto y reversible                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | Sebas sustituye el JSON y se regenera                                                                                                                                                                                                                                                                                                                                                   |
| 6   | 07-23 | MVP      | runtime-api                                         | `POST /runs` lleva el claim de dominio COMPLETO (`instance{n_nodes,edges}`, `assignment`, `canonical_statement`, `scope`, `claim_type`) como schema aditivo `RunClaimRequest`, no solo los 3 campos `{canonical_statement,scope,claim_type}` que lista el plan                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                | El seam `post_invoke` (CONGELADO, área Steven) pasa solo `output_digest`, no el objeto de salida ⇒ el claim lo declara el caller — idéntico al desacople capability↔claim del golden path `TestDosPatasReales`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    | Al cablear el cruce del gateway por step (Planeado, task 5) el claim se deriva de la salida del proposer; se elimina el campo                                                                                                                                                                                                                                                           |
| 7   | 07-23 | MVP      | runtime-api                                         | Registro instancia→verifiers en el API: CP-SAT (formal_exact) SIEMPRE para claims de optimalidad; pandapower (execution) SOLO si la instancia tiene dato eléctrico registrado; conjunto vacío ⇒ 400 fail-closed                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | Plan task 3; CP-SAT es agnóstico a la instancia (re-resuelve el MaxCut del claim); pandapower necesita topología+límites por instancia (dato de ciencia)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | Editar el mapa `ELECTRICAL_DATA` / la regla de resolución                                                                                                                                                                                                                                                                                                                               |
| 8   | 07-23 | MVP      | runtime-api                                         | Dato eléctrico semilla del registro = red sintética 4-bus PROBADA en `TestDosPatasReales` (dos islas, 7/7 real), bajo instancia `sintetica-4bus`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              | Único dato eléctrico REAL verificado hoy; ieee14 real pende de Sebas (decisión #5/#7) — habilita un smoke E2E de 2 patas honesto sin bloquear                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     | Sebas agrega ieee14 al registro y el smoke migra a esa instancia                                                                                                                                                                                                                                                                                                                        |
| 9   | 07-23 | MVP      | runtime-api                                         | Una llave Ed25519 EFÍMERA por proceso (generada en `create_app`), reusada por toda emisión de certificado                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     | Custodia = KeyProvider post-MVP (ya registrado); una llave/proceso hace el certificado byte-determinista al re-emitir                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | Inyectar `KeyProvider` cuando exista                                                                                                                                                                                                                                                                                                                                                    |
| 10  | 07-23 | MVP      | runtime-api                                         | Certificado por `GET /runs/{id}/certificate` (verbo GET, no POST)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | Proyección determinista del stream terminal ⇒ GET idempotente y semánticamente correcto; el plan permite «POST o GET si el run terminó»                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           | Agregar POST si un caller lo requiere                                                                                                                                                                                                                                                                                                                                                   |
| 11  | 07-23 | MVP      | runtime-api                                         | Run corre en `BackgroundTasks` de FastAPI (`execute_run` síncrono ⇒ threadpool de Starlette); `POST /runs` retorna `{run_id}` (202) de inmediato                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              | Plan task 1; `InMemoryEventStore` es thread-safe (`threading.Lock`) ⇒ append en threadpool + polling SSE en el loop es seguro; la carrera run-termina-antes-de-SSE la cubre el catch-up desde cursor 0                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            | Migrar a worker/cola si se necesita durabilidad de ejecución                                                                                                                                                                                                                                                                                                                            |
| 12  | 07-23 | MVP      | runtime-api                                         | Certificado pedido antes del evento terminal ⇒ 409 Conflict                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | `assemble_bundle` es fail-closed sobre run vivo (sin corte de provenance); 409 comunica «aún no» sin fabricar certificado parcial                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 | —                                                                                                                                                                                                                                                                                                                                                                                       |
| 13  | 07-23 | MVP      | runtime-api                                         | `Registry` inyectable por DI en `create_app` (default `load_registry(store)`); el API compone `execute_run` cruzando el área runtime (Steven) por MANDATO del cierre                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | Mantiene el endpoint testeable (capability echo hermética inyectada) y respeta ADR-008 (sin import estático de `blite_cap_*`; descubrimiento por entry points)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    | Revertir `create_app` a firma solo-store                                                                                                                                                                                                                                                                                                                                                |
| 14  | 07-23 | MVP      | runtime-api                                         | `ContentStore`=`InMemoryContentStore` y `Dispatcher`=`ProfileDispatcher` (perfil `in-process`) por app                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | Fase 1 in-process (freeze §1); sin durabilidad de artefactos todavía                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              | Swap por store durable detrás del mismo puerto                                                                                                                                                                                                                                                                                                                                          |
| 15  | 07-23 | MVP      | runtime-api                                         | `ruff format` aplicado a `scripts/verify_corpus_digests.py` en commit `chore` aislado — drift de formato HEREDADO de `mvp/base` (commit `b96069d`, área ciencia/reto-1), no introducido por este dominio                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | Sin esto `ruff format --check .` (gate 3, paso separado en CI) queda rojo para TODO commit de esta rama ⇒ rompe la invariante "4 gates verdes"; el cambio es 100% formato (cero semántica)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | `git revert` del chore; o ciencia lo reformatea en su rama (merge trivial)                                                                                                                                                                                                                                                                                                              |
| 16  | 07-23 | MVP      | planner                                             | Dato eléctrico ieee14: `pandapower.networks.case14()` como modelo declarado + límites estándar de planeamiento, PENDIENTE ratificación Sebas. **Task 2 la implementó — mecánica exacta en filas #11 (D3) y #12 (D4).**                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | Único faltante del golden path; el anchor_digest pinnea el modelo — honesto y reversible                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | Sebas sustituye el JSON y se regenera                                                                                                                                                                                                                                                                                                                                                   |
| 17  | 07-23 | MVP      | ciencia-reto                                        | Capability única `blite.graphs.maxcut` con `method∈{gw,greedy}` (default greedy), input QUBO `{matrix}`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | Consistencia con `blite.solvers.qubo`/`blite.quantum.qaoa` (misma convención de matrix); la rúbrica del reto exige ambos baselines clásicos                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | separar en dos ids (`blite.graphs.maxcut.gw` / `.greedy`)                                                                                                                                                                                                                                                                                                                               |
| 18  | 07-23 | MVP      | ciencia-reto                                        | `cvxpy` como extra opcional `[gw]` de `blite-cap-graphs`, import perezoso dentro del impl                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     | GW necesita SDP; cvxpy ya es dependencia de engine (mismo pin `>=1.9.2`), no agrega superficie nueva                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              | quitar el extra y el import perezoso                                                                                                                                                                                                                                                                                                                                                    |
| 19  | 07-23 | MVP      | ciencia-reto                                        | D5 — instancia ICE "provincia" (Task 3 original) queda DIFERIDA (CSVs del ICE no están en el repo + gate de ratificación de Sebas en `knowledge/islanding/01-corpus-benchmarks.md` §1.8); se agrega `ieee6` (`pandapower.networks.case6ww`) al corpus por la MISMA receta congelada (`scripts/gen_corpus_islanding.py`, doble ancla CP-SAT+fuerza bruta) como stand-in reproducible de 6 nodos para el experimento r vs p (Task 4)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            | No bloquear Task 4 mientras llegan los datos del ICE; `n=6 ≤ 14` habilita la doble ancla igual que ieee9/14; el corpus queda 8/8 con freeze intacto (6 digests preexistentes verificados sin drift antes de escribir)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | cuando lleguen los CSVs del ICE, generar `cr6`/`cr8` con la misma receta y re-apuntar el experimento r vs p (Task 4, `scripts/exp_r_vs_p.py`, default declarado `ieee6-flujo`) a la instancia real                                                                                                                                                                                      |
| 20  | 07-23 | MVP      | ciencia-reto                                        | D6 — experimento `scripts/exp_r_vs_p.py` parametrizado por instancia (`--instance`, default `ieee6-flujo`); el `optimo` CONGELADO del corpus es la verdad de terreno; barrido QAOA `p∈{1,2,3}×5 semillas` (`blite_cap_quantum.solve_qaoa`), media±std (poblacional) de `r=corte/óptimo` por `p`, comparado contra baselines GW/greedy (`blite_cap_graphs.solve_maxcut`) y CP-SAT exacto (`blite_cap_solvers.solve_qubo`); salida = tabla en stdout + JSON en `results/exp_r_vs_p/<instancia>.json` + figura opcional vía matplotlib (import perezoso — si no está instalado, se imprime aviso y se sigue)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     | La rúbrica pide implementación cuántica (30%) + comparación/escalamiento (20%); todo recomputable (nada a mano); Qiskit/Aer no es bit-determinista entre versiones (misma lección de Task 1) por lo que el JSON committeado es una instantánea ilustrativa, no un oráculo de test — los tests asertan invariantes (r∈[0,1], cpsat.r==1.0, determinismo dentro de la corrida)                                                                                                                                                                                                                                                                                                                                      | cambiar instancia/config (`--instance`, `--p-values`, `--seeds`, `--output-dir`) por flags de CLI y volver a correr                                                                                                                                                                                                                                                                     |
| 21  | 07-23 | MVP      | ciencia-reto (toca `capabilities/quantum`, aditivo) | D7 — FIX de D6: `qaoa.py::solve_qaoa` expone además del best-of-samples (`energy`) el valor esperado EXACTO ⟨C⟩ de la distribución variacional en los ángulos óptimos (`expected_energy`, statevector, positivo, `0≤expected_energy≤optimo`) y su estimador muestral (`sampled_mean_energy`, media de `_energy` ponderada por counts sobre los 2048 shots, varía con `seed`); si se pasa `reference_optimum` también `expected_ratio`. `tool.py` output_schema documenta los campos nuevos en wording genérico (sin términos de escenario). `exp_r_vs_p.py` reporta `r_esperado(p)` (curva primaria, del valor esperado) y `r_muestral(p)` media±std sobre ≥5 semillas (del estimador muestral), más `success_rate` (fracción de semillas cuyo best-of-samples alcanza el óptimo, secundario) — cambio ADITIVO, no toca `assignment`/`energy`/`approximation_ratio` existentes                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                | best-of-2048-shots sobre un espacio de 64 estados (6 qubits) encuentra el óptimo casi siempre ⇒ `r(p)=1.0000±0.0000` en todo `p` es un ARTEFACTO de muestreo, no la performance de QAOA — trivializa la métrica cuántica que pesa 30% de la rúbrica. Verificado empíricamente en `ieee6-flujo`: `expected_energy` (offset+⟨H⟩ del Hamiltonian Ising con signo invertido — ver comentario en `solve_qaoa`) da `r_esperado(p=1,2,3)=0.6085/0.7566/0.6870` (curva no trivial, seed-independiente porque solo depende de la optimización COBYLA sobre el ansatz, no del muestreo) mientras `success_rate` se mantiene en 1.0 (best-of-samples sigue trivial en esta instancia chica, reportado aparte y honestamente) | quitar los campos nuevos de `qaoa.py`/`tool.py` (no-breaking) y revertir `exp_r_vs_p.py` a reportar solo el ratio best-of-samples                                                                                                                                                                                                                                                       |
| 22  | 07-23 | MVP      | ciencia-reto                                        | D3 (Task 2) — topología eléctrica ieee14 vive en `knowledge/islanding/ieee14-topology.json` como envelope `{instancia,provenance,topology:{buses,slack,branches,loads},limits,digest}`; digest = misma canónica del corpus (`json.dumps(sort_keys=True,separators=(",",":"),ensure_ascii=True)` sin el campo `digest`, sha256 hex). Relabel de buses 0..13 — IDENTIDAD, porque el índice de bus de `case14()` ya es 0..13 ascendente (mismo orden que `asignacion_canonica` del corpus `ieee14-*.json`); `topology["buses"]` en ese orden es lo que fija el índice de `claim.assignment` en `ExecutionVerifier`. NO se guardó bajo `knowledge/islanding/corpus/` (ese directorio lo gatea `verify_corpus_digests.py` en 8/8 archivos — no se toca). Generador determinista: `scripts/gen_ieee14_topology.py`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 | El envelope necesita provenance+limits+digest junto a la topología (no solo el dict genérico) para que el `anchor_digest` de la Attestation pinnee un dato versionado y auditable, igual que el corpus; separar de `corpus/` evita romper el guard de 8 archivos que ya tiene otro dueño (Sebas)                                                                                                                                                                                                                                                                                                                                                                                                                  | Sebas sustituye el JSON (mismo envelope) y se regenera con `scripts/gen_ieee14_topology.py`                                                                                                                                                                                                                                                                                             |
| 23  | 07-23 | MVP      | ciencia-reto                                        | D4 (Task 2) — adapter `pandapower.networks.case14()` → topología genérica. **Grafo** = 20 aristas de `net.line`+`net.trafo` en servicio (idéntico al corpus `ieee14-flujo.json`, verificado 1:1). **Cargas** = `net.load` (p_mw,q_mvar) por bus. **Slack por isla**: los 5 buses-fuente de case14 (`ext_grid`+`gen` = `[0,1,2,5,7]`, calculados programáticamente y verificados contra la sonda del brief, no hardcode ciego) llevan `slack` con `vm_pu=1.0`; `ExecutionVerifier` promueve a `ext_grid` el/los que caen dentro de cada isla propuesta, así toda isla con un bus-fuente tiene fuente propia. **Impedancias — FALLBACK HONESTO aplicado**: se intentó primero derivar r/x por rama desde case14 (líneas: r/x nativos de `net.line`; trafos: `vk_percent/vkr_percent/sn_mva → z_ohm` en base declarada `V0=110kV`) y el flujo de la red COMPLETA (14 buses, una sola isla) NO convergió — `pandapower.diagnostic` marcó 13/20 ramas con `\|r\|` o `\|x\| ≤ 0.001 ohm` (las 8 líneas que en case14 corren al lado 0.208kV de los trafos colapsan a impedancia casi nula al reescalarse sobre 110kV, matriz mal condicionada para Newton-Raphson). Se aplicó el fallback (a) del brief: impedancias UNIFORMES declaradas (`r=0.5, x=1.5 ohm`, `length_km=1.0`, `max_i_ka=2.0` genérico) en las 20 ramas — el GRAFO y las CARGAS siguen siendo de case14, solo la impedancia por rama es un valor uniforme declarado (no case14-derivado). Con este fallback: red completa, bipartición válida `{0..5}\|{6..13}` y bipartición inválida `{0..6}\|{7..13}` (isla `{7..13}` desconectada, bus 7 sin arista interna) verifican como se esperaba (`pass`/`pass`/`fail`), voltajes en banda con holgura amplia (`vm_pu∈[0.978,1.0]`, loading máx ~7% del límite). **Límites**: `vm_pu∈[0.95,1.05]`, `line_loading_max_percent=100.0`, `slack_p_max_mw=400.0` (> carga total case14 ≈259 MW, con holgura declarada — el chequeo `power_balance` existe sin sabotear ningún caso de test). Ratificación de Sebas sigue PENDIENTE (fila #5) — la mecánica y la limitación quedan documentadas para que la ratifique con datos, no a ciegas.                                                                                                                 | Es la tarea de mayor riesgo del sprint (probe: case14 real es multi-voltaje, el formato genérico solo modela líneas); el intento de derivación fiel se hizo primero y se documentó POR QUÉ falló (diagnóstico real de pandapower, no una suposición) antes de caer al fallback — la rúbrica premia limitaciones honestas explícitas sobre convergencia forzada o datos fabricados                                                                                                                                                                                                                                                                                                                                 | si Sebas provee impedancias reales por rama que sí converjan (p.ej. un V0 distinto, o un modelo por tramos de voltaje fuera del formato genérico), se regenera `ieee14-topology.json` con `scripts/gen_ieee14_topology.py` ajustado y se re-congela el digest                                                                                                                           |
| 31  | 07-23 | MVP      | infra                                               | `worker` es servicio de primera clase en `compose.yaml` (misma imagen que `api`, comando `procrastinate worker`), pero CONFIG-presente-e-INERTE: no hay app procrastinate registrada en el engine todavía                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     | El seed `test_seed_infra_compose.py` y freeze §15 (O6) lo exigen como servicio; el runtime aún no encola jobs (dominio 01) — la verificación viva levanta solo `postgres api studio`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              | Dominio 01 registra la app procrastinate y el worker se activa SIN cambiar el compose; o se elimina el servicio                                                                                                                                                                                                                                                                         |
| 32  | 07-23 | MVP      | infra                                               | Credencial de DB vía `*_FILE`: un entrypoint infra-owned (`docker/api-entrypoint.sh`) lee `CHIMERA_DB_PASSWORD_FILE` y arma `CHIMERA_DATABASE_URL` en runtime                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 | EG-3/EG-4 (secreto jamás en el YAML) sin tocar `engine/` (`create_event_store` solo lee `CHIMERA_DATABASE_URL`) — el wrapper es de infra, cambio cero en el engine                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                | Soporte `_FILE` nativo en el engine ⇒ quitar el wrapper                                                                                                                                                                                                                                                                                                                                 |
| 33  | 07-23 | MVP      | infra                                               | `studio` servido por nginx con reverse-proxy de `/invoke\|/runs\|/health` a `api:8000` (`proxy_buffering off`, `read_timeout` largo para SSE); build con `VITE_GATEWAY_URL=""` (same-origin)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | Evita CORS sin tocar el api (dominio Steven); coincide con el comentario de `api/.../app.py` ("el `proxy_buffering off` vive en el compose, frontera Geovanni")                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | CORS middleware en el api + `VITE_GATEWAY_URL` absoluto ⇒ quitar el proxy                                                                                                                                                                                                                                                                                                               |
| 34  | 07-23 | MVP      | infra                                               | `postgres` publicado en loopback `127.0.0.1:5544:5432`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | `tests/integration/test_postgres_event_store.py` corre en el host con `CHIMERA_TEST_DATABASE_URL`; 5544 evita choque con un pg local en 5432; loopback = no expuesto a la red                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     | Quitar el publish y correr pytest dentro de un contenedor                                                                                                                                                                                                                                                                                                                               |
| 35  | 07-23 | MVP      | infra                                               | El nombre canónico de la env del studio es `VITE_GATEWAY_URL` (no `VITE_API_URL` del texto de `04-infra.md`)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | El código es autoridad: `apps/studio/src/gatewayClient.ts` y `.env.example` ya usan `VITE_GATEWAY_URL`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            | Renombrar en `gatewayClient.ts` + `.env.example` + compose                                                                                                                                                                                                                                                                                                                              |
| 36  | 07-23 | MVP      | infra                                               | `compose.record.yml` = override mínimo de modo grabación (bind-mount `./recordings` + `TZ=UTC` determinista)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | infra/03 exige el override de record separado; el seed solo requiere que exista; la captura de bundles se cablea cuando runtime/entregable emitan — honesto y reversible                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | Editar el override cuando el runtime emita bundles al disco                                                                                                                                                                                                                                                                                                                             |
| 37  | 07-23 | MVP      | infra                                               | Aplicar `ruff format` a `scripts/verify_corpus_digests.py` (drift de formato PRE-EXISTENTE en `mvp/base`, ajeno a infra) como primer commit del branch                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | El mandato exige los 4 gates verdes antes de cada commit; `ruff format --check .` escanea todo el árbol y este archivo lo tenía rojo. Cambio format-only, determinista (ruff format ≈ black), preserva comportamiento; `scripts/` no lo analizan pyright/lint-imports/pytest ni lo prohíbe 04-infra                                                                                                                                                                                                                                                                                                                                                                                                               | `git revert` del commit `style:`                                                                                                                                                                                                                                                                                                                                                        |
| 38  | 07-23 | MVP      | infra                                               | `secrets/postgres_password.txt.example` es UNA sola línea sin comentario `#` (antes traía una línea `# cp ...`)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | `postgres` y `docker/api-entrypoint.sh` leen el archivo ENTERO como password; el comentario metía `#`+newline y rompía el DSN del entrypoint en un `cp .example .txt` manual (footgun cazado en el review de Task 3). La instrucción `cp` se movió a `docs/mvp/infra-verificacion.md`                                                                                                                                                                                                                                                                                                                                                                                                                             | Restaurar el comentario y documentar la normalización del smoke como paso obligatorio                                                                                                                                                                                                                                                                                                   |
| 46  | 07-23 | MVP      | frontend                                            | Toggle fixtures↔vivo por `VITE_API_URL` (base de `chimera_api`): ausente ⇒ demo/fixtures (fallback intacto). Todo el egress a `chimera_api` (SSE, POST /runs, GET certificate) vive en `gatewayClient.ts`; `VITE_GATEWAY_URL`/`invokeCapability` (gateway del engine, `/invoke`) NO se toca                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | Plan 03 fija "`VITE_API_URL` ausente = fixtures"; INV-1 = un solo módulo de egress, admite varias funciones/bases                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 | renombrar/unificar la env var; el módulo sigue siendo el único egress                                                                                                                                                                                                                                                                                                                   |
| 47  | 07-23 | infra    | frontend                                            | Los gates de test de esta sesión corren `vitest --pool=threads --no-file-parallelism` (el pool `forks` y los workers paralelos no arrancan en este sandbox WSL2). Config commiteada (`vite.config.ts`) INTACTA — CI real usa forks                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            | Environment-only: `forks`/paralelo cuelga con "Timeout waiting for worker"; threads secuencial pasa 35/35 en 11s                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | quitar los flags cuando el runner arranque workers                                                                                                                                                                                                                                                                                                                                      |
| 48  | 07-23 | MVP      | frontend                                            | `ProjectedEvent` gana campo opcional aditivo `assurance?:{verifierClass, level}`; `toProjectedEvent` lo puebla de `payload.attestation.{verifier_class,level}` y corrige el verdict a `payload.verdict` (el wire real del orchestrator NO trae `payload.verification`). `verification.completed` → `AssuranceBadge` clase+AL+verdict; `claim.emitted` (sin AL) → marcador de claim                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            | nota 18 §5 permite props UI adaptables; el timeline necesita clase+AL para tarea 4; el mapper viejo apuntaba a un shape inexistente (bug latente)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 | quitar el campo/badge; el verdict-fix no se revierte (era bug)                                                                                                                                                                                                                                                                                                                          |
| 49  | 07-23 | MVP      | frontend                                            | `POST /runs` y `GET /runs/{id}/certificate` aún no existen en `chimera_api` (dominio runtime-api sin ejecutar en mvp/base). El Studio programa contra el contrato del plan 01; en modo demo `createRun` corta a un run mock local (`DEMO_RUN_ID`) y el certificado sirve el fixture. Flip a vivo = poner `VITE_API_URL` + endpoints (5 min, ya cableado y testeado con fetch mockeado)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | Plan 03 §2 lo autoriza explícitamente ("mientras no exista, contra el contrato + marcar el cambio a vivo como 5 min")                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | eliminar la rama demo cuando el backend exista                                                                                                                                                                                                                                                                                                                                          |
| 50  | 07-23 | MVP      | auditoria                                           | MVP APROBADO CON CONDICIONES (F1 gate Studio + F4 compose vivo); pulido de demo (superficie agéntica, reorg narrativa, guion) pasa a PLANEADO                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 | Mandato de Dylan: mantener el MVP como base estable y validar integración antes de iterar                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         | reabrir el veredicto en auditoria-mvp.md                                                                                                                                                                                                                                                                                                                                                |
| 51  | 07-23 | MVP      | auditoria                                           | El reto queda RESUELTO nivel provincia con ieee6 (r=0.608 ≥ 0.6 en p=1, baselines completos, JSON reproducible)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | Criterio oficial del PDF cumplido; ICE real es Planeado (D8 ciencia)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              | correr exp_r_vs_p con la instancia ICE al existir                                                                                                                                                                                                                                                                                                                                       |
| 52  | 07-24 | MVP      | fix-auditoria (frontend)                            | `apps/studio/vite.config.ts` fija `pool: 'threads'` (antes: default `forks`). Cierra **F1**: `pnpm -C apps/studio run test:run` corre 18 archivos/89 tests verdes en ~4 s (exit 0), sin cuelgue ni "no tests".                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                | `forks` cuelga bajo presión en el sandbox WSL2 ("Timeout waiting for worker", nota #47) — causa del síntoma F1 (255 s / "no tests" / errores colgantes) al correr la config commiteada. `threads` es liviano, estable (verificado 2× + 9 corridas de control con forks todas verdes) y CI-safe para tests jsdom puros sin binarios nativos; no borra ni debilita ningún test.                                                                                                                                                                                                                                                                                                                                     | Quitar la línea `pool: 'threads'` (vuelve al default `forks`).                                                                                                                                                                                                                                                                                                                          |
| 53  | 07-24 | MVP      | fix-auditoria (ciencia/deps)                        | `[tool.uv] override-dependencies = ["highspy==1.14.0"]` en pyproject raíz. Cierra **F3**: el wheel de highspy 1.15.0/1.15.1 (linux cp312) no exporta `_ZN5Highs13releaseMemoryEv` → cvxpy lanzaba ImportError al probar el solver HIGHS y caía a otro con warning ruidoso. 1.14.0 (el más alto que importa limpio; 1.15.x rotos, ≤1.14 limpios) elimina el error del log; HIGHS vuelve a `installed_solvers()`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | highspy es dep TRANSITIVA de cvxpy (extra `[gw]` de blite-cap-graphs + dep directa de engine); HiGHS es LP/MIP y NO participa en la relajación SDP de GW → el pin es cosmético para el resultado y solo limpia el log. Override (no dep directa) porque no es dependencia declarada nuestra. 4 gates verdes (436 passed, 12/12 imports, ruff/pyright limpios).                                                                                                                                                                                                                                                                                                                                                    | Quitar la línea override cuando exista un wheel highspy ≥1.15.x que importe en esta plataforma.                                                                                                                                                                                                                                                                                         |
| 54  | 07-24 | MVP      | fix-auditoria (ciencia/deps)                        | Grupo `[dependency-groups] experiment = ["matplotlib>=3.9"]` + `[tool.uv] default-groups = ["dev", "experiment"]`. Cierra **F2**: `uv run python scripts/exp_r_vs_p.py --instance ieee6-flujo` (sin flags) ya genera la figura r vs p (PNG 640×480 con barras de error de `r_muestral` ±std: p1=0.0051, p2/p3=0.0041) además del JSON. Se commitea el PNG (`results/` trackeado; el JSON deliverable ya estaba versionado).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | La rúbrica exige la figura r vs p con barras de error; `_maybe_plot` ya existía (import perezoso) pero matplotlib no estaba declarado → la figura se omitía. Grupo dedicado `experiment` (no en `dev`) separa deps de entregable de tooling; `default-groups` lo hace default para que el comando del Done funcione sin `--group`. matplotlib 3.11.1 (+ contourpy/pillow/fonttools/kiwisolver/cycler); no entra en cobertura/pyright/lint-imports → 4 gates verdes.                                                                                                                                                                                                                                               | Quitar el grupo `experiment` y `default-groups` (la figura vuelve a opcional) y borrar el PNG.                                                                                                                                                                                                                                                                                          |
| 55  | 07-24 | MVP      | fix-auditoria (infra)                               | **F4 verificado EN VIVO** (sin cambios de código). `bash scripts/smoke_infra.sh` → `SMOKE: PASS` (postgres healthy + api `/health` ok + evento `run.created` escrito por engine → postgres(compose) → leído por api SSE). `tests/integration` contra el Postgres vivo: 25 passed / 0 skipped (los 8 de Postgres, antes saltados). Stack bajado (`docker compose down`, sin `-v`).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | Condición de cierre manual del MVP: el walking skeleton P0 debía demostrarse vivo, no sólo validado estáticamente. El compose booteó tal cual — la imagen `api` no incluye matplotlib (`--package chimera-api` deja fuera el grupo `experiment` de F2) y respeta el override de highspy de F3, así que F2/F3 no rompieron el build.                                                                                                                                                                                                                                                                                                                                                                               | N/A (verificación). Re-verificar: `bash scripts/smoke_infra.sh` + `CHIMERA_TEST_DATABASE_URL=... uv run pytest tests/integration -q --no-cov`.                                                                                                                                                                                                                                          |
| 56  | 07-24 | MVP      | fix-auditoria (entregable)                          | `challenges/reto1/run_all.py` (Dominio 05, ítem 1 Nivel-MVP): entry point único reproducible. Reproduce figuras/cifras del reto en `ieee6-flujo` (reusa `scripts/exp_r_vs_p.py` vía `importlib`, sin duplicar) Y emite un certificado REAL 7/7 (AL3, 2 patas solver+execution, `verdict=verified`) disparando una corrida Chimera in-process (`TestClient` sobre `create_app`, espejo de `tests/unit/api/test_certificate.py::TestGoldenPath` — no un fixture). El certificado se emite sobre `sintetica-4bus`, NO sobre `ieee6-flujo`, porque es la única instancia con dato eléctrico registrado en `chimera_api.instance_verifiers.ELECTRICAL_DATA` (decisión #8) → dos patas reales; certificar ieee6 hoy sería una sola pata (CP-SAT). Salida en `results/reto1/` (figura + bundle + `resumen.md`). Determinista (seeds fijos; la llave Ed25519 es efímera por proceso —decisión #9— así que los bytes del bundle varían entre corridas, pero `verify-bundle` da 7/7 siempre).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           | La lista de entrega del reto exige UN entry point que reproduzca cada figura/cifra + un certificado verificable offline; el diferenciador Chimera es "no nos crea — corra `verify-bundle`". Certificar sobre la instancia de 2 patas ya probada (en vez de fingir una segunda pata inexistente en ieee6) es la opción honesta que la rúbrica premia (limitaciones explícitas), documentada en `resumen.md` §"Por qué el certificado no es sobre la instancia del reto".                                                                                                                                                                                                                                           | Registrar dato eléctrico de ieee6 en `ELECTRICAL_DATA` (Planeado) y apuntar el certificado a la instancia del reto; o borrar `challenges/reto1/`.                                                                                                                                                                                                                                       |
| 57  | 07-24 | MVP      | fix-auditoria (auditoria)                           | Re-auditoría de completitud del scope MVP (pedida por Dylan antes del freeze) detectó un gap real que la auditoría Fable previa NO evaluó: el **Dominio 05 (Entregable) nunca se ejecutó**. `05-entregable.md` §"Nivel MVP" define 3 ítems Nivel-1 (no Planeado): `run_all.py` (entry point único), README del reto, esqueleto de informe. Los tres se implementaron y cerraron en esta rama (run_all.py → decisión #56; `challenges/reto1/README.md` + `challenges/reto1/informe.md` → este commit). Dominios 01–04 reconfirmados completos y freezables (api 31 tests incl. E2E POST→SSE→certificado 7/7, r_esperado(p=1)=0.6085 ≥ 0.6, verify-bundle 7/7, seeds 5/5, compose vivo, Studio 89). → **MVP Nivel-1 scope COMPLETO**.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           | Dylan pidió validar "que no haya nada que agregar o arreglar dentro del scope del plan inicial" antes del freeze; la lista "FALTANTE PARA MVP (por dominio)" del plan maestro incluye el ítem 5 y la reproducibilidad es rubric-crítica ("incumplida = deducción en TODA la rúbrica"), así que el gap era Nivel-1, no diferible a Planeado.                                                                                                                                                                                                                                                                                                                                                                       | N/A (cierre de scope).                                                                                                                                                                                                                                                                                                                                                                  |
| 58  | 07-24 | Planeado | transversal (criterio)                              | El criterio de clasificación de niveles queda definido en `docs/planeado/00-criterio-niveles.md`: Planeado = clausura de tres autoridades (consigna/rúbrica del reto · identidad de la plataforma · guion congelado §15.4); Mejorado = todo lo demás por defecto. Reclasifica: gateway-por-step+AX1, ModelServer replay, Z3 y campos §1 bajan a Mejorado; escalas ICE se re-fundamentan como escalado por tamaño (P6).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | La definición por-lista del plan MVP no explicaba de dónde salía cada asignación (objeción de Dylan 2026-07-24); un criterio con autoridades nombradas es auditable y reclasificable.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | Editar el doc del criterio; las reclasificaciones se revierten moviendo filas entre tablas.                                                                                                                                                                                                                                                                                             |
| 59  | 07-24 | Planeado | demo (guion)                                        | Guion del día D definido en `docs/planeado/01-demo-dia-d.md`: 5 actos (compose vacío honesto → misión determinista sin LLM → run vivo 2 patas → falla sembrada refutada → verify-bundle offline + escalado). Estrategia de dos repos: `reto1-vanilla` = entregable oficial del reto; Chimera = plataforma que lo certifica; cr6/cr8 + 19 corridas Nexus entran a Chimera como DATOS (instancias con digest + patas pre-corridas P1-7).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | El vanilla ya supera la consigna (r=0.83 en p=1, hardware Quantinuum real) — re-resolver dentro de Chimera duplicaría ciencia sin subir rúbrica; certificarlo ES el diferenciador y mantiene el agnosticismo.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     | Deshacer el guion no toca código; la importación de instancias es aditiva (borrar los JSON del corpus).                                                                                                                                                                                                                                                                                 |
| 60  | 07-24 | Planeado | frontend-studio                                     | Los mocks de runtime del Studio se declaran defecto de identidad (P1, máxima prioridad): 6/7 queries sin rama live, vista Red estática, compose sirviendo fixtures (`VITE_API_URL` jamás seteada en Dockerfile/compose). El modo fixtures sobrevive SOLO como Replay etiquetado con banner, nunca default silencioso.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         | Una plataforma cuyo pitch es "no fabricar veredictos" no puede fabricar datos en su propia UI; además el guion (acto 0) usa el Studio vacío como beat de honestidad. Mapa completo del hallazgo en la sesión 2026-07-24.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | Revertir = volver al toggle silencioso (no recomendado); el detalle técnico vive en `00-criterio-niveles.md` P1-P3.                                                                                                                                                                                                                                                                     |
| 61  | 07-24 | Planeado | transversal (mandato Dylan)                         | Mandato de Dylan (v2 del set `docs/planeado/`): Chimera NO es solo verificador — debe GENERAR el resultado del reto con paridad a `reto1-vanilla` (derivación de datos ICE, QAOA, baselines, estadística), producir el informe formal como deliverable certificado, y presentar con superficie visual superior (mapa geográfico real, particiones, gráficos). El mapeo determinista de misiones (v1 P5) queda ELIMINADO; el agente real (ModelServer+LLM) sube de M1 a P4. Replay de sesiones agénticas REALES sigue siendo la puesta en escena por defecto (§15.4); LLM vivo en escena = flip explícito de Dylan. Supersede parcialmente #58/#59.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            | "Hablo con Chimera y Chimera resuelve" es identidad de producto, no un extra; un mapeo determinista fingiendo agencia viola la honestidad que la plataforma predica.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              | Restaurar v1 de `docs/planeado/` desde git; las promociones/eliminaciones viven en las tablas P/M del criterio.                                                                                                                                                                                                                                                                         |
| 62  | 07-24 | Planeado | transversal (cobertura)                             | Validación de cobertura diseño-vs-Planeado ejecutada (`docs/planeado/02-cobertura-diseno.md`): la mayoría del backlog YA está diseñado (ModelServer §15.7, sub-runs §13, deliverables §7/§12, payloads §9, ciencia construida). Ajustes derivados: (a) alcance P5 acotado — importar patas Nexus = Planeado, orquestar corridas nuevas vía qnexus = M5; (b) P7 corregido — el GeoJSON del ICE NO está en Chimera, se importa del espejo con digest; (c) propuesta SA→Mejorado (greedy ya cumple "GW + ≥1"). Choque de contrato identificado: freeze §13 "pipeline fijo Fase 1" + ratificación runtime #4 ("demo no invoca modelos") vs P4 agente que planifica — requiere supersede formal + ratificación de Steven ANTES de construir P4. Agenda de research R1–R6 fijada.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | El mandato v2 se construye sobre diseño existente donde lo hay; donde lo contradice, el supersede debe ser explícito y ratificado, no silencioso.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 | Revertir ajustes editando el doc de cobertura; el supersede de §13 aún NO está ejecutado — solo identificado.                                                                                                                                                                                                                                                                           |
| 63  | 07-24 | Planeado | transversal (research)                              | Research de estado del arte R1-R6 consolidado en `docs/planeado/03-research-estado-del-arte.md`. Tesis adoptadas: (1) NO se adopta motor de durable execution — se formaliza el que ya existe (loop determinista del stream, efectos journalizados por digest, `replay.divergence` tipado ⇒ "el certificado verifica ⟺ el replay fue fiel"); (2) ingesta/evidencia-externa/informe = UN patrón (instancia+receta PROV estilo dvc.lock+attestation DSSE; predicado SLSA para Nexus; PDF determinista con typst-py); (3) UI proyecta vocabularios (AG-UI/Vercel/OTel GenAI) desde el stream, jamás los adopta como protocolo. Stack: pandera+geojson-pydantic, in-toto Statement v1, typst-py, mapa SVG-fallback primero + MapLibre/PMTiles upgrade, Recharts+ErrorBar, scrubber de replay. Descartes: Temporal/Restate, LangGraph/MAF, CrewAI, vcrpy HTTP, deck.gl, Leaflet, ECharts, GX, DVC-infra, Sigstore/Rekor, LaTeX/Quarto en runtime, C2PA.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            | Cada elección respeta las restricciones (event-sourced, replay, DSSE offline, agnosticismo) y viene validada por prácticas de producción citadas con fuente.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | Editar el doc de research; ninguna elección está construida aún — todo pasa por specs en `docs/specs/` antes de código.                                                                                                                                                                                                                                                                 |
| 64  | 07-24 | Planeado | transversal (convergencia)                          | Convergencia diseño↔research VALIDADA (`docs/planeado/04-consolidacion.md` §1-2): el catálogo §14 ya traía `●PlanCreated`, execution/03 converge con R1, §15.3/§11/§7 convergen con R2/R3/R4. Divergencias resueltas: (a) attestation de importación Nexus EMBEBIDA en Fase 1 (T6; DSSE individual = Fase 2); (b) claim_type de ingesta = extensión ADITIVA del perfil STEM (anexo, ratifica dueño); (c) vistas SSE nuevas = extensión aditiva §9; (d) el supersede pipeline-fijo queda como ceremonia de Fase 0 con ratificación de Steven.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | Construir sobre convergencia probada evita re-litigar el freeze; las extensiones aditivas preservan lo congelado.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 | Editar §2 del doc de consolidación; las extensiones aditivas se revierten quitando el anexo.                                                                                                                                                                                                                                                                                            |
| 65  | 07-24 | Planeado | transversal (plan)                                  | Backlog operativo consolidado (`04-consolidacion.md` §3-4: dominios A-E + M1-M12, supersede las tablas de `00-criterio-niveles.md`) y plan paralelo v2 (`05-plan-paralelo.md`): rama `planeado/base` desde `mvp/base`, Fase 0 de contratos (6 specs de costura + tests de contrato desde la spec) que bloquea la implementación, 5 sesiones de dominio con las reglas MVP + 5 nuevas (cero mocks silenciosos, DoD = integración viva, tabla de interacciones, checkpoints de costura incrementales, presupuesto de sesión), Fase 2 de auditoría E2E + ensayo + ratificaciones.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                | Las lecciones del MVP (mocks divergentes, compose sin bootear, contratos implícitos) exigen contract-first e integración incremental; la metodología que funcionó se conserva.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    | Volver al plan por-dominio-sin-Fase-0 borrando `05`; la rama planeado/base se descarta sin tocar mvp/base.                                                                                                                                                                                                                                                                              |
| 66  | 07-24 | Planeado | A · Harness (frontera runtime §13/§8)               | **Ceremonia de supersede A1** — "pipeline fijo Fase 1" (freeze §13, `loop.py` "NO ReAct/NO plan-execute") → **loop agéntico Planeado** (P4). Diseño de los 5 componentes R1: (1) loop plano proponer→gobernar(8 etapas §8)→ejecutar→journalizar→verificar, el modelo propone y el harness es el único que ejecuta, cada transición = evento inmutable; (2) plan como artefacto en el stream (`plan.created`/`plan.item_updated` sobre `●PlanCreated` §14), ítems `{id, description, verification, status}`; replanificar = append con causa, JAMÁS re-entrada al gateway (respeta §8); (3) terminación triple: `max_turns` (~30) + budget declarado al crear el run + gate de verificación (done ⟺ verifier pasa; agotar budget ⇒ `exhausted`, nunca done implícito); (4) el agente elige sub-runs del registry (limpia el set hardcodeado formular/QAOA/baseline/verificar de §13) — sub-run = unidad que produce claims que el certificado citará; (5) replay por digest de cada efecto + evento `replay.divergence` (certificado verifica ⟺ replay fiel). Sobre `ModelPort`/`ModelServer`+backend `replay` (§15.7). Se materializa en `docs/specs/harness-agentico.md`; **NO se edita `contract-freeze.md`**.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              | El mandato (Chimera genera, no solo verifica) exige el loop; el freeze §13 congeló lo contrario a propósito. R1 y `execution/03` convergen en "loop plano, durabilidad por replay del stream, NO motor nuevo". La ceremonia registra la supersesión con causa (regla 3 del freeze) sin tocar código.                                                                                                                                                                                                                                                                                                                                                                                                              | **PENDIENTE-Steven** (es su plano §13/§8): ratifica ANTES de tocar `loop.py`. Si no ratifica, A3 avanza sobre este diseño registrado (regla del plan). Revertir = volver al pipeline fijo de `loop.py` y borrar `harness-agentico.md`.                                                                                                                                                  |
| 67  | 07-24 | Planeado | transversal (contratos/costura)                     | **Convención de fixtures de costura** (Fase 0, regla NUEVA #1 de `05`): un solo origen — modelos Pydantic del engine/sdk → JSON canónico (JCS/RFC-8785) emitido por un generador bajo `scripts/` (patrón `gen-example-bundle.py`), canónico en `tests/fixtures/contract/<spec>/`, **espejado** a `apps/studio/src/fixtures/contract/<spec>/` (Vite importa solo dentro de `src/`); parseado por el seed Pydantic Y por el Zod espejo (`schemas.ts`); test anti-drift byte-idéntico. **NO codegen Pydantic→Zod** (build-step pesado, descartado). Documentado en `docs/specs/README.md` §"Specs de costura". Fase 0 entrega spec+seed (`@pytest.mark.seed`+`xfail`); el fixture verde lo da el dueño en Fase 1 donde el modelo origen aún no existe.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           | Los 6 queries del Studio con fixtures divergentes del API real fueron LA lección del MVP; el origen único vuelve "cambiar una costura sin regenerar su fixture = defecto" enforceable en gate (el generador falla-fuerte).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | Quitar la sección del README y los dirs `*/fixtures/contract/`; cada dominio volvería a fixtures propios (el defecto corregido).                                                                                                                                                                                                                                                        |
| 68  | 07-24 | Planeado | A · Harness / confianza (freeze §14/§3 delta)       | **Eventos nuevos de la capa agéntica** — las specs introducen wire events que §14/§3 aún no listan: `plan.item_updated` (↔ `●PlanItemUpdated`), `replay.divergence` (↔ `●ReplayDivergenceDetected`), `approval.requested`/`approval.responded` (↔ `●ApprovalRequested`/`●ApprovalResponded`); `external_certificate.imported` (↔ `●ExternalCertificateImported`, ya reservado §14); más campos ADITIVOS `run.created.{max_turns, budget}` y el valor `run.failed{error_kind:"exhausted"}`. `plan.created`/`claim.emitted` ya existen. Se especifican en las 6 specs; NO se edita `contract-freeze.md`. Costura de naming: el Studio usa `capability.job.invoked`, el canónico es `capability.job.submitted` (§3/§14 C4) — el mirror del Studio se alinea en Fase 1 (D3).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | Los eventos materializan el loop agéntico (#66) y la evidencia importada (#64a); registrarlos como delta explícito evita que entren sin ratificación (regla 3 del freeze).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | **PENDIENTE-Steven** (§14/§3 [confianza/frontera]; misma ceremonia que #66). Los `●` y campos aditivos se revierten quitando su entrada del catálogo; ninguno debilita formas congeladas.                                                                                                                                                                                               |
| 69  | 07-24 | Planeado | E · API (`endpoints-studio.md`)                     | **E1 — semántica de proyección de las 6 rutas de lectura.** `GET /runs` porta `deriveRunSummary` server-side: `status="completado"` sii hay `run.completed` (el enum wire congelado no distingue failed/cancelled → `en_curso`); `verdict` emite el `ConclusionVerdict` del certificado (`verified`/`refuted`/`inconclusive`/`not_required_declared`), **NO** `pass\|fail\|inconclusive` — la prosa Zod de `runSummaryWireSchema.verdict` en la spec se LEE como `conclusionVerdict` (pin E↔D para el mirror de D3). Sin certificado (run vivo / sin ticket / `AssembleError`): defaults honestos (`"Sin conclusión registrada"`, `inconclusive`, `AL0`, `formal_exact`) para `/runs`; `[]` para `/artifacts`·`/knowledge`·`/ablation`; envelope vacío `{topology_ref:"",islands:[],cut_branch_ids:[],cut_cost:0}` para `/topology`; `attestations:[]` para step sin verificar. El certificado se proyecta reusando `assemble_bundle` + decode del payload DSSE (mismo helper que `get_certificate`). `/topology` pasa el payload de partición **INTACTO** (verification por-isla, §9). `run_id`/`step_id` desconocido → 404 (nunca 200 fabricado).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           | Un solo origen de verdad E↔D (portar la derivación del cliente mata la deriva mock-vs-real del MVP); fail-closed idéntico a `certificate.py::get_certificate`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    | Quitar `create_reads_router` de `create_app`; las formas son aditivas, no tocan nada congelado (`project_runs`/`assemble_bundle` intactos).                                                                                                                                                                                                                                             |
| 70  | 07-24 | Planeado | E · API (costuras E↔A/E↔D destapadas en Fase 1)     | **Huecos que E1 destapa, a cerrar por su dueño — E no los resuelve inventando binding:** (a) `verification.completed` real NO estampa `step_id` top-level (el orquestador emite `{claim_digest,verifier_id,verdict,attestation}`) → `/runs/{id}/steps/{step}/evidence` da `attestations:[]` para runs reales hasta que **A** estampe `step_id` (lo tiene en `PostInvokeContext`). (b) `POST /runs` (`runs.py`) no pasa `deliverables=` a `assemble_bundle` → `/artifacts` da `[]` aun en golden path (hueco Task **B**). (c) `run.metrics.recorded` (ablación) y el payload de partición (`islands`, topología) no los emite ningún run hoy → `[]`/envelope vacío contra runs reales (emisores: ciencia **B** / harness **A**). Las 6 rutas sirven **VIVO** (uvicorn + httpx, socket TCP real): `/runs` lista golden `completado`/`verified`/AL3 + `/knowledge` la conclusión AL3 real + 404 fail-closed + topología por-isla intacta + SSE aditivo fluyendo. Docker no está en este WSL: el smoke compose containerizado queda para Dylan.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | Honestidad > conveniencia: E expone la forma congelada y deja `[]`/envelope vacío donde el emisor aún no produce, con la costura flaggeada, en vez de fabricar.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | Cada gap se cierra en su dominio (A: step_id; B: deliverables/metrics; A/ciencia: partición) sin tocar `reads.py`.                                                                                                                                                                                                                                                                      |
| 71  | 07-24 | Planeado | C · Informe / arquitectura (ADR-008)                | **`blite_cap_report` es capability de la familia de DERIVACIÓN** — reutiliza los primitivos CONGELADOS del kernel de confianza (`blite.verification.*`, `blite.certificate.*`, `blite.content`) porque la identidad de una derivación ES su provenance + digest canónico (freeze §7/§12) y "una sola puerta" obliga a usar `blite.certificate.canonical` (no una copia); excepción DELIBERADA al contrato de cómputo puro ADR-008 (que lista solo las capabilities puras). Gate HONESTO: `blite_cap_report` entra a `root_packages` + contrato nuevo `ADR-008-report` que le PROHÍBE los internos OPERATIVOS del engine (`serving/gateway/runtime/authz/protocols/guardrails/events/identity`). 13 contratos import-linter, 0 rotos. Misma coartada que tendrá la capability de ingesta (B1).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 | Sin esto la capability quedaría CIEGA al linter (el smell de "contrato implícito" que `05` prohíbe) o reimplementaría `canonicalize`/`Provenance` (viola "una sola puerta").                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | Quitar `blite_cap_report` de `root_packages` + el contrato `ADR-008-report`; o (más limpio a futuro) mover `provenance`/`canonical` al SDK — refactor de frontera, fuera del alcance de C.                                                                                                                                                                                              |
| 72  | 07-24 | Planeado | C · Informe / B · Datos (costura B↔C)               | **C crea el `DerivationProvenance` compartido SIN esperar a B** — co-propiedad Sebas+Dylan, shape CONGELADO en `capability-ingesta.md` §Contrato y fijado por AMBAS seeds; C lo implementa verbatim en `engine/src/blite/verification/provenance.py` (unión discriminada por `kind`, Pydantic frozen/extra-forbid, canonicalización aplicada desde afuera, INV-2 OK — no importa serving). Desbloquea las seeds de B (ingesta) y C (3 xpassed). Deps del paquete report: `typst` CORE (su seed de byte-repro debe xpasar bajo `pytest` estándar sin `--all-extras`), `matplotlib` extra `plot` (lo provee el grupo `experiment`).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | "No esperes al dominio B" (prompt) + ambos co-poseen el tipo; quien aterriza primero lo crea. B lo reutiliza SIN cambio de forma.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 | Borrar el módulo; el shape está fijado por seed, así que una divergencia de B sería un defecto detectable, no una decisión abierta.                                                                                                                                                                                                                                                     |
| 73  | 07-24 | Planeado | C · Informe / confianza (freeze §7)                 | **Binding cifra→certificado + Statement del informe** — fail-closed: `certificate_conclusions=None` opta-OUT (modo recompilación/determinismo), cualquier valor (incluso `()`) enforced contra `conclusions ∪ attestations ∪ deliverables` (normaliza prefijo `sha256:`); una cifra que no resuelve ⇒ `UncitableFigureError` ANTES de compilar. `cert_id` entra a `params_digest` SOLO con binding activo (un `cert_id` inactivo no cambia bytes renderizados → no debe cambiar el digest). Statement in-toto del informe: `predicateType` NUEVO ADITIVO `https://blite.dev/ReportDerivation/v1`, `claim_type:"derivation"` (ya registrado, cero extensión), firma con `blite.certificate.dsse` (no reimplementa DSSE/PAE). PDF/figuras/slides byte-reproducibles CROSS-PROCESO (svg.hashsalt+fonttype=path+SOURCE_DATE_EPOCH; Typst `date:none`+`sys_inputs`, sin tempfile).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 | El binding ES la regla dura de C3 (freeze §7): nunca un informe con cifra sin sustento. El `predicateType` nuevo es aditivo (no toca el `TrustCertificate`).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | Desactivar el binding = pasar `certificate_conclusions=None`; el `predicateType` se revierte quitando `statement.py` (ningún consumidor congelado depende de él).                                                                                                                                                                                                                       |
| 74  | 07-24 | Planeado | B · Datos/evidencia (B1, freeze §12/§1/§14)         | **B1 — capability de ingesta GeoJSON→grafo** (spec `capability-ingesta.md`, R2): módulo nuevo `blite.verification.provenance` (`ExternalSourceProvenance`/`DerivationProvenance`/`DataQualityAssertion`, unión discriminada por `kind`, frozen) + paquete `capabilities/ingesta/` con `blite.ingesta.snapshot.fetch` (envuelve `ContentStore.put`, digest sobre bytes exactos) y `blite.ingesta.geojson.to_graph` (deriva `{aristas,n_nodos,nodos}` de los 2 GeoJSON ICE + receta PROV con assertions). Decisiones de diseño: (a) **ADR-008** — las capabilities NUNCA importan `blite.*`; construyen dicts con la MISMA forma y el CALLER (engine) cruza la ÚNICA puerta `canonicalize`; `provenance.py` deja `inputs/recipe/assertions` como dicts genéricos (el seed los indexa por clave). (b) **Determinismo**: la validación `geojson-pydantic` corre sobre una copia parseada que se DESCARTA (nunca fuente del output) + coords sin reformatear + orden por `FID` → cero segunda coerción de floats. (c) **Manifest v1**: se declara con el `CapabilityManifest` v1 existente; los 4 campos v2 (side_effects/required_permission/interaction/execution_profile) quedan documentados y flaggeados — **NO se toca el SDK** (carril Dylan, pendiente Fase 1). (d) deps `geojson-pydantic==2.1.1` + `pandera[pandas]` añadidas a `blite-cap-ingesta`. (e) **honestidad de aristas**: nearest-neighbor SIN filtro; sobre el ICE real → 21 self-loops + extremo SIEPAC a 0.51° → assertions `no_self_loop_edges`/`edge_endpoints_within_tolerance` fallan legítimamente (ingerido≠ancla), nada se descarta en silencio. Seed `test_seed_ingesta_receta.py` un-xfaileado (2/2 verde). Gates verdes en entorno CI (ruff · format · pyright 85=baseline · pytest 484 passed cov 91.85% · lint-imports 12·0).                                                                                                                                                                                                                                                                                                                                                                                                                                                   | El mecanismo genérico de ingesta (no el dato) que la spec pide; reutiliza `ContentStore`/`C(x)`/`●ClaimEmitted` sin maquinaria nueva (R2). La honestidad por assertions es el patrón "recuperado≠decisorio" de exec/10 aplicado a "ingerido≠ancla".                                                                                                                                                                                                                                                                                                                                                                                                                                                               | Borrar `capabilities/ingesta/` + `provenance.py` + re-xfailear el seed; quitar `blite_cap_ingesta` de los 6 lugares de `pyproject.toml` y revertir `uv.lock`. Ninguna forma congelada tocada.                                                                                                                                                                                           |
| 75  | 07-24 | Planeado | B · Datos/evidencia (B2, freeze §15.3)              | **B2 — cr6/cr8 + red ICE al corpus + guard generalizado**. (1) `cr6/cr8-{uniforme,voltaje}.json` copiados VERBATIM del espejo a `knowledge/islanding/corpus/` (digests internos preservados: `e8b2121c`/`aab9f07f`/`66bb6c5a`/`0af00267`). (2) **Red ICE**: derivación SEMÁNTICA por parseo del campo `Circuito` (paridad con `reto1-vanilla/build_cr_instances.py`, NO geometría) vía extensión GENÉRICA de `blite.ingesta.geojson.to_graph` — `edge_strategy ∈ {nearest-neighbor(default, B1 intacto), endpoint-name-match}` parametrizada por nombres de campo (`endpoint_property`/`endpoint_separator`/`node_match_property`/`weight_property`); los valores ICE viven en los params de `scripts/gen_corpus_ice.py`, cero término de escenario en el manifest (ADR-029). Resultado HONESTO: `ice-{uniforme,voltaje}.json` con `n_nodos=68` conexos / 90 aristas (de 70 subestaciones del snapshot: 2 aisladas por nomenclatura, 8 líneas descartadas — documentado en `notas` + assertion `edge_endpoint_names_resolved` passed=false), `optimo=null`/`solver_status="NOT_ATTEMPTED"` (n=68>14, sin doble ancla), `ExternalSourceProvenance`+`DerivationProvenance` embebidas (inputs por digest de snapshot), digests `0078d201`/`7bcda674`. (3) Snapshots ICE committeados en `knowledge/islanding/raw/` (reproducibilidad air-gap — el espejo estuvo AUSENTE al arranque de esta sesión). (4) Guard `scripts/verify_corpus_digests.py` generalizado: sin `!=8` clavado, `ESPERADOS_FREEZE_15_3` (8) congelado + `ESPERADOS_CHIMERA_B2` (6) pinneado, `SystemExit(1)` fail-loud → 14/14 interno+pinneado verde. Gates CI verdes (pyright 85=baseline · pytest 522 passed cov 92.12% · lint-imports 12·0 · guard 14/14).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                | El corpus vivo del checkpoint 3; la derivación semántica hace a cr6/cr8 sub-corredores COHERENTES del grafo nacional (no lo serían con la geometría cruda de B1). n=68 honesto y `optimo=null` es "ingerido≠ancla": se reporta lo derivable, no se inventa un óptimo a escala 68.                                                                                                                                                                                                                                                                                                                                                                                                                                 | Borrar los 6 corpus nuevos + `knowledge/islanding/raw/` + `gen_corpus_ice.py`; revertir la extensión `edge_strategy` y el guard a los 8 clavados. **Ratificación de Sebas §1.9 PENDIENTE** (no bloquea — patrón MVP).                                                                                                                                                                   |
| 76  | 07-24 | Planeado | B · Datos/evidencia (B3, freeze §7/§11/§14)         | **B3 — `ConsensusReplicationPredicate` §11 + importador de las 19 corridas Nexus** (spec `evidencia-externa.md`, R3). (1) Módulo nuevo `blite.verification.external_evidence`: `NormalizedCounts` (`bit_order` OBLIGATORIO sin default — mata el footgun Qiskit-LE/pytket-ILO-BE de `quantum/08` §1.5; `error_params=None` si no ruidoso), `ExternalImportStatement` (in-toto Statement v1 / predicado SLSA `blite.dev/ExternalImport/v1`, `.to_intoto()`), `normalize_counts` (conversor PLANO — **CERO `RuntimeDecoder`**, CVE GHSA-x4x5-jv3x-9c7m; el nombre prohibido no aparece ni en prosa porque el seed lo grepea). Reutiliza `provenance.py` + `canonicalize` (no reintroduce el par Provenance). (2) `evidence.py`: `ConsensusLeg{seed,backend_id,transpiled_circuit_digest,noise_config_digest}` + `ConsensusReplicationPredicate.legs=()` ADITIVO + validador (si legs no vacío: len==replicas y seeds==patas); campos existentes INTACTOS, tests previos verdes. (3) `scripts/import_nexus_runs.py`: 19 corridas → 3 capas (blob crudo `ExternalSourceProvenance` / `NormalizedCounts`+`DerivationProvenance` / `ExternalImportStatement`) EMBEBIDAS en `deliverables` (**cero firma DSSE individual** en Fase 1; Fase 2 declarada) + payload `●ExternalCertificateImported` (wire `external_certificate.imported`). **`bit_order` EMPÍRICO** (no adivinado): decodifica cada corrida bajo ambos órdenes y recompone el corte contra el grafo del corpus → **msb-left 19/19** (caso decisivo `ieee14-flujo`: msb-left=57070=best_cut, msb-right=56335 corto; validado independientemente por Opus). **Honestidad §11**: `digest_coverage_notes` declara que `circuit_digest`=canonicalize({instance,p,betas,gammas}) NO son bytes de circuito, `noise_config_digest` H2-1LE sin ruido / H2-Emulator descriptor declarativo. **4** `ConsensusReplicationPredicate` con legs (multi-backend H2-1LE+H2-Emulator: cr6-unif p1, cr8-unif p1/p2/p3, agreement=true). Salida determinista en `knowledge/nexus/` (`retrieved_at`/`imported_at` ancladas al timestamp de corrida + constante, nunca wall-clock). Seed `evidencia` un-xfaileado (pyright baseline 85→69). Gates CI verdes (pyright 69 · pytest 570 passed cov 92.35% · lint-imports 12·0). | Es el checkpoint 6 (evidencia). La custodia de terceros (in-toto/SLSA) certifica LA IMPORTACIÓN, jamás sustituye la `Attestation` científica (spec §Ortogonalidad); `bit_order` explícito + verificado es el único modo de que dos honestos no decodifiquen el mismo conteo distinto. El conversor plano es innegociable (RCE).                                                                                                                                                                                                                                                                                                                                                                                   | Borrar `external_evidence.py` + `import_nexus_runs.py` + `knowledge/nexus/`; revertir `legs`/`ConsensusLeg` de `evidence.py`; re-xfailear el seed. Ninguna forma congelada tocada (todo aditivo).                                                                                                                                                                                       |
| 77  | 07-24 | Planeado | B · Datos/evidencia (B4, §15.3) + A·graphs (cross)  | **B4 — artefacto de extrapolación honesta** (`results/extrapolation/extrapolation.{json,md}` vía `scripts/gen_extrapolation.py`, determinista, digest `e4eb94da`). Escalera de instancias anclada en la **barrera de 26 qubits** (H2 exacto, `quantum/08` §2): `quantum-eligible` n≤26 (cr6/cr8×2/ieee9/ieee14 — r cuántico REAL de las corridas Nexus, `ratio_mean` citando `job_id`) vs `classical-only` n>26 (ieee30, ICE-68 — `quantum:null` con razón de **BARRERA física, NO brecha no intentada**). Baseline clásico GW/greedy + **cota SDP** para todas; **ICE-68** (`optimo=null`) → banda HONESTA `[greedy_cut, gw_cut, sdp_upper_bound]`, cero r inventado. `honest_limitations`: (a) QAOA NO ganó a GW en ninguna corrida (verificado vacío, no supuesto; p=1 0.6924 < GW 0.878; `ratio_best=1.0` = artefacto de muestreo, no ventaja); (b) barrera física; (c) sin verdad de terreno a n=68. **Cross-dominio (flag):** corrige `blite_cap_graphs/maxcut.py` — coef SDP `0.25→0.5` (matemáticamente correcto: `terms` suma cada arista una vez en `i<j`) + expone `sdp_upper_bound`; cambio ADITIVO y **assignment-preserving** (el redondeo por hiperplano es invariante al escalar del objetivo → cero cambio a asignaciones/energías ya observadas; 27 tests de graphs verdes; los GW-cuts coinciden con el `RESULTS.md` del espejo). Gates CI verdes (pyright 69=baseline · pytest 606 passed cov 92.36% · lint-imports 12·0).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                | El entregable de escalamiento honesto de §15.3: dice DÓNDE el cuántico llega (≤26q, evidencia real) y dónde NO (barrera), sin fingir un óptimo a n=68 ni una ventaja cuántica inexistente. La cota SDP da una banda rigurosa a escala sin verdad de terreno.                                                                                                                                                                                                                                                                                                                                                                                                                                                      | Borrar `results/extrapolation/` + `scripts/gen_extrapolation.py`; revertir el diff de `maxcut.py`/`tool.py` (coef + `sdp_upper_bound`). **FLAG al dueño de `blite_cap_graphs`**: el fix del coef SDP es correcto pero toca su capability.                                                                                                                                               |
| 78  | 07-24 | Planeado | studio (producto)                                   | Modelo de producto F2a FORMALIZADO por Dylan (`docs/studio/product-model.md`): jerarquía Workspace→Project→Run; chat = superficie del project que lanza N runs (cada run enlazado a su mensaje origen; el chat jamás es fuente de verdad); demo día D run-céntrico con rutas anidables; superficies de dominio como LENTES resueltas por tipo de claim/capability (registry de lentes, la red eléctrica es la lente del caso demo). Directriz a D6: presentación conversacional como layout sobre eventos existentes. Chat multi-turno real = M1.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | La visión llevaba desde el 08-jul sin formalizar y D6/M1 la necesitaban como autoridad; decidida por Dylan en sesión dirigida (4 decisiones estructurales).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | Editar product-model.md; el routing anidable no obliga a construir projects hoy.                                                                                                                                                                                                                                                                                                        |
| 79  | 07-24 | Planeado | D · Studio (frontend)                               | **D1 — honestidad de modo en el Studio** (ejecuta la ratificación #60). `isLiveMode()` (=`VITE_API_URL` presente) parte dos modos: **Replay** (var ausente) sirve fixtures con banner global visible (`ReplayBanner` nuevo — cierra el hueco "cero semilla de UI"); **Live** consume la API real. Las 6 queries de `data/queries.ts` ganan rama demo/live (patrón `loadCertificate`): en vivo devuelven vacío (`[]`/`{}`), NUNCA el fixture, porque `chimera_api` hoy solo expone `POST /runs`, `GET /runs/{id}/certificate` y `GET /runs/{id}/events` — lista/artifacts/knowledge/step-evidence/ablation (E1/D3) no existen aún. Carrera SSE muerta: `runEventsQueryOptions` deja de parsear el fixture en vivo y fija `staleTime:Infinity`+sin refetch (el SSE `useRunEventStream` es el ÚNICO escritor). Spike muerto como default: la vista Red usa `GridSpike` solo en Replay; en vivo muestra EmptyState "topología pendiente (D3/D4)". `DEMO_RUN_ID` queda como id de Replay (rama demo de `mutations`).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | Una plataforma cuyo pitch es "no fabricamos veredictos" no puede fabricar datos en su UI; el guion (acto 0) usa el Studio vacío como beat de honestidad. Verificado EN VIVO contra el compose (ver Interacciones). TDD: 112 tests verdes (era 89), lint/arch/tsc limpios.                                                                                                                                                                                                                                                                                                                                                                                                                                         | Revertir = volver al toggle silencioso (#60 lo desaconseja): quitar `ReplayBanner`/`RedSlot`/ramas live y restaurar los fixtures incondicionales.                                                                                                                                                                                                                                       |
| 80  | 07-24 | Planeado | D · Studio (compose live; toca infra §Geovanni)     | **D2 — cablear `VITE_API_URL` en el build del Studio.** `docker/studio.Dockerfile` gana `ARG VITE_API_URL=""` y lo pasa a `pnpm build` junto a `VITE_GATEWAY_URL`; `compose.yaml` (servicio `studio`) setea `VITE_API_URL: http://localhost:3000`. OJO (causa raíz del bug #60 "VITE_API_URL jamás seteada"): coexisten DOS env vars — `VITE_GATEWAY_URL` (solo el path `/invoke`, #35) ≠ `VITE_API_URL` (el toggle live real, #46). Cablear solo la primera NO enciende nada. `http://localhost:3000` = URL same-origin del propio `studio` vista por el navegador (nginx reverse-proxea `/runs,/health,/invoke` al `api` → sin CORS); no-vacía ⇒ live ON.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | El compose del MVP servía fixtures porque el Dockerfile solo threadeaba `VITE_GATEWAY_URL`; el DoD del checkpoint exige integración viva. Verificado EN VIVO: `curl :3000/health`→`{"status":"ok"}` (proxy same-origin), `localhost:3000` horneado en el bundle (2 hits), Studio vacío sin banner en el navegador (0 errores de consola).                                                                                                                                                                                                                                                                                                                                                                         | Fragilidad: hornea `localhost:3000` en el bundle (demo local canónica §15.4). Revertir = quitar el ARG/env; follow-up host-agnóstico = base relativa (tocaría `env.ts`/`gatewayClient.ts`).                                                                                                                                                                                             |
| 81  | 07-24 | Planeado | A · Harness (A2, freeze §15.7)                      | **Adapter ModelServer tras `ModelPort`** — `blite.protocols.model_server`: 3 backends por construcción (`replay` fail-closed: MISS⇒`ReplayMissError`, jamás toca `live_caller` ni red; `record` graba fixture+manifest; `live` sin fixture). `ReplayManifest` (clave replay→response_digest, §15.7 punto 4) es pieza DISTINTA del `ContentStore`: la clave se computa sobre la FORMA del request, no sobre bytes. `replay_key_digest` incluye `backend_id` (§15.7 punto 2); reusa `certificate.canonical`. `live_caller` inyectable + `import litellm` PEREZOSO. Vive en `protocols` por AX3-b.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | El puerto ya existía (§15.7 [S-F]); faltaba el adapter. Inyección del caller + import perezoso ⇒ testeable sin red/API key/litellm instalado.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     | Borrar `model_server.py`; el puerto `ModelPort` queda intacto. Ratifica Steven (§15.7).                                                                                                                                                                                                                                                                                                 |
| 82  | 07-24 | Planeado | A · Harness / confianza (A5, freeze §7/§15.7)       | **Replay por digest de cada efecto + punto 8 del bundle** — `blite.runtime.replay`: `ReplayDivergencePayload` (`effect_kind` cerrado {model_call,capability_job}); `extract_effects` empareja capability_job por `job_id` y model_call por adyacencia FIFO; `find_replay_divergences` con `recompute` INYECTABLE (runtime sin SDK). `check_bundle` gana `punto_8_replay_fidelidad`: un `replay.divergence` en el stream TUMBA el bundle aunque la firma DSSE valide. `scripts/{verify,gen-example}-bundle` derivan el denominador de `len(results)`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | R1: 'el cert verifica ⟺ el replay fue fiel'; ninguno de los 7 puntos leía el stream. FIFO = limitación conocida bajo concurrencia, inocua en Fase 1 secuencial (sin id de correlación en el freeze aún).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | Quitar `punto_8` de `_PUNTOS` + borrar `replay.py`. Ratifica Dylan (§7).                                                                                                                                                                                                                                                                                                                |
| 83  | 07-24 | Planeado | A · Harness (infra de sesión)                       | **Gates en worktree sin el gotcha de `uv sync`** — correr los 4 gates con el PYTHON del venv del PRINCIPAL + `PYTHONPATH` a los `src` del worktree (el código editado gana sobre el editable del principal); pyright vía `--pythonpath`; `lint-imports` es el script de consola (no `python -m importlinter`).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                | `uv sync` en un worktree deja el `.venv` sin editables ni deps de terceros. Baseline pyright del repo = 103 errores TODOS en `tests/seeds/` (0 en código real); criterio de gate = no subir errores en código real, no el exit-code.                                                                                                                                                                                                                                                                                                                                                                                                                                                                              | n/a (convención de herramienta).                                                                                                                                                                                                                                                                                                                                                        |
| 84  | 07-24 | Planeado | A · Harness (A3, freeze §13/§3, decisión #66)       | **Loop agéntico de 5 componentes + plan como eventos + terminación triple** — `execute_run` gana `max_turns`(30)/`budget`(RunBudget)/`proposer` inyectable/`plan_items`; SIN proposer = pipeline fijo byte-idéntico (API/E2E intactos), CON proposer = loop plano proponer→gobernar→ejecutar→journalizar→verificar. El MODELO solo propone (vía `proposer` que envuelve `ModelPort`); el harness es único ejecutor (INV-2). `plan.created`+`plan.item_updated` (append-only). Terminación triple: max_turns, budget (fail-closed ANTES de ejecutar), gate de verificación (`post_invoke` truthy = done); agotar ⇒ `run.failed{error_kind:'exhausted'}`, jamás done implícito.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 | Mandato v2 (Chimera genera) materializa la ceremonia #66. `PostInvokeDelegate` None→bool/None reusa la costura sin inventar otra; budget auto-reportado por el proposer (medición real vive en A2); plan default de 1 ítem si falta `plan_items`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                 | Llamar `execute_run` sin proposer (rama fija) o revertir el commit `de61d6e`. Ratifica Steven (§13/§3).                                                                                                                                                                                                                                                                                 |
| 85  | 07-24 | Planeado | A · Harness (A4, freeze §13 regla 1/2/3)            | **Sub-runs: `sub_run_id` + `blite.runtime.subrun`** — `ClaimEmittedPayload` gana `sub_run_id` (opcional), campo gemelo de `sub_run_provenance_hash` (§13 regla 2: el hash encadena, el id correlaciona). Módulo nuevo `blite.runtime.subrun`: `spawn_sub_run` con herencia FAIL-CLOSED de `policy_digest` (diverge⇒`PolicyInheritanceError` antes de escribir el `run.created` del hijo); `contribute_sub_run_claims` (fail-closed a `completed`) re-emite cada `claim.emitted` del sub-run al raíz con `sub_run_id`+hash; `cancel_run_with_cascade` (`run.cancelled{parent_cancelled}` a sub-runs directos, 1 nivel). Seed `harness_loop` 5/5, xfail retirado.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | §13 regla 1/2/3 'solo construir' sobre el loop agéntico. `sub_run_provenance_hash` usa prefijo runtime-local (`blite/sub-run-provenance/v1`) para NO acoplar runtime→certificate — frontera a reconciliar con el `provenance_hash` del cert.                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | Borrar `subrun.py` + el campo `sub_run_id` (backward-compatible). Ratifica Dylan (§13)/Steven (wiring del proposer real a un spawn).                                                                                                                                                                                                                                                    |
| 86  | 07-24 | Planeado | A · Harness (A6, freeze §6/§8/§10/§14)              | **Aprobación humana estilo elicitation + verificación tripwire** — `blite.gateway.approval`: par `approval.requested`/`approval.responded` (frozen, elicitation MCP, wire consumido por D/E sin traducir). `authorize_approval_response(payload, identity, *, scope) -> AuthzDecision` FAIL-CLOSED en 3 ejes (identity.id==authorized_by; identity.kind=='human'; `override:apply:<scope>` en la intersección efectiva), reusa `Identity.permissions`+`AuthzDecision`. Mitad tripwire = SOLO verificación (cero catálogo nuevo): `●SignalRecorded`/`●EscalationOpened` existen, `●Resolved` sin wiring.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | HALLAZGO: `OverrideEvent`/`OverridePayload`/`override:apply:` no existen como código (§10 doctrina); se reusa la primitiva subyacente. Interpretaciones err al lado seguro: exige `kind=='human'` (refuerzo AX2) y match de scope EXACTO (sin jerarquía).                                                                                                                                                                                                                                                                                                                                                                                                                                                         | Borrar `gateway/approval.py`. Ratifica Steven (§8/§10)/Dylan. `●Resolved`/`GuardrailsStage` = frontera Steven.                                                                                                                                                                                                                                                                          |
| 87  | 07-24 | Planeado | D · Studio (dataviz)                                | **D5 — dataviz "r vs p".** Curva real de la ciencia (`results/exp_r_vs_p/ieee6-flujo.json`) vía Recharts+`ChartContainer` (wrapper shadcn NUEVO `components/ui/chart.tsx`, adaptado a recharts 3.8 — el stock apunta a v2; `initialDimension` resuelve el `ResizeObserver` ausente en jsdom): `<Line>` `r_esperado ⟨C⟩` (honesta, sin barras, seed-independiente) + `<Scatter>`+`<ErrorBar>` `r_muestral` (media±error de muestreo sobre 5 semillas, offsets relativos) + `<ReferenceLine>` por baseline (cpsat/gw r=1.0 con dash distinto, greedy 0.80) + tabla comparativa. `success_rate` etiquetado "best-of-shots, trivial en esta instancia" (lección #21, no headline). `rvspQueryOptions` con rama demo/live (vivo→`null` honesto, sin endpoint aún); complementa —no reemplaza— `AblationPanel` en la sub-tab Ablación. **DIVERGENCIA de spec `superficie-visual.md` §5**: la spec pinnea `AblationMetric[]` como fuente, pero esa forma no tiene eje `p` ni barras de error → no puede expresar la curva; por mandato de Dylan se usa el JSON de ciencia. Registrar para ratificación (extender `AblationMetric` o corregir §5).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    | Es EL entregable cuántico del reto (`r_esperado(p=1)=0.6085 ≥ 0.6`, decisión #51/#21); best-of-shots trivializa (r=1.0) → la curva ⟨C⟩ es la honesta. Vistas puras contra forma congelada, render en Replay etiquetado (no bloquea en E1/A). TDD: 121 tests verdes (era 112), lint/arch/tsc limpios.                                                                                                                                                                                                                                                                                                                                                                                                              | Quitar `RvsPChart`/`ui/chart`/`fixtures/rvsp`/`rvspQueryOptions`; la sub-tab vuelve a solo `AblationPanel`. La divergencia §5 se cierra ratificando o extendiendo `AblationMetric`. **Nota de numeración:** Dominio A (`planeado/harness`) reservó #71+ en paralelo — colisión probable al mergear, se renumera en orden de merge (patrón #66-#70).                                     |
| 88  | 07-24 | Planeado | D · Studio (mapa/geo)                               | **D4 — router de formatos + mapa geográfico (ICE-70 real).** `DataFormatRouter` despacha por `dataset.format`; `geojson`→`GridMap`, desconocido→EmptyState (extensible). `GridMap`: d3-geo `geoMercator().fitExtent` sobre viewBox lógico FIJO (800×520 — evita ResizeObserver/jsdom, a diferencia del canvas cytoscape del spike), líneas por kV (`Voltaje` 230→3px/138→1.5px), subestaciones como `<circle>`, tokens vía `var(--color-*)` DIRECTO (SVG sigue el tema sin re-init), atribución ICE visible. **Datos REALES de la ICE** (`datos-ice-se.opendata.arcgis.com`, validado descargable como GeoJSON): 70 subestaciones + 102 líneas (72 LineString + 30 MultiLineString), importados vía Vite `?raw` como fixtures con **digest** (`39bd9a…`/`3f7ae3…`) + **provenance** (`fixtures/ice/provenance.ts`), Zod en la frontera + `normalizeProvincia` (Limón/San José). Ese **70 ES la "red ICE 70 nodos"** (B2/R5). Wired en la tab Red con toggle Diagrama(`GridSpike`)/Mapa(router), SOLO Replay; live sin cambio. **HONESTIDAD**: el mapa es la red NACIONAL real, NO la partición del run (redes distintas — ieee14 benchmark vs ICE-70); el overlay de partición/verificación por isla es un seam `partition?` declarado pero JAMÁS renderizado (cero islas inventadas) hasta que exista la partición sobre la ICE-70 (B2/R5). Dep: `d3-geo@3.1.1`+`@types`. Polish de verificación visual: etiquetas de baselines r=1.0 (cpsat/gw) a esquinas opuestas para no encimarse.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | Dylan pidió "router por formato → GeoJSON renderiza mapa"; validado que la ICE lo ofrece. Visual "país scale" REAL y honesto (no decorativo, no fabrica coordenadas). Vistas puras, Replay etiquetado (no bloquea E1/A). TDD: 153 tests verdes (era 121); lint/arch/tsc limpios; **verificado VISUALMENTE** (silueta CR reconocible, 70 nodos + 102 líneas por kV, tema oscuro).                                                                                                                                                                                                                                                                                                                                  | Quitar `DataFormatRouter`/`GridMap`/`iceGrid*`/`fixtures/ice/`/`d3-geo`; la tab Red vuelve a solo `GridSpike`. El overlay de partición se activa cuando exista B2/R5 (partición sobre la ICE-70). Bundle: `lineas.geojson` ~409KB bundleado (aceptable demo; optimizable con reducción de precisión + re-digest). **Numeración:** posible colisión con Dominio A #71+ (patrón #66-#70). |
| 89  | 07-24 | Planeado | E · API (confianza; api Dylan-owned)                | **E1 — las 6 rutas GET de lectura de `chimera_api`** (nuevo `api/src/chimera_api/reads.py` + `create_reads_router`, mismo patrón que `create_certificate_router`; consume el puerto `EventStore`+proyecciones, jamás la tabla cruda). `GET /runs`→`RunSummary[]` (`project_runs`+`assemble_bundle`); `/artifacts`,`/knowledge`→predicate `deliverables`/`conclusions`; `/steps/{id}/evidence`→stream filtrado por `step_id`; `/ablation`→`run.metrics.recorded`; `/topology`→`partition` embebida en `verification.completed`. **Semántica honesta**: 404 si run/step desconocido; run sin certificado → conclusion/verdict null + artifacts/knowledge `[]`; step sin `verification.completed` → `attestations:[]`. Seed `test_seed_endpoints_rutas.py` **un-xfaileado** (6 rutas verdes). **CAVEATS honestos (para D3 + producción):** (1) `assemble_bundle` solo funciona con `RunTicket` en cache in-memory por-proceso (poblado SOLO por `POST /runs`) → runs durables/reiniciados no tienen cert → estas rutas muestran null/`[]` más seguido de lo que los tests happy-path sugieren; (2) el orchestrator NO puebla `Attestation.step_id` → `evidence` de un run real devuelve `attestations:[]` (honesto, no fabrica; `capability_id`/digests sí salen de `capability.job.*`); (3) `ablation`/`topology` NO tienen productor real aún (`run.metrics.recorded` / clave `partition` no existen en el engine) → honest-empty, convención snake_case propuesta como punto de partida (el harness/ciencia la afina).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | Desbloquea D3 vivo (checkpoint 2); mecánico (las fuentes Python ya estaban verdes, R6). 4 gates Python verdes: pytest 467 passed / 9 skip / 17 xfail, lint-imports 12 kept/0, ruff limpio, pyright 68 err TODOS en seeds ajenos (el seed de E1: 35→0).                                                                                                                                                                                                                                                                                                                                                                                                                                                            | Quitar `reads.py` + su `include_router` de `app.py` + re-xfailear el seed. **Numeración:** Dominio A (`planeado/harness`, COMPLETO) tomó **#71-76**; yo tomé #71(D5)/#72(D4)/#73(E1) → colisión múltiple, se renumera TODO en orden al mergear (los merges los coordina Dylan).                                                                                                         |
| 90  | 07-24 | Planeado | D · Studio (egress vivo)                            | **D3 — egress vivo del Studio contra las rutas E1** (cierra checkpoint 2 con #73). 6 funciones GET en `gatewayClient.ts` (INV-1, mismo envelope que `getCertificate`); ramas live de `runs`/`artifacts`/`knowledge`/`ablation` ahora PEGAN a las rutas (404→throw/ErrorState, `[]` real→EmptyState, validado Zod en la frontera, jamás dato fabricado). **Fix de vocabulario** (bloqueante, freeze §3/§14): `KNOWN_RUN_EVENT_TYPES` `capability.job.invoked`→`capability.job.submitted` (el SSE real emite `.submitted`; el listener viejo lo perdía en silencio). 3 wire schemas nuevos + mappers snake→camel. **Descubrimiento (typecheck)**: el `verdict` de `RunSummary`/`ProjectArtifact`/`KnowledgeClaim` es `ConclusionVerdict` (`verified\|refuted\|inconclusive\|not_required_declared`, de `blite.certificate.predicate`), NO el `Verdict` de evento (`pass\|fail`) → nuevo `conclusionVerdictSchema`. `stepEvidence`: mapa construido desde los `step_id` de los eventos (N fetches paralelos), consumer `stepsQuery.data?.[stepId]` sin cambio; campos null→`''` (nunca digest fabricado). Artifacts/Knowledge project-level: `runId` opcional → honest-empty en vivo (no hay `runId` en la navegación aún; el path per-run está implementado+testeado pero inalcanzable por UI — flagged).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | Cierra checkpoint 2 (E1+D3): run list VIVO real. Vistas contra el contrato `endpoints-studio.md`, no mocks. 195 tests verdes (era 153); lint/arch/tsc limpios.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    | Revertir las ramas live a empty (D1); el fix de vocabulario NO se revierte (era bug latente). **FLAGGED (no arreglado, contrato aparte):** `mutations.ts::toCreateRunBody` omite `instance`/`assignment` que `ClaimRequest` exige → el form "Nuevo run" da 422 en vivo hasta reconciliar el claim. **Numeración:** colisión con Dominio A #71-76 (renumera al mergear).                 |
| 91  | 07-29 | Planeado | E · API ↔ A · Harness (checkpoint 5)                | **`POST /runs` modo misión — contrato ADITIVO discriminado por presencia de campo.** Body `{mission, instance_id?, capability_id?, max_turns?, budget?}` como ALTERNATIVA al claim-first #6 (INTACTO): `MissionRequest`/`MissionBudgetRequest` con `extra="forbid"` en ambos lados hacen la unión excluyente (un body con ambos discriminadores, o con ninguno, da 422). La misión se journaliza como `description` del ítem fundacional del plan (dentro del `provenance_hash` §2 — cero supersesión de `run.created` §3); ticket VACÍO (los claims los emiten sub-runs/steps, frontera P4); SIN gate de verificación el run termina `run.failed {error_kind: "exhausted"}` — jamás `run.completed` implícito (§Contrato-3); default `max_turns` misión = 3 (conservador hasta el gate real). Spec: `endpoints-studio.md` §"POST /runs — modo misión" + cross-ref en `harness-agentico.md` §Contrato-2. Fixture de costura single-origin `contract/endpoints/post-runs-mission.json` (generador `gen-contract-fixtures-endpoints.py` + anti-drift x3, patrón harness). **FLAG (frontera Steven, hallado por el test):** en el camino de error del turno agéntico, `plan.item_updated {failed}` se apendea DESPUÉS de `run.failed` (`loop.py::_run_agentic_turn` — `fail_run` corre dentro de `_run_resolve_and_invoke`); append post-terminal en el stream del run raíz.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     | La Fase 0 fijó las rutas GET pero NUNCA el contrato de arranque conversacional: el 422 vivo (flag de #90) era un hueco de spec, no solo un bug del mapper. Cierra la costura A↔E↔D del checkpoint 5.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              | Quitar `MissionRequest` de la unión (el claim-first queda solo) y marcar la sección de la spec como RECHAZADA; el fixture y sus tests se borran juntos.                                                                                                                                                                                                                                 |
| 92  | 07-29 | Planeado | E · API (costura A, frontera P4)                    | **Proposer determinista PLACEHOLDER en `chimera_api` — etiquetado, jamás "el agente".** `_make_goal_proposer` propone la capability meta con los mismos inputs en cada turno, por la MISMA costura `Proposer` que ocupará el agente real (P4: `ModelServer` tras `ModelPort`, #81); sin llamada de modelo no auto-reporta gasto (`tokens`/`cost_usd` en `None` — honesto, no cero fingido). El mapeo determinista COMO agente sigue RECHAZADO (mandato v2): esto es el seam de arranque, no el agente. Capability default del modo misión: `blite.solvers.qubo` (desconocida ⇒ `run.failed` fail-loud DENTRO del stream, mismo contrato que claim-first).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     | El modo misión necesita arrancar el loop agéntico HOY para cerrar la costura (plan como eventos en el stream); el seam evita bloquear el checkpoint 5 en P4.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | Inyectar el proposer real por el mismo parámetro de `execute_run` y borrar `_make_goal_proposer` — cero cambio del contrato HTTP.                                                                                                                                                                                                                                                       |
| 93  | 07-29 | Planeado | D · Studio (D6, directriz #78/product-model)        | **D6 — hilo conversacional como LAYOUT en RunDetail; tab "Hilo" primera y default.** `RunThread` deriva el hilo de los eventos EXISTENTES (reducer puro): misión = mensaje del usuario (la `description` del ítem fundacional del plan, contrato #91), `plan.created` = checklist del agente plegado append-only por `plan.item_updated`, terminal = mensaje de cierre (conclusión + AL titular con `run.completed`; `error_kind` sin fingir veredicto con `run.failed`/`run.cancelled`); un run claim-first muestra EmptyState honesto — jamás un hilo fabricado. Zod espejo `planCreatedSchema`/`planItemUpdatedSchema` validado contra los fixtures `contract/harness/` (lo que la sesión A dejó preparado para D6). `ProjectedEvent` gana `payload?` (ADITIVO, nota 18 §5) y `toProjectedEvent` lo conserva íntegro (freeze §9 — la proyección no recorta); `KNOWN_RUN_EVENT_TYPES` escucha `plan.created`/`plan.item_updated` (sin listener el SSE real perdía el checklist en silencio). SIN multi-turno ni persistencia de chat (M1).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | Directriz D6 del modelo de producto F2a (#78, mandato la citó como #69 pre-renumeración): la entrada conversacional es presentación sobre eventos, no feature nueva; el contrato D↔A queda cerrado por fixture, no por chat.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | Volver el default de tab a `timeline` y quitar el slot `hilo`; `payload?` es aditivo y puede quedarse.                                                                                                                                                                                                                                                                                  |
| 94  | 07-29 | Planeado | transversal (gobernanza)                            | Mandato de Dylan: los dominios YA NO tienen dueños individuales. Toda decisión se discute entre Dylan y Claude con análisis de soluciones en función de la arquitectura, el contexto y el estado del sistema. Las marcas PENDIENTE-{Steven,Sebas} dejan de ser gates: los ítems que esperaban ratificación (supersede A1 #66, cr6/cr8 §1.9, flag del append post-terminal #91) se resuelven por esa vía de discusión+análisis.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                | La hackathon terminó y el equipo cambió de modo: análisis conjunto sobre autoridad por plano.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     | Restaurar el modelo de dueños re-etiquetando las marcas PENDIENTE.                                                                                                                                                                                                                                                                                                                      |

## Sesión Fase 0 — contratos de costura (worktree `planeado/contratos`, 2026-07-24)

**Estado: FASE 0 COMPLETA.** Ceremonia A1 (#66) + convención de fixtures (#67) + delta de eventos (#68) registrados; las **6 specs de costura + 7 seeds** escritas con **gates verdes** (ruff, ruff format, pyright 0 err, lint-imports 12/0, pytest seeds 12 passed/22 xfailed/1 xpassed inocuo, markdownlint 0). Delegado a 3 subagentes Sonnet (harness / datos-evidencia-informe / frontend-wire); Opus validó cada spec contra el freeze. Falta solo la ratificación de Steven (#66/#68) — no bloquea; arranca la Fase 1 por dominio (A2–A6, B1–B4, C1–C3, D1–D6, E1–E2).

### Tabla de interacciones (regla NUEVA #3)

| Interfaz tocada                                                                                                                                               | Dominio afectado                 | Estado del contrato                               |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------- | ------------------------------------------------- |
| `docs/specs/README.md` §"Specs de costura" (convención + índice)                                                                                              | todos                            | SPEC                                              |
| Ceremonia supersede A1 → loop agéntico (#66)                                                                                                                  | A · Harness (§13/§8)             | PENDIENTE-Steven                                  |
| Convención fixtures de costura, un solo origen (#67)                                                                                                          | transversal                      | ADOPTADA                                          |
| Eventos nuevos capa agéntica (#68): `plan.item_updated`, `replay.divergence`, `approval.*`, `external_certificate.imported`, `run.created.{max_turns,budget}` | A · Harness / confianza (§14/§3) | PENDIENTE-Steven (delta freeze)                   |
| `harness-agentico.md` (A↔E↔D) + seeds `test_seed_harness_{loop,replay}.py`                                                                                    | A, E, D                          | SPEC+SEED (xfail)                                 |
| `capability-ingesta.md` (B↔A) · `evidencia-externa.md` (B) · `informe-derivado.md` (C↔B) + 3 seeds                                                            | B, A, C                          | SPEC+SEED (xfail)                                 |
| `superficie-visual.md` (D↔E↔A) · `endpoints-studio.md` (E↔D) + 2 seeds                                                                                        | D, E, A                          | SPEC+SEED (`superficie` verde, `endpoints` xfail) |
| Costura naming `capability.job.invoked`→`submitted` (Studio mirror)                                                                                           | D (Studio)                       | PENDIENTE Fase 1 (D3)                             |

## Sesión Fase 1 — Dominio E · API (worktree `planeado/api`, 2026-07-24)

**Estado: E1 + E2 VERDES, integración viva OK — lado E del checkpoint 2 listo.**
E1 (`chimera_api/reads.py`, 6 rutas GET) y E2 (lock del contrato SSE aditivo) sobre
`planeado/base`. Delegado a subagente Sonnet (E1) con TDD; Opus validó cada gate y
revisó el código. Decisiones #69–#70 (renumerar si colisionan con B/C al merge — el
ledger es compartido y hay sesiones paralelas). El otro lado del checkpoint es **D3**
(egress del Studio contra estas rutas), que programa contra las formas de #69.

**Gates (worktree `planeado/api`):** ruff `All checks passed`; ruff format 170/170;
lint-imports 12 kept/0 broken; pytest **469 passed**, cov **91.48%** (≥30). **pyright:**
la superficie de E está 100% limpia (0 err en `reads.py`/`app.py`/`test_reads.py`/
`test_sse_superficie.py`/`test_seed_endpoints_rutas.py`); el whole-repo marca 68 err
pre-existentes, TODOS en seeds de contrato de otros dominios (A/B/C) que referencian
módulos aún no implementados en su Fase 1 — baseline pre-rojo verificado por stash
(103 sin cambios = 103 con cambios; limpié mi seed 36→0, quedan 68). "4 gates verdes"
bajo Fase 1 paralela = **cero errores nuevos + superficie del dominio limpia** (el
whole-repo no puede estar verde hasta que A/B/C aterricen sus módulos — fuera del
alcance de E, no se tocan).

**Integración viva (DoD regla #2):** Docker no está en este WSL distro, así que el
smoke compose containerizado no corrió acá. Equivalente alcanzable ejecutado: `create_app`
bajo **uvicorn real** + httpx sobre **socket TCP** (round-trip HTTP genuino, no el ASGI
in-memory del TestClient). Las 6 rutas + el SSE aditivo respondieron correcto y honesto
(golden `verified`/AL3 enriquecido, topología por-isla intacta, 404 fail-closed, plan/
aprobación fluyendo por SSE). Hallazgo del smoke: `GET /runs` hereda el fail-loud de
`project_runs` ante un `run.created` sin `max_steps` (freeze §3 — explota a propósito, no
rellena defaults); el engine SIEMPRE lo estampa, así que solo un stream hand-seeded
malformado lo dispara — robustez a considerar en Mejorado (proyección parcial-tolerante),
sin tocar la proyección congelada ahora. **Para Dylan:** el smoke containerizado queda
pendiente — `docker compose up -d postgres api && curl :8000/runs` (o `smoke_infra.sh`).

### Tabla de interacciones (regla NUEVA #3)

| Interfaz tocada                                                                                                                       | Dominio afectado        | Estado del contrato                                                                                           |
| ------------------------------------------------------------------------------------------------------------------------------------- | ----------------------- | ------------------------------------------------------------------------------------------------------------- |
| `chimera_api.reads` — 6 rutas GET (`/runs`, `/runs/{id}/artifacts`, `/knowledge`, `/steps/{step}/evidence`, `/ablation`, `/topology`) | E↔D (D3 egress)         | **VERDE** — rutas vivas; seed `test_seed_endpoints_rutas.py` verde; D3 programa contra las formas de #69      |
| Pin E↔D: `verdict` de `/runs`+`/knowledge` = `ConclusionVerdict` (no `pass\|fail\|inconclusive`)                                      | E↔D (mirror Zod de D3)  | **PIN** — la prosa `runSummaryWireSchema.verdict` de la spec se lee como `conclusionVerdict`                  |
| SSE aditivo `plan.*`/`approval.*`/partición sobre `GET /runs/{id}/events`                                                             | E↔D↔A                   | **VERDE (E2)** — proyección type-agnostic transporta intacto; test end-to-end lock (`test_sse_superficie.py`) |
| `verification.completed` sin `step_id` top-level → step-evidence `attestations:[]`                                                    | E↔A (orquestador)       | **PENDIENTE A** — A estampa `step_id` (lo tiene en `PostInvokeContext`)                                       |
| `RunTicket` sin `deliverables` → `/artifacts` `[]` aun en golden                                                                      | E↔A (Task B, `runs.py`) | **PENDIENTE B** — declarar `deliverables` en el ticket                                                        |
| Emisores de `run.metrics.recorded` (ablación) y partición `islands` (topología)                                                       | E↔B/A (ciencia/harness) | **PENDIENTE** — E sirve la forma; el emisor la produce                                                        |
| Studio `KNOWN_RUN_EVENT_TYPES` sin `plan.*`/`approval.*`                                                                              | D (Studio, D6)          | **PENDIENTE D** — el SSE ya los emite; el mirror del Studio debe escucharlos                                  |
| Naming `capability.job.invoked`→`submitted` (heredado #68)                                                                            | D3                      | **PENDIENTE D** (sin cambio en E — E ya proyecta `.submitted`)                                                |

## Sesión Fase 1 — Dominio C · Informe (rama `planeado/informe`, 2026-07-24)

**Estado: C1–C3 COMPLETOS + checkpoint 7 (lado C) VERDE.** Opus validó / 6 subagentes Sonnet
implementaron (fundación por Opus). Commits, cada uno con los 4 gates + import-linter verdes:
`provenance` (fundación) → C1 plotting determinista → C2 informe Typst → C3a binding+anexo+statement
→ C3b slides+fixtures → smoke de integración. Decisiones #71–#73 arriba (renumeradas de #69–#71 al
mergear: E tomó #69–#70 en paralelo — ledger compartido).

**Entregado (informe-derivado.md §a/b/c):** `capabilities/report/` (`blite_cap_report`) con
`render_figure` (SVG byte-reproducible cross-proceso), `compile_pdf` (Typst `date:none`, ≤8p,
byte-reproducible), `compile_slides` (air-gap), binding cifra→certificado fail-closed, anexo de
verificación machine-readable, y el Statement SDK del informe (in-toto + DSSE). Fixtures de contrato
`tests/fixtures/contract/informe/{figura,pdf}-example.json` espejados byte-idénticos a `apps/studio/`.

**Integración viva (checkpoint 7, DoD regla NUEVA #2):** `tests/smoke/test_informe_pipeline.py` corre
el pipeline COMPLETO figura→PDF→binding→anexo→statement contra la instancia certificada REAL de la
Fase 0 (`scripts/example-bundle.json`, run `8f2c1a9b`): 5/5 verde. **Docker no está en este WSL**, así
que la evidencia es el pipeline Python EJECUTADO en la suite, no `docker compose up`.

**Salvedades / pendientes:**

- **pyright de proyecto:** MIS archivos (report + seed informe + `provenance`) = **0 errores**; los
  errores restantes son 100% seeds de dominios cuyos módulos Fase-1 aún no existen. Estado esperado de
  la rama de integración; va a verde cuando cada dominio complete sus módulos.
- **Fixes incidentales preexistentes de Fase 0** (no causados por C, corregidos para desbloquear mi
  gate): `ruff I001` en `test_seed_ingesta_receta.py` (imports locales sin ordenar) y tipado de
  `test_seed_informe_derivado.py` (el spread `**inputs` rompía pyright strict al existir `compile_report`).
- **PENDIENTE ratificación Dylan:** decisiones #71–#73 (excepción ADR-008 de report, binding, statement).
- **Lado D del checkpoint 7 (D4 mapa + D5 r-vs-p):** PENDIENTE dominio D — el lado C está cerrado.

### Tabla de interacciones (regla NUEVA #3)

| Interfaz tocada                                                                                                            | Dominio afectado                         | Estado del contrato                                                                                                                                                             |
| -------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `engine/src/blite/verification/provenance.py` (`DerivationProvenance`/`ExternalSourceProvenance`)                          | B (ingesta/evidencia) ↔ C                | VERDE — B lo reutiliza SIN cambio de forma (co-propiedad; C lo aterrizó primero)                                                                                                |
| `blite.report.render_figure`/`compile_pdf`/`compile_slides` (CapabilityManifest v2)                                        | A · ejecución (Registry/Dispatcher)      | SPEC — manifest v2 pendiente Fase 1 (misma discrepancia que ingesta, no exclusiva de C)                                                                                         |
| Contrato import-linter `ADR-008-report` (report → solo primitivos congelados)                                              | transversal / arquitectura               | ADOPTADA (#71)                                                                                                                                                                  |
| Fixtures `tests/fixtures/contract/informe/{figura,pdf}-example.json` + espejo `apps/studio/src/fixtures/contract/informe/` | D · Studio (badges `sha256 · cert:<id>`) | VERDE (fixtures byte-idénticos + anti-drift) — el parsing Zod es de D (`superficie-visual.md`)                                                                                  |
| `deliverables[{artifact_ref,digest}]` / `conclusions[]` / `attestations[]` del certificado (binding)                       | confianza (freeze §7)                    | VERDE — reutilizado sin cambio de forma; el binding resuelve contra ellos                                                                                                       |
| Statement `https://blite.dev/ReportDerivation/v1` (`claim_type:"derivation"`)                                              | confianza                                | ADITIVO — no toca el `TrustCertificate`; `derivation` ya registrado (perfil §1)                                                                                                 |
| **Datos reales de B (instancias cr6/cr8)** en el pipeline del informe                                                      | B · Datos                                | **PENDIENTE — tarea de 5 min**: hoy el smoke consume `example-bundle.json` (instancia certificada válida); el cambio a instancias reales de B es sustituir el bundle de entrada |
| Checkpoint 7 lado D (D4 mapa SVG + D5 r-vs-p)                                                                              | D · Studio                               | PENDIENTE dominio D — el lado C (C1–C3) está verde                                                                                                                              |

## Sesión Dominio B — datos y evidencia (worktree `planeado/datos`, 2026-07-24)

**Estado: B1 DONE (verde); B2–B4 en curso.** Opus valida / Sonnet implementa. El espejo de datos `reto1-vanilla` (que el prompt ubicaba en una ruta inexistente) fue clonado por Dylan en `/home/dylan/projects/blite/Hackathons/2026/Quantathon/reto1-vanilla` (solo lectura): 2 GeoJSON ICE (subestaciones = 70 nodos + líneas de transmisión), cr6/cr8 (`uniforme`/`voltaje`, ya en formato-corpus con digest interno), 19 corridas Nexus (`H2-1LE`/`H2-Emulator`, p1–p3, s0). **B1 (#74)** cerrado; provee el mecanismo para el corpus vivo de B2 (checkpoint 3). **Nota de entorno:** el worktree DEBE sincronizarse con `uv sync --all-extras` (como CI) — sin los extras falta `qiskit` y pyright/pytest fallan FALSAMENTE en `blite_cap_quantum/qaoa.py` (ajeno al dominio B); el subagente reportó gates desde un entorno degradado, revalidados verdes tras re-sync.

### Tabla de interacciones (regla NUEVA #3)

| Interfaz tocada                                                                                          | Dominio afectado                                  | Estado del contrato                                                                          |
| -------------------------------------------------------------------------------------------------------- | ------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| `blite.verification.provenance` (`ExternalSource`/`DerivationProvenance`/`DataQualityAssertion`)         | B (consumidor: B3 importa `DerivationProvenance`) | VERDE — implementado, seed en verde                                                          |
| `capabilities/ingesta` (`blite.ingesta.snapshot.fetch` · `.geojson.to_graph`)                            | B↔A (Registry/Dispatcher)                         | VERDE mecanismo; cableado `content_store`/`domain_id` lo fija el Dispatcher (Steven, Fase 1) |
| `CapabilityManifest` v2 (4 campos)                                                                       | A · ejecución (Steven)                            | DISCREPANCIA flaggeada — declarado v1; v2 pendiente (carril Dylan)                           |
| `claim_type: ingestion` (perfil STEM §1)                                                                 | confianza (Dylan)                                 | PROPUESTO — perfil congelado no editado, pendiente ratificación Dylan                        |
| Fixtures de contrato `ingesta/{snapshot,derivation}-example.json` + espejo Studio                        | B↔D (Zod mirror)                                  | VERDE — generados desde el modelo (origen único, #67)                                        |
| Política de aristas del ICE real (self-loops/tolerancia)                                                 | B (B2 define el dato ICE-70 sensato)              | RESUELTO en B2 (#75) — derivación semántica `endpoint-name-match`, cero self-loops           |
| `knowledge/islanding/corpus/{cr6,cr8}-{uniforme,voltaje}.json` (verbatim del espejo)                     | B · corpus (Sebas §1.9)                           | VERDE datos; **ratificación Sebas PENDIENTE** (no bloquea)                                   |
| `knowledge/islanding/corpus/ice-{uniforme,voltaje}.json` (derivación semántica vía capability real)      | B · corpus                                        | VERDE — 68 nodos conexos honestos, provenance embebida                                       |
| `blite.ingesta.geojson.to_graph` `edge_strategy` (extensión genérica, ADR-029)                           | B↔A (Registry/Dispatcher)                         | VERDE — genérico; default `nearest-neighbor` preserva B1                                     |
| `scripts/verify_corpus_digests.py` generalizado (freeze-8 + chimera-6, fail-loud)                        | B · guard (freeze §15.3)                          | VERDE — 14/14                                                                                |
| `knowledge/islanding/raw/ice-*.geojson` (snapshots committeados)                                         | B · reproducibilidad air-gap                      | VERDE — el espejo puede faltar                                                               |
| `blite.verification.external_evidence` (`NormalizedCounts`/`ExternalImportStatement`/`normalize_counts`) | B · confianza                                     | VERDE — seed en verde, conversor plano sin RuntimeDecoder                                    |
| `ConsensusReplicationPredicate.legs` + `ConsensusLeg` (aditivo §11)                                      | confianza (Dylan)                                 | VERDE — extensión pura, tests existentes intactos                                            |
| `●ExternalCertificateImported` / `external_certificate.imported` (payload)                               | confianza (Dylan)                                 | VERDE — forma de wire fijada; evento ya reservado §14                                        |
| Attestation de importación EMBEBIDA en `deliverables` (cero DSSE individual)                             | confianza (Dylan §7 T6)                           | VERDE Fase 1; DSSE individual = Fase 2 declarada                                             |
| `knowledge/nexus/` (19 statements + normalized + consensus + index)                                      | B · evidencia                                     | VERDE — determinista; `digest_coverage` honesto (§11)                                        |
| `bit_order` empírico msb-left (footgun endianness, `quantum/08` §1.5)                                    | B · ciencia (Sebas)                               | VERDE — verificado contra el corpus (G6 §5)                                                  |
| `results/extrapolation/` (artefacto honesto, barrera 26 qubits)                                          | B · entregable (§15.3)                            | VERDE — determinista, digest `e4eb94da`                                                      |
| `blite_cap_graphs.maxcut` `sdp_upper_bound` + fix coef SDP (0.25→0.5)                                    | **A · graphs (CROSS-DOMINIO)**                    | VERDE aditivo, assignment-preserving; **FLAG al dueño de graphs**                            |

## Integración 2026-07-25 — merge de `origin/planeado/base` (lados B/C/E) en `planeado/base`

> **Renumeración del ledger (obligada, no cosmética):** ambos lados avanzaron desde #68 **en
> paralelo** sobre el mismo ledger compartido, así que todo el rango #69+ colisionó. Se conserva
> la numeración **publicada** en `origin` (#69–#77: E · API, C · Informe, B · Datos) y se
> renumeran las decisiones locales que estaban sin push:
>
> | Antes (local) | Ahora   | Decisión                                                |
> | ------------- | ------- | ------------------------------------------------------- |
> | #69           | **#78** | Modelo de producto F2a (`docs/studio/product-model.md`) |
> | #69           | **#79** | D1 — honestidad de modo en el Studio                    |
> | #70           | **#80** | D2 — cablear `VITE_API_URL` en el build                 |
> | #71           | **#81** | A2 — adapter `ModelServer` tras `ModelPort`             |
> | #72           | **#82** | A5 — replay por digest + punto 8 del bundle             |
> | #73           | **#83** | Gates en worktree sin el gotcha de `uv sync`            |
> | #74           | **#84** | A3 — loop agéntico de 5 componentes                     |
> | #75           | **#85** | A4 — sub-runs (`sub_run_id` + cascada)                  |
> | #76           | **#86** | A6 — aprobación humana + verificación tripwire          |
>
> Se corrigió además un **`#69` duplicado** del lado local: el modelo de producto F2a y D1
> compartían número (dos sesiones distintas escribieron la misma fila). Ninguna otra ruta del
> repo referencia estos números (verificado por grep), así que el renumerado queda contenido aquí.

## Interacciones — sesión D1+D2 (checkpoint 1, 2026-07-24, rama `planeado/studio`)

Regla 3 de `05-plan-paralelo.md`: interfaz tocada → dominio afectado → estado del contrato.

| Interfaz / contrato tocado                                             | Dominio afectado                                   | Estado del contrato                                                                                                               |
| ---------------------------------------------------------------------- | -------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| `VITE_API_URL` (build ARG → env `isLiveMode()`)                        | D · Studio ↔ infra (compose/Dockerfile, §Geovanni) | Cableada same-origin vía nginx; cero cambio de código app                                                                         |
| `ReplayBanner` + `AppShellProps.banner` (slot nuevo)                   | D · Studio (interno)                               | Nuevo, aditivo, backward-compatible                                                                                               |
| Ramas live→vacío de las 6 queries `data/queries.ts`                    | D · Studio ↔ E · API (rutas E1)                    | Consumen el contrato "sin ruta aún"; D3 cablea el egress real cuando E1 exista (spec `endpoints-studio.md` YA en `planeado/base`) |
| `runEventsQueryOptions` (staleTime∞/sin refetch) + `useRunEventStream` | D · Studio (cache `['runs',id,'events']`)          | SSE = único escritor en vivo; carrera resuelta                                                                                    |
| Vista Red (`RedSlot`)                                                  | D · Studio ↔ D4 (mapa) / D3 (topología)            | En vivo: EmptyState pendiente; Replay: `GridSpike`                                                                                |
| `certificateQueryOptions`/`postRun` (ya live, sin cambio)              | D · Studio ↔ E · API                               | Cableados al contrato existente (`GET /runs/{id}/certificate`, `POST /runs`)                                                      |

> **Consecuencia honesta (por diseño):** con `runSummaries`→`[]` en vivo y sin `GET /runs`, abrir un run en vivo queda en Loading (el summary no resuelve). No es defecto: es el hueco que E1 llena — se cierra en el checkpoint 2 (E1+D3).
> **Nota de merge (RESUELTA 2026-07-25):** Fase 0 (`planeado/contratos`) se mergeó a `planeado/base` durante la sesión y ya tomó #66-#68; por eso estas se registraron como #69-#70. El conflicto anticipado ocurrió, y fue mayor de lo previsto: los lados B/C/E habían tomado #69-#77 en paralelo, así que estas dos quedaron **renumeradas a #79-#80** (y el modelo de producto F2a a #78). Ver la tabla de renumeración arriba.

## Sesión Fase 1 — Dominio A · Harness (worktree `planeado/harness`, 2026-07-24)

**Estado: CHECKPOINT 4 EN CIERRE.** A2 (ModelServer, commit `427b05f`) + A5 (replay por digest + punto 8, commit `ebd3e5d`) verdes en los 4 gates. Falta la demo de integración viva contra compose + el reporte a Dylan ANTES de A3/A4/A6 (orden mandado). Decisiones #81–#86 (registradas como #71–#76 en la rama). Nota de numeración: el salto a #71 no bastó — al integrar con `origin/planeado/base` los lados B/C/E ya habían consumido #69–#77 en paralelo, así que esta sesión quedó **renumerada a #81–#86** y la de Studio a #79–#80. Ver la tabla de renumeración arriba. Merge hecho el 2026-07-25.

### Tabla de interacciones (regla NUEVA #3)

| Interfaz tocada                                                                                                                                | Dominio afectado                             | Estado del contrato                                                                                                                                                                                                                                                                                                                                                                                  |
| ---------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ModelServer` (adapter) tras `ModelPort` + `ReplayManifest` (§15.7)                                                                            | frontera Dylan+Steven                        | IMPLEMENTADO (adapter); wiring a `loop.py` pendiente A3                                                                                                                                                                                                                                                                                                                                              |
| `replay.divergence` (`blite.runtime.replay`)                                                                                                   | E (SSE) + confianza (`check_bundle` punto 8) | IMPLEMENTADO (payload + punto 8); emisión desde el loop pendiente A3                                                                                                                                                                                                                                                                                                                                 |
| `check_bundle` 7→8 puntos                                                                                                                      | confianza (bundle/predicate)                 | IMPLEMENTADO — bundles limpios siguen 8/8                                                                                                                                                                                                                                                                                                                                                            |
| `plan.created`/`plan.item_updated` (`blite.runtime.plan`)                                                                                      | D (Studio timeline) + E (SSE)                | IMPLEMENTADO (A3, commit `de61d6e`) — emitido por el loop agéntico; wiring del proposer real a `ModelServer` pendiente (frontera Steven)                                                                                                                                                                                                                                                             |
| `approval.requested`/`approval.responded` (`blite.gateway.approval`)                                                                           | D (Studio card inline) + E (SSE)             | IMPLEMENTADO (A6, commit `547b841`, decisión #86) — payloads + `authorize_approval_response` fail-closed; wire-compat con seed superficie confirmada                                                                                                                                                                                                                                                 |
| Fixtures de contrato de costura (single-origin) `tests/fixtures/contract/harness/*.json` + espejo `apps/studio/src/fixtures/contract/harness/` | D (Studio — checkpoint 5)                    | IMPLEMENTADO (commit `d402e24`) — generador `scripts/gen-contract-fixtures-harness.py` desde los 5 modelos A2-A6; anti-drift byte-idéntico. **D6 ya puede espejar el Zod** contra estos JSON (coordinación por fixture, no por chat)                                                                                                                                                                 |
| `OverrideEvent`/`OverridePayload`/`override:apply:<scope>` (freeze §10)                                                                        | confianza/gateway (Dylan/Steven)             | **FRONTERA/HALLAZGO** — §10 es DOCTRINA, no existe como código (verificado por grep). A6 reusa la primitiva subyacente (`Identity.permissions`+`AuthzDecision`); cuando `OverridePayload` se materialice, el chequeo de A6 debe quedar textualmente idéntico. Definir además si el scope es jerárquico (A6 asume match exacto)                                                                       |
| Tripwire: `●SignalRecorded`/`●EscalationOpened`/`●Resolved` (§14) como eventos tipados                                                         | A/gateway/runtime (Steven)                   | PARCIAL — `Signal` y `escalation.opened` existen; falta el `GuardrailsStage` que journalice `signal.recorded` y el wiring de `escalation.resolved` (payloads los cierra Steven, ya declarado). A6 NO inventó catálogo                                                                                                                                                                                |
| `sub_run_id` en `ClaimEmittedPayload` + `blite.runtime.subrun`                                                                                 | confianza (predicate/bundle)                 | IMPLEMENTADO (A4, decisión #85) — spawn/aporte-al-raíz/cascada; wiring del proposer real a un spawn en vivo pendiente (frontera A6/uso en producción)                                                                                                                                                                                                                                                |
| `sub_run_provenance_hash` — fórmula del hash de sub-run                                                                                        | confianza (`blite.certificate`, Dylan)       | **FRONTERA A RECONCILIAR** — A4 usa prefijo `blite/sub-run-provenance/v1` (runtime-local, para NO acoplar runtime→certificate); NO es el `blite/provenance/v1` del cert. Si el cert raíz debe encadenar criptográficamente al `provenance_hash` del cert del sub-run, hay que reconciliar (constante compartida o re-estampado por la capa certificate). No bloquea A4 (gates verdes, capas limpias) |

## Sesión checkpoint 5 — costura A↔E↔D: misión → plan → hilo (rama `planeado/base`, 2026-07-29)

**Estado: CHECKPOINT 5 CERRADO en el plano de contrato + unit.** El 422 vivo del checkpoint 2
(flag de #90) está muerto por contrato. Commits: `e294a1e` (spec), `6511e47` (api modo misión),
`2a8140b` (studio misión-first + fixture), `86c3210` (D6 hilo), + este registro. Decisiones de
la sesión: #91–#93. Gates al cierre: 776 pytest (90.6% cov) · 13 contratos lint-imports ·
ruff 0 · pyright 0 · 207 tests studio (27 files) · eslint 0.

> **DoD de costura (regla NUEVA #2, declaración honesta):** la integración VIVA contra compose
> NO se corrió en esta sesión — los merges/smoke los coordina Dylan (mandato de la sesión); el
> lado E↔D queda cubierto por el fixture de contrato single-origin (opción prevista por el
> mandato: "el smoke contra compose si es viable, si no test de contrato con el fixture").

### Tabla de interacciones (regla NUEVA #3)

| Interfaz tocada                                                                                      | Dominio afectado                   | Estado del contrato                                                                                                                                                    |
| ---------------------------------------------------------------------------------------------------- | ---------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `POST /runs` gana body misión-first (`MissionRequest`, unión excluyente con claim-first #6 intacto)  | E · API ↔ D · Studio ↔ A · Harness | IMPLEMENTADO + spec (`endpoints-studio.md` §"POST /runs — modo misión", cross-ref `harness-agentico.md` §Contrato-2) — decisión #91                                    |
| Fixture `contract/endpoints/post-runs-mission.json` + generador + anti-drift x3                      | E ↔ D                              | VERDE — un solo origen (`MissionRequest`); `mutations.test.ts` compara literal; el API responde 202 al body EXACTO del fixture                                         |
| `toCreateRunBody` misión-first (`mutations.ts`, `CreateRunMissionBody` en `gatewayClient.ts`)        | D · Studio                         | VERDE — el 422 vivo del checkpoint 2 queda muerto por contrato                                                                                                         |
| `execute_run(proposer=...)` arrancado desde HTTP con proposer determinista                           | E ↔ A (frontera P4)                | PLACEHOLDER ETIQUETADO (decisión #92) — el agente real entra por el MISMO seam `Proposer`, cero cambio de contrato HTTP                                                |
| `plan.created`/`plan.item_updated` consumidos por el Studio (Zod espejo + listeners SSE + RunThread) | D ↔ A (`superficie-visual.md` §7)  | VERDE — espejo validado contra los fixtures `contract/harness/` que la sesión A dejó preparados                                                                        |
| `ProjectedEvent.payload?` + `toProjectedEvent` conserva el payload íntegro                           | D · Studio (interno)               | Aditivo, backward-compatible (nota 18 §5 / freeze §9)                                                                                                                  |
| Tab "Hilo" primera y default en `RunDetail` (slot `hilo` nuevo)                                      | D · Studio (D6, directriz #78)     | IMPLEMENTADO (decisión #93) — layout sobre eventos existentes, sin M1                                                                                                  |
| Orden de eventos en el camino de error del turno agéntico                                            | A · Harness (Steven)               | **FLAG** — `plan.item_updated {failed}` se apendea DESPUÉS de `run.failed` (`loop.py::_run_agentic_turn`); el test del API asevera presencia del terminal, no posición |

## Sesión auditoría Fase 2 — stack vivo (rama `planeado/base`, 2026-07-29)

**Estado: AUDITORÍA EJECUTADA.** Primera corrida REAL del stack compose completo
(postgres+api+studio, WSL2+Docker Desktop) con los 7 checkpoints verificados EN VIVO,
guion del demo ejecutado (óptimo AL3 verificado + falla sembrada refutada AL0 + bundle
8/8 offline), UI validada con Playwright. Cuatro fixes chicos (#95–#98, mandato "lo
chico arréglalo") + análisis para discusión (sin número, gobernanza #94). Gates al
cierre: 776 pytest (90.56%) · 13 contratos · ruff 0 · pyright 0 · 208 studio · eslint 0
· `SMOKE: PASS` con asserts nuevos.

### #95 — la imagen api instala el workspace completo (registry vivo dejaba de estar vacío)

- **Hallazgo (vivo)**: `uv sync --package chimera-api` dejaba la imagen SIN capabilities
  → `entry_points("blite.capabilities")` == `[]` en el contenedor → TODO run vivo
  (claim-first Y misión) moría en resolve con `run.failed {KeyError}`. El camino dorado
  POST /runs → verificación → certificado JAMÁS había corrido sobre compose (los smoke
  E2E usan TestClient + registry echo inyectado). Repro: run óptimo sintetica-4bus.
- **Decisión**: `uv sync --locked --all-packages --all-extras --no-dev` en
  `docker/api.Dockerfile` — restaura la intención escrita del propio Dockerfile
  ("workspace uv completo"), pineado por uv.lock. Tras el fix: óptimo `run.completed`
  con 2 patas + AL3, QAOA REAL (Aer 14q p=3) completado vivo, bundle 8/8 offline.
- **Alternativas evaluadas**: (a) capabilities como deps de chimera-api — ensucia la
  frontera de composición; (b) paquete `distributions/chimera` real como raíz de
  composición con extras curados — la opción correcta a mediano plazo, propuesta como
  ítem Mejorado (M14). Imagen queda 10.9GB (aceptable demo local, freeze §15.4).
- Colateral: `.dockerignore` no cubría `**/node_modules/` anidados ni `.claude/`
  (worktrees) — contexto de build ~25GB; corregido.

### #96 — el smoke deja de fingir un run (píldora envenenada en pgdata)

- **Hallazgo (vivo)**: `smoke_infra.sh` escribía `run.created` con payload mínimo;
  `project_runs` es fail-loud POR DOCTRINA (freeze §3) → `GET /runs` (E1) devolvía 500
  PARA SIEMPRE con ese stream en pgdata.
- **Decisión**: el smoke escribe `type="smoke.event"` (la proyección ignora tipos fuera
  del ciclo `run.*` por construcción; el SSE sirve cualquier evento) + asserts nuevos:
  registry no-vacío en el contenedor (paso 2.5) y `GET /runs` 200 sin listar el stream
  del smoke. Runbook `infra-verificacion.md` sincronizado. `SMOKE: PASS` verificado.

### #97 — el cliente escucha el vocabulario completo del stream

- **Hallazgo (vivo)**: en live TODO llega por SSE (`loadRunEvents` → `[]`) y
  `KNOWN_RUN_EVENT_TYPES` no incluía `run.created`, `run.step.*` ni
  `capability.job.failed` → el timeline mostraba 2 de 5 eventos de un run fallido
  (header: "5 eventos") mientras la demo narra "cero eventos perdidos".
- **Decisión**: listeners para el vocabulario completo que `execute_run` emite +
  `replay.divergence` (A5). Aditivo, cero cambio de contrato. TDD RED→GREEN en
  `gatewayClient.test.ts`; verificado en navegador (8/8 eventos renderizados).

### #98 — la vista Verificación acepta el bundle real + nginx no cachea index

- **Hallazgo (vivo)**: `loadCertificate` parseaba la respuesta de `GET /certificate`
  como envelope DSSE pelado; el api devuelve el BUNDLE completo `{envelope, public_key,
stream, …}` → la vista Verificación explotaba en Zod con TODO certificado vivo, y la
  descarga habría bajado solo el envelope (insuficiente para `verify-bundle.py`).
  Además nginx servía `index.html` sin `Cache-Control` → tras un redeploy el navegador
  retenía el bundle JS viejo (reproducido).
- **Decisión**: `certificateBundleWireSchema` (loose: solo tipa `envelope`, el resto
  pasa íntegro para descarga/verify offline) + `wire` = bundle entero; nginx gana
  `no-cache` para index.html e `immutable` para `/assets/`. TDD RED→GREEN; vista AL3
  verificada en vivo tras el fix.

### Análisis para discusión con Dylan (SIN decidir — gobernanza #94)

1. **Misión muere `KeyError`, no `exhausted` (doc #92 ↔ vivo)**: el proposer placeholder
   propone `{mission, instance_id}` como inputs de `blite.solvers.qubo` (ValueError:
   matrix requerida) y el Studio mapea proposers a `blite.solvers.qaoa|goemans_williamson|greedy`
   — IDs que NO existen como entry points (reales: `blite.quantum.qaoa`,
   `blite.graphs.maxcut`…) → KeyError turno 1. Los unit tests usan `cap.mission-echo`
   tolerante (mundo más amable que el vivo). El hilo D6 muestra el cierre honesto en
   todos los casos (verificado vivo). Opciones: (a) alinear `PROPOSER_CAPABILITY` con
   IDs reales + inputs válidos por capability (tabla instancia→matrix desde el corpus);
   (b) capability hermética `blite.mission.noop` para el placeholder; (c) aceptar el
   cierre KeyError y corregir #92/spec.
2. **`plan.item_updated {failed}` post-terminal (débil b, flag #91)**: repro in-memory
   Y vivo (seq 39 `run.failed` → seq 40 `plan.item_updated{failed}`). El store lo
   ACEPTA (familias rechazadas = solo `run.step.*`/`capability.job.*`) y queda FUERA
   del corte del provenance_hash. Fix natural: `_run_resolve_and_invoke` deja de
   journalizar `run.failed` y lo devuelve al caller (`_run_agentic_turn` emite el
   update ANTES del terminal; `_execute_single_turn` conserva su orden). Toca la
   costura compartida pipeline-fijo/loop — se discute antes de tocar.
3. **`status` wire sin estado fallido**: la spec (endpoints-studio §Zod) fija
   `enum(en_curso|completado)` → un run fallido queda "en curso" PARA SIEMPRE en la
   lista (verificado vivo + screenshot). Propuesta: extensión aditiva
   `fallido|cancelado` en wire+client+spec+fixture — toca contrato Fase 0.
4. **Proyección fail-loud vs lista entera**: ¿debe UNA fila envenenada tumbar TODO
   `GET /runs` (500)? Opciones: mantener doctrina (señal fuerte) vs skip honesto
   por-stream con `discarded_streams` en la respuesta. Toca freeze §3.
5. **Productores vivos ausentes para lo visual**: `run.metrics.recorded` (ablación),
   partición en `verification.completed` (badges del mapa), `GET /rvsp` — sin productor
   en el harness; Studio muestra honest-empty. El payoff visual de Actos 2-3 hoy solo
   existe en modo Replay etiquetado. (El tab Red vivo además dice "llega con D3/D4",
   copy caduco — D3/D4 ya mergearon; lo que falta es el productor.)
6. **Sesión agéntica real grabada NO existe** (A5 dejó maquinaria verde: 22 tests
   ModelServer/replay; sin artefacto de sesión ni wiring proposer→ModelServer, frontera
   P4) → el Acto 1 del guion (replay de sesión real) no es ejecutable hoy.
7. **Menores**: cliente reintenta certificate 409 como error (3 fetches + consola);
   `verify-bundle.py` NO es standalone (necesita el venv — el guion dice "terminal
   limpia"); guion dice "7/7" y el verificador ya es 8/8 (punto de replay A5); import
   Nexus re-ejecutado no es byte-idéntico (formato prettier vs json.dumps — digests
   canónicos intactos); certificado no sobrevive restart del api (`run_tickets`/
   ContentStore in-memory, #13/#14 — límite operativo de demo conocido).

### Tabla de interacciones (regla NUEVA #3)

| Interfaz tocada                                    | Dominio afectado              | Estado del contrato                                                            |
| -------------------------------------------------- | ----------------------------- | ------------------------------------------------------------------------------ |
| `docker/api.Dockerfile` (composición de la imagen) | infra ↔ TODOS (registry vivo) | FIX #95 — smoke paso 2.5 como gate ejecutable                                  |
| `scripts/smoke_infra.sh` (`smoke.event` + asserts) | infra ↔ E (`GET /runs`)       | FIX #96 — runbook sincronizado                                                 |
| `KNOWN_RUN_EVENT_TYPES` (`gatewayClient.ts`)       | D ↔ E (SSE)                   | FIX #97 — aditivo, espejo del vocabulario ya emitido                           |
| `certificateBundleWireSchema` + `loadCertificate`  | D ↔ E (`GET /certificate`)    | FIX #98 — el cliente espeja el bundle real; spec sin cambio (el api no cambió) |
| `docker/studio-nginx.conf` (cache headers)         | infra ↔ D                     | FIX #98 — index no-cache, assets immutable                                     |
| Orden post-terminal de `plan.item_updated`         | A ↔ confianza                 | FLAG CONFIRMADO VIVO — análisis en discusión punto 2                           |
| `status` wire de `RunSummary`                      | E ↔ D ↔ spec Fase 0           | DRIFT DE PRODUCTO — análisis en discusión punto 3                              |

### #99 — pulido UI post-auditoría (directrices de Dylan, 2026-07-29)

Sesión corta sobre la base auditada, con Dylan dictando las directrices en vivo
(gobernanza #94: decisión discutida y tomada juntos). Implementado (TDD, gates
210 studio + 18 assurance-ui + eslint + tsc):

1. **Glifo de confianza simplificado** — supersede la variante de 5 barras de
   DESIGN.md §4: TRES barras / CUATRO estados (nula=AL0 sin barra coloreada,
   poca=AL1 baja, media=AL2 intermedia, alta=AL3/AL4 la más alta), color del
   veredicto; el AL exacto sigue en la etiqueta accesible
   (`confianza media (AL2 de AL4)`) y en el texto mono — el glifo simplifica,
   el dato no.
2. **Navegabilidad**: breadcrumb del topbar deja de ser decorador (tramos
   previos = botones, `onBreadcrumbNavigate`) + botón "Volver a runs" en el
   detalle del run.
3. **Tabla de runs**: `whitespace-nowrap` en ID/actor/fecha. **ROLLBACK del
   recorte de `run-`** (misma sesión, corrección de Dylan): la instrucción era
   condicional — recortar SOLO si el prefijo era decorador del frontend; se
   verificó que `run-` SÍ es parte del ID real (`runs.py: run-{uuid4().hex}`,
   así viaja en DB/streams), así que la celda muestra el ID COMPLETO (con
   `hover:underline` como affordance de click).
4. **Sidebar**: pill del proyecto sin la palabra "proyecto" (redundante),
   iconos lucide en los ítems, aire en potencias de 2 (px-4/py-8/gap-1/p-2).
5. **Aire general**: SectionHeader (mt-2 título→descripción, mb-8 al
   contenido), RunDetail (header+meta gap-2, gap-8 hacia tabs) — regla: gaps/
   margins/paddings en potencias de 2 (2/4/8/16/32/64px); tablas y topbar se
   dejaron como estaban (directriz explícita).
6. **Cursores** (addendum, misma sesión): regla base en `index.css` — el
   preflight de Tailwind v4 deja `cursor: default` en botones; todo botón/
   control habilitado (`button`, `[role=button|tab]`, `a[href]`) recupera
   `cursor: pointer`, + `hover:underline` en el ID de la tabla como
   affordance de click.

**Mapeado a Mejorado** (04-consolidacion §4): M15 sidebar completo
(user/organization, multi-proyecto, colapsable), M16 branding/logo (brief
destilado de las referencias de Dylan: marca geométrica mínima, línea
topológica/nodos, mono + acento teal), M17 URLs reales + go-back en el resto
de secciones. M14 (distribution root) ya venía de #95.

## Sesión cierre de Planeado — "Fable valida, Sonnet hace" (rama `planeado/base`, 2026-07-29/30)

**Estado: PLANEADO CERRADO en lo ejecutable.** Cuatro carriles delegados a agentes
Sonnet (TDD, sin commits — el validador commiteó) + auditoría final en vivo. Gates al
cierre: **804 pytest (90.96%) · 13 contratos · ruff 0 · pyright 0 · 221 studio ·
eslint 0 · tsc 0**. Commits: `bef0ad3` (orden post-terminal), `fb9f494` (misión
instancia→inputs reales + guard anti-traversal), `cfc69b4` (proposer real vía
ModelServer), `feec573` (status fallido/cancelado + menores).

### #100 — cierre ejecutado, con evidencia viva (stack compose reconstruido)

1. **Orden post-terminal RESUELTO** (flag #91): `_run_resolve_and_invoke` devuelve el
   error y cada caller journaliza su terminal — `plan.item_updated {failed}` entra
   ANTES de `run.failed` (dentro del corte del provenance_hash); pipeline fijo intacto.
2. **La misión viva PROGRESA** (cierra "Análisis para discusión" punto 1, opción a):
   POST misión `cr6-uniforme` en compose → 3 turnos reales (QUBO real, 3×
   `capability.job.completed`) → cierre `run.failed {exhausted}` como ÚLTIMO evento.
   `PROPOSER_CAPABILITY` en IDs reales; guard anti path-traversal en `instance_id`.
3. **Proposer real cableado por el seam** (#92 → P4): adapter Proposer←ModelServer en
   el api (`model_proposer.py`, protocolo JSON estricto = `ProposedStep`), sesiones
   grabadas content-addressed (`model_session.py`, `SessionCorruptError` fail-loud),
   flip `CHIMERA_MODEL_BACKEND=replay|record|live` (ausente ⇒ placeholder intacto),
   `scripts/record_session.py` para grabar la sesión REAL (pendiente: correrlo con la
   key de Dylan — cero llamadas LLM en esta sesión). Frontera anotada para Steven:
   envolver la llamada al proposer en `loop.py` (hoy el adapter degrada fallas a un
   ProposedStep centinela → run.failed{KeyError}, contrato de capability desconocida).
4. **Status wire `fallido|cancelado`** (cierra punto 3): extensión aditiva en spec +
   server + client espejo; verificado vivo — los 4 runs fallidos del store muestran
   `fallido` (muere el "en curso" eterno), 3 completados intactos.
5. **Menores**: 409 de certificate sin retry (4xx corta), copy honesto del tab Red,
   guion actualizado a 8/8.

### Fuera del cierre — bloqueado por DEFINICIÓN, no por código (pasa a Mejorado)

- **Partición sobre el mapa** (M18 propuesto): falta una convención VERSIONADA de
  branch-ids — el modelo eléctrico (4bus/ieee14/ICE-70) solo tiene pares (from,to);
  la #88 ya lo había diferido. Tres campos de 4 del payload son derivables hoy.
- **Ablación `run.metrics.recorded`** (M19 propuesto): ninguna spec define productor,
  campos científicos ni el pipeline de dos brazos (quantum/classical).
- **`GET /rvsp`** (M20 propuesto): `results/extrapolation/extrapolation.json` tiene
  r_greedy/r_gw/ratio_best/ratio_mean REALES de las 5 instancias Nexus, pero
  `rEsperadoMean` (⟨C⟩ exacto, campo obligatorio del schema D5) no existe para ellas —
  llenarlo = simulación clásica nueva (ciencia, no plomería).
- **Grabar la sesión agéntica real** (bloquea el replay de escena del Acto 1): un
  comando de Dylan con su key (`scripts/record_session.py`), luego
  `CHIMERA_MODEL_BACKEND=replay` en compose (comentado, listo).

### Tabla de interacciones (regla NUEVA #3)

| Interfaz tocada                                                               | Dominio afectado    | Estado del contrato                                                        |
| ----------------------------------------------------------------------------- | ------------------- | -------------------------------------------------------------------------- |
| Orden de eventos del turno agéntico (`loop.py`)                               | A ↔ confianza       | RESUELTO — terminal siempre último; provenance cubre el plan               |
| Misión instancia→inputs (`runs.py` + `mutations.ts` + fixture)                | E ↔ D ↔ corpus      | VERDE VIVO — spec §misión actualizada aditiva                              |
| Proposer←ModelServer (`model_proposer.py` + protocolo en harness-agentico.md) | E ↔ A ↔ protocols   | IMPLEMENTADO — flip por env, default placeholder; frontera loop.py anotada |
| `status` wire `RunSummary` (spec + reads.py + client)                         | E ↔ D ↔ spec Fase 0 | EXTENSIÓN ADITIVA VERDE VIVO                                               |
| `compose.yaml` env api (`CHIMERA_MODEL_BACKEND`)                              | infra ↔ E           | DOCUMENTADO comentado — se activa al existir la sesión grabada             |

## Sesión control Mejorado — Etapa 0 · criterio (rama `planeado/base`, 2026-07-29)

**Precondición verificada antes de abrir la fase**: la auditoría Fase 2 de Planeado SÍ
corrió (#95–#98) y el cierre #100 resolvió sus puntos 1–3; quedan como insumo de
Mejorado los M18–M20 propuestos, el punto 4 del análisis (proyección fail-loud vs
`discarded_streams`, SIN decidir) y la sesión agéntica real sin grabar.

### #101 — criterio de Mejorado (Etapa 0 con Dylan)

- **Mandato**: Chimera pasa de demo a PRODUCTO; norte = generalidad (resolver más que
  el Reto 1) + producto usable (listo para terceros) + confianza (el diferenciador).
- **La pregunta** (ordena, NO filtra — todo lo mapeado se implementa, mandato
  explícito): «¿acerca esto a que un tercero resuelva con Chimera un problema que NO
  es el nuestro, sin nosotros al lado y sin perder la confianza verificable?».
- **Autoridades**: 1) los retos 2/3 (generalidad; KB2-02 — reto 2 kernel agua, reto 3
  TFIM/Trotter), 2) un externo sin contexto (usabilidad), 3) el freeze/certificado
  (confianza).
- **Cierre de fase = tres llaves conjuntivas**: retos 1–3 punta a punta en la
  plataforma + lista para terceros + backlog M1–M20+ completo sin descartes.
- **Flip OSS sin fecha** (el ancla ~1-ago quedó liberada); **sesión agéntica real al
  backlog** (bloqueado-por-Dylan: requiere su key).
- **Fase siguiente parqueada** (NO entra a Mejorado): 3 ideas ganadoras corriendo en
  la plataforma, retos vs resultado de hackathon, research de competencia.
- Doc: `docs/mejorado/01-criterio.md`. Docs-only: ninguna interfaz de código tocada.

## Sesión control Mejorado — Etapas 1-3 · cobertura + research + consolidación (rama `planeado/base`, 2026-07-30)

Gates baseline verificados VIVOS al abrir la fase (no de fe): 804 pytest (90.96%) ·
13 contratos lint-imports · ruff 0 · pyright 0 · 221 studio · eslint 0. Etapas 1-2 en
paralelo (5 exploraciones de cobertura + 3 frentes de research con web) →
`docs/mejorado/02-cobertura.md` y `03-research.md`. Etapa 3 con Dylan →
`docs/mejorado/04-consolidacion.md` (backlog operativo G/P/C/V/O + ítems M21-M32).

### #102 — supersede [MEJORADO] del freeze §13

El freeze §13 gana supersede explícito con causa: el loop agéntico (ceremonia #66,
`harness-agentico.md`) reemplaza la letra «pipeline fijo Fase 1» + set hardcodeado;
el catálogo §14 gana los eventos de #68. El freeze sigue siendo LA autoridad única.
Cierra el conflicto C-1 de `02-cobertura.md` §5 (la regla del índice de specs estaba
siendo violada). Ejecución: ola 0.

### #103 — M3 por la ruta formal_exact + proof

`RuleBackend` se diseña con salida de certificado de prueba (cvc5→Alethe→checker
Carcara empaquetado en el bundle: AL4 verificable offline, freeze §4-iii literal); la
v1 con Z3 emite `property_rule` AL2 honesto con `rlimit` (jamás timeout wall-clock —
determinismo del replay). Cero techos rotos. trust/11 se traduce a clase+AL (muere
`rung`). Cierra C-2.

### #104 — skip honesto en GET /runs (supersede parcial de la letra de lectura §3)

La ruta de LECTURA descarta streams envenenados y expone `discarded_streams`
(extensión aditiva del wire E↔D + Zod + fixture + test con la píldora #96). Línea
roja: escritura/certificados/provenance siguen fail-loud («explota, no rellena»
intacto donde importa). Cierra el punto 4 de la auditoría Fase 2. Cierra C-3.

### #105 — Rekor re-entra como pieza 5 de M8

Supersede del descarte ×2 (freeze §7 / 03-research Planeado): el fundamento era la
emisión keyless con Fulcio; Rekor v2 GA con backend POSIX + stapled inclusion proof
mantiene la verificación 100% offline. Orden incremental de M8 fijado: hash-chain →
DSSE/VSA → StatusList → OpenBao → Rekor witness opcional. SPIFFE queda FUERA de M8
(gate = despliegue multi-nodo, no fase). Cierra C-7.

### #106 — bloque de resoluciones C-4…C-15 + orden global ratificados

Las 11 resoluciones de `04-consolidacion.md` §3 quedan decididas tal como están
escritas (C-4 payload de métricas extendido + dos brazos como sub-runs; C-5
GatewayContext aditivo + un cruce por invocación; C-6 verify_all() +
independence_group compartido por corrida; C-8 branch-ids híbrida; C-9 rvsp por run;
C-10 estampar -voltaje@v1; C-11 proyector standalone; C-12 manifest envolvente MCP;
C-13 dualidad de digests; C-14 EXACT_DIAGONALIZATION + tolerancia; C-15 baselines
coordinado). Orden entre dominios confirmado: G → P → C (manifest-v2 adelantado) →
V → O, con ola 0 documental inmediata. Ajustes posteriores = supersede individual.

Sin interfaces de código tocadas en estas etapas (docs-only); la tabla de
interacciones nace con la ola 0 y las sesiones de Fase 1.

## Sesión control Mejorado — saneamiento como precondición (rama `mejorado/base`, 2026-07-30)

### #107 — saneamiento documental y de cimientos ANTES de la Fase 0

- **Mandato de Dylan** (2026-07-30): ordenar, podar y ajustar la KB y la
  documentación antes de seguir — mucha información atada a features específicos
  (plano de confianza) y a UN problema (reto 1); la rigidez documental degrada
  mantenibilidad y escalabilidad.
- **Validación de la sesión de control**: CIERTO, con precisión — 8 evidencias del
  propio ciclo de planning (`06-saneamiento.md` §1: 15 conflictos C-1..C-15,
  freeze §13 describiendo un sistema que no existe, vocabulario muerto en specs
  implementables, nombres nunca reconciliados, fugas reto-1 en capas de borde,
  contradicciones internas congeladas, índices rotos, arqueología multi-doc como
  costo fijo). Los cimientos ARQUITECTÓNICOS no son el blocker (el research los
  validó; los 15 conflictos se resolvieron aditivos) — el blocker es la capa
  documental + los cimientos de proceso de la era hackathon.
- **Efecto**: la Fase 0 de contratos queda BLOQUEADA hasta que S4 cierre; la ola 0
  del plan paralelo se funde en S3. Plan S1 (censo) → S2 (diseño del orden con
  Dylan, decisiones #108+) → S3 (ejecución) → S4 (validación con checklist).
- **Línea roja**: contratos congelados solo por ceremonia; jamás re-digestar nada
  estampado; ledger solo-anexar; los refactors de código reto-1 se quedan en el
  backlog G/P/C/V/O (no se hacen dos veces).
- Docs: `docs/mejorado/06-saneamiento.md` (plan + prompts S1/S3); salida S1 será
  `07-censo-documental.md`. Docs-only: ninguna interfaz de código tocada.

## Sesión S2 — diseño del orden del saneamiento (rama `mejorado/base`, 2026-07-30)

Insumo: `docs/mejorado/07-censo-documental.md` (censo S1 @ `9733f2b`, con las tres
extensiones de mandato: terminología era-hackathon, research huérfana, validación
de diseño). Método: opciones analizadas + AskUserQuestion con Dylan, 3 rondas.
Las decisiones (h)/(i)/(j) responden a la agenda extendida commiteada en
`f54a051`.

### #108 — jerarquía de autoridad documental ÚNICA (con desempates)

Cadena: constitución (`invariants` + `base-logica-formal` + `contract-freeze` +
anexo) → specs de costura → docs de fase → knowledge = INSUMO, jamás autoridad →
archivo. MÁS los 4 desempates que el censo exigió (07-censo §5): (1) el freeze
manda y `spec-confianza-v3-2` es su vocabulario DELEGADO — la regla se escribe;
(2) mapa sección→doc único para las 3 arquitecturas en `docs/README.md`; (3)
trust/10-12 se reconocen como «diseño interno citado por código» con nota de
rango (promoción a spec = Fase 0 si hace falta); (4) `planeado/03-research` se
anuncia como co-autoridad de las specs de costura. El ledger figura en el índice
como autoridad global VIGENTE. Reversión: supersede con causa.

### #109 — política de estados obligatoria en header

TODO doc de `docs/` y `knowledge/` lleva `Estado: {VIGENTE | VIGENTE-CON-DRIFT
(+nota) | SUPERSEDIDO-POR-<x> | HISTÓRICO} (fecha)`. Reglas: el supersede marca
al doc VIEJO, no solo al ledger; los sellos de verificación llevan
fecha-de-validez y se corrigen con nota fechada nueva (jamás borrando el sello
erróneo — caso `islanding/01` §1.8); `docs/README.md` refleja el estado de cada
doc.

### #110 — destino del freeze: mono-doc + supersedes + índice-mapa

Opción (a)+(c) de `06-saneamiento.md` §5: el freeze queda ÚNICO; S3 aplica los 8
frentes de supersede con decisión registrada (07-censo §1.7-B) con marcas
`[MEJORADO]` + causa; se crea un índice-mapa por plano que apunta a las secciones
(cero referencias `freeze §N` rotas). La modularización (b) queda descartada CON
causa: re-escribir la constitución a mitad de fase multiplica el drift y rompe
cientos de refs, incluidas las de docstrings del engine.

### #111 — el ledger se MUEVE a `docs/decisiones.md`

`git mv docs/mvp/decisiones.md docs/decisiones.md` (la historia se conserva) +
encabezado nuevo que lo declara «Registro GLOBAL de decisiones
(MVP→Planeado→Mejorado→…), solo-anexar, autoridad vigente». S3 actualiza las ~54
referencias repo-wide (docs, docstrings, compose, scripts) — ese barrido de
docstrings queda amparado por #115. El CONTENIDO sigue intocable (línea roja).
Nota de la sesión: la alternativa quedarse-en-sitio era más barata; Dylan eligió
la ubicación honesta — el costo de refs se paga una vez y coincide con el barrido
quirúrgico ya aprobado.

### #112 — cimientos de proceso muertos: archivar con marca + rescates ANTES

Los históricos van por `git mv` a la carpeta de archivo que S3 proponga (header
HISTÓRICO; jamás rm): ratificaciones/ ×5, decisiones-delegadas,
guia-ratificacion, demo-dia-d, contratos TS v1, esquema v1, mockup HTML,
planeado/{01,02,04,05}, research de proceso ×4. PRECONDICIÓN: ejecutar los 4
rescates de 07-censo §6 (registro ADR-001-027 de arc42 §12 → `docs/adr/`; tabla
invariante→componente de arc42 §6; pesos QUBO de reconciliada §4 →
`islanding/01`; concepto `local: boolean` de contratos-v1 §7 → nota).
`CODEOWNERS` y `GOVERNANCE.md` se REESCRIBEN alineados a #94 (config activa, no
histórico); `promote-demo.yml` sale de CI (queda en historia git).

### #113 — el vendorizado quantathon SE QUEDA como insumo de trabajo próximo

Decisión de Dylan (corrige la recomendación de desvendorizar): el árbol
`knowledge/quantum/quantathon/` es el material completo dado durante la
hackathon; el plan es REFINARLO y dárselo al modelo o meterlo al harness
(conecta directo con el huérfano #7 del censo: ingesta RAG/KB con procedencia —
ver #116). Efectos para S3: se excluye del gate de docs
(`.markdownlintignore`/`.prettierignore` — resuelve N6 sin borrar nada), gana
marca de VENDORIZADO-AJENO + «insumo de trabajo próximo» en `quantum/README` e
`INDEX`, y la licencia/atribución de terceros (N11) queda EXPLÍCITAMENTE
pendiente en O2/M26 ANTES del flip OSS. Reversión: si el refinamiento no llega,
se re-litiga la desvendorización con este registro como causa.

### #114 — idioma: migración PROGRESIVA a inglés, carril propio post-S4

El corpus completo converge a inglés. Faseo (g2): S3 solo escribe la REGLA en
`docs/README.md` («el corpus converge a inglés; los docs nuevos nacen en
inglés»); la traducción del corpus existente es un carril propio DESPUÉS de S4,
por oleadas empezando por lo normativo (freeze+specs juntos, gates y refs
verificadas por oleada) — el saneamiento no se contamina de traducción y la
línea roja del freeze se respeta (traducción = cambio con ceremonia propia por
oleada).

### #115 — S3 gana alcance quirúrgico de docstrings/comentarios

El hueco S3↔código del censo (§8.5) se cierra DENTRO de S3: traducción de
vocabulario muerto y terminología de evento en los ~40 archivos de código (diff
solo-comentarios, cero efecto en runtime ni contratos — los gates verdes lo
prueban: 804 pytest / 13 contratos / 221 studio). Intocables: los vectores de
hash congelados (`"rung": 1` en `test_canonical` y
`gen-canonicalization-vectors`, declarados dato arbitrario por el anexo §163) y
el ledger. Coherente con #111: un solo barrido de comentarios, no dos.

### #116 — TOP-10 de research huérfana: los 10 entran al backlog

Coherente con #101 («la pregunta ORDENA, no filtra»). S3 los anexa a
`04-consolidacion.md` con dominio y orden: corpus-runner/eval + KPI over-refusal

- tres-planos → O temprano; corrector AI-QEM → V; protocolo de convergencia
  simulada↔real como herramienta → O; registro de guardrail-adapters + pick HHEM →
  C; `JobQueue`/Procrastinate → P (amplía P5); Cedar Analysis + bundle OPA → C;
  ingesta RAG/KB con procedencia → P/O (adelantado por #113); REGRID M.3/M.4 +
  feasibility-feedback → G; puerto `ExecutionHarness` + guarda PASS_TO_PASS → C;
  SEPs white-box → KB + O tardío. Las menciones honoríficas de 07-censo §7.1
  quedan como KB curada. Todo descarte futuro = CON causa registrada (dejan de
  existir los huérfanos sin registro).

### #117 — los 4 hallazgos de diseño entran como ítems

S3 los anexa al backlog: (1) registry de lentes de dominio del Studio (la letra
ya existe en `product-model.md` §38-45) → dominio P; (2) gate de agnosticismo
multi-capa (engine/api/studio con excepciones declaradas) → dominio O TEMPRANO —
es el ítem que hace irreversibles los demás; (3) evaluador de policy completo en
`bundle_check` (`min_level` + `side_effects`; aditivo + ceremonia porque cambia
el veredicto de bundles estampados) → dominio C; (4) guards de datos estampados
(corpus a CI + guard nuevo para `knowledge/nexus/`) → dominio O.

Docs-only: ninguna interfaz de código tocada en esta sesión. Siguiente: sesión
S3 (prompt `06-saneamiento.md` §4.2) con 07-censo §9 + #108-#117 como insumos
obligatorios; luego S4 valida contra el checklist §6 y desbloquea la Fase 0.

### #118 — saneamiento ≠ resultado final: dos horizontes (aclaración de mandato)

- **Aclaración de Dylan** (2026-07-30, post-S2): una cosa es el saneamiento y
  otra el resultado deseado. **Saneamiento** = preparar el camino: borrar
  archivos basura (archivándolos), agregar tags temporales de estado,
  identificar dónde hay valor y dónde no, actualizar terminologías, y que la
  documentación y el knowledge REFLEJEN el resultado real del proyecto. **El
  resultado final** (toda la documentación ordenada, sin parches, estructura
  ideal, traducida al inglés) es un REFACTORING INTEGRAL propio que se hace AL
  COMPLETAR la fase Mejorado — no antes.
- **Supersede parcial de #111** (con esta causa): el `git mv` del ledger a
  `docs/decisiones.md` + el barrido de ~54 referencias se DIFIERE al refactoring
  final. En S3 el ledger solo gana el encabezado que lo declara registro GLOBAL
  vigente y la presentación correcta en `docs/README.md`, en su ubicación
  actual — cero referencias rotas mientras tanto. La decisión de moverlo sigue
  en pie; cambia el CUÁNDO.
- **Supersede parcial de #114** (con esta causa): la traducción a inglés es
  parte del resultado final — el carril de traducción se ancla AL COMPLETAR
  Mejorado, no post-S4. S3 solo escribe la regla en `docs/README.md` («el
  corpus converge a inglés en el refactoring final; las superficies públicas ya
  en inglés se mantienen en inglés»). Los docs de trabajo de fase siguen en
  español hasta ese refactoring.
- **Ratificados como saneamiento** (sin cambio): #109 tags de estado, #110
  marcas de supersede en el freeze + índice-mapa, #112 archivar la basura con
  los rescates antes, #113 marcar/excluir el vendorizado, #115 actualización
  quirúrgica de terminologías en docstrings, #116/#117 registro de valor
  (research + hallazgos al backlog). Las marcas de S3 son deliberadamente
  TEMPORALES: son el mapa del refactoring final, no parches permanentes.
- **Registro del hito**: el refactoring documental final entra a la lista de
  parqueados de `01-criterio.md` §Fuera-de-la-fase como trabajo de cierre
  post-Mejorado. Reversión: supersede con causa.

## Sesión S3 — saneamiento documental EJECUTADO (worktree `mejorado/saneamiento`, 2026-07-30)

Insumos obligatorios consumidos: `06-saneamiento.md` (plan + línea roja),
`07-censo-documental.md` (censo S1) y las decisiones #108–#118 (diseño S2).
Horizonte #118 respetado: marcas TEMPORALES, cero traducción a inglés (solo la
regla en `docs/README.md`), ledger EN SU UBICACIÓN con encabezado global, cero
reorganización más allá del archivo de lo decidido. Siete commits, uno por
bloque del alcance: `0493c5c` (b1 estados #109, 53 archivos) · `a99ff95` (b2
rescates #112 + 19 archivos a `docs/archivo/` + `docs/README.md` mapa de
autoridad #108/#110) · `8d1ef01` (b3 supersedes del freeze #102/#104/#105/#106
más C-9/C-10/N12, checklist 7→8 y nota manifest v2 §1) · `8773167` (b4
traducciones a clase+AL #103: trust/11 completa, stub TFIM
`knowledge/quantum/11`, DESIGN.md §4 3-barras, READMEs honestos) · `04ee723`
(b5 higiene: `.markdownlintignore`/`.prettierignore` #113, CI `mejorado/**`,
`promote-demo.yml` fuera, CODEOWNERS/GOVERNANCE per #94, `.env.example` con
`CHIMERA_MODEL_*` y sin `OLLAMA_API_KEY`) · `88d012e` (b6: §7 de
`04-consolidacion.md` con los 14 ítems #116/#117 — O8-O12/V9/C12-C15/P11-P13/G8
— + barrido #115 solo-comentarios en 65 archivos).

**Gates (verificación, no fe — batería completa ANTES de cada commit; final
sobre el árbol completo):** pytest **799 passed + 5 xpassed (= 804), 14
skipped, cov 90.92%** · lint-imports **13 kept / 0 broken** · ruff **0** ·
pyright **0** · studio **221/221** · eslint **0** · **gate de docs verde SOBRE
TODO EL REPO**: `pnpm run docs:lint` = 0 errores y `prettier --check .` = limpio
(baseline pre-S3: 671+ errores por el vendorizado). Sin regresión respecto del
baseline #108 (804/90.9x/13/221 — la centésima de cobertura varía por entorno
de worktree, no por código).

### Tabla de interacciones de la sesión

| Frente            | Qué se hizo                                                                                                                                                                     | Interacción / nota                                                                                                                                                                   |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Estados #109      | Header de estado en TODO doc vivo de `docs/` y `knowledge/`; sello falso de `islanding/01` §1.8 declarado ERRÓNEO con nota fechada (sin borrarlo)                               | los V-D llevan el delta con refs; los archivados llevan HISTÓRICO + destino                                                                                                          |
| Archivo #112      | 19 archivos a `docs/archivo/` con `git mv` (ratificaciones ×5, decisiones-delegadas, guía, contratos v1, esquema v1, mockup, planeado 01/02/04/05, research de proceso ×4)      | 4 rescates ANTES: registro ADR-001-027 + tabla invariante→componente → `docs/adr/registro-adr-historico.md`; QUBO §4 → `islanding/01` §6; `local: boolean` → nota en el registro ADR |
| Freeze            | Marcas [MEJORADO] con causa en §1/§3/§7/§8/§13/§14/§15.3/§15.7; C-10 estampó los 6 digests reales (cr6/cr8/ice × uniforme/voltaje) con nota de procedencia                      | letra congelada intacta; ieee30 + flips cr6/cr8 siguen en O6/M30                                                                                                                     |
| Vocabulario       | `rung`→clase+AL (trust/11 traducida entera #103), `aggregate_rung`→`titular_level`, `min_rung`→matriz 0.2.0, 5 barras→3, `MODEL_ROUTER_BACKEND`→nota N12, era-hackathon en docs | hits restantes = ledger (histórico intocable) + declaraciones polarizadas que DECLARAN la muerte del término                                                                         |
| Código #115       | 65 archivos, diff SOLO comentarios/docstrings (engine/api/tests/studio/compose/pyproject); intocables respetados (vectores `"rung":1`, signal.py:7, «pipeline fijo» del loop)   | los gates idénticos antes/después lo prueban (cero efecto en runtime)                                                                                                                |
| Backlog #116/#117 | Los 14 ítems anexados a `04-consolidacion.md` §7 con dominio y orden declarado; menciones honoríficas = KB curada; N11 explícito en O2                                          | **cero descartes** (todo entró — #101); el único descarte-con-causa previo (`results/` duplicado) ya estaba en el censo §2.7                                                         |
| Índices           | `docs/README.md` reconstruido (jerarquía #108 + 4 desempates + mapa por plano del freeze #110 + regla de idioma #114/#118); knowledge/quantum/nexus con índices completos       | `knowledge/nexus/README.md` creado (40 JSON — el censo decía 37; contado en vivo)                                                                                                    |

### Hallazgos REPORTADOS al handoff (línea roja: sin decisión NO se ejecuta)

1. **Anexo de canonicalización — inmunización §163 no cubre V6** (censo): extenderla
   toca un doc CONGELADO sin decisión registrada → NO se hizo; que S4/Fase 0 lo decida.
2. **El freeze cita rutas hoy archivadas** (guía de ratificación y actas de research en
   sus registros de cierre): letra congelada, sin decisión de path-fix → intactas; el
   mapa del índice y `docs/archivo/README.md` resuelven la navegación.
3. **D-N12 (divorcio del mapa)** registrado con nota en `superficie-visual.md` §4 —
   resolución = V1/M18, no saneamiento.
4. **Fixtures del Studio siguen emitiendo `capability.job.invoked`**
   (`apps/studio/src/fixtures/runEvents.ts`, test del hook): es DATO de test — fuera del
   alcance solo-comentarios de #115; traducirlos cambia comportamiento del modo fixtures
   → trabajo de código (va con la whitelist SSE del cliente, censo §8.3).
5. **`apps/studio/index.html:8`**: «escalera de verificación» vive en el `content` del
   `<meta name="description">` — string funcional servido, no comentario → código.
6. **Strings de `describe()`** con «MVP task N»/«checkpoint 5» en 5 tests del Studio —
   dato de runtime de test → código menor.
7. **La ruta fantasma `/invoke`** (gatewayClient postea, nginx proxea, nadie la sirve —
   censo §2.7) sigue SIN ítem propio de backlog.
8. **El codename de marca interna** sigue en su única aparición (`docs/specs/README.md`);
   S2 no decidió reformular la línea; el enforcement versionado es O2/M26.
9. **ci.yml**: el ignore de CVE con fecha de re-evaluación vencida sigue igual (sin
   decisión); `ISSUE_TEMPLATE/config.yml` con URL rota hasta el flip.
10. **Pin frágil `68af0c1`** (`protocolo-auditoria-ratificaciones.md` alcanzable solo por
    `git show`): registrado en los headers de las actas archivadas — NO podar esa rama
    sin traer el doc al árbol.
11. **Residuos de autoría con dueño** dejados como registro de procedencia (no gates):
    «frontera Steven» en `approval.py`/su test, tags `[S-G · Steven]`, cita literal «Ese
    test ES el MVP del dominio» (comilla de doc histórico).
12. **Drift código-manifest de solvers**: el enum del manifest expone `"gurobi"` que
    `invoke` rechaza en runtime → backlog.

Docs-only salvo el barrido #115 (solo-comentarios, autorizado). Contratos tocados:
SOLO por las ceremonias ya decididas (#102-#106/C-9/C-10/N12); cero re-digests; ledger
solo-anexado (este bloque es el anexo). Siguiente: **S4 valida contra el checklist §6
de `06-saneamiento.md`** con esta evidencia y desbloquea la Fase 0.

## Sesión control Mejorado — S4 validación del saneamiento (rama `mejorado/base`, 2026-07-30)

### #119 — S4 VALIDADO con evidencia: merge de `mejorado/saneamiento` + FASE 0 DESBLOQUEADA

**Merge**: fast-forward `8e69132..f6fd024` (7 commits S3) a `mejorado/base`, hecho por
la sesión de control tras la forense del diff (abajo). Checklist §6 de
`06-saneamiento.md`, punto por punto, contra evidencia VIVA (no contra el handoff):

1. **Headers de estado + índice**: solo 2 archivos sin header
   (`docs/mvp/auditoria-mvp.md`, `knowledge/trust/README.md`) — cerrados EN S4 por la
   sesión de control (este commit; el segundo además cargaba atribución por persona
   contraria a #94). El índice es `docs/README.md` reconstruido como mapa de
   autoridad en capas (#108: jerarquía + tablas por área; los READMEs de área
   indexan por archivo) — la letra original («cada doc nombrado en docs/README»)
   queda satisfecha por el diseño en capas decidido en S2. ✓
2. **Vocabulario muerto**: los residuos de `rung`/`MODEL_ROUTER_BACKEND`/
   `PENDIENTE-{persona}`/«pipeline fijo» verificados uno a uno — TODOS viven en (a)
   docs marcados HISTÓRICO/SUPERSEDIDO con mapa de traducción (trust/03),
   (b) notas de vocabulario [S3] explícitas (quantum/04), (c) anotaciones «era
   PENDIENTE-X, gate muerto por #94» (harness-agentico ×7), (d) headers de drift
   que citan el delta (infra/03), o (e) docs de la propia fase que los citan como
   dato. Conforme a la política #109/#118 (marcas temporales; traducción total =
   refactoring final). «Pipeline fijo» además sigue siendo un MODO VIVO del código
   (claim-first) — no es vocabulario muerto. ✓
3. **Supersedes aplicados**: 10 marcas [MEJORADO] en el freeze; §15.3 con los 6
   digests cr6/cr8/ice `-voltaje@v1` + procedencia; nota N12 de reconciliación
   (`CHIMERA_MODEL_BACKEND`); `superficie-visual.md` §5 SUPERSEDIDA con marca
   C-9/#106; M9 = Langfuse perfil opcional en la consolidación. ✓
4. **Gate de docs VERDE sobre TODO el repo**: `docs:lint` 0 + `prettier --check` 0
   (antes: 671 errores); CI con `push: branches: [main, 'mejorado/**']`;
   `promote-demo.yml` placeholder eliminado. ✓
5. **Gobernanza**: CODEOWNERS reescrito a catch-all sin dueños por plano (#94);
   `.env.example` con `CHIMERA_MODEL_*` y sin `OLLAMA_API_KEY` (solo la nota de su
   remoción); era-dueños en `docs/archivo/` (19 archivos) con los 4 rescates
   aplicados ANTES (#112: registro ADR en `docs/adr/registro-adr-historico.md`,
   QUBO en islanding/01 §6). ✓
6. **Líneas rojas**: paths sensibles intactos (fixtures/corpus/nexus-data/sql: solo
   un README NUEVO en `knowledge/nexus/`); ledger solo-anexado (única línea
   «borrada» = puntero al doc archivado #112); 61 archivos de código con diff
   SOLO-comentarios/docstrings (#115, muestreado + probado por gates idénticos);
   cero re-digests. ✓
7. **Gates SIN regresión (corridos en vivo sobre el merge)**: 804 passed / 9
   skipped / 5 xpassed / cov 90.96% — IDÉNTICO al baseline (la contabilidad
   «799+5» del handoff S3 era imprecisa) · 13 contratos lint-imports · ruff 0 ·
   pyright 0 · 221 studio · eslint 0. ✓
8. **FASE 0 DESBLOQUEADA** — esta decisión. El prompt de la sesión Contratos
   (05-plan-paralelo §4) queda ajustado: su ítem (1) ola-0 está HECHO, arranca
   en (2). ✓

**Verificado además**: codename de marca interna = 0 hits repo-wide (el hallazgo del
handoff quedó resuelto). **Quedan ABIERTOS por diseño, no como deuda del
saneamiento**: los 12 hallazgos de handoff registrados por S3 (sin decisión — se
triagean en Fase 0/backlog), la migración a inglés (carril propio post-S4, #114/#118),
el refactoring documental integral y el traslado del ledger (parqueados al cierre de
Mejorado, #118), y la licencia del vendorizado quantathon (O2 pre-flip, #113).

### Tabla de interacciones (regla #3)

| Interfaz tocada                              | Dominio afectado | Estado del contrato                           |
| -------------------------------------------- | ---------------- | --------------------------------------------- |
| merge `mejorado/saneamiento`→`mejorado/base` | TODOS (docs)     | ff limpio; gates verdes citados arriba        |
| headers de estado ×2 + título trust/README   | docs             | cierre del checklist 1 (#109)                 |
| prompt Contratos en `05-plan-paralelo.md` §4 | Fase 0           | ola-0 marcada HECHA — evita trabajo duplicado |

### #120 — auditoría de reconciliación del plan de Mejorado tras el saneamiento

**Pregunta de Dylan**: ¿hace falta auditar el plan de implementación ahora que la
docs y archivos de referencia cambiaron? **Respuesta: SÍ, dirigida — ejecutada en
esta sesión.** Los docs 02/03 son registros fechados (snapshots @ 8d0620f) y NO se
editan; el plan operativo (04 §4/§7 + prompts de 05) tenía tres desincronizaciones
reales, todas cerradas:

1. **14 ítems nuevos sin sesión** (§7 de 04-consolidacion, #116/#117) — asignados:
   G += G8; P-rt += P11, P12; P-ui += P13; C-2 += C12–C15; V += V9; O += O8–O12
   (O8/O11 TEMPRANOS). Nota de extensiones bajo la tabla de sesiones + bloque
   EXTENSIONES en cada prompt.
2. **Ítems ya hechos por S3 citados como pendientes** — prompts corregidos: trust/11
   ya traducida (C-2 la lee como spec), receta TFIM = completar el stub
   knowledge/quantum/11 (G), ola-0 ya estaba marcada HECHA (#119).
3. **Triage de los 12 hallazgos de handoff S3**: 1→Contratos (inmunización V6, con
   ceremonia); 2→aceptado (letra congelada, navegación por archivo/README);
   3→ya es V1/M18; 4/5/6→P-ui; 7→P-rt (/invoke: implementar o matar);
   **8→RESUELTO VERIFICADO** (codename: 0 hits repo-wide, barrido multilínea
   incluido — el hallazgo era caduco); 9/10→O; 11→aceptado (registro de
   procedencia); 12→G (enum gurobi).

Verificado además: la tabla de dueños de specs/README está correctamente marcada
como derogada (#94) con su valor de mapa de fronteras — sin acción. Docs-only.

### #121 — asignación de modelos por sesión: doble garantía de calidad

**Decisión de Dylan (2026-07-31)**: la calidad GLOBAL la garantiza la sesión de
control (Fable — valida cierres con evidencia, mergea por checkpoint, registra); la
calidad INDIVIDUAL la garantiza el modelo de cada sesión según su riesgo:

- **FABLE (rigurosas)**: Contratos (Fase 0 — ceremonias sobre docs congelados),
  C-1 (supersede de GatewayContext + flip AX1 + JWT) y C-2 (hash-chain/DSSE/
  StatusList/KeyProvider — el diferenciador; C15 cambia veredictos estampados).
- **Opus orquesta → Sonnet implementa → Opus valida** (patrón #100 «valida-hace»):
  G, P-runtime, P-studio, V y O — brief quirúrgico por ítem, subagente Sonnet con
  TDD sin commitear, el orquestador corre gates y commitea solo lo validado; los
  ítems con ceremonia de contrato no se delegan (van al handoff de control).

Estampado en `05-plan-paralelo.md` §4 (tabla + bloques MODO copy-paste que se pegan
junto al bloque REGLAS al lanzar cada sesión). Docs-only.

## Sesión Contratos Mejorado — Fase 0 (rama `mejorado/contratos`, 2026-07-31)

> Alcance: specs de costura S-A…S-F + fixtures single-origin + tests anti-drift
> (`05-plan-paralelo.md` §1) + la extensión #120 (inmunización V6). La ola 0 se
> verificó HECHA en el ledger (#119) — no se repite. Baseline de gates en el
> worktree citado al abrir: pytest 799 passed / 14 skipped / 5 xpassed / cov
> 90.92% (mismo total 813 que #119 — 5 tests dependientes de compose pasan a
> skip fuera del stack) · lint-imports 13 kept/0 broken · ruff 0 · pyright 0 ·
> studio 221 passed.
>
> **Nota de renumeración (rebase 2026-07-31):** esta sesión abrió sobre @65cea5d
> y numeró sus decisiones #121–#127; en paralelo la base ganó el #121 (modelos,
> @b53d09a). Al rebasar sobre la base se renumeraron a **#122–#128** (mapa:
> viejo+1). Los MENSAJES de los commits previos al rebase citan los números
> viejos — este bloque y todos los ARCHIVOS citan los definitivos.

### #122 — inmunización V6 del anexo de canonicalización (hallazgo 1 del handoff S3, vía #120)

**Problema (censo §8.5 / hallazgo 1):** la nota de inmunización del anexo
(`contract-freeze-anexo-canonicalizacion.md` §6, nota final) declara «los
vectores prueban los bytes, no el vocabulario» pero nombra SOLO V1
(`stream_id: "run:…"`) y V2 (`"rung": 1`). V6 — vector NORMATIVO de
`view(claim)` — exhibe un `canonical_statement` de islanding y un
`scope = {dataset, corpus_digest}`: un implementador de retos no-MaxCut (los
consumidores de S-C) puede leer esas claves como la FORMA congelada del scope y
bloquear scopes legítimos (folds de C2, series ED de C3).

**Opciones analizadas (gobernanza #94):** (a) extender la nota de inmunización
para cubrir V6 explícitamente — aditivo, cero bytes tocados; (b) regenerar V6
con datos neutrales — RECHAZADA: la propia nota prohíbe regenerar (romperían
hashes) y el checklist punto 6 ya verifica contra estos bytes; (c) no hacer
nada — RECHAZADA: el hallazgo es real y S-C lo pisa de inmediato.

**Decisión: (a).** La forma normativa de `view(claim)` es EXACTAMENTE el sobre
de 2 campos `{canonical_statement, scope}` (§5 del anexo); el CONTENIDO del
vector — el texto del statement y las claves internas `{dataset, corpus_digest}`
del scope — es dato arbitrario del gate de hashing: el scope real es el
ScopeExpr canónico del certificado (freeze §4), cuyas claves dependen del claim.
Edición aditiva con marca `[MEJORADO #122]` tras la nota existente; los vectores
y sus hashes quedan intactos byte a byte.

### #123 — S-A: contrato de chat/conversación (`docs/specs/chat-conversacion.md`, spec NUEVA)

Cierra M1-c/M1-d como CONTRATO (la implementación es P3/P6 de Fase 1). Decisiones
de forma, cada una con su porqué:

1. **`mission.message` ↔ `●MissionMessage`** materializa la reserva explícita del
   catálogo §14 (marca [MEJORADO #102]: «entra cuando M1/P3 lo traiga») — cero
   supersede nuevo. Payload `{run_id, message_id, author, text}`, módulo propuesto
   `blite.runtime.mission`. El evento entra al stream ANTES del terminal ⇒ queda
   DENTRO del `provenance_hash`: la conversación que dirigió el run es parte de lo
   que el certificado ampara.
2. **`POST /runs/{id}/messages`**: `202 {message_id}` / 404 / **409 post-terminal**
   (el §2 ya rechaza appends post-terminales — el 409 es la cara HTTP de esa regla,
   no una política nueva). `author` NO viaja en el body: lo estampa la identidad del
   request (hoy `_API_ACTOR`; C2/M2 lo vuelve real — mismo patrón AX1).
3. **`POST /runs/{id}/cancel`**: emite `run.cancelled` YA congelado (§3);
   `reason` default `"user_requested"` (`"parent_cancelled"` queda reservado a la
   cascada §13). 202/404/409.
4. **`run.created` gana `thread_id?`/`project_id?` ADITIVOS** — extensión de la
   forma exacta de §3 ⇒ ceremonia: esta decisión + marca «(d)» en el bloque de
   supersedes de §3 (mismo patrón que max_turns/budget vía #66). `thread_id` =
   `run_id` del run RAÍZ del hilo (ausente ⇒ este run abre hilo); el enhebrado
   post-terminal se hace creando un run NUEVO con `thread_id`, jamás apendeando al
   stream muerto. `project_id` = referencia opaca a la fila relacional de M15
   (FUERA del event store; el evento no valida FK — la valida el API cuando P6
   exista). `MissionRequest` gana los mismos dos campos opcionales.
5. **`TurnContext.pending_messages`** (queue-to-next-turn): tupla con default `()`
   — aditivo compatible; los mensajes llegados DURANTE un turno se drenan al
   `TurnContext` del turno siguiente, jamás interrumpen el turno en curso.
6. **`PROMPT_PROTOCOL` v2 con historial**: `chimera/mission-proposer-prompt/v2` =
   v1 + `messages: [{author, text}]` (la misión como primer mensaje + cada
   `mission.message` en orden de stream). **`message_id` se EXCLUYE de la vista**
   por la MISMA razón que `run_id` en v1 (freeze §15.7: la clave de replay jamás
   repetiría entre sesión grabada y reproducción). Las sesiones v1 grabadas siguen
   reproduciendo (el manifest pinnea digests; el campo `protocol` discrimina).
7. **Zod espejo de approvals** (el hueco N2 lado contrato): `approvalRequested/
RespondedSchema` + tests del Studio contra los fixtures `contract/harness/`
   existentes — se entrega EN Fase 0 (es test anti-drift, no feature); la card
   inline es P3-D.

### #124 — S-B: forma del wire de `discarded_streams` (elaboración de #104)

**Estado previo verificado:** los CINCO supersedes doc-side de S-B ya estaban
estampados por S3 en el freeze (§3 marcas (a) #104 y (b) C-4; §7 marca (c) C-6;
§8 marca C-5; §15.7 nota N12) — esta sesión NO los re-estampa; entrega el lado
ejecutable (spec de wire + seeds).

**Problema de forma:** #104 manda «extensión aditiva del wire E↔D», pero
`GET /runs` devuelve un **array desnudo** (`reads.py:371`, `list[RunSummary]`)
— envolverlo en `{runs, discarded_streams}` rompería el parse Zod existente
(exactamente el choque que C-3 de la cobertura flaggeó).

**Opciones:** (a) envolver el array — RECHAZADA (rompe E↔D; contradice la letra
«aditiva» de #104); (b) header HTTP con el conteo — RECHAZADA (los headers no
viajan por el pipeline fixture+Zod: contrato invisible); (c) **ruta hermana
`GET /runs/discarded`** — ADITIVA pura: `GET /runs` queda byte-idéntico.

**Decisión: (c).** `GET /runs/discarded` → `{discarded_streams: [{stream_id,
error_kind, detail?}]}` (envelope objeto — ruta nueva, extensible). Semántica:
la proyección de `GET /runs` captura POR STREAM la excepción de proyección
(píldora #96: `run.created` sin `policy_digest`/`max_steps` explota hoy TODO el
listado), omite ese stream del array y lo registra para la ruta hermana —
`error_kind = type(exc).__name__`, mismo vocabulario que `run.failed`. Reserva
de namespace: el segmento literal `discarded` no colisiona (los `run_id` son
uuid4; misma doctrina que la reserva `system:` del freeze §2). **Línea roja
intacta:** SOLO la ruta de lectura — escritura/certificados/provenance siguen
fail-loud. Fixture declarado: `contract/endpoints/get-runs-discarded.json`
(modelo Fase 1, P2); seed `tests/seeds/test_seed_lectura_discarded.py` con la
píldora #96 como caso. El payload extendido de metrics (C-4) se especifica en
la pasada S-D (`superficie-visual.md` — es la superficie que lo consume); los
seeds de C-5 (`GatewayContext` aditivo) y C-6 (`verify_all`) entran con esta
decisión sin ceremonia nueva (C-5/C-6 ya están decididas en #106).

### #125 — S-D: superficie visual — branch-ids C-8, rvsp C-9, metrics C-4 (elaboraciones de #106)

**Estado previo verificado:** el supersede de `superficie-visual.md` §5 ya estaba
estampado por S3 (marca [MEJORADO C-9/#106]). Esta decisión materializa el DETALLE
ejecutable que #106 dejó enunciado:

1. **Convención de branch-ids (C-8)** — texto normativo nuevo en
   `superficie-visual.md` §8: instancias derivadas de GIS usan `edge_id_property`
   (FID/OBJECTID del portal, declarado en la receta de `geojson_to_graph`);
   modelos sin GIS usan el id canónico determinista **`L{min}-{max}[-k]`**
   (buses ordenados; `k` = índice 1-based de paralela, presente SOLO con
   multi-aristas). La convención se VERSIONA con la instancia
   (`recipe.version` + `params_digest` — un cambio de convención es instancia
   nueva, jamás re-etiquetado silencioso). Verdict por isla =
   `derive_execution_verdict` aplicado al subconjunto de checks `island-{k}:*`
   de esa isla; `step_id = island_id` estable (`island-{k}`) — la base que C4/M4
   consume.
2. **Wire de `GET /runs/{run_id}/rvsp` (C-9)** — fila nueva en
   `endpoints-studio.md`: snake_case (el espejo camelCase existente
   `rvspSchema` gana mapper en Fase 1, mismo patrón `toRunSummary`); 404 para
   run desconocido Y para run cuya instancia no tiene `optimo` (`ice-*` FUERA
   del endpoint — jamás una curva fabricada); `baselines` cerrado a 3 claves
   (`cpsat/greedy/gw`) con extensión COORDINADA al llegar `sa` (C-15, G5).
3. **Payload extendido de `run.metrics.recorded` (C-4)** — forma exacta en
   `superficie-visual.md` §9: los campos de confianza congelados (§3 [S-F]) se
   mantienen; entran `variant?` (enum de 4: `quantum|classical|mitigated|zne`) y
   los científicos opcionales `cut_cost?`/`wall_ms?` (lo que `AblationMetric`
   consume — nada más se especula). Módulo propuesto: `blite.runtime.metrics`
   (`RunMetricsRecordedPayload`). Dos brazos = sub-runs (§13): cada brazo emite
   SU evento en SU stream. `AblationMetric`/Zod/TS/chart extienden el enum a 4
   en el MISMO checkpoint (extensión coordinada, jamás catchall).
4. **Fixture `contract/superficie/`** (precondición del merge de V1, letra C-8):
   `topology-snapshot.json` se genera HOY desde `TopologyResponse`
   (`api/src/chimera_api/reads.py:138` — el modelo YA existe) con el shape §4
   (verification POR isla) y branch-ids ejemplificando la convención §8;
   espejo + Zod `topologySnapshotSchema` NUEVO + anti-drift en ambos lados.
   Declarados (modelo Fase 1): `run-metrics-recorded.json` (V2) y
   `contract/endpoints/get-runs-rvsp.json` (V3).

### #126 — S-C: contrato de generalidad (`docs/specs/generalidad-retos.md`, spec NUEVA)

Decisiones de forma para que los retos 2/3 corran EN la plataforma (G1–G4):

1. **claim_types por reto = REUSO del registro STEM, no invención**: la
   conclusión C3 (series TFIM vs ED) es **`simulation_result`** (perfil §1:
   modelo digest + params digest + seeds + output digest — calza exacto, techo
   AL3); la conclusión C2 (desempeño del clasificador vs baseline) es
   **`statistical`** (McNemar; la extensión `statistical_procedure` ya prevista
   en perfil §1 nota). Los claims intermedios siguen el vocabulario runtime
   (`intermediate`, C1). El perfil está CONGELADO ⇒ **anexo aditivo aparte**
   (mismo patrón que `capability-ingesta.md` declaró): la §"Anexo del perfil
   STEM" de la spec ES el anexo (versión menor v1.0→v1.1 — perfil §6: agregar
   schemas/plantillas = versión menor), sin editar el doc congelado.
2. **C-14 (detalle de la extensión ya decidida en #106):** `Differential.status`
   gana el literal **`EXACT_DIAGONALIZATION`** (aditivo a la unión CpSat) y
   `Differential` gana **`relative_tolerance: float | None = None`** (≤5%
   oficial; `None` para CP-SAT que sigue en `abs_tol: 0`); la tolerancia entra
   al `verifier_params_digest` del verificador que la usa.
3. **Homes de los verificadores nuevos** (predicates YA congelados sin adapter):
   `blite.verification.exact_diagonalization.ExactDiagonalizationVerifier`
   (`formal_exact`, ancla `solver` — recompute vivo, mismo patrón CP-SAT) ·
   `blite.verification.ground_truth.GroundTruthVerifier` (`ground_truth`, ancla
   `dataset`) · `blite.verification.property_rule.PropertyRuleVerifier`
   (`property_rule`, ancla `rule`). Dos patas C3 por construcción: formal_exact
   (recompute ED) + ground_truth (series congeladas del corpus) = grupos de
   independencia distintos.
4. **Identidad de corpus GENERALIZADA**: la regla islanding §1.6/§15.3 se
   generaliza a `dataset_id = "<corpus>/<instancia>[-<convencion>]@v<n>"` con
   digest EMBEBIDO self-consistente (mismo algoritmo); C3 =
   `tfim-corpus/...`, C2 = `tabular-corpus/...` (ids concretos los estampa
   G1/G2 al congelar los JSON — jamás esta spec). Folds C2 sellados por
   COMPROMISO PREVIO: `folds_digest` (asignación de folds canonicalizada)
   emitido ANTES de cualquier fit, citado por el claim.
5. **Dispatch por clase (G3)**: `resolve_verifiers` conserva su firma; el
   hardcode Reto-1 (`_OPTIMALITY_CLAIM_TYPES`/`ELECTRICAL_DATA`) se reemplaza
   por un registro declarativo por `claim_type` (`CLAIM_TYPE_VERIFIERS`) —
   resolución vacía sigue siendo 400 fail-closed.
6. **Fixtures `contract/generalidad/`**: generables HOY (modelos existentes) —
   `claim-c3-simulation-result.json` / `claim-c2-statistical.json` (desde
   `ClaimEmittedPayload`) y `predicate-ground-truth.json` /
   `predicate-property-rule.json` (desde los predicates congelados); espejo
   Studio byte-idéntico con verificación Python (mismo precedente que
   ingesta/informe: sin consumidor Zod todavía).

### #127 — S-E: manifest v2 en el SDK (`docs/specs/manifest-v2-sdk.md`, spec NUEVA)

El §1 del freeze está congelado desde S-E; esta decisión fija SOLO lo que la
letra dejó abierto para aterrizarlo en `blite_capability.manifest`:

1. **Sin defaults para el riesgo**: `side_effects`/`required_permission`/
   `interaction` son OBLIGATORIOS (la letra §1 solo da default a
   `execution_profile = "in-process"`); defaultear `side_effects` mentiría el
   eje de riesgo que la Policy y el reintento §13 consumen — un manifest sin
   migrar FALLA al cargar (cae en `failed[]` del registry, visible, jamás
   silencioso).
2. **El dataclass se queda** (SDK-standalone sin deps — contrato import-linter);
   los 3 literals se validan en `__post_init__` (`ValueError` fail-closed al
   cargar el entry point).
3. **Convención de `required_permission`**: baseline `capability:invoke`;
   permisos finos donde el riesgo lo pida (los `capability:ingest:*` de la
   tabla-workaround de ingesta se PORTAN tal cual). La etapa 2 del gateway lo
   chequea contra la intersección efectiva (§8) — el manifest declara, no
   autoriza.
4. **Migración coordinada de las 13**: tabla completa en la spec (12 de 13 son
   `pure`/`request_response`/`in-process`; la excepción es
   `blite.ingesta.snapshot.fetch` = `reversible-external`/`job`). El
   docstring-workaround de ingesta (`tool.py:8-30`) MUERE al migrar — sus
   valores viajan al manifest y la tabla del docstring se borra.
5. **Gate de genericidad EXTENDIDO**: `_manifest_text`
   (`tests/invariants/test_capability_genericity.py`) pasa de serializar 4
   campos a serializar el manifest COMPLETO (incl. `required_permission`,
   `tags` y los 4 nuevos) — un permiso con vocabulario de escenario también es
   fuga.
6. Fixture declarado: `tests/fixtures/contract/manifest/capability-manifest-v2.json`
   (dataclass → `asdict`; lo genera C1 al existir el campo). Seed:
   `tests/seeds/test_seed_manifest_v2.py`.

### #128 — S-F: proyector de observabilidad (`docs/specs/observabilidad-proyeccion.md`, spec NUEVA)

Materializa C-11 (#106: consumer standalone FUERA de `blite.*`) como contrato:

1. **Home**: miembro nuevo `projectors/otel/` (paquete `chimera_otel`) — fuera
   de `blite.*` y de los 13 contratos import-linter por construcción; NO
   importa el engine: parsea los eventos como JSON (el wire ES el contrato).
2. **Fuente**: lectura READ-ONLY de la tabla `events` con usuario Postgres
   SOLO-SELECT + catch-up por `global_seq` con cursor PROPIO fuera del event
   store (misma doctrina notify-then-catchup §2). No toca Inv-E/INV-6: el
   proyector deriva, jamás gobierna; exporta DIGESTS, jamás contenido
   (hash-first §2 — un span jamás carga prompt/respuesta en claro).
3. **IDs deterministas** (replay/re-proyección ⇒ trazas byte-idénticas):
   `trace_id = SHA-256("blite/otel-trace/v1\n" + run_id)[:16 bytes]`;
   `span_id = SHA-256("blite/otel-span/v1\n" + run_id + ":" + <ancla del
span>)[:8 bytes]` (ancla = `step_id`/`job_id`/tipo según la tabla de
   mapeo); timestamps = `occurred_at` del evento, jamás el reloj de la
   proyección. Prefijos de dominio versionados (misma disciplina del anexo).
4. **Semconv GenAI PINNEADA y ESTAMPADA**: la versión exacta la pinnea O3 al
   implementar (con registro); la REGLA es contrato: cada span porta
   `chimera.semconv_version` + `chimera.projector_version` — dos proyecciones
   con semconv distinta jamás se confunden.
5. **Langfuse = perfil OPCIONAL** del compose (consumidor OTLP aguas abajo,
   herramienta interna de debugging del proposer) — jamás «backend».
6. Fixture declarado: `tests/fixtures/contract/observabilidad/trace-example.json`
   (golden trace del proyector sobre un stream fixture — lo genera O3). Seed:
   `tests/seeds/test_seed_observabilidad_proyector.py` (derivación de ids
   recomputada de forma independiente).

### Registro de cierre — Fase 0 Contratos COMPLETA (2026-07-31)

**Alcance cerrado**: (1) ola-0 verificada HECHA en #119 — NO repetida; (2)–(7)
S-A…S-F entregadas + extensión #120 (inmunización V6, #122). Decisiones de la
sesión: **#122–#128**. Commits en `mejorado/contratos` (docs/spec SIEMPRE
separados de fixtures/tests, sin push — lo coordina Dylan).

**Gates al cierre (corridos en vivo, worktree con venv del principal +
PYTHONPATH):** pytest **818 passed / 14 skipped / 29 xfailed / 5 xpassed / cov
90.92%** (baseline de apertura: 799 passed — los +19 son los tests de contrato
nuevos de superficie/generalidad; los 29 xfailed incluyen los ~21 seeds nuevos
de Fase 0, todos `strict=False`) · lint-imports **13 kept / 0 broken** · ruff
**0** · pyright **0** · studio **227 passed** (221 + 6 de espejos
approvals/topología) · eslint **0** · markdownlint **0** · prettier **0**.

**Entregables por costura:**

- **S-A**: `chat-conversacion.md` + marca (d) freeze §3 (#123) + Zod espejo de
  approvals VERDE ambos lados + seed `test_seed_chat_conversacion.py` (8).
- **S-B**: los 5 supersedes doc-side YA estaban estampados por S3 (verificado:
  §3 a/b, §7 c, §8 C-5, §15.7 N12); entregado el lado ejecutable — wire
  `GET /runs/discarded` (#124) + seeds discarded/gateway-context/verify_all (6).
- **S-C**: `generalidad-retos.md` (#126) + 4 fixtures `contract/generalidad/`
  VERDES ambos lados + seed C-14/homes/dispatch (4).
- **S-D**: §8/§9 de `superficie-visual.md` + fila rvsp y nota ablation en
  `endpoints-studio.md` (#125) + fixture `contract/superficie/topology-snapshot`
  VERDE ambos lados (con `topologySnapshotSchema` nuevo) + seeds metrics/rvsp (5).
- **S-E**: `manifest-v2-sdk.md` (#127, tabla de migración de las 13) + seed (3).
- **S-F**: `observabilidad-proyeccion.md` (#128) + seed ids deterministas (3).
- **#120**: inmunización V6 del anexo (#122) — aditiva, bytes/hashes intactos.

### Tabla de interacciones (regla #3)

| Interfaz tocada                                                    | Dominio afectado | Estado del contrato                                       |
| ------------------------------------------------------------------ | ---------------- | --------------------------------------------------------- |
| Anexo canonicalización — nota V6 (#122)                            | confianza        | VIGENTE — aditivo con ceremonia; vectores intactos        |
| freeze §3 marca (d): `run.created.{thread_id?,project_id?}` (#123) | A↔E↔D            | Supersede aditivo registrado; implementa P3/P6            |
| `docs/specs/chat-conversacion.md` (NUEVA)                          | A↔E↔D            | SPEC — consumen P3, P6, P-ui                              |
| Zod espejo `approval.*` (`schemas.ts` + tests)                     | D                | **VERDE** — fixtures existentes, anti-drift ambos lados   |
| `endpoints-studio.md` §GET /runs/discarded (#124)                  | E↔D              | SPEC + seed — implementa P2                               |
| `endpoints-studio.md` §GET /runs/{id}/rvsp + nota ablation (#125)  | E↔D              | SPEC + seed — implementa V3/V2                            |
| `superficie-visual.md` §8 branch-ids C-8 / §9 metrics C-4 (#125)   | D↔E↔A            | SPEC — implementan V1/V2; base de C4/M4                   |
| `contract/superficie/topology-snapshot` + `topologySnapshotSchema` | D↔E              | **VERDE** — single-origin `TopologyResponse`, ambos lados |
| `docs/specs/generalidad-retos.md` (NUEVA, #126) + 4 fixtures       | B↔A↔confianza    | SPEC; fixtures **VERDES** ambos lados — consumen G1–G4    |
| `docs/specs/manifest-v2-sdk.md` (NUEVA, #127)                      | SDK↔B↔ejecución  | SPEC + seed — implementa C1; desbloquea G/O5              |
| `docs/specs/observabilidad-proyeccion.md` (NUEVA, #128)            | stream→OTel      | SPEC + seed — implementa O3                               |
| Índice `docs/specs/README.md` — sección Fase 0 Mejorado            | docs             | Aditiva; 4 specs nuevas + 2 extendidas indexadas          |

**Siguiente paso (sesión de control):** merge de `mejorado/contratos` a
`mejorado/base` (gates citados arriba como evidencia) — con eso las sesiones de
Fase 1 (G, P-rt, P-ui, C-1, C-2, V, O) quedan desbloqueadas con sus contratos
completos: cada prompt de `05-plan-paralelo.md` §4 ya cita la spec que aquí se
entrega.

## Sesión control Mejorado — validación y merge de Fase 0 (rama `mejorado/base`, 2026-07-31)

### #129 — FASE 0 CONTRATOS VALIDADA Y MERGEADA: Fase 1 desbloqueada

**Merge**: fast-forward `b53d09a..0283afa` (15 commits de `mejorado/contratos`,
rebasados limpio) hecho por la sesión de control tras forense y validación:

- **Forense del diff**: 35 archivos, +2519 líneas, TODO aditivo; **cero código
  productivo tocado** (engine/api/sdk src intactos — Fase 0 pura); cero paths
  sensibles (corpus/nexus/SQL); contratos tocados SOLO por ceremonia (anexo V6
  con marca [MEJORADO #122] y vectores intactos; freeze §3 marca (d) #123; los
  supersedes doc-side de S-B ya estampados por S3 — verificados, no duplicados).
- **Entregables verificados**: 4 specs nuevas (chat-conversacion, generalidad-retos,
  manifest-v2-sdk, observabilidad-proyeccion) + 2 extendidas (endpoints-studio:
  discarded/rvsp; superficie-visual: §8 branch-ids/§9 metrics) + 5 fixtures
  single-origin **byte-idénticos verificados con diff -r** en ambos lados + Zod
  espejo de approvals y topología + 9 seeds xfail + 2 anti-drift + índice.
- **Gates corridos EN VIVO sobre el merge** (autoridad sobre los del worktree):
  **823 passed / 9 skipped / 29 xfailed / 5 xpassed / cov 90.96%** — contabilidad
  exacta: 823 = 804 baseline + 19 tests de contrato nuevos; skips idénticos al
  baseline (los «14 skipped / 818 / 90.92%» del registro de cierre eran artefacto
  del entorno del worktree); los 29 xfailed son los seeds de Fase 0, rojos a
  propósito (`strict=False`) hasta que Fase 1 los implemente · lint-imports 13/0 ·
  ruff 0 · pyright 0 · studio 227 · eslint 0 · markdownlint 0 · prettier 0.
- **Decisiones de la sesión Contratos**: #122–#128 (registradas por ella;
  renumeración por colisión con #121 hecha en su último commit).

**FASE 1 DESBLOQUEADA**: G, P-rt, P-ui, C-1, C-2, V y O tienen sus contratos
completos; cada prompt de `05-plan-paralelo.md` §4 cita la spec entregada aquí.
Orden de lanzamiento (#121): paso 2 = C-1 (FABLE) + G/P-rt/P-ui (Opus→Sonnet→Opus);
paso 3 = C-2 (FABLE) + V/O. Los checkpoints CP1–CP7 los valida y mergea la sesión
de control.

### Tabla de interacciones (regla #3)

| Interfaz tocada                            | Dominio afectado  | Estado del contrato                    |
| ------------------------------------------ | ----------------- | -------------------------------------- |
| merge `mejorado/contratos`→`mejorado/base` | TODOS (contratos) | ff limpio; gates verdes citados arriba |

## Sesión CONFIANZA-1 Mejorado — C1 manifest v2 + C2 gateway por step (rama `mejorado/confianza-1`, 2026-07-31)

> Numeración #130–#133 tomada al cierre de esta sesión; si otra sesión de Fase 1
> colisiona, se renumera al merge (precedente #122–#128).

### #130 — C1 EJECUTADO: manifest v2 en el SDK + migración coordinada de las 13

La letra de S-E (#127) aterrizó tal cual: `side_effects`/`required_permission`/
`interaction` obligatorios + `execution_profile` default `"in-process"`, literals
validados en `__post_init__` (`ValueError` fail-closed); las 13 capabilities
migradas EXACTAMENTE según la tabla de S-E en el mismo checkpoint; el
docstring-workaround de ingesta MURIÓ (una sola fuente: el manifest). Decisiones
propias de la ejecución:

- **El despacho consume el manifest**: `loop.py` y `MediationStage` resuelven
  `dispatcher.resolve(manifest.execution_profile)` — el TODO «hasta que el
  manifest exponga execution_profile» se cerró; un perfil sin estrategia falla
  el run/cruce, jamás fallback silencioso (test nuevo con capability
  `remote-job`).
- **Hallazgo + fix del gate de genericidad**: los entry points registran
  CLASES (ADR-008) y el gate previo hacía `getattr(clase, "manifest")` → un
  `property object` → escaneaba `""` — **el gate ADR-029 corría sobre texto
  vacío para toda capability registrada como clase**. Fix: instanciar antes de
  leer; `_manifest_text` ahora serializa el manifest COMPLETO vía
  `dataclasses.asdict` (permisos/tags/versión incluidos, letra #127) y un
  self-test fija la cobertura del propio gate.
- Fixture de contrato `contract/manifest/capability-manifest-v2.json`
  (generador `gen-contract-fixtures-manifest.py`, espejo Studio, anti-drift
  falla-fuerte) + seed `test_seed_manifest_v2` VERDE (xfail retirado).

### #131 — C2 EJECUTADO: cruce del gateway por step — inyección, 6 etapas reales, mapeo de eventos

`GatewayContext` ganó `run_id`/`step_id`/`domain_id` opcionales (ceremonia C-5
cumplida — aditivo puro, frozen/forbid intactos; seed retirado). Las 6 etapas
que faltaban son REALES según los deberes de execution/01 §1.2; `mediation`/
`egress` quedaron intactas salvo extensión journalizadora. Decisiones de diseño
registradas:

- **UN cruce por invocación** (interpretación §13 de C-5): el loop llama el
  cruce una vez por par resolve→invoke; resolve es parte de mediation. El seam
  runtime-side (`CrossingRequest`/`CrossingRejected`/`GatewayCrossing`) vive en
  `blite.runtime.loop`; el adapter (`RunCrossing` + `build_run_pipeline`) en
  `blite.gateway.crossing` — **contrato import-linter `layers` nuevo (14º)**:
  gateway importa runtime, runtime JAMÁS gateway.
- **Semántica de actores (elaboración de §13 cascada)**: los eventos DEL CRUCE
  (`capability.job.*`, `signal.recorded`) llevan el actor REAL de la Identity
  del cruce (AX1); los eventos del RUNTIME fuera del cruce (`run.started`,
  `run.step.*`, terminales) conservan `service:runtime` con `run.created`
  estampando el actor del caller — la regla de §13 se escribió cuando el cruce
  no existía; esta partición la honra sin reescribirla.
- **Mapeo `Rejection`→eventos**: `run.step.failed` (RunStep status=failed) +
  `run.failed {error_kind: "GatewayRejection", stage, reason}` — claves
  ADITIVAS del payload (la proyección solo lee `error_kind`). `mediation` con
  store journaliza `capability.job.failed` ANTES de su Rejection (INV-4).
- **Etapas y sus límites**: `identity` rechaza SOLO identidad inválida
  (coherencia de dominio del cruce); `authorization` evalúa
  `manifest.required_permission` (manifest v2 — por eso C1 fue primero) contra
  los permisos de la Identity y corta ANTES de gastar despacho; `guardrails`
  registra `Signal`s como `signal.recorded` (●SignalRecorded §14) y JAMÁS
  decide (INV-3) — detector roto sí es Rejection fail-closed; `provenance:pre/
post` emiten `capability.job.submitted/completed` (PR1: submitted ANTES de
  ejecutar) con digests por la MISMA puerta canónica que el loop (módulo nuevo
  `blite.runtime.digests` — dos canonicalizaciones divergentes envenenarían la
  procedencia; test de igualdad step↔job); `verification` es el seam POR
  INVOCACIÓN con consistencia fail-closed (outputs presentes) — la verificación
  DECISORIA del run sigue en el delegate post-invoke (INV-2/R-Pol1 intactos).
- **Sin cruce inyectado** (`crossing=None`): comportamiento byte-idéntico al
  previo — la superficie de tests/API existente no cambió (mismo patrón que
  `proposer`).

### #132 — la sesión de seguridad del API: JWT en cookie (P1-9) + flip AX1

`blite.identity.jwt`: JWS compacto EdDSA (jamás HS256) firmado VÍA el puerto
`KeyProvider` del §7 (la llave no sale de la custodia; escalón 1 = llave
efímera en memoria del API — Transit es C8/C-2); claims exactos del freeze §8
(`iss/sub/kind/domain_id/permissions/act/iat/exp`); verificación solo con la
llave pública (S2). `POST /auth/session` emite la cookie HttpOnly del OPERADOR
del despliegue (`CHIMERA_OPERATOR_ID`/`CHIMERA_OPERATOR_PERMISSIONS`; doctrina
§7: quién actúa es dato del despliegue). Reglas:

- cookie INVÁLIDA ⇒ **401 fail-closed** — un token roto jamás degrada al
  default (sería bypass silencioso).
- cookie AUSENTE ⇒ la identidad default del operador local (la MISMA que
  `/auth/session` emitiría) — **frontera registrada**: el flip a
  401-obligatorio (incluido el SSE, letra P1-9) espera a que el Studio
  bootstrapee su sesión (P-ui/P6); imponerlo hoy rompería el Studio vivo sin
  su mitad del contrato. `_API_ACTOR = "user:api"` MURIÓ.
- **AX1 volteado**: `test_types.py::test_event_has_non_null_actor_id` perdió el
  xfail y ganó la aserción ENDURECIDA a procedencia del actor (un cruce real
  journalizado debe estampar la identidad verificada en cada evento del job);
  el test jamás se borra. `docs/invariants.md` §AX1 pasa a **ENFORCED** con la
  historia del placeholder preservada.

### #133 — rollback de la decisión #6 (claim del body): NO ejecutado

Mandato del prompt: evaluar el rollback SOLO si el cruce lo habilita. Análisis:
el cruce media INVOCACIONES de capability (resolve+invoke) — no toca el origen
del claim ni su verificación; derivar el claim server-side seguiría siendo
inferencia sin actor atribuible del lado del enunciado. **#6 sigue vigente**: el
claim viaja completo en el request; nada se infiere server-side. Registrado
aparte como manda el prompt.

### Registro de cierre — C1+C2 (2026-07-31)

- Commits: `17f455c` (C1) · `735b539` (C2 cruce) · `1bd10ab` (C2 sesión/AX1),
  sobre `bdde94e` en `mejorado/confianza-1` (sin push).
- Gates en el worktree (venv del principal + PYTHONPATH del worktree, TODAS las
  rutas de capabilities — con PYTHONPATH corto los entry points resuelven al
  código v1 del principal y los 13 caen en `failed[]`; artefacto de entorno,
  no defecto): **861 passed / 14 skipped / 24 xfailed / 4 xpassed / cov
  91.24%** · lint-imports **14 kept / 0 broken** · ruff 0 · pyright 0 ·
  studio 227. Los 14 skipped = sin `CHIMERA_TEST_DATABASE_URL` ni espejo
  reto1-vanilla en el entorno; los 4 xpassed son previos (informe×3 +
  cvxpy/HIGHS), AX1 ya no xpassa: pasa DURO.
- Contabilidad de seeds: 29 xfailed del baseline − 3 (manifest v2) − 2 (ctx
  aditivo) = 24; +38 tests netos nuevos (823→861).
- **CP4/CP5 VIVOS contra compose (2026-07-31, stack del worktree
  `mejorado-confianza-1`, imagen construida desde la rama):**
  - `scripts/smoke_infra.sh` **PASS** completo (smoke 2.5 verde): postgres
    healthy + api /health + **13 entry points en el contenedor** + integración
    Postgres 8/8 + evento E2E engine→postgres→SSE + proyección ilesa.
  - **CP4**: dentro del contenedor api, los 13 entry points CARGAN y sus
    manifests portan los 4 campos v2 EXACTOS de la tabla S-E (verificado campo
    por campo; `snapshot.fetch` = reversible-external/ingest:external-source/
    job, `geojson.to_graph` = pure/ingest:derive, resto pure/invoke/
    request_response; los 13 in-process).
  - **CP5**: `POST /auth/session` emitió la cookie JWT (`user:local-operator`)
    → `POST /runs` modo misión sobre `cr6-uniforme` (registry real,
    `blite.solvers.qubo`) → run `run-8b76d14c…` con 2 turnos REALES: los 4
    `capability.job.submitted/completed` del rastro los emitió el CRUCE con
    `actor_id: user:local-operator` (el actor del JWT), `run.created` estampa
    el mismo actor, los `run.*`/`run.step.*` del runtime conservan
    `service:runtime` (partición #131), terminal `run.failed {exhausted}`
    exacto al §Contrato-3. Cookie manipulada ⇒ **HTTP 401** en vivo.

### Tabla de interacciones (regla #3)

| Interfaz tocada                                                        | Dominio afectado | Estado del contrato                                        |
| ---------------------------------------------------------------------- | ---------------- | ---------------------------------------------------------- |
| `blite_capability.manifest` v2 (4 campos §1)                           | SDK↔B↔ejecución  | **VERDE** — letra S-E/#127; seed retirado                  |
| 13 capabilities migradas + muerte del workaround ingesta               | B                | **VERDE** — tabla S-E exacta                               |
| `loop.py`/`MediationStage` despachan por `manifest.execution_profile`  | ejecución        | VIGENTE — sin fallback silencioso                          |
| Gate ADR-029 `_manifest_text` (asdict + instanciación)                 | invariantes      | **VERDE** — fix: antes escaneaba texto vacío               |
| `contract/manifest/capability-manifest-v2.json` + generador + espejo   | SDK↔D            | **VERDE** — byte-idéntico + anti-drift                     |
| `GatewayContext` +`run_id`/`step_id`/`domain_id` (C-5)                 | gateway          | VIGENTE — ceremonia cumplida; seed retirado                |
| 6 etapas reales + extensión journalizadora de `mediation`              | gateway          | **VERDE** — deberes execution/01 §1.2                      |
| `execute_run(crossing=...)` + `CrossingRequest/Rejected`               | ejecución        | Aditivo — default None = byte-idéntico previo              |
| `blite.gateway.crossing` (`RunCrossing`/`build_run_pipeline`)          | gateway          | NUEVO — adapter del lado alto de la capa                   |
| Contrato import-linter `layers` gateway/runtime (14º)                  | repo             | NUEVO — 14 kept / 0 broken                                 |
| `run.failed` payload aditivo `{stage, reason}` en GatewayRejection     | E↔D              | Aditivo — proyección/Studio leen `error_kind` como siempre |
| `signal.recorded` emitido por guardrails (●SignalRecorded §14)         | confianza        | VIGENTE — catálogo ya lo declaraba; primer emisor real     |
| `blite.identity.jwt` (JWS EdDSA vía KeyProvider)                       | confianza        | NUEVO — claims freeze §8                                   |
| `POST /auth/session` + cookie `chimera_session` (P1-9)                 | E↔D              | NUEVO — 401 fail-closed con cookie inválida                |
| `POST /runs` deriva actor de la sesión; `_API_ACTOR` muere             | E                | VIGENTE — frontera P-ui: flip a 401-obligatorio pendiente  |
| `tests/invariants/test_types.py` AX1 endurecido + `invariants.md` §AX1 | confianza        | **ENFORCED** — jamás borrado                               |
| `blite.runtime.digests` (puerta canónica compartida)                   | ejecución        | NUEVO — igualdad step↔job testeada                         |

### Adenda — ronda de revisión de código de la sesión (2026-07-31)

Revisión independiente sobre el diff completo de la rama (agente code-reviewer):
JWT (firma/expiración/confusión de alg), etapas fail-closed, integridad del
rastro y compat `crossing=None` confirmados sin hallazgos de alta confianza.
UN hallazgo importante, corregido en `37063cb`: la cookie de sesión sin
atributo `Secure`. `secure=True` incondicional rompería el walking skeleton
local (una cookie Secure en http plano se DESCARTA en silencio ⇒ degradación
al operador default sin error) — el atributo pasa a dato del despliegue:
**`CHIMERA_SESSION_COOKIE_SECURE=1` obligatorio en despliegues TLS (Fargate)**,
apagado en local. Nota registrada para quien cablee el `verification_hook`
(hoy seam sin consumidor): `VerificationStage` deberá recibir `store` para
journalizar el rastro del job si el hook explota.

| Interfaz tocada                                              | Dominio afectado | Estado del contrato                            |
| ------------------------------------------------------------ | ---------------- | ---------------------------------------------- |
| Env `CHIMERA_SESSION_COOKIE_SECURE` (+`.env.example` sesión) | E/infra          | NUEVO — knob del despliegue; default local off |

## Sesión GENERALIDAD Mejorado — G1 reto 3 (TFIM/Trotter) (rama `mejorado/generalidad`, 2026-07-31)

> Numeración #134+ tomada al cierre de esta sesión; si otra sesión de Fase 1
> colisiona, se renumera al merge (precedente #122–#128, #130–#133).
>
> **Base de la rama — decisión previa a todo lo demás**: `mejorado/generalidad`
> sale de **`mejorado/confianza-1` (@8f7145c)**, no de `mejorado/base`.
> `docs/specs/manifest-v2-sdk.md` §Consumen dice literalmente «G1/G2
> (capabilities nuevas nacen v2)», y el manifest v2 solo existe en C-1. C-1 es
> descendiente ESTRICTO de base (merge-base == punta de base), así que si
> control mergea C-1 primero esta rama entra sin divergencia. **Si control
> decidiera NO mergear C-1, esta rama hay que rebasarla y los 6 manifests
> nuevos vuelven a v1** — frontera declarada, no supuesto.

### #134 — G1: la receta C3 y sus tres hallazgos (nota KB 11 completa)

El STUB `knowledge/quantum/11-receta-c3-tfim-trotter.md` pasa a nota completa
al estilo de la 02 §1. Convención congelada:
`H = −J Σ Z_iZ_{i+1} − h Σ X_i` (cadena ABIERTA, J=1), quench desde |0⟩^⊗N,
t = 1.0, malla N∈{6,8,12} × h/J∈{0.5,1,2}. Todos los números de la nota se
computaron en vivo; ninguno se cita de memoria. Tres hallazgos que cambian
decisiones de implementación:

- **El orden 1 de Trotter converge O(dt²) aquí — y le GANA al orden 2.**
  Medido (N=8, h/J=1): razón de error ≈ 4.0 al partir dt en orden 1, y el
  orden 2 (Strang) da ~2× MÁS error a igual número de pasos. El mecanismo está
  verificado, no conjeturado: la corrección BCH líder es ∝ `i[A,B]`, operador
  hermítico **puramente imaginario** en la base Z, cuyo valor esperado sobre
  estados REALES se anula idénticamente (⟨ψ|i·M|ψ⟩ = i·ψᵀMψ = 0 con M real
  antisimétrico). Control que cierra el argumento: con estado inicial COMPLEJO
  el mismo conmutador vale **−2.000** (contra **+0.000e+00** en el real) y la
  razón de convergencia cae a **2.00** = O(dt). Consecuencias: **el circuito
  usa orden 1** (una capa RX por paso en vez de dos, y más preciso), y la
  relación metamórfica «razón ≈ 4 ⇒ orden 2» queda registrada como **FALSA en
  este montaje** — la cumple también el orden 1. Se llama
  `trotter_convergence_ratio` con esa semántica escrita; nombrarla «verifica el
  orden» sería un verificador que miente.
- **El criterio oficial «≤5%» está mal planteado leído por elemento**, porque
  los observables cruzan cero: a N=8, h/J=1, `⟨Z₀⟩ = −0.033022` contra
  `max_i|⟨Zᵢ⟩| = 0.343341` — un criterio por elemento sería **10× más
  estricto** en el sitio 0 que en el de máxima magnitud, por puro accidente.
  Definición CONGELADA: error relativo a la escala L∞ de la serie,
  `max_i|cand_i − ref_i| / max(max_i|ref_i|, 1e−12)`, evaluado **por separado**
  para ⟨Zᵢ⟩ y ⟨ZᵢZᵢ₊₁⟩, **ambas** ≤ 0.05.
- **Las dos series se verifican, no una.** En el punto más ordenado de la malla
  (h/J=0.5) con el control negativo r=2, la serie ⟨Zᵢ⟩ **pasaría** (0.04569 <
  0.05) y solo el correlador lo caza (0.07867). Un verificador de una sola
  serie daría un falso «pass» ahí.

Parámetros del corpus fijados con margen medido: **r = 16** (dt = 0.0625) deja
el peor punto de la malla (h/J=2) en 0.00903/0.00496, margen ~5.5× bajo el
criterio — suficiente para no depender de la versión de BLAS, ajustado para
seguir cazando regresiones. **Control negativo r = 2**: falla en los tres h/J.

### #135 — capabilities del reto 3: cero deps nuevas y una trampa de Qiskit

`blite.quantum.trotter_evolve` (proponente, circuito) y
`blite.numeric.exact_evolve` (ancla, `scipy.sparse.linalg.expm_multiply`)
entran como hermanas de los paquetes existentes — **sin tocar ninguna
dependencia**: reusan los extras ya declarados (`blite-cap-numeric[full]` ya
trae scipy; `blite-cap-quantum[qaoa]` ya trae qiskit). `uv.lock` byte-intacto,
verificado. Decisiones:

- **Wire genérico compartido** (ADR-029): el operador viaja como cadenas de
  Pauli con coeficientes y **el índice i, de izquierda a derecha, es el sitio
  i** — deliberadamente NO el little-endian de Qiskit; la inversión explícita
  (`label[::-1]`) vive del lado del circuito y tiene test propio con estado
  inicial ASIMÉTRICO (con `"00"` un bug de inversión global pasaría en verde).
  El TFIM, el barrido h/J y el protocolo de quench viven en `knowledge/` y en
  los datos — jamás en el manifest.
- **`PauliEvolutionGate` devuelve en silencio la exponencial EXACTA si el
  circuito no se transpila** — ignora `reps`. Sin `transpile(...)` previo, el
  control negativo (dt grande ⇒ debe divergir) habría pasado en verde para
  siempre y la «independencia proponente/verificador» habría sido decorativa.
  Documentado en el código; es el modo de fallo exacto que S-C §Contrato-3
  manda cazar.
- **El manifest jamás anuncia lo que `invoke` rechaza**: `trotter_evolve` NO
  declara `shots` porque no lo implementa (ver #137).

### #136 — verificadores C3: independencia POR ALGORITMO, con presupuesto declarado

`ExactDiagonalizationVerifier` (`formal_exact`/`solver`) y `GroundTruthVerifier`
(`ground_truth`/`dataset`), grupos de independencia distintos = las dos patas
que la policy C3 exige. Decisiones:

- **El ancla usa un algoritmo DISTINTO al de la capability**: diagonalización
  densa (`numpy.linalg.eigh`, la ED literal del enunciado) contra el Krylov
  disperso de `exact_evolve`. No es cosmético: ADR-008 prohíbe que el engine
  importe capabilities, así que la reimplementación era obligatoria — y se
  aprovechó para que además sea otro método. numpy se usa por estar garantizado
  vía `pandapower` (dependencia DIRECTA del engine que lo exige); pinearlo
  directo queda como follow-up para no mover `uv.lock`.
- **Presupuesto de dimensión declarado, no cambio silencioso de método**:
  `max_dense_dimension = 1024` (medido: eigh tarda 0.084 s a N=8 y **70 s con
  537 MB a N=12**). Por encima del presupuesto el verificador devuelve
  `inconclusive`/`budget_exhausted`/AL0 — **jamás cae a otro algoritmo**, que
  es justo lo que destruiría la independencia que esta clase promete. Ambos
  parámetros entran al `verifier_params_digest` (la letra de C-14: dos corridas
  con tolerancia distinta jamás comparten digest de params).
- **Consecuencia declarada**: el certificado del reto 3 se emite en **N=8** —
  que es el punto de referencia del propio enunciado — mientras el corpus y el
  experimento cubren la malla completa. Es el MISMO precedente que el reto 1
  (experimento sobre `ieee6-flujo`, certificado sobre `sintetica-4bus`).
  Certificar N=12 exige subir el presupuesto o una segunda ancla escalable.
- **`objective`/`reference_objective` del `Differential`** cargan (peor error
  relativo observado, 0.0) porque este claim no tiene UN objetivo escalar: son
  dos series. `pass ⟺ objective ≤ relative_tolerance` mantiene el par legible
  sin inventar campo nuevo.
- **Defecto encontrado en revisión y corregido**: el chequeo de digest del
  record de ground-truth era **circular** (recomputaba sobre los campos del
  propio record, así que jamás podía detectar manipulación del corpus) pero su
  mensaje decía «ancla envenenada». Se separan las dos preguntas: `source_digest`
  (digest del artefacto congelado, lo que el `anchor_digest` de la attestation
  debe portar) y el chequeo de integridad del record; la verificación del
  archivo del corpus ocurre al cargarlo, fail-closed.

### #137 — corpus C3 y el fix del drift código↔manifest

- **Corpus C3**: 9 puntos en `knowledge/tfim/corpus/`, identidad
  `tfim-corpus/chain-n<N>-h<h·10>@v1` — forma **adoptada, no elegida**: ya la
  congeló el fixture de costura de Fase 0
  (`predicate-ground-truth.json` pinnea `tfim-corpus/chain-n8-h10@v1`). Digest
  embebido self-consistente con el MISMO algoritmo del corpus de islanding.
  `scripts/verify_corpus_digests.py` se generaliza a varios directorios y gana
  la tabla pinneada `ESPERADOS_TFIM_C3`: **23/23 internos, 23/23 pinneados**.
- **Honestidad del generador**: el corpus se GENERA por la capability ED, así
  que la pata «serie congelada» y la pata «recompute vivo» son independientes
  por **algoritmo** (Krylov vs eigh) e **inmutabilidad**, no por método
  físico. La diversidad metodológica real del C3 llega con G6 (BdG analítico)
  — y ese checker cubre ⟨ZᵢZᵢ₊₁⟩, **no ⟨Zᵢ⟩** (operador de cuerda: exige
  Pfaffianos). Escrito ANTES de implementarlo para que nadie prometa AL4 sobre
  ⟨Zᵢ⟩ por esa vía.
- **Chequeo físico del generador**: a t=1 el valor de BORDE es independiente de
  N a 9 cifras (cono de luz de Lieb-Robinson) y el generador aborta si no lo
  es. El valor de BULK **sí** depende de N (N=6 difiere de N=12 en ~8e−4);
  la nota lo tabula. Un chequeo de N-independencia sobre el bulk habría estado
  mal planteado y habría pasado en verde por casualidad a h/J=2.
- **Hallazgo 12 del handoff S3 corregido**: el manifest de `blite.solvers.qubo`
  anunciaba el backend `"gurobi"` que `invoke` rechazaba. El enum y el guard
  salen ahora de UNA tupla (`_BACKENDS_SOPORTADOS`) y un test estructural
  recorre el enum invocando cada valor — el drift deja de ser posible, no solo
  deja de existir. El extra `gurobi` del pyproject queda como bundle de
  dependencia declarado, sin prometer despacho.
- **Corrección de un test frágil ajeno**: `TestVerifyCorpusDigestsGuard`
  pinneaba `"internos: 14/14"` — la misma fragilidad de cardinalidad que esa
  clase existe para prohibir, un piso más arriba. Pasa a assertar el
  INVARIANTE (todos self-consistentes, todos los pins coincidiendo) y la
  cobertura de ambos corpus.

### #138 — G3 dispatch por clase + G4 policies por reto: muere el Reto-1-only

**Dispatch (G3).** `resolve_verifiers(*, claim_type, instance_id)` conserva firma
y fail-closed; lo que muere es la FUENTE: `_OPTIMALITY_CLAIM_TYPES = {"solution"}`

- `ELECTRICAL_DATA` de un slug se reemplazan por `CLAIM_TYPE_VERIFIERS`, un
  registro declarativo donde cada entrada aporta constructor de claim + resolución
  de instancia. Reto 1 se re-expresa como la primera entrada, **compat total**
  (mismos `verifier:cpsat-differential` / `verifier:pandapower-islanding`, mismos
  grupos e ids). Decisiones propias:

- **`statistical` se registra VACÍO con `TODO(G2)`**, no con un verificador de
  mentira: la clave existe (el seed la exige) pero la resolución vacía sigue
  dando 400. Prometer una pata que no existe sería peor que no tenerla.
- **El corpus se verifica al CARGARLO, fail-closed**: slug validado por regex
  antes de tocar el filesystem (traversal), y el digest embebido del archivo se
  recomputa con la regla del corpus. Un corpus manipulado jamás llega a un
  verificador — y no puede convertirse en un `fail` que culparía al proponente
  por la corrupción del ancla.
- **Las dos patas C3 examinan el MISMO claim candidato**: un adapter privado
  traduce el `SimulationSeriesClaim` a `GroundTruthClaim`, en vez de pedirle al
  llamador que mande dos claims distintas (que podrían divergir).

**Cuerpo del claim (G3, parte 2).** `ClaimRequest` era Reto-1-only
(`instance` + `assignment` obligatorios). Gana `payload: dict | None` y un
validador que exige **exactamente una** forma: payload, o el par legacy — nunca
ambas, nunca ninguna. El par legacy se NORMALIZA a payload antes del dispatch,
así que río abajo hay **un solo camino**. `challenges/reto1/run_all.py` y los
tests existentes siguen mandando la forma legacy sin cambios.

**Policies (G4).** Dos plantillas versionadas nuevas
(`reto3-simulation.yaml`, `reto2-statistical.yaml`), cargables cada una por
separado, y COMPUESTAS en `verification-default.yaml` — «una policy por
distribución sigue siendo la forma» (S-C §Contrato-5). Bump a **0.3.0** con nota
de supersede en el estilo del `[S-F 2026-07-20]` existente; las reglas
`solution`/`intermediate` quedan byte-intactas. `policy_digest` cambia por
diseño; los bundles ya estampados conservan el suyo. Test nuevo: cada plantilla
debe ser byte-equivalente a su regla dentro de la policy compuesta — si no, las
plantillas driftean en silencio.

### #139 — CP2 VIVO: el reto 3 corre punta a punta

`challenges/reto3/run_all.py` (un solo comando, mismo patrón que reto 1). Medido
en esta sesión, no proyectado:

- **Malla completa del enunciado en verde**: los 9 puntos (N∈{6,8,12} ×
  h/J∈{0.5,1,2}) con Trotter orden 1, r=16, contra las series de ED del corpus:
  peor punto `chain-n*-h20` con err ⟨Zᵢ⟩ = 0.00903 y err ⟨ZᵢZᵢ₊₁⟩ = 0.00496
  (margen ~5.5× bajo el 5%).
- **Control negativo FALLA como debe** en los tres h/J (0.07867 / 0.32550 /
  1.03393). El script **aborta** si alguno pasa: un error chico con dt grande
  sería sospecha de código compartido, no un éxito.
- **Barrido de dt**: razón 4.46 → 4.10 → 4.03 → 4.01 (O(dt²), #134).
- **Certificado REAL**: misión → claim `simulation_result` → 2 verificadores
  (anclas `solver` + `dataset`) → `titular_level` **AL3**, veredicto
  **verified** → `check_bundle` **8/8** en proceso → `verify-bundle.py`
  **8/8 offline**. El certificado se emite en **N=8** por la causa de #136.

Gates al cierre de esta pieza: **1073 passed / 14 skipped / 21 xfailed /
4 xpassed, 91.88%**; **14 contratos kept, 0 broken**; ruff limpio; pyright 0;
guard de corpus **24/24 internos y pinneados**.

### Tabla de interacciones — sesión GENERALIDAD

| Interfaz tocada                                                                                       | Dominio afectado | Estado del contrato                                                      |
| ----------------------------------------------------------------------------------------------------- | ---------------- | ------------------------------------------------------------------------ |
| `Differential`: status `EXACT_DIAGONALIZATION` + `relative_tolerance` (C-14)                          | confianza        | ADITIVO — `CpSatStatus` intacto; seed de C-14 VERDE                      |
| `DifferentialStatus` exportado desde `blite.verification`                                             | confianza        | NUEVO — alias público                                                    |
| `blite.verification.exact_diagonalization` (verificador + `SimulationSeriesClaim`)                    | confianza        | NUEVO — `formal_exact`/`solver`, AL3 sin `proof`                         |
| `blite.verification.ground_truth` (+ `source_digest`, `build_ground_truth_record`)                    | confianza        | NUEVO — `ground_truth`/`dataset`; `anchor_digest` = digest del artefacto |
| `blite.verification.property_rule` (`PROPERTY_RULES`/`METAMORPHIC_RULES`)                             | confianza        | NUEVO — `property_rule`/`rule`, techo AL2 honesto                        |
| `CLAIM_TYPE_VERIFIERS` en `chimera_api.instance_verifiers`                                            | E (api)          | NUEVO — `resolve_verifiers` conserva firma y fail-closed                 |
| `ClaimRequest.payload` (+ `instance`/`assignment` opcionales, validador de forma única)               | E↔D              | ADITIVO — la forma legacy se normaliza; reto 1 sin cambios               |
| Entry points `blite.numeric.exact_evolve`, `blite.quantum.trotter_evolve`                             | B (capabilities) | NUEVOS — manifest v2, cero dependencias nuevas                           |
| Entry points `blite.ml.{tabular_prep,svm_precomputed,classifier_baseline}`, `quantum.fidelity_kernel` | B (capabilities) | NUEVOS — manifest v2, cero dependencias nuevas                           |
| `blite.solvers.qubo` — enum `backend` deja de anunciar `gurobi`                                       | B (capabilities) | CORREGIDO — hallazgo 12; enum y guard con UNA fuente                     |
| `distributions/chimera/policies/verification-default.yaml` 0.2.0 → **0.3.0**                          | distribución     | SUPERSEDE — `policy_digest` CAMBIA; reglas viejas byte-intactas          |
| `distributions/chimera/policies/reto{2,3}-*.yaml` (plantillas)                                        | distribución     | NUEVAS — cargables solas; byte-equivalentes a su regla compuesta         |
| `knowledge/tfim/corpus/` (9 puntos) y `knowledge/tabular/corpus/` (1 + CSV)                           | knowledge/datos  | NUEVOS — digests embebidos y pinneados                                   |
| `scripts/verify_corpus_digests.py` multi-directorio + `ESPERADOS_TFIM_C3`/`ESPERADOS_TABULAR_C2`      | invariantes      | EXTENDIDO — 24/24                                                        |
| `challenges/reto3/` (y `challenges/reto2/`)                                                           | producto         | NUEVOS — entry point único, mismo patrón que reto 1                      |

### #140 — CP3 vivo, y la comparación que estaba amañada

`challenges/reto2/run_all.py` cierra el reto 2 punta a punta sobre el corpus
COMPLETO (3276 filas, 5 folds, 27.6 s): folds sellados con `folds_digest`
emitido ANTES de cualquier `fit` (compromiso previo, Dwork et al.) → kernel de
fidelidad por statevector → SVM precomputado → baseline SVM-RBF CV-5 → McNemar
→ certificado `statistical` con anclas `dataset` + `rule` → `check_bundle` 8/8
→ `verify-bundle` **8/8 offline**.

**El hallazgo de la sesión.** La primera corrida concluía que el brazo cuántico
**superaba** al clásico con **McNemar p = 2.00e-15** y Δaccuracy = +0.0812. El
número era real; la conclusión, no. Los dos brazos no recibían los mismos datos:
el cuántico corría sobre `prepared` (4 features seleccionadas por importancia RF
ajustada en train, imputadas y escaladas a [0, π]) y el clásico sobre las 9
features CRUDAS, imputadas pero **sin escalar y sin selección**. Eso viola la
letra del baseline (`knowledge/quantum/07` §1.3: «el baseline directo: **mismo
pipeline**, kernel gaussiano») y convierte el McNemar en «pipeline preparado de
4 features vs pipeline crudo de 9», no en «kernel cuántico vs kernel RBF».

Corrección: `ClassifierBaseline` gana un modo `prepared_folds` para que los dos
brazos difieran SOLO en el kernel. Números reales tras la corrección:

| brazo                                                       | accuracy OOF |
| ----------------------------------------------------------- | ------------ |
| cuántico (kernel de fidelidad)                              | 0.6807       |
| clásico MISMO pipeline (certificado)                        | 0.6838       |
| clásico sobre features crudas (informativo, NO certificado) | 0.5995       |

**Δaccuracy = −0.0031, McNemar p = 0.4655 (b=81, c=71) ⇒ NO significativo ⇒ la
lectura correcta es «competitivo»**, jamás «supera». El p=2e-15 era artefacto
del confundido, y desapareció al igualar el preprocesamiento. Se conserva la
fila de features crudas como dato honesto — muestra que el preprocesamiento
aporta ~8 puntos, más que el kernel — pero **no participa del McNemar
certificado**: compararse contra ella confundiría kernel con preprocesamiento.

Guarda puesta para que el sesgo no vuelva en silencio: un test con fixture donde
las filas crudas no tienen NINGUNA señal sobre la etiqueta y `prepared_folds` sí
— si la capability alguna vez ignorara `prepared_folds` y reajustara desde
`rows`, la accuracy colapsaría de 1.0 a ~0.5 y el test lo caza.

λ_min del kernel antes de reparar: ~−4e−13 en los 5 folds (PSD por construcción
en statevector exacto, teorema de Schur); la reparación `clip` se aplica y se
REPORTA como dato, jamás en silencio.

### Handoff de la sesión GENERALIDAD — qué queda y qué NO se verificó

**Cerrado (con gates citados, no «debería pasar»).** Gates sobre la punta de la
rama al momento de escribir: **1098 passed / 14 skipped / 20 xfailed / 4 xpassed,
92.08%**; **14 contratos kept, 0 broken**; ruff limpio; pyright 0; guard de corpus
**24/24**. El seed `test_seed_generalidad_retos.py` quedó **completamente verde**
(sus 4 xfail retirados pieza por pieza: C-14 → verificadores → dispatch).

- **G1** (reto 3): receta KB 11, C-14, `trotter_evolve`/`exact_evolve`, corpus C3.
- **G3** (dispatch por clase) y **G4** (policies por reto, 0.3.0).
- **G2 parcial** (reto 2): las 4 capabilities, el corpus sellado y
  `PropertyRuleVerifier`.
- **G8 parcial**: el fix del drift enum de solvers (hallazgo 12).
- **CP2 vivo**: reto 3 punta a punta con certificado AL3 y `verify-bundle` 8/8.

**NO hecho — entra al handoff, con causa:**

| Ítem                                                                                   | Estado            | Causa                                                                                                                                                                                                                                                                                       |
| -------------------------------------------------------------------------------------- | ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **G5** (M11 baseline SA, `method:"sa"`)                                                | NO empezado       | `dwave-samplers` 1.8.0 está instalado (`neal` NO — el adapter va contra `dwave.samplers`). C-15 exige extensión COORDINADA de `baselines` (schema + tipo TS + fixture + chart en el MISMO checkpoint) y eso cruza al Studio; no cabía en el presupuesto de esta sesión sin dejarlo a medias |
| **G6** (doble ancla BdG, stretch)                                                      | NO empezado       | Declarado en la receta §2 con su alcance honesto: el checker de fermiones libres cubre ⟨ZᵢZᵢ₊₁⟩ pero **NO ⟨Zᵢ⟩** (operador de cuerda ⇒ Pfaffianos). Quien lo tome no debe prometer AL4 sobre ⟨Zᵢ⟩ por esa vía                                                                               |
| **G8** (reparación M.3/M.4 REGRID-QAOA + feasibility-feedback DFS + pesos desde flujo) | NO empezado       | Solo se hizo el fix del enum del mismo ítem                                                                                                                                                                                                                                                 |
| **DoD «contra compose»**                                                               | **NO verificado** | Ver abajo — es la brecha más importante de este handoff                                                                                                                                                                                                                                     |

**Brecha 1 — la verificación viva fue EN PROCESO, no contra compose.** CP2 (y CP3)
se verificaron con `TestClient` in-process + `check_bundle` + `verify-bundle.py`
offline. El DoD pide además el stack de `docker compose`. No se corrió, y hay una
razón estructural que quien lo intente debe conocer primero (brecha 2).

**Brecha 2 — los entry points nuevos NO están vivos en el venv local.**
`entry_points(group="blite.capabilities")` lee metadatos de la instalación, no el
código: los 6 entry points nuevos (`exact_evolve`, `trotter_evolve`,
`tabular_prep`, `fidelity_kernel`, `svm_precomputed`, `classifier_baseline`) no
aparecen hasta reinstalar los paquetes (`uv sync --locked --all-packages
--all-extras` tras el merge). Consecuencias concretas:

- `tests/invariants/test_capability_genericity.py` recorre entry points
  INSTALADOS ⇒ **hoy no escanea los 6 manifests nuevos**. Mitigación puesta en su
  lugar: cada capability nueva trae su propia clase `TestGenericitySelfCheck` que
  corre la denylist sobre su manifest serializado. No es lo mismo que el gate
  global: **al mergear, re-sincronizar y volver a correr el gate global** es
  obligatorio.
- El smoke 2.5 debe pasar de **13 a 19 entry points** en el contenedor. Si sigue
  diciendo 13, la imagen no se reconstruyó.

**Brecha 3 — tensión de la policy del reto 2 (AL2 vs AL3), heredada de la spec.**
`reto2-statistical.yaml` declara `min_level: AL3`, pero las DOS patas que S-C
§Contrato-3 prescribe para ese reto son `ground_truth` (techo AL3) y
`property_rule` (**techo AL2**, decisión #103). Como `titular_level =
mín(level_efectivo)`, cualquier claim `statistical` verificado por esas dos patas
queda en **AL2, jamás AL3**. El bundle igual pasa `check_bundle` 8/8 porque el
punto 7 exige `required_legs`/`required_anchors` pero **no** `min_level` — que es
exactamente el hallazgo **C15** ya en el backlog (`04-consolidacion.md` §7.2:
«una conclusión AL1 bajo regla AL3 pasa el punto 7»). Esta sesión **no** bajó el
`min_level` para que cerrara: se deja la contradicción visible. Las salidas son
(a) bajar la regla a AL2 con causa, (b) darle al reto 2 una tercera pata que
alcance AL3, o (c) resolver C15 primero y dejar que el punto 7 lo reporte. Es
decisión de la sesión de control, no de esta.

**Frontera 4 — la base de la rama.** Repetido aquí porque condiciona el merge:
esta rama sale de `mejorado/confianza-1`, no de `mejorado/base`. Si control
mergea C-1 primero, entra limpio; si no, hay que rebasar y los 6 manifests nuevos
vuelven a v1.

**Frontera 5 — honestidad del corpus C2.** El CSV oficial CC0 del reto no es
obtenible sin red en este entorno. El corpus es **sintético declarado**
(`procedencia: "synthetic_generated"`, con caveats explícitos en el propio
registro): todo claim es sobre ESE CSV sellado y nada dice del fenómeno del mundo
real. Cuando el CSV oficial aparezca, su digest supersede y **el pipeline no
cambia**, porque el corpus es DATO.

## Sesión control Mejorado — validación y merge de C-1 + G (rama `mejorado/base`, 2026-07-31)

### #141 — C-1 (CP4/CP5) y G (CP2/CP3) VALIDADOS Y MERGEADOS + decisión AL2 del reto 2

**Merge**: ff `bdde94e..60af544` (5 commits C-1 + 14 G; topología lineal
base→C-1→G — la dependencia de rama que G declaró se resolvió mergeando ambos en
orden). **Forense**: paths sensibles intactos; «diff del runtime = 0» de G
VERIFICADO (cero cambios engine runtime/gateway/events en su segmento); AX1
endurecido y jamás borrado; `uv.lock` byte-intacto; 116 archivos +18084/−306.

**Gates EN VIVO sobre el merge (tras `uv sync` — los 6 entry points nuevos no
viven sin reinstalar): 1116 passed / 9 skipped / 20 xfailed / 4 xpassed / cov
91.77%** · lint-imports **14 kept** (nuevo contrato layers gateway/runtime) ·
ruff 0 · pyright 0 · studio 227 · **19 entry points** en el venv · corpus guard
verde. Mejor que lo reportado por las sesiones (sus 14 skipped eran artefacto
del entorno worktree).

**Integración hecha por control al merge** (huecos menores):

1. **Gate de docs estaba ROJO en el árbol mergeado**: los 9 JSON del corpus TFIM
   son artefactos CONGELADOS que G no añadió a `.prettierignore` (+ `knowledge/
tabular/corpus/`, defensivo) — jamás se reformatean, el congelado manda; +
   formato menor en 4 md (prettier/markdownlint --fix). Docs gate VERDE.
2. **Decisión de Dylan — AL2 del reto 2**: `reto2-statistical.yaml` v0.2.1 y
   `verification-default.yaml` v0.3.1 bajan `min_level` AL3→AL2 (la verdad de
   HOY: la pata property_rule tiene techo AL2 congelado ⇒ AL3 era incumplible y
   C15 la volvería falla retroactiva). ASPIRACIÓN AL3 registrada en la plantilla
   (sube cuando exista 2ª pata AL3 — ruta #103 o ancla adicional). Tests de
   policy actualizados a los pins nuevos (17/17).
3. **Validación compose de G (CP2/CP3 contra compose, aprobada por Dylan):
   BLOQUEADA por entorno** — Docker no disponible en el WSL en este momento
   (Docker Desktop apagado/sin integración). C-1 SÍ validó CP4/CP5 contra
   compose desde su rama (smoke PASS + cruce con actor JWT vivo + 401).
   PENDIENTE-ENTORNO registrado: con Docker arriba, correr
   `docker compose build api && KEEP_STACK=1 bash scripts/smoke_infra.sh` —
   debe imprimir «capabilidades instaladas: 19» — + misión E2E. Es el único
   residuo del checkpoint.

**Pendientes de G con causa (registrados por la sesión)**: G5 (SA), G6 (doble
ancla BdG), G8 (REGRID) — siguen en el backlog del dominio G.

### Tabla de interacciones (regla #3)

| Interfaz tocada                                            | Dominio afectado | Estado del contrato                                   |
| ---------------------------------------------------------- | ---------------- | ----------------------------------------------------- |
| merge `mejorado/generalidad` (incluye C-1)→`mejorado/base` | TODOS            | ff limpio; gates vivos citados arriba                 |
| `.prettierignore` + corpus tfim/tabular congelados         | docs/infra       | VERDE — el congelado jamás se reformatea              |
| policies reto2 v0.2.1 / default v0.3.1 (`min_level` AL2)   | confianza        | SUPERSEDE con causa #141; bundles previos intactos    |
| Validación compose CP2/CP3                                 | infra            | PENDIENTE-ENTORNO (Docker apagado) — paso documentado |

## Sesión PRODUCTO-RUNTIME Mejorado — P1 frontera del proposer (rama `mejorado/producto-rt`, 2026-08-02)

### #142 — P1/M32 EJECUTADO: el seam del proposer deja de colgar runs, y el centinela muere

**El hueco.** `_run_agentic_turn` (`engine/src/blite/runtime/loop.py`) llamaba
`proposer(TurnContext(...))` SIN try/except. Un `raise` ahí propagaba la excepción
cruda fuera de `execute_run` — y `starlette.background.BackgroundTask.__call__`
tampoco atrapa nada — ANTES de journalizar ningún evento: el run quedaba en el
stream **sin terminal, para siempre**. Con el placeholder determinista eso no se
notaba (no puede fallar); con el agente real es el modo de falla NORMAL (miss de
replay, respuesta no parseable, red caída). Por eso bloqueaba todo M1.

**Lo ejecutado (dos guards, dos alturas).**

1. **Guard del proposer** (`loop.py`, la raíz): try/except alrededor de la llamada,
   con `plan.item_updated {status: failed, cause}` **ANTES** del terminal (orden
   #100.1 — jamás post-terminal, fuera del corte de `provenance_slice`, freeze §2) y
   `run.failed {error_kind: type(exc).__name__}`. El caso `step_id is None` del par
   resolve→invoke **no existe** acá: el proposer explota antes de que ningún step
   arranque, así que nadie más journalizó — `fail_run` es de este caller, exactamente
   una vez (test del turno tardío lo fija: `run.failed` cuenta 1).
2. **Guard de nivel TASK** (`chimera_api.runs.run_in_background`): último recurso para
   lo que escape de `execute_run` por una frontera que aún no tenga guard. Cierra el
   run con `run.failed` **solo si el stream no tiene terminal** — la comprobación es
   de este guard, no del writer (§2 solo rechaza `run.step.*`/`capability.job.*`
   post-terminales, así que un `run.failed` duplicado SÍ entraría). Nunca relanza: una
   tarea de fondo no tumba el worker; lo que no se puede escribir se registra con
   `logging.exception`, jamás se traga en silencio.

### #142.1 — la capability CENTINELA `PROTOCOL_VIOLATION_CAPABILITY_ID` MURIÓ (con causa)

`chimera_api.model_proposer` traducía toda falla del seam modelo a un `ProposedStep`
con una capability que ningún registry conoce, para que el turno cayera por el único
paso que YA era fail-loud (`registry.get` ⇒ `KeyError`). Era un rodeo del hueco de
arriba, y la propia `harness-agentico.md` lo anticipó literal: envolver la llamada
«volvería innecesaria la traducción a capability centinela».

Con el guard en la raíz, el rodeo se retira. **Por qué esto es estrictamente mejor
para la confianza** (el criterio que decide, no la comodidad):

1. **`error_kind` nombra la causa real** — `ReplayMissError` /
   `ModelResponseProtocolError` en el stream, en vez de un `KeyError` prestado que
   escondía qué falló de verdad.
2. **El rastro deja de fabricar un paso que nunca ocurrió** — el centinela provocaba
   un `run.step.*` de resolve contra una capability inexistente: evidencia inventada
   DENTRO del corte que el certificado ampara. Eso es un mock sin etiqueta en el
   plano de confianza, la regla dura #1 del plan paralelo.
3. **Un concepto menos**: el seam del proposer falla como cualquier otra frontera
   delegada del loop (`post_invoke` ya lo hacía así).

`parse_proposed_step` sigue siendo ESTRICTO — cambia a dónde va su excepción, no su
rigor. Efecto observable estampado en el test de integración
(`TestModoMisionProposerReal::test_replay_miss_falla_fail_loud_en_el_primer_turno`):
antes `1 run.step.started` + `error_kind: "KeyError"`; ahora **cero** `run.step.*` +
`error_kind: "ReplayMissError"`, con `plan.item_updated` inmediatamente antes del
terminal.

### Tabla de interacciones — P1

| Interfaz tocada                                                   | Dominio afectado | Estado del contrato                                                      |
| ----------------------------------------------------------------- | ---------------- | ------------------------------------------------------------------------ |
| `_run_agentic_turn` — guard del `proposer`                        | A (runtime)      | ADITIVO — cero cambio de firma; solo camino de error nuevo               |
| `chimera_api.runs.run_in_background` (+ ambos `add_task`)         | E (api)          | NUEVO — público para test; envuelve `execute_run`, sin cambio HTTP       |
| `chimera_api.model_proposer.PROTOCOL_VIOLATION_CAPABILITY_ID`     | E (api)          | **ELIMINADO** con causa (#142.1) — el adapter ahora es fail-loud         |
| `make_model_proposer` — deja escapar `ReplayMiss`/`ProtocolError` | E (api)          | CAMBIO OBSERVABLE — `error_kind` del stream nombra la causa real         |
| `docs/specs/harness-agentico.md` §"Frontera declarada"            | spec             | MARCA [MEJORADO P1/M32] — la letra histórica se conserva, manda la marca |

### #143 — P2/#104 EJECUTADO: skip honesto de lectura, sin tocar el camino de escritura

**El hueco (píldora #96, probado en vivo).** UN `run.created` sin `policy_digest`/
`max_steps` — payload que el freeze §3 declara obligatorio, así que
`_row_from_created` explota POR DISEÑO — tumbaba `GET /runs` entero con 500. Un
stream ajeno al pedido dejaba ciego al Studio completo.

**Lo ejecutado.** `chimera_api.reads._proyectar_salteando_envenenados` agrupa los
eventos POR STREAM y proyecta cada uno por separado, omitiendo el que explote.
Decisiones de diseño que importan:

- **`project_runs` se reusa TAL CUAL** — cero cambio de semántica en el fold del
  engine. El aislamiento vive en la ruta de lectura, que es exactamente donde #104
  autoriza el skip. Escritura, certificados y `provenance_hash` siguen fail-loud: un
  stream envenenado sigue reventando el recompute y cualquier emisión. Esta ruta lo
  REPORTA, no lo cura (línea roja de #104, literal).
- **`GET /runs` conserva su forma byte-idéntica** (array desnudo): lo único que cambia
  es que un stream envenenado se omite en vez de tumbar el listado. El reporte vive en
  la ruta hermana `GET /runs/discarded` con envelope OBJETO (#124: el array desnudo no
  admite un campo hermano sin romper E↔D).
- **`error_kind` reusa el vocabulario de `run.failed`** (`type(exc).__name__`), y
  `detail` es opcional legible. Vacío honesto `{"discarded_streams": []}` cuando no se
  descartó nada — jamás filas fabricadas.

**Fixture single-origin.** `get-runs-discarded.json` generado desde
`chimera_api.reads.DiscardedStreams` por `gen-contract-fixtures-endpoints.py` (que
gana el concepto REQUEST vs RESPUESTA: los de respuesta NO excluyen defaults, porque
el server sí emite el campo) + espejo byte-idéntico en el Studio + tres tests
anti-drift + **un cuarto test que corre la píldora contra el endpoint VIVO y compara
con el fixture** — si el wire y el fixture divergen, falla. El Zod espejo del Studio
entra con la rama live (frontera D, sesión P-ui).

**Seed a VERDE.** `tests/seeds/test_seed_lectura_discarded.py` pierde su `xfail` (los
3 casos pasan) y queda como regresión permanente de la píldora #96 — el test NO se
borra (ciclo SPEC→SEED→VERDE del README de specs).

### Tabla de interacciones — P2

| Interfaz tocada                                                   | Dominio afectado | Estado del contrato                                              |
| ----------------------------------------------------------------- | ---------------- | ---------------------------------------------------------------- |
| `GET /runs`                                                       | E↔D              | FORMA INTACTA — solo deja de morir por un stream ajeno           |
| `GET /runs/discarded` + `DiscardedStreams`/`DiscardedStream`      | E↔D              | NUEVO — envelope objeto, extensible; espejo Zod = frontera D     |
| `tests/fixtures/contract/endpoints/get-runs-discarded.json`       | E↔D              | NUEVO single-origin — espejo Studio byte-idéntico verificado     |
| `gen-contract-fixtures-endpoints.py` — casos REQUEST vs RESPUESTA | contratos        | EXTENDIDO — `serialize(case, payload)`; el caso viejo sin cambio |
| `blite.runtime.projection.project_runs`                           | A (runtime)      | **NO TOCADO** — línea roja de #104 respetada por construcción    |

### #144 — P3/M1 EJECUTADO: el chat real, y por qué NO hay tabla de mensajes

**El contrato S-A completo, lado engine/api.** Las 8 piezas del seed
(`test_seed_chat_conversacion.py`) pasan contra implementación real; el xfail se
retiró y el test queda como regresión permanente.

**La decisión estructural: el mensaje es un evento del MISMO stream.** No hay tabla
`conversations`/`messages` ni buffer paralelo — `blite.runtime.mission` deriva TODO
del log (`pending_messages_for`). Consecuencias que importan y que ningún producto
estudiado en el research R2 ofrece:

- la conversación que dirigió el run queda **DENTRO del `provenance_hash`**: el
  certificado ampara también lo que se PIDIÓ, no solo lo que se hizo;
- el replay reconstruye la cola leyendo el mismo stream en el mismo orden —
  determinista por construcción, sin estado que sincronizar;
- una segunda fuente de verdad habría roto el replay (research R2, literal).

**Queue-to-next-turn (§Contrato-5), verificado contra el loop real.** Un mensaje
journalizado a mitad del turno N aparece en el `TurnContext` del turno N+1 y jamás se
re-entrega (`TestDrenadoQueueToNextTurn` fija la secuencia exacta `[(1, ()), (2,
("cambiá de rumbo",)), (3, ())]`). Es la traducción del «safe boundary» del estado del
arte a la frontera que Chimera YA tenía: el límite de turno. Steer intra-turno queda
vetado por doctrina propia (freeze §8: reautorizar a mitad de step es error
fail-closed) — no es una limitación, es la garantía.

**`PROMPT_PROTOCOL` v2 (§Contrato-6).** La vista gana `messages` con el historial
completo en orden de stream. **`message_id` se EXCLUYE** por la MISMA razón que
`run_id` en v1: un id minteado por request haría que la clave de replay jamás
repitiera entre la sesión grabada y su reproducción. El historial se acumula en el
proposer (el loop entrega cada mensaje exactamente una vez) en vez de cargar dos veces
la misma información en `TurnContext`.

**Efecto colateral CORRECTO detectado por un test existente**: grabar una sesión con
otra misión ahora produce otro `prompt_digest` ⇒ el replay hace miss. No es un detalle
del test: una sesión grabada es de UNA conversación concreta. `_write_fake_session`
gana `mission`/`mission_author` para grabar la conversación real.

**Approvals (§Contrato-7).** Dos mitades:

- **Emisor**: puerto `ApprovalGate` inyectable en el loop (mismo patrón que `proposer`
  y `crossing`), consultado DESPUÉS de gobernar y ANTES de ejecutar. **Sin gate
  cableado no se emite nada** — cero aprobaciones fabricadas. Una aprobación negada
  corta el run con `cause` propia (`approval_denied`): es una decisión humana
  registrada, no un error del sistema.
- **Respuesta**: `POST /runs/{id}/approvals/{approval_id}` con cuatro compuertas
  fail-closed — 404 (request inexistente: nadie responde una pregunta que no se hizo),
  409 (par 1:1), 422 (el valor no valida contra el `json_schema` que el request
  DECLARÓ), 403 (`authorize_approval_response`, maquinaria §8/§10 reusada sin reabrir).

**Dos decisiones de diseño que conviene mirar:**

1. **`_APPROVAL_SCOPE = "run"`** (el conjunto es cerrado: `{run, domain, global}`). Es
   el más angosto que aplica. Consecuencia honesta y BUSCADA: el operador local por
   defecto no porta `override:apply:run`, así que responder un approval devuelve 403
   hasta que el despliegue otorgue el permiso explícito. Nadie aprueba por accidente.
2. **El payload de `approval.requested` se arma a mano en el loop** porque el contrato
   `layers` prohíbe `runtime→gateway` (mismo caso que `CrossingRejected`). Para que las
   dos mitades no se separen hay un test anti-drift que valida el dict REAL emitido
   contra `ApprovalRequestedPayload` (`extra="forbid"`: una clave de más o de menos
   revienta).

**Dependencia nueva declarada**: `jsonschema>=4.26` (MIT) en `api/pyproject.toml` —
estaba disponible transitivamente en el venv; ahora es una dependencia REAL y no un
accidente. Escribir un validador propio sería reimplementar un estándar.

**Frontera que queda declarada (no entregada)**: cómo se ESPERA la respuesta humana
—bloquear el worker, suspender el run, reanudar por cola— es del adapter, no del loop.
Con `BackgroundTasks` un gate bloqueante retiene un hilo; la casa natural del gate que
espera de verdad es la cola durable (P11/`JobQueue`).

### Tabla de interacciones — P3

| Interfaz tocada                                                     | Dominio afectado | Estado del contrato                                                 |
| ------------------------------------------------------------------- | ---------------- | ------------------------------------------------------------------- |
| `blite.runtime.mission` (`MissionMessagePayload`, `PendingMessage`) | A (runtime)      | NUEVO — materializa la reserva `●MissionMessage` del §14            |
| `TurnContext.pending_messages`                                      | A (runtime)      | ADITIVO default `()` — compat total con el loop sin chat            |
| `execute_run(thread_id=, project_id=, approval_gate=)`              | A (runtime)      | ADITIVOS — `run.created` omite los `None`, payload byte-igual       |
| `ApprovalGate`/`ApprovalRequest`/`ApprovalDecision`                 | A (runtime)      | NUEVO puerto — sin gate inyectado es no-op                          |
| `approval.requested` emitido por el loop                            | A ↔ gateway      | wire congelado REUSADO — anti-drift por test, no por import         |
| `POST /runs/{id}/messages`                                          | E↔D              | NUEVO — 202/404/409/422; `author` de la identidad                   |
| `POST /runs/{id}/cancel`                                            | E↔D              | NUEVO — evento ya congelado, faltaba emisor (N1)                    |
| `POST /runs/{id}/approvals/{approval_id}`                           | E↔D              | NUEVO — valida contra el `json_schema` del request; 403 fail-closed |
| `MissionRequest.thread_id`/`project_id`                             | E↔D              | ADITIVOS — `extra="forbid"` intacto                                 |
| `PROMPT_PROTOCOL` v1 → **v2**                                       | E ↔ proposer     | SUPERSEDE de la constante — sesiones v1 siguen reproduciendo        |
| `make_model_proposer(mission=, mission_author=)`                    | E (api)          | ADITIVO — siembra el primer mensaje del historial                   |
| `jsonschema>=4.26` (MIT)                                            | deps             | NUEVA declarada — antes solo transitiva                             |

### #145 — P4/M31 EJECUTADO: la llamada de modelo deja rastro, y el replay se puede auditar

**Cuatro huecos encadenados, cerrados en orden.**

**1 · `model.call.*` no los emitía NADIE.** El vocabulario está congelado en el freeze
§3 desde el día uno (`requested {backend_id, local, prompt_digest}` →
`completed {response_digest} | failed {error_kind}`) y la llamada de modelo era **el
único efecto del sistema sin rastro propio**. Ahora `chimera_api.model_proposer` los
emite vía un `emit` inyectado (mismo patrón que un delegate `post_invoke` recibe
`recorder.append` — el adapter no conoce el store, lo recibe). El `failed` cierra el
rastro cuando la llamada revienta: sin él un `requested` quedaría colgado sin
desenlace, que es justo lo que este par existe para evitar.

**2 · `find_replay_divergences` era infraestructura sin uso.** El núcleo (A5) existía
con un `Recomputer` inyectable y nadie que lo inyectara — porque sin (1) no había
efectos de modelo que emparejar. `chimera_api.replay_fidelity` cierra el circuito:
`session_recomputer` arma el recomputador contra el manifest de una sesión usando la
MISMA derivación de `replay_key` que el backend `replay` en producción, y
`check_run_fidelity` corre la comprobación sobre el stream. Con esto, «el certificado
verifica ⟺ el replay fue fiel» deja de ser prosa: un test estampa que una respuesta
cambiada produce un `replay.divergence` tipado con los tres digests.

**Frontera honesta declarada**: el recomputador de `capability_job` NO vive ahí.
Recomputar un job es re-ejecutar la capability (posibles efectos) — decisión de
política. Se levanta `UnrecomputableEffectError` en vez de fabricar un digest: **un
check que no se pudo hacer no es un check que pasó.**

**3 · `SessionManifest` gana `version` + `entries_digest`.** El freeze §15.7 punto 4
manda que «el SET de fixtures se pinnea por digest — el modo grabación no puede mutar
la config del demo en silencio». Se verificaba cada respuesta INDIVIDUALMENTE pero
nada miraba el conjunto: **quitarle o agregarle entradas a una sesión pasaba
inadvertido**. Ahora `load_session` recomputa el digest del set (canonicalización
única del proyecto, orden-independiente) y falla fail-loud. `version` convierte una
sesión de formato futuro en un error legible en vez de una carga a medias.
`entries_digest` vacío ⇒ sesión anterior al campo: se carga, sin esa garantía —
compat DECLARADA, no silenciosa.

**4 · Config: key por archivo y fail-fast del `record` efímero.**

- `CHIMERA_MODEL_API_KEY_FILE` → env var (misma disciplina `*_FILE` del compose). Una
  key en env se filtra por `docker inspect`, por `/proc/<pid>/environ` de cualquier
  proceso del contenedor y por los volcados de crash. La env var explícita GANA sobre
  el archivo: quien la exporta a mano está depurando.
- **`CHIMERA_MODEL_BACKEND=record` en la API ahora FALLA al arrancar.** El manifest de
  `record` vive en memoria y quien lo dumpea a disco es `scripts/record_session.py`,
  no la API: un operador que arrancara el servicio creyendo que graba estaría quemando
  llamadas de modelo REALES —con su costo— para tirarlas al reiniciar. Escape hatch
  explícito: `CHIMERA_ALLOW_EPHEMERAL_RECORD=1`.

**Runbook de grabación (listo; la grabación real queda BLOQUEADA-POR-DYLAN).** Con la
key de Dylan, desde la raíz del repo:

```bash
export CHIMERA_MODEL_API_KEY_FILE=/ruta/segura/model.key   # nunca la key en el comando
uv run python scripts/record_session.py \
  --session-dir knowledge/sessions/<nombre> \
  --mission "<la misión textual>" \
  --instance-id cr8-uniforme \
  --model-id anthropic/claude-sonnet-4-5 \
  --max-turns 3
```

Produce `manifest.json` (con `version` y `entries_digest` estampados) + `responses/`.
Reproducir: `CHIMERA_MODEL_BACKEND=replay CHIMERA_MODEL_SESSION_DIR=<dir>`.
**Cuidado registrado**: la vista del prompt es v2 y el historial incluye la misión con
su `author` — grabar con OTRA misión (o con otro operador) produce otro
`prompt_digest` y el replay hace miss. Una sesión grabada es de UNA conversación
concreta; eso es correcto, no un bug.

### Tabla de interacciones — P4

| Interfaz tocada                                     | Dominio afectado | Estado del contrato                                                     |
| --------------------------------------------------- | ---------------- | ----------------------------------------------------------------------- |
| `model.call.requested/completed/failed` EMITIDOS    | E ↔ stream       | wire congelado §3 — primera emisión, cero forma nueva                   |
| `make_model_proposer(emit=)`                        | E (api)          | ADITIVO — sin `emit` no se emite nada (tests intactos)                  |
| `chimera_api.replay_fidelity`                       | E (api)          | NUEVO — conductor de `find_replay_divergences`                          |
| `SessionManifest.version`/`entries_digest`          | E (api)          | ADITIVOS con default — sesiones viejas cargan (compat declarada)        |
| `load_session` valida versión y digest del conjunto | E (api)          | ENDURECIDO — antes el set no se verificaba                              |
| `CHIMERA_MODEL_API_KEY_FILE`                        | infra/config     | NUEVA — `*_FILE` como el resto del compose                              |
| `CHIMERA_MODEL_BACKEND=record` en la API            | infra/config     | **ROMPE a propósito** — escape hatch `CHIMERA_ALLOW_EPHEMERAL_RECORD=1` |

### #146 — P5/M27 EJECUTADO: la autoridad 2 por fin tiene artefacto

La autoridad 2 del criterio (#101) —«un externo instala y usa la plataforma sin
nosotros al lado»— era la única de las tres **sin ningún entregable**. Ahora tiene
cuatro, y uno de ellos corrigió un defecto real.

**1 · `scripts/generate-secrets.sh`.** El compose ya era `*_FILE`-only (más estricto
que el referente Supabase del research R2) pero no había forma de PRODUCIR esos
archivos: un tercero clonaba y chocaba con un `postgres_password.txt` inexistente sin
saber qué poner. Tres decisiones de diseño: **jamás sobreescribe** (rotar es explícito,
no un efecto de correr setup dos veces), **600 desde el nacimiento** vía `umask` (no un
`chmod` posterior que deje una ventana legible), y aleatoriedad del sistema (nunca una
contraseña de ejemplo «temporal» que termine en producción). Verificado corriéndolo dos
veces: crea 600 la primera, respeta la segunda.

**2 · `docs/QUICKSTART.md` — 5 minutos que TERMINAN en `verify-bundle` offline.**
Ningún referente estudiado cierra su quickstart con evidencia criptográfica (research
R2): ese es el momento diferenciador. Incluye el paso de **adulterar el bundle a
propósito** y ver la verificación fallar — el argumento del producto entero en dos
comandos. **Los 8 puntos citados son la salida REAL** (corrida sobre
`scripts/example-bundle.json`), no una maqueta: la primera versión de este doc inventó
etiquetas plausibles y se corrigieron contra la ejecución. El demo de adulteración
también se ejecutó: falla en `[1/8] firma/PAE del envelope`, tal como se documenta.

**3 · `docs/USO.md`.** Qué es cada pieza, qué significan los niveles AL0-AL4 («que un
resultado sea AL2 y no AL3 no es una falla: es información»), las dos formas de lanzar
trabajo, cómo traer un problema propio — y una sección **«lo que hoy NO hace»** con las
cuatro limitaciones reales (sin multi-tenancy, cola no cableada, aprobaciones necesitan
permiso explícito, revocación no implementada). Preferimos decirlas antes que dejar al
tercero descubrirlas a los tropiezos.

**4 · `docker compose up` ARREGLADO — y el diagnóstico corrige una suposición mía.**
El servicio `worker` no era «inerte e inofensivo» como escribí primero: el comentario
del propio compose ya decía que **FALLA al arrancar** (`procrastinate worker` sin app
registrada). O sea, el primer `docker compose up` de alguien que recién llega mostraba
un contenedor en crash-loop sin ninguna pista de que era esperado — la autoridad 2 rota
por una razón puramente cosmética. **Solución: perfil `queue`.** Compose no arranca
servicios con `profiles:` salvo que se pidan, así que `up` levanta el stack que de
verdad funciona y el worker espera a P11. Se saca el perfil cuando la cola exista, no
antes: un servicio declarado de primera clase que crashea es peor que uno honestamente
apagado.

**5 · `install-dev.sh` deja de escribir en `~/.claude` sin preguntar** (N10). Escribía
en un directorio de configuración PERSONAL, fuera del repo, desde un script llamado
«install-dev». Ahora es opt-in: bandera `--with-claude-agent`, env
`INSTALL_CLAUDE_AGENT=1`, o responder el prompt. **En no-interactivo (CI) se salta por
defecto**: sin TTY nadie pudo consentir.

**6 · `.env.example` completo** con las dos variables nuevas de P4
(`CHIMERA_MODEL_API_KEY_FILE`, `CHIMERA_ALLOW_EPHEMERAL_RECORD`), cada una con la razón
por la que existe.

### Tabla de interacciones — P5

| Interfaz tocada                            | Dominio afectado | Estado del contrato                                                                 |
| ------------------------------------------ | ---------------- | ----------------------------------------------------------------------------------- |
| `scripts/generate-secrets.sh`              | infra            | NUEVO — idempotente, 600 al nacer, nunca sobreescribe                               |
| `docs/QUICKSTART.md`                       | producto         | NUEVO — salida de verify-bundle VERIFICADA, no citada de memoria                    |
| `docs/USO.md`                              | producto         | NUEVO — incluye límites reales declarados                                           |
| `compose.yaml` — `worker` → perfil `queue` | infra            | **CAMBIO DE COMPORTAMIENTO**: `up` ya no intenta arrancarlo (arregla el crash-loop) |
| `scripts/install-dev.sh`                   | infra/dev        | CAMBIO — el efecto en `~/.claude` es opt-in; CI lo salta                            |
| `.env.example`                             | infra/config     | COMPLETADO — las 2 vars de P4 documentadas con su porqué                            |

### #147 — hallazgo 7: la ruta fantasma `/invoke` se MATA (no se implementa), con causa

**El hallazgo.** `apps/studio/src/gatewayClient.ts` exportaba `invokeCapability()`, que
posteaba a `POST /invoke`; `docker/studio-nginx.conf` proxeaba ese prefijo al api; y
**ningún servidor implementaba la ruta**. Verificado antes de decidir: el único caller
de esa función en todo el repo era su propio test — cero componentes del Studio la usan
(el camino real de datos es `POST /runs` + SSE, por el mismo módulo).

**La decisión: matarla.** El criterio no es «es código muerto» (que también), sino la
autoridad 3:

> Implementarla habría creado una **SEGUNDA vía de invocar una capability que evade
> run, claim y verificación** — un resultado sin evidencia, sin attestation y sin
> certificado. Eso contradice de frente la doctrina fail-closed que sostiene el
> diferenciador («jamás un run sin verificación», decisión #7). Una ruta que produce
> resultados sin rastro no es una funcionalidad faltante: es un agujero en el plano de
> confianza que por suerte nadie había cavado todavía.

**Lo retirado, en cascada** (cada pieza verificada sin lectores antes de tocarla):

1. `invokeCapability()` + `GatewayRequest` (`gatewayClient.ts`) y sus 3 tests;
2. el prefijo `invoke` del `location` de nginx — proxear lo que nadie sirve es
   superficie de ataque gratis y una pista falsa para quien lea la config;
3. **`VITE_GATEWAY_URL`** y su constante `GATEWAY_BASE_URL`: existían ÚNICAMENTE para
   armar esa URL (todas las funciones vivas usan `apiBaseUrl`/`VITE_API_URL`). Se
   retiran de `compose.yaml`, `docker/studio.Dockerfile` y `.env.example` — **una env
   var documentada que nadie lee es documentación de una mentira**.

**El ancla del Invariante 1, reapuntada.** `docs/invariants.md` anclaba INV-1 (gateway
como chokepoint) a `gatewayClient.ts::invokeCapability` — o sea, el invariante estaba
anclado a la función muerta. Ahora apunta a `GatewayResponse`, el tipo que TODAS las
funciones de egress devuelven: **el invariante lo sostiene que todo egress cruce ESE
módulo, no una función en particular.** El ancla es más fuerte después del cambio, no
más débil.

**El test de nginx se ACTUALIZA, no se borra**: `test_nginx_conf_proxies_los_prefijos_
vivos_y_ninguno_mas` fija los dos prefijos vivos **y** que `invoke` no reaparezca.

### Tabla de interacciones — hallazgo 7

| Interfaz tocada                                   | Dominio afectado | Estado del contrato                                           |
| ------------------------------------------------- | ---------------- | ------------------------------------------------------------- |
| `POST /invoke`                                    | E↔D              | **MUERTA** con causa — jamás existió del lado servidor        |
| `gatewayClient.invokeCapability`/`GatewayRequest` | D (studio)       | ELIMINADOS — `GatewayResponse` y el resto del módulo intactos |
| `docker/studio-nginx.conf` `location`             | infra            | `^/(invoke\|runs\|health)` → `^/(runs\|health)`               |
| `VITE_GATEWAY_URL` (compose/Dockerfile/.env)      | infra/config     | RETIRADA — sin lectores tras (1)                              |
| ancla INV-1 en `docs/invariants.md`               | confianza        | REAPUNTADA a `GatewayResponse` — más fuerte, no más débil     |

### #148 — P11: el puerto `JobQueue` — `interaction: job` por fin tiene dónde correr

**El hueco.** El manifest v2 congela `interaction: job` y `execution_profile:
remote-job` (freeze §1), pero `ProfileDispatcher` los rechazaba con
`NotImplementedError`: el vocabulario existía y **no tenía casa**. La dependencia
(`procrastinate`, en `engine/pyproject.toml`) y el servicio (`worker` del compose)
estaban pagados desde el MVP, sin nadie detrás.

**Lo entregado — el puerto, hexagonal como el resto.** `blite.runtime.jobs`:

- **`JobQueue`** (Protocol `runtime_checkable`): `enqueue(capability_id, inputs) ->
job_id`. Se encola la **id**, no el objeto: el worker la resuelve contra SU registry
  — mandar la capability exigiría serializar código, justo lo que el patrón de entry
  points evita.
- **`RemoteJobStrategy`**: devuelve `JobRef`, **nunca** un `Result`. Encolar no es
  ejecutar; un trabajo que va a tardar no puede fingir haber terminado. La capability
  NO se invoca en este proceso (test lo estampa: `invocaciones == 0`).
- **`InMemoryJobQueue`**: respaldo etiquetado con honestidad — NO es durable, no
  reintenta, no sobrevive al proceso. Existe para ejercitar la costura sin base de
  datos (mismo rol que `InMemoryReplayManifest` para el modelo).
- **`ProfileDispatcher(remote_job=...)`**: inyección ADITIVA. **Sin cola inyectada,
  `remote-job` sigue siendo `NotImplementedError`** — un despliegue sin cola no puede
  fingir que corre trabajos largos (nota execution/06 §6: tratar `remote-job` como
  síncrono es EL modo de falla que este diseño evita). Hay test de regresión.

`blite.runtime` no importa `procrastinate` — mismo principio que `ModelPort` con
litellm (AX3-b): la casa legítima del SDK está afuera del runtime.

**Lo que NO se entregó, y por qué (frontera declarada).** El **adapter Procrastinate
concreto** y el flip del perfil `queue` del compose quedan pendientes: registrar la app
y probar que un worker levanta y consume exige **Postgres vivo**, y el entorno de esta
sesión no tiene Docker (misma restricción que dejó pendiente el compose de G). Escribir
el adapter sin poder ejecutarlo sería entregar código no verificado en la pieza cuyo
único valor es que corra de verdad. El puerto —que es la decisión arquitectónica— está
cerrado y probado; el adapter es mecánico detrás de él.

### Tabla de interacciones — P11

| Interfaz tocada                          | Dominio afectado | Estado del contrato                                          |
| ---------------------------------------- | ---------------- | ------------------------------------------------------------ |
| `blite.runtime.jobs` (`JobQueue` + cía.) | A (runtime)      | NUEVO puerto — cero imports de procrastinate en el runtime   |
| `ProfileDispatcher(remote_job=)`         | A (runtime)      | ADITIVO — sin cola, `NotImplementedError` intacto            |
| adapter Procrastinate + perfil `queue`   | infra            | **PENDIENTE-ENTORNO** — exige Postgres vivo para verificarse |

### #149 — la corrida VIVA cazó un 500 que 1157 tests verdes no vieron

**Qué pasó.** El DoD pedía «un run live con proposer que falla muere con `run.failed`
(jamás colgado)». Con Docker apagado (mismo bloqueo de entorno que G), se levantó un
**uvicorn real** —no `TestClient`, que corre los `BackgroundTasks` INLINE y por eso no
ejercita el camino que P1 arregla. El run live salió perfecto:

```
run.created · run.started · plan.created · model.call.requested ·
model.call.failed · plan.item_updated · run.failed {error_kind: "ReplayMissError"}
```

Eso valida de una sola vez P1 (el proposer levantó y el run MURIÓ en vez de colgarse,
con `plan.item_updated` antes del terminal), P4 (`model.call.*` emitidos, con el
`failed` cerrando el efecto) y la muerte del centinela (`error_kind` nombra la causa
REAL, cero `run.step.*` fabricados).

**Pero `GET /runs` respondió 500.** Traceback:
`AttributeError: 'dict' object has no attribute 'encode'` en `canonicalize`.

**Causa raíz (PREEXISTENTE, no de esta sesión).** `PlanCreatedPayload.model_dump()`
devuelve `items` como **tupla** (el campo se declara `tuple[PlanItem, ...]` para ser
inmutable). `canonicalize` —anexo CONGELADO— implementa el modelo de datos JSON y solo
trata `list`: la tupla caía en la rama de objeto e intentaba `.encode()` sobre cada
ítem. Efecto: el certificado de **cualquier run de misión** explotaba, y con él el
listado entero.

**Por qué 1157 tests verdes no lo vieron.** El store Postgres serializa a JSON en el
camino (la tupla vuelve como lista); **solo el store en memoria conservaba el tipo
Python**. Es una divergencia in-memory ↔ Postgres: la clase de bug que ningún test de
unidad con store en memoria puede cazar solo, porque el test y el defecto comparten el
mismo entorno.

**El arreglo, en la ÚNICA puerta de escritura.** `_RunRecorder.append` normaliza a JSON
nativo (`_json_native`) antes de tocar el store. Se eligió ahí y no en cada call site
porque cubre a todos los emisores presentes y futuros, y porque la propiedad que de
verdad faltaba es que **ambos stores guarden lo mismo**. La canonicalización congelada
no se toca: se le entrega la entrada válida que su contrato siempre exigió. Test de
regresión: todo payload del stream es canonicalizable y ningún valor es tupla.

**Segunda mitad de #104, encontrada por el mismo camino.** Mi skip honesto de P2 envolvía
la PROYECCIÓN, pero el 500 venía de `_run_summary` (ensamblado del certificado) — o sea
`GET /runs` seguía pudiendo morir por un run ajeno al pedido, que es exactamente el
defecto que #104 cierra, una capa más abajo. Ahora ambas mitades están cubiertas y las
DOS rutas (`/runs` y `/runs/discarded`) salen del **mismo cómputo**: si divergieran, el
reporte dejaría de explicar lo que el listado omitió.

**Verificación posterior al fix, en vivo:** `GET /runs` → **200** con el run listado;
`GET /runs/discarded` → `{"discarded_streams": []}` (vacío honesto: ya no hay nada que
descartar). Códigos del chat contra el servidor real: `messages` sobre terminal **409**,
`cancel` sobre terminal **409**, `cancel reason=parent_cancelled` **422**, `messages` a
run inexistente **404**, `approvals` sobre terminal **409**.

**Hallazgo de arnés (para la próxima sesión en worktree).** La receta de gates en
worktree tiene un punto ciego: **pyright resuelve `blite` desde el editable del repo
PRINCIPAL**, no desde el `include` del worktree, así que un módulo NUEVO del worktree
(`blite.runtime.mission`, `blite.runtime.jobs`) le resulta irresoluble a los tests y sus
errores de tipo pasan inadvertidos. Se corrige con un `pyrightconfig.json` en el
worktree que declare `extraPaths` a sus `src` (excluido localmente vía
`.git/info/exclude` — jamás commiteado: lleva rutas absolutas de la máquina).

### Tabla de interacciones — #149

| Interfaz tocada                          | Dominio afectado | Estado del contrato                                            |
| ---------------------------------------- | ---------------- | -------------------------------------------------------------- |
| `_RunRecorder.append` — normaliza a JSON | A (runtime)      | **FIX de bug preexistente** — payloads del stream JSON-nativos |
| `canonicalize` (anexo congelado)         | confianza        | **NO TOCADO** — recibe la entrada válida que siempre exigió    |
| `GET /runs` — skip cubre el resumen      | E↔D              | ENDURECIDO — segunda mitad de #104                             |
| `/runs` y `/runs/discarded`              | E↔D              | UN solo cómputo — el reporte no puede divergir del listado     |

### Handoff de la sesión PRODUCTO-RUNTIME — qué queda y qué NO se verificó

**Gates al cierre** (worktree `mejorado/producto-rt`, 8 commits sobre `mejorado/base`
@c4b44a5, sin push):

| Gate                           | Resultado                                                |
| ------------------------------ | -------------------------------------------------------- |
| `pytest`                       | **1166 passed**, 14 skipped, **9 xfailed**, 4 xpassed    |
| cobertura                      | **91.62 %** (mínimo exigido 30 %)                        |
| `lint-imports`                 | **14 contratos kept, 0 broken**                          |
| `ruff check`                   | limpio                                                   |
| `pyright`                      | **0 errores** (con `extraPaths` del worktree — ver #149) |
| `pnpm -C apps/studio test:run` | **224 passed** / 27 files                                |
| `pnpm -C apps/studio lint`     | limpio                                                   |

Baseline al abrir: 1111 passed / 20 xfailed. Los **11 xfailed que desaparecieron** son
los seeds S-A y S-B puestos en verde (chat 8 + lectura descartada 3) — ninguno borrado:
quedan como regresión permanente de su contrato.

**Alcance cerrado**: P1, P2, P3, P4, P5, P11 y la ruta fantasma `/invoke` (hallazgo 7).

**NO cerrado — P12 (ingesta RAG/KB con procedencia DSSE).** No se empezó, y la razón es
de coordinación, no de tiempo: el enunciado la declara **«coordina con O»**, y la sesión
O no se ha lanzado. La frontera SÍ está congelada y es precisa (freeze §7: contenido
recuperado entra como `assumptions[{statement, ref{name, digest}}]`, **jamás** como
`Attestation` ni dentro de `conclusions`), y hay dos insumos previos
(`capabilities/ingesta/`, `docs/research/arquitectura-ingesta-kg-fase2.md`). Sugerencia
para quien la tome: el pedazo de mayor valor y menor acoplamiento es **volver ejecutable
la frontera** —un guard que impida que contenido recuperado termine en `conclusions` o
como `Attestation`— antes de construir el retrieval; hoy esa regla solo vive en prosa.
El freeze también avisa un delta real: bajo `replay`, la llamada de embeddings del
retrieval **es** una llamada de modelo y necesita sus propios fixtures (mismo patrón
§15.7) — con P4 esto ya es más barato, porque `model.call.*` se emite de verdad.

**Bloqueado por entorno (no por decisión):**

1. **CP1 completo** exige el lado D (sesión P-ui, no lanzada). Lo verificable sin ella
   —el wire E: `mission.message` en el stream, `run.cancelled`, approvals, códigos
   409/422/404— quedó verificado en vivo (#149).
2. **Compose**: Docker no está disponible en este WSL (mismo bloqueo que dejó G). Con
   Docker: `docker compose up -d --build` debe levantar **postgres + api + studio**
   (el `worker` YA NO arranca por defecto — perfil `queue`, ver #146) y
   `bash scripts/smoke_infra.sh` sigue siendo el checkpoint. **El DoD de fondo —«un run
   live con proposer que falla muere con run.failed, jamás colgado»— SÍ se verificó**,
   contra un uvicorn real (no `TestClient`), que es donde el camino de `BackgroundTasks`
   se ejercita de verdad (#149).
3. **Grabación de la sesión real (P4)**: bloqueada-por-Dylan (necesita su API key). El
   runbook quedó listo y probado en su parte mecánica (#145), con el aviso de que la
   vista v2 incluye la misión y su autor: grabar con otra misión produce otro digest.

**Fronteras que dejo declaradas para la sesión de control:**

- **`ApprovalGate` sin adapter**: el puerto existe y el loop lo consulta, pero **cómo se
  ESPERA la respuesta humana** (bloquear el worker, suspender, reanudar por cola) es del
  adapter. Con `BackgroundTasks` un gate bloqueante retiene un hilo: su casa natural es
  la cola durable (P11), cuyo **puerto** ya está cerrado y probado.
- **Adapter Procrastinate + flip del perfil `queue`**: pendientes por entorno (exige
  Postgres vivo). El puerto —la decisión arquitectónica— está cerrado; el adapter es
  mecánico detrás de él.
- **`api/src` fuera del `include` de pyright**: al incluirlo aparecen **45 errores
  preexistentes** que el gate del repo nunca revisó. No los toqué (cambiar el alcance de
  un gate es decisión de plataforma/O, no mía), pero conviene saberlo: hoy el tipado
  estricto **no** cubre el API.
- **`docs/USO.md` §8 declara cuatro límites reales** (sin multi-tenancy, cola no
  cableada, approvals requieren permiso explícito, revocación no implementada). Si
  alguno se cierra, ese doc es el que hay que actualizar — es lo que un tercero lee.

### #150 — verificación VIVA contra el compose real: dos defectos propios y un gate ampliado

Con Docker disponible se corrió el stack REAL (`docker compose up -d --build`) y se usó la
plataforma como la usaría un tercero. **Encontró dos defectos que ningún test veía — los
dos en entregables MÍOS de P5.**

**Defecto 1 · `generate-secrets.sh` rompía el quickstart en el paso 3.** El script creaba
los secretos en **600**; los contenedores corren como usuario NO-root (`chimera`, uid 999)
y el compose los monta por bind-mount, así que el api moría con
`cat: /run/secrets/postgres_password: Permission denied`. La secuencia que yo mismo
documenté —generar secretos, `docker compose up`— **fallaba**. Corregido a **644 con el
directorio en 700**: la protección del host la da el directorio (ningún otro usuario puede
atravesarlo), y el contenedor puede leer. La alternativa (`chown 999` en el host) es peor:
deja el archivo ilegible para el desarrollador. La causa quedó escrita en el script para
que nadie lo "arregle" de vuelta a 600.

**Defecto 2 · el QUICKSTART prometía 8/8 con un ejemplo que da 7/8.** El comando de ejemplo
usaba una instancia de juguete (`par-minimo`, 2 nodos) fuera del corpus: solo la ampara UN
verificador, y la política de la distribución exige **2 patas independientes** para esa
criticidad. Resultado real: `[7/8] FALLA — 1 pata(s) por independence_group < 2 exigidas`.
Los 8/8 que yo citaba salían de `scripts/example-bundle.json` —un bundle guardado—, **no
del flujo que el propio doc manda correr**. Un tercero habría concluido que la plataforma
no cumple lo que promete. Corregido: el ejemplo usa `sintetica-4bus` (instancia del corpus,
dos patas reales) y el doc **explica** que una instancia inventada da 7/8 a propósito —
«eso no es la plataforma rota, es la política haciendo su trabajo». La tabla de
troubleshooting gana esa fila y la del secreto.

**Evidencia viva recogida (todo contra el compose, no contra `TestClient`):**

| Qué                                              | Resultado                                                                                                                             |
| ------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------- |
| `docker compose up -d`                           | postgres healthy + api healthy + studio; **el `worker` NO arranca** (perfil `queue` de #146 funcionando)                              |
| entry points dentro de la imagen                 | **19** (checkpoint de C-1/G confirmado sobre imagen reconstruida)                                                                     |
| `smoke_infra.sh`                                 | postgres healthy · `/health` ok · 19 capabilities                                                                                     |
| `test_postgres_event_store.py` vs Postgres real  | **8 passed**                                                                                                                          |
| run claim-first `sintetica-4bus`                 | 2 × `verification.completed` → certificado → **`verify-bundle` 8/8**                                                                  |
| bundle adulterado (1 byte de la firma)           | **falla [1/8]**, 7/8 — exactamente lo que el doc promete                                                                              |
| `POST /runs/{id}/messages` sobre run EN VUELO    | **202**, y el `mission.message` queda journalizado a mitad del stream, con el actor de la sesión (`user:local-operator`), NO del body |
| el mismo POST segundos después (run ya terminal) | **409** — el rechazo post-terminal del §2, en vivo                                                                                    |
| `GET /runs` / `GET /runs/discarded`              | 3 runs con status y AL correctos / `{"discarded_streams": []}`                                                                        |
| Studio por nginx                                 | `/` → 200 · proxy `/runs` → 200 · **`POST /invoke` → 405** (la ruta fantasma también murió en el proxy)                               |

Un run de misión sobre `blite.quantum.qaoa` falló con `GatewayRejection {stage: mediation}`
porque la capability rechazó los inputs — **camino fail-loud correcto**, no defecto: el
arranque HTTP nunca falla por un error DENTRO del run.

**Gate ampliado: `api/src` entra a pyright.** Era el único paquete de PRODUCCIÓN fuera del
tipado estricto — se revisaba el runtime y el SDK, y no la capa que atiende HTTP. Destapó
26 errores, todos resueltos en el mismo cambio: 15 eran el falso positivo de FastAPI
(`reportUnusedFunction` sobre handlers que registra el decorador — silenciado per-file con
su causa, no apagando la regla en el resto del proyecto) y 11 huecos reales de tipado al
recorrer payloads en `reads.py` (resueltos con `cast` DESPUÉS del `isinstance`, así que la
comprobación en runtime sigue siendo real).

**Hallazgo para P-ui (no lo toco: es su alcance).** `docker/studio-nginx.conf` proxea
`^/(runs|health)` al api, así que **nginx es dueño del prefijo `/runs`**: cualquier ruta
de cliente bajo `/runs` sería tragada por el proxy y el SPA nunca cargaría en un deep-link.
Hoy no hay choque (el Studio aún no tiene router) y el árbol planeado
`/w/:ws/p/:proj/runs/:id/:tab` lo esquiva por construcción — pero si P7 pasa por un paso
intermedio con `/runs/:id/:tab` al tope, colisiona. Verificado en vivo:
`GET localhost:3000/runs/x/y` → 404 del API, no `index.html`.

**Nota de entorno (no es del repo):** `~/.docker/config.json` declara
`"credsStore": "desktop.exe"`, binario que no existe en esta distro WSL — cualquier build
que deba resolver metadatos de una imagen base falla con `error getting credentials`. Se
sorteó con un `DOCKER_CONFIG` limpio y temporal, sin tocar la config del usuario.

### Tabla de interacciones — #150

| Interfaz tocada                           | Dominio afectado | Estado del contrato                                                  |
| ----------------------------------------- | ---------------- | -------------------------------------------------------------------- |
| `scripts/generate-secrets.sh` — modo 644  | infra            | **FIX** — el quickstart fallaba en el paso 3 con 600                 |
| `docs/QUICKSTART.md` — ejemplo de 2 patas | producto         | **FIX** — el ejemplo anterior daba 7/8; ahora 8/8 verificado en vivo |
| `[tool.pyright] include` += `api/src`     | gates            | AMPLIADO — 26 errores destapados y resueltos                         |
| `reads.py` — tipado de payloads           | E (api)          | ENDURECIDO — `cast` tras `isinstance`, runtime intacto               |

### #151 — el quickstart corrido EN LIMPIO: de cero a certificado verificado

Tras los fixes de #150 se destruyó todo (`docker compose down -v`, secreto borrado) y se
ejecutó `docs/QUICKSTART.md` **literal, paso por paso**, como un tercero recién llegado.
Sin atajos, sin pasos extra, sin editar nada a mitad:

| Paso del doc                       | Resultado real                                                      |
| ---------------------------------- | ------------------------------------------------------------------- |
| 2 · `generate-secrets.sh`          | secreto creado 644 dentro de `secrets/` 700                         |
| 3 · `docker compose up -d --build` | volumen y red nuevos; **api healthy en ~13 s**; `worker` no arranca |
| 4 · el `curl` documentado          | 202 + **2 `verification.completed`** (las dos patas)                |
| 5 · certificado + `verify-bundle`  | **8/8 puntos verificados**, exit 0                                  |
| 5b · bundle adulterado             | **FALLA [1/8]**, exit 1                                             |
| Studio                             | `GET localhost:3000` → 200                                          |

**La autoridad 2 del criterio #101 —«un externo instala y usa la plataforma sin nosotros
al lado»— queda demostrada con evidencia, no con prosa.** Y la demostración vale
precisamente porque la primera pasada NO funcionó: el paso 3 moría por permisos y el paso
5 daba 7/8. Un quickstart que nadie ejecuta en limpio es una promesa sin verificar.

## Sesión PRODUCTO-STUDIO (worktree `mejorado/producto-ui`, 2026-08-03/04)

**Rama base: `mejorado/producto-rt` @08d9fbb, NO `mejorado/base`.** Decisión de esta
sesión, registrada porque cambia cómo mergea la de control: P-rt cerró SIN merge y CP1
es explícitamente un checkpoint de DOS lados (P-rt ↔ P-ui). Ramificar desde `base`
habría obligado a fabricar el lado E para probar el lado D — exactamente el mock
silencioso que la regla 1 prohíbe. **El merge de CP1 lleva ambas ramas juntas.**

### Decisiones tomadas con Dylan

| #   | Decisión                                                                                                                                                                                                                                                                                                                                                                                                                  |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| P7  | **Router = TanStack Router.** Mismo ecosistema que `@tanstack/react-query` (ya instalado), params y search params tipados de verdad + validación Zod nativa — el stack ya es TanStack+Zod. Descartados: React Router v7 (`useParams` tipado por aserción, no real) y wouter (sin anidamiento de primera clase, que es justo lo que el árbol #78 necesita). **Propuesta hecha ANTES de instalar, como mandaba el prompt.** |
| P8  | **M16 branding = BLOQUEADO-POR-DYLAN.** Las 21 referencias visuales no están disponibles; la decisión red-de-nodos vs 3-barras y el sistema de marca NO se toman a ciegas. El ítem sale del alcance de esta sesión con causa, no por olvido.                                                                                                                                                                              |

### Tabla de interacciones (interfaces tocadas)

| Interfaz                                           | Dominio afectado | Estado del contrato                                                           |
| -------------------------------------------------- | ---------------- | ----------------------------------------------------------------------------- |
| `mission.message` ↔ `missionMessageSchema`         | A↔D              | **CERRADO** — fixture single-origin + Zod espejo + parse test                 |
| `POST /runs/{id}/messages`                         | E↔D              | **VIVO** — 202/409/422/404 verificados contra compose                         |
| `POST /runs/{id}/cancel`                           | E↔D              | **VIVO** — 422 del `parent_cancelled` reservado verificado                    |
| `POST /runs/{id}/approvals/{id}`                   | E↔D              | CABLEADO — card inline + 403 `override:apply:run` mostrado tal cual           |
| `POST /runs` (envelope)                            | E↔D              | **CORREGIDO** — el server responde `{run_id}` pelado, no envelope (ver abajo) |
| `run.created.thread_id`                            | A↔E↔D            | **VIVO** — enhebrado Studio→API→stream verificado                             |
| `NewRunInput` `{instance,proposer}` → misión libre | D                | ROTO A PROPÓSITO — consumidor único (`App.tsx`), migrado en el mismo commit   |
| `RunThreadModel.checklist` → `.entries`            | D                | ROTO A PROPÓSITO — consumidor único (`RunThread`), tests migrados             |
| `GatewayResponse` gana `status?`                   | D                | ADITIVO — sin él, 409/403/422 colapsan a un mensaje genérico                  |
| `KNOWN_RUN_EVENT_TYPES` += chat                    | E↔D              | ADITIVO — la whitelist es ahora exportada y verificada contra los fixtures    |

### Defectos propios cazados (dos por corrida viva, uno por el gate)

1. **`postRun` esperaba un envelope que el API nunca envió.** `POST /runs` responde el
   wire crudo `{run_id}` (`CreateRunResponse`); el cliente lo casteaba a
   `GatewayResponse`, así que `success` salía `undefined` y **crear un run desde el
   Studio en modo live SIEMPRE fallaba con «No se pudo crear el run» aunque el run se
   creaba**. Lo grave no es el bug: es que los tests estaban VERDES porque el mock
   devolvía un envelope — el doble codificaba un contrato que el servidor no cumple.
   Solo apareció al correr el Studio real contra el API real. **Es la regla 2 del plan
   paralelo justificándose sola.**
2. **El anti-drift de fixtures del harness tenía un hueco estructural.**
   `tests/unit/contract/test_harness_contract_fixtures.py` parametriza sus 3 tests sobre
   `_MODELS`, un espejo A MANO de `_cases()` del generador: un caso nuevo quedaba sin
   guard, en silencio y con la suite en verde. Pasó con `mission-message`. Cerrado con
   un cuarto test que compara ambos conjuntos.
3. **Los fixtures del Studio nombraban `capability.job.invoked`**, un evento que el
   servidor jamás emitió (hallazgo 4 del handoff S3). Traducidos, y la whitelist del
   cliente pasa a exportarse para que un test la compare contra los fixtures.

### CP1 — VERIFICADO VIVO contra compose (2026-08-04)

Stack del worktree (`mejorado-producto-ui-{postgres,api,studio}`), imágenes construidas
desde esta rama. Wire E verificado con `curl`; lado D conducido en el navegador real:

| Comprobación                                                        | Resultado                                             |
| ------------------------------------------------------------------- | ----------------------------------------------------- |
| `POST /runs` con misión de TEXTO LIBRE                              | 202 `{run_id}` — sin plantilla en el body             |
| `POST /runs/{id}/messages` en stream vivo                           | **202** `{message_id}`                                |
| `mission.message` en el stream, en orden de log                     | **SÍ** — entre `capability.job.submitted` y `.failed` |
| `POST /runs/{id}/messages` sobre stream terminal                    | **409** con el texto del freeze §2                    |
| `text` vacío                                                        | **422**                                               |
| `cancel` con `reason: "parent_cancelled"` (reservado a la cascada)  | **422**                                               |
| run desconocido                                                     | **404**                                               |
| Studio: hilo con misión + plan + **mensaje sucesivo** + cierre      | **SÍ** (captura y snapshot de accesibilidad)          |
| Studio: stream terminal ⇒ sin compositor + «Continuar en run nuevo» | **SÍ**                                                |
| Studio → `POST /runs` → `run.created.thread_id` journalizado        | **SÍ** — `thread_id: run-cd74980f…` en el evento      |

**Lo que NO se verificó vivo y por qué:** la card de approval no se ejercitó contra un
`approval.requested` real — el loop no emitió ninguno en estas corridas (el run muere
antes, en `GatewayRejection`). Su contrato está cubierto por tests contra los fixtures
de costura, pero **el par vivo queda pendiente** para quien tenga un run que pida
aprobación. Se declara, no se disimula.

**Hallazgo lateral (no arreglado, fuera de alcance):** un run fallido dispara
`GET /runs/{id}/certificate` → 409, que aparece como error de consola en el navegador.
Es honesto (un run fallido no tiene certificado) pero ruidoso: el Studio pide el
certificado incondicionalmente. Candidato a no pedirlo cuando el run no es `completado`.

### Handoff de la sesión PRODUCTO-STUDIO — qué queda y qué NO se verificó

**Gates al cierre** (worktree `mejorado/producto-ui`, 11 commits sobre
`mejorado/producto-rt` @08d9fbb, sin push):

| Gate                            | Resultado                                         |
| ------------------------------- | ------------------------------------------------- |
| `pytest`                        | **1197 passed**, 14 skipped, 9 xfailed, 4 xpassed |
| cobertura                       | **91.5 %** (mínimo exigido 30 %)                  |
| `lint-imports`                  | **14 contratos kept, 0 broken**                   |
| `ruff check`                    | limpio                                            |
| `pyright`                       | **0 errores**                                     |
| `pnpm -C apps/studio test:run`  | **299 passed** / 32 files                         |
| `pnpm -C apps/studio lint`      | limpio                                            |
| `pnpm -C apps/studio typecheck` | limpio                                            |

Baseline al abrir: pytest 1166 / studio 224 en 27 files.

**Alcance cerrado**: P3-D, P6 (parcial — ver abajo), P7, P9, P10, P13 y los
hallazgos 4/5/6 del handoff S3.

#### Cómo reproducir las verificaciones vivas (para la sesión de control)

Los gates de esta sesión se corren con la receta de worktree (python del venv
del repo PRINCIPAL + `PYTHONPATH` del worktree; `uv sync` en un worktree no
instala los editables). Las tres corridas vivas, en orden de valor:

```bash
# 1 · CP7 offline — el checklist completo sobre el bundle vigente
python scripts/verify-bundle.py scripts/example-bundle.json          # 12/12, exit 0

# 2 · Custodia real (C8) — la llave vive en OpenBao, no en el proceso
docker compose --profile custody up -d openbao
scripts/openbao-init.sh                    # inicializa, desella, crea las 3 llaves
# luego: TransitKeyProvider(address=..., token=secrets/transit_token.txt)
#        → assemble_bundle(key_provider=...) → check_bundle 12/12

# 3 · Hash-chain durable (C5) — contra Postgres real
#     create_event_store(DSN) y comprobar prev_hash/hash + provenance_slice
```

**Trampa operativa (verificada en carne propia):** las sesiones paralelas
levantan SU compose con los MISMOS puertos publicados (5544 postgres, 8000
api, 3000 studio). Con `chimera-plataforma` arriba, `docker compose up` en
este worktree falla con «port is already allocated» — no es un defecto del
compose. Para verificar contra Postgres sin pelear por el puerto, se levanta
un contenedor aparte en otro puerto con `engine/sql/init_v2.sql` montado, o se
coordina el turno con la otra sesión. El perfil `custody` publica 8200 y el
`transparency` 3003: mismo cuidado si dos sesiones los usan a la vez.

#### Lo que NO se cerró, con causa

1. **P8/M16 branding — BLOQUEADO-POR-DYLAN.** Las 21 referencias visuales no
   están disponibles. La decisión red-de-nodos vs 3-barras y el sistema de
   marca 16px NO se tomaron a ciegas: es la decisión más subjetiva del alcance
   y hacerla sin el material que la informa habría producido algo que hay que
   rehacer. Se retoma cuando lleguen.
2. **P6/M15 — la fila relacional `project` NO existe.** El resto de P6 sí está
   (selector honesto, colapsable, bloque de usuario real vía `GET /me`).
   **Es ceremonia, no olvido**: la tabla vive en `engine/sql/init_v2.sql`, que
   está bajo candado bidireccional doc⊆SQL⊆doc
   (`tests/invariants/test_esquema_migration.py`) contra
   `docs/esquema-datos-v2.md` — SEMILLA v2 gobernada por `contract-freeze.md`.
   Crear la tabla exige editar un doc CONGELADO con ceremonia registrada, que
   el plan reserva a la sesión de control.

   **DDL propuesto** (para que la ceremonia tenga algo concreto que ratificar):

   ```sql
   CREATE TABLE projects (
       id          TEXT PRIMARY KEY,
       domain_id   TEXT NOT NULL REFERENCES domains (id),
       name        TEXT NOT NULL,
       created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
   );
   ```

   Fuera del event store, como manda S-A §Contrato-4: `run.created.project_id`
   es referencia OPACA y el evento no valida FK — la valida el API al crear el
   run. El Studio ya está listo para consumirla: `AppShell` acepta
   `projects`/`onProjectChange` y solo dibuja el selector con dos o más, y el
   router ya lleva el `:proj` en la URL. **P6 se termina llenando datos, sin
   reescribir rutas ni vistas.**

3. **P10 — no verificado VIVO.** El endpoint de archivos y la vista Papers
   están completos y con gates verdes (19 tests propios: 11 del adapter + 8 de
   las rutas), pero la corrida contra compose quedó sin hacer. Comando exacto
   para cerrarlo:

   ```bash
   docker compose build api studio && docker compose up -d
   curl -X POST http://localhost:3000/files -H 'Content-Type: application/pdf' \
        -H 'X-Filename: paper.pdf' --data-binary @archivo.pdf
   curl http://localhost:3000/files
   ```

4. **La card de approval no se ejercitó contra un `approval.requested` real.**
   El loop no emitió ninguno en las corridas de esta sesión (el run muere antes,
   en `GatewayRejection`). Su contrato está cubierto contra los fixtures de
   costura; el par vivo queda pendiente para quien tenga un run que pida
   aprobación.

#### Dos agujeros de seguridad propios, encontrados y cerrados (2026-08-04)

Un review de seguridad sobre el commit de P10 encontró **dos defectos reales en
código de esta sesión**. Ambos corregidos con test de regresión antes de cerrar:

1. **XSS almacenado en el MISMO origen que el Studio.** `GET /files/{digest}`
   devolvía el `Content-Type` que había declarado quien subió el archivo, y
   `/files` se proxea en el origen del Studio: un HTML subido se servía como
   HTML y ejecutaba **con la cookie de sesión adjunta** — podía crear runs o
   responder approvals en nombre del usuario. Que la cookie sea `HttpOnly` no
   ayuda: el navegador la manda sola. Cerrado con tres capas (neutralizar los
   tipos activos, `Content-Disposition: attachment`, `nosniff`) más saneo del
   nombre, que venía de un header del cliente y volvía en otro (CRLF ⇒ header
   splitting).
2. **Aislamiento de dominio roto por colisión.** `_domain_dir` saneaba el
   `domain_id` con reemplazos — una función **con pérdida**: `acme:prod` y
   `acme/prod` caían en el mismo directorio y el SO2 se evaporaba sin que nada
   fallara, justo la propiedad que ese adapter existe para cumplir. Y `..`
   sobrevivía al filtro intacto (salida del root). El directorio pasa a ser el
   `sha256` del `domain_id` y además se comprueba el dominio del metadato al
   leer: un aislamiento que depende de UNA comprobación se rompe entero cuando
   esa comprobación falla.

**La lección, porque se repite:** las dos veces el código _parecía_ implementar
la doctrina y hasta la citaba en su docstring. La sanitización con `re.sub` se
lee como una defensa y es un colador; el `media_type` guardado se lee como un
metadato y es una instrucción para el navegador.

#### Fronteras declaradas para la sesión de control

- **La rama sale de `mejorado/producto-rt`, no de `mejorado/base`.** CP1 es un
  checkpoint de dos lados y P-rt cerró sin merge; ramificar desde `base` habría
  obligado a fabricar el lado E para probar el lado D. **El merge de CP1 lleva
  ambas ramas juntas.**
- **`scripts/smoke_infra.sh` no corre desde un worktree**: usa `uv run`, y el
  `.venv` de un worktree no tiene los editables (gotcha conocido). Sus pasos se
  corrieron a mano con la receta de worktree y dieron verde; el script sigue
  sirviendo desde el repo principal. Arreglarlo es de plataforma (O).
- **`resources.content` sigue siendo `InMemoryContentStore`.** El adapter
  durable ya existe (`blite.content_fs`) y habla el mismo puerto, así que
  migrar la evidencia de los runs a disco es un cambio de una línea de
  cableado — pero cambia el plano de CONFIANZA (la evidencia dejaría de
  evaporarse al reiniciar) y merece decisión propia, no colarse en producto.
- **El flip a 401-obligatorio** que `test_auth_session.py` declara «frontera
  P-ui» no se hizo: hoy sin cookie se cae a la identidad del operador local.
  Cambiarlo rompe el flujo sin sesión y no estaba en el alcance enumerado.
- **Un run fallido dispara `GET /runs/{id}/certificate` → 409** y aparece como
  error de consola en el navegador. Es honesto (un run fallido no tiene
  certificado) pero ruidoso: el Studio pide el certificado incondicionalmente.
  Candidato a no pedirlo salvo `status === 'completado'`.

### #152 — CP1 (P-rt + P-ui) VALIDADO Y MERGEADO + primer push de Mejorado

**Fecha:** 2026-08-04. **Sesión de control.** Validación rápida a pedido de
Dylan (sin auditoría profunda: los dos lados de CP1 ya estaban verificados
VIVOS y registrados en #142–#151 + bloque P-ui).

**Merge:** fast-forward `c4b44a5..c95aeb9` (27 commits: 13 de
`mejorado/producto-rt` + 14 de `mejorado/producto-ui`, cadena lineal). Las dos
ramas entran JUNTAS porque P-ui ramificó desde P-rt — exactamente el diseño de
CP1 (checkpoint de dos lados). Tras el merge, TODAS las ramas de sesión de la
fase (contratos, confianza-1, generalidad, saneamiento, producto-rt,
producto-ui) son ancestros de `mejorado/base`.

**Gates vivos en el repo principal sobre el árbol mergeado** (regla de control:
los números de sesión no se heredan, se re-corren):

| gate                  | resultado                                             |
| --------------------- | ----------------------------------------------------- |
| `uv run pytest`       | **1209 passed / 9 skipped / 9 xfailed / 4 xpassed**   |
| cobertura             | **91.62%**                                            |
| `uv run lint-imports` | 14 contratos kept, 0 broken                           |
| `uv run ruff check`   | 0                                                     |
| `uv run pyright`      | 0 errores (con `api/src` ya en el include, #150)      |
| studio `test:run`     | **299 passed / 32 files**                             |
| studio `lint`         | 0 warnings                                            |
| `docs:lint`           | 0                                                     |
| `format:check`        | verde tras formatear `docs/specs/harness-agentico.md` |

El único rojo del árbol combinado era prettier sobre `harness-agentico.md`
(spec VIVA editada por P-rt; verificado sin pin de digest — la única referencia
es un docstring). Se formateó. Requirió `uv sync --locked --all-packages
--all-extras` por el paquete nuevo `chimera-distribution` (P9).

**Push AUTORIZADO por Dylan** (este registro): trabajará el paso 3 en paralelo
desde otra máquina. Se publica `mejorado/base` a origin por primera vez (vía
HTTPS/gh, regla del repo) — contiene toda la fase hasta acá.

**Hereda al backlog, con causa (del handoff P-ui):** P8 branding
(bloqueado-por-Dylan), fila `project` de P6 (CEREMONIA sobre
`docs/esquema-datos-v2.md`, DDL propuesto arriba), P10 sin verificación viva,
card de approval sin par vivo, P12 (espera sesión O), y tres fronteras que
piden decisión propia: content store durable (plano de confianza), flip
401-obligatorio, certificado 409 ruidoso en Studio.

**Veredicto:** el paso 2 del plan está COMPLETO. Quedan por lanzar C-2 (Fable),
V y O — paso 3, paralelizable.

> **[merge · 2026-08-10] Colisión de numeración materializada.** Las sesiones
> VISUAL y PLATAFORMA corrieron en paralelo y ambas numeraron desde **#153**.
> Las dos secciones se conservan íntegras —el ledger es append-only— y la
> **renumeración la resuelve la sesión de control**, que además tiene que
> contar con la sesión C-2 cuando integre. Hasta entonces, un `#1XX` de esta
> zona hay que leerlo junto al nombre de su sesión, no solo por su número.
> Ver `docs/mejorado/08-handoff-plataforma.md` §3.1.

## Sesión VISUAL/CIENCIA (worktree `mejorado/visual`, 2026-08-05)

Dominio V de `docs/mejorado/04-consolidacion.md` §4. Mandato: **los
honest-empty del Studio mueren DONDE exista productor real** — el énfasis es
de la sesión, no una licencia para fabricar el productor.

### #153 — V1/M18: el productor de partición y la convención de branch-ids C-8

**Qué faltaba, exactamente:** el payload de mapa estaba fijado por contrato
desde trust/07, la ruta de lectura lo esperaba (`reads::_project_topology`), el
Zod espejo existía y el fixture de costura estaba generado — y NADIE lo
emitía. El honest-empty no era falta de diseño: era un cable que nunca se
conectó.

Decisiones de esta sesión (analizadas contra la letra, no inventadas):

1. **La convención canónica de branch-ids vive en el SDK**
   (`blite_capability.branch_ids`), no en el engine ni en la capability. Es lo
   único que ambos lados deben producir BYTE-IDÉNTICO, y ADR-008 declara
   `blite_capability` como la única interfaz compartida. Una copia por lado
   sería el drift que C-8 cierra.
2. **`edge_id_property` exige estrategia 1:1 feature↔arista.** Con
   `endpoint-name-match` (que AGREGA paralelas) se rechaza en frontera: un id
   del portal por rama agregada sería una mentira sobre N features. La mitad
   canónica queda para esos casos.
3. **Los ids canónicos son DERIVADOS, no estampados.** El corpus ya sellado no
   se re-etiqueta ni cambia de digest — quien lo consuma recomputa los mismos
   ids con la misma función. Por eso la receta de `geojson_to_graph` NO sube de
   versión al ganar el campo.
4. **`build_partition` devuelve `None` sin checks por isla.** Un badge por isla
   derivado del veredicto global sería el mock silencioso que la regla 1 del
   plan prohíbe. Y una isla nunca reporta MÁS nivel que la attestation que la
   ampara.
5. **`ABSTENTION_CHECKS` pasa a ser DATO en `execution.py`.** Estaba enterrada
   en el flujo de `verify()`; quien LEE la attestation después necesita la
   misma regla para no leer una abstención como un fail.
6. **`StructuralPartitionVerifier` (AL2, ancla `rule`) — decisión de alcance.**
   La red real del ICE no trae impedancias, así que pandapower no puede correr
   sobre ella y sin checks `island-{k}:*` no hay badges posibles. La salida
   honesta no era inventar dato eléctrico: es verificar lo que el grafo SÍ
   permite (conectividad por isla, corte no vacío) con el techo que le
   corresponde. Entra **solo** donde no hay dato eléctrico registrado — donde
   pandapower corre, sumarla inflaría las patas del punto 7 sin aportar un
   método realmente nuevo.

**M23a/N3 cerrado:** el orquestador hilvana el `step_id` que el loop siempre le
pasó. La evidencia por paso deja de llegar `attestations: []`; el test que
afirmaba ese defecto ahora afirma el arreglo.

### #154 — V2/M19: el cierre métrico existe, y se DERIVA del log

**El choque C-4 en una frase:** el evento estaba congelado con campos de
confianza, el consumidor esperaba campos científicos por variante, y nadie lo
emitía.

- **Las métricas se derivan del stream, no se acumulan en memoria.** Por eso el
  orquestador estampa `latency_ms` por attestation: un tercero que replaye el
  log obtiene los mismos números; un acumulador del proceso emisor no ofrece
  eso.
- **`false_reject_proxy` se DEFINE en vez de fabricarse:** de los claims que
  alguna pata rechazó, qué fracción otra pata independiente aceptó. La
  medición fuerte (contra corpus de óptimos conocidos, trust/05 §1.3) es el
  ítem O8 y se dice en el código, no se aproxima con un número inventado.
- **`AblationMetric` importa el enum del emisor** en vez de repetir el
  `Literal`: extensión coordinada de los 4 espejos (Pydantic, Zod, tipo TS,
  chart), disciplina C-15.
- **`AblationArm` no tiene campo de policy:** la herencia fail-closed de §13
  regla 3 queda garantizada POR CONSTRUCCIÓN. Comparar brazos bajo exigencias
  distintas no sería una ablación.
- **La agregación de brazos es de LECTURA:** `GET /runs/{id}/ablation` suma los
  sub-runs directos; cada brazo conserva su stream, su procedencia y su propia
  respuesta.

### #155 — V8/M23b: el cable de `deliverables` y las rutas de proyecto

`assemble_bundle` aceptaba `deliverables=` desde siempre y nadie se lo pasaba
(N4/#70b) — honest-empty ESTRUCTURAL. Decisión: el deliverable es el
**artefacto de salida del run**, el único que el log identifica sin ambigüedad
(`run.completed.output_digest`) y cuyos bytes son recuperables byte a byte del
content store; o sea, el único que un tercero puede re-verificar contra el
digest que el certificado cita. Un artefacto no recuperable NO se cita: un
certificado no se cae porque falte uno, se cae si MIENTE sobre uno.

### DEFECTO PROPIO cazado por este cambio (y cerrado)

`certificate.py`/`reads.py` decidían «el run terminó» mirando `stream[-1]`. El
freeze §2 [stress-final] admite familias de CIERRE post-terminales, así que el
primer `run.metrics.recorded` produjo un **409 en el certificado** — y pasarle
el stream completo a `assemble_bundle` habría metido un evento post-terminal
DENTRO del `provenance_hash`. Corregido: terminado = TIENE terminal, y lo que
se certifica es `provenance_slice(stream)`. Era un defecto latente desde antes
de esta sesión; lo destapó el primer productor de la familia de cierre.

### Tabla de interacciones — sesión VISUAL/CIENCIA

| Interfaz                                                     | Dominio afectado | Estado del contrato                                                          |
| ------------------------------------------------------------ | ---------------- | ---------------------------------------------------------------------------- |
| `blite_capability.branch_ids` (SDK, módulo nuevo)            | engine ↔ caps    | NUEVO — convención C-8 versionada (`canonical-l-min-max@v1`)                 |
| `blite.ingesta.geojson.to_graph` output + `edge_id_property` | caps → corpus    | ADITIVO — `branch_ids`/`branch_id_convention`; el corpus estampado no cambia |
| `blite.verification.partition` (módulo nuevo)                | engine           | NUEVO — productor del payload §4                                             |
| `blite.verification.structural_partition` (módulo nuevo)     | engine           | NUEVO — pata AL2 para instancias sin dato eléctrico                          |
| `ClaimDeclaration.result_projection` + `step_id` top-level   | engine ↔ api     | ADITIVO — binding de confianza intocable (llaves reservadas)                 |
| `verification.completed.latency_ms`                          | engine ↔ api     | ADITIVO — reservado; base de la derivación de métricas                       |
| `blite.runtime.metrics` (módulo nuevo)                       | engine ↔ api ↔ D | NUEVO — payload v2 C-4; `variant` enum de 4 en 4 espejos                     |
| `blite.runtime.ablation` (módulo nuevo)                      | engine           | NUEVO — brazos como sub-runs §13                                             |
| `chimera_api.deliverables` (módulo nuevo)                    | api              | NUEVO — cable de `deliverables=`                                             |
| `GET /runs/{id}/topology` (consumidor)                       | E ↔ D            | VERDE — el Zod espejo del fixture valida el wire vivo                        |
| `GET /runs/{id}/ablation` (agrega sub-runs)                  | E ↔ D            | ADITIVO de lectura — cada brazo conserva su propia respuesta                 |
| `GET /artifacts`, `GET /knowledge` (nivel proyecto)          | E ↔ D            | NUEVAS — allowlist de nginx ampliado en el MISMO cambio (lección de `/me`)   |
| `topologySnapshotSchema` / `ablationVariantSchema` (Zod)     | D                | ESPEJO — `ablationVariantSchema` compartido por fixture y wire               |
| `GridMap.partition` (seam → implementado)                    | D                | El seam declarado en D4 deja de ser seam                                     |
| `apps/studio/src/fixtures/ice/instancia.json`                | D                | NUEVO — proyección del corpus estampado con anti-drift                       |

### Hallazgo heredado (NO introducido acá)

`pnpm run arch` está **rojo en `mejorado/base`**, reproducido con el árbol
limpio: `no-circular App.tsx → router.tsx → App.tsx` y
`F3: App.tsx → gatewayClient`. Ambas vienen de P7 (router real). No está en la
lista de gates del bloque REGLAS, así que no bloquea — pero es un gate de
arquitectura en rojo y merece dueño. **CERRADO** en esta sesión: la raíz
dejó de ser también el módulo de pantallas (`screens.tsx`) y `fileDownloadUrl`
pasa por `data/`; la regla F3 se extendió para cubrir el archivo nuevo.

### #156 — V5: los ángulos de QAOA se reportan, se pueden dar, y se pueden escalar

Tres capacidades aditivas sobre `solve_qaoa` — sin argumentos nuevos el
comportamiento es idéntico.

1. **`angles` siempre se reporta.** Sin ellos, `expected_energy` era un número
   que nadie podía recomputar: el circuito que lo produjo quedaba sin
   identificar.
2. **`initial_angles` + `optimize=false`** — evaluar ⟨C⟩ en un calendario
   ajeno SIN re-optimizar. Re-optimizar cambiaría los ángulos de la corrida
   que se dice estar midiendo, que es exactamente lo que la haría
   incomparable. El round-trip (optimizar → devolver ángulos → re-evaluar en
   ellos → mismo ⟨C⟩) es exacto por construcción: ⟨H⟩ se recomputa siempre
   sobre los ángulos finales en vez de leerse del `fun` de COBYLA.
3. **`init_strategy="interp"`** — la escalera p=1…layers de Zhou et al. (2020)
   §IV. Vive en `warm_start.py` porque es aritmética PURA y por tanto
   verificable exactamente (extremos conservados, combinación convexa, +1 capa
   por paso); enterrada dentro de `solve_qaoa` solo se podría comprobar de
   refilón con un «la energía mejoró», que pasa aunque la fórmula esté mal.

Decisión de implementación: los parámetros del ansatz se ligan por **NOMBRE**,
no por posición. Confundir β con γ no produce un error — produce una energía
plausible de un circuito distinto del que se reporta.

### #157 — V3/M20: la curva r-vs-p se mide en los ángulos que corrió el hardware

**Dónde viven los datos.** El barrido r vs p abarca p×semillas corridas y no
cabe en el stream de UNA ejecución. Por eso `GET /runs/{run_id}/rvsp` es clave
POR RUN pero datos POR INSTANCIA: el run aporta el único dato que es suyo —qué
red se está resolviendo— y la curva sale de un corpus congelado nuevo,
`knowledge/rvsp/<instancia>.json`, con la MISMA disciplina de identidad que el
resto de `knowledge/` (digest embebido que cierra sobre el contenido).
`results/exp_r_vs_p/` sigue siendo lo que su docstring dice: una instantánea
ilustrativa del experimento, sin identidad.

**Por qué ángulos de Nexus.** Con ángulos que optimizamos nosotros, el punto de
la curva mide nuestro COBYLA tanto como mide QAOA. El importador ahora persiste
`betas`/`gammas` (antes vivían SOLO en el espejo solo-lectura) y
`gen_corpus_rvsp.py` evalúa ⟨C⟩ EN ellos vía `optimize=false` (#156). Los
ángulos ya eran la FUENTE de `circuit_digest`, así que persistirlos no mueve
ningún digest — hay un test que lo comprueba contra el índice committeado,
porque si se moviera habría que parar y reportar, no re-estampar.

**La ETIQUETA de la curva** (bloque `metodo` del record: backend, shots,
semillas, origen de los ángulos, `circuit_digest` por capa) vive en el
ARTEFACTO, no en el wire: la spec congeló el wire y dejó el método al dominio
de ciencia. Sin esa etiqueta, un punto medido en hardware y uno medido en
ángulos propios se ven idénticos y son afirmaciones distintas.

**Resultado honesto:** la curva NO es monótona en p (cr6-uniforme: 0.7034 →
0.8199 → 0.7601). Los ángulos de p=3 no fueron mejores que los de p=2. Se
reporta tal cual — es un dato sobre la corrida vanilla, no un defecto a
maquillar.

**Tres 404 que no degradan:** run desconocido / run sin instancia declarada /
instancia sin curva ingerida. Ninguno cae a `points: []` — un gráfico vacío se
lee como «el experimento dio esto», que sería falso. El Studio distingue el 404
(vacío honesto) del 500 (falla) vía el `status` que `fetchWireGet` propaga.

### Tabla de interacciones — V5 y V3/M20

| Interfaz                                                      | Dominio afectado | Estado del contrato                                                       |
| ------------------------------------------------------------- | ---------------- | ------------------------------------------------------------------------- |
| `blite_cap_quantum.warm_start` (módulo nuevo)                 | caps             | NUEVO — INTERP puro, sin qiskit                                           |
| `solve_qaoa` + manifest `blite.quantum.qaoa`                  | caps ↔ runtime   | ADITIVO — `initial_angles`/`optimize`/`init_strategy`; salida `angles`    |
| `scripts/import_nexus_runs.py` → `knowledge/nexus/index.json` | ciencia          | ADITIVO — `betas`/`gammas`; NINGÚN digest se mueve (test que lo prueba)   |
| `knowledge/rvsp/<instancia>.json` (corpus nuevo)              | ciencia ↔ api    | NUEVO — regla de identidad §15.3; bloque `metodo` fuera del wire          |
| `chimera_api.corpus_records` (módulo nuevo)                   | api              | EXTRAÍDO — una sola definición de identidad de corpus (tfim/tabular/rvsp) |
| `chimera_api.rvsp` (módulo nuevo)                             | api ↔ D          | NUEVO — `RvspResponse`; `baselines` cerrado a 3 (C-15)                    |
| `RunTicket.instance_id`                                       | api              | ADITIVO — qué instancia encargó el run; `None` ⇒ 404, jamás una adivinada |
| `GET /runs/{run_id}/rvsp`                                     | E ↔ D            | IMPLEMENTA el contrato congelado; seed des-xfaileado                      |
| `GatewayResponse.status` en las LECTURAS (`fetchWireGet`)     | D                | ADITIVO — sin él, un 404 del contrato es indistinguible de un 500         |
| `rvspWireSchema` + `toRvsPExperiment` (Zod)                   | D                | ESPEJO — snake_case → camelCase, mismo patrón que `toAblationMetric`      |
| `loadRvsP(runId?)` / `rvspQueryOptions`                       | D                | La rama live deja de devolver `null` fijo                                 |
| fixture `get-runs-rvsp.json` (canónico + espejo Studio)       | E ↔ D            | NUEVO — generado desde `RvspResponse` sobre el corpus REAL, no a mano     |

### #158 — V4/M6: el control negativo no es un extra, es la condición de publicación

El bloque `mitigation.*` estaba congelado en el freeze §11 desde S-E y cero
código lo emitía. Lo emite una capability propia (`blite.quantum.zne`) —
propia y no Mitiq porque Mitiq es GPL-3.0 y este repo se distribuye MIT (nota
09 §3); Mitiq entra como dependencia opcional del harness de benchmarks.

**La decisión de diseño que manda todo lo demás:** `mitigate_expectation` corre
SIEMPRE el control negativo de garbage-folding y devuelve
`improvement_survives_control`. arXiv:2607.09360 demuestra que ZNE produce
mejoras ARTEFACTUALES — cuando la amplificación supera la señal, la
extrapolación colapsa a un reescalado de una medición ruidosa y «mejora» sin
física detrás. Un mitigador que reporta solo su delta no se puede auditar.

**Reproducimos el hallazgo en nuestro propio código.** Con extrapolación lineal
sobre G6 al 5 % de ruido de 2 qubits: mejora legítima 0.1–0.3 %, control de
basura 28–52 %. Dos órdenes de magnitud de «mejora» sin física. Con Richardson
el control sale negativo (−0.08 a −1.19) y la mejora legítima (0.9–3.3 %) sí
sobrevive. Fijado como test parametrizado sobre 3 semillas: asevera que el
control FUNCIONA, no un número.

`training_digest` viaja en `None` EXPLÍCITO — ZNE no entrena, y rellenar el
campo fabricaría procedencia. El corrector aprendido (V9) sí lo llena: el
mismo bloque distingue los dos métodos sin cambiar de forma.

**Reproducibilidad medida, no prometida:** la rama legítima es bit-estable con
la seed pinneada; la del control no siempre lo es entre corridas (circuitos
mucho más profundos, Aer no garantiza el reparto de shots a esa profundidad).
El VEREDICTO sí es estable sobre 5 semillas. Se dice así.

### #159 — V2 cerrado: el costo de corte sale de la salida del brazo

El productor (`scripts/run_ablation.py`) destapó un hueco del mecanismo:
`cut_cost` había que declararlo ANTES de correr el brazo, pero es justo lo que
el brazo computa. Declararlo por adelantado obligaba a correr la capability dos
veces, y el `wall_ms` registrado sería el de la segunda corrida — midiendo un
trabajo ya hecho. `AblationArm.cut_cost_from` lo lee de la salida (recuperada
del content store por su digest). Las dos formas son EXCLUYENTES.

**Las barras tienen que ser la misma CLASE de número.** La primera corrida
comparaba el best-of-2048-shots del brazo cuántico contra un valor esperado
mitigado — y hacía ver a la mitigación peor por una razón que no tiene nada
que ver con mitigar. Corregido: cuántico reporta ⟨C⟩ (la lección del fix 4b),
exacto su óptimo, ZNE su valor mitigado.

**Regla de publicación del brazo ZNE:** si la mejora no sobrevivió al control,
el brazo NO aporta costo — ni siquiera cuando el campo del veredicto falta
(«no sé si es artefacto» no es «no lo es»). `mitigated` no se declara como
brazo: su productor es V9 y una barra vacía CON nombre es peor que una ausente.

Corrida real sobre `cr8-uniforme` (óptimo 7): quantum ⟨C⟩ 6.35 (r 0.907, 4.6 s)
· classical 7.00 (r 1.000, 0.2 s) · zne mitigado 5.94 (r 0.848, 28.5 s).

### Tabla de interacciones — V4/M6 y cierre de V2

| Interfaz                                 | Dominio afectado | Estado del contrato                                                      |
| ---------------------------------------- | ---------------- | ------------------------------------------------------------------------ |
| `blite_cap_quantum.zne` (módulo nuevo)   | caps             | NUEVO — folding, extrapoladores y el control negativo                    |
| `blite.quantum.zne` (capability nueva)   | caps ↔ runtime   | NUEVA — emite el bloque `mitigation.*` del freeze §11                    |
| `qaoa.prepare_circuit` / `sample_counts` | caps             | EXTRAÍDO — el mitigador usa EL MISMO circuito que el solver              |
| `AblationArm.cut_cost_from`              | engine           | ADITIVO — excluyente con `cut_cost`; cierra el hueco que V2 dejó         |
| `scripts/run_ablation.py`                | ciencia ↔ E ↔ D  | NUEVO — el llamante que a `blite.runtime.ablation` le faltaba            |
| `AblationPanel` (test)                   | D                | El panel de 4 barras no tenía NINGÚN test; ahora fija la leyenda honesta |

### Handoff de la sesión VISUAL/CIENCIA — qué queda, qué NO, y con qué causa

**Gates al cierre** (worktree `mejorado/visual`, 14 commits sobre
`mejorado/base` @cebbfe5):

| Gate                            | Resultado                                        |
| ------------------------------- | ------------------------------------------------ |
| `pytest`                        | **1409 passed**, 9 skipped, 4 xfailed, 4 xpassed |
| `lint-imports`                  | **14 contratos kept, 0 broken**                  |
| `ruff check`                    | limpio                                           |
| `pyright`                       | **0 errores**                                    |
| `pnpm -C apps/studio test:run`  | **327 passed** / 34 files                        |
| `pnpm -C apps/studio typecheck` | limpio                                           |
| `pnpm -C apps/studio lint`      | limpio                                           |
| `pnpm run arch` (depcruise)     | **0 violaciones** (146 módulos, 506 deps)        |

Baseline al abrir: studio 318 en 33 files; `pnpm run arch` **rojo** (ver abajo).

**Alcance cerrado**: V1/M18, V2/M19 (con su productor), V3/M20, V4/M6-ZNE, V5,
V8/M23b, más el gate de arquitectura heredado. Decisiones #153-#159.

#### Lo que NO se cerró, con causa

1. **V6/M5 adapter qnexus vivo — BLOQUEADO-POR-DYLAN (tres causas).**
   - `qnexus`/`pytket` NO están instalados, y agregarlos toca el venv
     **compartido** con la sesión de plataforma. No es una decisión de una
     sesión sola.
   - Submitir a Nexus consume cuota HQC: es gasto real y necesita autorización
     explícita, no inferida del alcance.
   - Sin poder importar el SDK no hay forma de verificarlo contra su API real.
     Escribir un adapter que _parece_ correcto contra una API que no se puede
     correr es exactamente lo que la regla de validar-con-cliente-real prohíbe:
     produciría código plausible que hay que rehacer al primer contacto.

   **Lo que SÍ está listo para cuando se desbloquee**: el pipeline del gateway
   con su etapa `egress` gobernada solo por authz (`gateway/stages.py`), y la
   maquinaria de aprobación humana (`blite.gateway.approval`,
   `authorize_approval_response`).

2. **V7 QEC/Iceberg — bloqueado por transitividad.** El entregable es el
   tradeoff **MEDIDO**; medirlo contra un simulador local no responde la
   pregunta que el enunciado hace. Depende de V6.

3. **V9 (#120) corrector AI-QEM — NO bloqueado, no alcanzó.** sklearn y
   xgboost ya están instalados, el corpus existe, y desde V4 tiene un baseline
   real que batir: `zne.apparent_improvement` y el mismo control negativo de
   costo igual. El bloque `mitigation.*` ya tiene forma emitida — V9 solo llena
   `training_digest` y cambia `method` a `ml-rf`/`ml-gbm`. **Al cerrarlo**:
   declarar el brazo `mitigated` en `scripts/run_ablation.py` (hoy NO se
   declara a propósito) y el panel queda con las 4 barras reales.

4. **DoD CP6 vivo contra compose — NO alcanzó.** Receta concreta: levantar
   compose, correr `scripts/run_ablation.py` con `CHIMERA_DATABASE_URL`
   apuntando a su Postgres, y verificar en el Studio el mapa con badges + el
   panel de ablación + la curva rvsp. Los tres productores existen y están
   probados por separado; falta la corrida de punta a punta.

#### Hallazgos heredados (NO introducidos en esta sesión)

1. **`ruff format --check .` está ROJO en `HEAD`** — 20 archivos
   (`capabilities/{ml,numeric,quantum}`, `challenges/reto{2,3}`, `scripts/`).
   Verificado con `git archive HEAD` que es anterior a esta rama. Es un gate de
   CI real (`.github/workflows/ci.yml:103`), así que **cualquier PR está rojo
   hoy**. No se arregló acá porque 16 de los 20 archivos son de otros dominios
   y un reformateo masivo dentro de un commit de features es ruido que esconde
   el cambio real. Necesita dueño y un commit propio.

   Efecto colateral a tener presente: `ruff format <dir>` reformatea TODO el
   directorio, así que arrastra ese drift al staging de quien formatee.

2. **La invariante ADR-029 no ve capabilities nuevas.**
   `tests/invariants/test_capability_genericity.py` enumera
   `entry_points(group="blite.capabilities")`, que lee metadata **instalada**:
   una capability nueva no entra al gate hasta un reinstall del paquete.
   Mitigación ya usada dos veces (`FidelityKernel`, `ZeroNoiseExtrapolation`):
   un `TestGenericitySelfCheck` local en el test de la capability, que corre la
   misma denylist contra el manifest en vivo. Vale la pena decidir si esa
   mitigación se vuelve convención escrita o si el gate cambia de fuente.

3. **`side_effects` del manifest no tiene NINGÚN enforcement.** Verificado por
   grep: no se consulta en `runtime/loop.py` ni en `gateway/*.py`. La regla de
   §13 («`pure` se reintenta libre; `reversible`/`irreversible-external` sin
   idempotencia NO se reintenta y escala a humano») no está expresada como
   código. Hoy no hay lógica de reintento en absoluto, así que el «no
   reintentar» es cierto **de facto** — lo que falta es la ESCALACIÓN. Es
   precisamente el mecanismo que V6 necesita, y por eso se reporta acá y no se
   improvisó: construir un motor de reintentos para colgarle una escalación es
   inventar arquitectura que §13 no pidió.

4. **La suite del Studio es sensible a la carga de la máquina.** Correr pytest
   y vitest en paralelo hace que `userEvent.type` de `NewRunView.test.tsx` se
   pase del timeout de 5 s. Verificado que NO es regresión (verde en
   aislamiento y en corridas limpias consecutivas). Se arregló el caso análogo
   de `registry.test.ts` (dos `import()` dinámicos DENTRO del test, sin ningún
   mock que los justificara); el de `NewRunView` es el `delay` por tecla de
   user-event y toca 6+ archivos, así que queda reportado en vez de barrido.

#### Frontera de contrato reportada (no se cruzó)

Exponer la ablación desde `POST /runs` necesita una **tercera forma de body**
(hoy claim-first y misión-first) ⇒ toca `docs/specs/endpoints-studio.md` ⇒
ceremonia de contrato, que el plan reserva a la sesión de control. El mecanismo
completo ya existe y está probado (`blite.runtime.ablation` +
`scripts/run_ablation.py`); lo único que falta es el wire.

## Sesión PLATAFORMA (dominio O) — worktree `mejorado/plataforma`, 2026-08-05

> Numeración: las sesiones paralelas de esta ola (C-2, V, O) anexan en sus ramas;
> si dos coinciden en un número, la sesión de control lo resuelve al mergear.

### #153 — O2: el mecanismo de enforcement versionado y el destino del vendorizado

**Discutido con Dylan (2026-08-05), como manda el enunciado de O2.**

**Contexto que cambió la pregunta.** El hook local que registraba la decisión del
2026-07-16 **no existe en esta máquina**: `.claude/settings.local.json` solo trae
`permissions`, `~/.claude/settings.json` no declara hooks, y no hay
`check-branding.sh` en ninguna parte. La regla estaba vigente en el papel y con
CERO compuertas vivas — que es exactamente el argumento de O2/M26.

**Decisión 1 — gitleaks con config privada opcional.** El enforcement versionado
se monta sobre gitleaks (que O2 pedía de todos modos): la herramienta y su
configuración base viajan con el repo, y una config privada NO versionada
extiende la lista de patrones. La tensión con la decisión del 16-jul («un
mecanismo de enforcement visible es en sí una señal») se resuelve porque lo
versionado es genérico —escaneo de secretos, lo que cualquier repo serio tiene— y
lo específico vive fuera de git. Descartados: script propio de denylist (dos
mecanismos donde alcanza uno, y un script a medida sí levanta la pregunta «¿por
qué existe esto?») y semgrep (hoy es advisory de CI, y la regla prohíbe CI para
esto).

**Decisión 2 — el árbol vendorizado sale del repo; el destilado se queda.**
`knowledge/quantum/quantathon/` son 16 MB / 81 archivos trackeados (65 `.md`,
15 `.png`, 1 `.yaml`): transcripciones de clases de YouTube (QWorld) y sesiones
de 7 ponentes nominados, **sin licencia declarada**. Dylan precisó para qué
existía: iba a refinarse e integrarse al agente como contexto. Eso separa dos
cosas que estaban pegadas — el VALOR es el destilado (escritura nuestra, que cita
las URLs públicas), el material crudo nunca necesitó estar versionado. Se mueve a
`~/projects/blite/hackathons/2026/Quantathon/quantathon-material/`: sigue a mano
por ruta absoluta para la sesión que lo destile, y deja de viajar en el repo.

- **Bloqueador pre-flip registrado**: el flip publica la HISTORIA, no solo HEAD.
  Sacarlo del árbol no lo saca del repo público — hace falta cirugía de historia
  (`git filter-repo`) ANTES de publicar, y la corre Dylan (el clasificador de la
  sesión bloquea filter-repo/force-push).
- **Ítem nuevo al backlog**: destilar ese material a skills / afinado del harness
  (razón de Dylan). No es alcance de O — se registra, no se ejecuta aquí.

### #154 — O11: el gate de agnosticismo deja de ser mono-superficie

**El problema (censo 07 §8.1/§8.5-4).** La doctrina de agnosticismo tenía UNA
compuerta sobre UNA superficie: 4 campos del manifest. Ni `engine/`, ni `api/`,
ni `apps/studio/` tenían gate — y las fugas censadas están, sin excepción, en las
superficies sin compuerta. Cada fuga nueva era indetectable por CI. Es el ítem
que hace irreversibles a los demás: sin él, la generalidad que ganan G/P/C/V se
erosiona en silencio, un id de instancia hardcodeado a la vez.

**Lo construido.** `tests/invariants/test_agnosticism_layers.py` +
`agnosticism_scan.py` escanean el código de PRODUCCIÓN de `sdk` · `engine` ·
`api` · `apps/studio/src` · `packages` contra el MISMO `scenario_denylist.txt`
que vigila los manifests (una lista, no dos: dos listas driftean el primer día).
Las excepciones son DECLARADAS en `agnosticism_exceptions.toml`, con clase y
causa. Documentado como **ADR-029b** en `docs/invariants.md` con anclas
`<!-- enforced: -->`.

**Cuatro decisiones de diseño, cada una con su porqué:**

1. **Trinquete de dos mitades.** Falla una fuga nueva sin declarar Y falla una
   excepción que ya no matchea nada. Sin la segunda mitad la lista se vuelve un
   cementerio que oculta que el gate ya podría ser más estricto.
2. **Frontera de palabra con `_` y `-` incluidos**, no `\b` ni subcadena. Por
   subcadena, `ice` matchea `service`/`slice`/`device` y el gate muere de ruido.
   Con `\b`, `_ISLANDING_CORPUS_DIR` **NO** matchea `islanding` — y el nombre de
   un identificador es justo donde el vocabulario de escenario se esconde mejor
   (esa línea de `runs.py` se colaba entera con `\b`).
3. **`lenses/` fuera del barrido, por doctrina.** P13 creó el registry de lentes
   del Studio y su propio código lo declara: «la única parte del Studio que puede
   nombrar capabilities de redes eléctricas, y por eso vive acá y no en el shell».
   Es el `capabilities/` del lado D. Si una lente no pudiera nombrar su dominio,
   no habría dónde ponerlo. También fuera: fixtures (datos etiquetados) y tests.
4. **Declarar, no refactorizar.** Las 16 fugas vivas se DECLARAN, no se arreglan
   en esta sesión: 11 de los 16 archivos son territorio de sesiones vivas (C-2 en
   `engine/verification` y `api`, V en el Studio). El gate existe para hacer la
   deuda visible y no-creciente; pagarla es de G3/P6/V1.

**El mapa que deja (16 archivos, 53 apariciones, 3 clases):**

| clase      | qué es                                          | ejemplos                                                                                             |
| ---------- | ----------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| `doctrina` | la regla citándose a sí misma                   | `sdk/.../manifest.py` — el docstring de ADR-029 usa los términos prohibidos como contraejemplo       |
| `contrato` | identificador YA estampado en evidencia emitida | `HARNESS_ID = "pandapower-islanding-v1"`, `verifier:pandapower-islanding` — renombrar RE-DIGESTA     |
| `deuda`    | fuga real, con el ítem que la cierra            | `_ISLANDING_CORPUS_DIR` en el borde HTTP (→G3) · `DEFAULT_PROJECT` del router (→P6) · el spike (→V1) |

**Términos nuevos en el denylist**: `pandapower`, `ieee14`/`ieee-14`,
`ieee30`/`ieee-30` — librería de dominio e ids de instancia benchmark del reto 1.
Una capa genérica que los nombra está cableada al escenario; `capabilities/` los
puede nombrar libremente (ADR-008 pone el dominio ahí).

**Verificado (no «debería»)**: con un canario `MICROGRID_MODE` inyectado en
`engine/src/blite/runtime/dispatch.py`, el gate falla citando archivo, línea y
término; revertido el canario, verde. `tests/invariants/`: **88 passed / 1
skipped**. `pyright` **0 errores** (worktree con `pyrightconfig.json` local —
`extraPaths` + `venvPath` al venv del principal; excluido en `.git/info/exclude`,
lleva rutas absolutas de esta máquina). `ruff` limpio. `markdownlint` y
`prettier --check` verdes sobre `docs/invariants.md`.

### Tabla de interacciones — #153/#154

| Interfaz tocada                          | Dominio afectado | Estado del contrato                                                  |
| ---------------------------------------- | ---------------- | -------------------------------------------------------------------- |
| `tests/invariants/scenario_denylist.txt` | TODOS (doctrina) | EXTENDIDO — 5 términos nuevos; una lista alimenta las DOS compuertas |
| `docs/invariants.md` — ADR-029b          | TODOS (doctrina) | NUEVO — aditivo; ADR-029 intacto                                     |
| `agnosticism_exceptions.toml`            | engine · api · D | NUEVO — mapa declarado de deuda; solo puede encoger                  |
| Baseline del worktree                    | n/a              | 1205 passed / 13 skipped / 9 xfailed / 4 xpassed / cov 91.62 %       |

### #155 — O8: el tercer plano existe, y su primera medición encontró algo

**El hueco (censo 07 §7.1-1).** G1-G7 metieron los retos 2 y 3, C-1/C-2 profundizan
la confianza, V pinta los productores — y **no había forma de medir si el sistema
MEJORA**. El `false_reject_proxy` que trust/05 §1.3 define como KPI de primer
nivel llevaba meses sin consumidor.

**Lo construido.** `chimera_eval` (`tools/corpus-runner/`, miembro nuevo del
workspace), con la forma de Inspect (UK AISI) —`Dataset → Task → Solver →
Scorer`— y su vocabulario `C/I/P/N`, **portados sin la dependencia** (la decisión
ya estaba tomada en trust/17 §2: adoptar el framework metería su ciclo de vida
dentro del nuestro). Más `docs/tres-planos.md`, el marco transversal promovido
desde trust/17 §1.6, y `scripts/run_eval_corpus.py`, que arma el dataset desde el
corpus C3 y corre los verificadores REALES.

**Tres decisiones de diseño que no son de Inspect:**

1. **`config_digest`.** El `EvalSpec` de Inspect captura `revision` y `packages`
   pero ningún digest de configuración: la reproducibilidad había que computarla
   igual. Acá la identidad de una evaluación ES su digest.
2. **Cero reloj en el log.** Dos corridas idénticas dan bytes idénticos
   (verificado: mismo sha256 en dos corridas seguidas). Con timestamp, comparar
   dos variantes de una ablación sería lectura a ojo en vez de un `diff`.
3. **Un error de PROCESO no es un veredicto** — la misma doctrina que
   `VerificationProcessError` en el engine. Si el solver explota, la muestra sale
   de las tasas y se reporta aparte: contarla como `I` inventaría un error del
   sistema, y como `N` inventaría una abstención que nadie tomó. Las dos mentiras
   corrompen justo el KPI que el runner existe para medir.

**`target` estructurado, no string.** Es la única fricción de forma que trust/17
§1.2 anotaba («`Target` es estrictamente `str | list[str]`»): una partición de
grafo o una serie numérica no son texto. El corpus de esta casa tiene óptimos y
series; el tipo lo dice.

**La frontera, hecha gate.** Contrato de import-linter nuevo — **«O8: evaluation
is downstream — nothing imports the corpus runner»**: `blite`, `chimera_api`, el
SDK y las 9 capabilities tienen prohibido importar `chimera_eval`. La flecha
inversa es legítima y por eso NO se prohíbe (la tarea importa el plano de
verificación para medirlo). Si un día se invirtiera, una métrica retrospectiva
habría entrado al camino crítico de un run — que es exactamente la confusión
eval≈verificación que el marco existe para evitar.

**LA MEDICIÓN (corpus C3, 9 instancias × 2 polaridades, verificadores reales):**

| KPI                   | valor     |
| --------------------- | --------- |
| `scored`              | 18        |
| `process_errors`      | 0         |
| `accuracy`            | 0.667     |
| `over_refusal_rate`   | **0.333** |
| `decisive_error_rate` | **0.0**   |

Las dos polaridades importan: sin la muestra perturbada, un verificador que
dijera `pass` a todo sacaría 100 %. La perturbación es MULTIPLICATIVA (×1.5) y no
aditiva a propósito — un offset aditivo sobre valores cercanos a cero no mueve el
error L∞-RELATIVO que estos verificadores usan, y la «mentira» se colaría como
verdad.

**El hallazgo — HANDOFF a G / C-2.** Cero errores decisivos (el sistema nunca se
pronunció equivocado, en ninguna polaridad). Pero el 33 % de sobre-rechazo está
**enteramente en `N = 12`**: `verifier:ed-dense` se abstiene con
`budget_exhausted` porque 2¹² = 4096 supera su `_DEFAULT_MAX_DENSE_DIMENSION =
1024`. La abstención es honesta y diseñada así (rehúso explícito antes que cambio
silencioso de algoritmo, §Deliverable-1 punto 2). La consecuencia NO estaba
medida: **en `N = 12` los claims del reto 3 quedan sostenidos por UNA pata** (el
corpus congelado), no por las dos independientes que la receta 11 promete — la
independencia se degrada justo en las instancias más grandes. No es bug de nadie;
es una medición que antes no existía. Decidir es de G/C-2: subir el presupuesto,
declarar `N=12` como single-leg con causa, o traer una segunda pata que escale.

**Hallazgo de arnés (corrige la receta #83).** `uv sync --locked --all-packages
--all-extras` DENTRO del worktree crea un `.venv` completo, con los editables
apuntando al worktree. La receta anterior (venv del principal + `PYTHONPATH`) ya
no hace falta y además ocultaba errores de tipo de módulos nuevos (#149). Los
gates de esta sesión corren con `uv run` a secas.

**Flake preexistente registrado (NO introducido acá).** En la PRIMERA corrida del
baseline, `capabilities/ml/tests/test_integration_reto2.py::TestFullChainOnCorpusSlice::test_both_arms_produce_metrics_with_aligned_shapes`
falló; en las tres corridas siguientes (misma config, con y sin cobertura) pasó.
Aislado pasa siempre. Un test no determinista en un repo cuyo argumento es el
determinismo merece dueño: queda REPORTADO, sin decisión, para G.

### Tabla de interacciones — #155

| Interfaz tocada                                       | Dominio afectado | Estado del contrato                                                   |
| ----------------------------------------------------- | ---------------- | --------------------------------------------------------------------- |
| `pyproject.toml` — workspace + testpaths + coverage   | build            | EXTENDIDO — miembro nuevo `tools/corpus-runner`; `uv.lock` regenerado |
| contrato import-linter «O8: evaluation is downstream» | TODOS            | NUEVO — 15 contratos kept, 0 broken                                   |
| `docs/tres-planos.md` + índice `docs/README.md`       | docs (autoridad) | NUEVO — marco transversal; cero cambios de contrato                   |
| `chimera_eval` (paquete)                              | eval (nuevo)     | NUEVO — fuera de `blite.*`, sin deps de runtime                       |
| `results/eval/*.json`                                 | evidencia        | NUEVO — log reproducible (mismo sha256 en dos corridas)               |

### #156 — CI de `mejorado/base` estaba ROJA, y por qué nadie lo vio

**Hallazgo al empezar O2.** El último push de la fase (#152, `cebbfe5`) dejó CI
en rojo — tres jobs fallando — y ninguna sesión lo notó porque **los gates
locales que el bloque REGLAS manda correr no incluyen los que fallan**:

| job fallando             | causa REAL (reproducida local)                                                                                            | ¿lo cubre el gate local?                                      |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| Python → Format check    | `ruff format --check .` con **21 archivos** sin formatear (ml, numeric, quantum, `challenges/reto{2,3}`, `scripts/gen_*`) | **NO** — el bloque REGLAS dice `ruff check`, que es OTRA cosa |
| Security → gitleaks      | falso positivo: `signing_key: ed25519.Ed25519PrivateKey` en `api/.../runs.py:396` — una ANOTACIÓN DE TIPO, sin valor      | **NO** — no había gitleaks local                              |
| Web → dependency-cruiser | 2 violaciones reales del Studio (abajo)                                                                                   | **NO** — no está en el bloque REGLAS                          |

`lint-staged` solo toca lo que UNO stagea: un archivo que otra sesión dejó sin
formatear sobrevive hasta que CI lo dice. Y el `pre-commit` de husky no corre en
un worktree sin `node_modules` — bypassearlo es exactamente cómo se acumularon
los 21.

**Corregido acá**: `ruff format` sobre el árbol (21 archivos, cambio puramente
mecánico; las sesiones que los escribieron ya cerraron), el falso positivo de
gitleaks (vía `.gitleaks.toml`, abajo), y CONTRIBUTING gana la sección «los dos
gates que la gente olvida» con `ruff format --check .` y `depcruise`.

**Hueco de CI cerrado de paso**: el filtro de rutas del job Python NO incluía
`api/**` — un cambio SOLO en la capa HTTP se saltaba pytest, pyright y
lint-imports enteros. Entran también `distributions/`, `tools/`, `challenges/`
y `scripts/`.

**REPORTADO, no arreglado — depcruise (decisión de arquitectura del Studio, no
mía):** `src/App.tsx → src/router.tsx → src/App.tsx` (`no-circular`) y
`src/App.tsx → src/gatewayClient.ts` (`F3: views-consume-only-the-data-layer`).
Las dos llegaron con el router de P7 y las dos son estructurales: romper el
ciclo mueve dónde vive el árbol de rutas, y F3 dice que una vista no habla con
el cliente HTTP. Es alcance de P-ui/V; hasta que se resuelva, **CI seguirá roja
en el job Web**.

### #157 — O2: enforcement versionado de patrones, y el árbol de terceros fuera

**Ejecuta la decisión #153.**

**Enforcement.** `.gitleaks.toml` versionado (extiende el set upstream) +
`scripts/pre-commit-secrets.sh` colgado del `pre-commit` de husky, que escanea
lo STAGED. Lo específico vive en `.gitleaks.local.toml`, gitignoreado: si
existe, el hook lo usa EN LUGAR del compartido. Lo que viaja en el repo es
genérico —escaneo de secretos, lo que cualquier repo serio tiene— y no dice
nada de qué patrones hay del otro lado.

Comportamiento sin gitleaks instalado, decidido a propósito:

- **sin** config local → avisa y deja pasar (CI escanea la historia y bloquea;
  una herramienta de dev faltante no debe frenar a alguien en su primer día);
- **con** config local → **falla**. Configuraste patrones extra: saltárselos en
  silencio sería lo peor de los dos mundos, enforcement que crees tener y no
  tienes.

**Verificado en vivo** con el binario pinneado de CI (v8.30.1, sha256
verificado): (1) sin gitleaks y sin config local → exit 0 con aviso; (2) sin
gitleaks y con config local → exit 1; (3) con gitleaks y un token de Stripe
staged → **exit 1, commit bloqueado**. Y la allowlist es ANGOSTA, probada por
separado: `signing_key: str = "sk_live_…"` (anotación CON valor) **sí** se
detecta; solo se perdona la declaración sin valor.

**Desvendorizado.** `knowledge/quantum/quantathon/` (81 archivos, 16 MB:
transcripciones de YouTube de QWorld + 7 ponentes nominados, sin licencia
declarada) salió del árbol a
`~/projects/blite/hackathons/2026/Quantathon/quantathon-material/`. Quedan dos
archivos: `catalog.yaml` (índice de fuentes PÚBLICAS — URLs y ponente, se
referencia, no se reproduce) y un `README.md` con la causa.

- **Consecuencia buena e inesperada**: las exclusiones de `.markdownlintignore`
  y `.prettierignore` para ese árbol se BORRAN — el gate de docs vuelve a cubrir
  el repo COMPLETO, sin un agujero de 671 errores «que no son nuestros».
- **Ítem nuevo al backlog** (razón de Dylan): destilar ese material a skills /
  afinado del harness. El valor nunca fue el material, era el destilado — y el
  destilado es escritura nuestra que cita las URLs públicas.
- **BLOQUEADOR PRE-FLIP**: publicar el repo publica la HISTORIA. Sacarlo de HEAD
  no lo saca del repo público: falta `git filter-repo` sobre esa ruta antes del
  flip, y lo corre Dylan (el clasificador de la sesión bloquea filter-repo).

### Tabla de interacciones — #156/#157

| Interfaz tocada                              | Dominio afectado | Estado del contrato                                                          |
| -------------------------------------------- | ---------------- | ---------------------------------------------------------------------------- |
| `.gitleaks.toml` + `pre-commit-secrets.sh`   | repo/CI          | NUEVO — genérico versionado; lo específico fuera de git                      |
| `.husky/pre-commit`                          | repo             | EXTENDIDO — `lint-staged` + escaneo de lo staged                             |
| `.github/workflows/ci.yml` — filtro `python` | CI               | CORREGIDO — `api/**` faltaba; +distributions/tools/challenges/scripts        |
| 21 archivos `ruff format`                    | G (cerrada)      | MECÁNICO — cero cambio semántico; desbloquea el job Python                   |
| `.markdownlintignore` / `.prettierignore`    | docs             | ENDURECIDO — muere la exclusión del vendorizado; gate cubre todo             |
| `knowledge/quantum/quantathon/`              | knowledge        | REDUCIDO a índice + causa; el crudo vive fuera del repo                      |
| `apps/studio` depcruise ×2                   | D (P-ui/V)       | **ROTO — reportado, sin decisión**: CI Web seguirá roja hasta que se arregle |

### #158 — EL REPO YA ES PÚBLICO: el bloqueador pre-flip de #157 no es pre-flip

**Verificado en vivo hoy (2026-08-05), no inferido:**

```
gh repo view Blite-HQ/chimera → {"isPrivate": false, "visibility": "PUBLIC"}
gh api repos/Blite-HQ/chimera/contents/knowledge/quantum/quantathon
  → CLAUDE.md · catalog.yaml · corpus-spec.md · knowledge · slides_png
```

El árbol vendorizado de terceros **está publicado ahora mismo** en GitHub. La
decisión #157 lo sacó del árbol, y eso sirve para HEAD — pero la historia
también es pública, así que la cirugía (`git filter-repo` sobre
`knowledge/quantum/quantathon/` + force-push) deja de ser «antes de publicar» y
pasa a ser **remediación de una exposición viva**. La corre Dylan (el
clasificador de la sesión bloquea filter-repo/force-push), y conviene además
pedirle a GitHub Support que purgue los objetos sueltos: un force-push deja los
blobs accesibles por SHA.

Esto NO cambia el diseño de #157 — el enforcement versionado sigue siendo
genérico y el patrón sigue fuera de git, que es justo lo que hay que hacer con
un repo público. Cambia la urgencia y el orden.

### #159 — hallazgos 9 y 10 del handoff S3, cerrados con evidencia

**Hallazgo 9a — el ignore de CVE con fecha vencida.** RE-EVALUADO hoy:
`pip-audit -f json` reporta `PYSEC-2026-2447` (diskcache 5.6.3, alias
CVE-2025-69872) con **`fix_versions: []`** — upstream sigue sin release
arreglada, así que el ignore SIGUE justificado. El comentario de `ci.yml` deja
de tener una fecha muerta: dice cómo re-evaluarlo y que se quita en cuanto
aparezca un fix.

**Y lo que la re-evaluación destapó — dos CVEs con arreglo disponible,
tapados por la CI roja:**

| paquete               | vuln           | fix disponible | estado                            |
| --------------------- | -------------- | -------------- | --------------------------------- |
| `aiohttp` 3.14.2      | CVE-2026-69244 | **3.14.3**     | PR de dependabot ABIERTO, CI roja |
| `cryptography` 49.0.0 | CVE-2026-69247 | **50.0.0**     | PR de dependabot ABIERTO, CI roja |
| `diskcache` 5.6.3     | CVE-2025-69872 | ninguna        | ignore justificado                |

El job Security corre gitleaks ANTES que pip-audit, así que el falso positivo
de #156 abortaba el job y `pip-audit` **nunca llegaba a correr**: dos parches de
seguridad esperando detrás de un fallo que no tenía nada que ver. Con #156/#157
el job vuelve a llegar a ese paso. **NO se bumpean acá**: los PRs de dependabot
son el vehículo correcto y duplicarlos en `uv.lock` solo crearía conflicto.

**Hallazgo 9b — URL rota de `ISSUE_TEMPLATE/config.yml`.** RESUELTA POR LOS
HECHOS: `https://github.com/Blite-HQ/Chimera/blob/main/SECURITY.md` responde
**200** (comprobado con curl; el nombre real del repo es `Blite-HQ/chimera` y
GitHub no distingue mayúsculas). Estaba «rota» solo mientras el repo era
privado. Sin cambio.

**Hallazgo 10 — pin frágil `68af0c1`.** VERIFICADO alcanzable: el commit existe
local y en origin (`gh api .../commits/68af0c1` →
`68af0c19cf56f95474ffb6e5b14aecf62d5f803f`), lo contiene la rama
`ejercicio/sf-ratificacion-simulada` (local y remota) y
`protocolo-auditoria-ratificaciones.md` se lee ahí. **No podar esa rama.** La
fragilidad se retira de verdad en O9, que necesita ese mismo protocolo como
fuente y lo trae al árbol — a partir de ahí el pin deja de ser la única vía.

### #160 — O12: los datos estampados dejan de depender de que alguien se acuerde

`verify_corpus_digests.py` existía y **nadie lo corría en CI**; `knowledge/nexus/`
—19 corridas externas de Nexus con cadena de digests in-toto— no tenía guard del
todo, solo un README que declara «NADA se re-digesta ni se regenera».

**`scripts/verify_nexus_digests.py`** (nuevo) verifica, por fila de `index.json`:
`sha256(canonicalize(normalized_counts))` = `normalized_digest` · el statement
entero = `statement_digest` · **el eslabón in-toto**: `subject[0].digest.sha256`
= `normalized_digest`, que es lo que hace que la attestation certifique ESTOS
counts y no otros · coherencia de los digests dentro de `event` · **cero
huérfanos** en `normalized/`/`statements/` · y que cada `job_id` de
`consensus.json` exista en el índice.

Recanonicaliza en vez de comparar bytes (el digest manda, no el formato) y usa
el MISMO `canonicalize` del anexo congelado que usó el importador — un guard con
su propia serialización estaría verificando otra cosa.

**Verificado que MUERDE, no solo que pasa**: sobre los datos reales, 19/19 y
cadena íntegra; con `counts["000000"] += 1` en una corrida, **exit 1** citando
digest esperado y recomputado; con un archivo extra en `normalized/`, exit 1 por
huérfano; restaurado, verde otra vez.

**CI**: job nuevo `Data guards` con filtro de rutas propio (`knowledge/*/corpus/**`,
`knowledge/nexus/**`, los dos scripts) — un corpus editado no arrastra la suite
de Python entera, y el `ci-gate` agregador ya lo exige.

### Tabla de interacciones — #158/#159/#160

| Interfaz tocada                         | Dominio afectado | Estado del contrato                                                         |
| --------------------------------------- | ---------------- | --------------------------------------------------------------------------- |
| `scripts/verify_nexus_digests.py`       | datos/confianza  | NUEVO — solo lee y recomputa; cero re-digest                                |
| `.github/workflows/ci.yml` — job `data` | CI               | NUEVO — + filtro propio + entra al `ci-gate`                                |
| `ci.yml` — ignore de CVE                | seguridad        | RE-EVALUADO con evidencia; sigue justificado (sin fix upstream)             |
| `knowledge/nexus/`, corpus              | datos            | **NO TOCADOS** — el guard los lee, jamás los escribe                        |
| exposición pública del vendorizado      | repo             | **ABIERTO — requiere a Dylan**: filter-repo + force-push + purga de objetos |

### #161 — el hallazgo que casi arruina #157: git no corre hooks en un worktree

**Encontrado probando mi propio entregable.** Tras cablear el escaneo de
secretos al `pre-commit`, hice el commit de #157 esperando ver correr
`lint-staged`. No corrió nada.

```
git config core.hooksPath  →  .husky/_
ls .husky/_                →  No such file or directory
```

`core.hooksPath` está configurado, pero `.husky/_` lo GENERA el script
`prepare` de npm y **no está versionado**. Un worktree recién creado hereda la
config y no el directorio: git no encuentra los hooks y **no corre ninguno, sin
error y sin aviso**. Los commits simplemente dejan de revisarse.

Es la causa raíz de #156: 21 archivos sin formatear entraron a `mejorado/base`
porque `lint-staged` —que los habría formateado— jamás corrió en las sesiones de
worktree. Y habría dejado el enforcement de #157 en decorativo: un hook
versionado que en la práctica no se ejecuta es peor que no tenerlo, porque uno
cree estar cubierto.

**Arreglo**: `npx husky` una vez por worktree. Documentado en CONTRIBUTING (con
la comprobación de que el directorio EXISTA, no solo la config) y en el bloque
de reglas de `05-plan-paralelo.md` §0, junto con la corrección de la receta de
gates (`uv sync` en worktree SÍ funciona hoy) y los dos gates que faltan en el
bloque REGLAS (`ruff format --check`, `depcruise`).

**Verificado en vivo, no asumido**: con `.husky/_` generado, `git commit` con un
token de Stripe staged termina en `husky - pre-commit script failed (code 1)` —
el commit NO se crea.

### #162 — O3: el proyector OTel, y el pin de semconv

**Ejecuta S-F (#128) / C-11.** `projectors/otel/` (paquete `chimera_otel`,
miembro nuevo del workspace) deriva trazas OTLP del stream. Es un PROCESO
aparte: no gobierna, no escribe, no importa el engine.

**Lo que se decidió acá (S-F lo dejaba a O3):**

| decisión                    | valor      | por qué                                                                                         |
| --------------------------- | ---------- | ----------------------------------------------------------------------------------------------- |
| pin de semconv GenAI        | **1.38.0** | las semconv GenAI siguen incubando; el pin es una decisión fechada y cada span la porta         |
| `chimera.projector_version` | **1**      | cambiar el mapeo = bump acá Y en el prefijo de dominio (`.../v2`), como el anexo                |
| collector del perfil        | `debug`    | el DoD es «un run real llega a un collector»: stdout lo hace observable sin montar Jaeger/Tempo |

**Tres fronteras hechas hechos, no promesas:**

1. **Solo-SELECT de verdad.** El proyector se conecta con el rol
   `chimera_otel`, creado por un init script con `SELECT` sobre `events` y nada
   más. **Probado en vivo**: `INSERT` → `ERROR: permission denied for table
events`; `SELECT count(*)` → 13. El append-only no depende de que el código
   se porte bien.
2. **Imagen propia.** El proyector NO usa la imagen del api: instala
   `--package chimera-otel` y ni siquiera lleva `blite` dentro. Más dos
   contratos de import-linter, uno por dirección (17 contratos kept, 0 broken).
3. **Cursor fuera del event store** — volumen propio. Se puede perder: reproyectar
   es idempotente.

**Determinismo, el punto del ítem.** El SDK de OTel genera ids ALEATORIOS. Se
usa su punto de extensión (`IdGenerator`) para devolver los del plan —
deliberadamente NO se escribe el `_context` privado del span, que habría
funcionado hoy y se habría roto en la próxima versión del SDK, en silencio y
justo en la propiedad que sostiene el diseño.

**DoD CUMPLIDO EN VIVO** (`docker compose --profile otel up -d --build`), no en
tests:

- run REAL creado por HTTP (`run-1d7edb53aecc4f2d96b61d0272cb2b96`, 12 eventos);
- el collector recibió **5 spans**: `run` · `step` ×2 · `capability` ·
  `verification` — las cinco clases de la tabla §3 que este run produce;
- `trace_id` en el collector = **`bd03fae4d4e1fa97dc7c441ba71ba859`**, idéntico
  al recompute independiente de `sha256("blite/otel-trace/v1\n" ‖ run_id)[:16]`;
- cada span porta `chimera.semconv_version=1.38.0` y
  `chimera.projector_version=1`;
- **re-proyección**: borrado el cursor y reiniciado el servicio, el collector
  vuelve a recibir la MISMA traza — la promesa de §4 verificada contra un
  collector real, no contra un mock.

**El stream `system:registry` quedó fuera**, como manda §3: no es el rastro de
un run.

**Fixture de costura** `tests/fixtures/contract/observabilidad/trace-example.json`
con su generador (`scripts/gen-contract-fixtures-observabilidad.py`) y su test
anti-drift; el golden cubre las CINCO clases de span. Espejo Studio no aplica
(el consumidor es un collector).

**Seeds S-F en verde**: los 3 xfail de `test_seed_observabilidad_proyector.py`
se retiraron — quedan como regresión permanente de su contrato, recomputando la
derivación de ids de forma INDEPENDIENTE.

**Langfuse** queda documentado como perfil OPCIONAL aguas abajo del collector,
con el bloque de exporter listo para descomentar y las credenciales por env var
(EG-3). El proyector no sabe que existe: exporta OTLP y no le importa quién
escucha — ese es el punto de que la costura sea un collector.

### Tabla de interacciones — #162

| Interfaz tocada                    | Dominio afectado | Estado del contrato                                        |
| ---------------------------------- | ---------------- | ---------------------------------------------------------- |
| `projectors/otel` (paquete)        | observabilidad   | NUEVO — fuera de `blite.*`; 2 contratos de imports         |
| rol `chimera_otel` + init script   | infra            | NUEVO — SELECT sobre `events` y nada más                   |
| perfil `otel` del compose          | infra            | NUEVO — fuera del camino por defecto                       |
| `events` (tabla)                   | A (runtime)      | **NO TOCADA** — solo lectura                               |
| fixture `contract/observabilidad/` | costura          | NUEVO — golden + anti-drift; sin espejo Studio (declarado) |
| seeds S-F                          | costura          | xfail RETIRADO — 3 tests de regresión permanente           |

### Handoff parcial de la sesión PLATAFORMA (dominio O) — estado al 2026-08-05

**Rama `mejorado/plataforma`, 6 commits sobre `mejorado/base` @cebbfe5, sin push.**

| ítem                      | estado                                                                    |
| ------------------------- | ------------------------------------------------------------------------- |
| O11 gate multi-capa       | **CERRADO** (#154) — trinquete + 16 fugas declaradas, probado con canario |
| O8 corpus runner          | **CERRADO** (#155) — KPI vivo sobre corpus C3; halló el hueco de N=12     |
| O2 enforcement + vendor   | **CERRADO** (#157) — gitleaks en pre-commit probado; árbol fuera          |
| O12 guards de datos       | **CERRADO** (#160) — guard nuevo de nexus + job de CI; probado que muerde |
| hallazgos 9/10            | **CERRADOS** (#159) — con evidencia; 9b resuelto por los hechos           |
| O3 proyector OTel         | **CERRADO** (#162) — DoD VIVO contra collector real                       |
| O4 Croissant              | **PENDIENTE**                                                             |
| O5 MCP gobernado          | **PENDIENTE** — el más grande de los que quedan                           |
| O9 protocolo convergencia | **PENDIENTE**                                                             |
| O10 1-pager SEPs          | **PENDIENTE**                                                             |
| O7 deck.gl                | **NO evaluado** — condicional por umbral, no es compromiso                |

**Gates al cierre parcial** (worktree, `uv run` directo — la receta #83 quedó
caduca, ver #161):

| gate                  | resultado                                                  |
| --------------------- | ---------------------------------------------------------- |
| `pytest`              | **1283 passed** / 9 skipped / 6 xfailed / 4 xpassed        |
| cobertura             | **90.27 %** (mínimo 30 %)                                  |
| `lint-imports`        | **17 contratos kept, 0 broken** (3 nuevos: O8 ×1, C-11 ×2) |
| `ruff check`          | limpio                                                     |
| `ruff format --check` | limpio (**gate que faltaba en el bloque REGLAS** — #156)   |
| `pyright`             | **0 errores**                                              |
| `markdownlint`        | 0 · `prettier --check` 0, ya sobre el repo COMPLETO        |

Baseline al abrir: 1205 passed / cov 91.62 %. Los 6 xfailed que quedan son 3
menos que el baseline: los seeds S-F del proyector entraron en verde y su xfail
se retiró (jamás borrados).

**Dos cosas BLOQUEADAS EN DYLAN, ninguna es deuda de esta sesión:**

1. **Exposición viva del vendorizado (#158)** — el repo YA es público y el
   material de terceros está publicado. Hace falta `git filter-repo` +
   force-push (el clasificador de la sesión los bloquea) y, idealmente, pedirle
   a GitHub Support la purga de objetos sueltos.
2. **Push de esta rama** — como manda el bloque REGLAS.

**Una cosa REPORTADA a otra sesión (#156):** las 2 violaciones de
dependency-cruiser del Studio (`App.tsx ↔ router.tsx` circular y `App.tsx →
gatewayClient.ts` contra F3). Son de P-ui/V y son estructurales. **Hasta que se
arreglen, el job Web de CI sigue rojo** aunque todo lo demás esté verde.

**El stack quedó ARRIBA** (`docker compose --profile otel`) para el DoD de O5.
Bajarlo: `docker compose --profile otel down`.

### #163 — dependabot desbloqueado: 15 vulnerabilidades cerradas, y por qué estaban ahí

**Encargo de Dylan (2026-08-06): «podés arreglar los errores del dependabot».**

**El diagnóstico, no el síntoma.** Los updates de npm fallaban TODOS con el
mismo error, en el log del updater:

```
corepack pnpm update brace-expansion@5.0.9 --lockfile-only --no-save -r
[ERR_PNPM_MISSING_TIME] The metadata of @radix-ui/react-id is missing the "time" field
This error happened while installing the dependencies of radix-ui@1.6.0
```

`minimumReleaseAge` (cuarentena de 14 días) vivía en `pnpm-workspace.yaml` y
terminaba haciendo **lo contrario de lo que promete: bloquear las
actualizaciones de SEGURIDAD**. El proxy sandboxeado del updater no devuelve el
campo `time` de todos los paquetes; con `resolutionMode: highest` los de primer
nivel solo sacan un WARN («skipping the minimumReleaseAge check»), pero al
re-validar el árbol TRANSITIVO revienta y aborta el update entero
(pnpm/pnpm#9963, dependabot/dependabot-core#13165).

La sesión anterior ya lo había topado y respondió agregando paquetes a
`minimumReleaseAgeExclude` — cinco entradas. **No se gana así**: el paquete que
revienta cambia en cada corrida y es transitivo. Seguían fallando cinco
actualizaciones de seguridad.

**Decisión: la cuarentena se muda entera a Dependabot.** `dependabot.yml` ya
declara EXACTAMENTE la misma política (`cooldown` 14/90/14/7) y además la
implementa bien — las actualizaciones de seguridad la saltan a propósito, que es
justo lo que `minimumReleaseAge` no sabía hacer. Lo único que se cede es la
cuarentena de un `pnpm add` MANUAL: un acto raro, deliberado, y todavía cubierto
por `pnpm audit --audit-level=high` en CI. Vuelve el día que el bug upstream se
resuelva; el porqué queda escrito en el archivo.

**Y el resultado, medido:**

| ecosistema | antes                            | después                                  |
| ---------- | -------------------------------- | ---------------------------------------- |
| npm        | **13 vulnerabilidades** (8 high) | **0** — «No known vulnerabilities found» |
| Python     | 3 (2 con fix disponible)         | **1** — solo diskcache, sin fix upstream |

npm: `overrides` para las cinco transitivas (`brace-expansion`, `fast-uri`,
`js-yaml`, `postcss`, `undici`) — ninguna es dependencia directa nuestra, así
que no hay `pnpm update` que las mueva; el override es el único camino.
Python: `aiohttp` 3.14.2→3.14.3 (CVE-2026-69244) y `cryptography` 49→50
(CVE-2026-69247), los dos que #159 había encontrado esperando detrás de la CI
roja.

**Nota de proceso (mía).** Los tres archivos de dependencias aterrizaron primero
en el checkout PRINCIPAL en vez de en el worktree, por confusión de directorio
de trabajo. Se detectó, se movió el cambio al worktree, se restauró
`mejorado/base` (`git status` limpio) y se reinstaló su `node_modules` — sus
tests del Studio vuelven a dar 299/32. Queda escrito porque el modo de falla es
real y silencioso: en un repo con cuatro worktrees vivos, un comando sin `cd`
explícito edita el árbol equivocado.

### #164 — el repo queda LISTO para el flip: todo lo configurable, configurado

**Contexto de Dylan (2026-08-06):** el repo pasó a privado para hacer estas
limpiezas y volverá a ser público; quiere dejarlo listo para cuando eso sea
definitivo, con lo que se pueda hacer hoy y **sin parches ni trucos**. Referencia
de estilo: `qnexus-mcp`.

**Configurado hoy (verificado contra la API, no supuesto):**

- **Topics**: 10, de vacío (`verifiable-computing`, `agentic-ai`, `provenance`,
  `in-toto`, `supply-chain-security`, `event-sourcing`, `quantum-computing`,
  `combinatorial-optimization`, `reproducible-research`, `mcp`).
- **`NOTICE`** (nuevo): el material de terceros que SÍ viaja en el árbol —
  benchmarks IEEE vía pandapower (BSD-3), red del ICE, evidencia de Nexus (con
  el descargo nominativo de marca, como qnexus-mcp), y el árbol que ya NO está.
- **`CITATION.cff`** (nuevo): GitHub renderiza «Cite this repository» — una
  plataforma de investigación tiene que ser citable.
- **`.github/rulesets/main.json`** (nuevo): la protección de `main` como DATO
  versionado, con `scripts/apply-repo-rulesets.sh` que la aplica e **idempotente**
  (actualiza si ya existe). Hoy la API responde 403 «Upgrade to GitHub Pro or
  make this repository public»; el script lo dice con esas palabras en vez de
  escupir el error crudo.
- **`docs/pre-flip-checklist.md`** (nuevo): qué está listo, qué no se puede y
  **con qué causa verificada**, y los cinco comandos del día del flip en orden.

**Lo que NO se puede hoy, con la causa comprobada** (no inferida): rulesets →
403 (Pro o público) · reporte privado de vulnerabilidades → **404** en repo
privado · secret scanning + push protection → **422** (GHAS) · code scanning y
Scorecard → mismo caso. Cada uno con su comando exacto en el checklist.

**Lo que ya estaba bien y se deja constancia**: merge squash-only sin merge
commits ni rebase (historia lineal por construcción — justo lo que Dylan pidió),
borrado de rama al mergear, alertas de Dependabot activas, arreglos de seguridad
automáticos activos.

**Licencia del corpus ICE — investigada (parte de O4).** Contra el feed DCAT del
portal `datos-ice-se.opendata.arcgis.com` (2026-08-06): publisher **ICE**,
`accessLevel: "public"` en todo el catálogo incluidos `Subestaciones` y
`LineasDeTransmision`, y **ningún identificador de licencia estándar** (no
CC-BY, no ODbL, no dominio público; un dataset hermano dice «Uso Público» en
texto libre). Queda estampado en `NOTICE` §2 con la pregunta abierta explícita:
«datos abiertos, acceso público» **no es** una concesión de redistribución de
obras derivadas. Antes del flip: conseguir los términos, o sacar del árbol
publicado las instancias `ice-*`/`cr*-*` y quedarse con las IEEE, que no tienen
esa ambigüedad.

**Historia**: por decisión de Dylan, la corrección integral se hace DESPUÉS de
Mejorado, en una sola pasada. Queda anotada en el checklist §4, no ejecutada.

### Tabla de interacciones — #163/#164

| Interfaz tocada                       | Dominio afectado | Estado del contrato                                                     |
| ------------------------------------- | ---------------- | ----------------------------------------------------------------------- |
| `pnpm-workspace.yaml`                 | build/seguridad  | CAMBIO DE POSTURA — cuarentena delegada a Dependabot, con causa         |
| `pnpm-lock.yaml` · `uv.lock`          | build            | 15 vulnerabilidades cerradas; suite y Studio verdes tras el bump        |
| `NOTICE` · `CITATION.cff`             | legal/OSS        | NUEVOS                                                                  |
| `.github/rulesets/` + script          | repo             | NUEVO — dato versionado, inerte hasta el flip por límite real de GitHub |
| `docs/pre-flip-checklist.md` + índice | docs             | NUEVO                                                                   |
| `SECURITY.md`                         | seguridad        | ANOTADO — la ruta de reporte cambia al flujo privado en el flip         |
| topics del repo                       | repo             | 10, desde vacío                                                         |

### #165 — el override de `undici` rompía el Studio entero: se corrige por la vía correcta

**Cazado verificando, no en review.** El override `undici: '>=7.29.0'` de #163
dejaba los **32 archivos de test del Studio sin arrancar**:

```
Failed to start threads worker for test files …
Caused by: Error: Cannot find module 'undici/lib/handler/wrap-handler.js'
  … jsdom@29.1.1/lib/jsdom/browser/resources/jsdom-dispatcher.js
```

`jsdom@29.1.1` declara `undici: ^7.25.0` — o sea que 7.29.0 está DENTRO de su
rango — pero requiere `lib/handler/wrap-handler.js` por ruta interna, y undici
lo eliminó en un release **menor**. El rango semver decía «compatible» y no lo
era.

**Corregido subiendo `jsdom` a ^30.0.1**, que pide `undici ^8` — fuera del rango
afectado por la alerta (7.0.0–7.28.x). El override de `undici` se BORRA: ya no
hace falta, y mantener uno que no se necesita es deuda que alguien va a tener
que descifrar después. `pnpm audit`: **sin vulnerabilidades conocidas**.

La lección, escrita porque se repite: **un override de seguridad es un cambio de
comportamiento, no un número**. Forzar una versión «dentro del rango» de un
consumidor no garantiza nada si ese consumidor usa rutas internas. Se verifica
corriendo la suite, no leyendo el semver.

**Flake preexistente encontrado de paso (para P-ui/V, no lo toco).**
`apps/studio/src/lenses/registry.test.ts` → «los jobs del fixture llevan
capability_id» falla intermitente con **timeout de 5000 ms** (1 de 3 corridas,
con la máquina cargada). No es corrección: el test hace `await import()`
dinámico y bajo carga la transformación del módulo pasa los 5 s. Lo arregla su
dueño subiendo el timeout o quitando el import dinámico.

### Handoff de PLATAFORMA — actualización tras el encargo del 2026-08-06

El handoff parcial de más arriba sigue vigente en su tabla de ítems (O4, O5, O9
y O10 siguen PENDIENTES; O7 sin evaluar). Lo que cambió después:

- **#163/#165 — dependencias**: 15 vulnerabilidades cerradas (npm 13→0,
  Python 3→1). Dependabot vuelve a poder actualizar npm.
- **#164 — flip**: todo lo configurable en un repo privado quedó configurado, y
  lo que no se puede tiene su causa verificada y su comando listo en
  `docs/pre-flip-checklist.md`.
- **Historia**: por decisión de Dylan NO se ejecuta cirugía ahora; la corrección
  integral va después de Mejorado, en una pasada única.
- **depcruise del Studio**: lo toma otro agente (Dylan, 2026-08-06). Sigue
  siendo lo único que mantiene rojo el job Web.
- **#166 — O5 CERRADO** (DoD vivo en compose). El handoff de más arriba lo
  listaba PENDIENTE: quedan **O4, O9 y O10**, más O7 sin evaluar.

**Gates al cierre de este tramo**: pytest **1283 passed** / cov 90.27 % ·
lint-imports 17/0 · ruff check y `format --check` limpios · pyright 0 ·
Studio **299 passed / 32 files** · eslint 0 · `pnpm audit` sin vulnerabilidades ·
`pip-audit` solo diskcache (sin fix upstream) · guards de datos verdes.

### #166 — O5/M13: un tool MCP ajeno, invocado como capability GOBERNADA

**Ejecuta C-12.** La resolución decía la parte difícil: los manifests de terceros
NO son `CapabilityManifest` de primera clase. Si cada tool ajeno se registrara
como capability propia, su vocabulario entraría a un manifest nuestro y ADR-029
se caería el primer día.

**Lo construido, y qué hueco tapa cada pieza:**

| pieza                                     | qué es                                                 | hueco que cierra                                      |
| ----------------------------------------- | ------------------------------------------------------ | ----------------------------------------------------- |
| `blite.runtime.distribution`              | el `DistributionManifest`, MATERIALIZADO               | el freeze §1 lo daba por existente desde el principio |
| `distributions/chimera/distribution.yaml` | la allowlist real (servers + tools + egress + pins)    | C-12: el vocabulario del tercero como DATO con digest |
| `blite.protocols.mcp`                     | el round-trip (egreso, por eso vive en `protocols`)    | M13 no tenía adapter                                  |
| `ServiceStrategy` (`runtime.dispatch`)    | la estrategia de red del perfil `service`              | la tabla de despacho tenía UNA sola entrada real      |
| `blite_cap_mcp`                           | UNA capability genérica para cualquier tool ajeno      | C-12, literal                                         |
| `chimera_api.mcp_wiring`                  | la attestation de importación (`builder.id = mcp://…`) | O5 lo pedía explícito                                 |

**Y dos piezas que estaban construidas sin caller** (censo 07 §8.1-2) ahora lo
tienen: `validate_interaction_profile` se llama al CARGAR el manifest —
fail-closed en deploy, no en la primera invocación— y los `version_pins` que
`registry.py` esperaba («trabajo pendiente del DistributionManifest») tienen de
dónde salir.

**Cuatro decisiones con su porqué:**

1. **`side_effects: irreversible-external`.** Es el piso honesto: no sabemos qué
   hace el tool de un extraño, y asumir reversibilidad inventaría una garantía
   que no tenemos. La regla de reintentos del freeze §13 LEE ese campo — un
   default optimista haría que el runtime reintente algo irreversible.
2. **`invoke()` de la capability SIEMPRE levanta.** No es una limitación: es
   `execution_profile: service`. Si el despacho llegara ahí, un fallback
   silencioso a in-process ejecutaría un tool ajeno saltándose allowlist, pin y
   attestation. Y sin invocador inyectado, `ProfileDispatcher` NO registra
   estrategia `service` — misma doctrina anti-fallback que `remote-job` sin cola.
3. **Que el servidor esté permitido NO permite todos sus tools.** Un servidor MCP
   puede añadir tools entre versiones; heredar permiso por pertenecer al servidor
   sería aceptar superficie que nadie revisó. Lista vacía = ninguno, jamás «todos».
4. **El `package_pin` es obligatorio, sin default.** `uvx paquete` sin versión
   trae lo que haya hoy en PyPI, y una capability gobernada no puede depender de
   eso. Es además lo que la attestation cita como `builder`.

**CEREMONIA REPORTADA, no ejecutada.** C-12 decía «reusa evidencia-externa» para
la attestation. **No se puede sin mentir**: `ExternalImportStatement` valida
llaves OBLIGATORIAS `circuit_digest` y `shots_requested` — es un import de job
CUÁNTICO con nombre genérico (`ExternalImport/v1`). Una llamada a un tool MCP no
tiene circuito ni shots, y rellenarlas sería fabricar campos para pasar un
validador. Generalizar ese modelo toca contrato congelado ⇒ ceremonia, y una
sesión de dominio no la ejecuta sola. Mientras tanto se emite un predicado
propio y ADITIVO (`https://blite.dev/McpToolImport/v1`), misma forma in-toto
Statement v1; el día de la ceremonia se fusionan. **Es también un hallazgo de
agnosticismo en un CONTRATO, no en código.**

**Qué certifica la attestation y qué no:** que este despliegue invocó ESTE tool,
en ESTE servidor, con ESTE pin, bajo ESTA configuración (digest del manifest), y
que el resultado tiene ESTE digest. **No** dice que el resultado sea correcto —
un tool ajeno no es un ancla (misma ortogonalidad que la evidencia de Nexus). Los
argumentos viajan por DIGEST: los pone el proponente y una attestation no es
lugar para contenido.

**DoD VIVO** — round-trip real contra `qnexus-mcp` 0.2.0 (10 tools publicados):

```
perfil: service → ServiceStrategy
is_error: False
content: [{"type":"text","text":"{\"logged_in\":false,\"hint\":\"run: qnx login\"}"}]
builder: mcp://qnexus-mcp/nexus_auth_status
pin: qnexus-mcp==0.2.0 | reportado: qnexus-mcp 0.2.0
manifest digest: b4e42a7e4e4f8072…
```

Y las dos negativas, también en vivo: `nexus_submit_job` (tool fuera de la
allowlist) y `servidor-pirata` (servidor no declarado) → `McpInvocationRefused`
antes de tocar la red. La respuesta «logged_in: false» es la correcta y honesta:
el contenedor no tiene sesión de Nexus, y el punto del DoD es la ruta gobernada,
no el contenido de la respuesta.

**DoD VIVO EN COMPOSE** (`docker compose exec api`, imagen reconstruida con la
distribución que declara el servidor):

```
perfil service -> ServiceStrategy
is_error: False
content: [{"type":"text","text":"{\"logged_in\":false,\"hint\":\"run: qnx login\"}"}]
builder: mcp://qnexus-mcp/nexus_auth_status
pin: qnexus-mcp==0.2.0 | reportado: qnexus-mcp 0.2.0
manifest digest: b4e42a7e4e4f
qnexus-mcp/nexus_submit_job -> McpInvocationRefusedError
servidor-pirata/x          -> McpInvocationRefusedError
```

**Hallazgo de despliegue, corregido:** el usuario del contenedor se crea con
`--no-create-home` (a propósito), así que `uvx` moría con «failed to create
directory /home/chimera/.cache/uv». Se le da caché propia por volumen
(`UV_CACHE_DIR=/app/var/uv-cache`) y el Dockerfile crea `var/` ANTES de que
docker monte los volúmenes — sin eso, un volumen sobre un directorio inexistente
queda de root y el proceso no puede escribir. **Nota para producción**: con
caché fría, la primera invocación baja el paquete de PyPI. Pre-hornear el
servidor en la imagen quita esa dependencia de red en runtime y es lo correcto
para un despliegue real; queda anotado, no hecho.

**Segundo hallazgo, del propio arreglo:** dar `HOME` efímero al proceso ajeno
rompía la caché de `uv` — cada invocación volvía a bajar ~90 MB de la red
(medido). Aislar el ESTADO del tercero no es lo mismo que tirar el trabajo ya
hecho: el `HOME` sigue siendo efímero (su config no persiste) pero
`UV_CACHE_DIR` apunta a la caché del proceso padre. Verificado: la segunda
invocación instala desde caché en 2 s.

**Efecto colateral del extra `mcp`, limpiado:** trajo tipos mejores de httpx y
dejó **20 `# pyright: ignore[reportUnknownMemberType]` sin nada que silenciar**
en tests de otras sesiones. `reportUnnecessaryTypeIgnoreComment = "error"` es
deliberado en este repo (un ignore que no silencia nada ES un error), así que se
removieron. Uno llevaba prosa pegada al comentario y quedó como comentario
propio, no borrado.

### #167 — O4/M10: el corpus deja de ser dato interno y pasa a dataset publicable

**El problema real de C-13, en una frase:** un mismo documento JSON admite más
de un digest legítimo, y publicar «el digest» sin decir cuál no verifica nada.

Son tres, y las tres son correctas a la vez sobre el MISMO archivo:

| digest             | sobre qué                              | quién lo usa                    |
| ------------------ | -------------------------------------- | ------------------------------- |
| `file_sha256`      | los BYTES distribuidos                 | quien descarga (`sha256sum`)    |
| `embedded_digest`  | el JSON compacto SIN la llave `digest` | la identidad interna del corpus |
| `canonical_digest` | `C(documento)` del anexo, entero       | el kernel de confianza          |

Los bytes cambian con un final de línea y el interno no; el interno ignora su
propia llave y el canónico no. Hay un test que lo demuestra guardando el mismo
documento con otra indentación: cambia uno, los otros dos no.

**Dónde va cada uno.** Croissant reserva `sha256` por archivo para los bytes
distribuidos — literal. Meter ahí el digest interno haría que `sha256sum`
fallara para todo el que descargue, y una verificación que falla siempre enseña
a ignorar la verificación. Así que `sha256` son los bytes, y los tres viajan
etiquetados —y con su explicación en inglés, DENTRO del export— en un
`RecordSet` inline. Un tercero no debería tener que leer nuestro repo para
saber cuál es cuál.

**Ninguno se recalcula para que cuadre con otro.** El interno se comprueba al
leer; si no coincide, `load_corpus` explota. La regla del freeze §15.3 es que
el digest manda: un archivo que dejó de coincidir es un incidente, no una
oportunidad de re-sellar. El modo de falla que el test prohíbe es el cómodo.

**Un `FileObject` por instancia, sin archivo comprimido.** Lo idiomático en
Croissant (un `.zip` + un `FileSet`) exigiría publicar el `sha256` de un
archivo que no existe. Un digest inventado en el campo que el spec reserva para
verificar es peor que un export menos elegante.

**Validado con el cliente real, no con un modelo nuestro del formato.**
`mlcroissant` —la implementación de referencia de MLCommons— sobre los datasets
que el manifest declara de verdad: **cero errores y cero avisos**, más un
round-trip que lee de vuelta las instancias y compara los tres digests contra
el catálogo. Los avisos se exigen igual que los errores: son propiedades
recomendadas (cita, fecha) y un dataset publicado sin decir cómo citarlo es
menos usable, que es justo lo que este export existe para arreglar.

**Agnosticismo por construcción, otra vez.** El código no sabe qué datos hay:
un despliegue los DECLARA en `distribution.yaml` (`DatasetSpec`) y el catálogo
sale de ahí. Cambiar de dominio es editar configuración. Misma forma que C-12
usó para los servidores MCP, y por el mismo motivo: ADR-029 se sostiene sin
vigilancia. `license` no tiene default a propósito — un default («desconocida»)
sería una respuesta inventada a una pregunta legal.

**Lo que NO se declara, y por qué.** El corpus de islanding se queda fuera del
catálogo: procedencia mixta, datos de ejemplo de UN reto, portal de origen sin
identificador de licencia (`NOTICE` §2). **Decisión de Dylan (2026-08-08):**
esos datos eran el ejemplo del reto 1 y no tienen que sobrevivir a Mejorado
salvo como datos de prueba. Un dataset que no se puede licenciar con claridad
no se publica.

**Hallazgo que eso destapó, y que hay que mirar antes del flip:**
`knowledge/nexus/` —la evidencia real de H2-1LE, la más fuerte que tiene el
proyecto— **se ancla a las instancias `cr6-*`/`cr8-*`**, que son derivadas del
ICE. Borrarlas la huérfana. Por eso `NOTICE` §2 y el checklist pre-flip ahora
recomiendan sacar el **geojson crudo** (la copia verbatim del portal) y
conservar las instancias derivadas, con el mismo razonamiento que ya usa §1
para pandapower. Queda escrito con sus dos comprobaciones obligatorias, no
ejecutado: toca archivos de otras sesiones.

**Un test ajeno cazó un hueco que introduje:** `test_studio_nginx_config.py`
deriva el allowlist del proxy de las rutas reales del API, así que
`/datasets` sin su prefijo en nginx se puso rojo acá y no en el navegador
—donde el síntoma habría sido «HTML donde esperaba JSON», que no menciona a
nginx por ningún lado.

**Deuda que este ítem hace visible (no la resuelve):** `runs.py` y
`instance_verifiers.py` siguen cableando tres directorios de corpus por ruta
literal. El `datasets:` del manifest es la forma de quitarles eso, pero rehacer
la resolución de verificadores es G3 («dispatch por clase de problema»), de
otro dominio. Se reporta, no se toca.

### #168 — O9: el protocolo de convergencia deja de vivir en un commit huérfano

**El problema no era la falta de método, era dónde vivía.** El procedimiento
completo estaba pinneado a `git show 68af0c1:docs/research/protocolo-auditoria-ratificaciones.md`
— un commit de una rama de ejercicio que no está en el árbol. Si alguien poda
esa rama, el método desaparece y el acta de S-F queda citando un fantasma
(hallazgo 10 del handoff S3). Un procedimiento que la organización usa no puede
depender de que nadie limpie ramas. Portado a `docs/protocolo-convergencia.md`
como MÉTODO —sin las cifras de aquella corrida, que son acta y no se tocan—.
**La rama ya se puede podar.**

**Qué se mecanizó, y qué no.** Clasificar NO: decidir si dos hallazgos son el
mismo defecto es leer y juzgar, y una herramienta que lo adivinara produciría
una matriz que se ve rigurosa sin serlo. Lo que sí se mecaniza es **impedir que
una clasificación no ganada llegue a veredicto**, porque ahí está el sesgo y
tiene dirección conocida: quien arma la matriz quiere que converja.

No es teoría. En la única corrida real del protocolo, la pasada de refutación
**reclasificó 3 ejes que estaban en A** — dos fallaban el test del paraguas y
uno era ósmosis del auditor, no un avistamiento independiente. Y **A es lo que
sostiene el veredicto**. Así que:

- un eje en A exige **evidencia primaria de AMBAS fuentes** (sin eso no se
  distingue convergencia de que el auditor ya supiera qué buscar);
- una convergencia parcial exige el **test del paraguas** registrado y pasado;
- los dos criterios del veredicto que no se computan desde la matriz
  —«ninguna decisión congelada invalidada», «la sustancia sobrevivió ambas
  pasadas»— hay que **declararlos con evidencia** o no hay veredicto.

**Sale 2, no 1, cuando la matriz está mal formada.** «No se pudo leer» no es
«divergen». Confundirlas dejaría que un gate encadenado tratara un error de
sintaxis como una conclusión sobre el trabajo.

**Contrato de imports en las dos direcciones.** El producto no importa el
auditor (sería meter una herramienta de proceso en el camino crítico de un run)
y el auditor no importa el producto (ataría un método general —dos revisiones
de cualquier cosa— a ESTE dominio).

### #169 — O10: el 1-pager white-box sale de la KB al árbol que un externo lee

`trust/16` §1.5 era el único argumento del corpus del tipo «esto una API cerrada
no lo puede copiar», y estaba enterrado en una nota de investigación. Extraído a
`docs/white-box-sep.md`. La nota sigue siendo la fuente (evidencia, citas,
licencias) y no se toca; el 1-pager es la versión entregable.

**Lo que se cuidó al extraerlo,** porque es material de pitch y el riesgo es
exagerar:

1. **Encabezado que dice que NO está implementado.** Es una posición, no una
   funcionalidad, y no hay compromiso de fecha.
2. **La madurez va en el cuerpo, no en una nota al pie:** paper de WORKSHOP
   (no track principal), código de investigación MIT con 91% notebooks y sin
   releases, y nadie lo productizó en dos años. Decirlo así —en vez de «tenemos
   SEPs»— es lo que hace que el argumento aguante una pregunta técnica.
3. **El caveat del proxy analyzer**, que acota el claim a un objeto epistémico
   preciso: la incertidumbre del GENERADOR sobre su propio significado, no
   fundamentación en la fuente.
4. **El encuadre no negociable, con su consecuencia dicha:** un score de SEP es
   `GuardrailSignal`, jamás acuña `Attestation` — `AnchorKind` no tiene
   `"model"` y eso es deliberado. Confundirlas no exagera una función:
   **desarma la credibilidad de toda la arquitectura de confianza** frente a
   quien sepa preguntar, que es justo el público de este argumento.

### Handoff de PLATAFORMA — cierre del alcance (2026-08-10)

**El backlog O queda cerrado salvo O7.** Los tres ítems que el handoff anterior
listaba pendientes están hechos: **#167 (O4)**, **#168 (O9)**, **#169 (O10)**.

| ítem         | estado                                                                                                                                                                      |
| ------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| O1–O5        | **CERRADOS**                                                                                                                                                                |
| O8, O11, O12 | **CERRADOS**                                                                                                                                                                |
| O9, O10      | **CERRADOS** (#168, #169)                                                                                                                                                   |
| **O7**       | **BLOQUEADO, no omitido** — el umbral de deck.gl exige medir FPS sobre un overlay de mapa que solo existe tras V1/M18, en la sesión V. No es compromiso (letra del encargo) |

**Lo que este tramo destapó y NO es mío de arreglar:**

1. **La evidencia de Nexus se ancla a instancias derivadas del ICE**
   (`cr6-*`/`cr8-*`). La salida al problema de licencia no puede ser borrarlas:
   huérfana la evidencia más fuerte del proyecto. `NOTICE` §2 y
   `docs/pre-flip-checklist.md` recomiendan sacar el **geojson crudo** y
   conservar las derivadas, con las dos comprobaciones obligatorias escritas.
   **Toca archivos de otras sesiones: reportado, no ejecutado.**
2. **`runs.py` e `instance_verifiers.py` cablean tres directorios de corpus por
   ruta literal.** El `datasets:` del manifest es la forma de quitárselo, pero
   rehacer la resolución de verificadores es **G3** («dispatch por clase de
   problema»), de otro dominio.
3. **Generalizar `ExternalImportStatement`** (toca contrato congelado ⇒
   ceremonia) sigue reportado para la sesión de control, sin ejecutar.
4. **La rama `ejercicio/sf-ratificacion-simulada` ya se puede podar**: su método
   está en `docs/protocolo-convergencia.md` (#168). El hallazgo 10 del handoff
   S3 queda cerrado.

**Lo que sigue rojo, y por qué no es mío:** el job **Web** — las 2 violaciones
de depcruise del Studio (App.tsx ↔ router.tsx circular; App.tsx → gatewayClient)
las toma otro agente por decisión de Dylan (2026-08-06).

**Gates al cierre** (worktree `mejorado/plataforma`, 2026-08-10):

- pytest **1392 passed** / 13 skipped / 6 xfailed / 4 xpassed · cobertura **90.23 %**
- `lint-imports` **18 contratos, 0 rotos** (el nuevo: aislamiento de `chimera_convergence`)
- `ruff check` y `ruff format --check` limpios · `pyright` **0 errores**
- Studio **299 passed / 32 files** — con el flake dependiente de carga ya
  reportado (`lenses/registry.test.ts`, import dinámico): falló una corrida,
  verde en la repetición
- `docs:lint` y `format:check` limpios
- `verify_corpus_digests` **24/24 internos, 24/24 contra tabla pinneada**
- gitleaks **sin hallazgos** en árbol e historia (era lo que tenía roja la
  compuerta Security — ver el arreglo de la allowlist)

## Sesión de CONTROL — cierre de Mejorado (2026-08-10)

### #170 — la colisión de numeración se resuelve por SUFIJO, no por renumeración

Las sesiones paralelas V y O anexaron al ledger en sus ramas y ambas arrancaron
en #153: V usó #153–#159 (bloque «sesión VISUAL/CIENCIA») y O usó #153–#169
(bloque «sesión PLATAFORMA»). Los commits de ambas —ya pusheados y PÚBLICOS—
citan sus números; renumerar cualquiera de los dos lados desincronizaría la
historia publicada del ledger. **Decisión:** los números duplicados se citan con
sufijo de dominio (`#153-V`…`#159-V` / `#153-O`…`#169-O`) y la secuencia
continua retoma aquí, en #170. La regla para futuras olas paralelas: la sesión
de control ASIGNA el rango a cada sesión en el prompt (p. ej. «usá #2xx»), para
que la colisión no vuelva a existir.

### #171 — validación de los merges V+O, y el veredicto terminado ≠ completado

V y O se auto-mergearon a `mejorado/base` sin pasar por control (11d2044 y
470e72c). Gates re-corridos EN VIVO sobre `HEAD @470e72c` en el repo principal:

| gate               | resultado                                              |
| ------------------ | ------------------------------------------------------ |
| `uv run pytest`    | **1593 passed / 12 skipped / 1 xfailed / 4 xpassed**   |
| cobertura          | **90.87%**                                             |
| `lint-imports`     | 18 contratos kept, 0 broken                            |
| `ruff check` + fmt | limpios (los 20 archivos rojos del handoff V: FIJADOS) |
| `pyright`          | 0                                                      |
| studio `test:run`  | **327 passed / 34 files** · eslint 0                   |
| `pnpm run arch`    | **0 violaciones** (el bloqueador del job Web: MUERTO)  |
| docs gate          | limpio                                                 |

Los merges quedan CONVALIDADOS. Pero la fase NO está completa: **C-2 no tiene
rastro en el repo** (ni rama local/remota ni entradas) — Dylan indica que pudo
haber corrido en su laptop sin push; **queda EN ESPERA de su verificación**. Si
existe: la sube, control la valida y mergea como checkpoint normal. Si no: su
destino se decide junto con la sesión estratégica (ver #173).

### #172 — `main` PÚBLICA sincronizada: el repo deja de mostrar el árbol viejo

Hallazgo: el repo es público con `main` como default y `main` estaba ~113
commits atrás — la cara pública era el árbol de la hackathon, con 14 alertas
dependabot que #163/#165 ya habían cerrado en `mejorado/base`. Con autorización
de Dylan (hoy): push fast-forward `0810d0a..470e72c` a `main`. Sin reescritura
de historia; reversible retrocediendo la ref. Efecto: QUICKSTART, retos 2/3,
Studio y los fixes de seguridad son ahora lo que un externo ve.

### #173 — los reencuadres de Dylan (2026-08-10): qué entra al cierre y qué va a visión

Dylan, disconforme con el estado del proyecto (features a medias, docs en caos,
agentes con contexto viejo), fija dirección. Registrado como decisiones:

1. **ICE = caso de uso / datos de prueba, jamás activo del producto.** Se
   ratifica la opción (b) del handoff de plataforma §1.1: sale el geojson crudo,
   se conserva lo derivado (que ancla la evidencia de Nexus), con las dos
   comprobaciones previas (índices de nexus + fixture propio para
   `test_geojson_to_graph.py`). Su único uso legítimo: CI, e2e, validación.
2. **El mapa es un ARTIFACT genérico de render geoespacial** disparado por el
   TIPO de dato (geojson/csv/json) o la salida del agente — al estilo de los
   artifacts de chat de Claude/ChatGPT. Ratifica el reencuadre del 2026-08-08:
   O7 se rediseña en el registry de lentes, no como vista del shell. El sistema
   COMPLETO de artifacts (editores, plano cartesiano, documentos, imágenes) es
   backlog de la fase VISIÓN.
3. **El saneamiento documental FINAL entra al cierre** (era el «refactoring
   documental final» diferido en #108–#118): la estructura y actualización de
   docs «se hace cada vez más insostenible» (Dylan).
4. **Auth/authz, sistema organizacional y chat se COMPLETAN** — «clave y
   necesario»: flip 401-obligatorio, tabla `projects` (ceremonia sobre
   `docs/esquema-datos-v2.md` con el DDL ya propuesto), formalización mínima de
   projects/workspaces (nunca se documentó), approval card contra un
   `approval.requested` real, cert 409 silenciado, P10 vivo.
5. **Nuevas capacidades de valor** (editor tipo Overleaf, suite completa de
   datos, research/deep-search, pipeline de publicación de papers, benchmark vs
   co-scientist y afines) → **backlog de la fase VISIÓN**; la sesión
   estratégica (Marco/valor/público meta) las ordena. No entran al cierre.
6. **V6/V7 REENCUADRADOS:** Nexus era requisito de la hackathon. El camino
   generalista ya existe — el patrón capability/MCP gobernada (#166-O); un
   backend cuántico concreto es un plugin de distribución, no core. V6-como-
   estaba se cierra por reencuadre; V7 (tradeoff QEC medido) pasa a visión.

### #174 — plan de cierre y el arreglo de raíz del contexto viejo

El plan de cierre vive en `docs/mejorado/09-cierre.md`: inventario completo
terminado→completado, tres frentes de implementación (CIERRE-PRODUCTO,
CIERRE-PLATAFORMA/CIENCIA, SANEAMIENTO-FINAL) + acciones de control, con rangos
de numeración asignados (#180+/#200+/#220+). Y se crea **`CLAUDE.md` en la raíz
del repo** — el arreglo de raíz al problema que Dylan señala («los agentes se
quedan con contexto viejo y sacan conclusiones absurdas»): estado actual del
proyecto como PRODUCTO, autoridades, reglas duras y gotchas, cargado por
cualquier agente al abrir el repo.

## Sesión CONFIANZA-2 Mejorado — C3→C15 (rama `mejorado/confianza-2`, 2026-08-05/06)

> Alcance del prompt generador (`docs/mejorado/05-plan-paralelo.md` §4):
> C3-C10 + extensiones #120 (C12-C15). **C11 NO entra** — su enunciado
> («MCP de salida, ingesta KG, Fargate/BYOC, al final del dominio y tras el
> flip OSS si llega») está repartido entre O5 y P12, y el prompt de esta
> sesión no lo lista. Se deja al backlog sin tocar.

### #153-C — C3/M3: las reglas del dominio entran como DATO SMT-LIB con digest

`RuleVerifier` + puerto `RuleBackend` + `RuleSet` (artefacto SMT-LIB 2
versionado). El `rule_digest` son los BYTES EXACTOS del archivo (Regla 1 del
anexo, como `policy_digest`) y el `rule_set_id` viaja DENTRO del artefacto —
un cargador que lo recibiera por parámetro dejaría que id y bytes deriven.

Decisiones que quedan estampadas:

1. **`rlimit`, jamás timeout de reloj** (#103): un corte por tiempo hace que
   `unknown` dependa de la máquina y el replay deja de ser determinista. La
   clase NO expone ningún parámetro de tiempo.
2. **El candidato se fija ENTERO o no se chequea nada.** Con un símbolo libre
   el solver ELIGE el valor que hace `sat`, y el `pass` diría «existe algún
   mundo donde se cumple» disfrazado de «el candidato cumple». Símbolo libre,
   símbolo ajeno, sort equivocado o float no finito ⇒ error de PROCESO.
3. **Cero techos rotos.** La v1 emite `property_rule` AL2. Un backend que
   devolviera prueba formal NO se emite en silencio ni se degrada escondiendo
   evidencia: explota nombrando la ceremonia pendiente (arm de prueba de
   reglas en `FormalExactPredicate`, freeze §4-iii). **Frontera declarada** —
   esa ceremonia queda para quien traiga cvc5.
4. La explicabilidad es la evidencia: además del `unsat_core` nativo, cada
   regla corre por separado, porque el core de Z3 es un subconjunto pequeño
   NO garantizado mínimo y presentarlo como diagnóstico completo engañaría.

`PropertyRulePredicate` gana `rule_set_id`/`rule_digest` (aditivos, trust/11
§1.5) y corrige dos campos intipables de la semilla: `unsat_core` era `str |
None` (el core ES un conjunto de reglas) y `status` era `str` libre teniendo
vocabulario cerrado. Sin emisores ni consumidores previos.

**Dependencia nueva:** `z3-solver>=4.16` como dep DIRECTA del engine (igual
que ortools y pandapower). Que la distribución ya lo instalara vía
`blite-cap-smt[z3]` era una dependencia implícita que se rompía al instalar
el engine solo.

### #154-C — C3: registro de confianza (`system:trust-registry`)

`●VerifierRegistered`/`●AnchorRegistered` y la proyección que produce los
`anchor_descriptors`/`verifier_descriptors` del Bundle. Antes se escribían a
mano en el generador: el punto 5 del checklist comparaba una lista contra otra
lista del MISMO autor. Ahora salen del log. Fail-closed: un `anchor_digest`
que no es sha256 no se registra, y la proyección lee SOLO su stream de sistema
(un evento homónimo en el stream de un run no inyecta descriptores).

Ciclo de vida (`Superseded/Deprecated/Revoked`) NO implementado: exige decidir
qué pasa con los certificados que citan un ancla retirada, y esa pregunta la
responde la StatusList (#157-C).

### #155-C — C4/M4: una constancia por isla, y las islas no inflan patas

`verify_all()` con default `= (verify(),)` (C-6/#106) + `ExecutionVerifier`
emitiendo una constancia POR ISLA (`step_id = island-{k}`, convención S-D §8)
con solo los checks de esa isla. Ambas rutas salen de la MISMA evaluación: si
cada una corriera sus propios checks, el bundle podría mostrar dos verdades
sobre el mismo run.

**La regla que lo hace seguro va en el mismo commit** (extensión del punto 7):
las constancias de un mismo verificador en un mismo run comparten
`independence_group`. Sin ella, partir un verdict en N y darle a cada parte su
grupo convierte UN verificador en las 2 patas que la Policy exige.

**Hallazgo de contrato:** la promesa «compat total, todo adapter hereda el
default» NO se cumple con typing estructural — un Protocol `runtime_checkable`
exige el ATRIBUTO para `isinstance`, y los 8 adapters del repo satisfacen
`Verifier` estructuralmente. Se declara explícito en los 8 y la promesa queda
viva por el helper `verify_all_of`, que aplica el mismo default desde afuera
para un adapter ajeno escrito contra el puerto viejo. Es el camino que usa el
orquestador.

Efecto observable: el golden path emite 3 `verification.completed` (1 formal +
2 islas) en vez de 2, con las MISMAS 2 patas. Los dos tests que contaban
eventos pasan a afirmar la propiedad real (grupos distintos).

### #156-C — C5/M28: hash-chain en el writer y el sub-run con integridad

Tres piezas que solo juntas cierran la letra del anexo §4:

1. **Hash-chain por evento** (`blite/events/chain.py`), génesis `""` — la
   elección EXPLÍCITA del anexo. Se computa en el writer, donde el evento
   queda definido y todavía no lo vio nadie. Las columnas `prev_hash`/`hash`
   de la semilla v2 por fin se llenan; CERO cambios de esquema.
2. **M28 — una sola fórmula.** `subrun.py` tenía prefijo, vista y
   canonicalización propios (frontera registrada en la fila «`sub_run_
provenance_hash`» de este ledger). El costo era concreto: el anexo manda
   que el verificador offline RECOMPUTE ese hash, y con dos fórmulas era
   imposible.
3. **Puntos 9 y 10 del checklist** + `sub_run_streams` y
   `provenance_chain_head` en el Bundle (el head va DENTRO del payload
   firmado: un valor de integridad fuera de la firma es un número que nadie
   atestigua).

**El `provenance_hash` NO se sustituye por el head todavía** — la promoción
que el anexo describe («sin cambiar forma») cambiaría el digest de todo
certificado ya emitido. Queda como ceremonia aparte, con el sustrato puesto.

**Postgres:** el `seq` ya no se decide dentro del INSERT (el hash necesita
id/seq/occurred_at antes de hashear). La concurrencia optimista no se debilita
— el `UNIQUE (stream_id, seq)` sigue siendo quien rechaza la carrera.
VERIFICADO VIVO contra Postgres 17 real: cadena correcta y
`ConcurrentAppendError` intacto.

### #157-C — C6/C7: DSSE por constancia y revocación comprobable (supersedes §7)

**C6 (T6 SUPERSEDIDO):** un sobre DSSE por constancia con predicate forma
**SLSA VSA** — se adopta la FORMA del estándar, no su stack, para que un
tercero con herramientas in-toto lea esto sin traductor. El `subject` es el
CLAIM (atarlo al run permitiría reusar el sobre para otro claim del mismo
run) y el `resourceUri` lleva el `step_id`, así que dos constancias por isla
no son indistinguibles una vez firmadas — es lo que hace a M4 «de primera
clase». El punto 7 exige que las dos vistas (embebida y firmada) coincidan
EXACTAMENTE. Con `attestation_public_keys` la separación S2 deja de ser
limitación declarada.

**C7 (T14 SUPERSEDIDO, acotado):** StatusList con forma W3C Bitstring como
artefacto estático firmado. El punto 11 es OPT-IN y esa es la resolución del
choque con el air-gap: sin lista la verificación offline sigue completa y el
punto DECLARA «válido a valid_as_of, revocación no comprobada». Para eso el
resultado de un punto gana `notes` — un checklist que imprimiera «12/12»
callando lo que no comprobó sería la ceremonia que T11 prohíbe.
`●CertificateRevoked` se emite en el stream del run (post-terminal, fuera del
corte) con actor humano y razón; los bits se PROYECTAN de esos eventos.
**`●CertificateReissued` sigue siendo Fase 2 declarada** — re-emitir exige
decidir qué pasa con el certificado anterior.

Detalles con causa escrita: índice 0 = bit más significativo (leerlo al revés
revocaría certificados ajenos); mínimo de 16 KB por PRIVACIDAD, no capacidad;
`gzip(mtime=0)` o el artefacto cambia en cada emisión; índice fuera de rango
= error, jamás «no revocado».

### #158-C — C8/M8 pieza 4: la llave sale del proceso (y tres hallazgos vivos)

El puerto `KeyProvider` existía desde S-G y nadie lo usaba. Ahora `assemble`,
los sobres de constancia y la StatusList firman POR EL PUERTO, con `purpose`
separados (`certificate`/`attestation`/`status-list`). Escalón 1
(`LocalKeyProvider`, efímero o del archivo del despliegue) y escalón 2
(`TransitKeyProvider` sobre OpenBao single-instance — el quorum de 3 resuelve
ALTA DISPONIBILIDAD, no seguridad). El api elige por env y **falla cerrado si
la custodia se configura a medias**: un Transit sin token no puede degradar a
llave efímera en silencio.

**VERIFICADO VIVO** (perfil `custody`, OpenBao 2.6.1): certificado firmado con
una llave que el proceso nunca vio → `check_bundle` 12/12 offline. La corrida
encontró tres cosas que ningún test de escritorio habría encontrado:

1. OpenBao 2.6 ELIMINÓ mlock — `disable_mlock` impide el arranque.
2. El volumen va en `/openbao/file` (path que la imagen crea con el dueño
   correcto); en una ruta propia lo crea Docker como root y el proceso —que no
   corre como root— no puede escribirlo.
3. **Transit devuelve la pública Ed25519 en base64 CRUDO, no en PEM.** El
   doble de protocolo del test asumía PEM y pasaba: un doble escrito de
   memoria prueba lo que uno cree, no lo que el servidor hace.

También salió del choque con la realidad el bug del script de init: `bao
status` sale con código 2 cuando el vault está sellado —estado normal— y con
`pipefail` la rama de unseal nunca corría.

### #159-C — C9/M8 pieza 5 (#105): prueba de inclusión engrapada

Rekor RE-ENTRA con causa: el descarte era correcto para la emisión _keyless_
con Fulcio (exige CA en línea al firmar); un log privado del que se extrae una
prueba que viaja DENTRO del bundle se verifica con aritmética. Qué agrega
sobre la firma: la firma no impide que el emisor produzca DOS certificados del
mismo run y le muestre uno a cada auditor.

Punto 12, opt-in como el 11. Exige que la hoja sea la de ESTE certificado —
una prueba de inclusión matemáticamente válida de otro documento es la forja
que un `verify` descuidado deja pasar.

**ALCANCE DECLARADO:** la mitad OFFLINE está implementada y probada (incluido
el árbol impar). El cliente de SUMISIÓN al log NO se escribió: hacerlo sin
ejercitarlo contra un servidor real produce código que falla en el primer
contacto — acaba de pasar en C8, y ahí sí había servidor para descubrirlo.
Perfil `transparency` del compose listo; comando en el handoff.

### #160-C — C10/M29: la relajación con responsable (§10 → código)

`OverridePayload` + `apply_override` que REGISTRA antes de aplicar (INV-4) —
por eso la función no recibe ni ejecuta la acción relajada: mezclarlas
permitiría aplicar primero «y de paso» registrar.

**Match EXACTO del permiso** (A6 lo asumía; queda por escrito):
`override:apply:global` no habilita un override de alcance `run` ni al revés.
La alternativa jerárquica hace que el permiso más peligroso sea también el más
cómodo. **`authorized_by` en snake_case** — el `authorizedBy` del §10 es prosa
con sabor TS. Y el autorizador que PRESENTA el override es el que queda
registrado: nadie inscribe a otro como responsable.

Un intento RECHAZADO no escribe: mezclar intentos con hechos haría que «hay un
override registrado» dejara de significar «hubo un override». AX2 con test
propio, sin camino de permiso más fácil que los demás.

### #161-C — C15: el punto 7 evalúa la Policy completa (CEREMONIA)

Ceremonia obligatoria porque cambia el veredicto de bundles estampados. La
evidencia de que no rompe nada vivo: la suite completa verde (1357), incluidos
los e2e de los tres retos, más un test que lo afirma sobre el bundle vigente.

Dos huecos, y el segundo es peor. `min_level` NUNCA se comprobaba (una
conclusión AL1 bajo regla AL3 pasaba). Y `MatchCondition.side_effects` se
ignoraba eligiendo la regla con el PRIMER `claim_type` que casara: en la
Policy que se distribuye HOY, la regla `{side_effects: irreversible-external}`
no tiene `claim_type`, así que era **INALCANZABLE** — un claim irreversible se
evaluaba con la regla `pure`. El caso más peligroso, juzgado por la vara más
laxa, con la regla estricta en el archivo dando la impresión contraria.

La corrección es monotónica: aplican TODAS las reglas cuyas dimensiones
restringidas satisface el claim y la exigencia es el MÁXIMO — el orden del
YAML deja de decidir. `min_level` se exige solo a lo VERIFICADO (una
refutación tiene AL0 por construcción). Los `side_effects` se derivan del
`claim.emitted`; `reversible-external` NO se infiere de un booleano.

**Efecto en el fixture:** `scripts/example-bundle.json` no emitía
`claim.emitted`, así que su conclusión se venía evaluando contra una regla que
no le correspondía. Ahora lo emite con sus portadores, como cualquier run real.

### #162-C — C12/C13/C14: tres puertos hacia lo que no es el reto 1

**C14 `ExecutionHarness`** (prepare/run/collect/dispose + guarda
PASS_TO_PASS): `dispose` corre SIEMPRE y la garantía vive en el helper, no en
que cada implementador recuerde su try/finally. La guarda cuenta como roto un
check que DESAPARECIÓ — borrarlo es la forma más limpia de «arreglarlo».
`isolation` declarado en la spec (AX3 deja de ser aspiracional en la forma).

**C13 análisis del SET de políticas:** `policy_diff.py` compara texto; la
pregunta real es si algún caso quedó más laxo, y se puede aflojar agregando
una regla, AMPLIANDO un `match` o reordenando. Se adopta la idea de Cedar
Analysis sin su motor: el dominio `(claim_type, side_effects)` es finito, la
comparación es exhaustiva por enumeración y usa el MISMO evaluador que el
checklist — un analizador con su propia noción de «exigencia» respondería
sobre una política que nadie aplica.

**C12 registro de detectores** con digest: los guardrails llegaban como
callables anónimos y dos corridas con detectores distintos dejaban rastros
indistinguibles. El pick de trust/16 (HHEM-2.1-Open + AlignScore) se declara
como ids con su `kind`.

**Hallazgo de arquitectura:** HHEM y AlignScore son MODELOS y el contrato
AX3-b prohíbe a `blite.guardrails` importar SDKs de modelo — un detector
model-backed no puede vivir en ese paquete. El registro recibe la puntuación
por un callable inyectado y el modelo corre detrás del puerto de
`blite.protocols`. No es una incomodidad del diseño: es lo que impide que un
«detector» se vuelva la puerta por la que un modelo entra sin mediación.
`GuardrailsStage` YA existía (la trajo C-1); el enunciado del ítem estaba
desactualizado.

### Tabla de interacciones — sesión CONFIANZA-2 (regla #3)

| Interfaz tocada                                                                                     | Dominio afectado           | Estado del contrato                                                             |
| --------------------------------------------------------------------------------------------------- | -------------------------- | ------------------------------------------------------------------------------- |
| `Verifier.verify_all()` + `verify_all_of`                                                           | G, V (verificadores)       | **EXTENDIDO** (C-6/#106 ya lo autorizaba); 8 adapters lo declaran explícito     |
| `Attestation.step_id` = `island-{k}`                                                                | V (M18/badges)             | convención S-D §8 CONSUMIDA — V ya puede atar badge↔isla                        |
| `verification.completed` ×N por isla                                                                | V, P-ui (SSE)              | **CAMBIO OBSERVABLE**: 3 eventos donde había 2, mismas 2 patas                  |
| `PropertyRulePredicate` (+`rule_set_id`/`rule_digest`, `unsat_core`, `status`)                      | G (reto 2)                 | ADITIVO + 2 correcciones de tipo sin emisores previos; fixture regenerado       |
| `blite.events.chain` (vista canónica + 2 hashes)                                                    | todos                      | **fuente ÚNICA** de la fórmula; `assemble`/`bundle_check`/writer/subrun la usan |
| `Event.prev_hash`/`hash` poblados                                                                   | O (proyector), infra       | columnas de la semilla v2, sin cambio de esquema                                |
| `PostgresEventStore.append` (2 statements)                                                          | infra                      | mismo puerto; concurrencia por `UNIQUE`, verificada viva                        |
| `assemble_bundle(key_provider=…)`                                                                   | api (2 sitios)             | **BREAKING** para el caller: `signing_key`/`keyid` → puerto                     |
| `RunResources.key_provider`                                                                         | api                        | reemplaza `signing_key`+`keyid`                                                 |
| Bundle: `sub_run_streams`, `attestation_envelopes`, `attestation_public_keys`, `transparency_proof` | verificador offline        | ADITIVOS, todos opt-in                                                          |
| Predicate firmado: `provenance_chain_head`, `status_list_entry`, `revocation:"status_list"`         | Studio (`CertificateView`) | ADITIVOS; el fixture del Studio se regeneró                                     |
| `PointResult.notes` + `check_bundle(status_list=…)`                                                 | CLI verify-bundle          | ADITIVO; el CLI imprime las notas                                               |
| checklist 8 → **12 puntos**                                                                         | CP7, seed                  | el seed deriva el denominador; los 8 originales intactos                        |
| `compose.yaml`: perfiles `custody` y `transparency`                                                 | O (plataforma)             | servicios con `profiles:` — el mínimo canónico sigue en 3 sin perfil            |
| `override.applied` (`blite.gateway.override`)                                                       | C-1 (gateway), api         | tipo NUEVO del catálogo §14 aterrizado                                          |
| `blite.verification.harness` / `guardrails.registry` / `certificate.policy_analysis`                | G, O                       | puertos NUEVOS sin consumidor todavía                                           |

### Cierre de la sesión CONFIANZA-2 — CP7 vivo y qué NO se verificó

**Alcance CERRADO:** C3, C4, C5 (+M28), C6, C7, C8, C9, C10 y las
extensiones #120 (C12, C13, C14, C15). **C11 no entra** (ver encabezado de esta sesión).

**Gates al cierre** (worktree `mejorado/confianza-2`, rama del mismo nombre
sobre `mejorado/base` @cebbfe5, sin push):

| Gate                           | Resultado                                        |
| ------------------------------ | ------------------------------------------------ |
| `pytest`                       | **1357 passed**, 9 skipped, 8 xfailed, 4 xpassed |
| cobertura                      | **91.50 %** (mínimo exigido 30 %)                |
| `lint-imports`                 | **14 contratos kept, 0 broken**                  |
| `ruff check`                   | limpio                                           |
| `pyright`                      | **0 errores**                                    |
| `pnpm -C apps/studio test:run` | **299 passed** / 32 files                        |
| `docs:lint` + `format:check`   | limpio                                           |

Baseline al abrir el worktree: pytest 1205 / cobertura 91.62 %.

**CP7 — VERIFICADO VIVO** (`scripts/verify-bundle.py`, no solo la librería):

```
12/12 puntos verificados                      · exit 0
11/12 con la StatusList que revoca ese índice · exit 1
```

Los 8 puntos originales conservan su semántica y un test lo prueba sobre un
bundle re-firmado SIN nada de lo que esta sesión agregó. Los puntos 9-12
declaran lo que no comprobaron en vez de callarlo.

**Verificado vivo además** (fuera del checklist):

- **Custodia real**: certificado firmado con una llave que vive en OpenBao
  2.6.1 (perfil `custody`) → 12/12 offline. Tres defectos encontrados y
  corregidos ahí (ver #158-C).
- **Hash-chain en Postgres 17 real**: cadena correcta desde la génesis y
  `ConcurrentAppendError` intacto.

#### Cómo reproducir las verificaciones vivas (para la sesión de control)

Los gates de esta sesión se corren con la receta de worktree (python del venv
del repo PRINCIPAL + `PYTHONPATH` del worktree; `uv sync` en un worktree no
instala los editables). Las tres corridas vivas, en orden de valor:

```bash
# 1 · CP7 offline — el checklist completo sobre el bundle vigente
python scripts/verify-bundle.py scripts/example-bundle.json          # 12/12, exit 0

# 2 · Custodia real (C8) — la llave vive en OpenBao, no en el proceso
docker compose --profile custody up -d openbao
scripts/openbao-init.sh                    # inicializa, desella, crea las 3 llaves
# luego: TransitKeyProvider(address=..., token=secrets/transit_token.txt)
#        → assemble_bundle(key_provider=...) → check_bundle 12/12

# 3 · Hash-chain durable (C5) — contra Postgres real
#     create_event_store(DSN) y comprobar prev_hash/hash + provenance_slice
```

**Trampa operativa (verificada en carne propia):** las sesiones paralelas
levantan SU compose con los MISMOS puertos publicados (5544 postgres, 8000
api, 3000 studio). Con `chimera-plataforma` arriba, `docker compose up` en
este worktree falla con «port is already allocated» — no es un defecto del
compose. Para verificar contra Postgres sin pelear por el puerto, se levanta
un contenedor aparte en otro puerto con `engine/sql/init_v2.sql` montado, o se
coordina el turno con la otra sesión. El perfil `custody` publica 8200 y el
`transparency` 3003: mismo cuidado si dos sesiones los usan a la vez.

#### Lo que NO se cerró, con causa

1. **Cliente de sumisión a Rekor (C9).** La mitad offline está probada; el
   cliente no se escribió porque hacerlo sin un servidor que lo ejercite
   produce código que falla en el primer contacto — pasó en C8 con la pública
   de Transit. Para retomarlo:
   `docker compose --profile transparency up -d rekor` y escribir el cliente
   contra `http://127.0.0.1:3003` con un round-trip real antes de mergear.
2. **Promoción del `provenance_hash` al head de la cadena.** El anexo la
   describe «sin cambiar forma», pero cambiaría el digest de todo certificado
   ya emitido: ceremonia aparte, con el sustrato ya puesto (#156-C).
3. **Arm de prueba de reglas en `FormalExactPredicate`** (`formal_exact` desde
   el `RuleBackend`). Hoy el adapter EXPLOTA si un backend devuelve prueba, en
   vez de inflar o esconder. Se abre cuando exista el backend cvc5 (#153-C).
4. **`●CertificateReissued`** sigue siendo Fase 2 declarada: re-emitir exige
   decidir qué pasa con el certificado anterior (#157-C).
5. **Ciclo de vida del trust-registry** (`Superseded/Deprecated/Revoked` de
   anclas y verificadores) — misma razón: qué pasa con lo ya emitido (#154-C).
6. **Los tres puertos nuevos no tienen consumidor todavía**
   (`ExecutionHarness`, registro de detectores, análisis de políticas). Son
   contratos con test, no features vivas: engancharlos es de G (un harness de
   dominio), O (el gate de políticas en CI) y C-1 (los detectores en la etapa).

#### Fronteras declaradas para la sesión de control

- **`assemble_bundle` cambió de firma** (`signing_key`/`keyid` → `key_provider`).
  Los dos sitios del api están migrados; cualquier rama sin mergear que llame
  al ensamblador va a chocar ahí, y es un cambio de una línea
  (`LocalKeyProvider(la_llave)`).
- **El golden path emite 3 `verification.completed`, no 2.** Es el efecto
  buscado de C4, pero V y P-ui consumen ese stream: la sesión V debería mirar
  `attestation.step_id` para el badge por isla en vez de asumir un evento
  único. El `step_id` TOP-LEVEL del payload (M23a) sigue siendo de V — esta
  sesión no lo tocó.
- **`docs/contract-freeze.md` §7 y §10 llevan marcas de supersede nuevas**
  (T6, T14 acotado, checklist de 12 puntos, match exacto del override). El
  anexo de canonicalización NO se tocó: sus fórmulas se implementaron tal cual.
- **`scripts/example-bundle.json` y el fixture del Studio se regeneraron** con
  `claim.emitted`, head de cadena y sobres por constancia. El generador sigue
  siendo auto-validante.
- **La policy de la distribución no cambió** — pero ahora su regla
  `irreversible-external` es alcanzable. Si algún claim del sistema empieza a
  declararse irreversible, exigirá 2 patas y ancla `solver`+`execution` de
  verdad.

### #175 — Integración de CONFIANZA-2 con `mejorado/base` (V + O ya mergeadas)

`mejorado/base` avanzó 37 commits mientras esta sesión corría (V y O mergearon).
La integración destapó cinco cosas que ninguna sesión podía ver sola — se
registran porque son el tipo de hallazgo que se pierde si solo vive en el
mensaje de merge.

1. **Colisión de numeración del ledger.** V, O y C-2 arrancaron a numerar desde
   #153 en paralelo. V+O ocuparon #153-#169; las de esta sesión se corrieron a
   **#153-C-#162-C** (con sus referencias internas). **Regla para la próxima ola:**
   quien abre worktree reserva su rango ANTES de escribir, o el ledger deja de
   ser una secuencia y pasa a ser tres.

2. **La granularidad por isla tenía que ser ADITIVA, no sustitutiva.** C4 hacía
   que `verify_all()` devolviera SOLO las constancias por isla; el productor de
   `partition` de V1/M18 (`build_partition`) deriva las islas agrupando los
   checks de UNA attestation, así que con la constancia de `island-1` producía
   una partición de una sola isla y la ruta de lectura la mostraba como el
   resultado completo. **Corregido:** `verify_all()` devuelve la GLOBAL primero
   y las de isla después. Quien pregunta «¿cómo le fue al resultado?» no tiene
   que re-agregar lo que el verificador ya sabe.

3. **`latency_ms` no se puede repetir por constancia.** `derive_run_metrics`
   (V2/M19) SUMA el campo por evento; estampar la latencia de la llamada en las
   N constancias que produce la multiplicaría por N. Se estampa en la primera y
   se OMITE en las demás — omitir dice «este evento no trae la medida», un 0.0
   diría «esto no costó tiempo», que es falso.

4. **El gate de agnosticismo multi-capa (O11) cazó tres docstrings míos**
   (`harness.py`, `rule_set.py`, `rule_z3.py` nombraban el simulador o el
   dominio del reto 1 al explicar por qué existe el puerto). Se REFORMULARON,
   no se declararon como excepción: el propio archivo de excepciones dice que
   añadir una entrada no es el camino barato. El trinquete funciona.

5. **`StructuralPartitionVerifier` (nuevo, de V) no declaraba `verify_all`.** Es
   exactamente el caso de compat de #155-C: a runtime funciona por
   `verify_all_of`, pero un Protocol `runtime_checkable` exige el atributo.
   Se le agregó el método explícito, como a los otros ocho adapters.

### Anotaciones sueltas de CONFIANZA-2 (deuda observada, sin ítem propio)

Cosas que se vieron trabajando y NO se tocaron, para que no se pierdan:

| Observación                                                                                                                                                        | Por qué importa                                                                                                                                                                                          |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `capabilities/smt` sigue siendo un stub que levanta `NotImplementedError`, y el comentario de la distribución dice «Z3 es el backend de reglas de C3/M3»           | El backend de C3 vive en el ENGINE, no en esa capability. O se implementa la capability, o el comentario de `distributions/chimera/pyproject.toml` se corrige — hoy promete algo que ese paquete no hace |
| `PropertyRuleVerifier` (reto 2, reglas como código) y `RuleVerifier` (C3, reglas como dato SMT-LIB) coexisten con la MISMA clase `property_rule`                   | Es deliberado y está documentado en ambos módulos, pero un tercero que agregue un tercer «rule verifier» necesita saber cuál extender                                                                    |
| `EphemeralSessionKeys` (api/auth.py) y `LocalKeyProvider` (engine) son el MISMO escalón 1 del mismo puerto, escritos dos veces                                     | Unificarlos es trivial ahora que el puerto está cableado; se dejó fuera para no mezclar C8 con la sesión de identidad                                                                                    |
| Aristas de paquete nuevas: `blite.events.chain` → `blite.certificate.canonical` (la única puerta de canonicalización) y `blite.certificate` → `blite.events.store` | Ningún contrato de import-linter las vigila hoy. Si alguien agrega uno de capas entre esos paquetes, romperá — conviene decidirlo a propósito                                                            |
| `scripts/example-bundle.json` se construye a MANO, no con `assemble_bundle`                                                                                        | Por eso pudo vivir sin `claim.emitted` (lo que C15 destapó). Generarlo con el emisor real lo mantendría honesto por construcción                                                                         |
| El remoto responde `This repository moved` en cada push: el origin apunta a `Blite-HQ/Chimera` y GitHub redirige a `Blite-HQ/chimera` (minúscula)                  | Funciona por redirección, pero es un rename sin propagar: conviene actualizar el `origin` de los worktrees y de la doc de onboarding antes del flip OSS, o un externo clonará la URL vieja               |
| El `checklist` pasó de 8 a 12 puntos y `PointResult` ganó `notes`                                                                                                  | Cualquier consumidor que muestre el checklist (Studio incluido) debería mostrar las notas, o volverá a decir «verificado» callando lo que no comprobó                                                    |

### #175 — C-2 VALIDADA Y CONVALIDADA (ya venía mergeada y pusheada) + P8 desbloqueado

**Fecha:** 2026-08-11. Dylan subió C-2 (16 commits lineales sobre 1df1e15,
C3→C15 completos) ya integrada en `mejorado/base` y pusheada @52c90fa. Forense:
los supersedes de `contract-freeze.md` §7 tienen ceremonia registrada y son
ADITIVOS (checklist 8→10→12 puntos sin invalidar bundles previos); `uv.lock` +2
líneas; segmento lineal limpio. **Gates vivos en el principal:** 1741 passed /
12 skipped / **0 xfailed** (las últimas semillas se implementaron) / 4 xpassed /
90.84% / 18 contratos / ruff+format limpios / pyright 0 / studio 327/34 /
`arch` 0 violaciones / docs verdes. **CP7 cerrado — el checkpoint de C-2 queda
CONVALIDADO.**

**P8 DESBLOQUEADO:** Dylan entregó las 21 referencias visuales; quedan en
`~/projects/blite/hackathons/2026/Quantathon/branding-refs/` (fuera del árbol a
propósito: material de terceros en repo público). Entra al alcance de F1.

La nota del rename del remoto (`Chimera`→`chimera` sin propagar, anotación de
C-2) queda asignada a F3/saneamiento-final.

### #176 — CEREMONIA ejecutada: la tabla `projects` entra al esquema v2

Supersede ADITIVO sobre `docs/esquema-datos-v2.md` §2 + espejo exacto en
`engine/sql/init_v2.sql` (candado bidireccional verde: 3 passed). DDL: el
propuesto por el handoff P-ui, sin cambios. Reglas que la acompañan:
`run.created.project_id` sigue siendo referencia OPACA (S-A Contrato-4) — el
evento NO valida FK; la valida el API al crear el run. F1 llena datos y cablea
la validación; el Studio ya consume (`AppShell`, router `:proj`).

### #177 — CEREMONIA ejecutada: tercera forma de body de `POST /runs` (ablación)

Extensión ADITIVA registrada en `docs/specs/endpoints-studio.md`:
`{ablation: {instance_id, layers?, seed?}}`, discriminada por presencia de campo
como `claim`/`mission` (`extra="forbid"`). Los brazos corren como SUB-RUNS y el
cierre métrico se DERIVA del log (V2/M19); los brazos NO los elige el caller
(regla #158-V; `mitigated` cuando V9 exista); fail-loud intacto. El wire HTTP lo
implementa F2. Con #176+#177 **F1 y F2 quedan desbloqueados**; prompts de
lanzamiento en `09-cierre.md` §5.
