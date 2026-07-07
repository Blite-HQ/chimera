# Nota 14 — Integración de terceros: evaluación corta de Nango y Composio, descarte del mes, semilla del token vault de Fase 2

**Ítem del backlog (ficha G3):** sub-área de mi fila sin nota — conectores con auth de terceros → evaluación corta → descarte formal + semilla Fase 2 (third-party token vault, conecta con nota 08).
**Fecha:** 2026-07-07 · **Estado:** insumo para el contract freeze (no cambia contrato este mes)
**Fuentes:** Nango (`nango.dev`, `github.com/NangoHQ/nango` — LICENSE, docs de seguridad/self-hosting, issues #900/#5536) y Composio (`composio.dev`, `github.com/ComposioHQ/composio` — LICENSE, docs de connected accounts, issue #291, discussion #1037, post-mortem del incidente de seguridad de mayo 2026) verificados en vivo 2026-07-07 · nota 08 (identidad lite)

---

## 1 · Patrón / mecanismo

### 1.1 Qué resuelven (y por qué Chimera no lo necesita este mes)

Ambos son plataformas de **integración de terceros**: manejan el flujo OAuth/API-key contra cientos de APIs externas, refrescan tokens, y exponen un proxy para llamar esas APIs "en nombre de" un usuario/agente. Es exactamente la pieza que Chimera **no** tiene este mes — una sola capability (`solver.qubo`), cero llamadas salientes a SaaS de terceros, postura air-gapped por diseño (nota 02 §1.2, nota 05). Evaluarlos ahora es evitar reinventar mal en Fase 2 si aparece una capability que sí necesite delegar auth a un servicio externo real.

### 1.2 Nango

- **Qué es:** "Auth para 800+ APIs" — OAuth/API-key/JWT/basic-auth, refresco de tokens, proxy de llamadas, sync de datos opcional. Integraciones definidas como código desplegable, no solo config de dashboard.
- **Vault de tokens:** credenciales cifradas en reposo con **AES-256-GCM**; en self-host, la llave de cifrado la aporta y custodia el operador (a diferencia de Cloud, donde Nango la gestiona). TLS 1.2+ en todo el tráfico. SOC 2 Tipo II, GDPR, HIPAA (BAA bajo pedido).
- **Licencia real:** **Elastic License 2.0 (ELv2)** — NO open source por la definición OSI. Cláusula anti-hosting estándar (prohíbe ofrecer el software como servicio hosteado a terceros). Un issue de la comunidad (#900, "Use of 'Open Source' in advertising") pidiendo corregir el marketing fue cerrado `wontfix` por los mantenedores.
- **Self-host, pero open-core:** el tier gratuito self-hosted es **solo Auth + Proxy** — excluye Functions/syncs, webhooks, servidor MCP, RBAC, SSO/SAML. El feature-set completo exige **Enterprise Self-Hosted** (contrato pago anual + fracción del uso). Un segundo issue (#5536) pidiendo aclarar el alcance exacto del tier gratuito sigue sin respuesta de mantenedores.

### 1.3 Composio

- **Qué es:** plataforma de tool-calling nativa para agentes (vs. el enfoque más genérico de Nango) — "1000+ apps", empaquetado de tools para LangChain/CrewAI/OpenAI Agents SDK/Google ADK/MCP nativo.
- **Vault de tokens:** modelo Auth Config → Connected Account; **las credenciales se guardan del lado del servidor en la infraestructura cloud de Composio incluso cuando el cliente registra su propia app OAuth** — el callback que se registra ante el proveedor es el backend de Composio, así que el token termina en su nube igual. Campos sensibles enmascarados por defecto en las respuestas de API (desenmascarables bajo demanda).
- **⚠️ Hallazgo material — incidente de seguridad mayo 2026** (~6 semanas antes de esta nota): un token OAuth de Gmail de un empleado comprometido escaló hasta ejecución de código arbitrario en un entorno sandboxed; ~0,3% de las conexiones activas comprometidas — **5.001 tokens de GitHub, 12 de Gmail, 5.241 API keys** en una caché auxiliar, más tokens dispersos de 20+ servicios, y un token interno de GitHub con acceso al código productivo. Como respuesta, Composio anunció que construirá un **"Zero Trust Proxy KMS"** para que los clientes custodien sus propias llaves de cifrado — admisión implícita de que el diseño anterior tenía a Composio como único custodio de las llaves de un vault centralizado.
- **Licencia real:** el repo público (`ComposioHQ/composio`, rama `next`) es **MIT**, pero **solo cubre el SDK cliente** — requiere una API key contra `backend.composio.dev`; el backend de auth, el store de connected-accounts y el sandbox de ejecución de tools NO están en ese repo ni son open source.
- **Self-host:** no existe sección de self-hosting en la documentación oficial. Un issue pidiendo on-prem (#291, jul-2024) nunca recibió respuesta de mantenedores; una discussion comunitaria (#1037) especula un self-host con Docker Compose pero concluye que los tokens igual fluyen al cloud de Composio (el callback OAuth sigue siendo el de ellos). Self-hosting real solo existe como conversación de venta enterprise.

### 1.4 El ángulo comparativo

Nango es el modelo arquitectónico más cercano a "un token vault propio detrás de nuestro `KeyProvider`/frontera de identidad" si Fase 2 lo retoma: su repo OSS **es** el motor de auth+proxy (no solo un SDK), define un esquema de cifrado concreto con custodia de llave por el operador, y tiene tooling de self-host real (Helm/ECS/Compose) — aunque el tier gratuito esté deliberadamente recortado. Composio está mejor empaquetado para ergonomía de tool-calling de agentes (LangChain/CrewAI/MCP), pero su store de credenciales real y su sandbox de ejecución son cerrados y permanentemente hosteados por ellos; el MIT solo cubre un wrapper de SDK, y el incidente de mayo 2026 es una demostración en vivo del riesgo sistémico de que un tercero custodie tokens delegados de forma centralizada con sí mismo como único guardián de las llaves — exactamente lo que la postura soberana de Chimera (nota 02, nota 08) busca evitar.

---

## 2 · Decisión

| Referencia   | Decisión                                                | Racional                                                                                                                                                                                         |
| ------------ | ------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Nango**    | **descartar este mes** / candidato de referencia Fase 2 | Sin necesidad hoy (cero SaaS de terceros); ELv2 no es open source real y el tier gratuito self-host excluye justo lo que se necesitaría (webhooks/MCP/RBAC)                                      |
| **Composio** | **descartar** (sin reconsiderar sin auditoría propia)   | El vault de tokens real es cerrado y cloud-only pase lo que pase; incidente de mayo 2026 es la prueba de por qué un vault de terceros centralizado es riesgo sistémico para un proyecto soberano |

Ninguno se integra ni se referencia como dependencia. La semilla de Fase 2 (§4) toma **la forma** de Nango (vault cifrado con llave del operador + proxy que nunca expone el token crudo al caller) como referencia de diseño — no el producto.

## 3 · Licencias

| Pieza                          | Licencia                                                | Verificado 2026-07-07                                     |
| ------------------------------ | ------------------------------------------------------- | --------------------------------------------------------- |
| Nango (self-host OSS)          | **Elastic License 2.0** — no-OSI, cláusula anti-hosting | ✅ en vivo (`LICENSE` del repo + issue #900 sin corregir) |
| Nango Enterprise Self-Hosted   | comercial (contrato)                                    | ✅ en vivo (docs de pricing/self-hosting)                 |
| Composio SDK (repo público)    | **MIT** — cubre solo el cliente, no la plataforma       | ✅ en vivo (`LICENSE`, rama `next`)                       |
| Composio backend/vault/sandbox | cerrado, sin licencia pública (`backend.composio.dev`)  | ✅ en vivo (sin repo, sin self-host documentado)          |

## 4 · Impacto en contrato

**Ningún contrato cambia este mes.** Semilla anotada para Fase 2 (sin forma congelada todavía):

1. **Third-party token vault (Fase 2, si aparece una capability que delega auth a un servicio externo real):** el patrón de referencia es "cifrado con llave custodiada por el operador + proxy que nunca entrega el token crudo al llamador" (la forma self-host de Nango, no el producto) — coherente con la postura soberana ya congelada (nota 02 §1.2: el certificado se verifica offline; misma lógica de "nada crítico depende de un tercero que guarda las llaves").
2. **Conecta con `Identity`/JWT (nota 08):** un token de terceros vaulteado sería, en la forma de esta nota, un secreto más custodiado detrás del mismo puerto `KeyProvider` que la ficha G4 diseña para las llaves del engine (nota 15) — mismo Protocol, backend distinto (secretos de terceros en vez de llaves Ed25519/JWT propias). Señalado como extensión futura del puerto, no decidido.
3. **Sin dependencia nueva.** Ninguna de las dos plataformas se agrega a `contract-freeze.md` §"Dependencias nuevas".

## 5 · Reconciliación contra la base lógica

- **AX3 (mediación, un modelo nunca toca el mundo directamente) / INV-1 (gateway como único chokepoint):** SOPORTADO por la decisión — de integrarse en Fase 2, un token vault de terceros viviría detrás del gateway como cualquier otro adapter de protocolo; nunca como acceso directo desde un agente.
- **AX1 (atribución) / nota 08 (identidad, intersección de permisos):** si Fase 2 delega auth a un tercero, el token delegado hereda la misma disciplina de intersección (`derive()` de nota 08) — el agente nunca obtiene más permiso del que el token de terceros ya tenía acotado. Sin cambio de contrato hoy, principio ya congelado.
- **Ninguna referencia contradice la base lógica.** El incidente de Composio es dato sobre Composio (arquitectura de custodia centralizada de llaves), no sobre nuestra lógica — de hecho la refuerza: es el caso de estudio en vivo de por qué Inv-E y la postura air-gapped existen.
