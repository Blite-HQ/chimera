# Spec — evidencia externa importada (corridas Nexus/Quantinuum, costura B, R3)

**Gobernada por:** freeze §7 (Certificate/Bundle — `deliverables`, T6/decisión #64a) · freeze §11
(campos multi-backend del claim proponente) · freeze §14 (`●ExternalCertificateImported`, ya reservado
en el catálogo) · freeze-anexo-canonicalización §2 (`C(x)`) · **Dueño:** Sebas · **Estado:** SPEC
(2026-07-24)

> **Rango (S3 2026-07-30):** spec **DE DOMINIO** (lente cuántica/Nexus-Quantinuum), no
> contrato genérico del núcleo — el doc entero es dominio alojado en `docs/specs/` genérico
> (censo `docs/mejorado/07-censo-documental.md` §4, tipo (iii): `NormalizedCounts` en
> `engine/`, predicado con campos solo-cuánticos, `ConsensusLeg` sobre una clase decisoria
> del freeze §4). El contenido queda intacto; solo cambia el rango declarado.
>
> Insumo: `docs/planeado/03-research-estado-del-arte.md` §R3 · `knowledge/quantum/08-ruta-quantinuum-guppy.md`
> §1.5 (footgun de endianness Qiskit↔pytket) y §4/Impacto en contrato (campos por backend-leg) ·
> `knowledge/trust/04-anclas-duras-mapa-oraculos.md` (mapa de anclas — esta spec NO agrega un ancla
> nueva, importa evidencia PARA una pata `consensus_replication` ya existente). **Misma receta que
> [`capability-ingesta.md`](capability-ingesta.md)** (R2) para las capas (1)/(2) — esta spec no
> reintroduce el par `Provenance`/`ContentStore`, lo reutiliza y agrega la capa 3 (attestation de
> importación) que le es propia.

## Contrato

Patrón **"evidencia importada con cadena de custodia"**, tres capas — las dos primeras son una instancia
de la MISMA receta de derivación de `capability-ingesta.md` (nada nuevo que inventar ahí); la tercera es
específica de evidencia de terceros.

### Capa 1 — blob crudo

La respuesta de la API de Nexus (JSON de `qnexus`/`BackendResult`) se ingiere exactamente como el
"snapshot crudo" de `capability-ingesta.md` §Contrato: `ContentStore.put(bytes_de_la_respuesta,
media_type, ctx) -> Artifact`, digest sobre bytes exactos, `ExternalSourceProvenance{kind:
"external-source", uri: "nexus://...", retrieved_at, ...}` (mismo tipo, mismo módulo
`engine/src/blite/verification/provenance.py`). **Cero tipo nuevo en esta capa.**

### Capa 2 — instancia normalizada

`BackendResult.to_dict()` (pytket) se transforma en un **esquema propio de counts**, NO se re-expone el
dict de pytket tal cual (acopla el contrato a una librería externa que cambia forma entre versiones):

```
NormalizedCounts = {
  counts: dict[str, int],       # bitstring -> conteo
  bit_order: Literal["msb-left", "msb-right"],   # EXPLÍCITO — nunca implícito
  backend: str,
  noisy_simulation: bool,
  error_params: dict[str, Any] | None,           # None si noisy_simulation=false
}
```

Módulo Fase 1 (Sebas, no existe hoy): `engine/src/blite/verification/external_evidence.py` —
`NormalizedCounts` y `ExternalImportStatement` (abajo) viven ahí; `DerivationProvenance` se importa de
`engine/src/blite/verification/provenance.py` (capability-ingesta.md), sin duplicarla.

Esto ES una `DerivationProvenance` (capability-ingesta.md): `inputs=[{ref: "nexus-response",
digest: <digest de la capa 1>}]`, `recipe={capability: "blite.evidencia.nexus.normalize_counts",
version, params_digest, code_ref}`, `assertions=[{name: "bit_order_declared", passed: true}, ...]`. El
resultado (`NormalizedCounts` canonicalizado con `C(x)` — la ÚNICA puerta, capability-ingesta.md
§Determinismo) se guarda vía `ContentStore.put()` como cualquier otra instancia derivada.

**El footgun que esta capa existe para matar (`knowledge/quantum/08` §1.5):** Qiskit es little-endian
(q₀ a la derecha), pytket default es ILO-BE (q[0] a la izquierda, MSB). Sin `bit_order` explícito en el
esquema, dos implementaciones honestas decodifican el MISMO conteo distinto — exactamente el modo de
falla que `view(claim)`/`C(x)` ya combatieron para otros digests. `bit_order` es campo OBLIGATORIO, no
opcional con default implícito.

### Capa 3 — attestation de importación (in-toto Statement / predicado SLSA v1)

```
ExternalImportStatement = {
  _type: "https://in-toto.io/Statement/v1",
  subject: [{name: "nexus-job:<job_id>", digest: {sha256: <digest capa 2>}}],
  predicateType: "https://blite.dev/ExternalImport/v1",
  predicate: {
    externalParameters: {circuit_digest, shots_requested},
    resolvedDependencies: [
      {name: "transpiled_circuit", digest: {sha256: transpiled_circuit_digest}},  # freeze §11
      {name: "noise_model", digest: {sha256: noise_config_digest}},               # freeze §11
    ],
    builder: {id: "nexus://quantinuum/H2-1E"},
    invocationId: job_id,
    metadata: {startedOn, finishedOn},
  },
}
```

Reutiliza `transpiled_circuit_digest`/`backend_id`/`noise_config_digest` **tal cual ya están en el freeze
§11** (campos multi-backend del claim proponente) — cero campo nuevo del lado del claim proponente, solo
un consumidor nuevo (esta Statement) de digests que ya existían.

**Firma y encaje (T6/decisión #64a, ya congelados):** el `ExternalImportStatement` se canonicaliza
(`C(x)`) y se guarda vía `ContentStore.put()` como cualquier `Artifact`; su digest entra a
`deliverables[{artifact_ref: "external-import:<job_id>", digest}]` del predicate del certificado (freeze
§7). La ÚNICA firma DSSE del mes es la del certificado completo (Fase 1: attestations embebidas en el
payload DSSE del certificado, T6) — esa MISMA firma ampara transitivamente este deliverable porque
`deliverables[]` es parte del predicate firmado. **Ninguna firma DSSE individual para este Statement en
Fase 1** — eso es Fase 2 declarada (mismo texto que T6 ya declara para attestations individuales). El
Statement "entra por deliverables sin tocar el runtime": el pipeline de 8 etapas (freeze §8) no gana una
etapa nueva, el import es trabajo de un `RunStep`/sub-run cuyo resultado se referencia igual que
cualquier otro deliverable.

**Ortogonalidad con la Attestation científica (no confundir las dos capas):** este Statement certifica
LA IMPORTACIÓN (custodia — "esto vino de Nexus, en este momento, con estos parámetros"); NO reemplaza ni
sustituye la `Attestation` clase `consensus_replication` (freeze §4/§11, AL2) que usa esos counts como
UNA pata de consenso multi-backend (`knowledge/quantum/08` §2.3: Aer + Selene/H-series). Son dos
afirmaciones distintas sobre el mismo dato: una de procedencia, otra de veredicto científico.

**Honestidad documentada (R3):** la firma DSSE atesta quién importó, qué y cuándo; la custodia
criptográfica de los BYTES originales termina en la API de Nexus — mismo modelo de confianza que SLSA
declara para su `builder.id` externo. `job_id` + proyecto Nexus permiten re-consulta cruzada por
terceros (no se reimplementa esa re-consulta aquí).

### `ConsensusReplicationPredicate` — extensión ADITIVA a campos §11

`engine/src/blite/verification/evidence.py` define hoy:

```python
class ConsensusReplicationPredicate(BaseModel):
    method: Literal["consensus_replication"] = "consensus_replication"
    replicas: int = Field(ge=2)
    seeds: tuple[int, ...]
    agreement: bool
```

Freeze §11 exige, POR PATA de consenso: `transpiled_circuit_digest`, `backend_id`, `noise_config_digest`
— hoy sin portador en este predicate (mismo tipo de hueco que `SF-P1-2` ya cerró para `claim_type`). Esta
spec **propone** (Fase 1, Sebas) la extensión aditiva:

```python
class ConsensusLeg(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    seed: int
    backend_id: str
    transpiled_circuit_digest: str
    noise_config_digest: str

class ConsensusReplicationPredicate(BaseModel):
    ...
    legs: tuple[ConsensusLeg, ...] = ()   # NUEVO, aditivo — freeze §11
    # validador: si legs no vacío, len(legs) == replicas y
    # seeds == tuple(leg.seed for leg in legs) — consistencia dura
```

Ningún campo existente (`replicas`/`seeds`/`agreement`) se elimina ni cambia de forma — extensión pura.

**[S3 2026-07-30]** Implementado (D-N6): `ConsensusLeg` y la extensión `legs` corren en
producción con el validador exacto aquí propuesto (legs↔replicas y seeds por pata) —
`engine/src/blite/verification/evidence.py:133-181`. El «esta spec propone» de arriba quedó
histórico; la letra se conserva como registro de la propuesta.

### Seguridad dura — NO NEGOCIABLE

**JAMÁS deserializar evidencia externa con `RuntimeDecoder` de Qiskit** (CVE
GHSA-x4x5-jv3x-9c7m — ejecución de código arbitrario sobre JSON no confiable). Todo conversor de la capa
2 es un **conversor plano** (parseo explícito campo a campo, cero `json.loads(..., cls=RuntimeDecoder)`
ni equivalente). Este requisito aplica a CUALQUIER implementación de
`blite.evidencia.nexus.normalize_counts`, sin excepción por conveniencia.

## Eventos / payloads nuevos

`●ExternalCertificateImported` — ya reservado en el catálogo (freeze §14); esta spec fija su forma de
wire:

- Wire: `external_certificate.imported`
- Payload: `{job_id: str, backend_id: str, statement_digest: str, raw_blob_digest: str,
normalized_digest: str, imported_by: str, imported_at: datetime}`
- Se emite en el stream del run (o sub-run) que hizo la importación — misma disciplina de §2/§13 del
  freeze (append-only, `actor_id` obligatorio).

## Interfaces con otros dominios

| Interfaz                                                           | Dominio                | Estado                                                                      |
| ------------------------------------------------------------------ | ---------------------- | --------------------------------------------------------------------------- |
| Receta de derivación (`Provenance`, `ContentStore`, `C(x)`)        | costura (Sebas+Dylan)  | VERDE — reutiliza [`capability-ingesta.md`](capability-ingesta.md) tal cual |
| `deliverables[{artifact_ref, digest}]` del predicate               | confianza (Dylan)      | VERDE (freeze §7, reutilizado sin cambio de forma)                          |
| Firma DSSE del certificado (T6/#64a)                               | confianza (Dylan)      | VERDE (freeze §7, ampara transitivamente — cero firma individual en Fase 1) |
| `transpiled_circuit_digest`/`backend_id`/`noise_config_digest`     | ciencia (Sebas)        | VERDE (freeze §11, ya congelados del lado del claim proponente)             |
| `ConsensusReplicationPredicate.legs` (extensión)                   | confianza (Dylan)      | SPEC — propuesta aditiva, pendiente Fase 1                                  |
| `●ExternalCertificateImported` / `external_certificate.imported`   | confianza (Dylan)      | SPEC — nombre de wire fijado aquí, evento ya reservado en catálogo §14      |
| `CapabilityManifest` v2 (`blite.evidencia.nexus.normalize_counts`) | A · ejecución (Steven) | SPEC — misma discrepancia flaggeada en `capability-ingesta.md`              |

## Fronteras (qué NO decide esta spec)

- No decide el cliente `qnexus` concreto (credenciales, retries, paginación de jobs) — Fase 1 Sebas.
- No re-decide el veredicto científico de la pata `consensus_replication` — solo la custodia de cómo
  llegó el dato; el veredicto sigue siendo del `Verifier`/`Attestation` (freeze §4).
- No agrega DSSE individual por Statement — Fase 2 declarada (T6), sin excepción por presión de tiempo.
- No decide el mapa completo de anclas (`knowledge/trust/04`) — esta spec no agrega un `AnchorKind`
  nuevo ni reabre esa taxonomía.
- No decide si hay re-consulta activa contra la API de Nexus para auditoría de terceros — se declara
  posible (job_id + proyecto), no se implementa.

## Tests de contrato (fixtures de costura)

`tests/fixtures/contract/evidencia/nexus-import-example.json`, espejado a
`apps/studio/src/fixtures/contract/evidencia/nexus-import-example.json` — **declarado, no generado**
(el modelo `ExternalImportStatement`/`NormalizedCounts` no existe hoy).

## Tests semilla

- `tests/seeds/test_seed_evidencia_importacion.py` — `xfail(strict=False)`, Fase 1 Sebas: fija la forma
  del esquema normalizado de counts (`bit_order` obligatorio) y la regla "conversor plano, jamás
  `RuntimeDecoder`".
