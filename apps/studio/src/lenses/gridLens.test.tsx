/**
 * P13 — los tests de la vista de red viajaron CON la lente. Antes vivían en
 * `App.test.tsx` porque la vista vivía en `App.tsx`; que hayan tenido que
 * mudarse es la señal de que el acoplamiento era real.
 *
 * GridSpike monta cytoscape sobre un canvas real (`readToken` llama a
 * `canvas.getContext('2d')`) y jsdom no implementa contexto 2D sin el paquete
 * `canvas`; GeoMap dibuja con d3-geo y tiene su propio archivo de test. Acá
 * importa la SELECCIÓN de vista, así que ambos se mockean con dobles mínimos.
 *
 * O7/#173.2 (directiva de Dylan 2026-08-11) — la lente ya NO renderiza el
 * dataset del ICE bundleado: el mapa sale del content store genérico
 * (`GET /files`), y `appliesTo` reconoce un run también porque el proyecto
 * OFRECE un dato geoespacial, no solo por capabilities de redes eléctricas.
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, test, vi } from 'vitest';

import { GridLensView, gridLens } from './gridLens';

import type { LensContext } from './types';

/**
 * [V1/M18] La lente consulta `GET /runs/{id}/topology` en vivo, así que
 * necesita un QueryClient. `retry: false` para que un rechazo se vea de una
 * en vez de reintentarse tres veces dentro del test.
 */
function renderLens(runId = 'run-1') {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <GridLensView runId={runId} />
    </QueryClientProvider>
  );
}

vi.mock('../spike/GridSpike', () => ({
  default: () => <div data-testid="cy-container" />
}));

vi.mock('../views/GeoMap', () => ({
  default: () => <div data-testid="geo-map-stub" />
}));

describe('gridLens — a qué runs se reconoce (P13, O7/#173.2)', () => {
  const contexto = (
    over: Partial<{
      claimTypes: string[];
      capabilityIds: string[];
      offeredMediaTypes: string[];
    }> = {}
  ): LensContext => ({
    runId: 'run-1',
    claimTypes: over.claimTypes ?? [],
    capabilityIds: over.capabilityIds ?? [],
    offeredMediaTypes: over.offeredMediaTypes ?? []
  });

  test('aplica cuando el run usó una capability de red', () => {
    expect(gridLens.appliesTo(contexto({ capabilityIds: ['blite.sim.power_flow'] }))).toBe(true);
  });

  test('aplica cuando el claim es de partición', () => {
    expect(gridLens.appliesTo(contexto({ claimTypes: ['partition.optimal_cut'] }))).toBe(true);
  });

  test('aplica porque el proyecto OFRECE un dato geoespacial — sin ninguna capability de red', () => {
    expect(gridLens.appliesTo(contexto({ offeredMediaTypes: ['application/geo+json'] }))).toBe(
      true
    );
  });

  test('NO aplica a un run de otro dominio sin ningún dato geoespacial — nada de tabs vacías ajenas', () => {
    expect(
      gridLens.appliesTo(
        contexto({
          capabilityIds: ['blite.quantum.trotter_evolve'],
          claimTypes: ['simulation'],
          offeredMediaTypes: ['application/pdf']
        })
      )
    ).toBe(false);
  });

  test('sin offeredMediaTypes declarado (contexto viejo, aditivo) sigue funcionando por capability', () => {
    const contextoViejo: LensContext = { runId: 'run-1', claimTypes: [], capabilityIds: [] };
    expect(gridLens.appliesTo(contextoViejo)).toBe(false);
    expect(
      gridLens.appliesTo({ ...contextoViejo, capabilityIds: ['blite.graphs.partition'] })
    ).toBe(true);
  });
});

describe('GridLensView (D1 task 4 — mata el spike como vista "Red" en vivo)', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  // CP6 vivo (2026-08-11): el mapa dejó de depender de que exista una
  // partición verificada — pintar la geografía que el proyecto OFRECE es el
  // artifact genérico, y la partición es superposición opcional. Sin archivo
  // geoespacial el honest-empty ahora habla del dato ausente, no del veredicto.
  // Lo que sigue intacto es #88: sin veredicto no se COLOREA isla alguna.
  test('en vivo SIN archivo geoespacial: lo dice, nunca el spike IEEE-14 fabricado', () => {
    vi.stubEnv('VITE_API_URL', 'http://api.test');
    renderLens();

    expect(screen.getByText(/no ofrece ningún archivo geoespacial/i)).toBeInTheDocument();
    expect(screen.queryByTestId('cy-container')).not.toBeInTheDocument();
  });

  test('en replay: el spike IEEE-14 (etiquetado por el banner global, no acá)', () => {
    vi.stubEnv('VITE_API_URL', undefined);
    renderLens();

    expect(screen.getByTestId('cy-container')).toBeInTheDocument();
  });
});

/**
 * O7/#173.2 — antes el toggle "Mapa" en modo réplica pintaba el GeoJSON del
 * ICE bundleado en el código. Ese bundle se borró (la directiva es sacar la
 * data quemada de la app): en réplica no hay servidor al que preguntarle por
 * archivos, así que "Mapa" ahora es honest-empty — jamás un dataset de
 * reemplazo fabricado (regla dura: cero mocks silenciosos).
 */
describe('GridLensView — toggle Diagrama/Mapa en réplica (O7/#173.2, honestidad de dato)', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  test('en replay: por defecto muestra Diagrama, y el toggle "Mapa" está disponible', () => {
    vi.stubEnv('VITE_API_URL', undefined);
    renderLens();

    expect(screen.getByTestId('cy-container')).toBeInTheDocument();
    expect(screen.queryByTestId('geo-map-stub')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /diagrama/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /mapa/i })).toBeInTheDocument();
  });

  test('en replay: clic en "Mapa" declara honestamente que no hay archivo geoespacial en este modo — nunca fabrica uno', async () => {
    vi.stubEnv('VITE_API_URL', undefined);
    const user = userEvent.setup();
    renderLens();

    await user.click(screen.getByRole('button', { name: /mapa/i }));

    expect(screen.queryByTestId('cy-container')).not.toBeInTheDocument();
    expect(screen.queryByTestId('geo-map-stub')).not.toBeInTheDocument();
    expect(screen.getByText(/sin archivo geoespacial en modo réplica/i)).toBeInTheDocument();
  });

  test('en replay: clic en "Mapa" y de vuelta en "Diagrama" restaura el spike', async () => {
    vi.stubEnv('VITE_API_URL', undefined);
    const user = userEvent.setup();
    renderLens();

    await user.click(screen.getByRole('button', { name: /mapa/i }));
    await user.click(screen.getByRole('button', { name: /diagrama/i }));

    expect(screen.getByTestId('cy-container')).toBeInTheDocument();
    expect(screen.queryByText(/sin archivo geoespacial en modo réplica/i)).not.toBeInTheDocument();
  });

  test('en vivo: el toggle no existe — la vista la manda el run, no el usuario', () => {
    vi.stubEnv('VITE_API_URL', 'http://api.test');
    renderLens();

    expect(screen.queryByRole('button', { name: /diagrama/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /mapa/i })).not.toBeInTheDocument();
    expect(screen.getByText(/no ofrece ningún archivo geoespacial/i)).toBeInTheDocument();
  });
});
