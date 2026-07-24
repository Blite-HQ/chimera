import { render, screen } from '@testing-library/react';
import { afterEach, describe, expect, test, vi } from 'vitest';

import App, { RedSlot } from './App';

/**
 * GridSpike monta cytoscape sobre un canvas real (readToken llama a
 * canvas.getContext('2d')) — jsdom no implementa un contexto 2D sin el
 * paquete `canvas`, así que se mockea acá con un doble mínimo que conserva
 * el único contrato que este archivo verifica: el testid del contenedor
 * (GridSpike.tsx `data-testid="cy-container"`). El objetivo de estos tests
 * es la SELECCIÓN de vista (D1 task 4), no el spike en sí (fuera de scope,
 * intacto).
 */
vi.mock('./spike/GridSpike', () => ({
  default: () => <div data-testid="cy-container" />
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

  test('en vivo: pendiente de D3/D4, nunca el spike IEEE-14 fabricado', () => {
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
