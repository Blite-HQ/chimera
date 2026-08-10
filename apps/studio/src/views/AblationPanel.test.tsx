import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import AblationPanel from './AblationPanel';

import type { AblationMetric } from './types';

/**
 * AblationPanel.test.tsx (V4/M6 · C-4) — el panel de 4 barras.
 *
 * Lo que se fija acá es la propiedad HONESTA de la leyenda, no la pintura:
 * el panel nombra las variantes que el run PRODUJO, no las que el enum
 * admite. Anunciar «ZNE» cuando ningún brazo de mitigación corrió sugeriría
 * una comparación que no ocurrió — que es la forma más barata de mentir en
 * un gráfico.
 *
 * Métricas inline (mismo patrón que RvsPChart.test.tsx): la vista se acopla a
 * la FORMA del dato, jamás a los valores de un fixture (F3).
 */
const metrica = (variant: AblationMetric['variant'], cutCost: number): AblationMetric => ({
  variant,
  cutCost,
  wallMs: 800,
  verificationLatencyMs: 400
});

const LAS_CUATRO: readonly AblationMetric[] = [
  metrica('quantum', 5),
  metrica('classical', 7),
  metrica('mitigated', 6),
  metrica('zne', 6.5)
];

describe('AblationPanel (V4/M6 — las cuatro variantes de C-4)', () => {
  it('renderiza sin lanzar (smoke — ResponsiveContainer en jsdom)', () => {
    expect(() => render(<AblationPanel metrics={LAS_CUATRO} />)).not.toThrow();
  });

  it('la leyenda nombra las cuatro variantes cuando las cuatro corrieron', () => {
    // Act
    render(<AblationPanel metrics={LAS_CUATRO} />);

    // Assert — el eje x de los 3 charts repite las etiquetas, así que se
    // consulta por «al menos una» en vez de por unicidad
    for (const etiqueta of ['Cuántico', 'Clásico', 'Mitigado', 'ZNE']) {
      expect(screen.getAllByText(etiqueta).length).toBeGreaterThan(0);
    }
  });

  it('una corrida sin brazos de mitigación NO anuncia Mitigado ni ZNE', () => {
    // Arrange — la ablación clásica de dos brazos
    const dos = [metrica('quantum', 5), metrica('classical', 7)];

    // Act
    render(<AblationPanel metrics={dos} />);

    // Assert
    expect(screen.getAllByText('Cuántico').length).toBeGreaterThan(0);
    expect(screen.queryByText('Mitigado')).not.toBeInTheDocument();
    expect(screen.queryByText('ZNE')).not.toBeInTheDocument();
  });

  it('un run sin métricas todavía no inventa ninguna variante', () => {
    // Act
    render(<AblationPanel metrics={[]} />);

    // Assert — honest-empty: los tres charts existen, sin barras ni leyenda
    expect(screen.getByText('Costo de corte')).toBeInTheDocument();
    expect(screen.queryByText('Cuántico')).not.toBeInTheDocument();
  });

  it('los tres charts son small-multiples, no un doble eje', () => {
    // El costo de corte, el tiempo y la latencia viven en escalas muy
    // distintas; superponerlos en un eje doble es el error de dataviz #1.
    // Act
    render(<AblationPanel metrics={LAS_CUATRO} />);

    // Assert
    expect(screen.getByText('Costo de corte')).toBeInTheDocument();
    expect(screen.getByText('Tiempo total')).toBeInTheDocument();
    expect(screen.getByText('Latencia de verificación')).toBeInTheDocument();
  });
});
