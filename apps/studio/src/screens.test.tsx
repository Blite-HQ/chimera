/**
 * P-cierre B — el certificado solo se pide cuando el run está `completado`.
 * Antes de esto, `RunDetailScreen` pedía `GET /runs/{id}/certificate`
 * incondicionalmente: un run `fallido`/`cancelado`/`en_curso` respondía 409
 * ("claim aún no emitido") y la pestaña Verificación mostraba un
 * `ErrorState` — honesto pero ruidoso (`docs/mvp/decisiones.md:2797-2800`).
 *
 * Se mockea SOLO `runSummariesQueryOptions` (no el módulo entero) para
 * controlar el `status` del run sin depender del único run fijo que trae el
 * fixture de réplica. El resto de `./data/queries` queda REAL: en modo
 * réplica (sin `VITE_API_URL`), `loadCertificate` sirve el fixture
 * `EXAMPLE_CERTIFICATE` sin red, así que un run `completado` sí puede
 * probarse renderizando el certificado de verdad — mismo criterio de mínimo
 * mock que `queries.test.ts`.
 */

import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider, queryOptions } from '@tanstack/react-query';
import { describe, expect, it, vi } from 'vitest';

import { RunDetailScreen } from './screens';
import { runSummariesQueryOptions } from './data/queries';

import type { RunSummary } from './views/types';

vi.mock('./data/queries', async importOriginal => {
  const actual = await importOriginal<typeof import('./data/queries')>();
  return { ...actual, runSummariesQueryOptions: vi.fn(actual.runSummariesQueryOptions) };
});

const BASE_SUMMARY: RunSummary = {
  runId: 'run-cierre-b',
  status: 'completado',
  conclusion: 'conclusión de prueba',
  verdict: 'verified',
  titularLevel: 'AL3',
  titularClass: 'formal_exact',
  eventsCount: 5,
  actor: 'user:dylan'
};

function renderVerificacion(summary: RunSummary) {
  vi.mocked(runSummariesQueryOptions).mockReturnValue(
    queryOptions({
      queryKey: ['runs'] as const,
      queryFn: async (): Promise<readonly RunSummary[]> => [summary]
    })
  );

  render(
    <QueryClientProvider client={new QueryClient()}>
      <RunDetailScreen runId={summary.runId} tab="verificacion" />
    </QueryClientProvider>
  );
}

describe('RunDetailScreen — Verificación solo pide el certificado cuando el run está completado', () => {
  it('un run en curso no pide el certificado y lo dice — sin error, sin "cargando" eterno', async () => {
    renderVerificacion({ ...BASE_SUMMARY, status: 'en_curso' });

    expect(await screen.findByText('El certificado todavía no existe.')).toBeInTheDocument();
    expect(screen.getByText('Se emite cuando el run se completa.')).toBeInTheDocument();
    expect(screen.queryByText('Cargando el certificado del run')).not.toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('un run fallido no pide el certificado — dice que no habrá, no que algo se rompió', async () => {
    renderVerificacion({ ...BASE_SUMMARY, status: 'fallido' });

    expect(await screen.findByText('Este run no tiene certificado.')).toBeInTheDocument();
    expect(
      screen.getByText('Terminó sin completarse — no hay claim que emitir.')
    ).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('un run cancelado no pide el certificado — mismo honest-empty que fallido', async () => {
    renderVerificacion({ ...BASE_SUMMARY, status: 'cancelado' });

    expect(await screen.findByText('Este run no tiene certificado.')).toBeInTheDocument();
  });

  it('un run completado sí pide el certificado y lo renderiza', async () => {
    renderVerificacion({ ...BASE_SUMMARY, status: 'completado' });

    expect(await screen.findByText(/óptimo exacto del corte/i)).toBeInTheDocument();
    expect(screen.queryByText('El certificado todavía no existe.')).not.toBeInTheDocument();
    expect(screen.queryByText('Este run no tiene certificado.')).not.toBeInTheDocument();
  });
});
