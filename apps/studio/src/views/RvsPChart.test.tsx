import { render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import RvsPChart from './RvsPChart';

import type { RvsPExperiment } from './types';

/**
 * RvsPChart.test.tsx (D5) — construye su propio `RvsPExperiment` inline
 * (mismo patrón que RunDetail.test.tsx), en vez de importar el fixture real
 * — la vista no debe acoplarse a los valores exactos del fixture, solo a
 * la FORMA del dato (F3: las vistas consumen tipos, no fixtures).
 */
const EXPERIMENT: RvsPExperiment = {
  instance: 'test-instance',
  optimo: 100,
  baselines: {
    cpsat: { energy: 100, r: 1.0 },
    greedy: { energy: 80, r: 0.8 },
    gw: { energy: 100, r: 1.0 }
  },
  points: [
    {
      p: 1,
      rEsperadoMean: 0.6,
      rMuestralMean: 0.59,
      rMuestralStd: 0.01,
      rMuestralMin: 0.58,
      rMuestralMax: 0.6,
      successRate: 1.0
    },
    {
      p: 2,
      rEsperadoMean: 0.75,
      rMuestralMean: 0.74,
      rMuestralStd: 0.02,
      rMuestralMin: 0.72,
      rMuestralMax: 0.76,
      successRate: 0.8
    }
  ]
};

describe('RvsPChart (D5 — dataviz "r vs p")', () => {
  it('renderiza sin lanzar (smoke — ResponsiveContainer + initialDimension en jsdom)', () => {
    expect(() => render(<RvsPChart experiment={EXPERIMENT} />)).not.toThrow();
  });

  it('la tabla comparativa lista cada p con r esperado, r muestral y tasa de éxito', () => {
    render(<RvsPChart experiment={EXPERIMENT} />);
    const table = screen.getByRole('table');

    expect(within(table).getByText(/p\s*=\s*1/i)).toBeInTheDocument();
    expect(within(table).getByText(/p\s*=\s*2/i)).toBeInTheDocument();
    expect(within(table).getByText('0.600')).toBeInTheDocument(); // r_esperado(p=1)
    expect(within(table).getByText('0.750')).toBeInTheDocument(); // r_esperado(p=2)
    expect(within(table).getByText(/0\.590.*0\.010/)).toBeInTheDocument(); // r_muestral mean ± std
    expect(within(table).getByText(/80%/)).toBeInTheDocument(); // success_rate(p=2), honestamente rotulado
  });

  it('la tabla incluye los 3 baselines clásicos con su r', () => {
    render(<RvsPChart experiment={EXPERIMENT} />);
    const table = screen.getByRole('table');

    expect(within(table).getByText(/CP-SAT/i)).toBeInTheDocument();
    expect(within(table).getByText(/Goemans-Williamson/i)).toBeInTheDocument();
    expect(within(table).getByText(/Greedy/i)).toBeInTheDocument();
    expect(within(table).getAllByText('1.000').length).toBeGreaterThanOrEqual(2); // cpsat + gw
    expect(within(table).getByText('0.800')).toBeInTheDocument(); // greedy
  });
});
