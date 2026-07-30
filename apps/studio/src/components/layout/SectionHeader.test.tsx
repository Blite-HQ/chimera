import { render, screen } from '@testing-library/react';
import { describe, expect, test } from 'vitest';

import { RunStatusDot } from '@/components/runs/RunStatusDot';

import { SectionHeader } from './SectionHeader';

describe('SectionHeader', () => {
  test('renderiza el título como heading de la vista con su descripción', () => {
    render(<SectionHeader title="Runs" description="Cada run llega con su confianza." />);

    expect(screen.getByRole('heading', { name: 'Runs' })).toBeInTheDocument();
    expect(screen.getByText(/su confianza/)).toBeInTheDocument();
  });
});

describe('RunStatusDot', () => {
  test('nombra el estado accesiblemente y es decorativo a la vista', () => {
    render(<RunStatusDot status="completado" />);
    expect(screen.getByLabelText('completado')).toBeInTheDocument();
  });

  test('distingue en curso de completado', () => {
    render(<RunStatusDot status="en_curso" />);
    expect(screen.getByLabelText('en curso')).toBeInTheDocument();
  });

  /**
   * Auditoría Fase 2 (`docs/mvp/decisiones.md` §"Análisis para discusión"
   * punto 3, extensión aditiva): fallido/cancelado ya no colapsan a
   * en_curso — cada uno nombra su propio estado accesiblemente.
   */
  test('nombra fallido', () => {
    render(<RunStatusDot status="fallido" />);
    expect(screen.getByLabelText('fallido')).toBeInTheDocument();
  });

  test('nombra cancelado', () => {
    render(<RunStatusDot status="cancelado" />);
    expect(screen.getByLabelText('cancelado')).toBeInTheDocument();
  });
});
