# Mejorado — research de estado del arte (Etapa 2)

> **Estado: VIGENTE (2026-07-30).** Salida de la Etapa 2 del playbook. Tres frentes —
> los que el criterio #101 prioriza: generalidad (retos 2/3), producto usable y
> confianza profunda — investigados por agentes paralelos con web (fuentes primarias
> verificadas jul-2026, incluyendo el venv del repo en vivo), con las restricciones de
> Chimera como filtro obligatorio (runtime agnóstico, event-sourced con replay, DSSE
> offline, self-hosted single-node) y cruce contra `knowledge/`. Los reportes crudos
> completos con todas las fuentes viven en la sesión de control; aquí queda lo
> accionable. Convención: **ADOPTAR / ADAPTAR / DESCARTAR** por hallazgo.

## Tesis transversales (las tres se sostienen)

1. **La generalidad no exige tocar el runtime**: los retos 2/3 entran completos como
   paquetes `blite.capabilities` + datos con digest + verificadores registrados. La
   prueba de generalidad es literalmente «diff del runtime = 0». El patrón
   entry-points de Chimera ES el estado del arte (pytest ~1500 plugins, plugins de
   transpiler de Qiskit, spec oficial de packaging); los registries MCP 2026 son
   isomorfos (manifiesto tipado + discovery) y validan el diseño sin que haya que
   adoptarlos.
2. **El event-sourcing ya construido es ventaja estructural, no deuda**: los mensajes
   de chat como eventos del mismo log (patrón OpenHands/AG-UI) quedan DENTRO del
   `provenance_hash` — conversación certificada, algo que ningún producto estudiado
   ofrece; el event store durable es el buffer de reanudación SSE que la industria
   está construyendo aparte (Durable Sessions/Redis); y el sello de holdout por
   compromiso previo (Dwork et al., Science 2015) sale nativo del plan-como-eventos.
3. **La confianza profunda tiene camino incremental estándar**: attestation por-check
   = SLSA VSA/SVR (in-toto); hash-chain con forma ya congelada; revocación = forma
   Bitstring Status List como artefacto estático firmado; Rekor v2 GA con backend
   POSIX volvió viable lo que en jul-02 era overkill. Todo aditivo sobre el DSSE
   existente, todo verificable offline.

---

## R1 · Generalidad — retos 2 (kernel cuántico) y 3 (TFIM/Trotter)

Versiones verificadas EN VIVO contra el venv (29-jul): qiskit 2.5.0, qiskit-aer
0.17.2, qiskit-algorithms 0.4.0, pennylane 0.45.1, scipy 1.18.0, scikit-learn 1.9.0
instalados; qiskit-machine-learning 0.9.0 y quimb/TenPy/QuTiP/statsmodels NO.

### Reto 2 — kernel cuántico + SVM

| Hallazgo                                                                                                                                      | Veredicto                                                | Nota                                                                                                                                                                                                                                                                                                          |
| --------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `qiskit-machine-learning` 0.9.0 (dic-2025): Qiskit 2.x + primitivas V2, `FidelityQuantumKernel`/QSVC estables, Apache-2.0                     | **ADOPTAR**                                              | 1 dep nueva → fila de licencia (disciplina nota 07 §3). Alternativa sin dep: kernel a mano con `Statevector` (~15 líneas) + `SVC(precomputed)` — decisión de planning                                                                                                                                         |
| **`FidelityStatevectorKernel`** (caché de statevectors, `enforce_psd`, `shots` opcional)                                                      | **ADOPTAR** — el hallazgo técnico mayor                  | **DIVERGENCIA con nota 02 §2.2**: el presupuesto de 18 675 circuitos y el submuestreo a 100–200 train aplican al kernel por circuitos; en simulador statevector el límite desaparece — las 3 276 muestras completas son viables. Correr statevector + réplica con shots para conservar la narrativa PSD/ruido |
| Reparación PSD clip/flip/shift formalizada (Hubregtsen et al., PRA 106, 042431 (2022); `pennylane.kernels` ya instalado la implementa)        | **ADOPTAR** como spec del verificador                    | **CONVERGENCIA fuerte con nota 04 §5.3** (clip + λ_min registrado + fail-loud) — ahora con paper citable. Clip como default; el método usado es dato del claim                                                                                                                                                |
| `zz_feature_map` en qiskit core (funcional, sin qiskit-ml); AngleEmbedding como 2ª opción de ablación                                         | **ADOPTAR / ADAPTAR**                                    | Feature map = DATO del claim (spec + reps + digest), no código — ADR-029 intacto                                                                                                                                                                                                                              |
| VQC/QNN como camino principal                                                                                                                 | **DESCARTAR** (reconfirmación de nota 02 §2.4 / 07 §1.3) | Con statevector kernel el argumento es aún más lopsided                                                                                                                                                                                                                                                       |
| Dataset Kaggle `water-potability`: **CC0**, 3 276 filas, balance 61/39, missing en ph/Sulfate/Trihalomethanes, **proveniencia INDOCUMENTADA** | **ADOPTAR con caveats sellados**                         | Refuerza `curated_internal` techo AL3 (nota 07 §1.6.3): el certificado dice «métricas sobre este CSV sellado», jamás «predice potabilidad real». Si el kit oficial trae CSV propio, su digest manda                                                                                                           |

**Qué es un claim verificable de un clasificador** (el análogo del CP-SAT — no existe
FORMAL_EXACT para generalización; techo GROUND_TRUTH → AL3):

1. **Holdout sellado por compromiso previo** (ADOPTAR): índices de folds + digest de
   etiquetas comprometidos en un evento del plan ANTES de entrenar; el verificador
   recomputa métricas desde predicciones almacenadas + etiquetas selladas. Respaldo:
   Dwork et al., _The reusable holdout_, Science 349 (2015). El event-sourcing lo
   implementa nativo.
2. **CV-5 estratificado** para el baseline SVM-RBF (protocolo OFICIAL del reto) —
   resuelve la divergencia ya auto-reconocida en la nota de drift de 02 §3 (split
   único vs CV-5): CV-5 para el comparativo oficial, holdout sellado como capa
   Chimera adicional.
3. **McNemar** cuántico-vs-clásico con `scipy.stats.binomtest` (ya instalado) —
   **statsmodels DESCARTADO** (dep evitable; fórmulas de nota 04 §6 + scipy bastan).
4. **PROPERTY_RULE del pipeline**: diag K=1, simetría, PSD (λ_min registrado),
   etiquetas barajadas anti-leakage (= nota 04 §5) + **aporte nuevo: chequeo KKT del
   dual del SVM** sobre (α, b, K) — el pedacito formal que SÍ existe en este dominio.

### Reto 3 — TFIM/Trotter

| Hallazgo                                                                                                                                                                                        | Veredicto                                             | Nota                                                                                                                                                                       |
| ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Qiskit core basta: `SparsePauliOp` + `PauliEvolutionGate` + `LieTrotter`/`SuzukiTrotter` (verificado en el venv)                                                                                | **ADOPTAR**                                           | Capas RZZ+RX = misma familia de compuertas del QAOA vivo → reuso de Aer/seeds/digest qasm3. **CONVERGENCIA literal con nota 07 §1.4**. **Cero deps nuevas**                |
| `TrotterQRTE` (qiskit-algorithms)                                                                                                                                                               | **DESCARTAR** como base                               | Envuelve lo mismo que ~10 líneas y quita el control fino (evento por paso, digest, shots/exact)                                                                            |
| Ancla 1: ED vía `scipy.sparse.linalg.expm_multiply` (N≤12, dim 4096, determinista, air-gapped)                                                                                                  | **ADOPTAR**                                           | El rol FORMAL_EXACT del criterio oficial (≤5% en ⟨Zᵢ⟩/⟨ZᵢZᵢ₊₁⟩, N=8)                                                                                                       |
| Ancla 2 (hallazgo nuevo): solución analítica por fermiones libres (Jordan-Wigner → Bogoliubov-de Gennes; Pfeuty 1970)                                                                           | **ADAPTAR** (stretch de alto valor)                   | Checker independiente de la ED = el análogo exacto del par CP-SAT+fuerza-bruta del reto 1; habilita doble ancla estilo AL4 (patrón nota 07 §1.6.3). ~100 líneas cuidadosas |
| Teoría del error de Trotter: Childs et al. PRX 11, 011020 (2021) — O(dt²) por conmutadores; **Heyl et al. Sci. Adv. 2019 — umbral en dt** (error independiente de tamaño/tiempo bajo el umbral) | **ADOPTAR** como conocimiento del informe/verificador | Heyl es aporte NUEVO sin contraparte en knowledge: convierte el barrido de dt en física, no solo convergencia numérica                                                     |
| quimb / TenPy / QuTiP / qiskit-dynamics                                                                                                                                                         | **DESCARTAR** para este alcance                       | ED con scipy basta en N∈{6,8,12}; TenPy catalogado como tercera ancla quasi-exacta si el escalado va a N>14                                                                |

**Qué es un claim verificable de una dinámica**: FORMAL_EXACT = serie exacta por ED
(+ doble ancla BdG donde exista); PROPERTY_RULE = invariantes físicos deterministas:
paridad Z₂ (⟨∏X⟩ conservada exactamente — violación = bug, no error de Trotter),
drift de energía acotado con ratio ≈4 al partir dt (orden 2), echo
U(−dt)·U(dt) = 1, norma = 1. Espejo fail-loud: «error 0.0000 entre Trotter y ED con
dt grande ⇒ sospecha de código compartido» — implementaciones independientes
proponente/verificador.

### Capabilities candidatas (7 — entran como paquetes, runtime intacto)

| #   | Entry point                                                           | Verificador / ancla                                                       |
| --- | --------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| 1   | `blite.ml.tabular_prep` — folds sellados, imputación en-fold, digests | PROPERTY_RULE anti-leakage + compromiso previo de folds (evento del plan) |
| 2   | `blite.quantum.fidelity_kernel` — K con λ_min y método PSD como datos | PROPERTY_RULE diag/simetría/PSD + spot-check determinista de celdas       |
| 3   | `blite.ml.svm_precomputed` — predicciones, α/b, métricas              | KKT del dual + GROUND_TRUTH holdout sellado (AL3)                         |
| 4   | `blite.ml.classifier_baseline` — SVM-RBF CV-5 oficial                 | GROUND_TRUTH + McNemar vs #3 + etiquetas barajadas                        |
| 5   | `blite.quantum.trotter_evolve` — series ⟨Z⟩/⟨ZZ⟩, digest qasm3        | ≤5% vs #6 en N=8 + paridad/echo/norma/ratio≈4                             |
| 6   | `blite.numeric.exact_evolve` — mismas series por `expm_multiply`      | ES el ancla FORMAL_EXACT                                                  |
| 7   | `blite.numeric.tfim_freefermion` (stretch) — series por BdG analítico | checker independiente de #6 → doble ancla                                 |

Deps nuevas mínimas: `qiskit-machine-learning>=0.9` (o cero con el kernel a mano);
reto 3: **cero**.

---

## R2 · Producto usable — chat multi-turno, streaming, onboarding, workspaces

| Hallazgo                                                                                               | Veredicto                          | Nota                                                                                                                                                                                                                                                                                                                  |
| ------------------------------------------------------------------------------------------------------ | ---------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Mensajes como eventos en el MISMO log append-only (OpenHands EventLog; AG-UI como validación de forma) | **ADOPTAR**                        | El D6 actual ya ES este patrón. **Nunca** tabla `conversations`/`messages` aparte (segunda fuente de verdad rompe replay). Bonus único: la conversación queda bajo el `provenance_hash` — chat certificado                                                                                                            |
| Steering mid-run: queue / steer / interrupt (Devin, Claude Code web, opencode)                         | **ADAPTAR** → _queue-to-next-turn_ | El «safe boundary» de Chimera ya existe: la frontera de turno. Steer intra-turno queda vetado por doctrina propia (freeze §8: reautorización mid-step = error fail-closed). Follow-up post-terminal ⇒ run nuevo enhebrado (`thread_id`) — streams terminal-bounded lo exigen                                          |
| Cancelación: endpoint stop dedicado (patrón AI SDK Vercel)                                             | **ADOPTAR**                        | **Hueco real detectado**: `run.cancelled` está congelado (con cascada §13) y `reads.py` ya proyecta `cancelado`, pero NO existe ruta HTTP que lo emita → `POST /runs/{id}/cancel` (202; 409 sobre terminal), cero evento nuevo                                                                                        |
| Aprobación humana mid-run (LangGraph interrupt/resume; AG-UI outcome interrupt)                        | **ADOPTAR lo ya spec'eado**        | `harness-agentico.md` §6 (`approval.requested/responded`) coincide 1:1 con el estado del arte y es MÁS fuerte (la aprobación queda dentro del provenance_hash). Falta implementación: emisor en el loop + card inline + POST de respuesta                                                                             |
| AG-UI como protocolo de wire                                                                           | **DESCARTAR**                      | Más pobre que el vocabulario congelado (sin verification/claims/provenance). Solo validación de forma                                                                                                                                                                                                                 |
| SSE + reanudación por `Last-Event-ID`/`global_seq`                                                     | **ADOPTAR (mantener)**             | Consenso 2026: SSE es el default correcto para agentes; el event store durable ES el buffer de reanudación (más fuerte que el Redis efímero del patrón Vercel). **Caveat latente**: ~6 conexiones por dominio en HTTP/1.1 — si M1 multiplica streams simultáneos, HTTP/2 en nginx o disciplina de un stream por vista |
| `resumable-stream` (Redis) / TanStack `experimental_streamedQuery`                                     | **DESCARTAR ambos**                | Resuelven problemas que Chimera no tiene; los maintainers de TanStack recomiendan exactamente el patrón ya implementado (`EventSource` + `setQueryData`). No migrar ni cuando salga de experimental                                                                                                                   |
| Lista de runs «viva»                                                                                   | **ADAPTAR**                        | `refetchInterval` corto mientras exista un run `en_curso` — KISS; SSE global de proyecto DESCARTADO hasta que un tercero lo pida                                                                                                                                                                                      |
| Init headless idempotente (`LANGFUSE_INIT_*`)                                                          | **ADAPTAR**                        | `CHIMERA_INIT_PROJECT_NAME`/`CHIMERA_INIT_USER_*` create-if-absent cuando workspaces/auth existan; JAMÁS seed de runs (doctrina #96)                                                                                                                                                                                  |
| Secretos: script generador + `*_FILE` (Supabase)                                                       | **ADOPTAR**                        | El compose ya es `*_FILE`-only (más estricto que Supabase); falta `scripts/generate-secrets.sh`. DESCARTAR el god-mode de instance-admin de Plane (13 servicios = anti-ejemplo)                                                                                                                                       |
| Seed honesto: instancia en blanco + demo explícita opt-in                                              | **ADOPTAR**                        | La demo Chimera es superior a todos los referentes: sesión REAL grabada + `CHIMERA_MODEL_BACKEND=replay` con badge — precondición: grabar la sesión (bloqueado-por-Dylan)                                                                                                                                             |
| Jerarquía workspaces (Langfuse org⊃project, aplanada en self-host)                                     | **ADAPTAR**                        | `project` = fila relacional chica FUERA del event store (config, no evidencia); `run.created.project_id?` aditivo (ceremonia #66); **organización DESCARTADA** como entidad hasta que exista un segundo usuario real; usuario mínimo cuando llegue el JWT-en-cookie                                                   |

**Modelo de conversación candidato** (todo aditivo al vocabulario congelado — entra a
la spec de chat en la Etapa 4): `mission.message` ↔ `●MissionMessage` (nuevo en
catálogo §14; `POST /runs/{id}/messages` → 202, 409 post-terminal);
`TurnContext.pending_messages` (campo aditivo, drenado al siguiente límite de turno);
lado asistente SIN evento nuevo en v1 (el hilo deriva de `plan.*`; `mission.reply`
queda bloqueado-por-definición hasta que el protocolo estricto `ProposedStep` gane
prosa); `POST /runs/{id}/cancel`; implementar `approval.*` ya spec'eados;
`run.created.thread_id?` (enhebrado post-terminal) y `.project_id?` (workspaces).

**Checklist de onboarding self-hosted candidato** (10 puntos, destilado): prereqs
declarados con verdad (imagen 10.9 GB) → `generate-secrets.sh` → `compose up` verde
solo por healthchecks (<3 min) → init headless idempotente → primer arranque
honest-empty con CTA → demo replay etiquetada (`make demo`) → smoke como paso de
verificación del usuario → guía de 5 minutos que TERMINA en `verify-bundle` offline
(ningún referente cierra su quickstart con evidencia criptográfica — momento
diferenciador) → troubleshooting mínimo → pinning declarado por release.

---

## R3 · Confianza profunda — M2/M3/M4/M8/M9

| Hallazgo                                                                                                                                               | Veredicto                                                                                                                       | Nota                                                                                                                                                                                                                                                                                                                                                            |
| ------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| in-toto attestation: catálogo con **SLSA VSA** (Verification Summary Attestation) y SVR — el formato estándar de «attestation por verificación» existe | **ADAPTAR**                                                                                                                     | Modelar el predicate propio (`blite/…` versionado) sobre VSA (`verifier.id`, policy, nivel, `timeVerified` ≈ Attestation+Policy de Chimera) en vez de inventar vocabulario. Base del DSSE-por-attestation de M8 y de M4 (una attestation DSSE por isla)                                                                                                         |
| **Rekor v2 (rekor-tiles) GA** con `rekor-server-posix` (un binario + disco) + patrón «stapled inclusion proof» (verificación sin contactar el log)     | **ADOPTAR** como pieza tardía opcional                                                                                          | **El descarte interno («rompe air-gap / overkill») era correcto para keyless+Fulcio y YA NO aplica** al patrón log privado + prueba engrapada en el bundle — hay que re-litigar la decisión registrada dos veces (freeze §7, 03-research Planeado)                                                                                                              |
| Hash-chain por evento en el writer único, canonicalización existente                                                                                   | **ADOPTAR**                                                                                                                     | Forma y fórmula YA congeladas (anexo canonicalización: `hash_i = SHA-256("blite/event/v1\n" ‖ hash_{i-1} ‖ C(view(e_i)))`, génesis `""`); columnas vacías desde la semilla; cero infra. Respetar el corte [stress-final] (head = evento terminal; familias de cierre fuera). tlog-tiles como formato de publicación = semilla, no compromiso. immudb DESCARTADO |
| Z3 (MIT, 4.16.x) como backend de M3, **con `rlimit` en vez de timeout wall-clock** (determinismo del replay)                                           | **ADOPTAR** (spec trust/11 vigente)                                                                                             | Corrección al spec: timeout hace `unknown` dependiente de máquina. Reglas como datos = SMT-LIB 2 con digest de bytes exactos                                                                                                                                                                                                                                    |
| **cvc5 + certificados Alethe + checker independiente Carcara**                                                                                         | **ADAPTAR** el puerto `RuleBackend` para que sea drop-in                                                                        | Conecta con freeze §4-iii: AL4 exige `proof {certificate_ref, checker_id, checker_verdict}`. Con Z3 solo, el RuleVerifier formal topa honesto en AL3; la ruta cvc5→Alethe→Carcara da AL4 **verificable offline por un tercero** — el criterio rector literal. Requisito del DISEÑO del backend, no de la primera implementación                                 |
| OPA/Rego/Cedar como motor de verificación                                                                                                              | **DESCARTAR** (reconfirmación de trust/11/13)                                                                                   | Son authz, no verificación de resultados. Lo aprovechable sigue siendo la forma del bundle firmado para distribuir rule-sets                                                                                                                                                                                                                                    |
| W3C **Bitstring Status List v1.0** (Recommendation may-2025)                                                                                           | **ADAPTAR la FORMA** — bitstring firmado + índice estampado como artefacto propio, sin el stack VC                              | Resolución del choque con verificación offline: la lista es artefacto estático firmado; `verify-bundle --status-list <archivo>` opcional — sin lista ⇒ «válido a valid_as_of, revocación no comprobada» (semántica ya congelada); con lista ⇒ frescura opt-in. Bundles con `revocation:"none"` siguen verificando. IETF Token Status List: vigilar hasta RFC    |
| OTel GenAI semconv: **siguen experimentales** (jul-2026; repo dedicado desde v1.42.0, sin 1.0); proyección post-hoc de streams = patrón establecido    | **ADOPTAR el proyector** (consumer del stream, fuera del camino certificado, semconv pinneado y estampado)                      | Convergencia total con R1 de Planeado. Ventaja: cada span sale de eventos certificados                                                                                                                                                                                                                                                                          |
| Langfuse self-hosted como backend M9                                                                                                                   | **ADAPTAR → degradar** a perfil OPCIONAL del compose (`--profile observability`), herramienta interna de debugging del proposer | Costo real v3: 6 contenedores, ~4 vCPU/8 GB — duplica el compose canónico; verdicts/AL no existen en el semconv (viajarían como atributos custom sin semántica); el Studio YA cubre la UX de confianza sobre el stream real. **DIVERGENCIA a registrar contra el enunciado de M9**                                                                              |
| OpenBao 2.6.x Transit, **single instance** (Raft integrado, sin HA)                                                                                    | **ADOPTAR** — Fase 2 temprana de M8, mejor ratio ganancia/costo                                                                 | Precisión a trust/15: el quorum de 3 es solo para HA. `KeyProvider` ya diseñado para que Transit sea drop-in; la llave que firma EL diferenciador deja de vivir en la memoria del proceso                                                                                                                                                                       |
| SPIFFE/SPIRE en single-node                                                                                                                            | **DESCARTAR** — gate explícito = despliegue multi-nodo/multi-tenant, no fase                                                    | En un host compose es teatro de seguridad (el mismatch de pre-registro de trust/08 sigue). Mantener `spiffe_id` reservado + URNs forma-SPIFFE. Paso proporcional si se quiere avanzar: mTLS estático entre contenedores con certs del propio KeyProvider                                                                                                        |

**Orden incremental candidato para M8** (criterio: «un tercero verifica sin confiar
en nosotros») — entra como propuesta a la consolidación:

1. **Hash-chain** (cero infra, todo lo demás firma sobre este sustrato — si va
   después habría que re-emitir);
2. **DSSE por attestation** con predicate sobre VSA/SVR (habilita M4; separación
   Signer≠Verifier deja de ser limitación declarada);
3. **StatusList propia** (cierra `revocation:"none"` — el único campo que hoy dice
   «no hay forma de saber si esto fue retirado»);
4. **OpenBao Transit** single-node (protege la raíz de todas las firmas anteriores);
5. **Rekor v2 witness opcional** (stapled proofs en el bundle; su valor crece con el
   flip OSS);
6. SPIFFE/SPIRE: fuera de M8 (gate por despliegue, no por fase).

Transversal: M3 diseña `RuleBackend` con la ruta a AL4 aunque la v1 sea Z3-solo; M9
corre ortogonal (proyección derivada, jamás camino certificado).

---

## Divergencias que exigen discusión (gate de la Etapa 3 — gobernanza #94)

1. **Rekor**: descartado dos veces en el registro (freeze §7 «rompen air-gap»,
   03-research Planeado «overkill») — el descarte era correcto ENTONCES y ya no aplica
   al patrón Rekor v2 posix + stapled proof. Re-litigar con causa antes de tocar M8.
2. **M9/Langfuse**: el enunciado dice «backend Langfuse self-hosted»; el análisis dice
   perfil opcional de debugging, no requisito — degradación a registrar.
3. **Presupuesto de circuitos del kernel (nota 02 §2.2)**: supersedido en simulador
   por `FidelityStatevectorKernel` — corre el dataset completo; la nota queda vigente
   solo para la narrativa por-circuitos/hardware.
4. **Techo AL2 de `property_rule` vs Z3 `unsat`** (cruza con la cobertura de M3): la
   ruta cvc5+Alethe+Carcara resuelve el dilema por la vía `formal_exact`+proof (AL4)
   sin romper los 4 espejos del techo — decisión de freeze, no de implementación.
5. **Dependencia nueva del reto 2**: `qiskit-machine-learning>=0.9` vs kernel a mano
   (~15 líneas, cero deps). Ambas cumplen; es una decisión de mantenimiento.
