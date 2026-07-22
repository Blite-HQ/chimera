# CHIMERA — Auditoría de las ratificaciones REALES (S-F) · Fase A · 2026-07-21

> **Qué es esto.** Los Pasos 1→2 del flujo pre-S-G (`protocolo-auditoria-ratificaciones.md` — vive
> solo en la rama ejercicio; pin: `git show 68af0c1:docs/research/protocolo-auditoria-ratificaciones.md`)
> aplicados a las ratificaciones **reales** de Sebas/Steven/Geovanni y a los cambios de código que
> los dueños **ya aplicaron** en la rama `ratificacion/consolidacion-sf`. **Paso 1** = normalizar las
> 3 respuestas a la forma del anexo simulado (comparables 1:1). **Paso 2** = auditar cada
> objeción/cambio contra el estado congelado (S-E = main) y decidir, por hallazgo, quién gana —
> con la **regla dura**: en las ratificaciones reales **el dueño manda en su plano** (su decisión se
> acata, no se refuta; solo se verifica coherencia interna y que no contradiga la base lógica).
>
> **Contrapeso independiente:** la simulación (`ejercicio/sf-ratificacion-simulada`) NO se tocó; la
> comparación simulada↔real y la convergencia son el paso POSTERIOR (§5 del protocolo), no esto.
>
> **Integridad.** Fase A = **cero escrituras al repo salvo este reporte**. Todo lo ejecutable se
> corrió con `uv run --frozen` (lock intacto, `git status --porcelain` vacío tras cada corrida).
> Método de doble pasada: (a) auditoría con evidencia primaria y **corridas reales**; (b) **3
> sub-agentes de refutación con contexto fresco** (ciencia / ejecución+código-aplicado / infra) con
> postura hostil. Sus veredictos están integrados abajo.

---

## 1 · Veredictos globales (declarado por el dueño → auditado)

| Dueño · plano          | Veredicto declarado   | Auditoría (Fase A)                                                                                                                                                                                                                                                                            |
| ---------------------- | --------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Steven** · ejecución | **RATIFICADO**        | **Sostiene.** 8 secciones sin objeción bloqueante — verificado. Su acción derivada #1 (endurecer AX3) **ya fue aplicada** (`0f74343`) y el gate la caza en vivo. Acciones #2/#3 + tests semilla = S-G.                                                                                        |
| **Geovanni** · infra   | **OK CON OBJECIONES** | **Objeción ítem-4 (Ollama Cloud) ACATADA** (su plano; no viola invariantes). 5 ítems `[COMPLETÁ VOS]` **marcados** (solo ejecuté ítem-6). LiteLLM: propuesta de drop **declinada** — se mantiene (aval Steven + requisito multi-proveedor de Dylan).                                          |
| **Sebas** · ciencia    | **OK CON MATICES**    | **Ciencia CONFIRMADA por corrida**: 6/6 digests con el lock actual, ieee30 35/32170 por enumeración independiente, vector de falla exacto. 2 matices de **completitud** (scripts inexistentes + placeholders). `metodos`→re-estampar = su decisión, **acatada** (pendiente cerrar identidad). |

**Lectura global.** Ninguna objeción invalida una decisión de diseño congelada. Las **decisiones de
dueño se acatan** (Ollama Cloud; `metodos` de ieee30). Los **cambios de código que los dueños
aplicaron son correctos y coherentes** con lo que ratificaron, y **todos los gates quedan verdes**.
Lo que sobrevive para aplicar es poco y de bajo riesgo (§8); casi todo el resto es **marca de
revisión** que solo Dylan / el dueño / una decisión cruzada pueden cerrar (§7).

---

## 2 · Normalización (Paso 1) — las 3 ratificaciones en forma comparable

### 2.A · Steven (ejecución) — RATIFICADO

| Ítem del checklist (guía §4)                       | Veredicto del dueño | Nota                                                                                     |
| -------------------------------------------------- | ------------------- | ---------------------------------------------------------------------------------------- |
| §1 Manifest v2 (`interaction`/`execution_profile`) | ✅ OK               | Coincide con execution/06 §11; `remote-job`⇒`JobRef`, no-soportado⇒`NotImplementedError` |
| §2 Las 8 etapas + disolución de `policy`           | ✅ OK               | `provenance:pre/post` como etapa nombrada = mejora sobre su nota 01                      |
| §3 Reautorización a mitad de pipeline fail-closed  | ✅ OK               | Cierra su §8.4 en la dirección segura                                                    |
| §4 Run jerárquico (opción A + `parent_run_id`)     | ✅ OK               | Confirma su opción A; cierra el modo de falla del `RunStep` colgado (§3)                 |
| §5 step↔job 1:1, cancelación, `max_steps`          | ✅ OK               | `max_steps` obligatorio = su mitigación pedida, vuelta contrato                          |
| §6 Idempotencia — `side_effects` manda             | ✅ OK               | Regla segura que su nota 03 recomendaba                                                  |
| §7 Model router `ModelPort`/`ModelServer`          | ✅ OK               | **+ Acción derivada #1: endurecer AX3 (no opcional, primer PR de S-G)**                  |
| §8 Registry tolerante a fallos                     | ✅ OK               | execution/04 verbatim; distinción "deshabilitada≠falló"                                  |

**Acciones derivadas (refuerzos, no objeciones):** #1 endurecer AX3 (`litellm`/`openai`/`anthropic`
explícitos) — **pide que sea obligatorio, no "si sobra tiempo"**; #2 Registry real sobre
`importlib.metadata`; #3 Pipeline/Stage explícito in-process. + 6 tests semilla como base para Dylan.
**Gap de código esperado (pre-construcción):** `runtime/registry.py` es stub; los `__init__.py` de
`gateway/runtime/serving/protocols` son docstrings — punto de partida, no regresión.

### 2.B · Geovanni (infra) — OK CON OBJECIONES

| Ítem (guía §5)                             | Veredicto del dueño             | Nota                                                                                                                                                                                   |
| ------------------------------------------ | ------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1 Escalera de custodia de llaves (§7)      | **`[COMPLETÁ VOS]`**            | No lo cierra (no tenía §7/trust-15 §4 a la vista)                                                                                                                                      |
| 2 Cola Procrastinate/Postgres, sin Redis   | **`[CONFIRMÁ VOS]`** → lee OK   | Coherente con su nota 02 congelada; BullMQ/Redis sería objeción a su propia nota                                                                                                       |
| 3 Demo dual: local manda, Fargate=stretch  | **`[COMPLETÁ VOS]`**            | Remite a §15.4 + cierre de infra/03                                                                                                                                                    |
| **4 Modelo Ollama `llama3.2:3b`**          | **OBJECIÓN (con causa)**        | No corre en su hardware ⇒ **Ollama Cloud passthrough** (`gpt-oss:20b-cloud`), `OLLAMA_API_KEY`, egress; rompe air-gap (soberanía=Fase 2). Kimi K3 NO va (no está en Ollama al 20-jul). |
| 5 Calendario de dry-runs (27/29)           | **`[COMPLETÁ VOS]` con equipo** | Ratificación de fechas con el equipo                                                                                                                                                   |
| 6 Reconciliación infra/01 §R vs invariants | **`[COMPLETÁ VOS]` ejecutable** | **No ejecutada por él** — la ejecuté yo (§5)                                                                                                                                           |
| 7 Huecos Fase 2 (§15.8)                    | **`[COMPLETÁ VOS]`**            | Recinto air-gapped + north-star; confirmar que quedan como huecos declarados                                                                                                           |
| Fuera de checklist: **dropear LiteLLM**    | Propuesta                       | **Pisa el §4 de Steven** → supersesión con causa, **necesita aval de Steven** (no unilateral)                                                                                          |

### 2.C · Sebas (ciencia) — OK CON MATICES · _(el borrador está superado por el final; no se audita como vigente)_

| Ítem (guía §3)                             | Veredicto del dueño     | Nota                                                                                                                                                                                     |
| ------------------------------------------ | ----------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1.1 Estratificación del C1 (Max-Cut core)  | OK                      | Extensión "constraint mixers" con base citable (Hadfield)                                                                                                                                |
| 1.2 S=100 parte de la instancia            | OK                      | Márgenes al umbral x.5 idénticos en 2 entornos (0.0298/0.0322/0.0090)                                                                                                                    |
| **1.3 Segunda ancla ieee30 (vectorizada)** | **✅ EJECUTADO**        | 105 s, enum uniforme=35 / flujo=32170 ✓. **`metodos`→`["cpsat","bruteforce_vectorized"]` ⇒ 2 digests cambian ⇒ re-estampar §15.3** (su aviso vale como "se reporta, no se sobreescribe") |
| **1.4 Regeneración corpus + 6 digests**    | **✅ EJECUTADO ×2**     | 6/6 en 2 entornos independientes. **⚠ contiene 2 placeholders sin llenar** (`[PEGAR AQUÍ…]`, `digest [pegar §1.4]`)                                                                      |
| 1.5 Identidad `dataset_id`↔digest          | OK con propuesta        | Estampar semántica de comparación (por VALOR de corte / asignación x₀=0, jamás bitstring)                                                                                                |
| 1.6 Campos de evidencia (§11)              | OK con 1 aditivo        | `seeds.sampler: "unsupported"` para emulador cloud                                                                                                                                       |
| 1.7 Consenso (CONSENSUS_REPLICATION, AL2)  | OK, matiz resuelto      | Réplica ≠ concordancia; seeds pinned = backends locales                                                                                                                                  |
| **1.8 Falla sembrada — bus concreto**      | **✅ EJECUTADO**        | ieee14-flujo **bus 1** (0-based) → corte 32597, gap 24473; prohibidos [7] / [0,1,11]; uniforme bus 8                                                                                     |
| 1.9 cr8 + cr6                              | **PENDIENTE (trabajo)** | Datos ICE validados; falta corredor + peso. CORE del demo en vivo — prioridad subida                                                                                                     |

**Hallazgos accionables del dueño:** (1) deps del corpus ausentes del pyproject → PR único S-G;
(2) pin `pandas<3` (pandapower revienta con pandas 3.x); (3) ratificación por digest, no `git status`
(CRLF/LF en Windows).

---

## 3 · Auditoría y decisión (Paso 2) — hallazgo por hallazgo

> Clasificación: **CONFIRMADO / MATIZADO / REFUTADO / ACATADO-dueño** + **P0/P1/P2**. "Quién gana"
> según la tabla §2 del protocolo. Las decisiones de dueño se **acatan** (no se refutan).

### 3.A · Ciencia (Sebas) — _pasada (a) corrida real + (b) refutación con contexto fresco_

| #   | Hallazgo                                                                                                                                                                   | Veredicto                               | Prioridad                       | Evidencia primaria (corrida / archivo:línea)                                                                                                                                                                                                                                                                                                                                                                            |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------- | ------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| C1  | Receta §1.9 reproduce 6/6 digests con el **lock actual**                                                                                                                   | **CONFIRMADO** (×2 corridas)            | — (mejora ya lograda)           | `uv run --frozen` recipe → frozen(§15.3)==committed==embedded==regenerado 6/6; márgenes 0.0298/0.0322/0.0090. El riesgo de que la receta rompiera con el lock **quedó resuelto** por `0f74343`.                                                                                                                                                                                                                         |
| C2  | Segunda ancla ieee30 = enum exhaustiva → 35 / 32170                                                                                                                        | **CONFIRMADO** (2 enums independientes) | —                               | Enumeración numpy 2²⁹ (x₀=0, 536 870 912 asignaciones, sin CP-SAT): uniforme=35, flujo=32170, == congelado.                                                                                                                                                                                                                                                                                                             |
| C3  | Vector de falla sembrada (bus 1 flujo / bus 8 uniforme)                                                                                                                    | **CONFIRMADO** (recompute exacto)       | P1 (seed de S-G)                | ieee14-flujo bus 1 → corte 32597, gap 24473 (42.9%); prohibido por degeneración **[7]** (única arista `[6,7,0]` peso 0); uniforme prohibidos **[0,1,11]**, bus 8 → corte 12, gap 4. top-3 flujo = 24473/23239/13924 (= bus 1/0/4 del doc).                                                                                                                                                                              |
| C4  | **La FINAL referencia `scripts/gen_corpus_islanding.py` y `scripts/verify_corpus_digests.py` (dice "queda en el repo") + 2 placeholders sin llenar — pero ninguno existe** | **CONFIRMADO — defecto de completitud** | **P1**                          | `git ls-files`/`ls scripts/` → los 2 scripts NO están (solo `gen-canonicalization-vectors.py`, `gen-example-trust-certificate.py`, `install-dev.sh`, `setup-branch-protection.sh`). Placeholders en `sebas-…-final.md:68` y `:138`; `:131` "queda en el repo" es falso. **La ciencia se sostiene** (reproduce); lo ausente es el artefacto al que apunta al "siguiente ratificador" + el bloque de evidencia de digest. |
| C5  | Mutar `metodos` de ieee30 (→re-estampar 2 digests)                                                                                                                         | **ACATADO-dueño** (coherente)           | P1 (identidad, la cierra Sebas) | Es SU identidad de ancla → se acata. No viola `invariants.md` (cero menciones de metodos/digest) ni base lógica (D9 `¬model(α)`: la enum exhaustiva es no-modelo, ancla válida). §15.3 **pre-autoriza** `["cpsat","bruteforce_vectorized"]`+re-estampa; su aviso honra "se reporta, no se sobreescribe".                                                                                                                |
| C6  | **Drift persistente: §15.3 dice "enum integrada al script §1.9" pero §1.9 tiene `FUERZA_BRUTA_MAX_N=14` (no enumera n=30)**                                                | **CONFIRMADO** (letra-vs-realidad)      | P1 (ligado a C5)                | El enumerador vectorizado vive solo en el script ad-hoc de Sebas (y el mío), no en el repo — drift letra-vs-realidad aún vigente. `metodos` de ieee30 en el corpus congelado hoy = `["cpsat"]`.                                                                                                                                                                                                                         |
| C7  | Procedencia de versiones floja en la FINAL                                                                                                                                 | **MATIZADO**                            | P2                              | Cita numpy 2.5.0 (islanding §1.7) / 2.4.4 (sus corridas) vs lock 2.4.6; pandapower 3.3.3 vs 3.5.4. Los digests sobreviven (holgura de redondeo ≥0.009), pero "combo verificado numpy 2.4.4" no es el del lock. Conclusión intacta, provenance suelto.                                                                                                                                                                   |

**Decisión.** La ciencia de Sebas **gana** donde toca (receta ejecutable, óptimos, vector) — todo por
corrida. Sus **decisiones de dueño se acatan** (C5). Lo que queda es completitud/letra: C4 (artefactos
ausentes) y C6 (drift §15.3↔§1.9) **se marcan para Sebas/Dylan** — el re-estampado real está
**bloqueado** hasta que Sebas dé los nuevos digests e integre el enumerador y cierre @v1/@v2 (§7).

### 3.B · Ejecución (Steven) + cambios de código aplicados — _pasada (a) + (b) refutación con violación forzada_

| #   | Hallazgo                                                                                  | Veredicto                            | Prioridad                       | Evidencia primaria                                                                                                                                                                                                                                                                                                                                                               |
| --- | ----------------------------------------------------------------------------------------- | ------------------------------------ | ------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| X1  | AX3 endurecido (`0f74343`) == acción derivada #1 de Steven, y **el gate la caza en vivo** | **CONFIRMADO**                       | — (aplicado)                    | `pyproject.toml` AX3 `forbidden_modules += litellm/openai/anthropic`; `lint-imports` = **9 kept, 0 broken**. Refutación forzó copia temporal `blite/serving/_probe.py` con `import litellm` → **AX3 BROKEN** (`blite.serving._probe -> litellm`). No depende ya solo de la detección transitiva vía httpx.                                                                       |
| X2  | Deps del walking skeleton + `numeric[full]` floors resuelven los hallazgos de Sebas       | **CONFIRMADO**                       | — (aplicado)                    | `engine/pyproject.toml` agrega los 9 (fastapi/uvicorn/psycopg/procrastinate/litellm/ortools/pandapower≥3.5.4/cvxpy/pyjwt); `numeric[full]` baja floors a `numpy≥1.26`/`pandas≥2.3`. Lock: pandapower 3.5.4, **pandas 2.3.3 (<3 ✓)**, **numpy 2.4.6 (<2.5 ✓)** — el combo roto (3.1.2+pandas 3.x) no está en el lock.                                                             |
| X3  | Floor de `capabilities/sim` sigue en `pandapower>=2.13` (sin endurecer)                   | **MATIZADO**                         | **P2** (defensa en profundidad) | En el lock del workspace domina `engine>=3.5.4` (seguro). Refutación: standalone `sim[pandapower]` **solo** resuelve la 3.5.4 más nueva (que topa pandas<3) → regresa **solo** si un co-constraint externo `pandas>=3` hace backtrack de pandapower. Gap **condicional**, no rotura en vivo.                                                                                     |
| X4  | **El fix utf-8 (`a1cd49e`) está INCOMPLETO**                                              | **MATIZADO**                         | **P2**                          | Solo parcha `tests/invariants/test_enforced_anchors.py`. Refutación: ~11 `read_text()` hermanos sin `encoding` siguen, incl. `test_verification_policy.py:37/46/58/85` que lee `verification-default.yaml` (no-ASCII en línea 1) → **misma clase de crash cp1252 en Windows** abierta en otro módulo. Es spot-patch, no el cierre sistémico que sugiere el hallazgo #3 de Sebas. |
| X5  | Acciones #2 (Registry real) / #3 (Pipeline/Stage) + tests semilla = S-G, no aplicadas     | **CONFIRMADO** (diferidas, no rotas) | S-G                             | `runtime/registry.py` sigue stub (`load_capabilities()->dict`, sin `.list()/.get()`/eventos); no hay clase `Pipeline`/`Stage`; sin tests semilla nuevos. Punto de partida esperado.                                                                                                                                                                                              |

**Decisión.** Steven **ratifica sin objeción**; su único pedido accionable (AX3 obligatorio) **ya está
aplicado y verificado en vivo**. Los cambios de código de los dueños son **correctos**. Se abren dos
**P2** de endurecimiento (X3 floor sim; X4 utf-8 incompleto) como sobrevivientes candidatos de Fase B.

### 3.C · Infra (Geovanni) — _pasada (a) + (b) refutación con contexto fresco_

| #   | Hallazgo                                                                     | Veredicto                                | Prioridad            | Evidencia primaria                                                                                                                                                                                                                                                                                                                                                                                                                 |
| --- | ---------------------------------------------------------------------------- | ---------------------------------------- | -------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| G1  | Ítem-4: modelo local → **Ollama Cloud passthrough** (OLLAMA_API_KEY, egress) | **ACATADO-dueño** (invariantes intactos) | P1 (su plano)        | Es SU plano → se acata. `ModelPort`/`ModelServer` se mantiene ⇒ modelo **mediado** (AX3 `invariants.md:39` holds sin importar dónde corre); egreso lo gobierna authz (INV-6 `:98`). `OLLAMA_API_KEY` por escalón-1 de custodia (§7 / freeze:101). `replay` sigue siendo la config del día D → autonomía D19 preservada.                                                                                                            |
| G2  | **Coherencia: "la soberanía es Fase 2" (geovanni:58) es un desliz de letra** | **MATIZADO**                             | P2                   | `base-logica-formal.md` define soberanía como **lógica siempre-activa** (custodia∧control∧autonomía), no diferible. Lo Fase 2 es el **recinto air-gapped** (freeze §15.8:232, dueño Geovanni) + perfil `redacted` (§15.1:179), NO la soberanía. Sustancia OK (el cloud solo ve ieee14 sintético/público). **Reformular** al acatar: "el recinto offline es Fase 2; la soberanía-lógica sigue activa (no egresa dato de red real)". |
| G3  | Los 5 ítems `[COMPLETÁ VOS]` siguen **abiertos** (el dueño no los cerró)     | **CONFIRMADO — marcar, no cerrar**       | P1/P2 (Dylan/equipo) | `geovanni:17/27/40/67/73/82`. Solo ítem-4 está decidido. No los cierra el auditor.                                                                                                                                                                                                                                                                                                                                                 |
| G4  | Ítem-6: reconciliación infra/01 §R vs `invariants.md` (ejecutable)           | **EJECUTADO → limpio**                   | —                    | Ver §5. Ningún punto de §R toca un invariante del engine.                                                                                                                                                                                                                                                                                                                                                                          |
| G5  | LiteLLM-drop = **decisión cruzada** (Steven+Dylan), no unilateral            | **CONFIRMADO → RESUELTA**                | se mantiene          | `geovanni:90-95` lo dice explícito; freeze §15.7 (`:220-225`) es dueño de la decisión LiteLLM (frontera, ratif. Steven+Dylan). Escalarlo como supersesión con causa = correcto.                                                                                                                                                                                                                                                    |

**Decisión.** La objeción de dueño (Ollama Cloud) **se acata**; solo se corrige el **encuadre** (G2:
soberanía-lógica no es diferible). Los 5 `[COMPLETÁ VOS]` **se marcan** (§7); el LiteLLM-drop quedó **resuelto** (se mantiene, aval Steven); nada se
cierra por el auditor.

---

## 4 · Evidencia por corrida (Fase A, `uv run --frozen`, repo limpio)

| Verificación                                                 | Resultado                                                                                                    |
| ------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------ |
| Corpus §1.9 regenerado (receta oficial del workspace)        | **6/6 digests** frozen==committed==embedded==regenerado; márgenes 0.0298/0.0322/0.0090                       |
| ieee30 segunda ancla (enum exhaustiva 2²⁹, x₀=0, sin CP-SAT) | uniforme **35** / flujo **32170** == congelado (536 870 912 asignaciones/convención)                         |
| Falla sembrada — flips ieee14                                | flujo prohibidos **[7]**, bus 1→32597 (gap 24473, 42.9%); uniforme prohibidos **[0,1,11]**, bus 8→12 (gap 4) |
| `lint-imports` (AX3 etc.)                                    | **9 kept, 0 broken** (+ violación forzada de AX3 detectada en vivo)                                          |
| Marca "Blite"+"Engine" juntas                                | **0 hits** repo-wide                                                                                         |
| `ruff check .`                                               | All checks passed                                                                                            |
| `pytest tests/ -q`                                           | **101 passed**, 1 xpassed (cobertura 92%)                                                                    |
| `tsc --noEmit -p apps/studio`                                | exit 0 (sin errores de tipo)                                                                                 |

---

## 5 · Reconciliación infra/01 §R vs `docs/invariants.md` (ítem-6 de Geovanni — ejecutada)

§R (`knowledge/infra/01-provisionar-aislar-operar.md:232-241`) tiene **4 puntos**; contrastados contra
los 16 invariantes de la constitución (`docs/invariants.md`):

| Punto §R                                                                                           | Naturaleza                          | ¿Toca algún invariante?                                                                                                    |
| -------------------------------------------------------------------------------------------------- | ----------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| 1 · Drift de stack NestJS/BullMQ → FastAPI/Python/Postgres (resuelto 2026-07-14)                   | Elección de stack del control plane | **No** — los invariantes gobiernan fronteras de import del engine, no el framework/cola                                    |
| 2 · "Baseline Terraform" externo al repo                                                           | Estado del repo                     | **No** — ningún invariante exige/prohíbe Terraform. **`find *.tf` → vacío** (no existe en el repo; el propio §R lo admite) |
| 3 · Entregables de demo faltantes (Dockerfiles, compose, ECR/Fargate, **sin-GPU Fargate**, fechas) | Cobertura del plan                  | **No** — "sin GPU" es restricción de hardware/deploy, NO el borde `ModelPort` (AX3/§15.7)                                  |
| 4 · workspaces/tenants/control plane administrado = Fase 2                                         | Alcance temporal                    | **No** — multi-tenancy es Fase 2 (consistente con §7 del doc y freeze §15.8)                                               |

**Resultado:** **ninguno de los 4 puntos contradice un invariante del engine** — confirma el
hallazgo de S-E ("cerró el freeze sin hallar contradicción"). El **residual** es la pregunta fáctica
"¿existe el baseline Terraform externo?" — que **solo Geovanni-real puede confirmar**. La reconciliación queda **limpia contra invariants.md**.

---

## 6 · Lista consolidada priorizada

### P0 — nada nuevo

El riesgo de que la receta del corpus no corriera con el `uv.lock` **ya está resuelto** por
`0f74343` — verificado por corrida (6/6). No aparecieron P0 nuevos en las ratificaciones reales.

### P1 — cerrar en la ventana

1. **(C4) Completitud de la FINAL de Sebas:** commitear `scripts/verify_corpus_digests.py` (y/o
   `gen_corpus_islanding.py`) o quitar las referencias colgantes; llenar los 2 placeholders con la
   salida real. **Marca para Sebas/Dylan** (no se re-litiga la ciencia).
2. **(C5+C6) Re-estampado de ieee30 + integración del enumerador a §1.9:** **acatado** como decisión
   de Sebas; **bloqueado** hasta que él dé los nuevos digests (`metodos` cambia) y cierre @v1/@v2 vs
   attestation externa. Hoy §15.3 dice "integrada al script §1.9" y §1.9 no la tiene (drift vigente).
3. **(C3) Vector de falla sembrada** = seed de test de S-G con su vector congelado (bus 1 flujo).
4. **(G1) Ollama Cloud** = supersesión con causa en §15.7/infra (acatada; ver §8).
5. **(G3) 5 `[COMPLETÁ VOS]` de Geovanni** = escalación a Dylan/equipo (custodia, demo dual,
   calendario, Fase 2).

### P2 — registrar / endurecer

- **(X3)** Endurecer floor `capabilities/sim`: `pandapower>=2.13 → >=3.5.4` (igual que el pin del engine; defensa en profundidad).
- **(X4)** Completar el fix utf-8: `encoding="utf-8"` en `test_verification_policy.py` y hermanos.
- **(G2)** Reformular "soberanía=Fase 2" → "recinto air-gapped=Fase 2".
- **(C7)** Corregir la procedencia de versiones en la FINAL (numpy 2.4.6 del lock, no 2.4.4).
- **(1.5/1.6 Sebas)** Estampar semántica de comparación del corpus + `seeds.sampler:"unsupported"`.

---

## 7 · Lo que queda MARCADO (no cerrado por el auditor)

- **Decisión de dueño — acatada, cierre fino pendiente del dueño:** identidad @v1/@v2 (o attestation
  externa sobre el mismo digest) de ieee30 (Sebas); modelo puntual del demo y su tag (Geovanni).
- **Decisión CRUZADA (Steven + Dylan) — RESUELTA (2026-07-21):** con el requisito de Dylan
  (**multi-proveedor + delegación de tareas por modelo**, p. ej. Anthropic + Ollama) la propuesta de
  dropear LiteLLM se **declina** — **se mantiene LiteLLM** (Steven dio aval). "Ollama Cloud" (ítem-4
  de Geovanni) queda como **una entrada del `model_list`**, no como razón para eliminar el router.
  Guardrails: el ruteo por tarea a cloud respeta §15.1 (default-deny de datos de red reales, gobernado
  por Policy) y el LLM nunca entra a la verificación (INV-2); el día D corre `replay`. Nota: LiteLLM
  vive en `ModelServer` (`blite.protocols`), no en `serving` — el endurecimiento de AX3 (prohíbe
  `litellm`/`openai`/`anthropic` en `serving`) es compatible con el uso multi-proveedor.
- **`[COMPLETÁ VOS]` de Geovanni (Dylan/equipo):** custodia de llaves §7 · demo dual §3 · calendario
  de dry-runs §5 · huecos Fase 2 §15.8 · (ítem-6 ya ejecutado, §5).
- **Trabajo, no ratificación (Sebas):** cr8/cr6 (CORE del demo en vivo) — corredor + definición de peso.
- **Integración de KB (próxima sesión):** `kb2-05-plataforma-quantinuum-h2.md` a fusionar con
  `quantum/08` — no es documento de ratificación.

---

## 8 · Fase B — APLICADO (2026-07-21)

Como **supersesión `[S-F-real]` fechada con causa** (jamás edición silenciosa / marca retroactiva),
con su bloque **"Registro de cierre (S-F-real)"**:

> **APLICADO** en 5 commits temáticos (rama `ratificacion/consolidacion-sf`, **sin push**), gates
> verdes por corrida (import-linter **10/10**, pytest **101**, ruff, `tsc` 0, marca 0):
> `0a8a4cb` contrato AX3-b · `cf6aa54` utf-8 · `d6fa811` higiene de secretos · `26c27e3` supersesión
> freeze §15.7/§15.3 + Registro de cierre + addendum infra/03 · `b290aea` floor `sim`.
> `0f74343`/`a1cd49e` quedan **ratificados sin re-aplicar** (ya en la rama, verificados).
> **NO aplicado a propósito:** re-estampado de ieee30 (identidad de Sebas), flip del `xfail` de AX1
> (decisión de Dylan, §9), bugs del compose y los 4 `[COMPLETÁ VOS]` (Geovanni), plano de confianza en
> código (S-G, §9).

1. **Ratificar los cambios de código ya aplicados** (`0f74343`, `a1cd49e`) — registrar causa por
   cada uno; gates verdes ya verificados. _(No se re-aplica nada; se documenta.)_
2. **§15.7 / model-router (G1, acatada):** nota de supersesión — modelo del demo = Ollama Cloud
   passthrough + `OLLAMA_API_KEY` (egress on; **recinto air-gapped = Fase 2**, no "soberanía");
   `ModelPort`/`ModelServer` + `replay` intactos. **LiteLLM se mantiene** (aval Steven + requisito
   multi-proveedor de Dylan); "Ollama Cloud" = una entrada del `model_list`. Causa: ratificación real
   Geovanni ítem-4 + decisión cruzada resuelta 2026-07-21.
3. **§15.3 / islanding (C5+C6, acatada, PARCIAL):** registrar la corrida de la segunda ancla
   (35/32170) y que `metodos`→`["cpsat","bruteforce_vectorized"]` **queda pendiente de re-estampar**
   (digests nuevos + @v1/@v2) por Sebas. **No re-estampar automáticamente.**
4. **P2 de endurecimiento (bajo riesgo):** X3 (floor `sim` `>=3.5.4`) + X4 (utf-8 en
   `test_verification_policy.py` y hermanos) — con test/gate verde por corrida.
5. **Registro de cierre (S-F-real)** con la causa por cambio + la lista de lo **marcado/cruzado** (§7).

**Verificación de Fase B (antes de cada commit):** `uv sync --all-packages --extra pandapower --extra
ortools --extra networkx` · `uv run lint-imports` · `uv run pytest tests/ -q` · `ruff` · `tsc` · hook
de la marca (0 hits). Commits temáticos con causa.

---

## 9 · Stress test brutal pre-B — veredicto **GO condicional**

Panel de **5 atacantes en postura de destrucción** (contexto fresco, independiente de la simulación)
sobre el diseño real + los cambios de ratificación. **El diseño sobrevivió; ninguna decisión
congelada quedó invalidada.**

- **Aguantó el ataque (robustez):** inyección→egress **cerrada** (AX3 + Inv-E + egress solo acepta
  `AuthzDecision`, nunca `Signal`); canonicalización DSSE/Ed25519 rigurosa; INV-2 estructural; **falla
  sembrada a prueba de drift** (el re-estampado no toca ieee14-flujo); **flip público limpio de
  licencias** (0 copyleft; ECOS-GPL ausente, clarabel/scs/osqp); import-linter 10/10; `replay`
  cableado como backend del día D (la demo **no** necesita el cloud en vivo).
- **Corregido/aplicado en Fase B:** hueco de import del SDK de modelo fuera de `serving` (**AX3-b**);
  contradicción air-gap↔Ollama Cloud (reconciliada en infra/03); higiene de secretos; floor `sim`;
  utf-8 (recalibrado: fragilidad **latente**, no crash activo — verificado empíricamente).
- **Riesgo dominante → S-G (no lo causan las ratificaciones):** el **plano de confianza vive
  pre-freeze en código** — vocabulario `rung` muerto (engine/Studio/`policy.py`/
  `verification-default.yaml`), **forja de `pass` sin ancla** (`anchor_digest` nullable, sin CHECK
  `verdict=pass ⇒ ancla`), `scripts/verify-bundle.py`/`api`/compose **inexistentes** (el runtime del
  día D no existe aún; dry-run 1 el 27-jul es la 1ª integración). **Es el diferenciador indefenso en
  código — prioridad #1 de S-G.**
- **Decisión abierta para Dylan:** flip del `xfail` de AX1 — `actor_id` ya es obligatorio (xpassa),
  pero `invariants.md:143` condiciona el flip a que el gateway estampe identidad, que aún no existe.

**Re-test sobre la versión final (HEAD aplicado, 2026-07-21):** panel completo re-corrido → **GO, cero regresión**; los 5 ejes AGUANTARON y el plano de confianza quedó byte-idéntico. Mejoras aplicadas por el re-stress: AX3-b y AX3 alineados a INV-2 (`cohere`/`transformers`); pointers de supersesión en las líneas obsoletas de `freeze:200` / `islanding/01` / `infra/03`. `xfail` de AX1 dejado como está (recomendación).

---

> **Siguiente (NO es parte de este flujo):** comparación simulada↔real y convergencia (§5 del
> protocolo) — recién cuando Fase B cierre sobre la ratificación real. Pendiente ofrecido: **re-correr
> el panel de destrucción sobre esta versión final aplicada.**
