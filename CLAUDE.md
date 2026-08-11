# Chimera — contexto para agentes

## Qué es esto HOY

Chimera nació en la Quantathon 2026 y hoy es un **producto en desarrollo
activo**: una plataforma de runs agénticos con verificación y certificados.
**No optimices para demo ni asumas contexto de hackathon.** Los retos 1–3 son
casos de uso y material de prueba, no el producto.

- Los datos del ICE (`knowledge/islanding/`) son **datos de prueba/caso de
  uso** — se usan solo en CI, e2e y validación; jamás son un activo del
  producto (decisión #173).
- El mapa y visualizaciones similares son **artifacts genéricos** disparados
  por el tipo de dato, no features de un reto (#173.2).

## Autoridades (leer antes de concluir nada)

- **Decisiones**: `docs/mvp/decisiones.md` — ledger continuo APPEND-ONLY.
  Números duplicados #153–#169 se citan con sufijo `-V`/`-O` (#170). Si tu
  sesión anexa, usá el rango que control te asignó.
- **Docs**: `docs/README.md` es el índice de autoridad. Fase actual:
  `docs/mejorado/` (plan de cierre: `09-cierre.md`).
- **Contratos congelados**: `docs/contract-freeze.md` — solo se tocan por
  ceremonia de supersede REGISTRADA en el ledger.

## Reglas duras

1. **Cero mocks silenciosos** — todo stub se etiqueta y registra.
2. **DoD = integración viva** contra compose, no solo tests verdes.
3. Artefactos con digest embebido (`knowledge/*/corpus/`, fixtures sellados)
   **jamás se reformatean ni re-digestean** — el congelado manda.
4. Nada de push sin coordinación de la sesión de control. Operaciones remotas
   por HTTPS/`gh` (el SSH del entorno no autentica contra este repo).
5. Commits: conventional, minúsculas, ≤100 caracteres.

## Gates (todos deben quedar verdes)

```bash
uv run pytest            # + cobertura
uv run lint-imports && uv run ruff check && uv run ruff format --check
uv run pyright
pnpm -C apps/studio run test:run && pnpm -C apps/studio run lint
pnpm run arch            # depcruise
pnpm run docs:lint && pnpm run format:check
```

## Gotchas del entorno

- **Worktrees**: `uv sync` NO instala los editables → usar el python del repo
  principal + `PYTHONPATH` del worktree. Git NO corre hooks en worktrees.
  `scripts/smoke_infra.sh` no corre desde un worktree.
- Tras mergear paquetes nuevos: `uv sync --locked --all-packages --all-extras`
  (sin `--all-packages` DESINSTALA miembros del workspace).
- La suite del Studio es sensible a carga de máquina (timeouts de 5s).
- Si `docker compose build` falla con `error getting credentials` /
  `desktop.exe`: el `~/.docker/config.json` declara un credsStore ausente en
  esta distro. Workaround: `export DOCKER_CONFIG=$(mktemp -d) && echo '{}' >
$DOCKER_CONFIG/config.json` antes del build (#150).
