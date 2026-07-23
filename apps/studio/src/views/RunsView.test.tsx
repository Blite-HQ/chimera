import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, test, vi } from 'vitest';

import RunsView from './RunsView';

import type { RunSummary } from './types';

const RUN: RunSummary = {
  runId: '8f2c1a9b',
  status: 'completado',
  conclusion: 'La partición propuesta de ieee14 es el óptimo exacto del corte',
  verdict: 'verified',
  titularLevel: 'AL3',
  titularClass: 'formal_exact',
  eventsCount: 5,
  actor: 'user:dylan',
  completedAt: '2026-07-22T12:00:05.000000Z'
};

describe('RunsView', () => {
  test('lista el run con conclusión, veredicto humano y confianza clase·AL', () => {
    render(<RunsView runs={[RUN]} onSelectRun={vi.fn()} />);

    expect(screen.getByRole('button', { name: /8f2c1a9b/ })).toBeInTheDocument();
    expect(screen.getByText(/óptimo exacto/)).toBeInTheDocument();
    expect(screen.getByText('verificada')).toBeInTheDocument();
    expect(screen.getByText(/formal exacto/)).toBeInTheDocument();
    expect(screen.getByText('AL3')).toBeInTheDocument();
    expect(screen.getByText('user:dylan')).toBeInTheDocument();
  });

  test('notifica el run seleccionado al presionar su fila', async () => {
    const user = userEvent.setup();
    const onSelectRun = vi.fn();
    render(<RunsView runs={[RUN]} onSelectRun={onSelectRun} />);

    await user.click(screen.getByRole('button', { name: /8f2c1a9b/ }));
    expect(onSelectRun).toHaveBeenCalledWith('8f2c1a9b');
  });

  test('muestra estado vacío que invita a actuar cuando no hay runs', () => {
    render(<RunsView runs={[]} onSelectRun={vi.fn()} />);
    expect(screen.getByText(/sin runs/i)).toBeInTheDocument();
  });
});
