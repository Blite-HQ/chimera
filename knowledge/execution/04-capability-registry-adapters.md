# Nota 04 — El Registry de capabilities: descubrimiento tolerante a fallos y el borde hacia adapters

**Ítem del plan:** plano de ejecución (Steven) — dar forma al contrato de `blite.runtime`'s registry
(`engine/src/blite/runtime/registry.py`) y su frontera con los adapters de protocolo (MCP/A2A) que
`knowledge/trust/06` ya diseñó del lado del contrato.
**Fecha:** 2026-07-10 · **Estado:** insumo para contract freeze — **mayormente cerrada** (S-E 2026-07-18):
descubrimiento tolerante a fallos (opción B, §4) **adoptado tal cual**, con eventos `registry.loaded
{capability_ids[], failed[]}` / `registry.capability_load_failed {entry_point, error_kind}`
(`actor_id: service:runtime`, stream `system:registry`) — cierra las dos preguntas abiertas de §10 sobre
reporte de arranque y distinción deshabilitada/fallida ("deshabilitada" = ausencia en el
`DistributionManifest`; "fallida" = entra en `failed`). Versión duplicada de un `id` (§6/§10) — cerrada:
pin por `DistributionManifest`, default **determinista, jamás `latest`**. Sigue **sin implementar**:
`engine/src/blite/runtime/registry.py` sigue siendo el stub `load_capabilities() -> dict` de Fase 1, no el
`Registry(Protocol)` de `list()`/`get()` con captura de excepción POR entry point que esta nota y el freeze
piden — próximo trabajo de S-G, todavía sin seed propio.
**EJECUTADA (2026-07-24)** — `runtime/registry.py` (`load_registry`, la opción B literal, eventos
`registry.loaded`/`registry.capability_load_failed`, pin determinista con `PinnedVersionNotFound`
fail-closed).
**Fuentes:** `docs/invariants.md` (ADR-008, ADR-029) · `pyproject.toml` (`[tool.uv.workspace]`,
`members = ["sdk", "engine", "capabilities/*"]`) · `capabilities/quantum/pyproject.toml`
(`vqe = ['qiskit>=1.0', 'qiskit-nature>=0.7', 'pyscf>=2.4']`, extra opcional que falla en Windows por
requerir BLAS — hecho observado en esta sesión de setup, no corregido aquí) ·
`knowledge/trust/06-protocolos-capability-mcp-a2a.md` (CapabilityManifest v2, mapeo manifest→MCP tool) ·
patrón general de plugin discovery vía entry points (ya en uso real en este repo, no es referencia
externa) · patrón general de "tool" en protocolos de agentes (MCP `tools/list`, referencia conceptual, no
verificada en vivo esta sesión)

---

## 1 · Patrón / mecanismo

### 1.1 El mecanismo de descubrimiento YA está decidido — ADR-008 + entry points

A diferencia de otras notas de esta carpeta, aquí no hace falta traer un patrón externo: el propio
`README.md` del repo y `CONTRIBUTING.md` ya especifican que cada capability declara un
`[project.entry-points."blite.capabilities"]` en su `pyproject.toml`, descubierto en runtime vía
`importlib.metadata` (estándar de Python, sin dependencia nueva). ADR-008 fija que el engine nunca importa
`blite_cap_*` directamente — el registry es el único lugar que sí lo hace, a través del mecanismo de entry
points, no de imports estáticos.

### 1.2 Capability vs Tool vs Adapter — tres conceptos que se confunden fácilmente

Esta distinción no estaba explícita en la versión anterior de esta nota y es la fuente más probable de
confusión de diseño, así que se detalla aquí:

- **Capability** — el concepto propio del proyecto (`CapabilityManifest`, ADR-029): una unidad de trabajo
  genérica, con `input_schema`/`output_schema`, descubierta vía entry points, que vive detrás del puerto
  `Capability` (trust/06 §1.1: "el puerto `Capability` es el contrato; MCP, A2A, HTTP, in-process son
  adapters en el borde"). Una capability existe independientemente de cómo se exponga hacia afuera.
- **Tool** — el vocabulario de MCP (`tools/list`, `tools/call` — referencia conceptual de la spec, no
  verificada en vivo esta sesión, ya citada en trust/06 §1.4). Un "tool" es cómo un CLIENTE MCP ve una
  capability EXPUESTA a través del adapter MCP. El mapeo ya está congelado del lado de Dylan:
  `manifest.id → tool.name`, `description → description`, `input_schema → inputSchema`,
  `output_schema → outputSchema` (trust/06 §1.4). No toda capability necesita convertirse en tool — solo
  las que el adapter MCP decide exponer.
- **Adapter** — el código que TRADUCE entre el puerto `Capability` (nuestro) y un protocolo externo
  (MCP, A2A, HTTP directo). Un adapter no es una capability ni un tool — es el traductor entre ambos
  mundos, y vive en el borde (`protocols/` del lado de Dylan, o un módulo de exposición equivalente),
  nunca dentro del núcleo de `blite.runtime`.

La confusión típica: tratar "registrar una capability" y "exponerla como tool MCP" como el mismo paso.
No lo son — el Registry (este documento) resuelve el PRIMERO; el adapter MCP (trust/06, plano de Dylan en
cuanto al protocolo, pero implementado potencialmente del lado de Steven en cuanto a mecánica) resuelve el
SEGUNDO, iterando sobre lo que el Registry ya expone.

### 1.3 El registry es lectura + despacho, no autorización ni verificación

Contrato mínimo propuesto:

```python
class Registry(Protocol):
    def list(self) -> tuple[CapabilityManifest, ...]: ...
    def get(self, capability_id: str) -> Capability: ...
```

El registry NO decide si el actor tiene permiso (`authz`, fuera de este plano), NO verifica el resultado
(`verification`, fuera de este plano) — es estrictamente: ¿qué capabilities existen? ¿cómo invoco una por
id? Esta separación mantiene el registry simple y evita que se vuelva un segundo lugar de decisión de
seguridad, algo que ADR-008/INV-1 implícitamente exigen (el gateway, no el registry, es el chokepoint).

### 1.4 Descubrimiento, validación, y el ciclo de vida de una entrada del registry

El descubrimiento no es un evento binario ("cargó" / "no cargó") — tiene varias etapas, cada una con su
propio modo de fallo:

1. **Enumeración de entry points.** `importlib.metadata.entry_points(group="blite.capabilities")` — esto
   solo lee METADATA instalada (lo que `pip`/`uv` registró), no importa código todavía. Puede fallar si el
   paquete está mal instalado, pero normalmente no falla por dependencias del propio código de la
   capability.
2. **Import del módulo/clase apuntado por el entry point.** Aquí es donde una dependencia opcional
   faltante (el caso pyscf/VQE, §1.5) causa un `ImportError` — el código Python de la capability importa
   `pyscf` en algún punto de su cadena de imports, y si no está instalado, el import falla.
3. **Construcción del `CapabilityManifest`.** Incluso si el import tuvo éxito, construir el manifest
   podría fallar si el código tiene un bug (ej. un schema mal formado).
4. **Validación de genericidad (ADR-029).** El manifest construido debe pasar el test de genericidad
   (`tests/invariants/test_capability_genericity.py`, ya existente en el repo) — esto ya ocurre a nivel de
   test, no en el registry en tiempo de ejecución, hasta donde esta nota pudo confirmar.

Cada una de estas etapas puede fallar independientemente, y el registry necesita una política explícita
para cada una — hoy, sin una implementación real, esa política no existe.

### 1.5 El caso pyscf/VQE como ejemplo concreto de por qué esto importa

`capabilities/quantum/pyproject.toml` declara un extra opcional `vqe = ['qiskit>=1.0',
'qiskit-nature>=0.7', 'pyscf>=2.4']`. En esta misma sesión de trabajo se observó que instalar
`blite-cap-quantum[vqe]` falla en Windows porque `pyscf` requiere BLAS (no disponible/instalado en ese
entorno). **Esta nota NO propone corregir esa falla de dependencia** — está fuera de alcance (instrucción
explícita) — pero la usa como evidencia concreta y ya observada (no hipotética) de un requisito de diseño:
si el registry importa entry points de forma estricta (un `ImportError` en cualquiera detiene TODO el
arranque del engine), entonces un desarrollador en Windows sin BLAS **no puede arrancar el engine en
absoluto**, aunque solo necesite capabilities que nada tienen que ver con VQE. Esto no es un caso límite
teórico — ya ocurrió en este mismo repositorio durante esta sesión.

### 1.6 La frontera con adapters (MCP/A2A) — el registry es lo que un adapter recorre

`knowledge/trust/06` §1.4 ya decidió que un servidor MCP genérico puede "iterar el registry y exponer cada
capability como tool — un adapter, cero cambios al núcleo". Esto fija una restricción de diseño sobre
ESTA nota: `Registry.list()` debe devolver manifests suficientemente completos (incluyendo los campos
nuevos de `CapabilityManifest` v2: `side_effects`, `required_permission`, `interaction`,
`execution_profile`) para que el mapeo manifest→MCP tool de trust/06 §1.4 no necesite ninguna llamada
adicional al registry por capability. Un adapter que itera `list()` verá únicamente las capabilities que
el registry logró cargar — las que fallaron en alguna etapa de §1.4 simplemente no aparecen, lo cual es
la razón de ser de la tolerancia a fallos discutida abajo.

## 2 · Alternativas consideradas

- **(A) Descubrimiento estricto (fail-fast).** Un `ImportError` en cualquier entry point detiene el
  arranque completo del engine.
- **(B) Descubrimiento tolerante a fallos (skip + registro del fallo).** Un entry point que falla al
  importar se omite del registry (no aparece en `list()`), y el fallo se registra (log/evento) para
  visibilidad, pero el engine arranca igual con las capabilities que sí cargaron.
- **(C) Descubrimiento perezoso (lazy).** El entry point se enumera pero NO se importa hasta que alguien
  invoca `get(capability_id)` — el fallo de import se pospone al momento de uso, no de arranque.
- **(D) Extras opcionales excluidos por defecto, habilitados explícitamente.** El registry (o un paso de
  configuración anterior) solo intenta cargar capabilities cuyas dependencias fueron instaladas
  explícitamente (ej. vía un flag de configuración o un manifiesto de distribución), en vez de intentar
  todas las descubribles.

## 3 · Por qué no (descartadas)

- **(A) descartada como default:** el caso pyscf/VQE (§1.5) demuestra directamente por qué — un
  desarrollador que solo necesita `capabilities/solvers` no debería quedar bloqueado porque
  `capabilities/quantum[vqe]` no puede instalarse en su entorno. Fail-fast en arranque convierte una
  dependencia OPCIONAL (así declarada en `pyproject.toml`, como extra) en una dependencia obligatoria de
  facto, contradiciendo la intención del propio `pyproject.toml` del repo.
- **(C) descartada como ÚNICA estrategia para Fase 1:** descubrimiento perezoso resuelve el arranque, pero
  desplaza el fallo a un momento de invocación en producción, potencialmente en medio de un run real (mal
  momento para descubrir que una capability no está disponible) — se prefiere fallar temprano PERO de
  forma NO bloqueante (ver decisión, opción B), no fallar tarde.
- **(D) no descartada, pero fuera de alcance de esta nota como diseño completo:** requiere un mecanismo de
  configuración/distribución (relacionado con `DistributionManifest`, trust/06 §1.2, carril de Dylan) que
  esta nota no diseña — se deja como posible refinamiento futuro de (B), no como alternativa excluyente.

## 4 · Decisión

| Referencia                                                                           | Decisión      | Racional                                                                                                                                              |
| ------------------------------------------------------------------------------------ | ------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| Entry points (`importlib.metadata`) para descubrimiento                              | **portar**    | Ya es el mecanismo elegido por el repo (ADR-008, `pyproject.toml` de cada capability) — no es una decisión nueva de esta nota, se documenta y consume |
| Registry como lectura + despacho puro (sin authz/verification propios)               | **portar**    | Se deriva directamente de INV-1 (gateway es el chokepoint, no el registry) y de la separación de responsabilidades ya vigente en los invariantes      |
| Descubrimiento tolerante a fallos, opción (B) de §2                                  | **portar**    | Directamente motivado por el caso real pyscf/VQE (§1.5); evita que una dependencia opcional bloquee todo el engine                                    |
| Descubrimiento estricto/fail-fast, opción (A)                                        | **descartar** | Ver §3 — convierte extras opcionales en obligatorios de facto                                                                                         |
| Mapeo manifest→MCP tool (trust/06 §1.4) como restricción sobre la forma del registry | **integrar**  | Contrato ya congelado del lado de Dylan; esta nota lo consume como requisito de completitud del manifest devuelto por `list()`                        |
| Distinción explícita Capability / Tool / Adapter (§1.2)                              | **portar**    | Necesaria para no confundir "registrar" con "exponer por protocolo" — previene errores de diseño en el adapter MCP futuro                             |

## 5 · Tradeoffs

| Eje                                                                  | Fail-fast (A)                                     | Tolerante a fallos (B, elegido)                                                                | Lazy (C)                                                       |
| -------------------------------------------------------------------- | ------------------------------------------------- | ---------------------------------------------------------------------------------------------- | -------------------------------------------------------------- |
| Robustez de arranque en entornos heterogéneos (ej. Windows sin BLAS) | Baja — bloquea todo                               | Alta — arranca con lo disponible                                                               | Alta                                                           |
| Visibilidad temprana de qué falta                                    | Alta (falla inmediatamente, imposible de ignorar) | Media (requiere revisar logs/eventos de arranque)                                              | Baja (el fallo aparece recién al invocar)                      |
| Riesgo de "sorpresa" en producción                                   | Bajo (si algo falta, no arranca)                  | Medio (arranca, pero una capability esperada podría no estar disponible sin que nadie lo note) | Alto (falla en medio de un run)                                |
| Complejidad de implementación                                        | Mínima                                            | Media (requiere capturar excepciones por entry point + reportar)                               | Media-alta (requiere manejar el import diferido correctamente) |

La opción (B) prioriza robustez operativa sobre visibilidad inmediata — el riesgo de "sorpresa" (§5) se
mitiga parcialmente con la recomendación de emitir un evento/log de arranque (pregunta abierta, §10, no
resuelta aquí en cuanto a vocabulario de eventos).

## 6 · Modos de falla

- **Import fallido de una dependencia opcional (caso real: pyscf/VQE en Windows).** Ya cubierto en detalle
  en §1.5 — el modo de falla que motiva la decisión central de esta nota.
- **Fallo silencioso.** Si el registry omite una capability que falló al cargar SIN registrar ese hecho en
  ningún lugar observable, un operador puede pasar mucho tiempo sin entender por qué una capability
  esperada "no existe" — la opción (B) resuelve el arranque pero introduce este riesgo si no se acompaña
  de reporte explícito (ver pregunta abierta y recomendación de POC).
- **Capability deshabilitada vs capability fallida — confundidas.** Una capability que un operador
  deshabilitó intencionalmente (ej. vía alguna configuración futura, relacionada con (D) de §2) y una que
  falló al cargar por accidente producen el mismo síntoma observable desde `list()` (no aparece) si el
  registry no distingue ambos casos — un riesgo de diagnóstico, no de seguridad.
- **Versión duplicada de un `id`.** Si dos paquetes instalados declaran el mismo `capability_id` (ej.
  durante una migración de versión), el comportamiento de `importlib.metadata` ante entry points
  duplicados no está definido por esta nota — riesgo de que el registry elija una versión arbitraria sin
  que quede claro cuál.

## 7 · Licencias

| Pieza                                                              | Licencia                               | Verificado                                                                        |
| ------------------------------------------------------------------ | -------------------------------------- | --------------------------------------------------------------------------------- |
| `importlib.metadata` (stdlib de Python)                            | PSF License (stdlib)                   | conocimiento general — mecanismo ya en uso en el repo, no nuevo                   |
| MCP `tools/list`/`tools/call` (vocabulario, referencia conceptual) | ya evaluada por trust/06 (MIT del SDK) | ver `knowledge/trust/06-protocolos-capability-mcp-a2a.md` §3 — no reevaluada aquí |

No se propone ninguna dependencia nueva en esta nota.

## 8 · Impacto en contrato

1. Propuesta de forma mínima de `Registry` (§1.3) — `list()`/`get()`; el nombre exacto del método de
   invocación (`invoke` vs delegarlo enteramente al objeto `Capability` devuelto por `get()`) no se fija
   aquí.
2. El registry vive en `blite.runtime` (ya así en el árbol actual — `runtime/registry.py`), consistente
   con CODEOWNERS (`engine/src/blite/runtime/` es de Steven).
3. Requisito derivado de trust/06 §1.4 (§1.6 arriba): `list()` debe exponer el `CapabilityManifest`
   completo, incluyendo los 4 campos nuevos de la v2, apenas ese manifest se congele del lado de Dylan —
   esta nota no lo congela, solo documenta la dependencia.
4. **Descubrimiento tolerante a fallos (§4) como requisito de contrato, no solo de implementación:** el
   registry debe capturar excepciones POR entry point individual (no una única try/except alrededor de
   toda la enumeración) — si un entry point falla, los demás deben seguir cargando. Esta es la forma
   concreta en que el diseño responde al caso pyscf/VQE.
5. El registry no emite eventos de "capability.registered" en esta propuesta para el caso de éxito, pero
   SÍ debería registrar (de alguna forma, mecanismo no fijado — pregunta abierta) las capabilities que
   fallaron al cargar, para no caer en el modo de falla "fallo silencioso" (§6).

## 9 · Implicaciones de test / spec

- **Test de descubrimiento tolerante a fallos:** un test que instale (o simule vía mock de
  `importlib.metadata`) dos entry points, uno que importa correctamente y otro que lanza `ImportError`, y
  verifique que `Registry.list()` devuelve solo el primero, sin que la construcción del registry lance
  excepción — esta es la prueba directa de que el modo de falla pyscf/VQE no bloquea el resto del sistema.
- **Test de genericidad end-to-end vía registry:** el repo ya tiene
  `tests/invariants/test_capability_genericity.py` (mencionado en `docs/invariants.md`, ADR-029) — esta
  nota no lo modifica, pero señala que, con descubrimiento tolerante a fallos, ese test debería correr
  sobre las capabilities que SÍ cargaron, no fallar en bloque si una capability opcional no está
  disponible en el entorno de CI/test actual. Verificar esto es una implicación directa del diseño, no una
  garantía ya confirmada.
- **Test de reporte de fallos de carga:** una vez que se defina el mecanismo de reporte (pregunta abierta,
  §10), un test que verifique que una capability fallida queda registrada en algún lugar observable
  (log estructurado o evento), no simplemente silenciada.
- **Test de manifest completo para adapters:** verificar que cada manifest devuelto por `list()` tiene
  todos los campos que trust/06 §1.4 necesita para el mapeo a MCP tool — cierra la frontera de completitud
  señalada en §1.6.
- Ninguno de estos tests existe hoy — señalados como trabajo futuro derivado de este diseño.

## 10 · Supuestos y preguntas abiertas

**Supuestos:**

- El registry es un singleton en memoria por instancia del engine, construido una vez al arrancar el
  proceso — no hay recarga en caliente (hot-reload) de capabilities en Fase 1.
- Todas las capabilities activas están instaladas en el mismo entorno Python que el engine (mismo
  `uv sync --all-packages`), no hay descubrimiento remoto de capabilities en Fase 1.

**Preguntas abiertas:**

- ¿Cómo se versiona una capability si dos versiones del mismo `id` están instaladas a la vez (ej. durante
  una migración)? No investigado — `CapabilityManifest.version` existe pero esta nota no define política
  de resolución de conflictos (modo de falla §6, "versión duplicada").
- ¿El registry debería emitir un evento de arranque (ej. `registry.loaded` con la lista de ids cargados Y
  fallidos) para que quede en el log de procedencia qué capabilities estaban disponibles durante un run, y
  cuáles fallaron y por qué? Directamente motivado por el modo de falla "fallo silencioso" (§6) — a decidir
  con Dylan (toca el vocabulario de eventos).
- ¿Cómo se distingue una capability "deshabilitada intencionalmente" de una "que falló al cargar" en la
  salida observable de `list()`/logs? No resuelto (modo de falla §6).
- ¿Existe algún mecanismo (relacionado con la opción (D) de §2, `DistributionManifest`) para declarar de
  antemano qué extras opcionales se espera que estén disponibles en un despliegue dado, de forma que un
  fallo de import de algo NO esperado sea más ruidoso que uno de algo ya sabido como opcional? No resuelto.

## 11 · Recomendación mínima de POC

1. `Registry.list()`/`get()` implementados sobre `importlib.metadata.entry_points(group="blite.capabilities")`,
   con un `try/except ImportError` (y, por seguridad, `except Exception` capturado como fallo de carga
   también — un manifest mal formado no debería tumbar el arranque igual que un import faltante) alrededor
   de CADA entry point individualmente, no de la enumeración completa.
2. Las capabilities que fallan al cargar se acumulan en una lista separada (`Registry.failed` o
   equivalente, forma no comprometida) accesible para debugging, aunque no se emita ningún evento formal
   todavía en el POC — un `print`/log simple basta para validar el mecanismo.
3. Un test manual/de integración: con el extra `vqe` de `capabilities/quantum` deliberadamente NO
   instalado (el estado real observado en Windows esta sesión), verificar que el registry arranca
   igual y expone las demás capabilities — esto usa el caso real ya observado como el propio caso de
   prueba del POC, sin necesidad de simular un fallo artificial.

## 12 · Dirección later / producción

Fuera de alcance de esta nota, como dirección conceptual: un mecanismo de reporte estructurado de fallos
de carga (probablemente un evento `registry.capability_load_failed` o similar, a coordinar con Dylan dado
que toca vocabulario de eventos) para que un operador de producción tenga visibilidad sin revisar logs de
texto libre; y eventualmente un mecanismo de declaración explícita de qué capabilities/extras se esperan
en un despliegue dado (opción D de §2, relacionado con `DistributionManifest` de trust/06), de forma que
"faltó algo que no se esperaba" se pueda distinguir de "faltó un extra opcional conocido". Ninguna de estas
direcciones se compromete en esta nota.

## 13 · Reconciliación contra la base lógica (`docs/invariants.md`)

- **ADR-008 (capabilities fuera del core del engine):** INTACTO y reforzado — el registry es precisamente
  el único punto de contacto entre `blite` y `blite_cap_*`, vía entry points, nunca vía import estático;
  esta nota no propone ninguna excepción. La tolerancia a fallos de carga (§4) refuerza además la
  independencia entre capabilities — el fallo de una NUNCA debe propagarse al resto, lo cual es consistente
  con el espíritu de "capabilities como plugins independientes" detrás de ADR-008.
- **ADR-029 (manifests genéricos):** INTACTO — el registry no interpreta el contenido semántico del
  manifest, solo lo transporta; no introduce ningún término de escenario. La distinción Capability/Tool/
  Adapter (§1.2) refuerza esto: un "tool" es una vista de protocolo sobre una capability genérica, no una
  segunda entidad con su propio vocabulario de escenario.
- **INV-1 (gateway único chokepoint):** INTACTO — el registry es consultado DESDE el pipeline del gateway
  (nota 01) o desde el runtime bajo su despacho, nunca es un punto de entrada alternativo al gateway.
- **AX1 (actor_id obligatorio en cada evento):** la decisión de no emitir un evento de "registro" exitoso
  al arrancar es consistente con AX1 tal como está — el arranque del proceso no tiene un actor humano o de
  agente asociado, así que forzar un evento ahí requeriría un actor sintético de la forma `service:<nombre>`
  (ej. `service:runtime`, patrón ya usado en trust/08 §1.4). El caso de un evento de FALLO de carga
  (pregunta abierta, §10) tendría la misma
  necesidad de actor sintético si se implementa.
- **Ninguna referencia contradice la base lógica.** El mecanismo de entry points ya es parte del repo, no
  una referencia externa nueva a evaluar; la tolerancia a fallos es una decisión de robustez operativa, no
  una relajación de ningún invariante de seguridad o procedencia.
