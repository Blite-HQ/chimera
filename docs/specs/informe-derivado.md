# Spec — el informe como derivación (figuras + PDF Typst byte-reproducible, costura C↔B, R4)

**Gobernada por:** freeze §7 (Certificate/Bundle — `deliverables`, binding C3) · freeze §12
(`Artifact`/`ContentStore`) · freeze §13 (Run jerárquico / claims al raíz) · **Dueño:** Dylan ·
**Estado:** SPEC (2026-07-24)

> Insumo: `docs/planeado/03-research-estado-del-arte.md` §R4 · `knowledge/trust/02-trust-certificate-attestation.md`
> (forma Statement/predicate que este documento reutiliza para "cifra→certificado") · **misma receta que
> [`capability-ingesta.md`](capability-ingesta.md)** (R2) — el informe entero es una instancia más de esa
> receta, aplicada a un dominio distinto (plotting/tipografía en vez de GIS). Esta spec no redefine
> `Provenance`/`DerivationRecipe`; los usa tal cual.

## Contrato

**"El informe ES una derivación más" (R4) — cero maquinaria de confianza nueva.** Cada figura y el PDF
final son instancias `DerivationProvenance` (capability-ingesta.md §Contrato) donde el dominio de la
capability es "reporte", no "ingesta". Se reutiliza el mismo triplete `inputs[{ref,digest}] +
recipe{capability,version,params_digest,code_ref} + assertions[]`.

### (a) Cada figura = instancia derivada

Módulo Fase 1 (Dylan, no existe hoy): `capabilities/report/src/blite_cap_report/` (mismo patrón
`blite_cap_<domain>` de `blite_cap_sim`/`blite_cap_quantum`) — `render_figure`/`compile_pdf` viven ahí;
ambos importan `DerivationProvenance` de `engine/src/blite/verification/provenance.py`
(capability-ingesta.md) sin redefinirla.

**[S3 2026-07-30]** Existe (D-N7): `capabilities/report/src/blite_cap_report/` está en el árbol
(con su gate propio `ADR-008-report` en import-linter, `pyproject.toml:194`) — el «no existe
hoy» de arriba quedó histórico.

Capability `blite.report.render_figure` (`side_effects: pure`, `interaction: request_response` —
CapabilityManifest v2, misma discrepancia con `sdk/manifest.py` flaggeada en `capability-ingesta.md`, no
se repite aquí): `inputs = [{ref: "conclusion:<claim_digest>", digest: <digest de la instancia
certificada que la figura grafica>}, ...]`, `recipe.params_digest = C(x)` sobre `{dpi, figsize, style,
data_selection, ...}` (los parámetros de matplotlib que determinan el render). El output es un
`Artifact` PNG/SVG cuyo digest se guarda vía `ContentStore.put()` — sin excepción a la regla "el digest
es la identidad" (O3).

**Determinismo matplotlib (sin esto, dos corridas honestas producen bytes distintos y el PDF deja de ser
recomputable):**

- `matplotlib.rcParams["svg.hashsalt"]` fijo a una constante del repo (nunca aleatorio — el default de
  matplotlib usa un salt basado en `id()`/hash de proceso, no reproducible entre corridas).
- `SOURCE_DATE_EPOCH` fijado (env var, convención reproducible-builds) — cualquier metadata de timestamp
  que matplotlib/backends de imagen pudieran embeber usa este valor, no `datetime.now()`.

### (b) El PDF = derivación final con Typst

`typst-py` (sin toolchain LaTeX) compila: plantilla versionada con su propio digest + las figuras (por
digest, paso (a)) + las cifras citadas (por digest, ver binding C3 abajo) → `typst.compile()` con
`set document(date: none)` explícito en la plantilla ⇒ **PDF byte-reproducible y digestable**. Esta
propiedad es la razón de descartar LaTeX/Quarto (abajo): ninguno de los dos garantiza bytes idénticos
entre corridas con el mismo input por defecto.

- `recipe.inputs` del PDF = `[{ref: "template", digest: <digest de la plantilla Typst>}] +
[{ref: "figure:<n>", digest: <digest de cada figura (a)>}] + [{ref: "cifra:<n>", digest: <claim_digest o
attestation_digest citado>}]` — el PDF hereda TODOS los digests de sus insumos, no solo su propio
  contenido.
- **Verificar el informe = recompilar y comparar digests + DSSE offline**: el mismo patrón que
  `scripts/verify-bundle.py` (freeze §7) aplicado a este dominio — un verificador independiente
  recompila desde los mismos inputs pinneados por digest y compara el digest del PDF resultante contra
  el `deliverable` firmado en el certificado. Sin diferencia de bytes, sin re-confiar en quien lo generó.

### (c) Trazabilidad visible (patrón showyourwork)

Cada figura y cada cifra citada en el cuerpo del informe lleva al pie `sha256:<digest> · cert:<id>` —
visible en el documento mismo, no solo en un anexo separado. El anexo de verificación es una tabla
`artefacto → digest → certificado` que enumera TODOS los deliverables del informe (plantilla, cada
figura, el PDF final) — el mismo principio que el checklist de 7 puntos de `verify-bundle.py` (freeze
§7): nada se afirma sin que su digest esté ahí para recomputar.

### Binding cifra→certificado (C3) — la regla dura de esta spec

Toda cifra numérica citada en el informe **DEBE** resolver, por su digest, a una entrada real en
`conclusions[]`/`attestations[]`/`deliverables[]` del certificado EMITIDO para el run que la produjo
(freeze §7). Esto se valida como una `assertion` MÁS dentro de la receta del PDF (mismo mecanismo de
"validación en frontera dentro de la receta" de `capability-ingesta.md`): si una cifra no resuelve, la
derivación del PDF **falla al generarse** (fail-closed) — nunca un informe "aproximado" o con una cifra
sin sustento. Es la aplicación literal de C3 (binding cifra→certificado) al dominio del informe.

### Trazabilidad al run raíz

El informe corre como **sub-run** del run raíz que produjo los resultados que reporta (freeze §13:
"es sub-run SOLO la unidad que produce claims propios que el certificado citará" — el informe SÍ produce
un claim propio, `claim_type: "derivation"`, ya registrado en `perfil-stem-v1-0.md` §1, cero extensión
nueva de claim_type aquí a diferencia de `capability-ingesta.md`). Aporta al raíz vía `●ClaimEmitted
{claim_digest, sub_run_id, sub_run_provenance_hash}` (freeze §13, ya congelado, sin cambio de forma). El
PDF final entra a `deliverables[]` del certificado del RAÍZ (o del propio sub-run si el informe emite su
propio certificado amortizado — ambos patrones ya existen en el freeze, esta spec no elige entre ellos,
lo deja a criterio de implementación Fase 1 porque no cambia ningún contrato).

### Descartes (con causa, R4)

| Alternativa                               | Por qué NO                                                                                                                                      |
| ----------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| LaTeX                                     | Toolchain pesado; sin garantía de bytes idénticos entre corridas por defecto (timestamps, fuentes)                                              |
| Quarto/papermill EN el camino certificado | Autoría humana interactiva, no determinista — válido como HERRAMIENTA de autoría fuera del camino, nunca como paso de la derivación certificada |
| C2PA                                      | Vigilar como estándar de procedencia de medios, no adoptar este mes — fuera del alcance del mínimo (§15.4 del freeze)                           |
| WeasyPrint                                | Solo FALLBACK si Typst no está disponible en el entorno de despliegue — nunca el camino primario/certificado                                    |

## Interfaces con otros dominios

| Interfaz                                                                          | Dominio                       | Estado                                                                      |
| --------------------------------------------------------------------------------- | ----------------------------- | --------------------------------------------------------------------------- |
| Receta de derivación (`Provenance`, `ContentStore`, `C(x)`)                       | costura (Sebas+Dylan)         | VERDE — reutiliza [`capability-ingesta.md`](capability-ingesta.md) tal cual |
| `deliverables[{artifact_ref, digest}]` del predicate                              | confianza (Dylan)             | VERDE (freeze §7, reutilizado sin cambio de forma)                          |
| Run jerárquico / `●ClaimEmitted{sub_run_id, sub_run_provenance_hash}`             | frontera (Dylan+Steven)       | VERDE (freeze §13, reutilizado tal cual)                                    |
| `claim_type: "derivation"`                                                        | confianza (Dylan)             | VERDE (`perfil-stem-v1-0.md` §1, ya registrado — cero extensión nueva aquí) |
| `verify-bundle.py` (patrón de verificación offline)                               | confianza (Dylan)             | VERDE (freeze §7, mismo patrón aplicado al dominio del informe)             |
| `CapabilityManifest` v2 (`blite.report.render_figure`/`blite.report.compile_pdf`) | A · ejecución (Steven)        | SPEC — misma discrepancia flaggeada en `capability-ingesta.md`              |
| Superficie visual del Studio (badges `sha256:… · cert:<id>`)                      | D · superficie visual (Dylan) | SPEC — frontera con `superficie-visual.md`, no decidida aquí                |

## Fronteras (qué NO decide esta spec)

- No decide el diseño visual/tipográfico de la plantilla Typst — contenido de autoría, no contrato.
- No decide si el informe emite certificado propio o cuelga del certificado del raíz — ambos patrones ya
  están congelados (§7 modo amortizado / §13 run jerárquico); la elección es de implementación Fase 1.
- No re-implementa `ContentStore`/`C(x)`/`Provenance` — reutiliza `capability-ingesta.md` sin cambios.
- No decide cómo el Studio renderiza las badges de verificación (frontera con `superficie-visual.md`).
- No adopta Quarto/papermill/C2PA como dependencias — quedan descartadas explícitamente arriba, no como
  pregunta abierta.

## Tests de contrato (fixtures de costura)

`tests/fixtures/contract/informe/figura-example.json` y `tests/fixtures/contract/informe/pdf-example.json`
(digests + receta, NO el PDF binario), espejados a
`apps/studio/src/fixtures/contract/informe/*.json` — **declarados, no generados** (las capabilities
`render_figure`/`compile_pdf` no existen hoy).

**[S3 2026-07-30]** Generados (D-N8): `tests/fixtures/contract/informe/{figura-example,pdf-example}.json`
y su espejo en `apps/studio/src/fixtures/contract/informe/` existen commiteados — «declarados,
no generados» quedó histórico.

## Tests semilla

- `tests/seeds/test_seed_informe_derivado.py` — `xfail(strict=False)`, Fase 1 Dylan: fija la forma de la
  receta aplicada al informe y la regla dura "PDF byte-reproducible" (dos compilaciones del mismo input
  producen el mismo digest).
