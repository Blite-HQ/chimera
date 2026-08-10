# Checklist pre-flip OSS

> **Estado: VIGENTE (2026-08-06).** Lo que hay que hacer el día que el repo
> vuelva a ser público — y, sobre todo, lo que YA está hecho para que ese día no
> haya que reconstruir nada de memoria. Cada fila «no se puede hoy» dice la
> causa **verificada contra la API**, no supuesta. Ítem de backlog: O2/M26.

## Estado del repo hoy

`Blite-HQ/chimera` es **privado** (Dylan lo cambió el 2026-08-06 para hacer
estas limpiezas). Estuvo público antes, y volverá a serlo.

## 1 · Ya configurado — no hay que tocarlo el día del flip

| Qué                                                                                   | Estado                                                                                |
| ------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| Merge squash-only, sin merge commit ni rebase                                         | ✅ ya en la config del repo — historia lineal por construcción                        |
| Borrar rama al mergear                                                                | ✅                                                                                    |
| Alertas de Dependabot                                                                 | ✅ activas (`GET /vulnerability-alerts` → 204)                                        |
| Arreglos de seguridad automáticos                                                     | ✅ `{"enabled": true, "paused": false}`                                               |
| Cuarentena de supply-chain                                                            | ✅ `cooldown` 14/90/14/7 en `dependabot.yml` (las de seguridad la saltan a propósito) |
| Escaneo de secretos en CI                                                             | ✅ gitleaks sobre la historia COMPLETA, bloqueante                                    |
| Escaneo de secretos local                                                             | ✅ `pre-commit` sobre lo staged (`scripts/pre-commit-secrets.sh`)                     |
| Auditoría de dependencias                                                             | ✅ `pip-audit` + `pnpm audit --audit-level=high`, bloqueantes                         |
| SAST                                                                                  | ✅ Semgrep (reglas propias + `p/python` + `p/secrets`), advisory                      |
| Hardening del runner                                                                  | ✅ `step-security/harden-runner` en todos los jobs                                    |
| Acciones pinneadas por SHA                                                            | ✅ + Dependabot las mantiene al día                                                   |
| Permisos mínimos del token                                                            | ✅ `permissions: contents: read` por defecto                                          |
| `LICENSE` · `NOTICE` · `CODE_OF_CONDUCT` · `CONTRIBUTING` · `GOVERNANCE` · `SECURITY` | ✅                                                                                    |
| `CITATION.cff`                                                                        | ✅ — GitHub renderiza «Cite this repository»                                          |
| Plantillas de issue y PR · CODEOWNERS                                                 | ✅                                                                                    |

## 2 · Escrito y listo, esperando el flip

| Qué                            | Dónde vive                   | Cómo se aplica                        |
| ------------------------------ | ---------------------------- | ------------------------------------- |
| Protección de `main` (ruleset) | `.github/rulesets/main.json` | `bash scripts/apply-repo-rulesets.sh` |

El ruleset exige: PR con 1 aprobación + CODEOWNERS, hilos resueltos, historia
lineal, sin force-push, sin borrado de rama, solo squash, y **un único check
requerido: `CI gate`** (el job agregador — marcar python/web/docs por separado
dejaría colgado para siempre cualquier PR que los saltee por filtro de rutas).
`bypass_actors` vacío a propósito: aplica también a admins.

**Por qué no está aplicado**: `GET /repos/Blite-HQ/chimera/rulesets` → **403
«Upgrade to GitHub Pro or make this repository public»** (verificado
2026-08-06). Exige repo público o plan de pago. No hay parche que lo habilite
antes, y el script lo dice con esas palabras si se corre hoy.

## 3 · No se puede hoy — con la causa verificada

| Qué                                 | Causa (verificada)                                                              | Cuándo                   |
| ----------------------------------- | ------------------------------------------------------------------------------- | ------------------------ |
| Ruleset / branch protection         | 403 «Upgrade to GitHub Pro or make this repository public»                      | al flip, o con plan pago |
| Reporte privado de vulnerabilidades | `PUT /private-vulnerability-reporting` → **404** en repo privado                | al flip                  |
| Secret scanning + push protection   | `PATCH security_and_analysis` → **422**; es GHAS (público gratis, privado pago) | al flip                  |
| Code scanning (CodeQL)              | mismo caso que arriba                                                           | al flip                  |
| OpenSSF Scorecard                   | la acción exige repo público                                                    | al flip                  |
| Bot de DCO para PRs externos        | no hay PRs externos todavía                                                     | al primer contribuidor   |

## 4 · Bloqueadores REALES del flip (no son configuración)

1. **Historia**: el árbol vendorizado de terceros (`knowledge/quantum/quantathon/`)
   salió de HEAD el 2026-08-05, pero **sigue en los commits**. Publicar el repo
   publica la historia. Decidido con Dylan (2026-08-06): la corrección integral
   de la historia se hace **después de Mejorado**, en una pasada única, cuando el
   proyecto deje de moverse tanto. Hasta entonces queda anotado, no ejecutado.
2. **Licencia de los datos del ICE** — ver `NOTICE` §2. Parcialmente cerrado
   (2026-08-08): esos datos **no se publican como dataset** (el catálogo de
   `GET /datasets` declara solo corpus propios), y la decisión de fondo ya está
   tomada — eran el ejemplo de UN reto y la plataforma no depende de ellos.

   Lo que queda es que publicar el repo publica el árbol. Opción recomendada:
   sacar `knowledge/islanding/raw/ice-*.geojson` —la copia verbatim del portal—
   y conservar las instancias DERIVADAS con el mismo razonamiento de `NOTICE`
   §1. Antes de ejecutarlo, dos comprobaciones que no son opcionales:

   - **`knowledge/nexus/` se ancla a `cr6-*`/`cr8-*`.** La evidencia real de
     H2-1LE cuelga de esas instancias (`index.json`, `consensus.json`).
     Borrarlas huérfana la evidencia más fuerte del proyecto.
   - `scripts/gen_corpus_ice.py` y `capabilities/ingesta/tests/test_geojson_to_graph.py`
     leen el geojson crudo: sacarlo pide reubicar ese test a un fixture propio.

## 5 · El día del flip, en orden

```bash
# 1. repo a público (UI o gh)
gh repo edit Blite-HQ/chimera --visibility public --accept-visibility-change-consequences

# 2. protección de main (ahora sí responde)
bash scripts/apply-repo-rulesets.sh

# 3. reporte privado de vulnerabilidades
gh api -X PUT repos/Blite-HQ/chimera/private-vulnerability-reporting

# 4. secret scanning + push protection
gh api -X PATCH repos/Blite-HQ/chimera \
  -f 'security_and_analysis[secret_scanning][status]=enabled' \
  -f 'security_and_analysis[secret_scanning_push_protection][status]=enabled'

# 5. verificar
bash scripts/apply-repo-rulesets.sh --check
gh api repos/Blite-HQ/chimera --jq '{visibility, security_and_analysis}'
```

Y después: cambiar la ruta de reporte de `SECURITY.md` del correo al flujo
privado de GitHub (ya anotado en ese archivo), y añadir el workflow de
Scorecard.
