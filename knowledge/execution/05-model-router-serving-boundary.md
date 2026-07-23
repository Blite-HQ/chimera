# Nota 05 — Router de modelos y el aislamiento de red de `blite.serving` bajo AX3

**Ítem del plan:** plano de ejecución (Steven) — cómo se selecciona un backend de modelo sin que
`blite.serving` viole AX3 (un modelo nunca toca el mundo directo), que ya está enforced por
import-linter contra `httpx`/`requests`/`aiohttp`/`urllib3`/`socket` dentro de `blite.serving`.
**Fecha:** 2026-07-10 · **Estado:** **RESUELTA** (execution/09 + freeze §15.7, ratificación final
Steven+Dylan, S-E 2026-07-18): se decidió la **opción (b)** de §1.4/§5 — `ModelPort` (Protocol, cero red)
vive en `blite.serving`; el adapter que sí hace la llamada real (`ModelServer`, envuelve LiteLLM `Router`)
vive en `blite.protocols`, bajo INV-6 (protocols exige authz). El contrato **AX3-b** (endurecido en el
stress-final 2026-07-22) cierra el hueco de cobertura que esta nota señalaba en §6/§10 ("egreso de modelo
sin pasar por authz"): ningún módulo del engine fuera de `blite.protocols` puede importar un SDK de modelo.
`ModelPort` ya existe en código (`engine/src/blite/serving/model_port.py`, S-G Etapa 0 — Protocol listo,
**SPEC**); la implementación de `ModelServer` sigue pendiente.
**Fuentes:** `docs/invariants.md` (AX3, INV-2, INV-6) · `pyproject.toml` (contrato `AX3` de import-linter,
`forbidden_modules` de `blite.serving`: `blite.protocols`, `blite.gateway`, `blite.runtime`, `blite.authz`,
`httpx`, `requests`, `aiohttp`, `urllib3`, `socket`) · `engine/src/blite/serving/__init__.py` (vacío hoy) ·
referencias conceptuales de routers/serving de modelos, **ninguna verificada en vivo esta sesión**: router
simple compatible con la forma de API de OpenAI (un único formato de request/response, un solo backend),
router estilo LiteLLM (múltiples proveedores detrás de una interfaz unificada), serving local tipo
Ollama/vLLM (el propio proceso sirve el modelo, sin proveedor de red externo), y un adapter de serving de
producción (forma conceptual — capa de egress gestionada, con rate limiting/retries/observabilidad)

---

## 1 · Patrón / mecanismo

### 1.1 El problema en términos exactos del gate ya existente

Esto no es una hipótesis — es una restricción de código YA enforced. `pyproject.toml`, contrato
`AX3`, prohíbe que `source_modules = ["blite.serving"]` importe cualquiera de:
`blite.protocols`, `blite.gateway`, `blite.runtime`, `blite.authz`, `httpx`, `requests`, `aiohttp`,
`urllib3`, `socket`. Esto significa, en términos concretos de código Python: **ningún archivo bajo
`engine/src/blite/serving/` puede contener una línea `import httpx` (ni las otras 4 libs de red), ni
`import blite.protocols` etc.** — si lo hiciera, `uv run lint-imports` fallaría en CI. Esta es la
restricción real, verificable, no una interpretación de esta nota.

### 1.2 Por qué esto es un problema real, no un tecnicismo

Un "model router" típico (patrón de referencia genérico: una capa que decide, dado un request, qué backend
de modelo usar por costo/latencia/capacidad, y LUEGO hace la llamada) normalmente combina las dos
responsabilidades — decidir Y llamar — en el mismo lugar. AX3 fuerza a separarlas: `serving` puede decidir
QUÉ backend usar (dato puro), pero no puede ser el código que efectivamente abre la conexión de red hacia
ese backend. Esto es exactamente la misma restricción arquitectónica que ya aplica al modelo en sí (AX3:
"un modelo nunca toca el mundo directo") — extendida aquí a la CAPA que sirve al modelo.

### 1.3 Cuatro formas de router/serving — comparadas concretamente, y dónde cada una choca con AX3

| Forma                                                                                                                                                                                             | Qué hace en su forma "de manual"                                                                                                                                | Dónde choca con AX3 si se implementa ingenuamente dentro de `blite.serving`                                                                                                 |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Router simple compatible con la forma de API de OpenAI** (referencia conceptual — un único formato de request/response, típicamente un solo backend o unos pocos con la misma forma)            | Recibe un request, lo reenvía tal cual (o casi) a un único endpoint HTTP                                                                                        | Su forma "de manual" hace la llamada HTTP directamente — chocaría de inmediato con la prohibición de `httpx`/`requests` dentro de `serving`                                 |
| **Router estilo LiteLLM** (referencia conceptual — múltiples proveedores detrás de una interfaz unificada, con normalización de formatos)                                                         | Traduce un formato de request unificado al formato específico de cada proveedor, Y hace la llamada de red a cada uno                                            | Igual que el anterior, pero multiplicado por N proveedores — cada adapter de proveedor típicamente incluye su propio cliente HTTP                                           |
| **Serving local tipo Ollama/vLLM** (referencia conceptual — el modelo corre en el mismo host/proceso o en un proceso hermano local, sin salir a internet)                                         | El "proveedor" es un servidor local (ej. `localhost:11434`) — sigue siendo una llamada de red (HTTP a localhost), aunque no cruce la frontera de la red pública | Técnicamente sigue siendo una llamada de socket/HTTP — `AX3` no distingue "red local" de "red externa"; el import-linter prohíbe `socket`/`httpx` sin importar el destino   |
| **Adapter de serving de producción** (referencia conceptual — capa de egress gestionada, con rate limiting, reintentos, observabilidad, normalmente ya pensada como un servicio/proceso separado) | Encapsula la llamada de red DETRÁS de una interfaz — es, por diseño, la forma que YA separa "decidir" de "llamar"                                               | Es la única de las 4 que, en su forma habitual, ya separa las dos responsabilidades — pero "producción" implica más superficie (rate limiting, retries) que un POC necesita |

### 1.4 El problema estructural que esta nota deja explícitamente sin resolver (y por qué debe quedar así)

Las 4 formas de §1.3 muestran que el choque con AX3 es el MISMO problema repetido — la pregunta real no es
"¿qué forma de router?" sino "¿dónde vive físicamente el código que abre el socket?". Hay al menos dos
diseños posibles, y esta nota NO elige entre ellos porque los invariantes actuales no dan suficiente
información para decidir:

- **(a) `serving` solo da forma/decide, otro módulo llama.** `serving.route(request) -> BackendChoice`
  (dato puro, sin red); un módulo distinto (¿`gateway`? ¿un adapter dentro de `protocols`, que sí puede
  hacer red bajo INV-6/authz?) ejecuta la llamada real y le devuelve el resultado a `serving` para que lo
  reempaquete.
- **(b) `serving` expone un `ModelPort` (Protocol) y el CALLER (gateway) inyecta la implementación
  concreta que sí sabe hacer red**, viviendo esa implementación físicamente fuera de `blite.serving` (en
  el módulo del adapter), aunque conceptualmente sea "parte de cómo se sirve un modelo".

Ambas son coherentes con AX3 tal como está escrito (la prohibición es sobre qué **importa** el paquete
`blite.serving`, no sobre qué hace conceptualmente "servir un modelo") — la diferencia es de dónde vive el
código, no de qué invariante se cumple. **Esta nota marca explícitamente que decidir entre (a) y (b)
requiere una sesión conjunta con Dylan** (dueño de `protocols`/`authz`), no una decisión unilateral del
plano de ejecución — los invariantes actuales (AX3, INV-6) restringen SERVING pero no dicen dónde
específicamente debe vivir la implementación de red, y esa ambigüedad es exactamente el tipo de decisión
de frontera que `docs/contract-freeze.md` reserva para coordinación explícita entre planos.

## 2 · Alternativas consideradas

Las 4 formas de §1.3, cruzadas con las 2 opciones estructurales de §1.4 (8 combinaciones en teoría, aunque
no todas tienen sentido — ej. "serving local" combinado con "adapter de producción" es más una cuestión de
DÓNDE corre el modelo que de dónde vive el código de llamada).

## 3 · Por qué no (descartadas, parcialmente)

- **Cualquier forma que haga la llamada de red DENTRO de `blite.serving` — descartada sin ambigüedad.**
  Esto no es una preferencia de esta nota, es una regla ya enforced por `import-linter` (§1.1). Ninguna de
  las 4 formas de §1.3 puede implementarse "de manual" dentro de `serving` sin violar el gate existente.
- **Elegir entre (a) y (b) de §1.4 unilateralmente — descartado deliberadamente.** No es que una opción
  sea peor que la otra según lo que esta nota pudo analizar — es que ninguna de las dos tiene evidencia
  suficiente en los invariantes actuales para preferirla, y la decisión afecta directamente `protocols`/
  `authz` (plano de Dylan). Comprometerse aquí sería exactamente el tipo de decisión unilateral que
  `docs/contract-freeze.md` ya evita mediante las etiquetas `[frontera]`.
- **Modelos registrados en el mismo `Registry` de capabilities (nota 04) — descartada tentativamente:**
  `AnchorKind` (ADR-029/PR2, ya congelado) excluye `"model"` por construcción — un modelo nunca es un
  ancla de verificación. Mezclar los dos registries podría hacer que un consumidor externo (ej. vía el
  adapter MCP de trust/06) confunda "invocar una capability verificable" con "invocar un modelo no
  verificable". Tentativa porque no se confirmó con Dylan.

## 4 · Decisión

| Referencia                                                                                  | Decisión                                          | Racional                                                                                                                                              |
| ------------------------------------------------------------------------------------------- | ------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| Patrón "router + adapter por proveedor" (referencia general, ej. forma tipo LiteLLM)        | **inspirar**                                      | Informa la idea de "una interfaz uniforme sobre múltiples backends de modelo" — no se integra ningún paquete concreto                                 |
| Cualquier llamada de red directa dentro de `blite.serving`                                  | **descartar**                                     | Ya prohibido por el gate `AX3` de import-linter — no es negociable en esta nota, se hereda como restricción dura                                      |
| Serving local tipo Ollama/vLLM como backend válido (no como diseño de dónde vive el código) | **inspirar**                                      | Relevante como UNO de los backends posibles a rutear — no resuelve el problema estructural de §1.4, que aplica igual a llamadas locales               |
| Opción (a) vs (b) de §1.4 (dónde vive la llamada de red)                                    | **sin decidir — punto de coordinación con Dylan** | Los invariantes actuales no dan suficiente información para preferir una sobre otra; decidir unilateralmente sería inapropiado dado que toca su plano |
| Modelos registrados en el mismo `Registry` de capabilities (nota 04)                        | **descartar** (tentativo)                         | AnchorKind excluye "model" por diseño (PR2); pendiente de confirmar con Dylan                                                                         |

## 5 · Tradeoffs

| Eje                                               | Opción (a): serving decide, otro módulo llama                                 | Opción (b): `ModelPort` inyectado por el caller                                                                                                      |
| ------------------------------------------------- | ----------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| Dónde vive el código de red                       | Un módulo nuevo o existente fuera de `serving` (¿gateway? ¿protocols?)        | Fuera de `serving` también, pero como implementación de una interfaz que `serving` define                                                            |
| Quién posee la interfaz de "cómo se ve un modelo" | `serving` (produce una decisión de dato)                                      | `serving` (define el `Protocol`), pero no lo implementa                                                                                              |
| Testabilidad de `serving` en aislamiento          | Alta — `serving` nunca necesita mockear red, solo produce datos               | Alta también — el `ModelPort` se mockea fácilmente en tests de `serving`                                                                             |
| Acoplamiento con `gateway`/`protocols`            | `serving` no conoce a quién le entrega la decisión (bajo acoplamiento)        | El caller conoce la interfaz de `serving` para inyectar la implementación (acoplamiento vía interfaz explícita, patrón de inyección de dependencias) |
| Coherencia con INV-6 (egreso solo por authz)      | Directa si el módulo que llama YA está sujeto a INV-6 (ej. si es `protocols`) | Depende de quién implemente el `ModelPort` — si lo hace algo que no pasa por authz, es un riesgo                                                     |

Sin una decisión conjunta con Dylan, esta nota no puede afirmar cuál de las dos filas es preferible en la
práctica de este repo — ambas son coherentes con AX3 en abstracto.

## 6 · Modos de falla

- **Implementación ingenua que viola AX3 directamente.** El riesgo más obvio: alguien implementa un router
  "de manual" (§1.3) dentro de `blite.serving` con un `import httpx` — esto YA está cubierto por el gate
  de CI (`lint-imports`), así que el modo de falla real no es "pasa desapercibido", sino "bloquea el build"
  — un modo de falla de PRODUCTIVIDAD (el desarrollador se entera tarde, en CI, en vez de en diseño) más
  que de seguridad.
- **Egreso de modelo sin pasar por authz (INV-6).** Si la opción elegida entre (a)/(b) termina poniendo la
  llamada de red en un módulo que NO está sujeto al gate `INV-6` (que hoy solo aplica explícitamente a
  `blite.protocols`/`blite.authz` como `source_modules` del contrato de layers), una llamada de salida a
  un proveedor de modelo podría escapar de la exigencia de autorización que si aplica a otros tipos de
  egreso — un problema de cobertura del gate, no necesariamente de la lógica en sí.
- **Confusión entre "servir localmente" y "sin restricciones de AX3".** Un desarrollador podría asumir
  que, como Ollama/vLLM corren "local" (§1.3, tercera fila), no aplica la misma disciplina de mediación —
  pero el import-linter no distingue destino de red, así que esta confusión produce el mismo bloqueo de
  CI que cualquier otro caso, aunque la intuición de "es local, no debería contar como egreso real" podría
  llevar a alguien a intentar un bypass (ej. usando un socket UNIX en vez de TCP para "evitar" la regla) —
  un riesgo de rodeo del espíritu del invariante, no solo de su letra.

## 7 · Licencias

| Pieza                                                                                               | Licencia      | Verificado                                                                             |
| --------------------------------------------------------------------------------------------------- | ------------- | -------------------------------------------------------------------------------------- |
| Patrón router+adapter (referencia general, ej. LiteLLM-style, forma OpenAI-compatible, Ollama/vLLM) | no verificado | **no verificado en vivo esta sesión** — no se propone integrar ningún paquete concreto |

No se propone ninguna dependencia nueva en esta nota.

## 8 · Impacto en contrato

1. No se fija un contrato concreto de `ModelPort`/router en esta nota — el problema estructural de §1.4
   necesita resolverse ANTES de poder proponer una forma de dato estable, porque cambia qué módulo posee
   la interfaz.
2. Lo único que se fija como restricción (ya derivada de un gate existente, no nueva): ninguna
   implementación de router puede colocar el cliente HTTP dentro de `blite.serving` — esto aplica IGUAL a
   las 4 formas comparadas en §1.3, sin excepción para "serving local".
3. Se señala una dependencia de diseño hacia la nota 01 (pipeline del gateway): si la respuesta a §1.4 es
   la opción (a), el router pasa a ser candidato a etapa del pipeline o a colaborador directo de la etapa
   de despacho — a resolver junto con esa nota.
4. **Esta nota marca explícitamente que no tiene mandato para cerrar esta decisión** — cualquier
   implementación real que asuma (a) o (b) sin la sesión conjunta correspondiente estaría anticipando una
   decisión de frontera.

## 9 · Implicaciones de test / spec

- **Test de arquitectura (ya cubierto por el gate `AX3` existente):** no requiere trabajo nuevo — el
  contrato de import-linter ya verifica esto en cada CI run; esta nota no propone duplicar esa cobertura.
- **Test de cobertura de INV-6 para egreso de modelo:** una vez resuelto §1.4, verificar que CUALQUIERA sea
  el módulo que hace la llamada real al proveedor, esté efectivamente sujeto al contrato de layers `INV-6`
  (hoy solo cubre `protocols`/`authz` explícitamente) — si la opción elegida introduce un módulo nuevo, el
  contrato de import-linter necesitaría extenderse para cubrirlo, lo cual es una implicación directa sobre
  `pyproject.toml` (archivo fuera del alcance de edición de esta sesión, pero identificado como
  consecuencia).
- **Test de mock de `ModelPort` (si se elige la opción b):** un test que verifique que `serving` puede
  operar completamente en aislamiento con una implementación mock del puerto, sin ninguna dependencia de
  red real — valida la separación de responsabilidades independientemente de cuál backend real se use.
- Ninguno de estos tests existe hoy — señalados como trabajo futuro, condicionado a la resolución de §1.4.

## 10 · Supuestos y preguntas abiertas

**Supuestos:**

- Existe más de un backend de modelo a rutear (si solo hubiera uno, "router" sería una capa innecesaria) —
  no confirmado contra ningún requisito de producto real.
- Los modelos NO se exponen a través del mismo `Registry` que las capabilities (§3) — supuesto tentativo,
  no decisión.

**Preguntas abiertas — candidatas a revisión conjunta con Dylan (toca `protocols`/`authz`, su plano; esta
es la nota con la pregunta de mayor bloqueo de toda la carpeta, ver `README.md`, "Cómo revisar esto con
Dylan"):**

- ¿Dónde vive exactamente la llamada de red real a un proveedor de modelo — `gateway`, un adapter dentro
  de `protocols`, o un tercer módulo nuevo no listado en CODEOWNERS hoy? Esta es la pregunta central de la
  nota y no tiene dueño claro todavía entre los dos planos.
- Si la llamada de red vive en `protocols` (plano de Dylan), ¿cómo participa `INV-6` (egreso solo por
  authz) en una llamada de salida a un proveedor de modelo? ¿Se trata como cualquier otro egreso, o
  necesita una categoría propia?
- ¿El router es una etapa del pipeline (nota 01) o vive enteramente dentro de la etapa de despacho hacia
  `serving`? No resuelto.
- ¿Deberían los backends de modelo tener su propio manifest/registry, separado del de capabilities (§3),
  o basta un campo discriminador en el mismo `Registry`? No resuelto.
- ¿"Serving local" (Ollama/vLLM-style) necesita alguna excepción de diseño, o el mismo mecanismo de
  mediación aplica sin cambios sin importar si el destino es local o remoto? Esta nota asume lo segundo
  (§6, "confusión entre servir localmente y sin restricciones") pero no está confirmado.

## 11 · Recomendación mínima de POC

**No se recomienda implementar ningún router real en el POC hasta resolver §1.4.** En su lugar, la
recomendación mínima es un `ModelPort` (Protocol) definido dentro de `blite.serving` con una única
implementación STUB que devuelve una respuesta fija sin tocar red — esto permite que el resto del sistema
(gateway, runtime, notas 01/02/06) se desarrolle e integre contra la INTERFAZ sin bloquearse en la
decisión de dónde vive la implementación real. El POC explícitamente NO debe intentar conectar a ningún
proveedor de modelo real (ni siquiera local) hasta que la sesión con Dylan resuelva §1.4 — hacerlo
requeriría comprometerse a una de las dos opciones estructurales sin la revisión debida.

## 12 · Dirección later / producción

Explícitamente diferida — esta nota no compromete una arquitectura de producción porque la decisión de
frontera (§1.4) no está resuelta. Una vez resuelta, la dirección natural (no comprometida aquí) sería
evaluar en vivo (con licencias y arquitectura verificadas, a diferencia de esta nota) alguna forma tipo
"adapter de serving de producción" (§1.3, última fila) para el módulo que SÍ tenga permiso de hacer la
llamada real, dado que esa forma ya separa por diseño "decidir" de "llamar" y agrega naturalmente rate
limiting/retries/observabilidad — pero esto es una dirección posible, no una decisión.

## 13 · Reconciliación contra la base lógica (`docs/invariants.md`)

- **AX3 (un modelo nunca toca el mundo directo):** INTACTO por diseño — esta nota explícitamente rechaza
  cualquier solución que ponga un cliente de red dentro de `blite.serving`, para las 4 formas comparadas
  en §1.3 sin excepción. El problema sin resolver (§1.4/§10) es DÓNDE vive esa llamada, no SI `serving`
  puede hacerla (no puede, en ningún caso).
- **INV-2 (el verificador nunca es un modelo):** INTACTO — el router decide qué modelo invocar, no
  participa de ninguna decisión de verificación; no hay tensión.
- **PR2 (AnchorKind excluye "model"):** consistente con el supuesto de §3 de mantener modelos fuera del
  `Registry` de capabilities — pero esto es un supuesto de esta nota, no una extensión de PR2 en sí.
- **INV-6 (egreso solo por authz):** pendiente de resolución explícita (ver pregunta abierta, §10, y modo
  de falla, §6) — esta nota NO afirma que el diseño actual lo cumple, porque el diseño del punto de
  llamada de red no está decidido todavía. Se marca como brecha abierta, no como violación confirmada, y
  como el punto de mayor prioridad de coordinación con Dylan de toda esta carpeta.
- **Ninguna referencia contradice la base lógica de forma activa** — el problema identificado es de diseño
  no resuelto por insuficiencia de información en los invariantes actuales, no de un patrón externo en
  conflicto con un invariante.
