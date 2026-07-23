# chimera-api

API del walking skeleton (postgres+api+studio): SSE de eventos proyectados
sobre el puerto `EventStore`. Contrato en `docs/specs/confianza-api-sse.md`
(freeze §9 + trust/07 §1.2–1.3).

```sh
uv run uvicorn chimera_api.main:app --reload
```
