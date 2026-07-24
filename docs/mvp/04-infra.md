# Dominio Infra — el demo corre en cualquier máquina (dueño natural: Geovanni)

**Rama:** `mvp/infra` · **Base:** `integracion/runtime-confianza`
**Contexto obligatorio:** `docs/mvp/00-plan-maestro.md`,
`tests/seeds/test_seed_infra_compose.py` (xfail — define el done),
`engine/sql/init_v2.sql` (esquema append-only), `api/src/chimera_api/main.py`.

## Nivel MVP (en orden)

1. **Walking skeleton `compose.yaml`**: `postgres` (init con `engine/sql/init_v2.sql`) +
   `api` (uvicorn `chimera_api.main:app`, `CHIMERA_DATABASE_URL` activa el
   `PostgresEventStore`) + `studio` (vite build servido, `VITE_API_URL` al api). Secretos
   vía `*_FILE`, JAMÁS en el YAML. UN evento real de punta a punta = criterio de arranque.
2. **Poner en verde el seed de infra** (quitar el xfail SOLO cuando pase de verdad:
   compose canónico + `*_FILE` + `compose.record.yml`).
3. **Verificación**: levantar el stack y correr
   `tests/integration/test_postgres_event_store.py` contra el Postgres del compose +
   el smoke E2E del dominio runtime-api (POST /runs → SSE → certificado) apuntando al
   stack.

## Nivel Planeado

4. Servicio `worker` (procrastinate) cuando el runtime lo pida (compose canónico del mes).
5. Imagen/targets reproducibles (build args pineados) para el criterio de
   reproducibilidad del reto.

## Reglas del dominio

- TODO el mes es LOCAL (freeze §15.4: Fargate/cloud solo stretch post-27 verde). Nada de AWS.
- No tocar `engine/` ni `capabilities/` — si el compose exige un cambio ahí, decisión
  registrada en `decisiones.md` y cambio mínimo.
