# Nota 09 — Egress del model router: dónde vive la llamada de red bajo AX3 (propuesta de consolidación)

**Ítem del plan (§4, Steven):** cerrar el punto que la nota 05 dejó explícitamente "sin decidir": dónde
vive físicamente la llamada de red a un proveedor de modelo, verificando en vivo los patrones reales que
la nota 05 solo citó conceptualmente (LiteLLM proxy y SDK, OpenRouter, vLLM server, Ollama local) y
produciendo UNA recomendación compatible con AX3, con el demo dual (cloud = modelo por API, local =
Ollama, MISMO router) y con el freeze.
**Fecha:** 2026-07-14 · **Estado:** investigación de consolidación (Dylan) — pendiente validación y
ratificación de Steven; la decisión estructural es **propuesta de consolidación — pendiente ratificación
de Steven + Dylan (frontera)**, no un contrato cerrado.
**Fuentes:** `pyproject.toml`, contrato import-linter `AX3` (leído en esta sesión: `source_modules =
["blite.serving"]`, `forbidden_modules = ["blite.protocols", "blite.gateway", "blite.runtime",
"blite.authz", "httpx", "requests", "aiohttp", "urllib3", "socket"]`) y contratos `INV-2`
(prohíbe `litellm` en `blite.verification`), `INV-5`, `INV-6`, `Inv-E` · LiteLLM: `BerriAI/litellm`
(`LICENSE` raíz) + `docs.litellm.ai` (`/docs/routing`, `/docs/providers/ollama`) (**verificado en vivo
2026-07-14**) · Ollama: `ollama/ollama` (SPDX + `docs/api/openai-compatibility.mdx`, `docs/openapi.yaml`)
(**verificado en vivo 2026-07-14**) · vLLM: `vllm-project/vllm` (SPDX + README) (**verificado en vivo
2026-07-14**) · OpenRouter: `openrouter.ai/docs` (endpoint unificado) (**verificado en vivo 2026-07-14**) ·
`microsoft/agent-governance-toolkit` — `policy-engine/docs/integrations/litellm-proxy.md` y spec ACS §4
(`pre_model_call`/`post_model_call`) (**verificado en vivo 2026-07-14**, ver nota 08) ·
`knowledge/execution/05` (las 2 opciones estructurales y las 4 formas) · `knowledge/execution/06`
(`execution_profile`) · `docs/contract-freeze.md` (ítem pendiente `ModelServer`, etiqueta `[frontera]`) ·
`docs/invariants.md` (AX3, INV-2, INV-6, Inv-E)

---

## 1 · Patrón / mecanismo

### 1.1 La restricción exacta, releída del gate (no de memoria)

El contrato `AX3` de import-linter prohíbe que `blite.serving` importe `blite.protocols`, `blite.gateway`,
`blite.runtime`, `blite.authz`, `httpx`, `requests`, `aiohttp`, `urllib3` y `socket`. Con
`include_external_packages = true`, un contrato `forbidden` detecta también cadenas indirectas: si
`serving` importara `litellm`, la cadena `litellm → httpx` violaría el gate aunque `litellm` no esté en la
lista. Conclusión operativa: **ningún SDK de cliente de modelo puede vivir en `blite.serving`, ni siquiera
transitivamente** — la nota 05 §1.1 queda confirmada y endurecida.

### 1.2 Los cuatro patrones reales, verificados en vivo

| Patrón                                        | Qué es (verificado)                                                                                                                                                                                                                                                                                                                                                           | Dato clave para esta decisión                                                                                                                                                                                                                          |
| --------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **LiteLLM SDK (`Router`)**                    | Clase Python **in-process**: `model_list` separa `model_name` (alias lógico) de `litellm_params.model` (id del proveedor, ej. `azure/...`, `ollama_chat/...`); estrategias `simple-shuffle` (default), latency-based, usage-based-v2, least-busy, cost-based, custom; retries/cooldowns/fallbacks. **El Router mismo hace las llamadas HTTP** — decidir y llamar viven juntos | Es la traducción multi-proveedor ya resuelta (100+ APIs en formato OpenAI o nativo), sin proceso extra; pero jamás puede importarse desde `serving` (§1.1)                                                                                             |
| **LiteLLM Proxy (AI gateway)**                | Proceso separado con `config.yaml` (`model_list`) y hooks de guardrails — el AGT publica un hook ACS oficial para este proxy que mapea sus hooks a `pre_model_call`/`post_model_call`/`output` y bufferiza streams para evaluar antes de re-emitir                                                                                                                            | La forma "adapter de serving de producción" de nota 05 §1.3 existe y está madura; pero es otro proceso/config fuera del alcance del import-linter (mismo argumento que descartó la opción C de nota 01)                                                |
| **Ollama (serving local)**                    | Servidor local en `http://localhost:11434`: API nativa (`/api/chat`, `/api/generate`, `/api/embed`, …) + **API compatible OpenAI en `/v1/chat/completions` y `/v1/responses`**. LiteLLM lo soporta como un proveedor más (`ollama/` y `ollama_chat/`, este último recomendado; `api_base` default `http://localhost:11434`)                                                   | El backend local del demo dual es alcanzable por el MISMO `model_list` que los proveedores cloud — sigue siendo una llamada HTTP (AX3 no distingue localhost, nota 05 §6)                                                                              |
| **vLLM (serving local/self-hosted a escala)** | Motor de inferencia con "OpenAI-compatible API server, plus Anthropic Messages API and gRPC support" (README)                                                                                                                                                                                                                                                                 | Mismo rol que Ollama pero orientado a GPU/throughput — no aporta nada distinto a ESTA decisión estructural; relevante como backend de producción self-hosted                                                                                           |
| **OpenRouter**                                | API unificada **hosteada y comercial** en `https://openrouter.ai/api/v1/chat/completions` — un solo endpoint que rutea a múltiples proveedores                                                                                                                                                                                                                                | Terceriza el ruteo (nuestro diferenciador de mediación) a un intermediario cloud; incompatible con el lado local/air-gapped del demo dual; si algún despliegue lo quisiera, es alcanzable como un proveedor más del `model_list`, sin soporte especial |

### 1.3 La propuesta: opción (b) de la nota 05 §1.4, con la implementación viviendo en `blite.protocols`

Las dos opciones estructurales de la nota 05 (§1.4) eran: (a) `serving` decide y otro módulo llama; (b)
`serving` define un `ModelPort` (Protocol) y el caller inyecta la implementación que sí hace red. Esta
nota propone **(b), con la implementación de red viviendo en `blite.protocols` como un adapter de egreso
de modelo**:

1. **`blite.serving` = router puro + dueño del puerto.** Define `ModelPort` (Protocol) y la decisión de
   ruteo como dato (`route(request) -> BackendChoice`); cero red, cero clientes (AX3 intacto por
   construcción). Testeable en aislamiento con un stub (exactamente el POC que la nota 05 §11 recomendó).
2. **La implementación (`ModelServer`, el nombre que `docs/contract-freeze.md` ya reserva en su lista de
   correcciones pendientes) vive en `blite.protocols`.** Verificación contra los contratos existentes: nada
   prohíbe `protocols → serving` (Inv-E solo le prohíbe `verification`/`guardrails`; INV-6 lo pone encima
   de `authz`), y `serving` nunca importa `protocols` (la flecha va en un solo sentido — o en ninguno, si
   se usa tipado estructural de `Protocol`). Al vivir en `protocols`, **el egreso de modelo queda
   automáticamente bajo el contrato de layers INV-6 (protocols exige authz)** — esto cierra el modo de
   falla "egreso de modelo sin pasar por authz" que la nota 05 §6 señaló, sin extender el import-linter.
3. **El gateway cablea.** La etapa de despacho (nota 01, etapa 5) obtiene la decisión de `serving.route()`
   y la ejecuta a través del `ModelPort` inyectado — el precedente externo es directo: el AGT gobierna
   `pre_model_call`/`post_model_call` como cruce de frontera explícito mediado por el host (nota 08 §1.1),
   nunca deja que la capa de modelo alcance el mundo por su cuenta.
4. **Dentro del adapter, LiteLLM SDK (`Router`) como mecanismo de traducción multi-proveedor.** Un
   `model_list` único con entradas cloud (proveedor por API) y local (`ollama_chat/...` →
   `localhost:11434`); el `DistributionManifest` (trust/06 §1.2, potestad de Dylan) selecciona por
   despliegue qué entradas están activas — **mismo router, misma forma, los dos lados del demo dual**,
   consistente con el patrón `execution_profile` de la nota 06 (el empaquetado es perfil de despliegue,
   no contrato).

Qué se decide y qué no: esta nota **propone** (b)+`protocols`+LiteLLM-SDK como consolidación; **no** lo
congela. La nota 05 estableció que elegir entre (a) y (b) toca el plano de Dylan (`protocols`/`authz`) —
por eso el estado de esta nota es propuesta pendiente de ratificación conjunta, y el POC de la nota 05 §11
(stub de `ModelPort` sin red) sigue siendo el paso seguro mientras tanto.

## 2 · Decisión

| Referencia                                                                                             | Decisión                                                                                         | Racional                                                                                                                                                                                                 |
| ------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Opción (b) de nota 05 §1.4 (`ModelPort` en `serving`, impl inyectada) con la impl en `blite.protocols` | **portar** — **propuesta de consolidación, pendiente ratificación de Steven + Dylan (frontera)** | Única combinación que deja AX3 intacto por construcción Y pone el egreso de modelo bajo INV-6 sin extender gates; testabilidad de `serving` en aislamiento (nota 05 §5)                                  |
| LiteLLM **SDK** (`Router`) dentro del adapter de `protocols`                                           | **integrar** (condicionado a la ratificación de arriba; pinear versión; excluir `enterprise/`)   | Traducción a 100+ proveedores ya resuelta bajo MIT, incluyendo Ollama local — un solo `model_list` cubre el demo dual; escribir adapters httpx a mano por proveedor sería reinventarlo                   |
| LiteLLM **Proxy** (proceso separado)                                                                   | **descartar** este mes / dirección de producción                                                 | Otro proceso + config fuera del import-linter (mismo racional que nota 01 §3-C); su madurez (hooks ACS del AGT) lo hace candidato natural cuando haya necesidad operativa real                           |
| Ollama como backend local del demo dual                                                                | **integrar** (como backend a rutear, no como código del repo)                                    | MIT; `localhost:11434` + compat OpenAI; soportado por LiteLLM como proveedor (`ollama_chat/`) — el lado local del demo sin código especial                                                               |
| vLLM                                                                                                   | **descartar** este mes / backend self-hosted de producción                                       | Apache-2.0, server compatible OpenAI verificado; no cambia la decisión estructural y su costo operativo (GPU) no aporta al demo                                                                          |
| OpenRouter                                                                                             | **descartar** como pieza de arquitectura                                                         | Ruteo tercerizado a un intermediario cloud comercial: cede el diferenciador de mediación y rompe el lado local/air-gapped; alcanzable como un proveedor más del `model_list` si un despliegue lo pidiera |
| Llamada de red dentro de `blite.serving` (cualquier forma, incluso vía `litellm` transitivo)           | **descartar**                                                                                    | Gate AX3 ya la bloquea, incluida la cadena `litellm → httpx` (§1.1) — se hereda como restricción dura                                                                                                    |
| Modelos dentro del `Registry` de capabilities                                                          | **descartar** (ratifica lo tentativo de nota 05 §3)                                              | `AnchorKind` excluye `model` (PR2); el `ModelPort` es un puerto distinto del puerto `Capability`, sin mezcla de registries                                                                               |

## 3 · Licencias

| Pieza                       | Licencia                                                                                                                                                                                 | Verificado                                                                                                                                 |
| --------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| LiteLLM (`BerriAI/litellm`) | **MIT**, con carve-out explícito: todo lo bajo `enterprise/` queda bajo `enterprise/LICENSE` (comercial) — el SPDX del repo reporta `NOASSERTION` por esa dualidad; el texto raíz es MIT | ✅ en vivo 2026-07-14 (`LICENSE` raíz leído completo) — al integrar: no importar nada de `enterprise/`                                     |
| Ollama                      | **MIT**                                                                                                                                                                                  | ✅ en vivo 2026-07-14 (SPDX del repo)                                                                                                      |
| vLLM                        | **Apache-2.0**                                                                                                                                                                           | ✅ en vivo 2026-07-14 (SPDX del repo)                                                                                                      |
| OpenRouter                  | servicio hosteado comercial — sin licencia OSS aplicable (no hay software que integrar)                                                                                                  | ✅ en vivo 2026-07-14 (docs del endpoint)                                                                                                  |
| LiteLLM Proxy (mismo repo)  | mismo MIT + carve-out; features de gateway "enterprise" caen bajo la licencia comercial                                                                                                  | ✅ en vivo 2026-07-14 — **PENDIENTE** delimitar qué features exactas del proxy son enterprise si Fase 2 lo retoma (no se integra este mes) |

## 4 · Impacto en contrato

1. **Resuelve (como propuesta) el ítem `ModelServer` que `docs/contract-freeze.md` deja pendiente en su
   lista de correcciones de Steven:** forma propuesta — `ModelPort` (Protocol, definido en
   `blite.serving`: firma mínima `complete(request) -> ModelResponse`, sin red) + `ModelServer` (la
   implementación en `blite.protocols`, envolviendo LiteLLM `Router`). Etiqueta `[frontera]`: el puerto es
   mecánica de Steven, la implementación vive en el plano de Dylan — requiere el visto de ambos ANTES de
   entrar al freeze.
2. **Ningún gate de import-linter necesita cambio para que la propuesta funcione** (verificado contra los
   contratos leídos en esta sesión). Endurecimiento opcional recomendado (edición futura de
   `pyproject.toml`, fuera del alcance de esta nota): agregar `litellm`, `openai`, `anthropic` a los
   `forbidden_modules` de `AX3`, para que la prohibición de clientes de modelo en `serving` sea explícita
   y no dependa solo de la detección transitiva vía `httpx`.
3. **Dependencia nueva implicada (si se ratifica):** `litellm` (MIT, carve-out enterprise) — entraría a la
   tabla "Dependencias nuevas" del freeze con la anotación de pineo y exclusión de `enterprise/`. Ollama
   NO es dependencia del repo (es un proceso externo del entorno local, como Postgres).
4. **Demo dual sin bifurcación de código:** el `model_list` único (cloud + `ollama_chat/`) seleccionado
   por despliegue conecta con la potestad ya congelada del `DistributionManifest` de sobreescribir perfiles
   por despliegue (trust/06 §1.2, nota 06) — no se crea ningún mecanismo nuevo de configuración.
5. **Pregunta abierta que esta nota NO cierra (vocabulario de eventos, plano de Dylan):** si la llamada a
   modelo emite eventos propios (¿`model.call.requested/completed`?) o se registra como parte del step que
   la contiene (nota 07). El precedente AGT (`pre_model_call`/`post_model_call` como puntos gobernados)
   sugiere rastro propio, pero el vocabulario es frontera — a resolver en la misma sesión de ratificación.

## 5 · Reconciliación contra la base lógica

- **AX3 (un modelo nunca toca el mundo directo):** INTACTO por construcción — `serving` queda como router
  puro sin cliente de red ni transitivo (§1.1); la llamada real vive fuera, inyectada, exactamente como el
  axioma exige ("`serving` may be _called by_ the gateway, but must not itself reach… the network").
- **INV-6 / Inv-E (egreso solo por authz, nunca por verificación):** REFORZADOS — al colocar `ModelServer`
  en `blite.protocols`, el egreso de modelo hereda el contrato de layers INV-6 (protocols exige authz) sin
  gate nuevo, cerrando la brecha que la nota 05 §13 dejó marcada como "pendiente de resolución explícita";
  e Inv-E sigue aplicando (protocols no puede importar verification/guardrails, así que ningún verdict
  puede fabricar el egreso de una llamada de modelo).
- **INV-2 / PR2 (el verificador nunca es un modelo):** INTACTOS — el gate INV-2 ya prohíbe `litellm` en
  `blite.verification` (leído en vivo del `pyproject.toml`), de modo que integrar LiteLLM en `protocols` no
  acerca ningún cliente de modelo al verificador; `AnchorKind` sigue sin `model` y los modelos siguen fuera
  del `Registry` de capabilities.
- **INV-1 (gateway único chokepoint):** REFORZADO — la llamada a modelo se ejecuta únicamente desde la
  etapa de despacho del pipeline (nota 01), con el precedente externo del AGT gobernando ese mismo cruce
  (`pre_model_call`/`post_model_call`); ni `serving` ni el adapter son punto de entrada alternativo.
- **AX1 (atribución):** SOPORTADO, con la pregunta abierta de §4.5 — cualquier evento que la llamada de
  modelo termine emitiendo llevará `actor_id` como todo evento; el vocabulario exacto es frontera y no se
  anticipa aquí.
- **Ninguna referencia contradice la base lógica.** El único patrón en tensión real (OpenRouter: ruteo
  delegado a un tercero hosteado) se descarta precisamente por esa tensión con la postura de mediación
  soberana; LiteLLM/Ollama/vLLM encajan como mecanismo detrás de nuestros puertos, no como autoridad de
  decisión.
