# Reto 1 — Islanding / particionado de red eléctrica (QAOA vs. clásico)

Reto 1 del Quantathon: particionar un grafo de red eléctrica en dos islas
balanceadas (Max-Cut / QUBO), resuelto con QAOA y comparado contra baselines
clásicos, con el resultado respaldado por un certificado de confianza
verificable offline.

## Reproducción en un comando

Desde una instalación limpia del monorepo:

```bash
uv sync --all-packages --all-extras
uv run python challenges/reto1/run_all.py
```

`run_all.py` es el **único entry point** del reto (`docs/mvp/05-entregable.md`
§"Nivel MVP" ítem 1). Es determinista (semillas fijas) y en una corrida:

1. Carga la instancia congelada `ieee6-flujo`
   (`knowledge/islanding/corpus/ieee6-flujo.json`).
2. Corre los baselines clásicos (CP-SAT exacto, Goemans-Williamson, greedy).
3. Corre el barrido QAOA (p ∈ {1, 2, 3} × semillas 1..5).
4. Dispara un run real de Chimera (in-process, sin red) que verifica un claim
   de dominio y emite un certificado de confianza.

Salida, todo en `results/reto1/`:

- `ieee6-flujo.json` — reporte completo del experimento (baselines + QAOA).
- `ieee6-flujo_r_vs_p.png` — figura r vs p con barras de error.
- `certificado_sintetica-4bus.json` — bundle del certificado (AL3, 7/7).
- `resumen.md` — tabla resumen legible con las cifras y la decisión de diseño
  del certificado.

## Cómo verificar el certificado offline (el CLI del juez)

El diferenciador de Chimera no es una afirmación — es criptografía verificable
por un tercero, sin red y sin confiar en nosotros:

```bash
uv run python scripts/verify-bundle.py results/reto1/certificado_sintetica-4bus.json
```

Salida esperada: **7/7** (`exit 0`). Cada uno de los 7 puntos del checklist es
fail-closed — un solo punto no verificable hace fallar el CLI completo.

> No nos crea a nosotros — ejecute `verify-bundle` y créale a la
> criptografía.

## Mapa del código

| Pieza                                | Ubicación                                                                                                          |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------------------ |
| Corpus de instancias congeladas      | `knowledge/islanding/corpus/` (óptimo + doble ancla CP-SAT/fuerza bruta por instancia)                             |
| Baselines clásicos (GW, greedy)      | `capabilities/graphs` (`blite_cap_graphs`, capability `blite.graphs.maxcut`)                                       |
| Baseline exacto (CP-SAT)             | `capabilities/solvers` (`blite_cap_solvers`, capability `blite.solvers.qubo`)                                      |
| QAOA (QUBO → Ising, p × seeds)       | `capabilities/quantum` (`blite_cap_quantum`, capability `blite.quantum.qaoa`)                                      |
| Experimento r vs p (reusado por DRY) | `scripts/exp_r_vs_p.py`                                                                                            |
| Verificación (anclas no-modelo)      | `engine/src/blite/verification` (CP-SAT formal, pandapower execution, orchestrator)                                |
| Certificado (bundle DSSE)            | `engine/src/blite/certificate` (assemble, bundle_check, canonical, dsse)                                           |
| API del runtime                      | `POST /runs` (`api/src/chimera_api/runs.py`) → `GET /runs/{id}/certificate` (`api/src/chimera_api/certificate.py`) |
| CLI de verificación del juez         | `scripts/verify-bundle.py`                                                                                         |

## Resultado (cifras reales de `results/reto1/resumen.md`)

Instancia del reto: `ieee6-flujo` — óptimo congelado `21692`.

### r vs p (QAOA)

| p   | r_esperado | r_muestral | std_muestral | n semillas | éxito (best-of-shots) |
| --- | ---------- | ---------- | ------------ | ---------- | --------------------- |
| 1   | 0.6085     | 0.6076     | 0.0051       | 5          | 100.00%               |
| 2   | 0.7566     | 0.7550     | 0.0041       | 5          | 100.00%               |
| 3   | 0.6870     | 0.6849     | 0.0041       | 5          | 100.00%               |

`r_esperado(p=1) = 0.6085 ≥ 0.6` — cumple el criterio oficial del reto
("suficiente: r ≥ 0.6 con p=1 en 6 nodos").

### Baselines clásicos

| baseline | energy   | r      |
| -------- | -------- | ------ |
| cpsat    | 21692.00 | 1.0000 |
| gw       | 21692.00 | 1.0000 |
| greedy   | 17369.00 | 0.8007 |

### Certificado de confianza

Titular `AL3`, dos patas de verificación (`execution` + `solver`), veredicto
`verified`, verificado **7/7** con `verify-bundle.py`.

## La limitación honesta: por qué el certificado no es sobre `ieee6-flujo`

`ieee6-flujo` (la instancia del reto, usada arriba para las figuras y la
tabla) **no tiene dato eléctrico registrado** en
`chimera_api.instance_verifiers.ELECTRICAL_DATA`. Solo `sintetica-4bus` lo
tiene (decisión #8 en `docs/mvp/decisiones.md`) — es la única topología ya
probada de punta a punta con las **dos** patas reales de verificación
(CP-SAT formal + pandapower execution) en
`tests/unit/api/test_certificate.py::TestGoldenPath` y
`tests/smoke/test_runtime_api_e2e.py`.

Certificar hoy sobre `ieee6-flujo` solo ampararía la pata formal (CP-SAT, un
titular de una sola pata). En vez de fingir una segunda pata que no existe,
este entry point muestra el camino dorado de dos patas (AL3, 7/7) sobre la
instancia que ya lo prueba, y documenta la limitación con honestidad — tal
como lo exige la rúbrica del reto. Revertir esta decisión requiere registrar
el dato eléctrico de `ieee6-flujo` en `ELECTRICAL_DATA` (ver decisión #56).
