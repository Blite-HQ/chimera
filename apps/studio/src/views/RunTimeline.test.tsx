import { render, screen } from '@testing-library/react';
import { describe, expect, test, vi } from 'vitest';

import RunTimeline from './RunTimeline';

import type { ProjectedEvent } from './types';

/**
 * Nivel-1 task 4 — verification.completed debe mostrar AssuranceBadge
 * (clase + AL) + veredicto, y claim.emitted debe mostrar un marcador de
 * declaración. `resumen` evita a propósito las mismas palabras que
 * `classLabel`/el marcador emiten, para que las aserciones por texto no
 * choquen con el cuerpo del evento.
 */
const EVENTS: readonly ProjectedEvent[] = [
  {
    globalSeq: 1,
    type: 'claim.emitted',
    actorId: 'service:runtime',
    occurredAt: '2026-07-07T17:59:50.200Z',
    resumen: 'Corte óptimo propuesto para la partición IEEE-14'
  },
  {
    globalSeq: 2,
    type: 'verification.completed',
    actorId: 'service:verifier',
    occurredAt: '2026-07-07T17:59:51.500Z',
    resumen: 'Verificación formal exacta (AL3): corte óptimo confirmado',
    verdict: 'pass',
    assurance: { verifierClass: 'formal_exact', level: 'AL3' }
  }
];

describe('RunTimeline — afordancias de verificación', () => {
  test('verification.completed renderiza el AssuranceBadge (clase + AL) en vez del Badge plano', () => {
    render(<RunTimeline events={EVENTS} onSelectEvent={vi.fn()} viewMode="timeline" />);

    expect(screen.getByText(/formal exacto/)).toBeInTheDocument();
    expect(screen.getByText('AL3')).toBeInTheDocument();
  });

  test('claim.emitted renderiza un marcador de declaración de claim', () => {
    render(<RunTimeline events={EVENTS} onSelectEvent={vi.fn()} viewMode="timeline" />);

    expect(screen.getByText(/claim declarado/i)).toBeInTheDocument();
  });
});
