# Nota 15 — Forma del puerto `KeyProvider`: las 2 llaves del engine, env hoy → OpenBao Fase 2

**Ítem del backlog (ficha G4):** custodia de las 2 llaves del engine (Ed25519 del certificado + JWT); env hoy → OpenBao Fase 2; rotación por keyid. **Coordinación:** el §13 _del backlog externo de fichas_ (infraestructura/secretos en general — misma fuente que la "ficha G4"; NO es una sección de esta nota [aclarado en S-F]) es carril de Geovanni; el slice de ESTE puerto (cómo el engine pide firmas, no dónde vive la infra de secretos) es mío — señalado, no decidido por mí solo.
**Fecha:** 2026-07-07 · **Estado:** **VIGENTE (2026-07-30).** Escrita como «insumo para el contract freeze» — el freeze se materializó el 2026-07-18; el diseño del puerto `KeyProvider` sigue vigente.
**Fuentes:** nota 02 (Ed25519 del certificado), nota 08 §4.2 (JWT — dejaba "HS256 o Ed25519, decidir en implementación"), nota 09 §1.3 (keystore Protocol del AGT — Software/PKCS#11/TEE, inspiración directa), OpenBao (`openbao.org`, `github.com/openbao/openbao` — Transit engine, AppRole) verificado en vivo 2026-07-07

---

## 1 · Patrón / mecanismo

El engine custodia hoy **dos llaves**, ambas por env var (stopgap de hackathon): la Ed25519 que firma el `TrustCertificate` (nota 02) y la que firma los JWT de identidad (nota 08, punto abierto). Un solo `Protocol` chico las cubre a ambas — mismo principio ADR-008 ("el detalle vive en el adapter, no en el core"):

```python
class KeyProvider(Protocol):
    def sign(self, keyid: str, data: bytes) -> bytes: ...
    def verify(self, keyid: str, data: bytes, signature: bytes) -> bool: ...
    def public_key(self, keyid: str) -> bytes: ...          # raw Ed25519, 32 bytes
    def current_keyid(self, purpose: Literal["trust-certificate", "jwt"]) -> str: ...
    def rotate(self, purpose: Literal["trust-certificate", "jwt"]) -> str: ...  # -> nuevo keyid
```

**`keyid` = `"<purpose>:v<version>"`** (p. ej. `chimera-trust-cert:v1`, `chimera-jwt:v3`) — forma elegida por adelantado para calzar 1:1 con el keyring versionado de OpenBao Transit (`rotate` crea una versión nueva bajo el mismo nombre; versiones viejas quedan para verificar firmas viejas), así el `keyid` no se re-inventa entre fases, se lee directo del backend.

**Decisión que esta nota cierra (punto abierto de nota 08):** ambas llaves son **Ed25519** (no HS256 para el JWT). Unificar el tipo de llave detrás de un solo `KeyProvider` es más simple que sostener dos algoritmos, y Ed25519/EdDSA para JWT es asimétrico — coherente con "verificable sin confiar en nosotros" (D20) igual que el certificado, en vez de un secreto compartido HS256 que solo el propio engine podría validar.

- **Hoy (env):** implementación trivial — llave semilla de 32 bytes por `purpose` en env var (`CHIMERA_TRUST_CERT_KEY`, `CHIMERA_JWT_KEY`), `keyid` fijo `:v1`; `rotate()` no implementado (placeholder que levanta `NotImplementedError` documentado, no una promesa vacía). **[S-F] Convención `*_FILE`:** en compose las llaves viajan como **secrets file-based** (`CHIMERA_TRUST_CERT_KEY_FILE`, `CHIMERA_JWT_KEY_FILE` → ruta bajo `/run/secrets/`, montadas solo donde vive el Signer — infra/03); el adapter env acepta ambas formas (valor directo o `*_FILE`), mismo patrón que `POSTGRES_PASSWORD_FILE` — env plano en un yml sería anti-patrón para la llave que firma EL diferenciador.
- **Fase 2 (OpenBao, MPL-2.0, fork soberano de Vault — confirmado en vivo, adoptantes reales incl. Nvidia/SAP):** el Transit secrets engine firma/verifica **sin exponer la llave privada nunca** al proceso del engine (`POST /transit/sign/:name`, `POST /transit/verify/:name`, `POST /transit/keys/:name/rotate`); soporta Ed25519 de forma nativa. El engine se autentica con **AppRole** (`role_id` + `secret_id` de vida corta, modo "pull" + response-wrapping) bajo una policy acotada a firmar/verificar/rotar únicamente sus dos llaves — nunca acceso general al vault.
- **La forma no cambia entre fases** (regla rectora de la semilla, ya aplicada a `provenance_hash` en nota 02): el `Protocol` es el mismo; solo cambia el adapter detrás.

## 2 · Decisión

| Referencia                                     | Decisión                                                                         | Racional                                                                                                                       |
| ---------------------------------------------- | -------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| `KeyProvider` (Protocol, 1 puerto/2 llaves)    | **portar** (contrato nuevo, propio)                                              | Mismo patrón adapter que `Verifier`/`EventStore`; env hoy, OpenBao Fase 2, sin romper el contrato                              |
| Ambas llaves Ed25519 (cierra punto de nota 08) | **portar**                                                                       | Asimétrico, verificable por terceros sin secreto compartido; un solo tipo de llave, un solo backend                            |
| `keyid = "<purpose>:v<version>"`               | **portar**                                                                       | Calza literal con el keyring versionado de Transit — cero traducción al migrar                                                 |
| OpenBao (Transit + AppRole)                    | **inspirar hoy** (forma del adapter) / **integrar Fase 2**                       | MPL-2.0, API-compatible con Vault, adoptantes reales; Fase 2 porque exige quorum HA (mín. 3 réplicas) — sobrepasa el hackathon |
| Keystore Protocol del AGT (nota 09 §1.3)       | **inspirar** (confirma la forma: backends intercambiables detrás de un Protocol) | Convergencia con la industria; no se porta el runtime del AGT, solo la forma                                                   |

## 3 · Licencias

| Pieza                                  | Licencia                                         | Verificado 2026-07-07 |
| -------------------------------------- | ------------------------------------------------ | --------------------- |
| OpenBao                                | **MPL-2.0**, gobernanza OpenSSF/Linux Foundation | ✅ en vivo            |
| `cryptography` (Ed25519, ya integrada) | Apache-2.0/BSD                                   | conocida (nota 02)    |

Sin dependencia nueva este mes: la implementación env es código propio sobre `cryptography`, ya presente.

## 4 · Impacto en contrato

1. **`KeyProvider`** (Protocol nuevo) vive en `engine/src/blite/keys/` (módulo a crear); `certificate` (nota 02) y `identity` (nota 08) lo consumen para firmar, nunca manejan bytes de llave privada directamente.
2. **Nota 08 actualizada:** el JWT se firma **Ed25519/EdDSA**, no HS256 — cierra el punto abierto de su §4.2 sin cambiar la forma del claim.
3. **`keyid`** ya presente en `TrustCertificate.envelope.signatures[].keyid` (nota 02) y ahora también en el JWT (header `kid`) — mismo formato, mismo puerto.
4. **Frontera con Geovanni (§13 del backlog externo de fichas — no decidido por mí):** dónde vive/se opera la infraestructura de secretos (¿un OpenBao compartido del proyecto o uno por servicio?) es su carril; este puerto solo define cómo el engine LE PIDE una firma — coordinación pendiente (Fase 2), no bloqueante para el freeze.

## 5 · Reconciliación contra la base lógica

- **D20 (confianza = identidad + procedencia + ancla):** SOPORTADO — unificar a Ed25519 hace que tanto el certificado como la identidad sean verificables por terceros sin confiar en el engine, la misma propiedad ya congelada para el certificado (nota 02).
- **AX2 (integridad/encadenamiento):** INTACTO — `rotate()` nunca invalida firmas viejas (versión vieja retenida para verificar), coherente con que el log y las attestations pasadas deben seguir siendo verificables tras una rotación.
- **Inv-E:** sin relación directa — este puerto firma/identifica, no gobierna egreso.
- **Ninguna referencia contradice la base lógica.** OpenBao exige quorum Raft (mín. 3 réplicas) para HA real — dato operativo sobre Fase 2 (se documenta como costo de adopción), no sobre el contrato de hoy.
