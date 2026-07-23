import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { AssuranceBadge } from './AssuranceBadge';

describe('AssuranceBadge', () => {
  it('muestra la clase y el nivel AL en mono — "{clase} · AL{n}" (trust/18 §2.3)', () => {
    render(<AssuranceBadge level="AL3" verdict="pass" verifierClass="ground_truth" />);
    expect(screen.getByText(/verdad conocida/)).toBeTruthy();
    expect(screen.getByText('AL3')).toBeTruthy();
  });

  it('expone el glifo de la escala con etiqueta accesible', () => {
    render(<AssuranceBadge level="AL2" verdict="pass" verifierClass="property_rule" />);
    expect(screen.getByRole('img', { name: 'nivel AL2 de AL4' })).toBeTruthy();
  });

  it('reemplaza la etiqueta de clase cuando recibe detail', () => {
    render(
      <AssuranceBadge
        level="AL3"
        verdict="pass"
        verifierClass="formal_exact"
        detail="ortools-cpsat"
      />
    );
    expect(screen.getByText(/ortools-cpsat/)).toBeTruthy();
  });

  it('sin clase ni detail muestra solo el nivel', () => {
    render(<AssuranceBadge level="AL1" verdict="neutral" />);
    expect(screen.getByText('AL1')).toBeTruthy();
  });
});
