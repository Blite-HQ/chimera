# Spec de costura — Manifest v2 en el SDK (costura SDK↔B↔ejecución)

**Gobernada por:** freeze **§1** (`CapabilityManifest` v2 — la tabla de los 4 campos ES la
letra congelada; la marca [MEJORADO · censo §1.7-B] registra que el SDK sigue en v1) +
**§13** (reintentos por `side_effects`) + **§6** (la Policy consume el eje de riesgo) +
**§8** (la etapa 2 chequea `required_permission`) · el DDL (`engine/sql/init_v2.sql`) y la
matriz `interaction × execution_profile` (`blite.runtime.dispatch`) YA están verdes — esta
spec cierra el tercer lado del triángulo: el SDK.
**Costura:** SDK↔B↔ejecución · **Estado:** SPEC (Fase 0 Mejorado, 2026-07-31, decisión #127) ·
**Consumen:** C1 (implementa), G1/G2 (capabilities nuevas nacen v2), O5/M13 (mapeo a MCP).

> «El mayor ratio valor/esfuerzo de M8» (cobertura): sin los 4 campos en el SDK, el loop no
> puede razonar riesgo, la ingesta vive de un docstring-workaround y M13 no tiene manifest
> que mapear. Esta spec NO re-decide el §1 — aterriza su letra en
> `sdk/src/blite_capability/manifest.py` con las decisiones de borde #127.

## Contrato

**1 · Los 4 campos aterrizan TAL CUAL la letra §1:**

```python
side_effects: Literal["pure", "reversible-external", "irreversible-external"]
required_permission: str
interaction: Literal["request_response", "job", "stream"]
execution_profile: Literal["in-process", "service", "remote-job"] = "in-process"
```

- **Sin defaults para el riesgo (#127):** solo `execution_profile` tiene default (la letra
  §1); los otros tres son OBLIGATORIOS — defaultear `side_effects` mentiría el eje que la
  Policy (§6) y la regla de reintento (§13) consumen. Un manifest sin migrar FALLA al
  cargar su entry point y cae en `failed[]` del registry (§1: tolerante a fallos POR entry
  point) — visible, jamás silencioso.
- **El `@dataclass(frozen=True)` se queda** (SDK-standalone sin deps, contrato
  import-linter); los tres literals se validan en `__post_init__` (`ValueError`
  fail-closed). La matriz `interaction × execution_profile` sigue validándose al cargar el
  `DistributionManifest` (§1 [S-F]) — el manifest declara el par, la carga lo rechaza si es
  inválido.
- `Registry(Protocol).list()` ya promete el manifest COMPLETO (§1) — cero cambio de firma;
  el modelo crece y `list()` lo arrastra (el mapeo a MCP tool de O5 no requiere llamadas
  extra, letra §1).

**2 · Convención de `required_permission` (#127).** Baseline **`capability:invoke`** para
capability local pura; permisos FINOS donde el riesgo lo pida (los `capability:ingest:*`
del workaround de ingesta se portan tal cual; un adapter con egress declarará el suyo —
V6/M5). El manifest DECLARA el permiso; autorizarlo es de la etapa 2 del gateway contra la
intersección efectiva (§8) — nunca del SDK.

**3 · Plan de migración COORDINADA de las 13 (C1 lo ejecuta en un checkpoint + smoke 2.5).**

| Entry point                      | `side_effects`        | `required_permission`               | `interaction`      | `execution_profile` |
| -------------------------------- | --------------------- | ----------------------------------- | ------------------ | ------------------- |
| `blite.graphs.maxcut`            | `pure`                | `capability:invoke`                 | `request_response` | `in-process`        |
| `blite.graphs.partition`         | `pure`                | `capability:invoke`                 | `request_response` | `in-process`        |
| `blite.ingesta.snapshot.fetch`   | `reversible-external` | `capability:ingest:external-source` | `job`              | `in-process`        |
| `blite.ingesta.geojson.to_graph` | `pure`                | `capability:ingest:derive`          | `request_response` | `in-process`        |
| `blite.ml.classify`              | `pure`                | `capability:invoke`                 | `request_response` | `in-process`        |
| `blite.numeric.matrix_ops`       | `pure`                | `capability:invoke`                 | `request_response` | `in-process`        |
| `blite.quantum.qaoa`             | `pure`                | `capability:invoke`                 | `request_response` | `in-process`        |
| `blite.report.render_figure`     | `pure`                | `capability:invoke`                 | `request_response` | `in-process`        |
| `blite.report.compile_pdf`       | `pure`                | `capability:invoke`                 | `request_response` | `in-process`        |
| `blite.report.compile_slides`    | `pure`                | `capability:invoke`                 | `request_response` | `in-process`        |
| `blite.sim.power_flow`           | `pure`                | `capability:invoke`                 | `request_response` | `in-process`        |
| `blite.smt.check_constraints`    | `pure`                | `capability:invoke`                 | `request_response` | `in-process`        |
| `blite.solvers.qubo`             | `pure`                | `capability:invoke`                 | `request_response` | `in-process`        |

- La única no-pura hoy es `snapshot.fetch` (egress de red, re-ejecutable ⇒
  `reversible-external`; su semántica de job ya estaba declarada en el workaround). Los
  valores de ingesta son los del docstring-workaround (`capabilities/ingesta/.../tool.py`)
  — **ese workaround MUERE con la migración**: la tabla del docstring se borra y sus
  valores viven en el manifest (una sola fuente).
- El primer caso real de `service`/`remote-job` será el adapter qnexus (V6/M5) — NO es una
  de las 13; nace v2 directamente.

**4 · Gate de genericidad EXTENDIDO (#127).** `_manifest_text`
(`tests/invariants/test_capability_genericity.py`) hoy serializa solo
`id/description/input_schema/output_schema`; pasa a serializar el manifest **COMPLETO**
(incl. `required_permission`, `tags`, `version` y los 4 campos) — un permiso o tag con
vocabulario de escenario es la misma fuga que un schema con él (ADR-029, denylist
`tests/invariants/scenario_denylist.txt`).

## Eventos / payloads nuevos

Ninguno. `registry.loaded`/`registry.capability_load_failed` (§1) ya cubren la carga; un
manifest v1 sin migrar aparece en `failed[]` — eso es señal, no evento nuevo.

## Interfaces con otros dominios

| Interfaz                                            | Dominio          | Estado                                               |
| --------------------------------------------------- | ---------------- | ---------------------------------------------------- |
| `CapabilityManifest` v2 (4 campos, `__post_init__`) | SDK              | SPEC — seed xfail; implementa C1                     |
| Migración de las 13 + muerte del workaround         | B (capabilities) | SPEC — tabla arriba; C1 en un checkpoint + smoke 2.5 |
| Gate de genericidad sobre el manifest completo      | invariantes      | SPEC — C1 lo extiende junto con la migración         |
| `Registry.list()` → mapeo MCP                       | O5/M13           | Desbloqueado por esta spec; O5 no la cambia          |

## Fronteras (qué NO decide esta spec)

- **El `DistributionManifest` como código** (pins, allowlist) — O5/M13 y C1 lo materializan
  sobre la matriz ya validada; aquí solo se cita.
- **Los permisos finos futuros** (egress, approvals) — los declara cada adapter nuevo con
  su registro (V6, P11).
- **La semántica de `stream`** — sigue `NotImplementedError` en Fase 1 (§1 [S-F]); esta
  spec no la abre.

## Tests de contrato (fixtures de costura)

Declarado (modelo v2 aún no existe — Fase 1 C1):
`tests/fixtures/contract/manifest/capability-manifest-v2.json` (dataclass → `asdict`,
espejo Studio; generador nuevo `gen-contract-fixtures-manifest.py` al existir los campos).

## Tests semilla

- `tests/seeds/test_seed_manifest_v2.py` — **VERDE (C-1, 2026-07-31)**: los 4 campos
  existen con la forma §1 (`execution_profile` default `"in-process"`); construir sin
  `side_effects` explota (obligatorio, #127); un literal inválido explota en
  `__post_init__`. El xfail se retiró con la migración (decisión #130): SDK + 13
  capabilities en el mismo checkpoint, workaround de ingesta muerto, gate de
  genericidad sobre el manifest completo, fixture `contract/manifest/` generado.
