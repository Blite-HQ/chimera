/**
 * Fixture — copia tipada y fiel de `results/exp_r_vs_p/ieee6-flujo.json`
 * (experimento científico real, instancia `ieee6-flujo`, decision #21:
 * ⟨C⟩ como curva honesta, no best-of-shots). D5 diverge deliberadamente de
 * `docs/specs/superficie-visual.md` §5 (que pinnea `AblationMetric[]` como
 * fuente) porque esa forma no tiene eje `p` ni barras de error — ver nota
 * en `RvsPExperiment` (views/types.ts) y `docs/mvp/decisiones.md`.
 *
 * Solo se copian los campos que la vista consume (`baselines`, `qaoa.*.r_esperado`,
 * `qaoa.*.r_muestral`, `qaoa.*.success_rate`) — `best_energies`/`best_ratios`/
 * `expected_energies`/`sampled_mean_energies` quedan fuera a propósito (son
 * insumos intermedios del cálculo, no algo que esta vista deba renderizar).
 */

import type { RvsPExperiment } from '../views/types';

export const RVSP_EXPERIMENT: RvsPExperiment = {
  instance: 'ieee6-flujo',
  optimo: 21692,
  baselines: {
    cpsat: { energy: 21692, r: 1.0 },
    greedy: { energy: 17369.0, r: 0.800709939148073 },
    gw: { energy: 21692.0, r: 1.0 }
  },
  points: [
    {
      p: 1,
      rEsperadoMean: 0.6085304897099696,
      rMuestralMean: 0.6076189792751936,
      rMuestralStd: 0.005143781373912045,
      rMuestralMin: 0.6027915767477642,
      rMuestralMax: 0.6173565256272474,
      successRate: 1.0
    },
    {
      p: 2,
      rEsperadoMean: 0.7565665295246866,
      rMuestralMean: 0.7549595481989327,
      rMuestralStd: 0.0041211166872461855,
      rMuestralMin: 0.7505517812226281,
      rMuestralMax: 0.7613624208377513,
      successRate: 1.0
    },
    {
      p: 3,
      rEsperadoMean: 0.6869879172207626,
      rMuestralMean: 0.6848916615284437,
      rMuestralStd: 0.004114176108166365,
      rMuestralMin: 0.6805175241016274,
      rMuestralMax: 0.6912686479678568,
      successRate: 1.0
    }
  ]
};
