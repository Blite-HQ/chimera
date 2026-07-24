# Dominio Runtime/API — el sistema se vuelve usable (dueño natural: Steven)

**Rama:** `mvp/runtime-api` · **Base:** `mvp/base`
**Contexto obligatorio:** `docs/mvp/00-plan-maestro.md`, `docs/decisiones-delegadas-2026-07-23.md`
(decisiones 1–5 ya tomadas), `api/src/chimera_api/`, `engine/src/blite/runtime/loop.py`
(costura `post_invoke`), `blite/verification/orchestrator.py`, `blite/certificate/assemble.py`.

## Nivel MVP (en orden)

1. **`POST /runs` en `chimera_api`** — la puerta de entrada que hoy no existe (el
   `gatewayClient.ts` del Studio la espera). Body: `{capability_id, inputs, claim
{canonical_statement, scope, claim_type}, max_steps?}`. Efecto: compone
   `make_verification_delegate` (verifiers según la instancia declarada) + `execute_run`
   sobre el `EventStore` del proceso (factory por `CHIMERA_DATABASE_URL`), retorna
   `{run_id}` de inmediato y el run corre en background task de FastAPI. El SSE existente
   (`GET /runs/{id}/events`) transmite el progreso. TDD con el patrón de
   `tests/unit/api/test_app_sse.py`.
2. **`POST /runs/{id}/certificate`** (o `GET` si el run terminó): invoca `assemble_bundle`
   con el stream real y retorna el bundle JSON (llave efímera de proceso por ahora —
   decisión ya registrada: custodia = KeyProvider post-MVP). El Studio lo descarga y el
   juez corre `verify-bundle`.
3. **Registro de verifiers por instancia**: mapa simple en el API (config/factory) de qué
   verifiers aplican al claim (CP-SAT siempre; pandapower cuando el dato eléctrico de la
   instancia exista — ver dominio ciencia). Fail-closed: instancia sin verifiers ⇒ 400,
   jamás un run sin verificación.
4. **Smoke E2E**: test de integración que hace POST /runs → espera terminal por SSE →
   GET certificate → `check_bundle` 7/7. Ese test ES el MVP del dominio.

## Nivel Planeado (solo si el MVP del dominio está verde)

5. Cruce del gateway completo por step del loop (freeze §13) + flip del placeholder AX1
   (`tests/invariants/test_types.py::test_event_has_non_null_actor_id`).
6. ModelServer backend `replay` (freeze §15.7): fixtures content-addressed, miss ⇒
   `model.call.failed {replay_miss}`, JAMÁS passthrough a red.
7. Auth mínima del API (hoy no hay — documentada como pendiente consciente).

## Reglas del dominio

- No tocar `verification/`, `certificate/` (área confianza) — se consumen como están.
- La API es de Dylan y el runtime de Steven según CODEOWNERS: esta sesión cruza ambas
  áreas POR MANDATO del cierre; registrar cada cruce en `decisiones.md`.
- El endpoint no inventa contratos: reusa los tipos existentes (OptimalityClaim,
  ClaimDeclaration) — si algo no alcanza, decisión registrada + tipo mínimo aditivo.
