# Dominio Frontend/Studio — el demo se VE en vivo (dueño natural: Dylan)

**Rama:** `mvp/frontend-studio` · **Base:** `integracion/runtime-confianza`
**Contexto obligatorio:** `docs/mvp/00-plan-maestro.md`, `apps/studio/DESIGN.md` (design
system manda), `apps/studio/src/data/` (data layer F3: TanStack Query + Zod + seam SSE),
`apps/studio/src/gatewayClient.ts` (único punto de egress — INV-1, dependency-cruiser).

## Nivel MVP (en orden)

1. **Cablear el seam SSE a la API real** (`GET /runs/{id}/events`): el RunTimeline deja
   los fixtures y consume eventos vivos (catch-up por `Last-Event-ID` ya implementado del
   lado API). Toggle limpio fixtures↔vivo por env (`VITE_API_URL` ausente = fixtures) —
   el modo fixtures NO se borra (es el fallback del demo).
2. **Disparar un run desde el Studio**: pantalla mínima "nuevo run" (instancia + proposer)
   que hace `POST /runs` vía `gatewayClient` (el endpoint lo entrega el dominio
   runtime-api; mientras no exista, programar contra el contrato del plan 01 con MSW/mock
   y marcar el cambio a vivo como tarea de 5 minutos).
3. **Certificado real**: `CertificateView` consume el bundle de `GET /runs/{id}/certificate`
   (envelope DSSE — mismo shape del fixture actual) + botón de descarga del bundle
   completo ("verifíquelo usted: `python scripts/verify-bundle.py bundle.json`").
   El certificado de REFUTACIÓN se muestra con la misma dignidad que el pass (titular
   AL0, verdict refuted) — es el clímax del guion.
4. **Los eventos de verificación en el timeline**: `claim.emitted` y
   `verification.completed` renderizados con AssuranceBadge (clase+AL) y verdict — la
   proyección del API ya los pasa íntegros.

## Nivel Planeado

5. Mockups + layout definitivo multi-pantalla (runs/artifacts/papers/files) según
   `~/.claude/plans/chimera-carril2-frontend-studio.md` (mockups-primero, refs de layout:
   Vercel/Claude/Nexus/MS Discovery) y extracción de la librería de componentes por
   repetición real.
6. Badges por isla (cuando la attestation por isla exista — hoy checks prefijados
   `island-{k}:` dentro del predicate: se pueden agrupar visualmente YA con eso).
7. Gráfico r vs p del experimento (dataviz sobre wrapper shadcn — regla del stack).

## Reglas del dominio

- Stack cerrado: shadcn base, charts SOLO vía wrapper, TanStack+Zod, ustedeo, dark-first.
- Egress SOLO por `gatewayClient.ts` (dependency-cruiser lo gatea).
- Gates propios: `pnpm -C apps/studio test && pnpm -C apps/studio run lint && pnpm -C
apps/studio run arch` (además de los 4 de Python si se toca el repo raíz).
- Cero vocabulario rung (quedan restos en componentes viejos: matarlos al tocarlos).
