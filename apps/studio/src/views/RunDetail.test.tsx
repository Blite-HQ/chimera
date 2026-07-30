import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, test, vi } from 'vitest';

import RunDetail from './RunDetail';

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

function renderDetail() {
  const onDownloadBundle = vi.fn();
  render(
    <RunDetail
      summary={RUN}
      onDownloadBundle={onDownloadBundle}
      hilo={<p>vista hilo</p>}
      timeline={<p>vista timeline</p>}
      verificacion={<p>vista verificación</p>}
      red={<p>vista red</p>}
      ablacion={<p>vista ablación</p>}
      procedencia={<p>vista procedencia</p>}
    />
  );
  return { onDownloadBundle };
}

describe('RunDetail', () => {
  test('el header persistente muestra id, estado, AL titular y descarga', async () => {
    const user = userEvent.setup();
    const { onDownloadBundle } = renderDetail();

    expect(screen.getByRole('heading', { name: '8f2c1a9b' })).toBeInTheDocument();
    expect(screen.getByText('completado')).toBeInTheDocument();
    expect(screen.getByText('AL3')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /descargar bundle/i }));
    expect(onDownloadBundle).toHaveBeenCalled();
  });

  /**
   * Auditoría Fase 2 (`docs/mvp/decisiones.md` §"Análisis para discusión"
   * punto 3, extensión aditiva): fallido/cancelado muestran su propio
   * estado (no "en curso" para siempre) con el tono correcto (fail/neutral).
   */
  test('muestra fallido con tono fail', () => {
    render(
      <RunDetail
        summary={{ ...RUN, status: 'fallido' }}
        onDownloadBundle={vi.fn()}
        hilo={<p>vista hilo</p>}
        timeline={<p>vista timeline</p>}
        verificacion={<p>vista verificación</p>}
        red={<p>vista red</p>}
        ablacion={<p>vista ablación</p>}
        procedencia={<p>vista procedencia</p>}
      />
    );

    const label = screen.getByText('fallido');
    expect(label).toBeInTheDocument();
    expect(label.className).toContain('text-verdict-fail');
  });

  test('muestra cancelado con tono neutral', () => {
    render(
      <RunDetail
        summary={{ ...RUN, status: 'cancelado' }}
        onDownloadBundle={vi.fn()}
        hilo={<p>vista hilo</p>}
        timeline={<p>vista timeline</p>}
        verificacion={<p>vista verificación</p>}
        red={<p>vista red</p>}
        ablacion={<p>vista ablación</p>}
        procedencia={<p>vista procedencia</p>}
      />
    );

    const label = screen.getByText('cancelado');
    expect(label).toBeInTheDocument();
    expect(label.className).toContain('text-verdict-neutral');
  });

  test('abre en Hilo (D6, directriz #69) y cambia de vista con las sub-tabs', async () => {
    const user = userEvent.setup();
    renderDetail();

    expect(screen.getByText('vista hilo')).toBeInTheDocument();
    expect(screen.queryByText('vista timeline')).not.toBeInTheDocument();

    await user.click(screen.getByRole('tab', { name: 'Timeline' }));
    expect(screen.getByText('vista timeline')).toBeInTheDocument();
    expect(screen.queryByText('vista hilo')).not.toBeInTheDocument();

    await user.click(screen.getByRole('tab', { name: 'Verificación' }));
    expect(screen.getByText('vista verificación')).toBeInTheDocument();
    expect(screen.queryByText('vista timeline')).not.toBeInTheDocument();
  });
});
