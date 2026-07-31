# Decisiones delegadas — cierre del carril runtime+confianza (2026-07-23)

> **Estado: HISTÓRICO (2026-07-30, archivado por #112).** Su «Estado: VIGENTE, pendiente de
> ratificación» era un estado imposible bajo la decisión #94 (ya no hay dueños que
> ratifiquen). 3 de sus pendientes YA están cerrados en código: ModelServer/replay
> implementado (`engine/src/blite/protocols/model_server.py`), `ieee14-topology.json`
> entregado, y el golden path ya no usa fixture fabricado (`challenges/reto1/run_all.py`).
> El header viejo queda debajo como registro.
>
> **Estado: VIGENTE, pendiente de ratificación.** Dylan delegó cerrar el carril en esta
> sesión tomando las decisiones necesarias sin esperar validación previa. Este documento
> las registra TODAS para que Steven (ejecución) y Sebas (ciencia) las validen, editen o
> veten. Convención del equipo: PENDIENTE = marca de revisión, no decisión abierta.
> Rama: `integracion/runtime-confianza` (commits `8afc448..16142ce`). Gates 4/4 verdes.

## Para Steven (plano de ejecución)

1. **Costura `post_invoke` en `runtime/loop.py`** (commit `ef2ae62`) — parámetro opcional
   (default `None`, tus tests intactos): un delegate emite eventos DESPUÉS del step de
   invocación y ANTES del terminal, para que la verificación entre al corte de
   procedencia. El loop sigue sin verificar (INV-2) — solo ofrece el punto de inserción.
   Si el delegate levanta ⇒ `run.failed` con `error_kind` = tipo de la excepción (tu
   convención del registry). _Racional:_ sin esto, los eventos de verificación caerían
   post-terminal y el certificado no los ampararía.
2. **Protocol `Verifier` con properties read-only** (commit `ef2ae62`) — los miembros
   `verifier_class`/`anchor_kind`/`determinism` pasaron de atributos escribibles a
   properties de solo lectura. _Racional:_ el Protocol como estaba exigía atributos
   mutables ⇒ ningún adapter frozen podía conformar estáticamente (pyright) —
   contradicción con la inmutabilidad del propio plano. Cero cambio semántico del §4.
3. **Tus 6 decisiones de carril (doc de features §2): VALIDADAS las 6 sin veto.**
   `MaxStepsExceeded`, `actor_id service:runtime` en eventos del runtime, perfil default
   `in-process`, ctx del ContentStore fail-closed, JSON canónico mínimo del loop, y los
   payloads previos avisados. Ninguna contradice el freeze ni el golden path.
4. **ModelServer/replay (§15.7): DIFERIDO deliberadamente.** El golden path del demo no
   invoca modelos (el proposer es capability-side: QAOA/solvers ya reales); `serving` es
   tu área y el contrato replay está congelado — lo implementas cuando toque, sin
   bloqueo mutuo.
5. **Campos §1 del manifest (`execution_profile` etc.): DIFERIDOS.** El default
   `in-process` hardcodeado que documentaste sigue vigente; no bloquea el demo. Va en la
   sesión SDK/capabilities.

## Para Sebas (ciencia)

6. **`ExecutionVerifier` (pandapower) implementado GENÉRICO** (commit `16142ce`, spec
   trust/12): checks por isla (`island_connectivity`, `island_has_source`,
   `powerflow_converged`, `voltage_limits`, `line_loading`, `power_balance`), verdict
   derivado exacto de la spec (no-convergencia ⇒ `inconclusive`, jamás `fail`; hard-fail
   gana). **La topología eléctrica y los límites son DATOS de entrada** (regla "reglas
   como datos") — el `anchor_digest` pinnea el modelo de red declarado.
7. **Lo que falta de ti (único faltante del golden path ieee14 completo):** el dato
   `knowledge/islanding/` con (a) topología eléctrica de ieee14 en el formato genérico
   de `blite_cap_sim.power_flow` (buses/slack/branches/loads), (b) límites: banda
   `vm_pu`, `line_loading_max_percent`, `slack_p_max_mw` por isla, y (c) la convención
   de fuente/slack por isla. Con ese dato se regenera `gen-example-bundle.py` desde un
   run REAL (hoy el fixture sigue fabricado — el ensamblador ya existe y está probado).
8. **Decisiones dentro del verificador que puedes editar:** isla sin fuente = hard-fail
   (no inconclusive); `power_balance` = |P slack| ≤ límite, activo solo si el dato
   existe; razón de abstención por no-convergencia = `undecidable`; una Attestation por
   PARTICIÓN con checks prefijados `island-{k}:` (la attestation-por-isla del freeze §9
   queda para cuando el Studio pida badges por isla — no cambia patas del punto 7).

## Decisiones del plano confianza (área de Dylan — registradas por transparencia)

9. **Energía mentida SIN short-circuit:** el `ExactSolverVerifier` resuelve siempre
   (el `Differential` congelado exige un status real; saltarse el solve = fabricar
   evidencia). El short-circuit de la nota 10 §1.1 va a discusión de freeze (§4 aditivos).
10. **Ensamblador event-sourced fail-closed** (`certificate/assemble.py`): conclusiones
    por mínimo (cualquier pata `fail` ⇒ `refuted`; `inconclusive` socava; nivel = mín de
    patas pass); `valid_as_of` = `occurred_at` del terminal (determinista); solo claims
    presentes en el stream entran al certificado.
11. **`claim_view_digest` común** en `verification/claim.py` — emisor, adapters y
    checker computan la MISMA vista `{canonical_statement, scope}` (candado en tests).
12. **`inconclusive_reason` por presupuesto:** `budget_exhausted` (CP-SAT, presupuesto
    determinista) y `undecidable` (pandapower, no-convergencia) — "timeout" habría
    implicado reloj de pared.

## Estado verificable

`uv run pytest` → 345 passed · `lint-imports` 12/12 · `ruff` limpio · `pyright` 0.
El test `tests/unit/certificate/test_assemble.py::TestDosPatasReales` es el golden path
completo con CERO dobles: run vivo → CP-SAT real + pandapower real → certificado 7/7
con las dos anclas {solver, execution} que exige la policy default. El certificado de
REFUTACIÓN (titular AL0) también verifica 7/7.
