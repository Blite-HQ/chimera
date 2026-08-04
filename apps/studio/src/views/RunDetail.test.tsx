import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, test, vi } from 'vitest';

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
      lenses={[
        { id: 'red', label: 'Red', content: <p>vista red</p> },
        { id: 'ablacion', label: 'Ablación', content: <p>vista ablación</p> }
      ]}
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

/**
 * P3-D (N1) — `run.cancelled` estaba congelado desde antes y no tenía quién
 * lo emitiera; P-rt le dio ruta y acá le damos botón. La regla del freeze §2
 * manda la afordancia: un stream terminal no acepta appends, así que cancelar
 * un run ya cerrado no es una acción deshabilitada «por las dudas» — es una
 * acción que no existe.
 */
function Harness({
  summary,
  onCancel,
  cancelError
}: {
  readonly summary: RunSummary;
  readonly onCancel?: () => void;
  readonly cancelError?: string | null;
}) {
  return (
    <RunDetail
      summary={summary}
      onDownloadBundle={vi.fn()}
      {...(onCancel !== undefined && { onCancelRun: onCancel })}
      {...(cancelError !== undefined && { cancelError })}
      hilo={<p>vista hilo</p>}
      timeline={<p>vista timeline</p>}
      verificacion={<p>vista verificación</p>}
      lenses={[
        { id: 'red', label: 'Red', content: <p>vista red</p> },
        { id: 'ablacion', label: 'Ablación', content: <p>vista ablación</p> }
      ]}
      procedencia={<p>vista procedencia</p>}
    />
  );
}

describe('RunDetail — cancelar el run (P3-D)', () => {
  const enCurso: RunSummary = { ...RUN, status: 'en_curso' };

  it('ofrece cancelar mientras el run está en curso', () => {
    render(<Harness summary={enCurso} onCancel={vi.fn()} />);

    expect(screen.getByRole('button', { name: /cancelar/i })).toBeInTheDocument();
  });

  it('no ofrece cancelar un run ya terminal (§2: el stream no acepta appends)', () => {
    render(<Harness summary={{ ...RUN, status: 'completado' }} onCancel={vi.fn()} />);

    expect(screen.queryByRole('button', { name: /cancelar/i })).not.toBeInTheDocument();
  });

  it('no ofrece cancelar cuando no hay quién atienda la acción', () => {
    render(<Harness summary={enCurso} />);

    expect(screen.queryByRole('button', { name: /cancelar/i })).not.toBeInTheDocument();
  });

  it('avisa antes de cancelar y solo llama al handler si se confirma', async () => {
    const user = userEvent.setup();
    const onCancel = vi.fn();
    render(<Harness summary={enCurso} onCancel={onCancel} />);

    await user.click(screen.getByRole('button', { name: /^cancelar/i }));
    expect(onCancel).not.toHaveBeenCalled();

    await user.click(screen.getByRole('button', { name: /confirmar/i }));
    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it('muestra el error del server tal cual (409 si el run murió mientras tanto)', () => {
    render(
      <Harness
        summary={enCurso}
        onCancel={vi.fn()}
        cancelError="el run ya es terminal — el stream no acepta más appends"
      />
    );

    expect(screen.getByRole('alert')).toHaveTextContent('no acepta más appends');
  });
});
