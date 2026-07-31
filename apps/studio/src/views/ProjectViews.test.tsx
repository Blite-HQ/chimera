/** Vistas de proyecto (dominio Studio F2): Artifacts, Papers y Knowledge. */

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, test, vi } from 'vitest';

import ArtifactsView from './ArtifactsView';
import KnowledgeView from './KnowledgeView';
import PapersView from './PapersView';

import type { KnowledgeClaim, ProjectArtifact } from './types';

const ARTIFACT: ProjectArtifact = {
  artifactRef: 'partition.json',
  digest: 'a1b751764b2d516ab45b8ac077a0eff0ab49c3d4245e882f3c0bef59de498b93',
  runId: '8f2c1a9b',
  titularLevel: 'AL3',
  titularClass: 'formal_exact',
  verdict: 'verified',
  issuedAt: '2026-07-22T12:00:06.000000Z'
};

const CLAIM: KnowledgeClaim = {
  statement: 'La partición propuesta de ieee14 es el óptimo exacto del corte',
  scope: { problem: 'islanding-partition', instance: 'ieee14' },
  verdict: 'verified',
  level: 'AL3',
  titularClass: 'formal_exact',
  runId: '8f2c1a9b',
  validAsOf: '2026-07-22T12:00:06.000000Z'
};

describe('ArtifactsView', () => {
  test('lista el entregable con digest corto, run origen y confianza', () => {
    render(<ArtifactsView artifacts={[ARTIFACT]} onOpenRun={vi.fn()} />);

    expect(screen.getByText('partition.json')).toBeInTheDocument();
    expect(screen.getByText(/a1b751764b2d/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /8f2c1a9b/ })).toBeInTheDocument();
    expect(screen.getByText(/formal exacto/)).toBeInTheDocument();
  });

  test('navega al run origen al presionar su referencia', async () => {
    const user = userEvent.setup();
    const onOpenRun = vi.fn();
    render(<ArtifactsView artifacts={[ARTIFACT]} onOpenRun={onOpenRun} />);

    await user.click(screen.getByRole('button', { name: /8f2c1a9b/ }));
    expect(onOpenRun).toHaveBeenCalledWith('8f2c1a9b');
  });

  test('muestra estado vacío cuando no hay entregables', () => {
    render(<ArtifactsView artifacts={[]} onOpenRun={vi.fn()} />);
    expect(screen.getByText(/sin artifacts/i)).toBeInTheDocument();
  });
});

describe('PapersView', () => {
  test('invita a subir archivos con ustedeo y declara que aún no hay datos', () => {
    render(<PapersView />);

    expect(screen.getByRole('heading', { name: /papers y archivos/i })).toBeInTheDocument();
    expect(screen.getByText(/arrastre/i)).toBeInTheDocument();
    expect(screen.getByText(/todavía no hay archivos/i)).toBeInTheDocument();
  });
});

describe('KnowledgeView', () => {
  test('lista la conclusión verificada con su alcance, badge y run origen', () => {
    render(<KnowledgeView claims={[CLAIM]} onOpenRun={vi.fn()} />);

    expect(screen.getByText(/óptimo exacto/)).toBeInTheDocument();
    expect(screen.getByText(/instance: ieee14/)).toBeInTheDocument();
    expect(screen.getByText('AL3')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /8f2c1a9b/ })).toBeInTheDocument();
  });

  test('muestra estado vacío cuando no hay conclusiones acumuladas', () => {
    render(<KnowledgeView claims={[]} onOpenRun={vi.fn()} />);
    expect(screen.getByText(/sin conclusiones/i)).toBeInTheDocument();
  });
});
