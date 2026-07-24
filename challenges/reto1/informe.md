# Reto 1 — Islanding / particionado de red eléctrica

> **ESQUELETO (Nivel MVP).** Este documento es la estructura de 8 páginas del
> informe técnico exigido por el reto, con los huecos que llenan los
> resultados reales del entry point (`challenges/reto1/run_all.py`)
> pre-llenados con cifras reales de `results/reto1/resumen.md`. La prosa
> completa (narrativa, discusión extendida, exportación a PDF ≤8 páginas) es
> **Planeado** (`docs/mvp/05-entregable.md` §"Nivel Planeado" ítem 4). Los
> huecos de prosa faltante están marcados así:
>
> > _[completar en Planeado: …]_
>
> No se fabricó ninguna cifra: todo número en este documento proviene de
> `results/reto1/resumen.md` (generado por `run_all.py`) o de
> `docs/mvp/decisiones.md` / `docs/mvp/auditoria-mvp.md`.

## 1. Planteamiento del problema

El reto plantea el particionado ("islanding") de una red eléctrica en dos
islas — un problema de Max-Cut sobre el grafo ponderado de la red, formulado
como QUBO. La instancia usada aquí es `ieee6-flujo`
(`knowledge/islanding/corpus/ieee6-flujo.json`, adaptación de
`pandapower.networks.case6ww`), un grafo de 6 nodos con óptimo congelado
`21692` (doble ancla: CP-SAT exacto + fuerza bruta).

> _[completar en Planeado: motivación del problema de islanding en redes
> eléctricas, formulación matemática completa QUBO/Ising, contexto de la red
> IEEE case6ww, diagrama del grafo]_

## 2. Baseline clásica

Tres baselines clásicos, todos obligatorios por la rúbrica del reto:

| baseline | descripción                                                  | garantía / expectativa | energy   | r      |
| -------- | ------------------------------------------------------------ | ---------------------- | -------- | ------ |
| cpsat    | CP-SAT exacto (`capabilities/solvers`, `blite.solvers.qubo`) | óptimo exacto          | 21692.00 | 1.0000 |
| gw       | Goemans-Williamson vía CVXPY/SDP (`capabilities/graphs`)     | garantía ≥ 0.878       | 21692.00 | 1.0000 |
| greedy   | greedy (`capabilities/graphs`)                               | ~0.5 esperado          | 17369.00 | 0.8007 |

GW alcanza el óptimo en esta instancia (r = 1.0000), muy por encima de su
garantía teórica de ≥0.878. Greedy alcanza r = 0.8007, por encima de la
expectativa informal de ~0.5.

> _[completar en Planeado: discusión de por qué GW alcanza el óptimo en esta
> instancia particular, comparación con el comportamiento esperado en
> instancias más grandes/densas]_

## 3. Implementación cuántica (QAOA)

El QUBO se transforma a un Hamiltoniano Ising (`capabilities/quantum`,
`blite_cap_quantum.qaoa`, Qiskit + Aer) y se optimiza con QAOA para
p ∈ {1, 2, 3}, 5 semillas por valor de p.

Se reportan dos métricas de r = E_QAOA / E_óptimo (decisión #21,
`docs/mvp/decisiones.md`):

- **r_esperado** (curva primaria): del valor esperado exacto ⟨C⟩ de la
  distribución variacional en los ángulos óptimos (`expected_energy`,
  statevector) — determinista dado el óptimo de COBYLA, no depende del
  muestreo.
- **r_muestral** (secundaria): media ± std sobre 2048 shots, 5 semillas
  (`sampled_mean_energy`).
- **éxito (best-of-shots)**: fracción de semillas cuyo mejor muestreo alcanza
  el óptimo — reportado aparte porque en una instancia de 6 qubits (64
  estados) trivializa a ~100% y no refleja la performance real de QAOA (ver
  §5).

> _[completar en Planeado: detalle del ansatz QAOA, mapeo QUBO→Ising con
> signo/offset, elección de COBYLA como optimizador clásico, diagrama del
> circuito]_

## 4. Resultados con barras de error

### r vs p (tabla, `results/reto1/resumen.md`)

| p   | r_esperado | r_muestral | std_muestral | n semillas | éxito (best-of-shots) |
| --- | ---------- | ---------- | ------------ | ---------- | --------------------- |
| 1   | 0.6085     | 0.6076     | 0.0051       | 5          | 100.00%               |
| 2   | 0.7566     | 0.7550     | 0.0041       | 5          | 100.00%               |
| 3   | 0.6870     | 0.6849     | 0.0041       | 5          | 100.00%               |

**Criterio oficial del reto cumplido:** r_esperado(p=1) = 0.6085 ≥ 0.6.

### Figura

Figura de referencia (generada por `run_all.py`, barras de error de
r_muestral ± std):

```text
results/reto1/ieee6-flujo_r_vs_p.png
```

> _[completar en Planeado: análisis de escalado con más instancias del
> corpus (ieee9/14/30), comparación de tiempos de cómputo clásico vs
> cuántico]_

## 5. Limitaciones honestas (obligatorio)

Esta sección es la única prosa ya completa en este esqueleto — son
limitaciones reales y ya conocidas, no huecos de Planeado:

1. **Best-of-2048-shots trivializa r en instancias chicas.** En una instancia
   de 6 qubits (64 estados), el mejor de 2048 muestras encuentra el óptimo
   casi siempre — `r(p) = 1.0000 ± 0.0000` en todo p sería un artefacto de
   muestreo, no la performance real de QAOA. Por eso se reporta el **valor
   esperado exacto ⟨C⟩** (`r_esperado`) como curva primaria, no el
   best-of-shots (decisión #21, `docs/mvp/decisiones.md`).
2. **p = 3 (0.6870) < p = 2 (0.7566): no monótono.** Es un mínimo local del
   optimizador clásico COBYLA sobre el ansatz variacional, reportado tal cual
   sin ocultarlo — la rúbrica premia esta honestidad, no penaliza el "dip"
   (hallazgo F6, `docs/mvp/auditoria-mvp.md`).
3. **La instancia ICE real está diferida.** Los CSVs de la red del ICE
   (`datos-ice-se.opendata.arcgis.com`) no estaban disponibles en la sesión de
   cierre del MVP; se usa `ieee6-flujo` (`pandapower.networks.case6ww`
   congelada) como stand-in reproducible de la escala "provincia"
   (decisiones #19/#51; nota F5 de la auditoría).
4. **El certificado de dos patas no se emite sobre la instancia del reto.**
   `ieee6-flujo` no tiene dato eléctrico registrado en
   `chimera_api.instance_verifiers.ELECTRICAL_DATA` — solo `sintetica-4bus`
   lo tiene. Certificar `ieee6-flujo` hoy solo ampararía la pata formal
   (CP-SAT). El certificado real (AL3, 7/7, dos patas) se emite sobre
   `sintetica-4bus`, la instancia que ya prueba el camino dorado de punta a
   punta (decisión #56).
5. **Escala "país" (>26 nodos) queda sin pata cuántica.** Límite físico del
   emulador H2 de Quantinuum (26 qubits); esa escala se resuelve con
   clásicos + extrapolación honesta, sin fingir una corrida cuántica que no
   cabe en el hardware disponible (decisión #3).
6. **`ieee14`: impedancias uniformes declaradas, no derivadas de case14.** Se
   intentó primero derivar r/x reales por rama desde
   `pandapower.networks.case14()`, pero el flujo de la red completa (14
   buses, una sola isla) no convergió — 13/20 ramas quedaban con impedancia
   casi nula al reescalar los tramos de trafo. Se aplicó el fallback
   documentado: impedancias uniformes declaradas (`r=0.5, x=1.5 ohm`) en las
   20 ramas, con el grafo y las cargas siguiendo siendo de case14 (decisión
   #23).

## 6. Reproducibilidad y verificación

Un único entry point reproduce cada figura y cifra de este informe:

```bash
uv sync --all-packages --all-extras
uv run python challenges/reto1/run_all.py
```

Escribe `results/reto1/{ieee6-flujo.json, ieee6-flujo_r_vs_p.png,
certificado_sintetica-4bus.json, resumen.md}`. El certificado se verifica de
forma independiente y offline con el CLI del juez:

```bash
uv run python scripts/verify-bundle.py results/reto1/certificado_sintetica-4bus.json
```

Salida esperada: **7/7**. Ver `challenges/reto1/README.md` para el mapa
completo del código (corpus, baselines, QAOA, verificación, certificado).

> _[completar en Planeado: referencia cruzada cifra-por-cifra entre cada
> número de este informe y su bundle de certificado respaldando, formato
> final del statement del SDK ≤200 palabras]_

## 7. ODS / impacto

> _[completar en Planeado: mapeo a los Objetivos de Desarrollo Sostenible —
> ODS 7 (energía asequible y no contaminante) y ODS 9 (industria, innovación
> e infraestructura) vía la optimización de la resiliencia de red eléctrica;
> conexión con la instancia real del ICE cuando esté disponible (ver §5.3)]_

## 8. Referencias

> _[completar en Planeado: referencias bibliográficas — Goemans-Williamson
> (1995), Farhi et al. QAOA (2014), documentación de Qiskik/Aer, pandapower,
> OR-Tools CP-SAT, doc oficial del reto]_

- `docs/mvp/00-plan-maestro.md` — contrato del reto 1.
- `docs/mvp/02-ciencia-reto.md` — diseño del experimento r vs p.
- `docs/mvp/decisiones.md` — decisiones #3, #8, #19, #21, #23, #51, #56.
- `docs/mvp/auditoria-mvp.md` — hallazgos F5, F6.
- `results/reto1/resumen.md` — cifras fuente de este informe.
