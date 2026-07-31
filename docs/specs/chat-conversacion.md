# Spec de costura — Chat y conversación del run (costura A↔E↔D)

**Gobernada por:** freeze **§3** (vocabulario de eventos; extensión aditiva (d) del bloque de
supersedes — decisión #122) + **§14** (catálogo ● — materializa la reserva `●MissionMessage`
de la marca [MEJORADO #102]) + **§2** (rechazo de appends post-terminales — el 409 de abajo es
su cara HTTP) + **§9** (JWT en cookie; el Studio consume proyecciones) + **§13** (cascada de
cancelación) + **§15.7** (replay: la clave jamás repetiría si la vista cargara IDs frescos) ·
`docs/specs/endpoints-studio.md` §"POST /runs — modo misión" (el body que esta spec extiende
aditivamente) · `docs/specs/harness-agentico.md` (loop, `TurnContext`, approvals) ·
`docs/studio/product-model.md` (#78: chat = superficie del project; D6 = hilo sobre eventos,
decisión #93).
**Costura:** A↔E↔D · **Estado:** SPEC (Fase 0 Mejorado, 2026-07-31, decisión #122) ·
**Consumen:** P3 (chat real), P6 (workspaces), P-ui (hilo D6 multi-turno).

> Cierra M1-c/M1-d como contrato (cobertura `docs/mejorado/02-cobertura.md` §1: «cero
> endpoint de mensajes, cero entidad, cero evento `●Message*`»). La implementación es Fase 1
> (P3 lado engine/api, P3-D lado Studio, P6 project) — esta spec fija formas, rutas, códigos
> y semántica; no entrega features. La regla del hilo D6 no cambia: el chat es PRESENTACIÓN
> sobre eventos del stream (decisión #93), jamás un almacén paralelo de mensajes.

## Contrato

**1 · `mission.message` ↔ `●MissionMessage` — el mensaje del usuario como evento del run.**
Materializa la reserva explícita del catálogo §14 ([MEJORADO #102]: «`●MissionMessage`
(`mission.message`) entra cuando M1/P3 lo traiga») — cero supersede nuevo. Payload:

```
{ run_id: str, message_id: str, author: str (URN, regex de §8), text: str (no vacía) }
```

Módulo propuesto: `blite.runtime.mission` (`MissionMessagePayload`, `frozen=True,
extra="forbid"` — misma disciplina que `PlanCreatedPayload`). El evento se apendea al stream
del run con `actor_id = author`; solo se acepta ANTES del evento terminal (§2 ya rechaza
appends post-terminales) ⇒ **queda DENTRO del `provenance_hash`**: la conversación que
dirigió el run es parte de lo que el certificado ampara — no hay chat fuera del amparo.

**2 · `POST /runs/{run_id}/messages` — el emisor HTTP.** Body: `{text: str}` (no vacía,
`extra="forbid"`). `author` NO viaja en el body: lo estampa la identidad del request (hoy
`_API_ACTOR`; C2/M2 lo vuelve el actor del JWT — mismo patrón del flip AX1; el contrato no
cambia cuando eso pase). Respuestas: **`202 {message_id}`** (el efecto vive en el stream,
jamás en la respuesta — mismo principio que `POST /runs`) · `404` run desconocido · **`409`
stream ya terminal** (la cara HTTP del rechazo §2; el cliente enhebra con un run nuevo —
punto 4) · `422` body inválido. El mensaje aceptado se journaliza como `mission.message` y
se encola para el turno siguiente (punto 5) — jamás interrumpe el turno en curso.

**3 · `POST /runs/{run_id}/cancel` — el emisor HTTP que faltaba (N1).** `run.cancelled` ya
está congelado (§3); este endpoint solo le da emisor. Body: `{reason?: str}` (default
`"user_requested"`; el valor `"parent_cancelled"` queda RESERVADO a la cascada del runtime —
§13 regla (i) — y el endpoint lo rechaza con `422`). Respuestas: `202 {}` · `404` · `409` si
el stream ya es terminal. La cascada a sub-runs activos y el barrido de jobs son del runtime
(§13), no del endpoint; un step en RUNNING queda `interrupted` por proyección (§3) — esta
spec no inventa evento nuevo para eso.

**4 · `run.created` gana `thread_id?` y `project_id?` (aditivos — ceremonia #122, marca (d)
en freeze §3).** Semántica:

- `thread_id: str?` — `run_id` del run RAÍZ del hilo conversacional. Ausente ⇒ este run ABRE
  hilo (los runs existentes quedan retro-compatibles: cada uno es su propio hilo). El
  enhebrado post-terminal: como el stream muerto no acepta mensajes (409), continuar la
  conversación = `POST /runs` (modo misión) con `thread_id` del hilo — un run NUEVO con su
  propio stream y su propio certificado; el hilo es correlación de LECTURA (proyección/D6),
  jamás streams anidados (misma doctrina que `parent_run_id`, §2). `thread_id` ≠
  `parent_run_id`: el segundo es jerarquía de sub-runs DENTRO de una corrida; el primero es
  sucesión conversacional ENTRE corridas.
- `project_id: str?` — referencia opaca a la fila relacional `project` de M15 (FUERA del
  event store — decisión #122; el evento NO valida FK contra esa tabla: la valida el API al
  crear el run cuando P6 exista). Ausente ⇒ run sin proyecto (compat total).
- `MissionRequest` (`endpoints-studio.md` §"POST /runs — modo misión") gana los MISMOS dos
  campos opcionales — extensión aditiva del body; `extra="forbid"` intacto.

**5 · `TurnContext.pending_messages` — queue-to-next-turn.** `TurnContext`
(`engine/src/blite/runtime/loop.py`) gana `pending_messages: tuple[PendingMessage, ...] = ()`
(aditivo con default ⇒ compatible), con `PendingMessage = {message_id, author, text}`
(frozen). Regla: los `mission.message` journalizados DESPUÉS de construirse el `TurnContext`
del turno N se drenan al `TurnContext` del turno N+1, en orden de stream — el turno en curso
jamás se interrumpe ni re-planifica a mitad (coherente con «replanificar = steps nuevos»,
`harness-agentico.md` §Contrato-1). El harness deriva la cola del stream (fuente única),
no de un buffer paralelo.

**6 · `PROMPT_PROTOCOL` v2 — historial en la vista del proposer.** La constante
(`api/src/chimera_api/model_proposer.py:55`) pasa de `chimera/mission-proposer-prompt/v1` a
**`chimera/mission-proposer-prompt/v2`**: la vista v1 + un campo nuevo

```
"messages": [ { "author": "user:dylan", "text": "..." }, ... ]
```

— el historial conversacional COMPLETO en orden de stream: la misión como primer mensaje
(`author` = actor del `run.created`) seguida de cada `mission.message` journalizado hasta el
turno. **`message_id` se EXCLUYE de la vista** por la MISMA razón que `run_id` en v1
(`harness-agentico.md` §"Protocolo de mensaje": un ID minteado por request haría que la
clave de replay — freeze §15.7 punto 2 — jamás repitiera entre la sesión grabada y su
reproducción). `author`+`text` en orden de stream SÍ son deterministas entre replays de la
misma conversación. Compat: las sesiones grabadas bajo v1 siguen reproduciendo (el manifest
pinnea digests; el campo `protocol` de la vista discrimina); el adapter emite v2 desde que
P3 lo implemente — no hay doble emisión.

**7 · Wire de approvals — el pin y el espejo Zod (cierra el lado contrato de N2).** Los
payloads y fixtures YA existen (`blite.gateway.approval`, `contract/harness/approval-*.json`,
byte-idénticos ambos lados); lo que faltaba era el espejo Zod del Studio. Esta spec lo
ENTREGA en Fase 0 (es contrato/anti-drift, no feature): `approvalRequestedSchema` /
`approvalRespondedSchema` en `apps/studio/src/data/schemas.ts` + tests que parsean los
fixtures existentes. Pin de nombres de wire = `approval.requested` / `approval.responded`
(freeze §14 [MEJORADO #102]); `response` valida contra el `json_schema` del request en el
lado emisor (`authorize_approval_response`, ya implementado) — el Zod espejo NO re-valida el
`json_schema` (validación semántica del engine, no del wire). La card inline bloqueante y el
`POST` de respuesta del approval son P3/P3-D (Fase 1); el endpoint de respuesta reusa la
maquinaria `override:apply:<scope>` ya congelada (§8/§10) — esta spec no la reabre.

## Eventos / payloads nuevos

- **`mission.message`** ↔ `●MissionMessage` (reserva §14 materializada): payload del punto 1,
  módulo `blite.runtime.mission`.
- **`run.created`** gana `thread_id?`/`project_id?` — aditivos, ceremonia #122 (marca (d) en
  el bloque de supersedes de §3 del freeze).
- **Ningún otro evento nuevo**: cancel reusa `run.cancelled` (congelado), approvals reusan
  `approval.*` (catálogo §14 vía #102), el hilo D6 sigue siendo proyección (decisión #93).

## Interfaces con otros dominios

| Interfaz                                              | Dominio                           | Estado                                                               |
| ----------------------------------------------------- | --------------------------------- | -------------------------------------------------------------------- |
| `mission.message` en el stream + SSE                  | A (emisor) ↔ E (ruta) ↔ D (hilo)  | SPEC — fixture declarado, modelo Fase 1 (P3)                         |
| `POST /runs/{id}/messages` / `POST /runs/{id}/cancel` | E (rutas nuevas) ↔ D (UI de chat) | SPEC — seed xfail                                                    |
| `run.created.{thread_id?,project_id?}`                | A (payload) ↔ E (body) ↔ D (hilo) | SPEC — marca (d) en freeze §3; P3/P6 implementan                     |
| `TurnContext.pending_messages` + `PROMPT_PROTOCOL` v2 | A (loop) ↔ frontera proposer (P4) | SPEC — seed xfail                                                    |
| Zod espejo de `approval.*`                            | D (schemas.ts)                    | **VERDE en Fase 0** (esta sesión) — fixtures existentes, ambos lados |

## Fronteras (qué NO decide esta spec)

- **La UI del chat** (textarea, hilo multi-turno, card de approval, botón cancelar) — P3-D /
  P-ui, sobre los contratos de arriba.
- **La entidad `project` y sus rutas** (`GET /me`, selector) — P6/M15; aquí solo viaja la
  referencia opaca en `run.created`.
- **Quién drena la cola y en qué línea del loop** — el emisor exacto es de la sesión P-rt
  (misma frontera que `harness-agentico.md` declara para sus payloads).
- **El guard del proposer que falla** (P1/M32) — sin él un run vivo puede colgarse, pero esa
  frontera ya está declarada y asignada; esta spec no la duplica.
- **Autenticación** — JWT en cookie ya decidido (§9); las rutas nuevas lo heredan.

## Tests de contrato (fixtures de costura)

- **Existentes (ambos lados, byte-idénticos hoy):** `contract/harness/approval-requested.json`
  / `approval-responded.json` — esta sesión agrega el parse Zod del lado Studio
  (`schemas.test.ts`), cerrando el anti-drift en ambos lados.
- **Declarados (modelo origen aún no existe — Fase 1 los genera, regla del README):**
  `tests/fixtures/contract/harness/mission-message.json` (desde `MissionMessagePayload`,
  generador `gen-contract-fixtures-harness.py` gana el caso) ·
  `tests/fixtures/contract/endpoints/post-runs-mission-thread.json` (body misión con
  `thread_id`/`project_id`, generador `gen-contract-fixtures-endpoints.py` gana el caso) —
  espejados a `apps/studio/src/fixtures/contract/` como siempre.

## Tests semilla

- `tests/seeds/test_seed_chat_conversacion.py` — **SEED, xfail(strict=False)**,
  collection-safe (imports dentro de cada función): forma de `MissionMessagePayload`;
  `TurnContext.pending_messages` con default `()`; `PROMPT_PROTOCOL == ".../v2"`;
  `POST /runs/{id}/messages` → 202 + `mission.message` en el stream y 409 post-terminal;
  `POST /runs/{id}/cancel` → 202 + `run.cancelled`; `run.created` portando
  `thread_id`/`project_id` cuando el body de misión los manda. Verde cuando P3/P6
  implementen cada pieza — el xfail se retira pieza por pieza, jamás se borra el test.
