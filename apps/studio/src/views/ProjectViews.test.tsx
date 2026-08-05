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

describe('PapersView (P10/M24)', () => {
  const ARCHIVO = {
    digest: 'a'.repeat(64),
    filename: 'qaoa-regrid.pdf',
    media_type: 'application/pdf',
    size_bytes: 2048,
    created_at: '2026-08-04T12:00:00Z'
  };

  test('sin archivos declara el estado real, no lo disfraza', () => {
    render(<PapersView files={[]} />);

    expect(screen.getByRole('heading', { name: /papers y archivos/i })).toBeInTheDocument();
    expect(screen.getByText(/todavía no hay archivos/i)).toBeInTheDocument();
  });

  test('sin backend no ofrece subir — dice por qué en vez de un botón muerto', () => {
    render(<PapersView files={[]} />);

    expect(screen.queryByRole('button', { name: /subir/i })).not.toBeInTheDocument();
    expect(screen.getByText(/necesita el api en vivo/i)).toBeInTheDocument();
  });

  test('lista el archivo con su digest — es lo que un certificado puede citar', () => {
    render(<PapersView files={[ARCHIVO]} />);

    expect(screen.getByText('qaoa-regrid.pdf')).toBeInTheDocument();
    expect(screen.getByTitle('a'.repeat(64))).toBeInTheDocument();
    expect(screen.getByText('2 KB')).toBeInTheDocument();
  });

  test('un archivo sin nombre no rompe la fila — el digest es la identidad', () => {
    render(<PapersView files={[{ ...ARCHIVO, filename: null }]} />);

    expect(screen.getByText('(sin nombre)')).toBeInTheDocument();
  });

  test('con backend, elegir un archivo lo entrega al llamador', async () => {
    const user = userEvent.setup();
    const onUpload = vi.fn();
    render(<PapersView files={[]} onUpload={onUpload} />);

    const input = screen.getByLabelText(/archivo para subir/i);
    await user.upload(input, new File([new Uint8Array([1, 2, 3])], 'paper.pdf'));

    expect(onUpload).toHaveBeenCalledTimes(1);
    expect(vi.mocked(onUpload).mock.calls[0]?.[0]).toBeInstanceOf(File);
  });

  test('muestra el error de subida tal cual lo dijo el server', () => {
    render(<PapersView files={[]} onUpload={vi.fn()} uploadError="el cuerpo está vacío" />);

    expect(screen.getByRole('alert')).toHaveTextContent('el cuerpo está vacío');
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
