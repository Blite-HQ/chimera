import { render, screen } from '@testing-library/react';
import { describe, expect, test } from 'vitest';

import RunThread, { deriveRunThread } from './RunThread';

import type { ProjectedEvent, RunSummary } from './types';

/**
 * D6 (decisión #93) — dobles ETIQUETADOS: los payloads de plan.* siguen la
 * forma del fixture de costura (src/fixtures/contract/harness/*.json,
 * generado desde Pydantic); los eventos son ProjectedEvent construidos a
 * mano solo para fijar el layout del hilo (misión → checklist → cierre).
 */

const MISSION =
  'Particionar la red ieee14 en islas controladas y certificar la optimalidad del corte';

const SUMMARY: RunSummary = {
  runId: 'run-1',
  status: 'completado',
  conclusion: 'La partición propuesta de ieee14 es el óptimo exacto del corte',
  verdict: 'verified',
  titularLevel: 'AL3',
  titularClass: 'formal_exact',
  eventsCount: 8,
  actor: 'user:api',
  completedAt: '2026-07-29T12:00:05.000000Z'
};

function event(overrides: Partial<ProjectedEvent> & { readonly type: string }): ProjectedEvent {
  return {
    globalSeq: 1,
    actorId: 'service:runtime',
    occurredAt: '2026-07-29T12:00:00Z',
    resumen: overrides.type,
    ...overrides
  };
}

const PLAN_CREATED = event({
  globalSeq: 3,
  type: 'plan.created',
  payload: {
    plan_id: 'plan-run-1',
    run_id: 'run-1',
    items: [{ id: 'mission-1', description: MISSION, verification: 'delegate', status: 'pending' }]
  }
});

function planItemUpdated(globalSeq: number, status: string, cause?: string): ProjectedEvent {
  return event({
    globalSeq,
    type: 'plan.item_updated',
    payload: {
      plan_id: 'plan-run-1',
      run_id: 'run-1',
      item_id: 'mission-1',
      status,
      ...(cause !== undefined && { cause })
    }
  });
}

describe('deriveRunThread (reducer puro sobre el stream)', () => {
  test('pliega plan.item_updated sobre los ítems de plan.created (append-only)', () => {
    const thread = deriveRunThread([
      PLAN_CREATED,
      planItemUpdated(4, 'running'),
      planItemUpdated(7, 'ok')
    ]);

    expect(thread.mission).toBe(MISSION);
    expect(thread.checklist).toHaveLength(1);
    expect(thread.checklist[0].status).toBe('ok');
  });

  test('conserva la cause del último update (transición failed)', () => {
    const thread = deriveRunThread([
      PLAN_CREATED,
      planItemUpdated(4, 'running'),
      planItemUpdated(5, 'failed', 'exhausted')
    ]);

    expect(thread.checklist[0].status).toBe('failed');
    expect(thread.checklist[0].cause).toBe('exhausted');
  });

  test('sin plan.created no hay hilo (run claim-first)', () => {
    const thread = deriveRunThread([event({ type: 'run.started' })]);

    expect(thread.mission).toBeUndefined();
    expect(thread.checklist).toHaveLength(0);
  });
});

describe('RunThread (D6 — hilo conversacional como layout)', () => {
  test('renderiza la misión como mensaje del usuario y el plan como checklist', () => {
    render(
      <RunThread
        summary={{ ...SUMMARY, status: 'en_curso' }}
        events={[PLAN_CREATED, planItemUpdated(4, 'running')]}
      />
    );

    // La misión aparece 2 veces POR CONTRATO: como mensaje del usuario y
    // como description del ítem fundacional del plan (el server la siembra).
    expect(screen.getAllByText(MISSION)).toHaveLength(2);
    expect(screen.getByText(/misión/i)).toBeInTheDocument();
    expect(screen.getByText('Plan del agente')).toBeInTheDocument();
    expect(screen.getByText('running')).toBeInTheDocument();
    // Sin terminal todavía: el hilo lo dice, no lo inventa
    expect(screen.getByText(/sigue trabajando/i)).toBeInTheDocument();
  });

  test('run.completed cierra el hilo con la conclusión y el AL titular', () => {
    render(
      <RunThread
        summary={SUMMARY}
        events={[
          PLAN_CREATED,
          planItemUpdated(4, 'running'),
          planItemUpdated(7, 'ok'),
          event({ globalSeq: 8, type: 'run.completed' })
        ]}
      />
    );

    expect(screen.getByText(SUMMARY.conclusion)).toBeInTheDocument();
    expect(screen.getByText('AL3')).toBeInTheDocument();
    expect(screen.queryByText(/sigue trabajando/i)).not.toBeInTheDocument();
  });

  test('run.failed cierra el hilo con el error_kind, sin fingir veredicto', () => {
    render(
      <RunThread
        summary={{ ...SUMMARY, verdict: 'inconclusive' }}
        events={[
          PLAN_CREATED,
          planItemUpdated(4, 'running'),
          planItemUpdated(5, 'failed', 'exhausted'),
          event({ globalSeq: 6, type: 'run.failed', payload: { error_kind: 'exhausted' } })
        ]}
      />
    );

    expect(screen.getByText(/run\.failed/)).toBeInTheDocument();
    expect(screen.getAllByText(/exhausted/).length).toBeGreaterThan(0);
    expect(screen.queryByText(SUMMARY.conclusion)).not.toBeInTheDocument();
  });

  test('un run claim-first (sin plan.*) muestra el estado honesto, no un hilo fabricado', () => {
    render(<RunThread summary={SUMMARY} events={[event({ type: 'run.started' })]} />);

    expect(screen.getByText(/no arrancó de una misión/i)).toBeInTheDocument();
    expect(screen.queryByText('Plan del agente')).not.toBeInTheDocument();
  });
});
