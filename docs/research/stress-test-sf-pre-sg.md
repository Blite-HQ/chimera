# CHIMERA — Stress test brutal del diseño post-S-F (pre-S-G) · 2026-07-20 → 21

> **Qué es esto.** Panel adversarial de 5 atacantes con postura de DESTRUCCIÓN contra la versión
> corregida por S-F (commits `3f49ab7` re-lock, `7dbb57e` Policy 0.2.0, `02fa06d` supersesiones).
> Objetivo: BOTAR el diseño antes de arrancar S-G. Cada hallazgo pasó verificación adversarial
> (postura de refutación) con evidencia primaria — corrida real o `archivo:línea`. Lo YA cazado en
> `ratificacion-simulada-sf-validacion.md` (O/N/I/T/E/D) se trató como ruido, no como hallazgo.
> **Dos pasadas:** la 1ª (20-jul) se cortó por límite de sesión; la 2ª (21-jul) completó, corrigió un
> hallazgo de la 1ª y cerró los residuales. Ejercicio personal: rama `ejercicio/sf-ratificacion-simulada`.
> Durante la AUDITORÍA: cero archivos del repo modificados salvo este reporte. Los FIXES aplicados
> después (21-jul, con TDD y gates verdes) se registran en **§8**.

## 0 · Veredicto

**GO a S-G — condicionado a aplicar el P0 y los cuatro P1 antes del 23-jul.** El diseño SOBREVIVIÓ
dos pasadas adversariales (la 2ª completa, con verificación por refutación dentro del workflow):
ninguna decisión congelada quedó invalidada, ninguna semilla contradice la constitución
(`invariants.md` / `base-logica-formal.md`), y el único P0 (un `pass` con ancla fantasma,
representable) tiene fix pequeño y aplicable antes del 23. Los fixes S-F auditados (re-lock, Policy
C0–C3, segunda ancla ieee30, falla sembrada, titular computable) resistieron la refutación.

**Qué cambió en la 2ª pasada (2026-07-21):** (a) **corrigió SF-P1-1** — el bug de canonicalización es
más profundo de lo diagnosticado: el `engine` MISMO no conforma con ECMAScript, y el fix original
("unificar sobre el engine") lo habría enshrinado; (b) sumó **SF-P1-4** (el verificador offline no
ata las `conclusions` a su `claim_digest` ni a las attestations) y **SF-P2-4** (titular ciego al
verdict); (c) **cerró la mayoría de los residuales de §5 como SOBREVIVIÓ** (swap de attestation DSSE,
colisión `run_id`, volatilidad de replay, air-gap, SSE sin pérdidas, GW-vs-ancla); (d) refutó como
decisiones congeladas legítimas o ya-cazadas varios intentos de invalidación (DistributionManifest,
R-V2/AcceptanceAuthority, baselines GW+greedy, 6-12 nodos, orden de sacrificio día-D). **Ningún P0
nuevo; ninguna decisión congelada invalidada. Veredicto sostenido: GO condicional.**

## 1 · Método y nota de ejecución (honesta)

Workflow de 5 atacantes en paralelo (contexto fresco) + refutador por hallazgo, en 2 pasadas.

**1ª pasada (20-jul).** Los 5 atacantes ejecutaron ataques en vivo en scratchpad y **murieron por
límite de sesión** (`resets 8:40pm`) antes de emitir salida estructurada — 0 resultados devueltos. Se
**rescataron los transcripts** y el autor corrió a mano la verificación adversarial que el panel no
alcanzó (cada hallazgo re-confirmado con evidencia primaria propia).

**2ª pasada (21-jul, sesión reseteada).** Se re-lanzó el panel con los hallazgos de la 1ª marcados
como ya-encontrados (para no re-reportarlos) y cada atacante enfocado en sus residuales. Completó:
**18 agentes, 0 errores, ~15.5 min**, y la verificación adversarial por refutación **SÍ corrió dentro
del workflow** (cada hallazgo nuevo confirmado/refutado por un 2º agente con evidencia primaria). Las
correcciones que la 2ª pasada le hizo a la 1ª (FORGE-2 vs SF-P1-1) el autor las re-verificó con
`node` como ground-truth ECMAScript.

Severidad: **P0** = invalida algo congelado o mata el demo (fix antes del 23-jul). **P1** = cerrar
antes del 23-jul. **P2** = registrar. Dueños: Dylan (confianza) · Steven (ejecución) · Sebas
(ciencia) · Geovanni (infra) · equipo.

## 2 · P0 — forja representable

### SF-P0-1 · Un `pass` con ancla FANTASMA es representable y sobrevive toda la verificación offline especificada

**Estado prohibido que permite.** `check_α(d)=pass` con un `anchor_digest` que no referencia ningún
ancla existente ni registrada — un `verified` de nivel AL que el verificador offline no puede
distinguir de uno real.

**Evidencia primaria.**

- `docs/esquema-datos-v2.md:212` — `anchor_digest TEXT` (sin FK, texto libre).
- `docs/esquema-datos-v2.md:219-220` — el único guard es `CHECK (verdict <> 'pass' OR anchor_digest
IS NOT NULL)`: exige **presencia**, no existencia.
- `docs/esquema-datos-v2.md` tablas creadas: `events, domains, channels, identities, capabilities,
artifacts, runs_projection, attestations, trust_certificates` — **no existe tabla de anclas /
  anchor-registry** contra la cual resolver el digest.
- `docs/contract-freeze.md:118` (checklist [S-F] T11 de `verify-bundle`): el chequeo (5) es
  "`pass ⇒ anchor_digest` **presente**". Presencia, otra vez.
- Un `pass` con `anchor_digest = "<64 hex arbitrario>"` pasa el CHECK SQL y el checklist offline.

**Pega a.** `base-logica-formal.md` **D10** (el ancla debe EXISTIR y el check estar REGISTRADO) ·
freeze §7/T11 · esquema §5. El fix S-F T3 cerró el `NULL`, pero no la existencia.

**Fix (pre-23-jul, aplicable).** Añadir un 6º chequeo al spec de `verify-bundle`: `anchor_digest`
DEBE resolver contra los **descriptores de anclas que el Bundle ya empaqueta** (freeze §7: "Bundle
mínimo = … descriptores de anclas/verificadores") y su evidencia (`evidence_digests`) reproducir.
La info para detectarlo YA viaja en el bundle; falta la línea del checklist. **Dueño.** Dylan.
**Por qué no rompe el GO:** fix de pocas líneas sobre un seed de S-G; requiere un emisor
deshonesto/con bug, pero el diferenciador es "verificable offline por terceros" y hoy el tercero no
puede detectar el ancla fantasma — por eso es P0.

## 3 · P1 — cerrar antes del 23-jul

### SF-P1-1 (CORREGIDO en 2ª pasada) · El primitivo `C(x)` no conforma con ECMAScript/RFC 8785 — y el `engine` MISMO diverge, no solo el script → rompe la paridad cross-lenguaje que el anexo promete

**Corrección de la 1ª pasada.** La 1ª pasada diagnosticó "engine correcto, script incorrecto" (solo
el padding del exponente, `1e-7` vs `1e-07`) y propuso "unificar sobre el engine". **Era erróneo:** la
2ª pasada probó — y el autor re-verificó con `node` v24 — que `engine/src/blite/certificate/canonical.py`
TAMBIÉN diverge de ECMAScript en otra banda; unificar sobre el engine habría enshrinado el bug.

**Estado prohibido.** El anexo CONGELADO existe para que "dos implementaciones honestas" nunca
produzcan hashes distintos y "un verificador independiente en otro lenguaje llegue al mismo hash"
(§7/D20). El primitivo `C(x)` del repo NO produce la forma normativa ECMAScript.

**Evidencia primaria (corrida propia, `engine` vs `node` v24 = ground-truth ECMAScript).**

- Banda `[1e-6, 1e-4)`: ECMAScript usa notación **FIJA** — `1e-5→"0.00001"`, `1e-6→"0.000001"`,
  `1.5e-5→"0.000015"`; el `engine` emite **exponencial** — `"1e-5"`, `"1e-6"`, `"1.5e-5"`. El regex
  `_EXPONENT_LEADING_ZEROS` (`canonical.py:25/39`) solo quita ceros del exponente; **nunca** convierte
  exponencial→fija. (Fuera de la banda coinciden: `1e-4→"0.0001"`, `1e-7→"1e-7"`, `5e-8→"5e-8"`.)
- El script (`scripts/gen-canonicalization-vectors.py:23`, `repr()` crudo) diverge ADEMÁS en el
  padding (`1e-7→"1e-07"`).
- End-to-end: `claim_digest` de `{scope:{se_estimado:1e-5}}` → engine `2051f470…` vs conforme
  `96d0205…` — **MATCH: False**. El comentario `canonical.py:35-38` afirma FALSAMENTE que `repr()` da
  "the same shortest-round-trip digits as ECMAScript".
- **VERDE ENGAÑOSO on-gate:** V1–V6 se reproducen (V5 solo prueba `1e-7`, que coincide por azar, y
  `1e21`, salvado por `is_integer()`); la banda rota no está en ningún vector ⇒ el gate queda verde
  con impl no conforme.

**Pega a.** Anexo §2 punto 5 (formateo ECMAScript normativo) + §7/D20 (paridad cross-lenguaje).
Riesgo directo al beat §15.4 (verify offline en 2ª máquina) si esa máquina corre un verificador
conforme (`Number.toString` de JS, o la lib `rfc8785`) y el payload trae un float en la banda
(`se_estimado`/`gap`/std chico cerca del óptimo).

**Fix (pre-23-jul).** NO unificar sobre el engine. Adoptar un formateador ECMAScript conforme
completo (`Number::toString`: fija para `-6 ≤ exp < 21`, exponencial fuera) — el anexo §2 ya prefiere
el paquete PyPI **`rfc8785`** (Trail of Bits, conforme) — y hacer que `canonical.py` + los dos
scripts lo reproduzcan byte a byte. Añadir a V5 vectores en la banda rota (`1e-5→"0.00001"`,
`1e-6→"0.000001"`, `1.5e-5→"0.000015"`) como gate ejecutado. Corregir el comentario `canonical.py:35-38`.
**Dueño.** Dylan. No invalida el anexo (su regla ECMAScript es correcta; el impl no conforma) → P1.

### SF-P1-2 · La Policy 0.2.0 no es evaluable: 2 de sus 3 dimensiones de requisito no tienen portador en la semilla Fase 1, y sus valores de `claim_type` no están en el vocabulario registrado

**Estado prohibido / no construible.** La etapa de verificación (mecánica: LEE la Policy pinneada)
no puede casar un claim a su regla ni comprobar sus anclas con las semillas congeladas.

**Evidencia primaria.**

- `claim_type` existe SOLO en `engine/src/blite/verification/policy.py:35`. Grep en contratos v2 /
  esquema v2 / anexo = **vacío**; `view(claim) = {canonical_statement, scope}` lo excluye; el payload
  de `●ClaimEmitted` tampoco lo lleva. En Fase 1 "no hay entidad Claim ni tabla claims" (freeze §14).
- Los valores del YAML — `verification-default.yaml:13,19` `claim_type: solution` / `intermediate` —
  **no están** en el registro de claim_types: `perfil-stem-v1-0.md:18-26` (`simulation_result`, …)
  ni `spec-confianza-v3-2.md:88` (`numeric·comparative·…·derivation`). Las reglas nunca casarían un
  claim real → caerían al piso por defecto.
- `required_anchors: [solver, execution]` (AnchorKind) tampoco tiene portador: la `Attestation` seed
  lleva `verifier_class` + `anchor_digest` + `independence_group` (esquema §5:202/212/208) pero **NO**
  `anchor_kind`. Solo `required_legs` (por `independence_group`, fix S-F T5) SÍ tiene portador.

**Pega a.** freeze §6 (matriz Policy) · `spec-confianza-v3-2.md:88/90/100` · Perfil STEM §1 · freeze
§4. Es "contrato citado sin forma construible / decisión de contrato sin tomar", un nivel más
profundo que el T15 cazado (el seed ya existe; su **evaluador** no se puede construir).

**Fix (antes del 23-jul — decisión de contrato de Dylan).** (a) Declarar el portador de `claim_type`
en Fase 1 (p. ej. en `conclusions[]` / en el payload de `●ClaimEmitted`) y alinear los valores del
YAML al registro, o re-expresar las reglas por una dimensión que sí exista; (b) declarar el mapeo
`verifier_class → AnchorKind` o añadir `anchor_kind` a la `Attestation`. **Dueño.** Dylan.

### SF-P1-3 · Todo el plano de verificación del Studio (la superficie EN ESCENA) sigue en vocabulario PRE-FREEZE (escalera 1-7 `rung`/`aggregate_rung` + política muerta `@0.1.0`), sin marca

**Contradicción viva.** El camino dorado termina "Studio SSE con **badges por isla**" (freeze §15.4);
el pitch dice que el badge es clase+AL "no como titular" (freeze §7 T2 / trust/18). El código real
del Studio muestra **escalón 1..7** y el certificado de otra época.

**Evidencia primaria (grep + decode del fixture).**

- `rung`/`aggregate_rung` vivo, sin marca, en `apps/studio/src/components/verification/{RungBadge,
RungLadder,rungs}.tsx/ts` (+ tests), `spike/{ieee14.ts,GridSpike.tsx}`, `views/{StepInspector,
CertificateView.tsx:118,types.ts:59}`, `fixtures/{certificate,runEvents,stepEvidence}.ts`, y
  `scripts/gen-example-trust-certificate.py:124/130/145/157`.
- **Ampliación 2ª pasada (CERT-2):** el defecto es más ancho que `rung`. El fixture del cert
  (`apps/studio/src/fixtures/certificate.example.json`) y su generador emiten el predicate ENTERO
  del `TrustCertificate` **pre-freeze** — keys `{actor, aggregate_rung, attestations, issued_at,
policy_id, run_id, unanchored_steps}`, SIN `conclusions/titular_level/scope/canonical_statement/
assumptions/deliverables/independence_group/claim_digest/coverage_stats` — y fijan la política MUERTA
  `policy_id: "chimera-default@0.1.0"` (la que S-F §6 superseció a `0.2.0` por hablar `min_rung`).

**Pega a.** freeze §4 (rung desaparece; badges migran a clase+AL — trust/18) + §7 T2 (`aggregate_rung`
→ `titular_level`) + §6 T1 (Policy → 0.2.0; `@0.1.0` es la versión muerta) + §7 P0-2 (la UX abre con
el alcance, no con el número). Gemelo de E4 (superseded sin marca), en el plano demo-visible que la
auditoría S-F nunca barrió.

**Fix (antes del 23-jul).** Migrar los componentes de verificación del Studio a clase+AL (o acotar el
Studio del demo a vistas ya migradas); regenerar el fixture + `gen-example-trust-certificate.py`
contra el `TrustCertificate` S-F (conclusions/titular_level/assumptions/deliverables/independence_group,
`policy_id` de 0.2.0); estampar la supersesión. No invalida la decisión congelada (rung→clase+AL está
tomada; el código va atrás) → P1, no P0. **Dueño.** Dylan / Studio.

### SF-P1-4 (2ª pasada) · La verificación offline nunca ata las `conclusions` a su `claim_digest` ni a las attestations — `view(claim)`/V6 quedan como letra muerta y el beat "re-verificá, no nos creas" es parcialmente cosmético

**Estado prohibido / contradicción con lo congelado.** El checklist CONGELADO de `verify-bundle`
(freeze §7 T11, 5 puntos) recomputa `provenance_hash` y los digests de `deliverables`, pero **nunca**
(6) recomputa `conclusions[].claim_digest = SHA-256("blite/claim/v1\n"‖C(view(claim)))` ni (7) ata
cada conclusión a una attestation embebida con el mismo `claim_digest` y verdict/nivel compatibles.
Un certificado firmado puede portar `{claim_digest: D1, "partición óptima r=1.0, verified, AL4"}`
respaldado SOLO por una attestation `{claim_digest: D2 ≠ D1, verifier_class: property_rule (techo
AL2), pass}` y pasar los 5 puntos (titular = mín(level) = AL4 ✓; pass ⇒ anchor presente ✓; firma ✓).

**Evidencia primaria.** freeze §7:118 (checklist de exactamente 5 puntos, ninguno recomputa
`claim_digest` ni liga conclusión↔attestation) · anexo §5 + freeze §14 (`view(claim)`/V6 se
CONGELARON — T7 — "para que dos implementaciones honestas no produzcan digests distintos"; el
generador los reproduce byte a byte: `75c92854…`) pero **ningún verificador los consume** · dos
vocabularios de verdict sin mapeo (`conclusions`: {verified,refuted,inconclusive,not_required_declared}
vs `Attestation`: {pass,fail,inconclusive}, contratos-v2:335 vs :261).

**Pega a.** Anexo §5/§7 + freeze §14 (T7) + §7 T4 ("AL4 demostrable offline vía re-validación del
checker") + D20 ("auditable sin confiar en nosotros"). El beat central del demo (§15.4/§15.5:
"re-verificá offline, no nos creas") re-chequea los hashes de artefactos pero toma el
enunciado/verdict/nivel de la conclusión **a fe del firmante**.

**Matiz de severidad (verificación adversarial).** Como **forja contra un atacante no confiable** es
P2: la Fase 1 corre "confiá en el firmante" por diseño DECLARADO (S2 Signer≠Verifier y R-V2 son
limitaciones Fase 1 en `assumptions`; la re-derivación independiente del nivel es Fase 2). Se reporta
**P1 por el eje de CONTRADICCIÓN con lo congelado**: `view(claim)`/V6/T7 se congelaron explícitamente
para hacer `claim_digest` recomputable offline y el único verificador jamás los usa — letra muerta — y
el checklist se congeló "cerrado" en 5 puntos contra la intención T4.

**Fix (pre-23-jul, doc; se implementa en la seed de S-G).** Expandir el checklist §7 T11 a 7 puntos:
(6) recomputar cada `conclusions[].claim_digest`; (7) cada conclusión del camino crítico mapea a ≥1
attestation embebida con el mismo `claim_digest`, verdict correspondiente (pass↔verified,
fail↔refuted) y nivel dentro del techo de su `verifier_class`. **Dueño.** Dylan.

## 4 · P2 — registrar

### SF-P2-1 · cvxpy (baseline GW obligatorio Δ6) no está declarado en NINGÚN pyproject ni en `uv.lock`

`grep -c 'name = "cvxpy"' uv.lock` = 0; `grep -rl cvxpy --include=pyproject.toml` = 0. El freeze lo
lista "**Goemans-Williamson — baseline oficial obligatorio (Δ6)**" (`:284`). Contraste: qiskit SÍ
tiene hogar (extra `qaoa`). Consistente con "todas las deps en un solo PR de S-G" (§15.4), pero hoy el
baseline obligatorio no tiene declaración y la mitigación I11 (árbol GPL transitivo) no es accionable
hasta que se agregue. **Fix:** el PR único agrega cvxpy a `capabilities/{solvers,numeric}` con default
Clarabel/SCS (no ECOS/GPL) y lo lockea. **Dueño.** Sebas / Geovanni.

### SF-P2-2 · La cuarentena npm de 14 días está ACTIVA y 14 días desde hoy ya sobrepasa el evento

`pnpm-workspace.yaml:8` `minimumReleaseAge: 20160` (= 14 d) + `minimumReleaseAgeExclude` (`:17`).
Confirma y agudiza con fecha el riesgo §15.4/P2-4: 14 días desde el 20-jul = 03-ago > evento
(~1-ago). El "PR único de deps" debe traer solo npm ya fuera de cuarentena, y la reobra S-G del Studio
(SF-P1-3) debe introducir **cero** npm nuevas o pre-cargarlas hoy en `minimumReleaseAgeExclude`.
**Dueño.** Geovanni / Dylan.

### SF-P2-3 · El plano del código del Studio/`scripts` no tuvo revisor en la auditoría S-F (hueco estructural)

SF-P1-3 es su instancia más grave, pero es sistémico: la auditoría S-F barrió docs/semillas de
ciencia/ejecución/infra/confianza/equipo y **no** `apps/studio/**` ni `scripts/*`. **Fix:** un barrido
del plano Studio/scripts contra el vocabulario congelado (clase+AL, titular, Detector/Signal, Policy
0.2.0) antes del walking skeleton. **Dueño.** Dylan / Studio.

### SF-P2-4 (2ª pasada) · `titular_level = mín(conclusions[].level)` es ciego al `verdict` — falta un guard de defensa-en-profundidad

El cómputo del titular y el ítem 4 del checklist operan solo sobre `.level`, sin mirar `.verdict`
(freeze §7:118-119; campos independientes en contratos-v2:335). **No es forja** (la verificación
adversarial refutó el P0): el cálculo de la spec v3.2 §4 nunca asigna AL>0 a un no-`verified`, y la
regla de socavamiento A2 arrastra los dependientes listados a AL0 que el `mín()` sí caza; un firmante
con la llave emitiría `{verified, AL4}` directo. Lo que queda es un guard ausente que atraparía un BUG
del emisor. **Fix:** en el cómputo y el CHECK SQL, `verdict ∈ {refuted, not_required_declared,
inconclusive} ⇒ level_effective := AL0` antes del `mín()`; vector de gate `refuted+AL4 ⇒ titular AL0`.
**Dueño.** Dylan.

## 5 · Estado de los residuales de la 1ª pasada (cerrados en la 2ª)

Casi todos los vectores que la 1ª pasada dejó a medias fueron atacados a fondo en la 2ª:

- **Falsificador:** el swap de una attestation embebida bajo la firma DSSE → **SOBREVIVIÓ** (la firma
  cubre TODO el payload vía PAE; mutar un byte rompe Ed25519). `titular_level` ciego al verdict →
  degradado a P2 (SF-P2-4). `sub_run_provenance_hash` no recomputado → descartado (el nivel/verdict no
  deriva de él; attestations firmadas lo amparan). **Nuevo:** binding conclusión↔attestation (SF-P1-4).
- **Saboteador del día D:** `run_id` no colisiona (UUID4 por run); `ModelRequest` sin campos volátiles
  (clave de replay estable); air-gap estructural en dos capas (`internal:true` + sin secret de API key
  en modo replay); SSE sin pérdidas intra-stream (`seq` densa/monotónica); cert = proyección idempotente
  → **todos SOBREVIVIERON**. Orden de sacrificio y completitud de fixtures → refutados como "material
  del guion del 27-jul", no huecos abiertos.
- **Juez técnico:** GW correctamente demotado a cordura (no ancla); "exacto falta" no se materializa
  (las 6 instancias tienen óptimo exacto) → **SOBREVIVIÓ**. 6-12 nodos / media±std / baselines →
  refutados como ya-cazados (E1/E3) o con hogar comprometido (`quantum/07` fija GW+greedy).
- **Cazador:** `trust/03` SÍ lleva la marca SUPERSEDIDA; las notas de infra (Fargate/ollama) son
  pre-freeze correctamente supersedidas por §15.4/§15.7 → **SOBREVIVIERON**. No aparecieron valores
  superseded nuevos sin marca fuera del plano Studio (SF-P1-3/P1-4/P2-3).

**Único residual verdadero:** el conteo exacto de prompts del guion vs fixtures de replay — el diseño
es sólido (clave estable, fail-closed, dry-run como gate) pero "cuántos prompts y todos tienen fixture"
solo se cierra al escribir el guion, ~27-jul. No bloquea el GO.

## 6 · Lo que se intentó romper y NO se rompió (sobrevivió — evidencia de robustez)

1. **Canonicalización on-gate.** Los dos canonicalizadores COINCIDEN en todos los vectores congelados
   V1–V6 y reproducen V1 `e80b95edd718…`. Los hashes congelados NO están rotos (la no conformidad
   SF-P1-1 es estrictamente off-gate).
2. **Policy 0.2.0 (fix S-F T1).** Carga contra Pydantic (`extra=forbid`, 3 reglas);
   `model_json_schema() == verification-policy.schema.json` (True); **20/20** tests verdes. Vocabulario
   supersedido coherente — aunque su evaluador aún no sea construible (SF-P1-2).
3. **Re-lock pandapower (fix S-F P0-1).** `uv.lock` resuelve pandapower **3.3.0** + numpy **2.5.1**;
   extra `sim` `pandapower>=3.3`.
4. **Segunda ancla ieee30 (§15.3 [S-F]).** JSON NO mutados (`metodos: ['cpsat']`), óptimos **35** /
   **32170** y digests embebidos coinciden con la tabla del freeze. Doctrina aplicada fielmente.
5. **Falla sembrada (§15.5 [S-F]).** Flip del bus **1** sobre `ieee14-flujo` → corte **32597**,
   r=**0.5712** (la degradación MÁXIMA de los 14 flips), x₀=0 preservado; bus **7** → r=**1.0** (mina
   degenerada documentada). Confirmado 3× (2 pasadas + verificación independiente).
6. **Gates constitucionales estructurales.** append-only que falla fuerte (REVOKE + trigger), verdict
   tri-estado, `Detector`/`Signal` disjunto, `AuthzDecision` en egreso, CHECK `pass ⇒ ancla-no-null`
   (necesario, aunque insuficiente — SF-P0-1). Import-linter con 9 contratos.
7. **Integridad del payload DSSE (2ª pasada).** Intercambiar/editar una attestation EMBEBIDA y
   re-verificar → falla: la firma única cubre todo el payload vía PAE; cualquier byte mutado rompe
   Ed25519. "Una sola firma ampara cert + attestations" es sólida.
8. **Día D operativo (2ª pasada).** `run_id` = UUID4 fresco por run (sin colisión de PK); `ModelRequest`
   sin campos volátiles (clave de replay estable); air-gap estructural de dos capas; SSE sin pérdidas
   intra-stream; certificado = proyección idempotente (sin doble emisión en replay).
9. **Ciencia bajo lupa hostil (2ª pasada).** GW demotado a cordura (UB≥óptimo), no ancla; las 6
   instancias tienen óptimo exacto ⇒ "exacto falta" no se materializa; baselines GW+greedy con hogar
   en `quantum/07`.
10. **Contratos "sin cuerpo" declarados, no huérfanos (2ª pasada).** `DistributionManifest` tiene hogar
    y campos en trust/06; R-V2/AcceptanceAuthority y S2 (Signer≠Verifier) son limitaciones Fase 1
    DECLARADAS en `assumptions` (freeze §4:91) — trabajo futuro con dueño, no huecos que permitan un
    estado prohibido.

## 7 · Cierre

**GO a S-G, condicionado:** aplicar SF-P0-1 y SF-P1-1/2/3/4 antes del 23-jul y registrar los P2. Dos
pasadas adversariales (la 2ª completa) sin invalidar ninguna decisión congelada; el único P0 tiene fix
pre-23; los residuales de la 1ª pasada se cerraron mayoritariamente como SOBREVIVIÓ. El diseño post-S-F
**sobrevive** el stress test.

Dueños reales cierran (la auditoría no los sustituye): **Dylan** — SF-P0-1 (6º chequeo de
`verify-bundle`), SF-P1-1 (adoptar un `C(x)` ECMAScript-conforme — `rfc8785` — NO unificar sobre el
engine, que también diverge), SF-P1-2 (portador de `claim_type` + mapeo anchor_kind), SF-P1-4 (expandir
el checklist T11 a 7 puntos), SF-P1-3/P2-3/P2-4 (migrar Studio a clase+AL + regenerar el fixture/generator
del cert + guard de titular). **Sebas/Geovanni** — SF-P2-1 (cvxpy en el PR único). **Geovanni** —
SF-P2-2 (inventario npm vs cuarentena).

> **Método.** 2 pasadas de panel de 5 atacantes (postura destrucción) + verificación adversarial por
> hallazgo. 1ª pasada (20-jul): cortada por límite de sesión, rescate de transcripts + verificación a
> mano. 2ª pasada (21-jul): 18 agentes, 0 errores, verificación adversarial completa; corrigió SF-P1-1
> (re-verificado con `node`) y cerró los residuales.

## 8 · Registro de aplicación de fixes (2026-07-21, esta rama)

Aplicados en el nivel donde su artefacto existe HOY: **código** para lo ya construido, **spec congelada**
(supersesión marcada `[S-F stress · SF-*]`, regla del freeze — jamás edición silenciosa) para lo que S-G
construirá. Gates verdes: `pytest` 112 pass · `ruff` · `import-linter` 9/9 · `markdownlint` · `prettier`
· hook de marca. Los vectores congelados V1–V6 se re-verificaron intactos tras el fix.

**Aplicado — código + test (TDD, RED→GREEN):**

- **SF-P1-1** — `engine/src/blite/certificate/canonical.py::_format_number` ahora conforma con ECMAScript
  en la banda `[1e-6, 1e-4)` (notación fija), preservando el path entero (`1e21`) y los vectores
  congelados. Test nuevo `test_ecmascript_fixed_notation_band` (10 casos, ground-truth `node`).
  `scripts/gen-canonicalization-vectors.py` importa ahora `canonicalize` del engine (fuente única, sin
  2ª copia que derive). Anexo §2 (nota de hazard) + tabla V5 (3 vectores de banda como gate) corregidos.

**Aplicado — spec congelada (lo que S-G implementará):**

- **SF-P0-1 + SF-P1-4 + SF-P2-4** — freeze §7: el checklist T11 de `verify-bundle` pasa de 5 a **7 puntos**
  (resolución de `anchor_digest` contra descriptores del Bundle · recompute de `conclusions[].claim_digest`
  · binding conclusión↔attestation), y el punto 4 + la regla T2 acoplan `verdict → level_efectivo`
  (`refuted/inconclusive/not_required ⇒ AL0`).
- **SF-P1-2** — freeze §6: decisión de portadores registrada (el claim carga `claim_type` + `is_conclusion`;
  la matriz casa por criticidad computada; `required_anchors` se comprueba contra `anchor_kind`). Semillas
  v2 §5 suman `anchor_kind` (contratos + esquema), alineando con `attestation.py` que ya lo tenía.

**Queda para S-G (traducción de código ya planeada por el freeze — "Traducción a Pydantic/SQL real = S-G"):**

- **SF-P1-3 / P2-3** — migrar el plano de verificación del Studio y `engine/verification/attestation.py`
  (aún en `rung`) a clase+AL, y regenerar el fixture + generador del cert al esquema S-F (con `policy_id`
  0.2.0). La spec ya es correcta; solo el código va atrás. Frontend con su propia toolchain → sesión S-G.
- **SF-P1-2 (materialización)** — el seed Pydantic de la Policy que implementa la decisión de §6.
- **SF-P2-1** — cvxpy entra en el PR único de deps de S-G (con default Clarabel/SCS). **SF-P2-2** —
  inventario npm vs cuarentena antes de agregar deps del Studio.

> **Método.** 2 pasadas de panel de 5 atacantes (postura destrucción) + verificación adversarial por
> hallazgo. 1ª pasada (20-jul): cortada por límite de sesión, rescate de transcripts + verificación a
> mano. 2ª pasada (21-jul): 18 agentes, 0 errores, verificación adversarial completa; corrigió SF-P1-1
> (re-verificado con `node`) y cerró los residuales.
