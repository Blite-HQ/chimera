# chimera-api

API del runtime (postgres+api+studio) sobre el puerto `EventStore`. Contrato
SSE en `docs/specs/confianza-api-sse.md` (freeze §9 + trust/07 §1.2–1.3);
lecturas del Studio en `docs/specs/endpoints-studio.md`.

Rutas reales (`src/chimera_api/`) _[S3 2026-07-30: esta sección describía solo
el SSE; se completa con las 10 rutas vivas]_:

| Ruta                                      | Qué sirve                                                                    |
| ----------------------------------------- | ---------------------------------------------------------------------------- |
| `POST /runs` (202)                        | arranca un run — body claim-first o `{mission, …}` (modo misión) — `runs.py` |
| `GET /runs/{id}/events`                   | stream SSE de eventos proyectados — `app.py`                                 |
| `GET /runs`                               | lista de runs (proyección `RunSummary`) — `reads.py`                         |
| `GET /runs/{id}/artifacts`                | artifacts del bundle con veredicto y nivel titular — `reads.py`              |
| `GET /runs/{id}/knowledge`                | claims/conclusiones del bundle — `reads.py`                                  |
| `GET /runs/{id}/steps/{step_id}/evidence` | detalle de evidencia por paso — `reads.py`                                   |
| `GET /runs/{id}/ablation`                 | métricas de ablación — `reads.py`                                            |
| `GET /runs/{id}/topology`                 | topología/particiones proyectadas — `reads.py`                               |
| `GET /runs/{id}/certificate`              | bundle DSSE del run — `certificate.py`                                       |
| `GET /health`                             | health check — `app.py`                                                      |

```sh
uv run uvicorn chimera_api.main:app --reload
```
