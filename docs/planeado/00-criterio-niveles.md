# Planeado vs Mejorado — el criterio y el backlog

> **Estado: VIGENTE (2026-07-24, v2).** v2 incorpora el mandato de Dylan del mismo día:
> **Chimera no es solo verificador — es el agente que GENERA el resultado del reto (paridad
> con `reto1-vanilla`) y además lo verifica, lo certifica, produce el informe formal y lo
> presenta con superficie visual superior.** El mapeo determinista de misiones (v1 P5)
> queda ELIMINADO; el agente real sube a Planeado. Supersede parcialmente las decisiones
> #58–#59 (registrado en #61).

## El criterio (una pregunta, tres autoridades)

**La pregunta que clasifica: ¿quién nota su ausencia, y cuándo?**

- La nota **el juez o la audiencia el día D**, o su ausencia **vuelve falsa una afirmación
  nuestra sobre la plataforma** → **Planeado**.
- Solo la notaría **un usuario futuro del producto** (o nosotros como ingenieros) →
  **Mejorado**.
- Acopla **lógica del reto al runtime/agente** → **no va a ningún nivel, jamás**.

| Autoridad                              | Contrato                                                             | Qué obliga                                                                                                                                                                                                                                                                                                                                                               |
| -------------------------------------- | -------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **1 · La consigna y rúbrica del reto** | externo — `docs/retos/reto1-consigna.md`                             | informe PDF ≤8p, entry point único, r vs p con barras de error, baselines GW+greedy, limitaciones honestas, datos reales (ODS), hardware real (10%), escalado 2+ tamaños (20%), slides 5', statement SDK                                                                                                                                                                 |
| **2 · La identidad de la plataforma**  | interno — `invariants.md` + spec v3.2 + mandato 2026-07-24           | (a) "confiable ≠ plausible": ninguna superficie fabrica ni disimula datos — lo que el Studio muestra es real o está etiquetado como replay; (b) **"hablo con Chimera y Chimera resuelve"**: la plataforma es un agente capaz de generar la solución completa, no solo de auditarla. Un ítem que repare una violación de identidad es Planeado aunque ningún juez lo pida |
| **3 · El guion del demo**              | `docs/planeado/01-demo-dia-d.md` (instancia del camino dorado §15.4) | el flujo completo corriendo EN VIVO: conversación → generación → verificación → certificado → `verify-bundle` offline, falla sembrada refutada, video de respaldo                                                                                                                                                                                                        |

**Todo lo que ninguna de las tres autoridades exige es Mejorado por defecto.**
Desempates: (a) lo que des-riesga el día D sube a Planeado; (b) lo que exige ciencia nueva
baja a Mejorado salvo que la rúbrica lo pague.

### La regla de agnosticismo (transversal, no negociable)

El test es mecánico: **borrar `docs/retos/`, las instancias y las policies del reto debe
dejar la plataforma compilando y sus tests pasando.** El reto existe en Chimera solo como
DATOS: instancias con digest, anclas registradas, policies pinneadas, capabilities del
registry (una capability de "derivar grafo desde GeoJSON" es genérica; los GeoJSON del ICE
son datos). Cualquier `if` sobre "maxcut", "ICE" o "reto1" dentro del runtime/agente es un
defecto, no una feature.

### El agente real y la doctrina replay (tensión resuelta)

El freeze §15.4 veta "LLM generando en vivo" **el día D** — nunca vetó que Chimera SEA un
agente real. La lectura vigente: el agente (ModelServer + LLM real) se construye y corre
de verdad en preparación; `MODEL_ROUTER_BACKEND=replay` es la **puesta en escena por
defecto** (reproduce sesiones agénticas REALES grabadas, determinista). Correr el LLM vivo
en escena es un flip explícito que solo Dylan decide (registrar en `decisiones.md` si se
flipea). Lo que quedó eliminado es el sustituto barato: un mapeo determinista fingiendo
ser agente.

## Backlog Planeado (en orden; cada ítem con su autoridad)

| #   | Ítem                                                                                                                                                                                                                                                                                                                                                                                                                                                       | Autoridad               |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------- |
| P1  | **Honestidad del Studio**: matar los mocks silenciosos de runtime — 6 queries sin rama live (`queries.ts`), vista Red estática (`spike/ieee14.ts`), carrera fixture↔SSE, `DEMO_RUN_ID`. El modo fixtures sobrevive SOLO como "Replay" explícito y etiquetado (banner), jamás default silencioso                                                                                                                                                            | 2                       |
| P2  | **Compose enciende el modo live**: `VITE_API_URL` como ARG del `studio.Dockerfile` + env en `compose.yaml` — hoy `docker compose up` sirve fixtures                                                                                                                                                                                                                                                                                                        | 3                       |
| P3  | **Studio 100% API-driven**: egress faltante en `gatewayClient.ts` (GET /runs, artifacts, knowledge, step-evidence, ablation, topología/partición) + sus endpoints                                                                                                                                                                                                                                                                                          | 3 + 2                   |
| P4  | **El agente real**: ModelServer + loop agéntico con LLM real — recibe la misión en lenguaje natural, planifica, orquesta capabilities como steps del run (claims por sub-run), conversa. Replay = grabación de sesiones reales (modo escena), no sustituto. Promovido de M1 por mandato 07-24                                                                                                                                                              | 2                       |
| P5  | **Paridad generativa con `reto1-vanilla`**: Chimera genera la solución completa — capability genérica de derivación de grafos desde GeoJSON (los datos abiertos del ICE → cr6/cr8 con digest), QUBO, QAOA (Aer+seed en vivo), baselines GW/greedy/exacto (+SA), estadística ≥5 semillas; las 19 corridas Nexus (H2-1LE/H2-Emulator) importadas como patas pre-corridas con digest; nuevas corridas H2 orquestables vía qnexus cuando haya credenciales/MCP | 2 + 1                   |
| P6  | **El informe lo produce Chimera**: informe PDF ≤8 páginas ensamblado por la plataforma desde resultados CERTIFICADOS (cada figura y cifra referencia su certificado/digest) + slides 5' + statement SDK ≤200 palabras. El informe es un deliverable del bundle, no un doc escrito a mano                                                                                                                                                                   | 1 + 2                   |
| P7  | **Superficie visual superior**: mapa geográfico real de la red ICE (GeoJSON ya en mano) con partición y zonas de falla pintadas sobre el territorio, vista por isla con badges de verificación, r vs p con barras de error, comparación visual de baselines — todo API-driven                                                                                                                                                                              | 1 (explicación 20%) + 3 |
| P8  | **Escalado honesto**: cr6→cr8→ieee14→ieee30 + red ICE completa (70 subestaciones) clásica, con extrapolación honesta del límite cuántico (26 qubits H2)                                                                                                                                                                                                                                                                                                    | 1 (20%)                 |
| P9  | **Guion ensayado + video de respaldo integrado** (`compose.record.yml` ya existe)                                                                                                                                                                                                                                                                                                                                                                          | 3                       |
| P10 | **Sanitización continua** (cierra aunque nada más cierre)                                                                                                                                                                                                                                                                                                                                                                                                  | —                       |

## Backlog Mejorado (se ejecuta SOBRE la base Planeado)

| #   | Ítem                                                                                                                                           | Nota                                                                        |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| M1  | LLM vivo en escena como default (sin replay) + chat multi-turno libre en producción                                                            | el flip día-D es decisión de Dylan; esto es hacerlo default de producto     |
| M2  | Cruce del gateway por step + flip AX1 (`actor_id`)                                                                                             | deuda de invariante — primera de la lista                                   |
| M3  | Z3 `RuleVerifier` (clase formal adicional)                                                                                                     | ningún claim del guion lo exige                                             |
| M4  | Attestation por isla de primera clase (+ badges nativos)                                                                                       | hoy: checks `island-{k}:` agrupables                                        |
| M5  | Pata Guppy/qnexus viva                                                                                                                         | la consigna lo recomienda; el statement SDK lo cubre honesto                |
| M6  | Extensiones cuánticas nuevas (ZNE, warm-start, QEC/Iceberg)                                                                                    | el análisis de ruido H2 ya puntúa "extensiones"; esto lo sube a "Excelente" |
| M7  | Retos 2/3 con la misma plataforma                                                                                                              | prueba de generalidad                                                       |
| M8  | Fase 2 del freeze entera (hash-chain, StatusList, OpenBao/HSM, SPIFFE, Rekor), Fargate/BYOC, MCP de salida, ingesta KG, campos §1 del manifest | diseño declarado, construcción post-hackathon                               |

## Qué existe ya vs qué es nuevo (para dimensionar Planeado)

- **Ya existe (MVP)**: run loop + certificados DSSE + `verify-bundle` 7/7; verificadores
  CP-SAT y pandapower; capabilities QAOA (Aer+seed), solvers, sim; baselines GW/greedy y
  experimento r vs p (`scripts/exp_r_vs_p.py`); corpus con digests; API POST /runs + SSE +
  certificado; compose pg+api+worker+studio.
- **Nuevo en Planeado**: el loop agéntico con LLM (P4); capability GeoJSON→grafo (P5);
  importador de corridas Nexus como patas (P5); ensamblador de informe (P6); mapa
  geográfico + dataviz (P7); todo el cableado live del Studio (P1–P3).
