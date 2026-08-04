import { render, screen } from '@testing-library/react';
import { afterEach, describe, expect, test, vi } from 'vitest';

import App from './App';

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
