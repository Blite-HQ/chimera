# Nota 09 — MS Agent Governance Toolkit de primera mano: audit log, policy engine, identidad, plugin signing (mi mitad)

**Ítem del backlog (ficha A0):** la referencia central del pool jamás estudiada de primera mano (todo venía de los compass). Mi mitad: audit log tamper-evident · policy engine determinista · identidad Ed25519/DID · plugin signing+SBOM. La otra mitad (pipeline, capability model) es de Steven — su nota **aún no existe** (`knowledge/execution/` vacío al 2026-07-07), así que acá no hay delta que restar; lo que roza su carril queda señalado, no decidido.
**Fecha:** 2026-07-07 · **Estado:** estudio de primera mano completo; alimenta el anexo de canonicalización del freeze (G2)
**Fuentes:** `microsoft/agent-governance-toolkit` clonado en `pool/` (HEAD `54a2c52`, 2026-07) — código y specs leídos en vivo · notas 01/02/05/08 (para los deltas) · `docs/contract-freeze.md`

---

## 1 · Patrón / mecanismo

Contexto en una línea: el AGT es un toolkit de gobernanza para agentes ("policy enforcement, identity, sandboxing, SRE"), MIT, Public Preview, monorepo con SDKs en 8 lenguajes + un motor de políticas en Rust (`policy-engine/`). Su tesis coincide con la nuestra en el chokepoint: _"Actions the AGT kernel denies are not 'unlikely'. They are structurally impossible."_ — enforcement determinista fuera del alcance del modelo (nuestro AX3).

### 1.1 Audit log tamper-evident (la referencia del ADR-016, ahora verificada)

**Forma** (`agent-mesh/src/agentmesh/governance/audit.py` + spec `docs/specs/AUDIT-COMPLIANCE-1.0.md`): hash-chain + Merkle tree por encima.

- **Entrada** (`AuditEntry`): `entry_id`, `timestamp`, `event_type`, `agent_did`, `action`, `resource`, `data`, `outcome`, `policy_decision`, `matched_rule`, `previous_hash`, `entry_hash`, más contexto (`trace_id`, `sandbox_id`…).
- **Encadenamiento:** `previous_hash` = `entry_hash` de la entrada anterior; génesis = `""` (Python) — pero `"0"*64` en TypeScript y ventana acotada con `seam_hash` en TS/Rust (evicción con re-anclaje). El `entry_hash` incluye `previous_hash` → cadena.
- **Canonicalización del hash (spec §4.4):** subset FIJO de 9 campos → _"Serialize to JSON with keys sorted alphabetically and no extra whitespace"_ → SHA-256 hex lowercase → verificación con `hmac.compare_digest` (timing-safe).
- **Merkle** encima de los `entry_hash` (concatenación de strings hex, padding `"0"*64`): inclusion proofs por entrada + root — la forma transparency-log que nota 01 anticipó como Fase 2.
- **Persistencia** (`audit_backends.py`): `SignedAuditEntry` con `content_hash` + **HMAC-SHA256** (llave simétrica del operador) — no Ed25519; un tercero sin el secreto no puede verificar. Export a **CloudEvents v1.0** (`to_cloudevent()`) — costura limpia audit→eventing/OTEL (señalar a Geovanni).

**Los tres hallazgos que importan (verificados en vivo):**

1. **Spec e implementación de referencia NO producen los mismos bytes.** §4.4 exige "no extra whitespace"; la impl usa `json.dumps(data, sort_keys=True)` — separadores default de Python (`", "`, `": "`), CON espacios. Lo reproduje: mismo dict, hash spec-compliant `a9ac…` vs hash de la impl `ce3d…`. Dos implementaciones honestas del mismo spec no se verifican entre sí.
2. **Cada SDK tiene una canonicalización incompatible.** Python: JSON 9 campos ordenados; TypeScript (`src/audit.ts`): `JSON.stringify` en **orden de inserción** con otro set de campos (`agentId`, `decision`, `skillAuditMetadata`); Rust (`agentmesh/src/audit.rs`): ni siquiera JSON — string con pipes `seq|timestamp|agent_id|action|decision|prev_hash`. Cero verificación cruzada posible. Su propio módulo JCS lo admite: _"a digest computed here always reproduces here"_.
3. **Evolución de esquema vs cobertura del hash (spec §4.3.1):** los campos nuevos de v1.0 (`arguments_hash`, `approver_did`, `policy_version`, `issued_at`, `completed_at`) quedaron FUERA del hash canónico para no romper cadenas viejas — con advertencia explícita: _"a tampering party can mutate them without invalidating entry_hash… MUST NOT rely on these fields for tamper detection"_. La versión con selector de esquema recién llega en v1.1.

**La pieza madura del repo:** `ActionBinding` (ADR-0030, `governance/approval_protocol/`): cada aprobación humana se liga al **digest de la acción exacta** — `sha256:<hex>` sobre **RFC 8785 JCS** (subset vendoreado propio, ~100 líneas: orden por code units UTF-16, separadores compactos, UTF-8 literal, NaN/Inf rechazados, caveat documentado de paridad float) con `schema_version` DENTRO del payload hasheado. Donde la reproducibilidad del digest era requisito real, convergieron a JCS.

**¿La ficha A0 preguntaba si esto resuelve G2 de paso?** No: lo que resuelve G2 es la **lección negativa** (hallazgos 1–3 = exactamente la muerte de la verificación offline que G2 previene) más la **validación positiva** de JCS vía ADR-0030. El anexo del freeze la ejecuta.

**Delta vs nota 01:** confirmado que el AGT es la referencia implementable del hash-chain (forma `hash = H(canónico ‖ prev)` + Merkle para proofs, génesis `""`), y confirmada la licencia MIT que la nota 01 tenía como "⚠️ per compass". Lo que la nota 01 no sabía: la canonicalización del AGT **no se porta** (hallazgos 1–2), y la ventana acotada con `seam_hash` de TS/Rust rompe la verificación de historia completa — nuestro log Postgres completo (INV-5) es más fuerte en eso por diseño.

### 1.2 Policy engine determinista (contraste con `VerificationPolicy`)

Hay **dos motores**, no uno:

- **ACS core** (`policy-engine/core/`, Rust, spec normativo propio): PDP puro, _"stateless, deterministic, fail closed"_ por contrato — mismo manifest + snapshot ⇒ mismo verdict; **todo error ⇒ deny** con vocabulario de razones reservadas (`runtime_error:tool_unknown`, `:policy_output_invalid`, `:resource_limit_exceeded`…). 8 intervention points; el host es el PEP y adelanta budgets en el snapshot (el engine no guarda estado). La lógica vive en Rego/Cedar bindeados por manifest YAML versionado (`extends` remotos con pin SHA-256 obligatorio estilo SRI). Por cada evaluación deriva `input_identity`/`enforced_identity` = `sha256:` del **policy input canónico** (spec §8: keys ordenadas en todo nivel) — la llave estable que ata decisión ↔ snapshot exacto; la aprobación humana de una escalación se liga a `enforced_identity`.
- **agentmesh `PolicyEngine`** (`governance/policy.py`, el que usa `govern()`): reglas YAML declarativas (`match`/`condition` DSL + `action: allow|deny|warn|require_approval|log` + `priority`), **default-deny sin políticas cargadas**, error evaluando una condición ⇒ se trata como match (para que su deny aplique), resolución de conflictos configurable (`deny_overrides` por default en `govern()`).

**El patrón que valida nuestra base:** la capa probabilística (`advisory`: clasificadores/LLM) corre **solo después** de un allow determinista y falla **abierta**, marcada `"deterministic": False` en el audit — "detection is probabilistic, enforcement stays deterministic" hecho código. Es nuestro D18/D21/INV-3 confirmado por la industria, ahora de primera mano y no vía compass.

**Registro de decisiones:** cada evaluación audita `policy_evaluation` con `matched_rule` + `policy_name`; `govern()` computa `sha256` del **bundle** de política al cargar y lo estampa en un TRACE Trust Record **firmado Ed25519** al cierre de sesión; las aprobaciones ADR-0030 quedan ligadas a `policy_version` (_"so an approval is bound to the policy revision in effect when granted"_).

**Delta vs nota 05:** `VerificationPolicy` sale reforzada, sin cambios de forma. (a) Nuestro `policy_id`+`digest` en `verification.completed` es exactamente su bundle-hash estampado — congelado bien. (b) Su vocabulario de verdicts (`allow|deny|warn|escalate|transform`) es del plano authz, no colisiona con nuestro tri-estado de verificación; su `escalate` ≈ nuestro `escalate_human`. (c) Idea nueva a robar en Fase 2: **razones reservadas de fallo-cerrado** como vocabulario cerrado (nuestro `on_inconclusive` podría fallar con razones tipadas, no strings). (d) La atadura aprobación↔digest de acción (ADR-0030) es la semilla exacta para ligar la attestation rung 7 y el `OverrideEvent` al `claim_digest` — nuestra `Attestation.subject.claim_digest` ya lo permite; el anexo G2 define ese digest.

### 1.3 Identidad Ed25519/DID (delta vs nota 08)

- **DID custom, no derivado de llave:** `did:mesh:<32 hex aleatorios>` — el identificador **sobrevive rotaciones** (el DID no cambia cuando rota la llave; la llave vieja firma la nueva con prefijo de dominio `"rotate:"`). Coexisten `did:nexus:<nombre-legible>` (otro subsistema, otro formato) y una capa **SPIFFE paralela** (`spiffe://{trust_domain}/agentmesh/{agent}` mapeado 1:1 al DID + SVID X.509 por CA propia).
- **Llaves:** Ed25519 con `cryptography` (nuestra misma elección de lib), pública = raw 32 bytes en base64 (Nexus le antepone `"ed25519:"`), export JWK (`kty: OKP`); keystore como Protocol con backends Software/PKCS#11/TEE y rotación con TTL e historial.
- **Delegación:** identidades hijas con **subset estricto de capabilities** (wildcard prohibido de propagar), profundidad máx. 10, `get_effective_capabilities()` = **intersección a lo largo de toda la cadena**, y "lineage-bound trust" (el hijo no puede nacer con más confianza que el padre — anti-Sybil). Sin RFC 8693: su on-behalf-of es un `UserContext` casero que viaja en payloads firmados.
- **Enforcement:** el kernel in-process **no verifica criptográficamente al caller** (`agent_id` viene del config del propio proceso); la criptografía aparece en fronteras: handshake agente-agente verifica firma del challenge + llave contra el registro (_"never trust self-reported value"_), registro Nexus exige proof-of-possession.

**Delta vs nota 08:** convergencia fuerte que confirma el diseño lite — (1) identificador estable ≠ material de llave (su DID aleatorio ≡ nuestro URN; nuestro `sub` estable + rotación por `keyid` es la misma jugada); (2) su intersección por cadena ≡ nuestro `derive()` con intersección garantizada — el patrón es unánime en la industria (Kagenti, AgentCore, Entra, ahora AGT); (3) verificar identidad en la frontera y no en cada llamada interna ≡ nuestra etapa identity del gateway. Donde NO los seguimos: DIDs custom sin ecosistema (tres formatos incompatibles en el mismo repo) vs nuestro URN + JWT con `act` (estándares IETF); su OBO casero refuerza la elección de RFC 8693. Bonus para G4/sesión 4: su keystore-Protocol con backends es la forma exacta del puerto `KeyProvider`.

### 1.4 Plugin signing + SBOM (semilla Fase 2 / TH1: capabilities firmadas)

- **Qué se firma:** el **manifest completo** del plugin (todos los campos menos `signature`), Ed25519. El manifest lleva `artifact_sha256` del zip → **una firma ata manifest + artefacto**. Y las **`capabilities` declaradas van dentro de lo firmado** — escalarlas rompe la firma. TH1 tiene acá su referencia implementable.
- **La única canonicalización rigurosa del repo** (`agent-marketplace/.../manifest.py::signable_bytes`): `json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")`. El docstring documenta el bug que los llevó ahí: la versión anterior firmaba `yaml.dump(...)` y _"a signature produced on one machine could fail to verify on another"_ — la lección G2 vivida y escrita por Microsoft.
- **Verificación fail-closed en install:** sin firma ⇒ error; autor fuera del trust store (`author → pubkey`, inmutable en runtime) ⇒ error; SHA-256 del artefacto con `compare_digest`; guard anti zip-slip; escaneo AST de imports peligrosos que borra la instalación; **re-verificación en cada carga** (plugin manipulado post-install se omite). Escape explícito `verify=False`.
- **Declaración firmada ≠ concesión:** `trust_tiers.py` — 5 tiers que **recortan** las capabilities firmadas según confianza (`execute` exige trusted+, `admin` solo verified). La firma prueba lo que el autor declaró; el tier decide cuánto se concede. Es nuestra intersección de permisos aplicada al plano de plugins.
- **SBOM:** CI genera SPDX + CycloneDX y los attesta (GitHub artifact attestations/Sigstore, provenance del tarball incluido); el SDK puede generar/firmar SBOMs de agentes… pero **nadie los verifica en install** — SBOM attestado ≠ SBOM enforced.
- **Anti-patrones anotados** (para NO copiar): 6+ canonicalizaciones conviviendo; Nexus firma el **string hex del hash** en vez de los bytes canónicos; firmas simuladas en escrow (`f"nexus_escrow_{sha256(...)[:32]}"`) y una `requester_signature` que se acepta sin verificar; **cero DSSE/PAE en todo el repo** — nada ata el tipo de payload a la firma, con llaves compartidas entre planos (confusión de contexto posible).

**Delta vs nota 02:** nuestro stack DSSE/PAE + Ed25519 queda **validado por ausencia**: el AGT tiene exactamente los huecos que PAE cierra. Su patrón manifest-única-cosa-firmada con digest del artefacto adentro es la forma del certificado aplicada a supply chain — mismo principio D20 (afirmaciones sobre digests).

## 2 · Decisión

| Referencia                                            | Decisión                                                                       | Racional                                                                                     |
| ----------------------------------------------------- | ------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------- |
| AGT como dependencia/runtime                          | **descartar** (integrar)                                                       | Es un toolkit completo con su propio kernel; necesitamos las formas, no el runtime           |
| Audit hash-chain + Merkle (forma)                     | **inspirar** (confirma ADR-016; Merkle proofs = Fase 2)                        | La forma sí; su canonicalización NO se porta (hallazgos §1.1) — el anexo G2 fija la nuestra  |
| RFC 8785 JCS para digests de contenido (vía ADR-0030) | **portar** → anexo de canonicalización del freeze                              | Donde el AGT necesitó digests reproducibles de verdad, convergió a JCS                       |
| Spec §4.3.1 (campos aditivos fuera del hash)          | **inspirar** (lección negativa)                                                | Versión de esquema DENTRO del contenido hasheado desde el día 1                              |
| ACS: fail-closed + razones reservadas + PDP stateless | **inspirar** (Fase 2: vocabulario de errores tipados en la etapa verificación) | Confirma nota 05; la separación política/mecanismo es idéntica a ADR-017                     |
| Aprobación ligada a digest de acción (ADR-0030)       | **inspirar** (rung 7 / OverrideEvent → `claim_digest`)                         | Ata el juicio humano a la cosa exacta juzgada; nuestro contrato ya tiene el campo            |
| `did:mesh` / DID stack propio                         | **descartar**                                                                  | Identidad lite (URN + JWT `act`, nota 08) se mantiene: estándares IETF > formatos custom     |
| Keystore Protocol (Software/PKCS#11/TEE) + rotación   | **inspirar** (forma del puerto `KeyProvider`, ficha G4)                        | Backends intercambiables detrás de un Protocol — exactamente la costura env→OpenBao          |
| Plugin manifest firmado + trust tiers + installer     | **inspirar** (Fase 2 / TH1: capabilities firmadas)                             | Manifest como única cosa firmada, capabilities adentro, declaración ≠ concesión, fail-closed |
| SignedAuditEntry con HMAC simétrico                   | **descartar**                                                                  | La verificación por terceros exige asimétrica; Ed25519 ya decidido (nota 02)                 |
| Export CloudEvents del audit                          | **inspirar** (costura eventos↔OTEL, ficha A7 — señalar a Geovanni)             | Mapeo limpio entry→envelope; no cambia contrato hoy                                          |

## 3 · Licencias

| Pieza                                    | Licencia                             | Verificado 2026-07-07                                     |
| ---------------------------------------- | ------------------------------------ | --------------------------------------------------------- |
| microsoft/agent-governance-toolkit       | **MIT**                              | ✅ en vivo (LICENSE en el clon) — cierra el ⚠️ de nota 01 |
| Subset JCS vendoreado del AGT (~100 loc) | MIT (parte del repo)                 | ✅ portable con atribución si hiciera falta               |
| `rfc8785` (PyPI, impl. JCS standalone)   | Apache-2.0 ⚠️ (confirmar al agregar) | candidata para el anexo G2 — ver anexo                    |

Sin dependencias nuevas por esta nota; la única potencial (`rfc8785`) se decide en el anexo.

## 4 · Impacto en contrato

**Ningún contrato del freeze cambia.** Esta nota confirma §2 (hash columns como semilla), §6 (`VerificationPolicy` + policy_digest), §7 (DSSE/Ed25519) y §8 (identidad lite) contra la referencia más citada del pool, y produce **una adición**:

1. **Anexo de canonicalización** (`docs/contract-freeze-anexo-canonicalizacion.md`, G2): define `C(x)` (JCS), la vista canónica del evento, el cómputo exacto de `provenance_hash`, `policy_digest` y `claim_digest`, con vectores de prueba. El freeze §7 lo referencia.
2. Semillas Fase 2 anotadas (sin contrato hoy): Merkle proofs sobre el hash-chain; razones de fallo tipadas en la etapa de verificación; capability manifests firmados estilo marketplace + tiers; export CloudEvents.
3. Frontera Steven (su mitad, solo señalado): los 8 intervention points del ACS ≈ forma de los gateway stages; el patrón snapshot-inmutable-por-etapa (budgets host-side, engine stateless) le sirve para el pipeline. El `SnapshotBuilder` y el manifest de binding policy↔stage quedan para su nota.

## 5 · Reconciliación contra la base lógica

- **AX3 (enforcement determinista):** CONFIRMADO por la referencia — el AGT lo enuncia igual ("structurally impossible") y lo implementa fail-closed; su capa probabilística es advisory post-allow y fail-open (nuestro INV-3/D18/D21 como arquitectura ajena).
- **INV-5 (log append-only):** nuestra postura es más fuerte que la referencia — el AGT acota ventanas en memoria (evicción + `seam_hash`) y su persistencia firma con HMAC simétrico; nuestro Postgres completo + futuro Ed25519 offline-verificable exige más. Dato sobre la referencia, no sobre nosotros.
- **AX2/D14 (integridad/encadenamiento):** SOPORTADO — la forma del chain se confirma; la canonicalización portable que la referencia NO tiene es justo lo que el anexo G2 congela.
- **AX1 (atribución):** el AGT también la exige (`agent_did` obligatorio en cada entrada; "an agent did it is not an incident response") — convergencia, sin cambios.
- **Ninguna referencia contradijo la base lógica.** Los hallazgos §1.1 (spec≠impl, SDKs incompatibles, campos fuera del hash) y §1.4 (firmas simuladas, sin PAE) son datos sobre el AGT: madurez despareja de un Public Preview. Refuerzan, no debilitan, nuestras decisiones ya congeladas.
