import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, test, vi } from 'vitest';

import App, { RedSlot } from './App';

/**
 * GridSpike monta cytoscape sobre un canvas real (readToken llama a
 * canvas.getContext('2d')) — jsdom no implementa un contexto 2D sin el
 * paquete `canvas`, así que se mockea acá con un doble mínimo que conserva
 * el único contrato que este archivo verifica: el testid del contenedor
 * (GridSpike.tsx `data-testid="cy-container"`). El objetivo de estos tests
 * es la SELECCIÓN de vista (D1 task 4 / D4 task 6), no el spike en sí
 * (fuera de scope, intacto).
 */
vi.mock('./spike/GridSpike', () => ({
  default: () => <div data-testid="cy-container" />
}));

/**
 * D4 task 6 — GridMap dibuja el grid real del ICE con d3-geo; su propio
 * archivo de test (views/GridMap.test.tsx) ya cubre la proyección. Acá solo
 * importa que RedSlot cablee el toggle "Diagrama"/"Mapa" correctamente, así
 * que se mockea con un doble mínimo (mismo criterio que GridSpike arriba).
 */
vi.mock('./views/GridMap', () => ({
  default: () => <div data-testid="grid-map-stub" />
}));

describe('App — banner de Replay (D1, honestidad de modo)', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  test('aparece en modo replay (VITE_API_URL ausente) — nunca un default silencioso', () => {
    vi.stubEnv('VITE_API_URL', undefined);
    render(<App />);

    expect(screen.getByText(/modo replay/i)).toBeInTheDocument();
  });

  test('no aparece en modo vivo (VITE_API_URL presente)', () => {
    vi.stubEnv('VITE_API_URL', 'http://api.test');
    render(<App />);

    expect(screen.queryByText(/modo replay/i)).not.toBeInTheDocument();
  });
});

describe('RedSlot (D1 task 4 — mata el spike como vista "Red" en vivo)', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  test('en vivo: pendiente (falta productor de partición, decisión #88), nunca el spike IEEE-14 fabricado', () => {
    vi.stubEnv('VITE_API_URL', 'http://api.test');
    render(<RedSlot />);

    expect(screen.getByText(/topología en vivo/i)).toBeInTheDocument();
    expect(screen.queryByTestId('cy-container')).not.toBeInTheDocument();
  });

  test('en replay: el spike IEEE-14 (etiquetado por el banner global, no acá)', () => {
    vi.stubEnv('VITE_API_URL', undefined);
    render(<RedSlot />);

    expect(screen.getByTestId('cy-container')).toBeInTheDocument();
  });
});

/**
 * D4 task 6 — spec superficie-visual.md §4.3 "dual diagrama + mapa, no
 * reemplazo": en replay, RedSlot ofrece AMBAS vistas vía un toggle (mismo
 * patrón ToggleButton que timeline árbol/timeline y procedencia
 * compacto/crudo) — "Diagrama" (GridSpike, la partición benchmark del run)
 * y "Mapa" (DataFormatRouter → GridMap, la red nacional REAL del ICE). En
 * vivo el toggle no existe: sigue el EmptyState "pendiente" sin cambios.
 */
describe('RedSlot — toggle Diagrama/Mapa (D4 task 6, dual diagrama + mapa)', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  test('en replay: por defecto muestra Diagrama, y el toggle "Mapa" está disponible', () => {
    vi.stubEnv('VITE_API_URL', undefined);
    render(<RedSlot />);

    expect(screen.getByTestId('cy-container')).toBeInTheDocument();
    expect(screen.queryByTestId('grid-map-stub')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /diagrama/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /mapa/i })).toBeInTheDocument();
  });

  test('en replay: clic en "Mapa" oculta el diagrama y muestra el mapa real del ICE', async () => {
    vi.stubEnv('VITE_API_URL', undefined);
    const user = userEvent.setup();
    render(<RedSlot />);

    await user.click(screen.getByRole('button', { name: /mapa/i }));

    expect(screen.queryByTestId('cy-container')).not.toBeInTheDocument();
    expect(screen.getByTestId('grid-map-stub')).toBeInTheDocument();
  });

  test('en replay: clic en "Mapa" y de vuelta en "Diagrama" restaura el spike', async () => {
    vi.stubEnv('VITE_API_URL', undefined);
    const user = userEvent.setup();
    render(<RedSlot />);

    await user.click(screen.getByRole('button', { name: /mapa/i }));
    await user.click(screen.getByRole('button', { name: /diagrama/i }));

    expect(screen.getByTestId('cy-container')).toBeInTheDocument();
    expect(screen.queryByTestId('grid-map-stub')).not.toBeInTheDocument();
  });

  test('en vivo: el toggle no existe — sigue el EmptyState "pendiente" sin cambios', () => {
    vi.stubEnv('VITE_API_URL', 'http://api.test');
    render(<RedSlot />);

    expect(screen.queryByRole('button', { name: /diagrama/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /mapa/i })).not.toBeInTheDocument();
    expect(screen.getByText(/topología en vivo/i)).toBeInTheDocument();
  });
});
