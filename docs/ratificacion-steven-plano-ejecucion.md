# Ratificación del plano de ejecución — Steven

> **Estado: RATIFICADO (2026-07-19).** Respuesta al checklist de `guia-ratificacion.md` §4
> (~75 min de revisión, sección Steven). Cubre `contract-freeze.md` §1/§2/§3/§8/§13/§15.7 y las
> notas `knowledge/execution/01–09` contra su forma final en el freeze. Formato: veredicto por
> ítem + evidencia (nota/sección) + objeciones si las hay + acciones derivadas para S-G.
> **Resultado: ratifico las 8 secciones del checklist SIN objeciones bloqueantes.** Hay 3
> acciones derivadas (no objeciones — refuerzos de bajo costo) y 1 gap de código esperado
> (pre-construcción) documentado al final para que los seeds lo tomen como punto de partida.

---

## 1 · Manifest v2 (§1) — sin `protocol`, con `interaction`/`execution_profile`

**Veredicto: ✅ OK.** Coincide exactamente con `execution/06` §11: `execution_profile` default
`in-process`, sobreescribible por `DistributionManifest`; `remote-job` retorna `JobRef` (jamás
`Result` síncrono, cierra el modo de falla central de `execution/06` §6 — tratar un job remoto
como si fuera síncrono); perfil no soportado ⇒ `NotImplementedError` explícito, nunca fallback
silencioso a `in-process` (`execution/06` §11, decisión ya tomada por mí en la nota original).
Nada que objetar — el freeze no se desvió de mi investigación en este punto.

## 2 · Las 8 etapas y disolución de la etapa `policy`

**Veredicto: ✅ OK — es el cambio correcto sobre mi nota 01.** Mi propuesta original (`execution/01`
§1.2) tenía 7 etapas con una "Resolución de VerificationPolicy" como etapa propia, evaluada por
invocación. El freeze la disuelve: la Policy se fija por digest al crear el case (`PolicyPinned`,
R-Pol1) y la etapa de verificación la lee. Estoy de acuerdo con el cambio — evaluar la policy en
cada invocación era redundante si ya se fija una vez por case, y el nuevo orden (`identity →
authorization → guardrails → provenance:pre → mediation → verification → provenance:post →
egress`) generaliza mi etapa "despacho" a `mediation` (cubre capability Y model router bajo el
mismo nombre, coherente con freeze §15.7 "la etapa mediation ejecuta la decisión de
`serving.route()`") y separa explícitamente `provenance:pre`/`provenance:post` como los puntos
donde se escribe el evento ANTES/DESPUÉS de actuar — esto es una mejora sobre mi nota original:
hace el requisito de INV-4 (override registrado antes de ejecutar) una etapa nombrada en vez de
una responsabilidad implícita de "cualquier Stage que haga overrides" (`execution/01` §8.3).
Sin objeción.

## 3 · Reautorización a mitad de pipeline (§8.4) — fail-closed

**Veredicto: ✅ OK.** Cierra la pregunta abierta más señalada de mi nota 01 (§10, tercer punto) de
la forma más simple y más coherente con Inv-E: si el despacho revela un permiso distinto al
evaluado en la etapa 2, es error de contrato — el run falla y se re-invoca completo, nunca
re-evaluación en vuelo. Evita reabrir Inv-E como una decisión mutable a mitad de pipeline. Sin
objeción.

## 4 · Run jerárquico (cambio sobre mi nota 07)

**Veredicto: ✅ OK.** Se confirma mi opción A (`stream_id = run_id`, un stream por run —
`execution/07` §4) — la decisión de mayor prioridad de bloqueo que el `README.md` de la carpeta
marcaba (punto #1 de "Cómo revisar esto con Dylan"), y se agrega `parent_run_id` sin streams
anidados (opciones B/C de mi nota siguen correctamente descartadas). El case/certificado cuelga
SIEMPRE del run raíz (D5); los sub-runs aportan claims. Esto es exactamente la extensión mínima
que mi nota 07 no vio venir pero que no contradice ninguna de mis alternativas descartadas.

**Bonus — cierra un modo de falla que mi nota había dejado abierto sin mitigación:** mi nota 07
§6 (tercer modo de falla) señalaba que un `RunStep` en `RUNNING` cuando el `Run` pasa a
`CANCELLED` quedaba "colgado" sin transición formal. El freeze §3 lo resuelve: "un step en
RUNNING no recibe evento terminal — la proyección lo reporta `interrupted`" (regla de proyección,
no evento nuevo). Confirmo que esto cierra correctamente el hueco — no hace falta un evento
`run.step.interrupted` nuevo, la proyección basta. Sin objeción.

## 5 · Semántica step↔job 1:1, cancelación, `max_steps`

**Veredicto: ✅ OK.** `step↔job 1:1` en Fase 1 resuelve la pregunta abierta de mi nota 02 §10
("¿un RunStep puede disparar más de un capability.job?") con la simplificación correcta para
Fase 1 — paralelismo se modela como varios steps, no como un step con N jobs. `max_steps`
obligatorio a nivel de `Run` es exactamente la mitigación que mi nota 02 §6 pedía para el modo de
falla "loop infinito" (yo la dejé como "mitigación no implementada"; el freeze la vuelve
contrato). Sin objeción.

## 6 · Idempotencia — `side_effects` manda

**Veredicto: ✅ OK — es la regla segura que mi nota 03 recomendaba sin comprometerse al mecanismo
fino.** Mi nota 03 (§1.4, §10) identificó el problema (reintento de un paso `irreversible-external`
sin idempotencia garantizada = riesgo de duplicar un efecto externo real) pero explícitamente no
lo resolvía — lo marcaba como pregunta abierta y recomendaba, en la dirección later (§12),
"escalamiento obligatorio a revisión humana en vez de reintento automático" para el subconjunto
que no puede garantizar idempotencia por diseño. El freeze adopta exactamente esa regla segura:
sin idempotencia garantizada, NO hay reintento automático de pasos external — escala a humano con
override registrado (INV-4). El mecanismo fino queda declarado como mi diseño en S-G (freeze
§15.8) — correcto, es analizable con datos reales del walking skeleton, no antes. Sin objeción.

## 7 · Model router — `ModelPort`/`ModelServer`

**Veredicto: ✅ OK — ratificación conjunta con Dylan ya cerrada, confirmo mi mitad.** `ModelPort`
(Protocol) en `serving` (cero red, AX3 por construcción) + `ModelServer` (adapter) en `protocols`
bajo INV-6, envolviendo LiteLLM `Router` (un solo `model_list`: cloud + Ollama) + backend
`replay` como config de primera clase — es la propuesta de `execution/09`, verificada en vivo
contra el gate `AX3` real de `pyproject.toml` (incluida la cadena transitiva `litellm → httpx`) y
contra las licencias (LiteLLM MIT con carve-out `enterprise/`, Ollama MIT). Los eventos
`model.call.requested/completed` con digests cierran la pregunta abierta que mi nota 09 §4.5
dejaba sin resolver (¿rastro propio o parte del step?) — el freeze eligió rastro propio,
consistente con el precedente AGT (`pre_model_call`/`post_model_call`) que mi propia nota 08
verificó en vivo. Sin objeción.

**Acción derivada (no objeción — refuerzo de bajo costo, ya sugerido por mí en `execution/09`
§4.2):** el freeze §15.7 deja el endurecimiento de `AX3` (agregar `litellm`/`openai`/`anthropic`
explícitamente a `forbidden_modules`) como "tarea de S-G" opcional. Recomiendo NO tratarlo como
opcional sino incluirlo en el primer PR de S-G: hoy `AX3` bloquea `litellm` solo por detección
transitiva vía `httpx` (`include_external_packages = true`); es una protección real pero más
frágil que una entrada explícita — si la cadena interna de imports de LiteLLM cambiara alguna vez
antes de tocar `httpx`, el gate dejaría de detectarlo silenciosamente. Es una línea de config, cero
riesgo, cierra un gap real. Pido que quede en la lista de seeds de S-G como ítem concreto, no como
"si sobra tiempo".

## 8 · Registry — descubrimiento tolerante a fallos

**Veredicto: ✅ OK.** `Registry(Protocol).list() -> tuple[CapabilityManifest, ...] / get(capability_id)
-> Capability`; descubrimiento tolerante a fallos con excepción capturada POR entry point (nunca
un único try/except global); eventos `registry.loaded {capability_ids[], failed[]}` /
`registry.capability_load_failed {entry_point, error_kind}` con `actor_id = "service:runtime"`;
"deshabilitada intencionalmente" ≠ "falló al cargar" (lo primero es ausencia en el
`DistributionManifest`, lo segundo va en `failed`); versiones duplicadas resueltas por pin del
`DistributionManifest` con default determinista (nunca `latest`). Todo esto es exactamente lo que
`execution/04` propuso, motivado por el caso real observado en esta misma sesión de setup (pyscf/VQE
sin BLAS en Windows) — incluida la distinción "deshabilitada vs fallida" que mi nota 04 §6 dejaba
como riesgo de diagnóstico sin resolver, y la política de versionado que `execution/08` tomó
prestada de Composio (pin por despliegue, default determinista) para cerrar mi pregunta abierta de
§10. Sin objeción.

## Puntos de equipo que también reviso (no exclusivos de mi plano, pero tocan mi mecánica)

- **Walking skeleton (48h post-freeze, dueño Steven, freeze §15.4):** pendiente — es mi entregable
  de arranque de construcción, no una decisión a ratificar. Lo tomo como próximo paso inmediato
  tras el cierre de esta ratificación.
- **PR único con todas las deps (freeze §15.4/P2-4):** de acuerdo — evita que la cuarentena npm de
  14 días bloquee la semana de integración.

---

## Resumen: qué cierro que mis propias notas habían dejado abierto

Para que quede trazado (no solo "ratifico", sino "verifiqué que se cerró bien"):

| Pregunta abierta en mi nota original                                             | Dónde se cerró                | Conforme |
| ---------------------------------------------------------------------------------- | ------------------------------ | -------- |
| `execution/07` §10 — ¿un único `stream_id` por run?                              | freeze §2/§13                  | ✅       |
| `execution/07` §6 — `RunStep` colgado en `RUNNING` al cancelar el `Run`          | freeze §3                      | ✅       |
| `execution/02` §10 — ¿`RunStep` puede disparar >1 `capability.job`?              | freeze §3 (1:1 en Fase 1)      | ✅       |
| `execution/02` §6 — loop infinito sin límite                                     | freeze §3 (`max_steps` obligatorio) | ✅  |
| `execution/03` §10 — mecanismo de idempotencia para pasos external               | freeze §13 (regla segura; mecanismo fino = mi diseño en S-G) | ✅ (parcial, a propósito) |
| `execution/04` §10 — ¿evento `registry.loaded`? ¿distingue deshabilitada/fallida? | freeze §1                       | ✅       |
| `execution/04` §10/§6 — versión duplicada de un `id`                             | freeze §1 (pin por `DistributionManifest`) | ✅ |
| `execution/09` §4.5 — ¿la llamada a modelo emite evento propio?                  | freeze §3 (`model.call.*` propio) | ✅     |
| `execution/01` §8.4 — reautorización a mitad de pipeline                         | freeze §8 (fail-closed)         | ✅       |

Ninguna pregunta abierta de mis 9 notas quedó sin resolver o sin dueño declarado tras el freeze.

## Acciones derivadas para la fase de seeds (S-G) — para que Dylan las convierta en specs/tests

1. **Endurecer `AX3` explícitamente** (agregar `litellm`, `openai`, `anthropic` a
   `forbidden_modules` de `blite.serving`) — incluirlo en el PR único de S-G, no como opcional
   (ver §7 arriba).
2. **Registry real**: implementar `Registry.list()/get()` sobre `importlib.metadata` con captura
   de excepción por entry point (no global), exponiendo el manifest completo (4 campos v2), más
   los eventos `registry.loaded`/`registry.capability_load_failed`. El código actual
   (`engine/src/blite/runtime/registry.py`) es un stub previo al freeze — expone
   `load_capabilities() -> dict[str, Capability]`, sin tolerancia a fallos por entry point, sin
   `.list()`/`.get()`, sin eventos. Es el punto de partida esperado, no una regresión — lo
   reemplazo yo en S-G contra el contrato de arriba.
3. **Pipeline como `Pipeline`/`Stage` explícito in-process** (nunca `BaseHTTPMiddleware`, nunca
   middleware para las 8 etapas — `execution/08` §1.2, verificado en vivo contra docs de
   Starlette/FastAPI): las 8 etapas viven en un pipeline invocado por el endpoint del gateway;
   solo transversales de transporte (request-id, CORS) van como middleware ASGI puro.
4. Tests semilla directamente derivables de mis notas (para que Dylan los use como base, no como
   lista final — el diseño fino es mío en S-G):
   - Test de orden de las 8 etapas como tupla única (`execution/01` §9).
   - Test de "un `Rejection` corta la cadena" — la etapa de egreso nunca se alcanza si `authz`
     rechazó (`execution/01` §9).
   - Test de descubrimiento tolerante a fallos del registry, usando el caso real pyscf/VQE sin
     `vqe` instalado como fixture (`execution/04` §9/§11 — ya lo tenemos reproducible en este
     entorno).
   - Test de `Dispatcher.resolve("service"|"remote-job")` fallando explícito
     (`NotImplementedError`), nunca fallback silencioso a `in-process` (`execution/06` §9).
   - Test de que un `RunStep` con `execution_profile: remote-job` recibe `JobRef`, nunca `Result`
     síncrono (`execution/06` §9).
   - Test de reconstrucción de `RunState` por replay + idempotencia de la proyección
     (`execution/03` §9).

## Estado del código vs. el contrato (para contexto de arranque, no parte del checklist)

`engine/src/blite/{gateway,runtime,serving,protocols}/__init__.py` son hoy solo docstrings (sin
implementación); `runtime/registry.py` tiene la función stub descrita arriba. Esto es exactamente
lo esperado pre-S-G — el freeze fija la forma, la construcción no había empezado. Lo dejo anotado
para que el punto de partida de las specs/tests de Dylan no asuma código existente que no está.

---

**Firma:** Steven — ratificación final del plano de ejecución, 2026-07-19. Sin objeciones
bloqueantes sobre `contract-freeze.md` §1/§2/§3/§8/§13/§15.7. Listo para que se generen los seeds
(`docs/specs/`, tests semilla, `challenge1/reproduce.py`, fixture de falla sembrada,
`scripts/verify-bundle.py`) y para arrancar el walking skeleton de 48h.
