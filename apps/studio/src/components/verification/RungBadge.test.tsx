import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { RungBadge } from './RungBadge';

describe('RungBadge', () => {
  it('muestra el número de escalón en mono y su etiqueta', () => {
    render(<RungBadge rung={3} verdict="pass" />);
    expect(screen.getByText(/verdad conocida/)).toBeTruthy();
    expect(screen.getByText('3')).toBeTruthy();
  });

  it('expone el glifo de la escalera con etiqueta accesible', () => {
    render(<RungBadge rung={2} verdict="pass" />);
    expect(screen.getByRole('img', { name: 'escalón 2 de 7 — ejecución' })).toBeTruthy();
  });

  it('reemplaza la etiqueta por defecto cuando recibe detail', () => {
    render(<RungBadge rung={1} verdict="pass" detail="ortools-cpsat" />);
    expect(screen.getByText(/ortools-cpsat/)).toBeTruthy();
  });
});
