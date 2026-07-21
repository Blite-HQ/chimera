# Anexo del Contract Freeze — Canonicalización del `provenance_hash` (y de todo digest de contenido)

> **Estado: CONGELADO junto con el freeze (2026-07-18, cierre S-E)** — spec de la ficha G2. Complementa `contract-freeze.md` §7 (el freeze define QUÉ es el `provenance_hash`; este anexo define los BYTES exactos). Insumo: nota 09 (estudio de primera mano del MS Agent Governance Toolkit). Los vectores §6 son el gate de toda implementación.
> **Por qué existe:** sin spec exacta de bytes, dos implementaciones honestas producen hashes distintos y la verificación offline muere. No es hipótesis: el AGT lo demuestra — su spec de audit dice "no extra whitespace" pero su implementación de referencia serializa con espacios (hashes distintos, reproducido en vivo), y sus SDKs Python/TypeScript/Rust usan tres canonicalizaciones incompatibles entre sí (nota 09 §1.1).

---

## 1 · Las dos reglas (evaluación de alternativas)

| Alternativa                                                       | Evaluación                                                                                                                                                                                                                                                       |
| ----------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Bytes-firmados estilo DSSE**                                    | ✅ **Regla 1** para todo lo FIRMADO. No aplica a `provenance_hash`: los eventos viven en JSONB (Postgres re-serializa: pierde orden de keys y whitespace originales) — no hay "bytes originales" que preservar al releer el stream.                              |
| **RFC 8785 (JCS)**                                                | ✅ **Regla 2** para todo DIGEST DE CONTENIDO recomputable desde datos estructurados. Estándar, determinista, implementable en ~100 líneas. Único hazard real: formateo de floats (§3).                                                                           |
| **Lo que hace el AGT** (`json.dumps(sort_keys=True)` y variantes) | ❌ Descartado como spec: 6+ variantes conviven en el propio AGT, spec≠impl verificado, sin paridad cross-lenguaje. PERO: donde el AGT necesitó digests reproducibles de verdad (aprobaciones ADR-0030) convergió a JCS — validación independiente de la Regla 2. |

**Regla 1 — lo firmado se verifica sobre bytes exactos, jamás sobre una re-serialización.** El envelope DSSE persiste `payload_b64`; verificar = decodificar esos bytes y comprobar `PAE(payload_type, payload)` (nota 02). La canonicalización ocurre UNA vez, al emitir; después solo viajan bytes.

**Regla 2 — todo digest de contenido estructurado usa `C(x)` = RFC 8785 (JCS).** Consumidores: `provenance_hash` (§4), `claim_digest` de `Attestation.subject` (§5), y cualquier digest futuro de datos estructurados. `policy_digest` NO (§5: es digest de artefacto).

Las reglas componen: `C()` produce los digests que van DENTRO del Statement; DSSE/PAE firma el Statement como bytes. Nunca se firma una re-serialización, nunca se re-canonicaliza para verificar una firma.

## 2 · `C(x)` — algoritmo exacto

Entrada: un valor del **modelo de datos JSON** (post-parseo; lo que devuelve leer el JSONB). Salida: bytes UTF-8.

1. **Objetos:** miembros ordenados por **code units UTF-16** de la key (el orden de RFC 8785; equivale a ordenar por `key.encode("utf-16-be")`). Keys deben ser strings; otra cosa ⇒ error.
2. **Arrays:** orden preservado.
3. **Separadores:** `,` y `:` — cero whitespace.
4. **Strings:** escape JSON mínimo (`\"`, `\\`, cortos `\b \t \n \f \r`, `\u00XX` minúscula para el resto de control chars); **no-ASCII literal en UTF-8** (sin `\uXXXX` para é/汉/emoji).
5. **Números:** enteros sin punto decimal. Floats: formateo ECMAScript de valor más corto que round-tripea (regla RFC 8785); float de valor entero se emite como entero (`2.0` → `2`); `-0.0` → `0`; **NaN/Infinity ⇒ error** (fail-loud, jamás digest inestable).
6. **`null`/`true`/`false`** literales.
7. Cualquier tipo no-JSON ⇒ error.

**Implementación (decisión):** intentar el paquete PyPI **`rfc8785`** (Trail of Bits, sin dependencias — licencia ⚠️ confirmar al agregar, regla search-first); si no convence, **portar el subset del AGT** (`approval_protocol/digest.py`, MIT, ~100 líneas, ya auditado en nota 09) con su misma restricción documentada de floats. En ambos casos: los vectores de §6 son el gate — la impl que no los reproduce byte a byte no entra.

**Hazard de floats (documentado, acotado):** `repr()` de Python y ECMAScript divergen en exponentes (`1e-07` vs `1e-7`). Normativo: **ECMAScript** (lo que dice RFC 8785). Mitigación de contrato: los payloads que entran a digests evitan floats donde un entero o string sirva; enteros fuera de ±2^53 van como string (el modelo de datos es double). El corpus de vectores incluye los bordes.

## 3 · Vista canónica del evento (v1)

`view(e)` = objeto con **exactamente** estos 8 campos del `Event` (freeze §2):

| Campo         | Forma canónica                                                                                                                                                                                                          |
| ------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `id`          | UUID **lowercase** con guiones (string)                                                                                                                                                                                 |
| `stream_id`   | string tal cual                                                                                                                                                                                                         |
| `seq`         | entero                                                                                                                                                                                                                  |
| `type`        | string tal cual                                                                                                                                                                                                         |
| `actor_id`    | URN (nota 08) tal cual                                                                                                                                                                                                  |
| `domain_id`   | string tal cual                                                                                                                                                                                                         |
| `payload`     | el JSON del evento (valores post-JSONB)                                                                                                                                                                                 |
| `occurred_at` | string RFC 3339 UTC con **exactamente 6 dígitos fraccionales** y sufijo `Z`: `2026-07-07T12:00:00.000000Z` — formato fijo construido explícitamente, NUNCA `isoformat()` (omite microsegundos en cero y emite `+00:00`) |

**Exclusiones razonadas:** `global_seq` (cursor de almacenamiento, depende del interleaving con otros streams — no es contenido del evento); `prev_hash`/`hash` (capa de integridad — evitan circularidad y dejan el mismo `C()` para la cadena de Fase 2). Campos nuevos ⇒ **bump de versión del prefijo de dominio (§4)** — la lección §4.3.1 del AGT: jamás campos "aditivos" fuera del hash bajo la misma versión.

## 4 · `provenance_hash` — cómputo exacto (Fase 1)

Sobre el stream completo del run (`read_stream(run_stream)`, orden `seq` estricto 1..n, sin huecos). **[S-F] Alcance:** el `provenance_hash` se computa **solo sobre streams de run** — los streams de sistema (`system:*`, freeze §2 [S-F]) jamás entran. El trabajo de sub-runs queda amparado **transitivamente**: el evento `●ClaimEmitted {claim_digest, sub_run_id, sub_run_provenance_hash}` en el stream del raíz encadena el hash del stream del sub-run (estilo Merkle — freeze §13 [S-F]); el verificador offline recomputa el hash del sub-run y lo compara contra el payload del `●ClaimEmitted` que el hash del raíz ya ampara:

```
linea_i          = C(view(e_i)) ‖ 0x0A                      # JSONL: C() jamás emite \n crudo
provenance_hash  = SHA-256( "blite/provenance/v1\n" ‖ linea_1 ‖ … ‖ linea_n )   # hex lowercase
```

- El prefijo de dominio (`blite/provenance/v1\n` en UTF-8) separa este hash de cualquier otro uso de SHA-256 en el sistema y **lleva la versión del esquema de la vista** (§3).
- Framing por líneas: streameable (el verificador offline no carga el run entero) y sin ambigüedad de fronteras — la lección PAE de DSSE aplicada al caso multi-mensaje.
- Verificación offline = releer el stream, recomputar, comparar con el `subject.digest.sha256` del certificado (nota 02). Ese script ES demo (sesión 12).

**Fase 2 (semilla, no se implementa):** hash-chain por evento con el MISMO `C()`:
`hash_i = SHA-256("blite/event/v1\n" ‖ hash_{i-1}^hex ‖ "\n" ‖ C(view(e_i)))`, génesis `hash_0^hex = ""` (elección explícita — el AGT tiene `""` en Python y `"0"*64` en TS por no elegir). El head de la cadena SE VUELVE el `provenance_hash` sin cambiar forma ni `C()` (freeze §7).

## 5 · Los otros dos digests

- **`claim_digest`** (`Attestation.subject`, freeze §4): `SHA-256("blite/claim/v1\n" ‖ C(claim))`, hex lowercase. Regla 2: el claim es dato estructurado sin artefacto canónico. **[S-F · T7] `view(claim)` — la vista canónica que faltaba** (sin ella, dos implementaciones honestas producían digests distintos — exactamente la falla que este anexo existe para matar): `view(claim) = {canonical_statement, scope}` — exactamente esos 2 campos, en la forma en que viajan en `conclusions[]` del certificado (`canonical_statement`: string sin deixis; `scope`: el ScopeExpr canónico). Campos nuevos ⇒ bump del prefijo (`blite/claim/v2`), regla §3. Vector V6 en §6.
- **`policy_digest`** (freeze §6): `SHA-256` sobre los **bytes exactos del archivo YAML** de la política tal como se distribuye (`distributions/chimera/`). Regla 1, no Regla 2: la política ES un artefacto versionado — comentarios y formato son parte de lo distribuido; re-parsearla para canonicalizar reintroduciría exactamente la fragilidad que este anexo elimina.

## 6 · Vectores de prueba

Generados con la implementación de referencia del subset (**`scripts/gen-canonicalization-vectors.py`**, reproducible; los futuros tests de contrato — sesión 7.3 — DEBEN reproducirlos byte a byte).

**V1 — evento mínimo.** Entrada `view(e_1)`:

```json
{
  "id": "0198c0de-0000-7000-8000-000000000001",
  "stream_id": "run:8f2c1a9b",
  "seq": 1,
  "type": "run.started",
  "actor_id": "user:dylan",
  "domain_id": "d-default",
  "payload": {},
  "occurred_at": "2026-07-07T12:00:00.000000Z"
}
```

`C(view(e_1))` (206 bytes):

```
{"actor_id":"user:dylan","domain_id":"d-default","id":"0198c0de-0000-7000-8000-000000000001","occurred_at":"2026-07-07T12:00:00.000000Z","payload":{},"seq":1,"stream_id":"run:8f2c1a9b","type":"run.started"}
```

`SHA-256(C(view(e_1)))` = `e80b95edd718a533312fc2b4ecdda321681898ea6f10c8460207b1f27a45cbdf`

**V2 — payload con unicode, null, floats, anidamiento.** Entrada: evento `seq: 2`, `type: "verification.completed"`, `actor_id: "service:runtime"`, `occurred_at: "2026-07-07T12:00:01.500000Z"`, `id: "0198c0de-0000-7000-8000-000000000002"`, mismo stream, y

```json
"payload": {"verdict": "pass", "rung": 1, "gap": 0.1, "óptimo": true, "nota": "café ✓",
            "islands": [2, 3], "policy_id": "chimera-default@0.1.0", "detail": null, "cut_size": 5.0}
```

`C(view(e_2))` (370 bytes — notar: `cut_size` 5.0→`5`; `óptimo` ordenada DESPUÉS de `verdict` por UTF-16; unicode literal):

```
{"actor_id":"service:runtime","domain_id":"d-default","id":"0198c0de-0000-7000-8000-000000000002","occurred_at":"2026-07-07T12:00:01.500000Z","payload":{"cut_size":5,"detail":null,"gap":0.1,"islands":[2,3],"nota":"café ✓","policy_id":"chimera-default@0.1.0","rung":1,"verdict":"pass","óptimo":true},"seq":2,"stream_id":"run:8f2c1a9b","type":"verification.completed"}
```

`SHA-256(C(view(e_2)))` = `456eeed54eb5a23a4cd74d2ec1c8735c0c89429533f30ca096330e0f64b4c0e8`

**V3 — `provenance_hash` del stream `[e_1, e_2]`:**

```
SHA-256( b"blite/provenance/v1\n" + C(view(e_1)) + b"\n" + C(view(e_2)) + b"\n" )
= 049e89fb6abf0936e7cd3cd3e2ca49905202a7e62dc7a1c5325873c882cd6acc
```

**V4 — sensibilidad:** mismo stream con UN cambio (`payload.verdict` de `e_2`: `"pass"` → `"fail"`) ⇒
`provenance_hash = 1682394a91b2d25f1c41a5a100ea0d897bc43745b11f37783256a181b99ad9e8` (ningún prefijo común — el certificado sobre V3 no puede amparar el stream de V4).

**V5 — bordes numéricos y de orden (unitarios de `C`):**

| Entrada                      | `C()` esperado               | Nota                                                                                 |
| ---------------------------- | ---------------------------- | ------------------------------------------------------------------------------------ |
| `2.0`                        | `2`                          | float entero → entero                                                                |
| `0.1`                        | `0.1`                        | shortest round-trip                                                                  |
| `-0.0`                       | `0`                          | regla ECMAScript                                                                     |
| `1e21`                       | `1000000000000000000000`     | sin notación exponencial en este rango                                               |
| `1e-7`                       | `1e-7`                       | ⚠️ normativo ECMAScript; `repr()` Python da `1e-07` — la impl DEBE corregirlo (gate) |
| `NaN` / `Infinity`           | **error**                    | jamás un digest inestable                                                            |
| `{"é":1,"z":2,"a":3,"😀":4}` | `{"a":3,"z":2,"é":1,"😀":4}` | orden por code units UTF-16 (no por bytes UTF-8)                                     |

**V6 — `claim_digest` sobre `view(claim)` [S-F · T7].** Entrada:

```json
{
  "canonical_statement": "La particion propuesta para islanding-corpus/ieee14-flujo@v1 alcanza corte 57070, igual al optimo del corpus (r = 1.0).",
  "scope": {
    "dataset": "islanding-corpus/ieee14-flujo@v1",
    "corpus_digest": "c7880bb0d254d2d5f91c21cfd7cf0a5ac1cb9c88261c15b94cb7b22d6fd896ad"
  }
}
```

`C(view(claim))` (283 bytes — `corpus_digest` ordenada ANTES de `dataset`):

```
{"canonical_statement":"La particion propuesta para islanding-corpus/ieee14-flujo@v1 alcanza corte 57070, igual al optimo del corpus (r = 1.0).","scope":{"corpus_digest":"c7880bb0d254d2d5f91c21cfd7cf0a5ac1cb9c88261c15b94cb7b22d6fd896ad","dataset":"islanding-corpus/ieee14-flujo@v1"}}
```

`claim_digest = SHA-256(b"blite/claim/v1\n" ‖ C(view(claim)))` = `75c92854291ee855a99fea910ce0b98522524b082f2a07f810fbae416509a34a`

**Notas [S-F] sobre los vectores existentes (los vectores NO se regeneran — romperían hashes):** el `stream_id: "run:8f2c1a9b"` de V1 y el `"rung": 1` del payload de V2 son **datos arbitrarios del gate de hashing, no forma normativa** — el `run_id` real no lleva prefijo (freeze §7 [S-F]) y `rung` es vocabulario eliminado (freeze §4). Un payload es un JSON opaco para `C()`: los vectores prueban los bytes, no el vocabulario.

## 7 · Reconciliación

- **D14/AX2:** este anexo materializa la mitad "recomputable" de la integridad; la cadena de Fase 2 reusa `C()` sin cambio de forma (regla rectora de la semilla).
- **D20/verificación offline:** el certificado queda auditable sin confiar en nosotros — con ESTA spec, un verificador independiente escrito en otro lenguaje llega al mismo hash (los vectores son el contrato de paridad).
- **PR2:** `C()` es serialización pura; ningún digest usa modelos.
- **Inv-E intacto:** los digests describen, no gobiernan egreso.
