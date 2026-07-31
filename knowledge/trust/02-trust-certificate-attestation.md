# Nota 02 — `TrustCertificate` v0: el certificado con forma de attestation firmada (in-toto + DSSE, versión lite)

**Ítem del plan (§4 Dylan):** in-toto + Sigstore (formas) → `TrustCertificate` v0: JSON schema estilo attestation + firma lite; hash-chain queda semilla
**Fecha:** 2026-07-02 · **Estado:** **EJECUTADA (2026-07-24)** — `engine/src/blite/certificate/{dsse,keys,predicate,bundle_check}.py` (DSSE+PAE Ed25519, verify-bundle de 7 puntos). La nomenclatura evolucionó respecto de esta nota: `aggregate_rung` → `titular_level` (vocabulario clase+AL de la spec v3.2); el JSON de §1.3 es histórico, la forma vigente es `predicate.py`.
**Fuentes:** in-toto Attestation Framework (v1.2.0, verificado en vivo) · DSSE (verificado en vivo) · Sigstore cosign/Rekor (verificado en vivo) · semilla TS §6 · notas 01 (provenance) y 03 (aggregate_rung)

---

## 1 · Patrón / mecanismo

### 1.1 Las tres formas que la industria ya maduró (y que copiamos sin integrar)

1. **in-toto Statement** (Attestation Framework v1.2.0 — verificado 2026-07-02): la forma canónica de "afirmar algo sobre un artefacto":
   `{_type, subject: [{name, digest}], predicateType, predicate}` — el _subject_ identifica el artefacto por digest (no por nombre), el _predicateType_ versiona el vocabulario del claim, el _predicate_ lleva el contenido. Es exactamente la estructura que un certificado de confianza necesita: **afirmaciones tipadas sobre un digest inmutable**.
2. **DSSE envelope** (Apache-2.0 — verificado): `{payloadType, payload (b64), signatures[{keyid, sig}]}` firmado con **PAE** (pre-authentication encoding: se firma `PAE(payloadType, payload)`, autenticando el mensaje Y su tipo). Diseñado para evitar canonicalización frágil (el hueco clásico de JWS) — se firma el byte-stream, no una re-serialización.
3. **Sigstore** (cosign Apache-2.0 — verificado): keyless = OIDC → certificado efímero (Fulcio) + publicación en **Rekor** (transparency log). El patrón "publicar la prueba en un log público" es la versión social del hash-chain. GitHub artifact attestations / SLSA provenance usan exactamente este stack — es la forma madura de mostrar una cadena firmada legible (inspiración directa para la vista de certificado del Studio).

### 1.2 Por qué NO integrar Sigstore este mes

- Keyless exige OIDC + Fulcio + Rekor → infra externa y conectividad — **contradice el demo air-gapped** ("esto mismo corre air-gapped en esta laptop"). La soberanía es parte de la tesis; el certificado debe emitirse y verificarse offline.
- La decisión ya está tomada a nivel plan (§1.E.3: in-toto/Sigstore no se integran; se estudian formas). Esta nota la ejecuta: **el certificado v0 es un Statement propio dentro de un DSSE propio, firmado Ed25519 con llave local**.

### 1.3 Diseño `TrustCertificate` v0

```json
{
  "payloadType": "application/vnd.blite.trust-certificate+json",
  "payload": {
    // (b64 en el envelope real)
    "_type": "https://blite.dev/Statement/v0",
    "subject": [
      {
        "name": "run:8f2c...", // el run
        "digest": { "sha256": "<provenance_hash>" } // digest del stream de eventos del run
      }
    ],
    "predicateType": "https://blite.dev/TrustCertificate/v0",
    "predicate": {
      "run_id": "8f2c...",
      "actor": { "id": "user:dylan", "kind": "human", "domain_id": "d-1" },
      "titular_level": "AL3", // [S3 #103] antes `aggregate_rung` — el nivel MÁS DÉBIL (mínimo) del camino crítico (nota 03)
      "unanchored_steps": 0,
      "attestations": [/* Attestation[] con rung/verdict/evidence (nota 03) */],
      "policy_id": "chimera-default@0.1.0", // qué exigencia estaba vigente (nota 05)
      "issued_at": "2026-07-02T18:00:00Z"
    }
  },
  "signatures": [{ "keyid": "chimera-2026", "sig": "<ed25519 sobre PAE>" }]
}
```

Decisiones internas del diseño:

- **`provenance_hash`** = SHA-256 del stream canónico de eventos del run (leído por `read_stream`, nota 01). Cuando el hash-chain de Fase 2 exista, el head de la cadena SE VUELVE el provenance_hash — misma semántica, prueba más fuerte. La forma no cambia entre fases (la regla rectora de la semilla).
- **Firma Ed25519** con la librería `cryptography` (ya estándar en Python); llave del engine por env/secret, generación documentada. `keyid` permite rotación.
- **PAE de DSSE se implementa tal cual** (es ~5 líneas y evita inventar criptografía): `"DSSEv1" || len(type) || type || len(payload) || payload`.
- **Verificación offline**: cualquier tercero con la llave pública verifica el envelope y recomputa el provenance_hash contra el log — el certificado es **auditable sin confiar en nosotros**. Eso ES D20 hecho artefacto.
- `predicateType` versionado (`/v0`) — el vocabulario del certificado puede evolucionar sin romper verificadores viejos (la lección de in-toto).

## 2 · Decisión

| Referencia                               | Decisión                                                                             | Racional                                                                    |
| ---------------------------------------- | ------------------------------------------------------------------------------------ | --------------------------------------------------------------------------- |
| in-toto Statement (v1.2.0)               | **inspirar** (estructura subject/predicateType/predicate en tipos propios)           | Integrarlo traería su ecosistema completo; la forma es lo valioso           |
| DSSE + PAE                               | **portar** (implementación propia mínima del envelope y el PAE)                      | Spec chica y estable; evita canonicalización frágil; ~50 líneas             |
| Sigstore cosign (keyless/Fulcio)         | **descartar** este mes / reevaluar Fase 2                                            | Exige infra externa — rompe air-gap; keyless no aplica a un engine soberano |
| Rekor (transparency log)                 | **inspirar** (Fase 2: publicar digests de certificados como opción de transparencia) | El patrón "publicar la prueba"; opcional para clientes públicos             |
| GitHub attestations / SLSA / visor Rekor | **inspirar** (UX de la vista de certificado del Studio)                              | Cómo mostrar una cadena firmada legible (nota 07 la consume)                |
| `cryptography` (Ed25519)                 | **integrar** (dependencia)                                                           | Estándar de facto; primitiva madura, sin inventar crypto                    |

## 3 · Licencias

| Pieza                      | Licencia                                                                                 | Verificado 2026-07-02                     |
| -------------------------- | ---------------------------------------------------------------------------------------- | ----------------------------------------- |
| in-toto/attestation (spec) | Apache-2.0 ⚠️ (footer no visible en el fetch; confirmar antes de citar en docs públicos) | parcial                                   |
| DSSE (spec)                | **Apache-2.0**                                                                           | ✅ en vivo                                |
| Sigstore cosign            | **Apache-2.0**                                                                           | ✅ en vivo (sin dependencia — descartado) |
| `cryptography` (PyCA)      | Apache-2.0 / BSD (dual)                                                                  | conocida                                  |

Implementar la forma (no integrar las libs) elimina todo riesgo de licencia: los specs son documentos; nuestro código es propio.

## 4 · Impacto en contrato

Contra la semilla TS §6 (`TrustCertificate` plano: run_id, actor, provenance_hash, attestations, issued_at):

1. **`TrustCertificate`** (Pydantic) — CAMBIA de objeto plano a **Statement + Envelope**:
   - `statement`: `{_type, subject[{name, digest}], predicate_type, predicate}` con predicate = `{run_id, actor, titular_level ([S3 #103] antes aggregate_rung), unanchored_steps, attestations[], policy_id, issued_at}`.
   - `envelope`: `{payload_type, payload_b64, signatures[{keyid, sig}]}`.
   - Campos nuevos respecto de la semilla: **`titular_level`** ([S3 #103] antes `aggregate_rung`), **`unanchored_steps`** (nota 03), **`policy_id`** (nota 05), **firma** (la semilla no firmaba — "certificado firmado" es la corrección #7 de Arquitectura-Python).
2. **Tabla `trust_certificates`** (semilla §5): `+ titular_level NOT NULL` ([S3 #103] antes `aggregate_rung SMALLINT` — hoy el nivel es `AL0–AL4`, no un entero de escalera), `+ certificate JSONB NOT NULL` (el envelope completo), `+ keyid TEXT`. Sigue siendo proyección (regenerable del log + attestations).
3. **`provenance_hash`**: semántica congelada = SHA-256 del stream canónico del run; Fase 2 lo sustituye por el head del hash-chain sin cambiar la forma.
4. **Emisión**: al `run.completed`, el módulo `certificate` lee stream + attestations y emite; la emisión misma queda como evento (PR1). El módulo `certificate` ya existe como stub (`engine/src/blite/certificate/`).
5. **Studio** (nota 07): la vista de certificado renderiza el Statement legible (inspiración visor Rekor/GitHub attestations) — necesita el JSON del envelope tal cual por el API.

## 5 · Reconciliación contra la base lógica

- **D20 (confianza = identidad + procedencia + ancla):** REALIZADO literalmente — subject (procedencia por digest) + predicate.actor (identidad) + attestations (anclas). El certificado es el empaquetado de los tres, ahora verificable offline.
- **D14/AX2 (integridad/encadenamiento):** SOPORTADO por fases — provenance_hash hoy, hash-chain Fase 2, misma forma.
- **PR2:** el certificado **reporta** las attestations, no las produce; ninguna parte del certificado usa modelos.
- **Inv-E:** emitir (o no emitir) un certificado NO gobierna egreso; es un artefacto de salida más, sujeto a authz como todo egress.
- **Ninguna referencia contradijo la base lógica.** El keyless de Sigstore asume confianza en una CA externa (Fulcio) — dato sobre Sigstore: para un engine soberano, la raíz de confianza debe poder ser local.
