# Knowledge — Infra (plano de infraestructura · Geovanni)

> **Estado: VIGENTE-CON-DRIFT (2026-07-30, #109).** Dos señales actualizadas abajo: el `ollama`
> del compose diseñado quedó archivado (hoy `replay` / Ollama Cloud — addendum de la nota 03) y
> las fechas de dry-run son logística del evento ya terminado (HISTÓRICO en la nota 03 §1.5).
> Drift restante declarado: las «ratificaciones de Geovanni» pendientes son era-de-dueños,
> derogada por la decisión #94.

Notas de la investigación de infraestructura. La nota 01 fue importada al repo en la
consolidación del knowledge base (2026-07-14) desde el documento de trabajo externo; las notas
02–03 se investigaron en la consolidación para cerrar los huecos del plan (§4). **Desde el
cierre S-E (2026-07-18) sus decisiones están tomadas — queda la ratificación final de Geovanni
(ajustable bajo su criterio).** El template (decisión · licencias · impacto en contrato ·
reconciliación) se aplica en cada nota; los chequeos operativos restantes están declarados con
dueño y disparador (precios al provisionar, licencias al crear el Dockerfile, spikes al construir).

## Índice

| Nota                                  | Tema                                                                                                                                                                                                                                                                                 | Contratos que toca                                                                                                                           |
| ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------- |
| [01](01-provisionar-aislar-operar.md) | El método provisionar-aislar-operar: control/data plane (AWS SaaS Lens), escalera de aislamiento (6 escalones), Pulumi+Python (declarativo + Automation API), verificación de infra como escalera                                                                                    | tags `workspace_id`/`principal_id` obligatorios; registro del escalón de aislamiento; punto de encuentro con `execution_profile: remote-job` |
| [02](02-cola-de-jobs-python.md)       | La cola de jobs en Python (reemplazo del BullMQ del diseño original): Procrastinate (Postgres, MIT) integrar; SAQ plan B; arq/Celery/Dramatiq/RQ descartados con racional                                                                                                            | puerto `JobQueue` propio; consume el mismo Postgres del event store (LISTEN/NOTIFY + FOR UPDATE, coherente con trust/01)                     |
| [03](03-entorno-demo-dual.md)         | Diseño del entorno de demo dual: Dockerfiles multi-stage (uv / vite+nginx), compose air-gapped (postgres+api+worker+studio; el `ollama` del diseño quedó archivado — hoy `replay`/Ollama Cloud), ruta ECR/Fargate/ALB sin GPU, calendario de dry-runs (HISTÓRICO — evento terminado) | ninguno del engine; fija el diseño que `infra/` implementará en la fase de build (sesión scaffold v2 / construcción)                         |

## Estado de los pendientes originales

1. **Drift de stack — RESUELTO en la consolidación (2026-07-14):** los pasajes NestJS/BullMQ de la
   nota 01 se migraron al stack vigente (FastAPI + cola Python + Postgres); la elección concreta de
   cola está en la nota 02. **Geovanni ratifica.**
2. **Entregables del demo — CUBIERTOS como diseño en la nota 03** (Dockerfiles, compose, Fargate
   sin GPU verificado en fuente primaria, fechas de dry-run propuestas: local air-gapped 27 jul,
   Fargate 29 jul — **fechas ya pasadas, HISTÓRICO desde 2026-07-30: el evento terminó**). La
   implementación es de la fase de build, no de esta consolidación. **Geovanni
   ratifica diseño y fechas.**
3. **Licencias — RESUELTO (verificadas en vivo 2026-07-14):** Procrastinate MIT, SAQ MIT, uv
   MIT/Apache-2.0, Ollama MIT (Dramatiq LGPL-3.0 descartada); Pulumi Apache-2.0, E2B Apache-2.0
   (SDK Python MIT), Checkov/OPA/Conftest Apache-2.0, Temporal MIT (sección L de la nota 01).
4. **Reconciliación formal de la nota 01 contra `docs/invariants.md`** — sección R de la nota;
   sigue pendiente de Geovanni.
