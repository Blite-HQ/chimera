# Planeado vs Mejorado — el criterio y el backlog reclasificado

> **Estado: VIGENTE (2026-07-24).** Sustituye la definición por-lista del plan maestro MVP
> (`docs/mvp/00-plan-maestro.md` §Los tres niveles, cerrado). Autor: Fable, por mandato de
> Dylan ("definir de dónde sale que X es Planeado y Y es Mejorado"). Ratificación de dueños
> a posteriori, según el modelo operativo vigente.

## El criterio (una pregunta, tres autoridades)

**La pregunta que clasifica: ¿quién nota su ausencia, y cuándo?**

- La nota **el juez o la audiencia el día D**, o su ausencia **vuelve falsa una afirmación
  nuestra sobre la plataforma** → **Planeado**.
- Solo la notaría **un usuario futuro del producto** (o nosotros como ingenieros) →
  **Mejorado**.
- Acopla **lógica del reto al runtime/agente** → **no va a ningún nivel, jamás**.

"Planeado" NO es "lo que quedó pendiente" ni "lo que sería bonito": es la clausura de tres
contratos, y solo de esos tres:

| Autoridad                              | Contrato                                                        | Qué obliga                                                                                                                                                                                                                        |
| -------------------------------------- | --------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **1 · La consigna y rúbrica del reto** | externo — `docs/retos/reto1-consigna.md`                        | informe PDF ≤8p, entry point único, r vs p con barras de error, baselines GW+greedy, limitaciones honestas, datos reales (ODS), hardware real (10%), escalado 2+ tamaños (20%), slides 5', statement SDK                          |
| **2 · La identidad de la plataforma**  | interno — `invariants.md` + spec v3.2 ("confiable ≠ plausible") | ninguna superficie nuestra puede fabricar, inventar o disimular datos; si el Studio muestra algo, es real o está **etiquetado como replay**. Un ítem que repare una violación de identidad es Planeado aunque ningún juez lo pida |
| **3 · El guion congelado del demo**    | freeze `contract-freeze.md` §15.4                               | el camino dorado (run → claim → verificación → certificado DSSE → `verify-bundle` offline → Studio SSE con badges) corriendo EN VIVO, falla sembrada refutada, video de respaldo                                                  |

**Todo lo que ninguna de las tres autoridades exige es Mejorado por defecto.**
Desempates: (a) lo que **des-riesga el día D** sube a Planeado; (b) lo que exige ciencia
nueva (experimentos que no existen aún) baja a Mejorado salvo que la rúbrica lo pague.

### La regla de agnosticismo (transversal, no negociable)

El test es mecánico: **borrar `docs/retos/`, las instancias y las policies del reto debe
dejar la plataforma compilando y sus tests pasando.** El reto existe en Chimera solo como
DATOS: instancias con digest, anclas registradas, policies pinneadas, capabilities del
registry. Cualquier `if` sobre "maxcut", "ICE" o "reto1" dentro del runtime/agente es un
defecto, no una feature. (Es la misma doctrina del freeze §15.1–15.2: la plataforma
analiza y certifica; el dominio entra por configuración.)

## Backlog Planeado (en orden; cada ítem con su autoridad)

| #   | Ítem                                                                                                                                                                                                                                                                                                                          | Autoridad                    |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------- |
| P1  | **Honestidad del Studio**: matar los mocks silenciosos de runtime — las 6 queries sin rama live (`queries.ts`), la vista Red estática (`spike/ieee14.ts`), la carrera fixture↔SSE, el `DEMO_RUN_ID`. El modo fixtures sobrevive SOLO como "Replay" explícito y etiquetado en la UI (banner visible), jamás default silencioso | 2 (identidad) + 3            |
| P2  | **Compose enciende el modo live**: `VITE_API_URL` como ARG del `studio.Dockerfile` + env en `compose.yaml` — hoy `docker compose up` sirve fixtures                                                                                                                                                                           | 3 (guion)                    |
| P3  | **Studio 100% API-driven**: funciones de egress faltantes en `gatewayClient.ts` (GET /runs, artifacts, knowledge, step-evidence, ablation, topología/partición) + sus endpoints; la vista Red consume la partición del run real                                                                                               | 3 + 2                        |
| P4  | **El reto como datos de Chimera**: importar cr6/cr8 (instancias ICE con digest de `reto1-vanilla`) al corpus; registrar las 19 corridas Nexus (H2-1LE/H2-Emulator) como **patas pre-corridas con digests** — exactamente la figura que el freeze ya contemplaba (P1-7); en vivo solo Aer+seed                                 | 1 (ODS+hardware 10%) + 3     |
| P5  | **Superficie de misión agnóstica**: "nueva misión" en lenguaje natural → mapeo determinista a (capability, claim, policy) desde el registry — sin LLM en vivo el día D (NO-va §15.4); el chat real queda en Mejorado                                                                                                          | 2 (pitch/identidad)          |
| P6  | **Escalado honesto**: figura r vs p (media±σ, ≥5 semillas) + escalado por tamaño cr6→cr8→ieee14→ieee30 + **la red ICE completa (70 subestaciones) resuelta clásicamente** con extrapolación honesta del límite cuántico (26 qubits H2)                                                                                        | 1 (comparación/escalado 20%) |
| P7  | **Entregables obligatorios**: informe PDF ≤8 páginas (hoy NO existe ni en vanilla), slides 5', statement SDK ≤200 palabras (honesto: Qiskit elegido, Guppy evaluado), repo público listo                                                                                                                                      | 1                            |
| P8  | **Guion ensayado + video de respaldo integrado** (`compose.record.yml` ya existe)                                                                                                                                                                                                                                             | 3                            |
| P9  | **Sanitización continua** (regla de siempre: cierra aunque nada más cierre)                                                                                                                                                                                                                                                   | —                            |

## Backlog Mejorado (producto/generalidad; nadie lo nota el día D)

| #   | Ítem                                                                                                                                           | Nota                                                                                    |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| M1  | Chat/agente real sobre ModelServer (replay → vivo post-hackathon)                                                                              | la superficie P5 no lo necesita                                                         |
| M2  | Cruce del gateway por step + flip AX1 (`actor_id`)                                                                                             | deuda de invariante — primera de la lista                                               |
| M3  | Z3 `RuleVerifier` (clase formal adicional)                                                                                                     | ningún claim del guion lo exige                                                         |
| M4  | Attestation por isla de primera clase (+ badges nativos)                                                                                       | hoy: checks `island-{k}:` agrupables                                                    |
| M5  | Pata Guppy/qnexus viva                                                                                                                         | la consigna lo recomienda; el statement SDK lo cubre honesto                            |
| M6  | Extensiones cuánticas nuevas (ZNE, warm-start, QEC/Iceberg)                                                                                    | el análisis de ruido H2 del vanilla ya puntúa "extensiones"; esto lo sube a "Excelente" |
| M7  | Retos 2/3 con la misma plataforma                                                                                                              | prueba de generalidad                                                                   |
| M8  | Fase 2 del freeze entera (hash-chain, StatusList, OpenBao/HSM, SPIFFE, Rekor), Fargate/BYOC, MCP de salida, ingesta KG, campos §1 del manifest | diseño declarado, construcción post-hackathon                                           |

### Reclasificaciones respecto al plan MVP (el criterio tiene dientes)

- `gateway por step + flip AX1`: era Planeado → **Mejorado (M2)**. Corrección interna;
  invisible para las tres autoridades.
- `ModelServer replay`: era Planeado → **Mejorado (M1)**, porque P5 se decidió determinista.
- `Z3 RuleVerifier`, `campos §1 manifest`: eran Planeado → **Mejorado (M3, M8)**.
- `ICE 3 escalas` (provincia/región/país): se re-fundamenta como **P6, escalado por
  tamaño** — la geografía administrativa no es lo que la rúbrica mide; el tamaño de
  instancia sí ("2 o más tamaños"). La red ICE completa clásica ES la escala "país",
  contada con honestidad.
- `H2 pre-corridas con digests`: era Planeado hipotético → **P4 con evidencia existente**
  (las 19 corridas del vanilla ya están cacheadas con job_id y counts).
