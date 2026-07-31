# Specs (S-G) — la base para trabajar en paralelo

> **Estado: VIGENTE (S-G Etapa 0, 2026-07-22).** Convención reservada en `docs/README.md`
> ("Specs … seeded in S-G"). **Autoridad: [`../contract-freeze.md`](../contract-freeze.md)** —
> una spec jamás contradice el freeze; si necesita cambiarlo, el cambio va ALLÁ como
> supersesión con causa (regla 3 del propio freeze), nunca aquí.

## Qué es una spec aquí

Una spec fija **el contrato ejecutable de un plano** a nivel suficientemente bajo para que su
dueño lo implemente sin esperar a nadie. Cada spec declara:

1. **Sección(es) del freeze que la gobiernan** (con `§`).
2. **El contrato exacto**: modelos/puertos (Protocols) contra los que se programa.
3. **Sus tests semilla**: ruta en `tests/`, estado actual.
4. **Dueño** (CODEOWNERS) y fronteras (qué NO decide esta spec).

**Ciclo de vida:** `SPEC` (contrato escrito) → `SEED` (tests semilla en rojo, marcados
`@pytest.mark.seed` + `xfail(strict=False)` — CI queda verde) → `VERDE` (el dueño implementa
y quita el xfail; mismo patrón que el xfail de AX1).

Convención de archivo: `docs/specs/<plano>-<tema>.md` (ej. `confianza-verify-bundle.md`,
`ejecucion-replay.md`).

## Cómo trabajamos en paralelo (la regla del juego)

**El desacoplador es el contrato en código.** Cada quien programa contra los Protocols, los
modelos Pydantic, el SQL de `engine/sql/init_v2.sql` y los fixtures — **nunca contra la
implementación de otro dueño.** Las fronteras las vigilan `import-linter` (13 contratos —
**[S3 2026-07-30]** el doc decía 12; el 13º es `ADR-008-report`, `pyproject.toml:194`; D-N9)
y CODEOWNERS; si `lint-imports` falla, se arregla el código, no el contrato.

> **[S3 2026-07-30]** La tabla de dueños de abajo (y la columna «Dueño (Fase 1)» del índice
> de specs de costura al final) opera sobre el modelo de dueños DEROGADO por la decisión #94:
> toda decisión es gobernanza Dylan+Claude vía ledger, sin dueños por persona ni
> `PENDIENTE-{persona}`. La tabla se conserva sin editar porque su información de
> plano/alcance (qué área escribe qué, qué NO toca) sigue siendo el mapa vigente de
> fronteras del código.

| Dueño    | Área (escribe)                                                                                           | NO toca                                             |
| -------- | -------------------------------------------------------------------------------------------------------- | --------------------------------------------------- |
| Dylan    | `engine/src/blite/{verification,certificate,events,identity,protocols,guardrails,authz}`, `sdk/`, Studio | `gateway/runtime/serving`, `capabilities/*`         |
| Steven   | `engine/src/blite/{gateway,runtime,serving}`                                                             | `verification/certificate/events`, `capabilities/*` |
| Sebas    | `capabilities/*`, corpus (`knowledge/islanding` datos)                                                   | `engine/src/blite/*`                                |
| Geovanni | compose/infra, CI, `distributions/` operativo                                                            | `engine/src/blite/*`, `capabilities/*`              |

Reglas:

1. **TDD sobre seeds:** tu trabajo es poner en verde los seeds de tu plano (y agregar los
   tuyos propios — seed primero, implementación después).
2. **Gates verdes siempre:** `uv run pytest` · `uv run lint-imports` · `uv run ruff check` —
   antes de cada push. Un seed en rojo va como `xfail`, jamás como test fallando.
3. **¿Necesitás algo del plano de otro?** Programá contra el Protocol/fixture. Si el contrato
   no alcanza, eso es una **frontera**: se conversa con el dueño y el acuerdo se estampa en el
   freeze como supersesión (patrón EX-2/EX-5/nota-10) — no queda en chats.
4. **Cero vocabulario supersedido** en código nuevo (`rung`/escalera → clase + AL0–AL4 +
   criticidad C0–C3).
5. **Fable (opcional):** cualquiera puede usarlo para auditar/refinar su plano sobre esta
   base — la base no depende de eso.

## Índice de specs

> **[S3 2026-07-30]** Este índice quedó fechado 07-22/24 y no se re-marcó al implementarse
> las specs. Refresco (censo `docs/mejorado/07-censo-documental.md` §1.2): las 7 specs del
> directorio existen y su letra sigue vigente, pero varios estados «SPEC/xfail» ya corren en
> código sin marca — el estado real por spec vive en el censo §1.2 y en las marcas `[S3]`
> dentro de cada spec. Esta tabla no se reescribe: es registro de la Etapa 0.

| Base / seed (Etapa 0)                                                                                                                                                                                                                    | Plano              | Estado                      |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------ | --------------------------- |
| Esquema: `engine/sql/init_v2.sql` + `tests/invariants/test_esquema_migration.py` (anti-drift bidireccional)                                                                                                                              | todos              | **VERDE**                   |
| Reglas del log S-F: `blite/events/rules.py` (system:, post-terminal, corte del hash) + `test_event_rules.py`                                                                                                                             | confianza          | **VERDE**                   |
| Predicate mínimo §7: `blite/certificate/predicate.py` + `test_predicate.py` (titular fail-closed)                                                                                                                                        | confianza          | **VERDE**                   |
| Matriz interaction×profile: `blite/runtime/dispatch.py` + `test_dispatch_matrix.py`                                                                                                                                                      | ejecución          | **VERDE**                   |
| Puertos: `ModelPort`+replay (`serving/model_port.py`) · `KeyProvider` (`certificate/keys.py`) · `ContentStore` (`content.py`)                                                                                                            | frontera           | **SPEC** (Protocols listos) |
| `scripts/verify-bundle.py` — 7 puntos IMPLEMENTADOS (`blite/certificate/bundle_check.py` + 11 tests adversariales + fixture auto-validante `gen-example-bundle.py`)                                                                      | confianza (Dylan)  | **VERDE** (2026-07-22)      |
| Studio en clase+AL (ET-9): `assurance.ts` + `AssuranceScale`/`AssuranceBadge`, `CertificateView` abre con el alcance (predicate §7), fixture del cert emitido por `gen-example-bundle.py` (supersede `gen-example-trust-certificate.py`) | confianza (Dylan)  | **VERDE** (2026-07-22)      |
| [`confianza-api-sse.md`](confianza-api-sse.md) — `chimera_api` (miembro `api/`): SSE `GET /runs/{id}/events` sobre el puerto `EventStore` + 2 contratos import-linter nuevos (§10-1d)                                                    | confianza (Dylan)  | **VERDE** (2026-07-22)      |
| `AuthzDecision` publicada (`blite.authz` — freeze §5/EX-14): el único tipo que la etapa egress acepta; disjunta de `Signal` por construcción — desbloquea mediation (Steven)                                                             | confianza (Dylan)  | **VERDE** (2026-07-22)      |
| Palanca EX-5, mitad Policy (`blite/verification/policy_diff.py` — freeze §6): `assess_hardening(old, new)` → `{hardened, causes}`; la mitad runtime (`policy_watch` + `●EscalationOpened`) sigue en el seed frontera D+S                 | confianza (Dylan)  | **VERDE** (2026-07-22)      |
| Portadores de `●ClaimEmitted` (`blite/verification/claim.py` — freeze §6 SF-P1-2): `claim_type` + `is_conclusion` + flags de piso en el payload; `computed_criticality` (conclusión⇒C3, intermedia⇒C1, piso solo sube)                   | confianza (Dylan)  | **VERDE** (2026-07-22)      |
| `tests/seeds/test_seed_ejecucion_runs_projection.py` — proyección regenerable por replay                                                                                                                                                 | ejecución (Steven) | **VERDE** (2026-07-24)      |
| `tests/seeds/test_seed_ejecucion_palanca_ex5.py` — ○PolicyChanged endurecida ⇒ ●EscalationOpened                                                                                                                                         | frontera (D+S)     | **VERDE** (2026-07-24)      |
| `tests/seeds/test_seed_ciencia_falla_sembrada.py` — bus 1, r=0.5712, 32 597/57 070 — `capabilities_sim_api.recompute_seeded_failure` (digest §1.6 verificado en cada carga)                                                              | ciencia (Sebas)    | **VERDE** (2026-07-23)      |
| `tests/seeds/test_seed_infra_compose.py` — compose canónico + `*_FILE` + `compose.record.yml`                                                                                                                                            | infra (Geovanni)   | **VERDE** (2026-07-24)      |

> **Nota (2026-07-24, cierre MVP Nivel-1):** el plano runtime-API (`POST /runs` + `GET
/runs/{id}/certificate`) no tiene spec propia aquí — quedó especificado y cerrado en
> [`../mvp/01-runtime-api.md`](../mvp/01-runtime-api.md); su prueba estrella es
> `tests/smoke/test_runtime_api_e2e.py` (POST → SSE terminal → certificado → `check_bundle` 7/7).

## Specs de costura (Fase 0 · Planeado) — convención

> **Estado: SPEC (Fase 0, 2026-07-24).** Las 6 specs de costura de `05-plan-paralelo.md`
> §Fase 0 fijan los contratos ENTRE dominios ANTES de que las 5 sesiones de implementación
> arranquen. Autoridad: el freeze + `docs/planeado/03-research-estado-del-arte.md` (R1–R6).
> Una spec de costura jamás contradice el freeze; si necesita cambiarlo, va como
> supersesión con causa en `docs/mvp/decisiones.md` (regla 3 del freeze) — ej. la ceremonia
> A1 (#66), no aquí.

Cada spec de costura declara, además de lo de arriba: **(a)** una tabla de **interfaces con
otros dominios** (interfaz tocada → dominio afectado → estado del contrato); **(b)** los
**eventos/payloads nuevos** que introduce (nombre de wire dotted-lowercase — `plan.created` —
y su ● del catálogo §14 — `●PlanCreated`); **(c)** sus **tests de contrato** sobre fixtures
de costura (abajo).

### Fixtures de costura — un solo origen (regla NUEVA #1 de `05`)

Lección del MVP: los 6 queries del Studio corrían fixtures inventados por dominio, divergentes
del API real. Regla: **el fixture de costura tiene UN solo origen y ambos lados lo parsean.**

- **El origen es Python** (los modelos Pydantic del contrato). Un generador bajo `scripts/`
  (patrón heredado de `gen-example-bundle.py`, que de UN bundle auto-validado 7/7 emite
  `scripts/example-bundle.json` **y** `apps/studio/src/fixtures/certificate.example.json`)
  importa los modelos del `engine`/`sdk`, y emite el fixture **canónico** (JCS/RFC-8785,
  snake_case de wire) a `tests/fixtures/contract/<spec>/<caso>.json`, **espejado** a
  `apps/studio/src/fixtures/contract/<spec>/<caso>.json` (Vite solo importa dentro de `src/`).
- **El fixture ES el contrato:** el seed de Python lo parsea con el modelo Pydantic; el test
  de Studio lo parsea con el schema Zod espejo (`apps/studio/src/data/schemas.ts`). Ninguno
  inventa el dato. Un test anti-drift asegura que canónico y espejo son byte-idénticos (mismo
  espíritu que `test_verification_policy` comparando el JSON Schema contra `.model_json_schema()`).
- **NO se adopta codegen Pydantic→Zod** (rechazado: build-step pesado; el freeze ya descartó
  maquinaria de wire). El par [fixture JSON generado por Python + Zod espejo a mano + gate en
  ambos lados] es el patrón probado y suficiente; el Zod ya se declara "espejo de los contratos
  congelados".
- **Fase 0 entrega el contrato + el seed (xfail), no la feature.** Donde el modelo origen ya
  existe (Event/proyección SSE, Attestation, Certificate) el fixture se genera y commitea hoy;
  donde el modelo aún no existe (eventos de plan, manifest v2, predicado de importación) el
  seed queda `@pytest.mark.seed` + `xfail(strict=False)` y el fixture verde lo entrega el dueño
  en Fase 1. Cambiar una costura sin regenerar su fixture = defecto (el generador falla-fuerte).

### Índice de specs de costura

> **[S3 2026-07-30]** Los estados «SPEC» de esta tabla quedaron fechados 2026-07-24; según
> el censo §1.2 varias costuras ya corren implementadas total o parcialmente (las 6 rutas de
> `endpoints-studio` vivas, `ConsensusLeg` de `evidencia-externa` con su validador,
> `ModelServer` de `harness-agentico`, módulos y fixtures de `capability-ingesta` e
> `informe-derivado` en el árbol) — ver marcas `[S3]` en cada spec. La columna «Dueño
> (Fase 1)» quedó derogada por #94 (nota arriba); se conserva como registro de plano/alcance.

| Spec                                             | Costura | Dueño (Fase 1) | Estado |
| ------------------------------------------------ | ------- | -------------- | ------ |
| [`harness-agentico.md`](harness-agentico.md)     | A↔E↔D   | Dylan+Steven   | SPEC   |
| [`capability-ingesta.md`](capability-ingesta.md) | B↔A     | Sebas+Dylan    | SPEC   |
| [`evidencia-externa.md`](evidencia-externa.md)   | B       | Sebas          | SPEC   |
| [`informe-derivado.md`](informe-derivado.md)     | C↔B     | Dylan          | SPEC   |
| [`superficie-visual.md`](superficie-visual.md)   | D↔E↔A   | Dylan          | SPEC   |
| [`endpoints-studio.md`](endpoints-studio.md)     | E↔D     | Steven+Dylan   | SPEC   |

### Specs de costura (Fase 0 · Mejorado, 2026-07-31) — sección ADITIVA

> Producidas por la sesión Contratos de Mejorado (`05-plan-paralelo.md` §1; sin dueños por
> #94 — los consumidores son sesiones de Fase 1). Misma convención de fixtures single-origin
> de arriba; el ledger (`../mvp/decisiones.md` #121+) registra cada ceremonia.

| Spec                                           | Costura         | Consumen  | Estado               |
| ---------------------------------------------- | --------------- | --------- | -------------------- |
| [`chat-conversacion.md`](chat-conversacion.md) | A↔E↔D           | P3, P6    | SPEC (decisión #122) |
| [`generalidad-retos.md`](generalidad-retos.md) | B↔A↔confianza   | G1–G4     | SPEC (decisión #125) |
| [`manifest-v2-sdk.md`](manifest-v2-sdk.md)     | SDK↔B↔ejecución | C1, G, O5 | SPEC (decisión #126) |

Además: `endpoints-studio.md` ganó las secciones ADITIVAS «GET /runs/discarded» (#123) y
«GET /runs/{run_id}/rvsp» (#124); `superficie-visual.md` ganó §8 (branch-ids C-8) y §9
(metrics C-4) — #124.
