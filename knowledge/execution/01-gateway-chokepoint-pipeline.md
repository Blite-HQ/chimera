# Nota 01 — El gateway como chokepoint único: forma del pipeline de etapas

**Ítem del plan:** plano de ejecución (Steven) — dar forma de dato al pipeline detrás de `blite.gateway`
que hoy INV-1 exige como chokepoint único, sin todavía tener una implementación.
**Fecha:** 2026-07-10 · **Estado:** incorporada al freeze (S-E 2026-07-18), con dos ajustes de la convergencia (C2): (1) el orden de §1.2 quedó superado por las **8 etapas congeladas** — `identity → authorization → guardrails → provenance:pre → mediation → verification → provenance:post → egress` (freeze §8); (2) la etapa 4 "Resolución de VerificationPolicy" **se disuelve** — la Policy se fija por digest al crear el case (`PolicyPinned`, R-Pol1) y la etapa de verificación la LEE, no es una etapa por invocación. La pregunta §8.4 (reautorización a mitad de pipeline) quedó cerrada en el freeze §8: fail-closed, jamás re-evaluación en vuelo. Lo demás (Pipeline explícito in-process, fail-closed, firma de egreso que no acepta señales, INV-4 por Stage) entró tal cual. **Implementado en el MVP Nivel-1 (2026-07-24):** `engine/src/blite/gateway/pipeline.py` (`STAGE_ORDER` de 8 etapas, fail-closed en construcción y ejecución, `PassthroughStage`) + `stages.py` (mediation/egress reales).
**Fuentes:** `docs/invariants.md` (INV-1, AX3, Inv-E, INV-6, INV-3, INV-2) ·
`engine/src/blite/gateway/__init__.py` (vacío hoy) · patrón general de middleware chain /
chain-of-responsibility y de pipelines ASGI-style (referencia conceptual, **no verificado en vivo esta
sesión**) · `knowledge/trust/06-protocolos-capability-mcp-a2a.md` (adapters en el borde, no en el núcleo) ·
`knowledge/execution/07-run-lifecycle-events.md` (vocabulario de eventos que cada etapa podría emitir)

---

## 1 · Patrón / mecanismo

### 1.1 El gateway como composición de etapas ordenadas, no un monolito

INV-1 exige que toda invocación de capability, llamada a modelo y protocolo de egreso pase por `gateway` —
pero no dice cómo se compone internamente. El patrón genérico de referencia es una cadena de etapas
ordenadas (chain-of-responsibility / middleware chain, presente en casi cualquier framework HTTP con
middlewares apilados — ej. la forma conceptual de un stack ASGI, donde cada capa envuelve a la siguiente)
donde cada etapa puede: leer el contexto, mutarlo, cortar la cadena (rechazar), o dejar pasar al
siguiente. Esto es una **referencia de patrón**, no una librería a integrar — el mecanismo en sí (una lista
ordenada de funciones/objetos que se aplican en secuencia) no tiene dependencia de código.

### 1.2 Las 7 etapas, en detalle — qué puede y qué NO puede hacer cada una

El orden no es arbitrario — cada invariante fija una restricción de precedencia. Para cada etapa se
especifica: entrada, salida, lo que le está PERMITIDO hacer, y lo que le está PROHIBIDO hacer (la
prohibición es la parte que hace el diseño auditable, no solo el flujo feliz).

1. **Identidad** — resuelve quién hace la solicitud (consume el contrato `Identity` de
   `knowledge/trust/08`, aún no implementado del lado de Dylan).
   - _Puede:_ leer credenciales/token de la solicitud entrante, producir un `Identity` resuelto.
   - _NO puede:_ decidir permisos (eso es la siguiente etapa) ni rechazar por razones de política —
     solo puede rechazar si la identidad en sí es inválida (token expirado, firma inválida).
2. **Authz** — ¿esta identidad tiene permiso para esta operación? (INV-6: solo `authz` autoriza egreso;
   Inv-E: ninguna otra propiedad satisface el antecedente de un egreso).
   - _Puede:_ consultar `required_permission` del `CapabilityManifest` (trust/06 §4) contra los
     `permissions` de la `Identity`; producir una decisión de authz que las etapas posteriores solo
     pueden LEER, nunca sobreescribir.
   - _NO puede:_ ir después de guardrails/verification en el orden — si eso ocurriera, Inv-E ya no sería
     estructural.
3. **Guardrails (pre)** — validaciones de política que NO son autorización (INV-3: guardrails no decide
   egreso, no importa `authz`/`protocols`).
   - _Puede:_ producir `Signal`s no-decisionales (antes `GuardrailSignal`s, trust/04; la numeración
     «rung 5/6» desapareció con la escalera — freeze §5) que informen consenso/detección; rechazar
     una solicitud por política de contenido/forma, ANTES de gastar el costo de despachar.
   - _NO puede:_ producir una `Attestation` (eso requiere `AnchorKind`, que guardrails no tiene por
     construcción — trust/03 §1.1) ni tocar la decisión de authz ya tomada.
4. **Resolución de `VerificationPolicy`** — qué exigencia mínima pide este tipo de claim ([S3]: hoy
   la matriz clase×AL×criticidad de la Policy 0.2.0, freeze §6; consume `knowledge/trust/05`),
   calculado ANTES de despachar, no después.
   - _Puede:_ leer `side_effects`/`interaction` del manifest para elegir la política aplicable.
   - _NO puede:_ ejecutar la verificación misma (eso es la etapa 6) — solo decide QUÉ exigencia aplica.
5. **Despacho a capability** (vía Registry — nota 04) — `blite.runtime` ejecuta.
   - _Puede:_ invocar `Registry.get(capability_id)` y ejecutar según `execution_profile` (nota 06).
   - _NO puede:_ saltarse la etapa de authz si el despacho revela que se necesita un permiso distinto al
     ya evaluado (ej. una capability que internamente requiere un segundo permiso) — este caso es una
     pregunta abierta, no un caso resuelto (§8).
6. **Verificación** — corre el `Verifier` correspondiente (INV-2: nunca un modelo).
   - _Puede:_ producir una `Attestation` tri-estado (`pass|fail|inconclusive`, trust/03 §1.4).
   - _NO puede:_ decidir egreso — un verdict `pass` no es, por sí mismo, autorización de egreso (Inv-E).
7. **Egreso** — solo si `authz` (paso 2, ya evaluado) lo permitió.
   - _Puede:_ leer la decisión de authz cacheada del paso 2 y el resultado (con o sin `Attestation`) del
     paso 6, y decidir cómo etiquetar la salida (verificado / no anclado / bloqueado).
   - _NO puede:_ aceptar un verdict de verificación como sustituto de una decisión de authz ausente — si
     authz nunca autorizó, el resultado se marca no exportable, sin importar el verdict.

### 1.3 Por qué el orden es estructural, no solo convención

Poner `authz` antes que `verification`/`guardrails` (y no al revés) es lo que hace que Inv-E sea
**imposible de violar por construcción** dentro del pipeline: si la etapa de egreso solo puede consultar
la decisión ya tomada por `authz` en el paso 2, no hay forma de que un resultado de verificación
"fabrique" una autorización — el pipeline nunca le da esa entrada a la etapa de egreso. Esto es
precisamente el argumento que `docs/invariants.md` da para Inv-E como defensa estructural contra prompt
injection: ninguna instrucción embebida en contexto de modelo puede forzar egreso fabricando una
"verificación", porque el egreso ni siquiera SABE leer verdicts de verificación como entrada de decisión.

## 2 · Alternativas consideradas

- **(A) Pipeline de etapas fijas y ordenadas (propuesta de esta nota).** Una tupla estática de `Stage`,
  mismo orden para toda invocación.
- **(B) Grafo de etapas configurable por capability.** Cada capability declara qué etapas necesita y en
  qué orden (más flexible, análogo a middlewares por-ruta en frameworks HTTP).
- **(C) Gateway como proxy de red separado** (ej. forma conceptual de un API gateway tipo Kong/Envoy,
  delante del proceso Python, no dentro de él).
- **(D) Sin pipeline explícito — cada handler hace sus propias comprobaciones inline.** (el estado
  implícito de hoy: `gateway/__init__.py` está vacío, así que esto es, de hecho, el estado actual por
  omisión.)

## 3 · Por qué no (descartadas)

- **(B) descartada para Fase 1:** permitir que cada capability configure su propio orden de etapas
  reabre exactamente el riesgo que INV-1 quiere cerrar — un orden "flexible" es un orden que puede,
  por error de configuración, poner despacho antes de authz. La ganancia en flexibilidad no compensa el
  riesgo de que una mala configuración se vuelva un bypass silencioso del chokepoint.
- **(C) descartada para Fase 1:** un proxy de red separado agrega infraestructura operativa (otro proceso,
  otro punto de despliegue) sin necesidad demostrada; además complica INV-5 (todo evento pasa por el mismo
  proceso que puede escribir al `EventStore` sin un salto de red adicional). Reevaluable si el motivo es
  escalar horizontalmente el gateway — no es el caso hoy.
- **(D) es el estado actual, y es exactamente el riesgo que esta nota busca cerrar:** sin una forma
  explícita, "todo pasa por gateway" es una aspiración de INV-1 sin mecanismo — cualquier nuevo handler
  puede olvidar una comprobación y nadie lo detecta hasta un incidente o una revisión manual.

## 4 · Decisión

| Referencia                                                                   | Decisión      | Racional                                                                                                              |
| ---------------------------------------------------------------------------- | ------------- | --------------------------------------------------------------------------------------------------------------------- |
| Middleware chain / chain-of-responsibility (patrón general, alternativa A)   | **inspirar**  | Patrón genérico, sin licencia ni dependencia — informa la FORMA (lista ordenada de etapas), no el código              |
| Orden de etapas derivado de INV-1/INV-2/INV-3/Inv-E/INV-6                    | **portar**    | Es nuestro; se deriva directamente de los invariantes ya frozen, no de una referencia externa                         |
| Grafo de etapas configurable por capability (alternativa B)                  | **descartar** | Reabre el riesgo de bypass que INV-1 cierra; ver §3                                                                   |
| Gateway como proxy de red separado (alternativa C)                           | **descartar** | Sin necesidad demostrada en Fase 1; agrega infraestructura sin beneficio claro; ver §3                                |
| Cualquier gateway framework externo (Kong, Envoy, Express middlewares, etc.) | **descartar** | Fuera de alcance de Fase 1 — el gateway es interno al proceso Python, no un proxy de red separado (supuesto, ver §10) |

## 5 · Tradeoffs

| Eje                        | Pipeline fijo (A, propuesto)                         | Grafo configurable (B)                           | Proxy externo (C)                                                              |
| -------------------------- | ---------------------------------------------------- | ------------------------------------------------ | ------------------------------------------------------------------------------ |
| Auditabilidad              | Alta — un solo orden que revisar                     | Baja — orden depende de config por capability    | Media — depende de la config del proxy, fuera del repo                         |
| Riesgo de bypass           | Bajo (estructural)                                   | Alto (config incorrecta = bypass)                | Medio (dos sistemas de config a mantener en sync)                              |
| Flexibilidad               | Baja — toda invocación paga el costo de las 7 etapas | Alta                                             | Alta, pero fuera del control del import-linter                                 |
| Costo operativo            | Ninguno nuevo (mismo proceso)                        | Ninguno nuevo                                    | Un proceso/infraestructura adicional                                           |
| Coherencia con INV-1/Inv-E | Directa — el orden ES el mecanismo                   | Requiere disciplina externa para no violar Inv-E | Requiere que el proxy conozca invariantes que hoy solo el import-linter conoce |

La elección de (A) prioriza auditabilidad y coherencia estructural con Inv-E sobre flexibilidad — a costa
de que TODA invocación paga el costo de las 7 etapas incluso cuando alguna es un no-op para ese caso
(ej. una capability `side_effects: pure` igual pasa por la etapa de resolución de policy).

## 6 · Modos de falla

- **Bypass del gateway.** Un nuevo endpoint o entry point que invoca `runtime`/`serving` directamente sin
  pasar por `Pipeline` — mecánicamente posible hoy porque no existe ningún mecanismo que lo impida a nivel
  de código (solo import-linter, que restringe imports entre paquetes, no fuerza que un handler concreto
  use el pipeline). **Mitigación propuesta (no implementada):** un test de arquitectura que verifique que
  ningún módulo fuera de `blite.gateway` invoque `Registry.get()`/`invoke()` directamente — análogo al
  patrón ya usado por `tests/invariants/test_enforced_anchors.py` para otros invariantes.
- **Authz duplicado o divergente.** Si una etapa posterior (ej. despacho) vuelve a evaluar permisos con su
  propia lógica en vez de leer la decisión ya tomada en la etapa 2, se puede llegar a un estado donde dos
  evaluaciones de authz no coinciden — una superficie de bug de seguridad clásica (TOCTOU-like, aunque no
  es time-of-check/time-of-use en el sentido estricto, es "decisión duplicada, posible divergencia").
  **Mitigación:** el `ctx` que viaja por el pipeline debe cargar la decisión de authz como dato inmutable
  una vez calculada — ninguna etapa posterior debería volver a invocar `authz` por su cuenta.
- **Guardrail confundido con verificación.** Si un desarrollador nuevo asume que un `GuardrailSignal` con
  `flagged: false` es equivalente a una `Attestation` con `verdict: pass`, y usa eso para decidir egreso,
  viola Inv-E en la práctica aunque el código de import-linter no lo detecte (import-linter solo prohíbe
  IMPORTS, no confusión semántica en tiempo de ejecución). **Mitigación:** los dos tipos son disjuntos por
  diseño — `docs/contract-freeze.md` §5 (atribuido a nota 04) describe `GuardrailSignal` como "tipo disjunto
  de `Attestation`, sin conversión posible" — la etapa de egreso debería tener firma de tipos que
  literalmente no acepte un `GuardrailSignal` como argumento de decisión, solo `AuthzDecision`.
- **Egreso fuera del gateway.** Un módulo que hace su propia llamada HTTP de salida sin pasar por la etapa
  7 (ej. un handler de error que reporta a un servicio externo directamente). INV-6 ya lo cubre a nivel de
  import-linter para `blite.protocols`/`blite.authz`, pero un código fuera de esos paquetes que igual
  importe `httpx` directamente no está bloqueado por ningún gate hoy, hasta donde esta nota pudo revisar.

## 7 · Licencias

| Pieza                          | Licencia                | Verificado                                                  |
| ------------------------------ | ----------------------- | ----------------------------------------------------------- |
| Patrón chain-of-responsibility | N/A — patrón, no código | conocimiento general, **no verificado en vivo esta sesión** |

No se propone ninguna dependencia nueva en esta nota.

## 8 · Impacto en contrato

1. Propuesta de forma para `blite.gateway`: un `Stage` (Protocol) con una única operación
   `handle(ctx) -> ctx | Rejection`, y un `Pipeline` que compone una tupla ordenada y fija de `Stage`
   (identidad → authz → guardrails-pre → resolución de policy → despacho → verificación → egreso).
   **Esto es propuesta de diseño, no forma congelada.**
2. El `ctx` que viaja por el pipeline necesita cargar, como mínimo: identidad resuelta, decisión de authz
   (inmutable tras el paso 2 — §6), policy de verificación resuelta, y (tras el despacho) el
   resultado/job_ref — pero el contrato exacto de ese objeto de contexto no se fija aquí (pregunta
   abierta, §10).
3. Cualquier etapa que haga un override de un default (ej. forzar un guardrail) debe emitir su evento
   ANTES de aplicar el override (INV-4) — el `Pipeline` no puede ser el que decide esto por su cuenta; cada
   `Stage` que haga overrides debe emitir el evento él mismo vía el puerto `EventStore` (trust/01).
4. Caso no resuelto del despacho (§1.2, etapa 5): si una capability requiere, en tiempo de invocación, un
   permiso distinto al ya evaluado por la etapa 2, el diseño actual no tiene una vía limpia para
   "reautorizar a mitad de pipeline" — señalado como pregunta abierta, no como decisión.

## 9 · Implicaciones de test / spec

- **Test de arquitectura (análogo a `tests/invariants/test_enforced_anchors.py`):** verificar que ningún
  módulo fuera de `blite.gateway` invoque el despacho de capabilities directamente — cierra el modo de
  falla "bypass del gateway" (§6) con un gate automatizado, no solo disciplina.
- **Test de orden de etapas:** un test unitario que construya un `Pipeline` con etapas de prueba (mocks) y
  verifique que el orden ejecutado sea exactamente el de §1.2 — protege contra una futura refactorización
  que reordene por accidente.
- **Test de inmutabilidad de la decisión de authz:** verificar que ninguna etapa posterior a `authz` pueda
  mutar el campo de decisión en `ctx` — si el lenguaje/tipo lo permite, un test de tipos (pyright, ya en
  modo strict en este repo) puede exigir un tipo inmutable (`frozen=True` en un dataclass, por ejemplo).
- **Test de rechazo temprano:** verificar que un `Rejection` en cualquier etapa corta la cadena — ninguna
  etapa posterior se ejecuta, y en particular la etapa de egreso nunca se alcanza si `authz` rechazó.
- Ninguno de estos tests existe hoy en `tests/` — esta nota no los agrega (fuera del alcance de archivos
  permitidos), solo los identifica como trabajo futuro directamente derivado del diseño propuesto.

## 10 · Supuestos y preguntas abiertas

**Supuestos (marcados explícitamente, no verificados contra código ni con Dylan):**

- El pipeline corre in-process (llamadas Python síncronas o async/await encadenadas), no como servicio de
  red separado, en Fase 1. Si esto es falso, el diseño de `Stage`/`Pipeline` cambia sustancialmente.
- Las etapas son fijas y no configurables por capability individual (misma cadena para toda invocación) —
  no se investigó si algún caso de uso necesita saltarse una etapa.

**Preguntas abiertas:**

- ¿El pipeline es el mismo objeto/módulo que despacha (`runtime`, nota 02), o son dos componentes
  separados que se llaman en secuencia? Esta nota asume que son conceptualmente distintos pero no lo
  confirma con código existente.
- ¿Cómo se extiende el pipeline sin convertirse en un bypass del chokepoint? (ej. si una capability
  necesita una etapa extra, ¿dónde se declara sin que cada capability pueda alterar el orden global?)
- ¿Dónde entra exactamente el `model router` (nota 05) — es una etapa del pipeline, o vive completamente
  dentro de `serving`, invocado únicamente desde la etapa de despacho? **RESUELTO (execution/09, freeze
  §15.7):** no es etapa propia — `ModelPort` vive en `serving`, invocado desde la etapa de despacho como
  cualquier otra capability; la llamada real la hace el adapter `ModelServer` en `blite.protocols`.
- ¿Cómo se maneja el caso de §8.4 (reautorización a mitad de pipeline por un permiso adicional descubierto
  durante el despacho)? **RESUELTO en el freeze §8: fail-closed, jamás re-evaluación en vuelo** — esta
  lista quedó desactualizada respecto al encabezado de la nota; ver ahí la cita completa.

## 11 · Recomendación mínima de POC

Una implementación mínima que valide el diseño sin construir las 7 etapas completas:

1. `Stage` como `Protocol` con `handle(ctx: dict) -> tuple[dict, Rejection | None]` (usar `dict` como
   `ctx` en el POC, no un tipo congelado — evita comprometerse a un esquema antes de tiempo, ver §10).
2. Implementar solo 3 etapas reales: **identidad** (stub que siempre resuelve un actor fijo), **authz**
   (stub que siempre autoriza), **despacho** (invoca el Registry real de la nota 04 contra 1 capability de
   ejemplo). Las etapas de guardrails/policy/verificación/egreso quedan como **no-ops que pasan directo**
   — su ausencia real es aceptable en un POC porque el objetivo es validar el ORDEN y el mecanismo de
   corte de cadena, no la lógica de negocio de cada etapa (que es plano de Dylan de todas formas).
3. Un test que verifique que, si el stub de authz rechaza, el despacho NUNCA se ejecuta — esto valida la
   propiedad estructural central de la nota (§1.3) con el mínimo de código posible.

## 12 · Dirección later / producción

Fuera de alcance de esta nota, pero como dirección conceptual (no comprometida): una vez que existan
implementaciones reales de identidad/authz/guardrails/verification (plano de Dylan), el `Pipeline` de esta
nota se vuelve el punto de integración — cada `Stage` real reemplaza su stub sin cambiar el contrato de
`Pipeline`/`Stage` en sí (si el diseño de §8 se mantiene estable). Preguntas de producción explícitamente
diferidas: observabilidad por etapa (métricas de latencia por `Stage`), circuit-breaking si una etapa
externa (ej. un `Verifier` remoto) se degrada, y si el pipeline necesita paralelizar alguna etapa
(ej. guardrails y resolución de policy no tienen dependencia mutua evidente) — ninguna de estas se
investigó en esta pasada.

## 13 · Reconciliación contra la base lógica (`docs/invariants.md`)

- **INV-1 (gateway único chokepoint):** REFORZADO en el diseño — el pipeline propuesto es exactamente el
  mecanismo interno que hace cumplible la afirmación "todo pasa por gateway"; sin una forma explícita de
  etapas, INV-1 es una aspiración, no un mecanismo. El modo de falla "bypass" (§6) sigue siendo posible
  hasta que exista el test de arquitectura propuesto en §9 — la nota no afirma que INV-1 esté
  mecánicamente cerrado, solo que este diseño es el camino para cerrarlo.
- **INV-6 / Inv-E (egreso solo por authz, nunca por verificación):** REFORZADO por el orden de etapas
  (§1.3) — estructural, no solo disciplina. El modo de falla "guardrail confundido con verificación" (§6)
  identifica dónde ese refuerzo podría fallar en la práctica si no se acompaña de tipos disjuntos.
- **INV-3 (guardrails no decide egreso):** INTACTO — la etapa de guardrails-pre en este diseño no tiene
  acceso a decidir el paso de egreso, solo a rechazar antes de despachar.
- **INV-4 (override registrado antes de ejecutar):** INTACTO, con el matiz señalado en §8.3 — el diseño
  debe hacer explícito qué etapa es responsable de emitir el evento, no dejarlo implícito.
- **Ninguna referencia contradice la base lógica.** El patrón de middleware chain es genérico y no impone
  ninguna semántica de egreso o verificación propia — la restricción de orden es enteramente nuestra,
  derivada de los invariantes ya congelados.
