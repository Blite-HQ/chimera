import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';

import { AssuranceScale } from './AssuranceScale';

/**
 * Glifo simplificado (directriz Dylan 2026-07-29): TRES barras y CUATRO
 * estados de confianza — nula (0 barras coloreadas), poca (la baja), media
 * (la intermedia), alta (la más alta). El AL exacto sigue en la etiqueta
 * accesible y en el texto mono del badge: el glifo simplifica, el dato no.
 */
describe('AssuranceScale', () => {
  afterEach(cleanup);

  const barsOf = (label: string): Element[] => {
    const svg = screen.getByRole('img', { name: label });
    return Array.from(svg.querySelectorAll('rect'));
  };

  it('renderiza exactamente 3 barras', () => {
    render(<AssuranceScale level="AL3" verdict="pass" />);
    expect(barsOf('confianza alta (AL3 de AL4)')).toHaveLength(3);
  });

  it('AL0 = confianza nula: ninguna barra coloreada', () => {
    render(<AssuranceScale level="AL0" verdict="fail" />);
    const bars = barsOf('confianza nula (AL0 de AL4)');
    expect(bars.every(bar => bar.getAttribute('opacity') === '0.25')).toBe(true);
  });

  it('AL1 = poca: solo la barra más baja coloreada con el tono del veredicto', () => {
    render(<AssuranceScale level="AL1" verdict="inconclusive" />);
    const bars = barsOf('confianza poca (AL1 de AL4)');
    expect(bars.map(bar => bar.getAttribute('opacity'))).toEqual(['1', '0.25', '0.25']);
    expect(bars[0]?.getAttribute('fill')).toBe('var(--color-verdict-inconclusive)');
  });

  it('AL2 = media: solo la barra intermedia coloreada', () => {
    render(<AssuranceScale level="AL2" verdict="pass" />);
    const bars = barsOf('confianza media (AL2 de AL4)');
    expect(bars.map(bar => bar.getAttribute('opacity'))).toEqual(['0.25', '1', '0.25']);
  });

  it('AL3 y AL4 = alta: solo la barra más alta coloreada', () => {
    render(
      <>
        <AssuranceScale level="AL3" verdict="pass" />
        <AssuranceScale level="AL4" verdict="pass" />
      </>
    );
    for (const label of ['confianza alta (AL3 de AL4)', 'confianza alta (AL4 de AL4)']) {
      const bars = barsOf(label);
      expect(bars.map(bar => bar.getAttribute('opacity'))).toEqual(['0.25', '0.25', '1']);
      expect(bars[2]?.getAttribute('fill')).toBe('var(--color-verdict-pass)');
    }
  });

  it('sin veredicto la barra alcanzada hereda currentColor', () => {
    render(<AssuranceScale level="AL2" />);
    const bars = barsOf('confianza media (AL2 de AL4)');
    expect(bars[1]?.getAttribute('fill')).toBe('currentColor');
  });
});
