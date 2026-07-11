# Nota 06 — Despacho por `execution_profile`: in-process hoy, contrato abierto a más formas

**Ítem del plan:** plano de ejecución (Steven) — cómo `runtime`/`serving` deberían despachar según el
campo `execution_profile` que `knowledge/trust/06` ya diseñó como parte de `CapabilityManifest` v2.
**Fecha:** 2026-07-10 · **Estado:** insumo para contract freeze
**Fuentes:** `knowledge/trust/06-protocolos-capability-mcp-a2a.md` §1.2 y §4 (los dos ejes `interaction` /
`execution_profile`, valores congelados: `in-process|service|remote-job`) · `docs/invariants.md`
(ADR-029, AX3) · `knowledge/execution/04-capability-registry-adapters.md` (esta misma carpeta) ·
`knowledge/execution/05-model-router-serving-boundary.md` (el mismo problema de egress mediado aplica a
`remote-job`) · patrón general de strategy pattern / dispatch table (referencia conceptual, sin
dependencia) · concepto adicional de "external_gateway" (referencia conceptual propia de esta nota, NO
parte del contrato ya congelado por trust/06 — ver §1.2)

---

## 1 · Patrón / mecanismo

### 1.1 El contrato de dos ejes ya está congelado del lado de Dylan — esta nota es sobre el despacho

`knowledge/trust/06` §1.2 ya decidió: `interaction` (`request_response|job|stream`, semántica congelada en
el manifest) y `execution_profile` (`in-process|service|remote-job`, hint de empaquetado, sobreescribible
por `DistributionManifest`). Esta nota NO reabre esa decisión — asume el campo como dado y se enfoca en
qué hace `runtime`/`serving` con su valor al despachar una invocación.

### 1.2 `execution_profile` como estrategia de despacho — y una cuarta forma conceptual no congelada

`execution_profile` es, en términos de patrón, la clave de una tabla de despacho (`dispatch table` /
strategy pattern): dado el valor del campo, se elige QUÉ mecanismo ejecuta la invocación. Los 3 valores ya
congelados por trust/06 son `in-process`, `service`, `remote-job`. Esta nota agrega, únicamente como
concepto de análisis (NO como propuesta de un cuarto valor de contrato, que requeriría coordinación con
Dylan igual que cualquier cambio al manifest), la idea de **"external_gateway"** — el caso donde la
invocación no se ejecuta en ningún proceso propio del engine, sino que se reenvía a un gateway/API externo
que YA hace su propio despacho interno (ej. invocar una capability que en realidad es un wrapper alrededor
de un servicio SaaS de terceros). Se incluye en la comparación de §1.3 porque clarifica los límites de los
3 valores ya congelados, no porque se proponga como cuarto valor real.

### 1.3 Cuatro estilos de despacho — comparados concretamente

| Estilo | Dónde corre el código de la capability | Latencia típica esperada (conceptual, sin medición) | Requiere mediación de red (nota 05) | Estado en Fase 1 |
|---|---|---|---|---|
| **`in-process`** | Mismo proceso Python que el engine, llamada de función directa | Mínima — sin serialización de red | No | **Implementado en el POC** (§11) |
| **`service`** | Un proceso separado (ej. otro servicio dentro de la misma infraestructura), invocado vía IPC/HTTP interno | Media — hay un salto de proceso, pero dentro del mismo perímetro de confianza | Sí, aunque "interno" — el mismo argumento de AX3/mediación de la nota 05 aplica si `serving` fuera quien hace la llamada directamente | **Solo forma de contrato — no implementado** |
| **`remote-job`** | Un sistema externo de cómputo (ej. una cola de jobs, un cluster, una QPU real vía trust/06 §1.3) que puede tardar minutos/horas | Alta y variable — este es precisamente el caso que motivó el vocabulario `capability.job.*` en trust/06 | Sí, de forma explícita — cruza el perímetro de confianza | **Solo forma de contrato — no implementado** |
| **"external_gateway"** (concepto de análisis, no valor de contrato) | Un gateway/API de terceros que internamente decide cómo ejecutar | Desconocida — depende enteramente del tercero | Sí, y además introduce un segundo "gateway" fuera del control de INV-1 — riesgo arquitectónico distinto, ver §6 | **No es parte del contrato — mencionado solo para contraste** |

### 1.4 Un dispatcher genérico por perfil, no un `if/elif` de escenario

Para no violar ADR-029 (genericidad de manifests) ni introducir conocimiento de escenario en el engine, el
despacho por `execution_profile` debe ser un mecanismo genérico — un `Dispatcher` (Protocol) con una
estrategia registrada por valor de perfil, no una rama de código que conozca capabilities específicas:

```python
class DispatchStrategy(Protocol):
    def execute(self, capability: Capability, inputs: dict) -> Result | JobRef: ...

# execution_profile -> DispatchStrategy, resuelto de forma genérica, sin nombrar capabilities
```

### 1.5 Coherencia con AX3 si el perfil es `remote-job` o `service`

Si una capability tiene `execution_profile: remote-job` (y, en menor medida, `service` si el "servicio" es
externo al proceso del engine), la llamada de red hacia ese destino NO puede salir desde `blite.serving`
directamente (mismo razonamiento que la nota 05 sobre el router de modelos) — tiene que pasar por el mismo
camino mediado (gateway/protocols bajo authz, INV-6). Esta nota señala la coherencia requerida con la nota
05, no la resuelve por separado — es el MISMO problema estructural sin resolver, aplicado aquí a
capabilities en vez de a modelos.

## 2 · Alternativas consideradas

Las 4 filas de §1.3 (incluyendo el concepto de análisis "external_gateway") constituyen las alternativas
comparadas.

## 3 · Por qué no (descartadas)

- **Implementar `service`/`remote-job` ahora — descartado para Fase 1/POC:** sin necesidad demostrada; se
  deja el puerto abierto a extensión, no la implementación (mismo razonamiento que la nota 03 sobre
  durabilidad: no construir infraestructura sin evidencia de que se necesita).
- **"external_gateway" como cuarto valor real de contrato — descartado, y no es una decisión de esta
  nota tomarlo o no.** Se incluyó únicamente como concepto de análisis en §1.3 para clarificar el límite
  de `service`/`remote-job`; proponer un cuarto valor real requeriría modificar `CapabilityManifest`
  (contrato de Dylan) y no es algo que esta nota — ni ninguna nota de esta carpeta bajo su alcance
  restringido — pueda decidir unilateralmente.
- **Un `if/elif` de escenario en vez de un dispatcher genérico — descartado:** violaría directamente
  ADR-029 si el código de despacho terminara conociendo capabilities específicas por nombre en vez de
  resolver por VALOR de `execution_profile`.

## 4 · Decisión

| Referencia                                                     | Decisión      | Racional                                                                                          |
| -------------------------------------------------------------------| ------------- | ------------------------------------------------------------------------------------------------|
| Los dos ejes `interaction`/`execution_profile` (trust/06)          | **integrar**  | Contrato ya congelado del lado de Dylan; esta nota lo consume, no lo redefine                    |
| Dispatcher genérico por estrategia (strategy pattern, referencia general) | **portar**    | Necesario para respetar ADR-029 — el despacho no puede conocer capabilities específicas por nombre |
| Implementar estrategias `service`/`remote-job` ahora               | **descartar** (para Fase 1) | Sin necesidad demostrada; se deja el puerto abierto a extensión, no la implementación             |
| Concepto "external_gateway" como cuarto valor de contrato           | **descartar** | Fuera del mandato de esta nota; solo se usa como concepto de análisis en §1.3                      |

## 5 · Tradeoffs

| Eje | `in-process` (elegido para POC) | `service` | `remote-job` |
|---|---|---|---|
| Latencia | Mínima | Media | Alta y variable |
| Complejidad de implementación | Baja | Media (requiere IPC/HTTP interno) | Alta (requiere polling/webhooks de estado, vocabulario `capability.job.*`) |
| Aislamiento de fallos (un crash en la capability no tumba el engine) | Bajo — mismo proceso | Alto | Alto |
| Requiere mediación de red (nota 05) | No | Sí (si el servicio es externo al proceso) | Sí, siempre |
| Adecuado para cómputo de larga duración | No | Parcial | Sí — es el caso de diseño (ej. QPU real, trust/06 §1.3) |

## 6 · Modos de falla

- **Tratar un `remote-job` como si fuera síncrono.** Este es el modo de falla más importante de esta nota:
  si el código de despacho invoca una capability `execution_profile: remote-job` con la MISMA expectativa
  de retorno inmediato que usa para `in-process` (ej. bloquea esperando un resultado en la misma llamada de
  función, en vez de tratarlo como un `capability.job.submitted` que completará más tarde vía eventos), el
  resultado es un timeout, un bloqueo indefinido del `RunStep` (nota 02), o un `run` que parece "colgado"
  sin ninguna señal clara de qué está esperando. Este riesgo es DIRECTAMENTE la razón por la que trust/06
  §1.3 diseñó el vocabulario `capability.job.submitted/progress/completed/failed` — tratar todo como
  petición-respuesta síncrona rompe ese diseño.
- **Confundir `service` interno con `remote-job` externo en cuanto a garantías.** Un `service` que corre
  dentro del mismo perímetro de confianza podría tratarse (incorrectamente) con las mismas garantías de
  latencia/disponibilidad que `in-process`, cuando en realidad ya introduce una superficie de fallo de red
  (aunque interna) — un desarrollador que asuma "service es casi como in-process" puede no manejar
  timeouts/reintentos correctamente.
- **"external_gateway" como bypass no controlado (riesgo arquitectónico, no solo de implementación).** Si
  alguna capability terminara, en la práctica, delegando su ejecución completa a un gateway de terceros sin
  que ESE gateway esté sujeto a la misma disciplina de INV-1 (nuestro gateway) — introduce un segundo punto
  de control fuera de la vista del chokepoint único. Este es un argumento adicional (más allá de "no es
  parte del contrato") de por qué esta nota no propone "external_gateway" como valor real.

## 7 · Licencias

| Pieza                              | Licencia               | Verificado                                    |
| --------------------------------------| -------------------------| -------------------------------------------------|
| Strategy pattern / dispatch table     | N/A — patrón, no código  | conocimiento general, **no verificado en vivo esta sesión** |

No se propone ninguna dependencia nueva en esta nota.

## 8 · Impacto en contrato

1. Propuesta de forma: `Dispatcher.resolve(execution_profile) -> DispatchStrategy`, con `InProcessStrategy`
   como única implementación real en Fase 1. **Propuesta de diseño, no forma congelada.**
2. El valor por defecto de `execution_profile` (`"in-process"`, ya fijado en el manifest por trust/06 §4)
   determina que, si una capability no declara nada distinto, el dispatcher nunca necesita resolver
   `service`/`remote-job` — el camino feliz de Fase 1 no cambia por la existencia de este contrato.
3. Cualquier despacho hacia `service`/`remote-job` que en el futuro implique red debe reconciliarse con la
   nota 05 (AX3) antes de implementarse — señalado aquí como dependencia cruzada dentro de esta misma
   carpeta.
4. **Qué existe solo como contrato futuro vs qué el POC soporta de verdad:**
   - **El POC soporta (§11):** únicamente `in-process`, con el `Dispatcher` estructurado de forma que
     agregar las otras estrategias no requiera cambiar la firma del puerto.
   - **Solo forma de contrato, sin implementación:** `service` y `remote-job` — ambos existen hoy
     únicamente como valores de enum ya congelados del lado de Dylan (trust/06), sin código de despacho
     real detrás. Cualquier documentación o comunicación sobre estas notas debe dejar claro que "el
     contrato acepta estos valores" NO significa "el sistema puede ejecutarlos hoy".

## 9 · Implicaciones de test / spec

- **Test de resolución del dispatcher:** verificar que `Dispatcher.resolve("in-process")` devuelve la
  estrategia correcta, y que `resolve("service")`/`resolve("remote-job")` fallan de forma explícita y
  clara (no silenciosa) en Fase 1, ya que no hay estrategia real implementada — esto cierra parcialmente
  el modo de falla de tratar un perfil no soportado como si lo fuera.
- **Test de "no bloqueo síncrono para `remote-job`":** un test que, incluso con una estrategia mock, fuerce
  el caso de que una invocación con `execution_profile: remote-job` NO puede completarse en la misma
  llamada — verificando que el contrato de retorno es un `JobRef`, no un `Result` directo, para ese perfil.
  Cierra directamente el modo de falla central de §6.
- **Test de default:** verificar que una capability sin `execution_profile` explícito en su manifest recibe
  el valor por defecto `in-process` (ya fijado por trust/06 §4) y se despacha en consecuencia.
- Ninguno de estos tests existe hoy — señalados como trabajo futuro derivado de este diseño.

## 10 · Supuestos y preguntas abiertas

**Supuestos:**

- Solo se implementa `InProcessStrategy` en Fase 1; las otras dos son forma de contrato, no código
  funcional — si el equipo necesita `service`/`remote-job` antes de lo esperado, esta nota no alcanza como
  guía de implementación.
- El `Dispatcher` es invocado desde la etapa de despacho del pipeline del gateway (nota 01) o desde el
  runtime (nota 02) — no se confirmó cuál de los dos posee esta responsabilidad.

**Preguntas abiertas:**

- ¿Quién fija el `execution_profile` por defecto de una capability en Fase 1 — el autor de la capability en
  su manifest, o puede el registry/dispatcher sobreescribirlo sin una `DistributionManifest` real (que
  trust/06 §1.2 ubica en `distributions/chimera/`, carril de Dylan)? No decidido.
- ¿Un perfil `"service"` implica que `runtime` administra el ciclo de vida de un proceso del SO (arrancar/
  detener un servicio), o eso es enteramente responsabilidad de infraestructura fuera del engine? No
  investigado — impacta directamente si esta nota es solo de contrato o también de orquestación de
  procesos.
- ¿Cómo se comunica un fallo de "no hay estrategia disponible para este perfil todavía" (ej. alguien
  declara `remote-job` antes de que exista esa estrategia) — error de arranque, error en tiempo de
  invocación, o degradación a `in-process` si es posible? No decidido.

## 11 · Recomendación mínima de POC

El POC implementa ÚNICAMENTE `InProcessStrategy`. Concretamente: (1) el `Dispatcher` como diccionario
`{profile: DispatchStrategy}` con una sola entrada (`"in-process"`); (2) `resolve()` sobre cualquier otro
valor lanza una excepción explícita y clara (`NotImplementedError` o similar, con mensaje que indique que
el perfil existe en el contrato pero no en esta implementación) — NUNCA debe hacer fallback silencioso a
`in-process` para un perfil distinto, porque eso escondería exactamente el modo de falla central de §6
(tratar remote-job como síncrono) en vez de exponerlo. (3) Ningún test del POC debe usar `service` ni
`remote-job` como si funcionaran — son parte del contrato consumido (trust/06), no del código ejercitado.

## 12 · Dirección later / producción

Fuera de alcance de esta nota, como dirección conceptual: `service` sería la extensión más directa de
implementar (mismo perímetro de confianza, "solo" IPC/HTTP interno) y debería reconciliarse con la nota 05
antes de escribir la primera línea de código real. `remote-job` es la extensión de mayor valor para el
caso de uso original del proyecto (cómputo cuántico de larga duración, trust/06 §1.3) pero también la de
mayor superficie (requiere el vocabulario `capability.job.*` completo, manejo de timeouts/polling, y
mediación de red bajo INV-6) — no se compromete ninguna secuencia de implementación aquí. "external_gateway"
NO se recomienda como dirección futura sin antes resolver cómo mantener INV-1 (chokepoint único) si parte
de la ejecución ocurre detrás de un gateway ajeno al propio.

## 13 · Reconciliación contra la base lógica (`docs/invariants.md`)

- **ADR-029 (manifests genéricos):** INTACTO — el `Dispatcher` propuesto resuelve por VALOR del campo
  `execution_profile`, nunca por identidad de una capability específica; no se introduce ningún término de
  escenario. El concepto de análisis "external_gateway" no se propone como valor real, evitando cualquier
  tensión con este invariante antes de que exista una decisión de contrato.
- **AX3 (modelo/serving no toca el mundo directo):** pendiente de coherencia explícita con la nota 05 para
  los casos `service` (si es externo al proceso) y `remote-job` (§1.5) — señalado como dependencia cruzada,
  no como brecha resuelta ni como violación confirmada.
- **INV-1 (gateway único chokepoint):** el concepto "external_gateway" (§1.2, análisis, no contrato) es
  precisamente el caso que MÁS tensiona este invariante si se implementara sin cuidado — razón adicional
  por la que esta nota lo excluye explícitamente de cualquier propuesta de contrato real.
- **ADR-008 (capabilities fuera del core):** INTACTO — el `Dispatcher` opera sobre el `Capability` que le
  entrega el Registry (nota 04), nunca importa un paquete `blite_cap_*` por su cuenta.
- **Ninguna referencia contradice la base lógica.** El patrón de strategy/dispatch table es genérico y no
  impone ninguna semántica de egreso o verificación.
