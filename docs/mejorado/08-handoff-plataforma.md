# Handoff de PLATAFORMA (dominio O) → sesión de control

> **Qué es esto.** Todo lo que la sesión PLATAFORMA encontró y **no le tocaba
> ejecutar**, con lo que hace falta para decidirlo sin volver a investigarlo.
> No es un resumen de lo hecho —eso está en el ledger, entradas #153–#169— sino
> la lista de lo que necesita a otra persona, otra sesión o una ceremonia.
>
> Cada ítem trae: qué es · por qué no se ejecutó acá · qué hay que decidir · el
> primer paso concreto.

## 1 · Bloqueadores del flip

### 1.1 · El geojson crudo del ICE, y por qué la salida obvia está mal

**Qué es.** `knowledge/islanding/raw/ice-*.geojson` es una copia verbatim de dos
datasets del portal abierto del ICE. Su catálogo declara `accessLevel: public`
pero **ningún identificador de licencia estándar** — y «datos abiertos» no es lo
mismo que permiso explícito para redistribuir obras derivadas (`NOTICE` §2).

**Ya cerrado (Dylan, 2026-08-08):** esos datos eran el ejemplo del reto 1, la
plataforma no depende de ellos, y **no se publican como dataset** — el catálogo
de `GET /datasets` declara solo corpus propios (#167).

**Lo que queda abierto:** publicar el repo publica el árbol. Y acá está el
hallazgo que cambia la respuesta:

> **La evidencia de Nexus se ancla a instancias derivadas del ICE.**
> `knowledge/nexus/` —las corridas reales en H2-1LE, la evidencia más fuerte del
> proyecto— cuelga de `cr6-*` y `cr8-*`, que salen del ICE.
> **Borrarlas la huérfana.**

**Qué hay que decidir.** Entre dos, no tres:

| opción                                                | costo                                                            |
| ----------------------------------------------------- | ---------------------------------------------------------------- |
| (a) conseguir términos explícitos del ICE             | tiempo humano; el portal sugiere que existe un doc «UsoOpenData» |
| (b) **sacar el geojson crudo, conservar lo derivado** | se pierde poder re-correr `gen_corpus_ice.py` desde el árbol     |

(b) es la recomendada: lo que quedaría en el árbol es un grafo con pesos
enteros, no la geodata de subestaciones y líneas — el mismo razonamiento que
`NOTICE` §1 ya usa para pandapower. La receta y los digests se quedan, así que
cualquiera con los datos del portal puede re-derivar y comprobar.

**Primer paso si se elige (b).** Dos comprobaciones que no son opcionales:

1. `knowledge/nexus/index.json` y `consensus.json` — confirmar que no referencian
   el geojson, solo las instancias derivadas.
2. `capabilities/ingesta/tests/test_geojson_to_graph.py` lee el crudo: hay que
   moverlo a un fixture propio antes de sacar el archivo.

### 1.2 · Historia del repo

Sin cambios: por decisión de Dylan la corrección integral va **después de
Mejorado**, en una pasada única. El árbol vendorizado de terceros salió de HEAD
pero sigue en los commits.

## 2 · Necesitan ceremonia o son de otro dominio

### 2.1 · Generalizar `ExternalImportStatement` — ceremonia

C-12 pedía reusar la evidencia externa para la importación MCP. **No se puede
sin mentir:** `ExternalImportStatement` exige `circuit_digest` y
`shots_requested` — es un import de job cuántico con nombre genérico. Una
llamada a un tool MCP no tiene circuito ni shots, y rellenarlos sería fabricar
campos para pasar un validador.

Se resolvió con un predicado propio y **aditivo**
(`https://blite.dev/McpToolImport/v1`, `api/src/chimera_api/mcp_wiring.py`) que
no toca nada congelado. Generalizar el modelo original sí toca contrato
congelado ⇒ **ceremonia**, y una sesión de dominio no la ejecuta sola. El día
que se haga, los dos predicados se fusionan.

### 2.2 · Los corpus cableados por ruta literal en el API — es G3

`api/src/chimera_api/runs.py` (`_ISLANDING_CORPUS_DIR`) e
`instance_verifiers.py` (`_TFIM_CORPUS_DIR`, `_TABULAR_CORPUS_DIR`) apuntan a
tres directorios de corpus **por ruta escrita a mano**. Es la última atadura
grande del API a retos concretos.

El `datasets:` del `DistributionManifest` (#167) es la forma de quitárselo —
ya existe y ya se lee. Pero rehacer la resolución de verificadores es **G3
(«dispatch por clase de problema»)**, del dominio Generalidad. Reportado, no
tocado.

### 2.3 · Las 2 violaciones de depcruise del Studio — otro agente

`App.tsx ↔ router.tsx` circular · `App.tsx → gatewayClient.ts` contra F3.
Asignadas a otro agente por Dylan (2026-08-06). **Es lo único que mantiene rojo
el job Web**; todos los demás jobs de CI están en verde.

### 2.4 · O7 (deck.gl) — bloqueado, no omitido

Su umbral exige medir FPS sobre un overlay de mapa que **solo existe tras
V1/M18**, en la sesión V. El encargo dice explícitamente que O7 no es
compromiso. Queda para reevaluar cuando ese overlay exista.

Con el reencuadre de Dylan (2026-08-08), además, el mapa debe diseñarse como
**artifact genérico de render geoespacial** —disparado por el TIPO de dato, no
por el reto— al estilo de los artifacts de chat. Eso cambia dónde vive: registry
de lentes, no una vista del shell.

## 3 · Coordinación de merge

### 3.1 · Numeración del ledger

Esta sesión usó **#153–#169**. Las sesiones C-2 y V corrieron en paralelo y
pueden haber usado los mismos números. **La sesión de control resuelve la
colisión al integrar** — no se renumeró acá para no reescribir commits ya
empujados.

### 3.2 · La rama de ejercicio ya se puede podar

`ejercicio/sf-ratificacion-simulada` sostenía el pin `68af0c1` del que dependía
el método del protocolo de convergencia (hallazgo 10 del handoff S3). El método
está portado al árbol en `docs/protocolo-convergencia.md` (#168). **El hallazgo
10 queda cerrado y la rama es podable.**

### 3.3 · Dependabot: las alertas siguen abiertas en `main`

Las entradas #163/#165 cerraron 15 vulnerabilidades, pero **en esta rama**. El remoto sigue
reportando 14 en la rama por defecto (9 high, 5 moderate) y seguirá haciéndolo
hasta que esto llegue a `main`. No es una regresión: es que el arreglo aún no
está allá.

### 3.4 · Dependencia nueva de desarrollo

`mlcroissant>=1.1.0` entró al grupo `dev` (7 paquetes transitivos nuevos). Es el
validador de referencia de MLCommons y lo usa
`tests/integration/test_croissant_export.py`. **No viaja a las imágenes**: los
Dockerfiles instalan con `--no-dev`.

### 3.5 · Empujar cambios que tocan `.github/workflows/`

La cuenta activa de `gh` (`sebastianZO6`) **no tiene el scope `workflow`**; la
cuenta `dchavesh` sí. Un push que toque `ci.yml` se rechaza con la primera y
pasa con la segunda. Se cambia con `gh auth switch --user dchavesh` y **se
devuelve** al terminar, para no alterarles el `gh` a las otras sesiones.

## 4 · Flakes conocidos (reportados, no arreglados)

| test                                                                                                     | síntoma                                                                                                                                                  |
| -------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `apps/studio/src/lenses/registry.test.ts`                                                                | «Test timed out in 5000ms» en un `await import()` dinámico. Depende de carga: 299/299 con la máquina ociosa, falla si hay un build de Docker en paralelo |
| `capabilities/ml/tests/test_integration_reto2.py` (`test_both_arms_produce_metrics_with_aligned_shapes`) | falló una vez, verde en las repeticiones                                                                                                                 |

Ninguno de los dos es de esta sesión ni se tocó. Si el job Web se vuelve
intermitente después de arreglar depcruise, el primero es el sospechoso.

## 5 · Estado de las compuertas al cierre

Worktree `mejorado/plataforma`, 2026-08-10:

- pytest **1392 passed** / 13 skipped / 6 xfailed / 4 xpassed · cobertura **90.23 %**
- `lint-imports` **18 contratos, 0 rotos**
- `ruff check` · `ruff format --check` · `pyright` — limpios
- Studio **299 passed / 32 files** (con el flake de §4)
- `docs:lint` · `format:check` — limpios
- `verify_corpus_digests` **24/24** internos y contra tabla pinneada
- gitleaks **sin hallazgos** en árbol e historia
- **CI: todos los jobs en verde salvo Web**, que falla por §2.3
