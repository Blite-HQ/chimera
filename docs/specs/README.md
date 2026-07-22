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
implementación de otro dueño.** Las fronteras las vigilan `import-linter` (10 contratos) y
CODEOWNERS; si `lint-imports` falla, se arregla el código, no el contrato.

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

| Spec                                                                                                                                      | Plano | Estado |
| ----------------------------------------------------------------------------------------------------------------------------------------- | ----- | ------ |
| _(se llenan en la Etapa 0 — la primera es el esquema: `engine/sql/init_v2.sql` + `tests/invariants/test_esquema_migration.py`, ya VERDE)_ | —     | —      |
