# Nota 01 — Corpus de benchmarks con óptimos conocidos (IEEE 9/14/30)

**Ítem del plan (§4, Sebas):** el entregable central que faltó de la investigación del plano cuántico — valores óptimos concretos de IEEE 9/14/30 (+ la red CR estilizada), congelados como vectores con el mismo rol que G1–G6 de trust/10 (ver `knowledge/quantum/README.md`, pendiente №1).
**Fecha:** 2026-07-14 · **Estado:** investigación de consolidación (Dylan) — pendiente validación y ratificación de Sebas.
**Fuentes:** `knowledge/quantum/02-recetario-formulacion-por-reto.md` §1 (convención Q simétrica/maximización, Max-Cut, canonicalización x₀=0) · `knowledge/trust/10-spec-exact-solver-verifier-cpsat.md` §1.4–1.6 (determinismo, escalado entero, formulación Max-Cut de referencia, vectores G1–G6) · `knowledge/trust/17-evaluacion-inspect-tres-planos.md` (corpus runner rung 3) · `pandapower.networks` (case9/case14/case30) verificado en vivo 2026-07-14 · `docs/arquitectura-reconciliada.md` (benchmarks IEEE + red CR) · `knowledge/quantum/00-kb-fuentes.md` §1.5 (IEEE vía pandapower = mismo benchmark que REGRID-QAOA).

---

## 1 · Patrón / mecanismo

### 1.1 Qué es el corpus y dónde vive

`knowledge/islanding/corpus/` contiene **6 instancias de Max-Cut con óptimo exacto conocido** — un JSON por instancia×convención — generadas desde las topologías IEEE 9/14/30 de `pandapower.networks`. Son vectores de referencia (datos versionados con digest, no código — mismo principio que "λ es dato" de quantum/02 §1.3): cualquier proponente (QAOA, heurística clásica) que corra sobre estas instancias tiene un óptimo contra el cual calcular su approximation ratio, y el `ExactSolverVerifier` (trust/10) tiene instancias medianas de calibración además de los G1–G6 hechos a mano.

**La doble ancla independiente ES la tesis del proyecto aplicada al corpus:** ningún óptimo se publica con una sola fuente cuando dos son posibles. Cada valor de n≤14 está probado por dos métodos que no comparten código ni supuestos — CP-SAT (búsqueda exacta con prueba de optimalidad) y fuerza bruta (enumeración completa de 2^(n−1) asignaciones) — y el generador **aborta sin escribir nada** si discrepan (fail-loud, espejo de la regla "mejor que el óptimo ⇒ bug" de trust/10 §1.2). Es el mismo patrón CP-SAT ↔ enumeración de trust/10 §1.1, ahora produciendo el corpus en vez de verificando un claim.

### 1.2 Del caso IEEE al grafo

- **Nodos = buses** de la red. Se relabelan a `0..n−1` en orden ascendente del índice de bus de pandapower (en case9/14/30 el índice ya es `0..n−1`, así que el relabel es la identidad — pero la regla queda fijada para cualquier caso futuro).
- **Aristas = líneas + transformadores en servicio** (`net.line[net.line.in_service]` y `net.trafo[net.trafo.in_service]`). Los trafos conectan buses igual que las líneas y omitirlos desconectaría el grafo (en case9 los tres generadores cuelgan de trafos). No hay ramas fuera de servicio en ninguno de los tres casos.
- **Ramas paralelas** entre el mismo par de buses se agregan sumando su contribución (cortar el par implica abrir todas sus ramas). En case9/14/30 no existe ninguna (0 paralelas en los tres) — la regla queda definida, no ejercitada.
- **Conexidad verificada** con networkx (`nx.is_connected`) antes de publicar: los tres grafos son conexos y sin nodos aislados.

### 1.3 Las DOS convenciones de peso

| Convención | Peso de la rama                                                                  | `escala` | Racional                                                                                                                                                                                                 |
| ---------- | -------------------------------------------------------------------------------- | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `uniforme` | w_ij = 1 por rama                                                                | 1        | Topología pura: el corte cuenta ramas abiertas. Pesos enteros ⇒ exacto, `abs_tol = 0` (trust/10 §1.5, primer camino).                                                                                    |
| `flujo`    | w_ij = round(100·\|P\|) con \|P\| = flujo de potencia activa en MW del caso base | 100      | El corte pondera lo que "cuesta" abrir cada rama en el punto de operación. `pp.runpp(net)` con parámetros default; \|P\| = `res_line.p_from_mw` (líneas) / `res_trafo.p_hv_mw` (trafos), valor absoluto. |

**Factor de escala exacto (convención `flujo`):** `S = 100`, es decir `w_entero = round(100 · |p_mw|)` — resolución de 0.01 MW. Coherente con el escalado entero de trust/10 §1.5 (escalar-y-redondear, campo `scale` del `evidence.differential`). Punto clave de honestidad contable: **el redondeo es parte de la definición de la instancia, no error del solver** — el `optimo` publicado es exacto _para la instancia entera publicada_ (las `aristas` del JSON ya traen `w` entero). Quien recompute flujos con otra versión de pandapower debe comparar contra el **digest** del JSON congelado, que es la fuente de verdad; el margen mínimo del redondeo al umbral x.5 observado en la generación fue 0.0298 (ieee9), 0.0322 (ieee14) y 0.0090 (ieee30), en unidades de 0.01 MW — chico en ieee30, por eso la regla es "el archivo congelado manda; una regeneración que no reproduzca el digest se reporta, no se sobreescribe".

**Aristas con w = 0 en `flujo`:** `(6,7)` en ieee14 y `(8,10)` en ieee30 — ramas hacia buses de condensador síncrono cuyo flujo activo del caso base es < 0.005 MW. Se **conservan** en `aristas` (preservan la topología; la conexidad se chequea sobre el grafo completo) y no aportan al valor del corte.

### 1.4 Las dos anclas y sus parámetros

**Ancla 1 — CP-SAT (ortools 9.15.6755):** la formulación Max-Cut de referencia de trust/10 §1.5, literal: binaria `x_i`, variable de arista `y_ij` forzada a `x_i XOR x_j` con las 4 restricciones lineales, `maximize Σ w_ij·y_ij`, y `x_0 = 0` (ruptura de simetría). Parámetros de determinismo de trust/10 §1.4, los tres: `num_search_workers = 1`, `random_seed = 1`, `max_deterministic_time = 300.0` (tiempo determinista, no de pared). Los 6 solves terminaron `OPTIMAL` (subsegundo; ninguno se acercó al presupuesto). El objetivo reportado por el solver se **recomputa** contra la asignación devuelta antes de aceptarlo (paso 1 de trust/10 §1.1 aplicado al propio corpus).

**Ancla 2 — fuerza bruta (n ≤ 14):** enumeración completa de las 2^(n−1) asignaciones con `x_0 = 0` fijo (2⁸ = 256 para ieee9, 2¹³ = 8 192 para ieee14) y recómputo directo del corte. Sin solver, auditable por inspección.

**IEEE 30 (n = 30):** solo CP-SAT — 2²⁹ ≈ 5.4×10⁸ asignaciones quedan fuera del presupuesto de enumeración en Python puro. CP-SAT probó `OPTIMAL` (no hizo falta registrar cota+incumbente), así que el valor es exacto, pero hoy tiene **una sola ancla**; `metodos: ["cpsat"]` lo dice explícitamente. **Segunda ancla — DECIDIDA en S-E (2026-07-18, freeze §15.3; ratificación final de Sebas = correrla y comparar digests):** **enumeración exhaustiva vectorizada** (numpy por bloques, x₀=0, las 2²⁹ asignaciones — cero dependencias nuevas, cero código compartido con CP-SAT), integrada a este script §1.9 **(⚠ [S-F-real · 2026-07-21]: aún NO integrada — `FUERZA_BRUTA_MAX_N=14`; re-estampado pendiente de Sebas)** con presupuesto explícito; al ratificar, `metodos` pasa a `["cpsat","bruteforce_vectorized"]` y el digest se re-estampa. La cota superior del SDP de Goemans-Williamson (cvxpy, ya dep obligatoria) se registra como **chequeo de cordura** (UB ≥ óptimo), no como ancla.

### 1.5 Canonicalización de la asignación (documentada)

1. **`x_0 = 0` siempre** — rompe la simetría de complemento (x ↔ 1−x da el mismo corte), coherente con trust/10 §1.5 y con la decodificación canónica de quantum/02 §1.6.
2. El **valor** óptimo es único; la **asignación** puede no serlo (varios argmax). La `asignacion_canonica` publicada es _una testigo_: para n ≤ 14, la **lexicográficamente mínima** entre todas las óptimas con `x_0 = 0` (determinista por enumeración en orden lexicográfico); para ieee30, la asignación devuelta por CP-SAT determinista (workers=1, seed=1), recomputada. Un proponente que encuentre _otra_ asignación con el mismo valor NO está en conflicto con el corpus — el ancla es el valor `optimo`.

### 1.6 Forma del JSON y digest

Un archivo por instancia×convención: `<instancia>-<convencion>.json` con claves `{instancia, convencion, n_nodos, aristas: [[i,j,w]...], escala, optimo, asignacion_canonica, metodos, solver_status, digest}` (más `notas/incumbente/cota_superior` solo si un solve no probara óptimo — no ocurrió). `aristas` ordenadas por `(i,j)` con `i < j`.

**`digest` = SHA-256 del JSON canónico — claves ordenadas, sin espacios (separadores `,` y `:`), `ensure_ascii` — SIN el campo `digest`.** Verificación independiente de una línea (ambas reproducen los 6 digests, verificado 2026-07-14):

```bash
jq -cjS 'del(.digest)' ieee9-uniforme.json | sha256sum
```

```python
import json, hashlib
reg = json.load(open("ieee9-uniforme.json")); d = reg.pop("digest")
assert hashlib.sha256(json.dumps(reg, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest() == d
```

**Identidad como ancla (congelada en S-E, 2026-07-18):** el mapeo `dataset_id`↔digest quedó
fijado en `docs/contract-freeze.md` §15.3 — `dataset_id = "islanding-corpus/<instancia>-<convencion>@v1"`,
digest = el embebido de cada JSON (esta regla §1.6). IDs reservados para cr8/cr6 (§1.8); sus
digests se estampan en el freeze al congelar los JSON.

### 1.7 Resultados (tabla resumen)

| Instancia | Convención | n   | \|E\| | W (peso total) | **Óptimo** | Métodos            | `solver_status` | digest (prefijo) |
| --------- | ---------- | --- | ----- | -------------- | ---------- | ------------------ | --------------- | ---------------- |
| ieee9     | uniforme   | 9   | 9     | 9              | **9**      | cpsat + bruteforce | OPTIMAL         | `dee38cdeea9b`   |
| ieee9     | flujo      | 9   | 9     | 63 769         | **63 769** | cpsat + bruteforce | OPTIMAL         | `59fb22e6ec0a`   |
| ieee14    | uniforme   | 14  | 20    | 20             | **16**     | cpsat + bruteforce | OPTIMAL         | `fb9c3780d9cf`   |
| ieee14    | flujo      | 14  | 20    | 66 263         | **57 070** | cpsat + bruteforce | OPTIMAL         | `c7880bb0d254`   |
| ieee30    | uniforme   | 30  | 41    | 41             | **35**     | cpsat              | OPTIMAL         | `a864122e8358`   |
| ieee30    | flujo      | 30  | 41    | 35 890         | **32 170** | cpsat              | OPTIMAL         | `a3aed52a8c59`   |

**Chequeo de cordura estilo G1–G6 (racional a mano):** el grafo de ieee9 es **bipartito** (los 3 buses de generación cuelgan por trafo de un anillo par), así que el corte máximo corta TODAS las aristas: óptimo uniforme = \|E\| = 9 y óptimo flujo = W = 63 769. Ambas anclas lo confirman. Para ieee14/ieee30 no hay racional de una línea — para eso están las dos anclas.

Las anclas **coincidieron en las 4 instancias donde ambas corren** (cero conflictos). Versiones exactas de la generación: pandapower 3.3.3 · networkx 3.6.1 · ortools 9.15.6755 · numpy 2.5.0 · Python del workspace (`uv run python`).

### 1.8 La red CR (cr8 + cr6) — ESPECIFICADA en S-E (P0-7); datos en curso, dueño Sebas

La definición completa (lista de aristas + pesos) **no existe en el repo** — solo referencias agregadas, y con eso no se congela un vector (inventarla violaría todo el punto del corpus). Lo que se sabe, con fuente:

- **n = 8, W = 5.9, τ̂ = 0.3** ⇒ λ > W/τ̂² = 65.6 (`knowledge/quantum/02` §1.3).
- Degeneración del óptimo **g = 2** (solo el par complemento) usada en el cálculo de shots (`knowledge/quantum/04` §3: "Grid CR (n=8, g=2): p ≈ 0.008 ⇒ ~590").
- Es un "grafo sintético de 8 subestaciones CR" (`knowledge/quantum/00` §1.5), "modelo estilizado de la red CR (ICE)" (`docs/arquitectura-reconciliada.md`), con narrativa San José/Cartago/Heredia (`docs/arquitectura-python.md`).
- La definición aristas+pesos vive — si existe — en el doc CHIMERA original fuera del repo.

**Acción pendiente (dueño: Sebas · ACTUALIZADA 2026-07-18 contra el enunciado oficial):**
construir `cr8` desde los **datos abiertos del ICE** (datos-ice-se.opendata.arcgis.com —
sugerencia textual del enunciado: "versión simplificada de la red de transmisión del ICE"), NO
desde el doc CHIMERA original: los valores W = 5.9 y g = 2 del grafo sintético quedan superseded
y se recalculan sobre la red real (recalibrar λ y el cálculo de shots de `quantum/04` §3 con los
valores nuevos). Congelar con el mismo formato + doble ancla + digest (`cr8-uniforme.json` /
`cr8-flujo.json`). **Agregar además una instancia de 6 nodos** (p. ej. reducción de la misma red
CR): el criterio oficial de suficiencia (p=1 con r ≥ 0.6) se define sobre una instancia de 6
nodos y hoy el corpus no tiene ninguna.

### 1.9 Script de generación completo (para regenerar y ratificar)

Correr **desde la raíz del repo** con el Python del workspace. Regenera los 6 JSON; la ratificación consiste en correrlo y comparar los digests contra los archivos congelados (§1.6).

```python
#!/usr/bin/env python3
"""Genera el corpus de benchmarks de islanding (Max-Cut con optimos conocidos).

Correr desde la raiz del repo:  uv run python <ruta a este script>
Salida: knowledge/islanding/corpus/<instancia>-<convencion>.json

Doble ancla independiente (trust/10 SS1.1): CP-SAT (OPTIMAL) + fuerza bruta (n<=14).
Si las anclas no coinciden, el script aborta y NO escribe nada.
"""

import hashlib
import itertools
import json
import sys
from pathlib import Path

import networkx as nx
import pandapower as pp
import pandapower.networks as pn
from ortools.sat.python import cp_model

ESCALA_FLUJO = 100          # w_int = round(100 * |p_mw|)  -> resolucion 0.01 MW
FUERZA_BRUTA_MAX_N = 14     # 2^(n-1) asignaciones con x0=0
CPSAT_TIEMPO_DETERMINISTA = 300.0   # trust/10 SS1.4: tiempo determinista, no de pared
CPSAT_SEED = 1

CASOS = {"ieee9": pn.case9, "ieee14": pn.case14, "ieee30": pn.case30}
CONVENCIONES = ("uniforme", "flujo")
DIR_SALIDA = Path.cwd() / "knowledge" / "islanding" / "corpus"


def cargar_ramas(constructor):
    """Red pandapower -> (n, ramas). Ramas = lineas + trafos en servicio,
    con buses relabelados a 0..n-1 (orden ascendente del indice de bus) y
    |P| activa del caso base (runpp) medida en el extremo from/hv."""
    net = constructor()
    pp.runpp(net)
    buses = sorted(int(b) for b in net.bus.index)
    relabel = {b: k for k, b in enumerate(buses)}
    ramas = []
    for idx, fila in net.line[net.line.in_service].iterrows():
        p_mw = abs(float(net.res_line.at[idx, "p_from_mw"]))
        ramas.append((relabel[int(fila.from_bus)], relabel[int(fila.to_bus)], p_mw))
    for idx, fila in net.trafo[net.trafo.in_service].iterrows():
        p_mw = abs(float(net.res_trafo.at[idx, "p_hv_mw"]))
        ramas.append((relabel[int(fila.hv_bus)], relabel[int(fila.lv_bus)], p_mw))
    return len(buses), ramas


def construir_aristas(ramas, convencion):
    """Ramas -> aristas [[i,j,w_entero]...] ordenadas (i<j). Las ramas paralelas
    entre el mismo par de buses se agregan sumando su contribucion."""
    acumulado = {}
    for a, b, p_mw in ramas:
        i, j = sorted((a, b))
        w = 1 if convencion == "uniforme" else round(ESCALA_FLUJO * p_mw)
        acumulado[(i, j)] = acumulado.get((i, j), 0) + w
    return [[i, j, w] for (i, j), w in sorted(acumulado.items())]


def valor_corte(aristas, x):
    return sum(w for i, j, w in aristas if x[i] != x[j])


def optimo_fuerza_bruta(n, aristas):
    """Enumeracion completa con x0=0 fijo (2^(n-1) asignaciones).
    Devuelve (optimo, asignacion lexicograficamente minima entre las optimas)."""
    mejor, mejor_x = -1, None
    for bits in itertools.product((0, 1), repeat=n - 1):
        x = (0, *bits)
        v = valor_corte(aristas, x)
        if v > mejor:                      # estricto -> conserva la lex minima
            mejor, mejor_x = v, x
    return mejor, list(mejor_x)


def resolver_cpsat(n, aristas):
    """Formulacion Max-Cut de referencia de trust/10 SS1.5 (XOR linealizado con
    las 4 restricciones, x0=0) + parametros de determinismo de trust/10 SS1.4."""
    model = cp_model.CpModel()
    x = [model.new_bool_var(f"x{i}") for i in range(n)]
    model.add(x[0] == 0)                   # ruptura de simetria -> canonica
    objetivo = []
    for i, j, w in aristas:
        y = model.new_bool_var(f"y_{i}_{j}")
        model.add(y <= x[i] + x[j])
        model.add(y <= 2 - x[i] - x[j])
        model.add(y >= x[i] - x[j])
        model.add(y >= x[j] - x[i])
        objetivo.append(w * y)
    model.maximize(sum(objetivo))

    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = CPSAT_SEED
    solver.parameters.max_deterministic_time = CPSAT_TIEMPO_DETERMINISTA
    status_nombre = solver.status_name(solver.solve(model))

    if status_nombre not in ("OPTIMAL", "FEASIBLE"):
        return {"status": status_nombre}
    asignacion = [int(solver.value(v)) for v in x]
    valor = int(round(solver.objective_value))
    recomputado = valor_corte(aristas, asignacion)
    if recomputado != valor:               # paso 1 de trust/10 aplicado al corpus
        raise AssertionError(f"CP-SAT inconsistente: objetivo {valor} != recompute {recomputado}")
    return {
        "status": status_nombre,
        "valor": valor,
        "asignacion": asignacion,
        "cota": int(round(solver.best_objective_bound)),
    }


def con_digest(registro):
    """digest = SHA-256 del JSON canonico (claves ordenadas, sin espacios,
    ensure_ascii) SIN el campo digest."""
    canonico = json.dumps(registro, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return {**registro, "digest": hashlib.sha256(canonico.encode("utf-8")).hexdigest()}


def generar_instancia(instancia, convencion, n, ramas):
    aristas = construir_aristas(ramas, convencion)
    grafo = nx.Graph((i, j) for i, j, _ in aristas)
    if not nx.is_connected(grafo) or grafo.number_of_nodes() != n:
        raise AssertionError(f"{instancia}: grafo no conexo o con nodos aislados")

    cpsat = resolver_cpsat(n, aristas)
    metodos, notas = ["cpsat"], []

    if n <= FUERZA_BRUTA_MAX_N:
        bruto, x_bruto = optimo_fuerza_bruta(n, aristas)
        metodos.append("bruteforce")
        if cpsat.get("status") != "OPTIMAL" or cpsat["valor"] != bruto:
            raise AssertionError(
                f"CONFLICTO en {instancia}/{convencion}: cpsat={cpsat} vs bruteforce={bruto}"
            )
        optimo, asignacion = bruto, x_bruto   # lex minima entre las optimas
    elif cpsat.get("status") == "OPTIMAL":
        optimo, asignacion = cpsat["valor"], cpsat["asignacion"]
    else:
        notas.append(f"sin prueba de optimalidad: incumbente={cpsat.get('valor')} "
                     f"cota={cpsat.get('cota')}")
        optimo, asignacion = None, None

    registro = {
        "instancia": instancia,
        "convencion": convencion,
        "n_nodos": n,
        "aristas": aristas,
        "escala": 1 if convencion == "uniforme" else ESCALA_FLUJO,
        "optimo": optimo,
        "asignacion_canonica": asignacion,
        "metodos": metodos,
        "solver_status": cpsat["status"],
    }
    if notas:
        registro["notas"] = notas
        registro["incumbente"] = cpsat.get("valor")
        registro["cota_superior"] = cpsat.get("cota")
    return con_digest(registro)


def main():
    DIR_SALIDA.mkdir(parents=True, exist_ok=True)
    resumen = []
    for instancia, constructor in CASOS.items():
        n, ramas = cargar_ramas(constructor)
        pares = {tuple(sorted((a, b))) for a, b, _ in ramas}
        paralelas = len(ramas) - len(pares)
        # margen al umbral de redondeo x.5 (robustez de la regeneracion entre
        # maquinas: un flujo pegado al umbral podria redondear distinto por fp)
        margen = min(abs(abs(ESCALA_FLUJO * p - round(ESCALA_FLUJO * p)) - 0.5)
                     for _, _, p in ramas)
        for convencion in CONVENCIONES:
            registro = generar_instancia(instancia, convencion, n, ramas)
            ruta = DIR_SALIDA / f"{instancia}-{convencion}.json"
            ruta.write_text(json.dumps(registro, sort_keys=True, indent=2,
                                       ensure_ascii=True) + "\n", encoding="utf-8")
            resumen.append((instancia, convencion, n, len(registro["aristas"]),
                            registro["optimo"], "+".join(registro["metodos"]),
                            registro["solver_status"]))
        print(f"{instancia}: {len(ramas)} ramas ({paralelas} paralelas agregadas), "
              f"margen minimo al umbral x.5 = {margen:.4f} (en unidades de 0.01 MW)")
    print()
    print(f"{'instancia':10} {'convencion':10} {'n':>3} {'|E|':>4} {'optimo':>8} "
          f"{'metodos':18} status")
    for fila in resumen:
        print(f"{fila[0]:10} {fila[1]:10} {fila[2]:>3} {fila[3]:>4} "
              f"{str(fila[4]):>8} {fila[5]:18} {fila[6]}")


if __name__ == "__main__":
    sys.exit(main())
```

---

## 2 · Decisión

| Referencia                                                             | Decisión                                                                              | Racional                                                                                                    |
| ---------------------------------------------------------------------- | ------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| `pandapower.networks` (case9/14/30) como fuente de topologías          | **integrar** (ya en el workspace)                                                     | Mismo benchmark que REGRID-QAOA (quantum/00 §1.5): "validamos en el mismo benchmark que el estado del arte" |
| Doble ancla CP-SAT + fuerza bruta para el corpus                       | **portar** (patrón de trust/10 §1.1)                                                  | Diversidad de anclas aplicada al propio corpus; fail-loud ante conflicto                                    |
| Dos convenciones de peso (`uniforme` + `flujo`) por instancia          | **portar** (de `docs/arquitectura-reconciliada.md`: "pandapower … power flow → w_ij") | La uniforme es exacta y auditable a mano; la de flujo es la que conecta con el dominio                      |
| Escala entera S = 100 para `flujo` (0.01 MW)                           | decidido acá — **a ratificar por Sebas**                                              | Coherente con trust/10 §1.5; el redondeo queda dentro de la definición de la instancia                      |
| Corpus como **datos versionados con digest** en `knowledge/islanding/` | **portar** (regla "λ es dato, no código" de quantum/02 §1.3)                          | Sin digest, dos corridas no son comparables; el JSON congelado es la fuente de verdad                       |
| Ancla única para ieee30 (solo CP-SAT `OPTIMAL`)                        | **resuelto S-E:** segunda ancla = enumeración vectorizada (§1.4, freeze §15.3)        | Independiente de CP-SAT, cero deps nuevas; ratificación final de Sebas = correr y comparar digests          |
| Red CR en el corpus (cr8 + cr6)                                        | **decidido S-E (P0-7):** desde datos abiertos del ICE (§1.8) — dueño Sebas            | Procedencia pública oficial (resuelve PR3/soberanía del demo); IDs reservados en freeze §15.3               |

## 3 · Licencias

Verificadas con `importlib.metadata` sobre los paquetes instalados del workspace (2026-07-14):

| Pieza               | Versión instalada | Licencia                                                                             | Verificado                                         | Implicación                                                                   |
| ------------------- | ----------------- | ------------------------------------------------------------------------------------ | -------------------------------------------------- | ----------------------------------------------------------------------------- |
| pandapower          | 3.3.3             | **BSD** (classifier `OSI Approved :: BSD License`; campo `License-Expression` vacío) | ✅ metadatos instalados                            | Solo se usa para generar los datos; sin contaminación                         |
| networkx            | 3.6.1             | **BSD-3-Clause**                                                                     | ✅ metadatos instalados                            | Chequeo de conexidad en la generación                                         |
| ortools (CP-SAT)    | 9.15.6755         | **Apache-2.0**                                                                       | ✅ metadatos instalados (coincide con trust/10 §3) | Ancla 1; ya decidido en trust/04                                              |
| numpy (transitiva)  | 2.5.0             | **BSD-3-Clause** (AND 0BSD/MIT/Zlib/CC0 en componentes)                              | ✅ metadatos instalados                            | Transitiva de pandapower                                                      |
| Los JSON del corpus | —                 | datos generados del proyecto                                                         | —                                                  | Las topologías IEEE son casos de prueba estándar de dominio público académico |

## 4 · Impacto en contrato

**Ningún contrato del freeze cambia.** El corpus es conocimiento versionado (datos), no código del engine:

1. **Corpus rung 3 (trust/17):** estas 6 instancias son la semilla del corpus que el corpus runner ejecuta — instancias con óptimo conocido para computar approximation ratio y KPIs por run (quantum/04 §1: el ratio r = cut/óptimo necesita exactamente este denominador).
2. **`ExactSolverVerifier` (trust/10):** los G1–G6 siguen siendo el gate de implementación (óptimos a mano); estas instancias se suman como vectores de calibración de tamaño real. El campo `escala` de cada JSON es el mismo `scale` del `evidence.differential` (trust/10 §1.7) que un verify sobre la instancia debería registrar.
3. **Claims del proponente (quantum/02 §1.6):** la canonicalización x₀=0 del corpus es la misma que la decodificación canónica del lado QAOA — una sola convención en todo el pipeline.
4. **Digest:** el `digest` de cada instancia identifica el problema resuelto en la `evidence` de cualquier corrida (mismo rol que el digest de λ en quantum/02 §1.3). Nota: la receta de digest de esta nota es la del corpus (JSON canónico de la instancia); no es el `claim_digest` del anexo de canonicalización (que lleva prefijo de dominio) — son objetos distintos con reglas propias.

## 5 · Reconciliación contra la base lógica

- **PR2 / INV-2 (el verificador nunca es un modelo):** INTACTO — las dos anclas son un solver exacto y una enumeración; ningún modelo participó en la generación ni en los valores publicados.
- **ADR-029 (manifests genéricos; el conocimiento de escenario vive en la KB):** REALIZADO — islanding/IEEE/flujos viven acá, en `knowledge/`, no en ninguna capability. Esta nota es exactamente el "benchmark corpus with known optima (pending)" que el README de `knowledge/` ya anunciaba.
- **D20 (confianza = propiedad del proceso):** los parámetros deterministas (workers=1, seed=1, tiempo determinista) + el digest por instancia hacen el corpus **regenerable y comparable byte a byte**, no anecdótico.
- **Fail-loud (espíritu de trust/10 §1.2):** el generador aborta ante conflicto entre anclas o ante inconsistencia objetivo↔asignación — un corpus publicado con anclas en desacuerdo sería el equivalente al `pass` mentiroso.
- **Ninguna contradicción con `docs/invariants.md` encontrada en esta consolidación.** **Todo decidido (S-E 2026-07-18) — ratificación final de Sebas, ajustable bajo su criterio:** correr el script §1.9 (con la segunda ancla vectorizada de ieee30 integrada) y comparar digests; S=100 confirmado como definición de instancia; aportar cr8/cr6 desde los datos del ICE (§1.8, IDs y regla de digest ya congelados en freeze §15.3).
