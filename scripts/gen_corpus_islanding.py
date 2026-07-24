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
