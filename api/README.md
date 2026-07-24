# chimera-api

API del walking skeleton (postgres+api+studio): SSE de eventos proyectados
sobre el puerto `EventStore`. Contrato en `docs/specs/confianza-api-sse.md`
(freeze §9 + trust/07 §1.2–1.3).

```sh
uv run uvicorn chimera_api.main:app --reload
```

## CORS (solo dev local)

En compose, `studio` y `api` son same-origin vía el reverse-proxy de nginx
(`docker/studio-nginx.conf`) — CORS no aplica ahí. Corriendo `uvicorn` suelto
contra un `pnpm -C apps/studio dev` (`vite`, otro origin) sí lo necesitás:

```sh
CHIMERA_CORS_ORIGINS=http://localhost:5173 uv run uvicorn chimera_api.main:app --reload
```

CSV de orígenes exactos; sin la var, sin `CORSMiddleware` (default de siempre).
