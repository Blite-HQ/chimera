# Dominio Ciencia/Reto — el reto 1 resuelto POR Chimera (dueño natural: Sebas)

**Rama:** `mvp/ciencia-reto` · **Base:** `integracion/runtime-confianza`
**Contexto obligatorio:** `docs/mvp/00-plan-maestro.md` (sección "El reto 1 como contrato"),
`knowledge/islanding/01-corpus-benchmarks.md`, `capabilities/{sim,solvers,quantum}/`,
`engine/src/blite/verification/execution.py` (formato de topología+límites),
`knowledge/quantum/` (QAOA, baselines, ruta Quantinuum).

**Insumo externo:** la resolución de referencia del reto 1 hecha con Claude Code (sin
Chimera, fases 1–3) — Dylan la aporta; sirve para validar corrección, NO bloquea: mientras
llega, todo se valida contra el corpus congelado y CP-SAT.

## Nivel MVP (en orden)

1. **Baselines clásicos del reto (OBLIGATORIOS por rúbrica)** en `capabilities/graphs`
   (hoy stub): Goemans-Williamson (CVXPY — agregar dep con decisión registrada) + greedy.
   TDD contra el corpus (óptimos congelados). Manifest genérico (ADR-029).
2. **Dato eléctrico de ieee14** (`knowledge/islanding/`): topología en el formato genérico
   de `ExecutionVerifier`/`power_flow` (buses/slack/branches/loads) + límites (banda
   `vm_pu`, `line_loading_max_percent`, `slack_p_max_mw`) + convención de slack por isla.
   Fuente honesta: `pandapower.networks.case14()` como modelo declarado (el anchor_digest
   pinnea el JSON). Valores de límites = estándar de planeamiento, marcados en
   `decisiones.md` para ratificar. **Esto desbloquea la regeneración del fixture demo.**
3. **Instancia ICE "provincia" (6–8 nodos)**: del portal `datos-ice-se.opendata.arcgis.com`
   (red de transmisión CR), construir el grafo ponderado con la MISMA receta del corpus
   (convención flujo, escala S=100, digest embebido, generación documentada y
   reproducible). Con su topología eléctrica + límites. Es la instancia estrella del demo
   (datos reales ⇒ puntaje ODS).
4. **Experimento r vs p** (script en `scripts/` o notebook — será parte del entry point
   del entregable): QAOA p∈{1,2,3} × ≥5 seeds sobre la instancia de 6–8 nodos, media+std,
   r = corte/óptimo (óptimo por CP-SAT), comparación GW/greedy/bruta. Criterio del reto:
   r ≥ 0.6 en p=1. TODO recomputable; nada a mano.

## Nivel Planeado

5. Escalas "región" (~12–14 nodos) y "país" (>26 nodos ⇒ SOLO clásico + extrapolación
   honesta — el H2 topa en 26 qubits; así lo dice el freeze y lo premia la rúbrica).
6. Regenerar `gen-example-bundle.py` desde un run REAL con la instancia ICE (2 patas).
7. Sección de limitaciones honestas del informe (insumo directo de los verdicts
   `inconclusive`/`refuted` que el sistema produce).

## Nivel Mejorado

8. Extensiones del reto: ZNE/Pauli twirling, warm-start QAOA, análisis de escalado
   multi-instancia; H2/Guppy pre-corridas con digests (ruta en `knowledge/quantum/`).

## Reglas del dominio

- El corpus congelado manda: toda instancia nueva sigue su receta (digest embebido,
  regeneración que no reproduce se REPORTA, no se sobreescribe).
- Cero términos de escenario en manifests (ADR-029 — test lo gatea); "islanding"/"ICE"
  viven en knowledge/ y en los datos, jamás en el SDK/engine.
- Sin red en tests: los datos ICE se descargan una vez, se congelan con digest y el test
  usa el archivo congelado.
