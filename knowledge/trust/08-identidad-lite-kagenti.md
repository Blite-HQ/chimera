# Nota 08 — Identidad lite: forma SPIFFE + delegación RFC 8693 + intersección de permisos, sin SPIRE

**Ítem del plan (§4 Dylan):** Identidad lite — JWT claims scoped + intersección de permisos (forma SPIFFE/RFC 8693 sin SPIRE); nota de diseño
**Fecha:** 2026-07-03 · **Estado:** **EJECUTADA (2026-07-24)** — `engine/src/blite/identity/{identity,derive}.py` (campo `spiffe_id` reservado, delegación `act`) + `authz/decision.py` (`AuthzDecision`).
**Fuentes:** Kagenti verificado en vivo 2026-07-03 (Apache-2.0, "Identity and Auth Bridge") · compass panorama (patrón Kagenti detallado, AgentCore Identity, Entra Agent ID) · Revisión de arquitectura de referencia de Chimera (ADR-018) · RFC 8693 (OAuth Token Exchange) · semilla TS §1

---

## 1 · Patrón / mecanismo

### 1.1 El patrón de referencia (Kagenti / Red Hat) — dos capas de identidad

El diseño emergente más citado para identidad de agentes (compass; repo verificado):

1. **Identidad de workload** — _quién es este proceso/agente_: SPIFFE ID (`spiffe://trust-domain/path`, URN estable) emitido por SPIRE como SVID (X.509/JWT) con mTLS y rotación automática.
2. **Delegación del usuario** — _en nombre de quién actúa_: OAuth **Token Exchange (RFC 8693)** vía Keycloak — el agente intercambia el token del usuario por un JWT **scoped** que registra la cadena de delegación.
3. **Permission intersection** (⚠️ del compass, no verificable en el README): "los agentes solo pueden reducir permisos del usuario, nunca expandirlos". Un componente AuthBridge (sidecar) hace el exchange.

Referencias cruzadas del mismo patrón: **AgentCore Identity** (token vault; valida token de usuario → emite _workload access token_; audit trail que mantiene contexto del usuario) y **Entra Agent ID** (identidad dedicada por agente, blueprints con relaciones padre-hijo). Convergencia total de la industria: **identidad propia por agente + delegación que solo atenúa**.

Limitación conocida de SPIRE (compass): exige pre-registro de workloads — mala adaptación a sub-agentes efímeros. Otra razón para diferirlo: nuestros agentes del hackathon son efímeros por diseño.

### 1.2 ADR-018: capacidades atenuables, no booleanos

Los flags booleanos (`canCallTools`, `canUseNetwork`) son demasiado gruesos para una Ley: no expresan "qué herramientas, sobre qué datos, bajo qué condiciones". El modelo correcto: **permisos como conjunto de capacidades nombradas** (`{"capability:solver.qubo:invoke", "capability:sim.powerflow:invoke"}`) que en delegación solo se **interseca** — jamás se une. La semilla TS ya apuntaba ahí (`permissions: ReadonlySet<string>` + `requiredPermission` en el manifest); esta nota lo confirma y le da la semántica de delegación.

**El mismo principio ya está enforzado en el repo** a nivel de tooling: el invariante de sub-agentes (`tests/invariants/test_subagent_permissions.py` — un sub-agente solo declara un subconjunto del superset permitido). La identidad lite es ese principio elevado a contrato de runtime.

### 1.3 Diseño lite para el freeze (sin SPIRE, sin Keycloak)

**Forma del JWT** (emitido/verificado por el propio engine con llave local — coherente con air-gap):

```json
{
  "iss": "chimera",
  "sub": "user:dylan", // URN estable estilo SPIFFE ID (AX1a)
  "kind": "human", // human | agent | service
  "domain_id": "d-default", // AX1b — frontera de confianza
  "permissions": ["capability:solver.qubo:invoke", "run:create"],
  "act": { "sub": "agent:planner-7" }, // RFC 8693: cadena de delegación (quién actúa)
  "iat": 1780500000,
  "exp": 1780503600
}
```

- **`sub` = URN estable** (`user:dylan`, `agent:planner-7`, `service:api`): la forma SPIFFE sin la infra SPIFFE. Cuando llegue SPIRE (Fase 2), el URN mapea al path del SPIFFE ID y `spiffe_id` (campo ya presente en la semilla) se llena — sin migración de contrato.
- **`act` (actor claim, RFC 8693):** cuando un agente actúa en nombre de un usuario, el token derivado conserva `sub` del principal y encadena `act` — la atribución es del par (principal, actor), y el evento registra al **actor efectivo** con la cadena en el payload. Delegaciones anidadas anidan `act`.
- **Intersección en la derivación** (función pura, testeable):
  `permissions(token_derivado) = permissions(token_padre) ∩ permissions_declaradas(delegado)`
  Nunca unión, nunca escalada — imposible por construcción, con property-test (Hypothesis) de que la derivación jamás produce un permiso ausente en el padre.
- **Chequeo en authz (etapa 2 del gateway):** `manifest.required_permission ∈ permissions(token)` + el dominio permite (AX1b). El diseño conecta con `CapabilityManifest.required_permission` (nota 06).

### 1.4 La ruta para voltear el xfail de AX1

Hoy: `test_event_has_non_null_actor_id` es xfail porque ni `Event` tiene `actor_id` ni existe quién lo estampe. Ruta concreta:

1. **Freeze (viernes):** `Event.actor_id` obligatorio (nota 01) + contrato `Identity`/JWT (esta nota).
2. **Post-freeze:** módulo `identity` verifica el JWT y produce `Identity`; la etapa 1 del pipeline (carril Steven, contrato nuestro) la estampa en el contexto; el `EventStore.append` la exige (parámetro no-opcional).
3. **Flip:** el xfail se voltea a aserción real ("todo evento tiene actor_id no vacío") — nunca se borra (regla del invariante). Los eventos emitidos fuera de un request (bootstrap, jobs) usan identidades de servicio (`service:runtime`), no strings vacíos.

### 1.5 Honestidad OWASP (qué cubre el lite y qué NO)

| Riesgo (OWASP Agentic Top 10)              | ¿Cubierto por el lite?                                                 |
| ------------------------------------------ | ---------------------------------------------------------------------- |
| Identity abuse / privilege compromise      | ✅ intersección + required_permission + URN por actor                  |
| Acciones anónimas                          | ✅ AX1: actor_id obligatorio en todo evento                            |
| Excessive agency                           | ✅ parcial: permisos nombrados por capability (no booleanos)           |
| Workload impersonation (proceso a proceso) | ❌ sin mTLS/SVIDs — Fase 2 (SPIRE)                                     |
| Token theft / replay largo                 | ❌ parcial: exp corto sí; rotación/attestation de workload no — Fase 2 |
| Memory poisoning / tool misuse             | fuera de esta capa (gateway/guardrails/verificación)                   |

Esta tabla va al pitch técnico si preguntan "¿y la seguridad?" — decir qué no cubrimos es la postura de la arquitectura de referencia de Chimera ("la honestidad como postura de seguridad").

## 2 · Decisión

| Referencia                             | Decisión                                                            | Racional                                                               |
| -------------------------------------- | ------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| Forma SPIFFE ID (URN estable)          | **portar** (el formato URN sin la infra)                            | Migración limpia a SPIRE en Fase 2; campo `spiffe_id` ya reservado     |
| SPIRE / SVIDs / mTLS                   | **descartar** este mes (Fase 2, ya decidido en plan §1.E.3)         | Infra pesada; pre-registro choca con agentes efímeros                  |
| RFC 8693 (claim `act`, token exchange) | **portar** (el claim y la semántica de derivación, sin Keycloak)    | Estándar IETF; representa la cadena de delegación en el propio token   |
| Kagenti                                | **inspirar** (arquitectura de referencia de dos capas + AuthBridge) | Apache-2.0; su implementación es K8s-céntrica                          |
| AgentCore Identity / Entra Agent ID    | **inspirar** (token vault / blueprints padre-hijo → Fase 2)         | Cerrados; confirman el patrón, no aportan código                       |
| Intersección de permisos (ADR-018)     | **portar** (función pura + property-test)                           | Ya es principio enforzado en el repo (sub-agentes); se eleva a runtime |
| PyJWT                                  | **integrar** (dependencia para firmar/verificar JWT)                | MIT ⚠️ (confirmar al agregarla); estándar de facto en Python           |

## 3 · Licencias

| Pieza        | Licencia                                     | Verificado            |
| ------------ | -------------------------------------------- | --------------------- |
| Kagenti      | **Apache-2.0**                               | ✅ en vivo 2026-07-03 |
| SPIFFE/SPIRE | Apache-2.0 ⚠️ (Fase 2; verificar entonces)   | —                     |
| Keycloak     | Apache-2.0 ⚠️ (no se integra)                | —                     |
| RFC 8693     | documento IETF (sin licencia de código)      | —                     |
| PyJWT        | MIT ⚠️ (verificar al agregar la dependencia) | —                     |

## 4 · Impacto en contrato

Contra la semilla TS §1 y el stub actual (`engine/src/blite/identity/__init__.py` vacío):

1. **`Identity`** (Pydantic): `id: str` (URN validado por regex `^(user|agent|service):[a-z0-9-]+$`), `kind: Literal["human","agent","service"]`, `domain_id: str`, `permissions: frozenset[str]`, `spiffe_id: str | None = None` (Fase 2). Igual a la semilla + validación de forma del URN.
2. **Forma del JWT** (§1.3) congelada: claims `iss/sub/kind/domain_id/permissions/act/iat/exp`; firma con llave local del engine (HS256 o Ed25519 — decidir en implementación; la llave comparte gestión con la del certificado, nota 02).
3. **Derivación de identidad** (nuevo contrato): `derive(parent: Identity, requested: frozenset[str]) -> Identity` con intersección garantizada + property-test.
4. **`Event.actor_id` obligatorio** (nota 01) — el destino del dato de esta nota; payload lleva la cadena `act` cuando hay delegación.
5. **Etapa identity del gateway** (frontera con Steven): consume este contrato, estampa `Identity` en `InvocationContext`; la mecánica del pipeline es suya.
6. **Plan del flip AX1** (§1.4): queda escrito como criterio de la sesión de construcción post-freeze.
7. **Tabla `identities`** (semilla §3): confirmada sin cambios (ya tiene kind/domain/permissions/spiffe_id).

## 5 · Reconciliación contra la base lógica

- **AX1 (toda acción atribuible a exactamente un actor):** REALIZADO — URN obligatorio + `act` chain resuelve la ambigüedad "¿el usuario o su agente?": el actor efectivo es el que ejecuta; el principal queda en la cadena. Nunca anónimo.
- **AX1b (dominios sellados):** SOPORTADO — `domain_id` en el token y en cada evento; canales entre dominios siguen siendo la única vía de cruce (semilla §2, sin cambios).
- **Principio de sub-agentes del repo (intersección):** MISMO principio, dos niveles — tooling (ya enforzado) y runtime (este contrato). Se referencian mutuamente en docs.
- **Inv-E/INV-6:** INTACTOS — la identidad alimenta a authz; nada de esta capa toca egreso directamente.
- **Ninguna referencia contradijo la base lógica.** SPIRE exigiendo pre-registro contradice nuestros agentes efímeros — dato sobre SPIRE (por eso se difiere), no sobre AX1.
