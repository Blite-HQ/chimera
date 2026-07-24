# Extrapolación honesta — ieee30→70 nodos clásico, barrera 26 qubits

Barrera del emulador H2: **26 qubits** (fuente: knowledge/quantum/08-ruta-quantinuum-guppy.md §2 (actualización oficial 2026-07-18: 'tope de 26 qubits confirma la escalera de instancias: cr8/ieee9/ieee14 en emulador; ieee30 solo clásico')).

| instancia       | n   | régimen          | r cuántico (real)                                        | gw_cut  | greedy_cut | cota SDP | r_gw/r_greedy o banda                |
| --------------- | --- | ---------------- | -------------------------------------------------------- | ------- | ---------- | -------- | ------------------------------------ |
| cr6-uniforme    | 6   | quantum-eligible | ratio_mean 0.8148–0.9324 (4 corridas Nexus)              | 5.0     | 5.0        | 5.25     | r_gw=1.0000 · r_greedy=1.0000        |
| cr8-uniforme    | 8   | quantum-eligible | ratio_mean 0.8556–0.9441 (6 corridas Nexus)              | 7.0     | 7.0        | 7.50     | r_gw=1.0000 · r_greedy=1.0000        |
| cr8-voltaje     | 8   | quantum-eligible | ratio_mean 0.8596–0.9154 (3 corridas Nexus)              | 1150.0  | 1150.0     | 1242.00  | r_gw=1.0000 · r_greedy=1.0000        |
| ieee9-uniforme  | 9   | quantum-eligible | ratio_mean 0.7286–0.8506 (3 corridas Nexus)              | 9.0     | 9.0        | 9.00     | r_gw=1.0000 · r_greedy=1.0000        |
| ieee14-flujo    | 14  | quantum-eligible | ratio_mean 0.7591–0.8548 (3 corridas Nexus)              | 57070.0 | 57070.0    | 57766.89 | r_gw=1.0000 · r_greedy=1.0000        |
| ieee30-uniforme | 30  | classical-only   | barrera (excede la barrera de 26 qubits del emulador H2) | 35.0    | 34.0       | 36.29    | r_gw=1.0000 · r_greedy=0.9714        |
| ice-uniforme    | 68  | classical-only   | barrera (excede la barrera de 26 qubits del emulador H2) | 82.0    | 75.0       | 86.43    | banda [75.00, 82.00, 86.43]          |
| ice-voltaje     | 68  | classical-only   | barrera (excede la barrera de 26 qubits del emulador H2) | 16192.0 | 14858.0    | 17044.88 | banda [14858.00, 16192.00, 17044.88] |

## Limitaciones honestas

- **qaoa_vs_gw**: QAOA no superó a GW en ninguna corrida Nexus de este artefacto ('instances_where_qaoa_beat_gw' vacío ⇒ verificado, no supuesto): en las instancias con evidencia cuántica (n<=14) GW ya alcanza el óptimo exacto (r_gw=1.0); el ratio_best de QAOA solo lo empata por muestreo en espacios de estados chicos (best-of-~1024 shots sobre <=2^14 estados) — artefacto de muestreo documentado en scripts/exp_r_vs_p.py (Fix 4b), no ventaja cuántica; el ratio_mean muestral (la métrica honesta) se queda sistemáticamente por debajo de 1.0. Coherente con la garantía teórica: QAOA p=1 (0.6924) < GW (0.878).
- **barrier_26_qubits**: El emulador H2 hace tratamiento EXACTO hasta 26 qubits (1 nodo = 1 qubit en la codificación Max-Cut congelada) — NO es una brecha que no intentamos, es una barrera física del emulador confirmada por el enunciado oficial (2026-07-18). ['ieee30-uniforme', 'ice-uniforme', 'ice-voltaje'] exceden la barrera y son SOLO clásicas; ['cr6-uniforme', 'cr8-uniforme', 'cr8-voltaje', 'ieee9-uniforme', 'ieee14-flujo'] tienen evidencia cuántica real.
- **ice_no_ground_truth**: A n=68 no hay verdad de terreno: el óptimo no fue probado (excede FUERZA_BRUTA_MAX_N=14 de la doble ancla y esta generación no corrió CP-SAT sobre la red completa — scripts/gen_corpus_ice.py) — solo se reporta la banda [greedy_cut, gw_cut, sdp_upper_bound] por instancia, nunca un r inventado.

Digest del artefacto: `e4eb94daf0e540b66b413521774f65d29916d6e2566e18e2e76f675b184178c8`
