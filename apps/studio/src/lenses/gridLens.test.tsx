/**
 * P13 — los tests de la vista de red viajaron CON la lente. Antes vivían en
 * `App.test.tsx` porque la vista vivía en `App.tsx`; que hayan tenido que
 * mudarse es la señal de que el acoplamiento era real.
 *
 * GridSpike monta cytoscape sobre un canvas real (`readToken` llama a
 * `canvas.getContext('2d')`) y jsdom no implementa contexto 2D sin el paquete
 * `canvas`; GridMap dibuja con d3-geo y tiene su propio archivo de test. Acá
 * importa la SELECCIÓN de vista, así que ambos se mockean con dobles mínimos.
 */

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, test, vi } from 'vitest';

import { GridLensView, gridLens } from './gridLens';

vi.mock('../spike/GridSpike', () => ({
  default: () => <div data-testid="cy-container" />
}));

vi.mock('../views/GridMap', () => ({
  default: () => <div data-testid="grid-map-stub" />
}));

describe('gridLens — a qué runs se reconoce (P13)', () => {
  const contexto = (over: Partial<{ claimTypes: string[]; capabilityIds: string[] }> = {}) => ({
    runId: 'run-1',
    claimTypes: over.claimTypes ?? [],
    capabilityIds: over.capabilityIds ?? []
  });

  test('aplica cuando el run usó una capability de red', () => {
    expect(gridLens.appliesTo(contexto({ capabilityIds: ['blite.sim.power_flow'] }))).toBe(true);
  });

  test('aplica cuando el claim es de partición', () => {
    expect(gridLens.appliesTo(contexto({ claimTypes: ['partition.optimal_cut'] }))).toBe(true);
  });

  test('NO aplica a un run de otro dominio — nada de tabs vacías ajenas', () => {
    expect(
      gridLens.appliesTo(
        contexto({ capabilityIds: ['blite.quantum.trotter_evolve'], claimTypes: ['simulation'] })
      )
    ).toBe(false);
  });
});

describe('GridLensView (D1 task 4 — mata el spike como vista "Red" en vivo)', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  test('en vivo: pendiente (falta productor de partición, decisión #88), nunca el spike IEEE-14 fabricado', () => {
    vi.stubEnv('VITE_API_URL', 'http://api.test');
    render(<GridLensView />);

    expect(screen.getByText(/topología en vivo/i)).toBeInTheDocument();
    expect(screen.queryByTestId('cy-container')).not.toBeInTheDocument();
  });

  test('en replay: el spike IEEE-14 (etiquetado por el banner global, no acá)', () => {
    vi.stubEnv('VITE_API_URL', undefined);
    render(<GridLensView />);

    expect(screen.getByTestId('cy-container')).toBeInTheDocument();
  });
});

/**
 * D4 task 6 — spec superficie-visual.md §4.3 "dual diagrama + mapa, no
 * reemplazo": en replay, la lente ofrece AMBAS vistas vía un toggle (mismo
 * patrón ToggleButton que timeline árbol/timeline y procedencia
 * compacto/crudo) — "Diagrama" (GridSpike, la partición benchmark del run)
 * y "Mapa" (DataFormatRouter → GridMap, la red nacional REAL del ICE). En
 * vivo el toggle no existe: sigue el EmptyState "pendiente" sin cambios.
 */
describe('GridLensView — toggle Diagrama/Mapa (D4 task 6, dual diagrama + mapa)', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  test('en replay: por defecto muestra Diagrama, y el toggle "Mapa" está disponible', () => {
    vi.stubEnv('VITE_API_URL', undefined);
    render(<GridLensView />);

    expect(screen.getByTestId('cy-container')).toBeInTheDocument();
    expect(screen.queryByTestId('grid-map-stub')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /diagrama/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /mapa/i })).toBeInTheDocument();
  });

  test('en replay: clic en "Mapa" oculta el diagrama y muestra el mapa real del ICE', async () => {
    vi.stubEnv('VITE_API_URL', undefined);
    const user = userEvent.setup();
    render(<GridLensView />);

    await user.click(screen.getByRole('button', { name: /mapa/i }));

    expect(screen.queryByTestId('cy-container')).not.toBeInTheDocument();
    expect(screen.getByTestId('grid-map-stub')).toBeInTheDocument();
  });

  test('en replay: clic en "Mapa" y de vuelta en "Diagrama" restaura el spike', async () => {
    vi.stubEnv('VITE_API_URL', undefined);
    const user = userEvent.setup();
    render(<GridLensView />);

    await user.click(screen.getByRole('button', { name: /mapa/i }));
    await user.click(screen.getByRole('button', { name: /diagrama/i }));

    expect(screen.getByTestId('cy-container')).toBeInTheDocument();
    expect(screen.queryByTestId('grid-map-stub')).not.toBeInTheDocument();
  });

  test('en vivo: el toggle no existe — sigue el EmptyState "pendiente" sin cambios', () => {
    vi.stubEnv('VITE_API_URL', 'http://api.test');
    render(<GridLensView />);

    expect(screen.queryByRole('button', { name: /diagrama/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /mapa/i })).not.toBeInTheDocument();
    expect(screen.getByText(/topología en vivo/i)).toBeInTheDocument();
  });
});
